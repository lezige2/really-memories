// kvmem_page.cpp -- paged KV memory: does putting a block in the window restore recall?
//
// Experiment A measured the binding constraint: the frozen model reads back roughly
// 4-6k tokens, and recall is exactly 0 beyond ~8k no matter how much KV is resident.
// "Resident" and "readable" are therefore different properties, and the interesting
// one is positional distance, not VRAM capacity.
//
// This tool tests the placement layer on its own, with a PERFECT index (oracle), so
// that a failure cannot be blamed on retrieval:
//
//   build  split the document into blocks (one paragraph each), decode every block
//          STANDALONE at position 0.. so its K/V is valid for the window slot, and
//          dump each block's KV to disk.  Nothing here depends on the question.
//
//   query  for each question: wipe the chat sequence, load the block that is known
//          to contain the answer (oracle index = the qa id), decode the question
//          right after the block, generate.
//
// The block's positions are 0..n-1 and the question sits at n, so the distance is
// at most one block -- inside the readable window by construction. Compare against
// the flat run (results_20k_kv_q8_0.tsv), where the same facts sat 8-19k tokens back
// and scored 4/20.
//
// Because every block is encoded at the same canonical position range (starting at
// 0), swapping blocks needs no re-rotation of K and no engine change at all: it is
// the llama_state_seq_set_data path already proven to survive a process boundary.
//
// Modes:
//   build -m model.gguf -f doc.txt --outdir DIR [--kv f16|q8_0] [--gpu N] [--verbose]
//   query -m model.gguf -q qa.tsv --index DIR/index.tsv [--limit K] [--out FILE]
//
// index.tsv columns: block_id <TAB> n_tokens <TAB> n_bytes <TAB> file
//
// Exit code: 0 = ran to completion, 1 = runtime error, 2 = bad arguments.

#include "llama.h"

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

static const llama_seq_id SEQ_MEM  = 0;
static const llama_seq_id SEQ_CHAT = 1;

static const llama_vocab * g_vocab = nullptr;
static bool g_verbose = false;
// qid -> block_id, produced by tools/retrieval_baseline.py --emit-rank
static std::map<int, int> g_rank;

static void quiet_log(ggml_log_level, const char * text, void * /*user_data*/) {
    if (!g_verbose) {
        return;
    }
    fputs(text, stderr);
}

struct opts {
    std::string  mode;
    const char * model_path  = nullptr;
    const char * doc_path    = nullptr;
    const char * qa_path     = nullptr;
    const char * index_path  = nullptr;
    const char * out_path    = nullptr;
    const char * outdir      = nullptr;
    int          n_gpu_layers = 0;
    int          n_ctx        = 32768;
    int          n_predict    = 64;
    int          limit        = 0;
    bool         wrong        = false;
    std::string  rank_path;
    ggml_type    kv_type      = GGML_TYPE_Q8_0;
};

struct qa_item {
    int         id = 0;
    std::string question;
    std::string expect;
};

struct block_rec {
    int    id = 0;
    int    n_tokens = 0;
    size_t n_bytes = 0;
    std::string file;
};

static const char * type_name(ggml_type t) {
    return (t == GGML_TYPE_Q8_0) ? "q8_0" : (t == GGML_TYPE_F16 ? "f16" : ggml_type_name(t));
}

static bool read_text(const char * path, std::string & out) {
    FILE * f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "cannot open %s\n", path);
        return false;
    }
    char buf[65536];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0) {
        out.append(buf, n);
    }
    fclose(f);
    return true;
}

static bool read_qa(const char * path, std::vector<qa_item> & out) {
    std::string raw;
    if (!read_text(path, raw)) {
        return false;
    }
    size_t pos = 0;
    while (pos < raw.size()) {
        size_t eol = raw.find('\n', pos);
        if (eol == std::string::npos) {
            eol = raw.size();
        }
        std::string line = raw.substr(pos, eol - pos);
        pos = eol + 1;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const size_t t1 = line.find('\t');
        const size_t t2 = (t1 == std::string::npos) ? std::string::npos : line.find('\t', t1 + 1);
        if (t2 == std::string::npos) {
            continue;
        }
        qa_item it;
        it.id       = atoi(line.substr(0, t1).c_str());
        it.question = line.substr(t1 + 1, t2 - t1 - 1);
        it.expect   = line.substr(t2 + 1);
        out.push_back(it);
    }
    return !out.empty();
}

static bool read_index(const char * path, std::vector<block_rec> & out) {
    std::string raw;
    if (!read_text(path, raw)) {
        return false;
    }
    size_t pos = 0;
    while (pos < raw.size()) {
        size_t eol = raw.find('\n', pos);
        if (eol == std::string::npos) {
            eol = raw.size();
        }
        std::string line = raw.substr(pos, eol - pos);
        pos = eol + 1;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        char file[512];
        block_rec r;
        if (sscanf(line.c_str(), "%d\t%d\t%zu\t%511s", &r.id, &r.n_tokens, &r.n_bytes, file) == 4) {
            r.file = file;
            out.push_back(r);
        }
    }
    return !out.empty();
}

// rank.tsv: qid <TAB> block_id
static bool read_rank(const char * path) {
    std::string raw;
    if (!read_text(path, raw)) {
        return false;
    }
    size_t pos = 0;
    while (pos < raw.size()) {
        size_t eol = raw.find('\n', pos);
        if (eol == std::string::npos) {
            eol = raw.size();
        }
        std::string line = raw.substr(pos, eol - pos);
        pos = eol + 1;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        int qid = 0, bid = 0;
        if (sscanf(line.c_str(), "%d\t%d", &qid, &bid) == 2) {
            g_rank[qid] = bid;
        }
    }
    return !g_rank.empty();
}

static std::vector<llama_token> tokenize(const std::string & text, bool add_special) {
    if (text.empty()) {
        return {};
    }
    std::vector<llama_token> out(text.size() + 16);
    int n = llama_tokenize(g_vocab, text.c_str(), (int32_t) text.size(),
                           out.data(), (int32_t) out.size(), add_special, true);
    if (n < 0) {
        out.resize((size_t) -n);
        n = llama_tokenize(g_vocab, text.c_str(), (int32_t) text.size(),
                           out.data(), (int32_t) out.size(), add_special, true);
    }
    out.resize(n > 0 ? (size_t) n : 0);
    return out;
}

static bool decode_chunked(llama_context * ctx, const std::vector<llama_token> & ids,
                           llama_pos pos0, llama_seq_id seq, bool want_logits) {
    const int n_batch = 512;
    const int n = (int) ids.size();
    for (int off = 0; off < n; off += n_batch) {
        const int cnt = (n - off < n_batch) ? (n - off) : n_batch;
        llama_batch b = llama_batch_init(cnt, 0, 1);
        for (int i = 0; i < cnt; i++) {
            b.token[i]     = ids[off + i];
            b.pos[i]       = pos0 + off + i;
            b.n_seq_id[i]  = 1;
            b.seq_id[i][0] = seq;
            b.logits[i]    = (want_logits && (off + i) == n - 1) ? 1 : 0;
        }
        b.n_tokens = cnt;
        const int rc = llama_decode(ctx, b);
        llama_batch_free(b);
        if (rc != 0) {
            fprintf(stderr, "llama_decode failed (rc=%d)\n", rc);
            return false;
        }
    }
    return true;
}

static std::string generate(llama_context * ctx, llama_sampler * smpl, llama_seq_id seq,
                            llama_pos & pos, int n_predict) {
    std::string out;
    for (int i = 0; i < n_predict; i++) {
        const llama_token id = llama_sampler_sample(smpl, ctx, -1);
        if (llama_vocab_is_eog(g_vocab, id)) {
            break;
        }
        char buf[256];
        const int nb = llama_token_to_piece(g_vocab, id, buf, sizeof(buf), 0, false);
        if (nb > 0) {
            out.append(buf, nb);
        }
        std::vector<llama_token> one(1, id);
        if (!decode_chunked(ctx, one, pos, seq, true)) {
            out += " [decode error]";
            break;
        }
        pos++;
    }
    return out;
}

static std::string one_line(const std::string & s) {
    std::string r;
    bool prev_space = false;
    for (char c : s) {
        const char ch = (c == '\t' || c == '\n' || c == '\r') ? ' ' : c;
        if (ch == ' ' && prev_space) {
            continue;
        }
        r += ch;
        prev_space = (ch == ' ');
    }
    return r;
}

static bool parse_args(int argc, char ** argv, opts & o) {
    if (argc < 2) {
        return false;
    }
    o.mode = argv[1];
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "-m") && i + 1 < argc)          { o.model_path = argv[++i]; }
        else if (!strcmp(argv[i], "-f") && i + 1 < argc)     { o.doc_path   = argv[++i]; }
        else if (!strcmp(argv[i], "-q") && i + 1 < argc)     { o.qa_path    = argv[++i]; }
        else if (!strcmp(argv[i], "--index") && i + 1 < argc) { o.index_path = argv[++i]; }
        else if (!strcmp(argv[i], "--out") && i + 1 < argc)  { o.out_path   = argv[++i]; }
        else if (!strcmp(argv[i], "--outdir") && i + 1 < argc) { o.outdir   = argv[++i]; }
        else if (!strcmp(argv[i], "--gpu") && i + 1 < argc)  { o.n_gpu_layers = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--ctx") && i + 1 < argc)  { o.n_ctx        = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--n") && i + 1 < argc)    { o.n_predict    = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--limit") && i + 1 < argc) { o.limit       = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--wrong"))                { o.wrong = true; }
        else if (!strcmp(argv[i], "--rank") && i + 1 < argc) { o.rank_path = argv[++i]; }
        else if (!strcmp(argv[i], "--verbose"))              { g_verbose = true; }
        else if (!strcmp(argv[i], "--kv") && i + 1 < argc) {
            const char * kv = argv[++i];
            if (!strcmp(kv, "f16"))        { o.kv_type = GGML_TYPE_F16; }
            else if (!strcmp(kv, "q8_0"))  { o.kv_type = GGML_TYPE_Q8_0; }
            else { fprintf(stderr, "unknown --kv type: %s\n", kv); return false; }
        } else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            return false;
        }
    }
    return o.model_path != nullptr;
}

struct session {
    llama_model   * model = nullptr;
    llama_context * ctx   = nullptr;
    llama_sampler * smpl  = nullptr;

    bool init(const opts & o) {
        llama_model_params mparams = llama_model_default_params();
        mparams.n_gpu_layers = o.n_gpu_layers;

        model = llama_model_load_from_file(o.model_path, mparams);
        if (!model) {
            fprintf(stderr, "failed to load model: %s\n", o.model_path);
            return false;
        }
        g_vocab = llama_model_get_vocab(model);

        llama_context_params cparams = llama_context_default_params();
        cparams.n_ctx      = (uint32_t) o.n_ctx;
        cparams.n_batch    = 512;
        cparams.n_ubatch   = 512;
        cparams.n_seq_max  = 8;
        cparams.kv_unified = true;
        cparams.type_k     = o.kv_type;
        cparams.type_v     = o.kv_type;
        cparams.flash_attn_type = (o.kv_type != GGML_TYPE_F16)
            ? LLAMA_FLASH_ATTN_TYPE_ENABLED
            : LLAMA_FLASH_ATTN_TYPE_AUTO;

        ctx = llama_init_from_model(model, cparams);
        if (!ctx) {
            fprintf(stderr, "failed to create context\n");
            return false;
        }

        llama_sampler_chain_params sparams = llama_sampler_chain_default_params();
        smpl = llama_sampler_chain_init(sparams);
        llama_sampler_chain_add(smpl, llama_sampler_init_greedy());
        return true;
    }

    ~session() {
        if (smpl)  { llama_sampler_free(smpl); }
        if (ctx)   { llama_free(ctx); }
        if (model) { llama_model_free(model); }
    }
};

// ---------------------------------------------------------------- build

static int cmd_build(const opts & o) {
    if (!o.doc_path || !o.outdir) {
        fprintf(stderr, "build: -f <doc> and --outdir <dir> are required\n");
        return 2;
    }
    std::string doc;
    if (!read_text(o.doc_path, doc)) {
        return 1;
    }

    session s;
    if (!s.init(o)) {
        return 1;
    }
    llama_memory_t mem = llama_get_memory(s.ctx);

    // One paragraph == one block. The generator emits one planted fact per paragraph,
    // and the qa id *is* the paragraph index, so the oracle index needs no offset math.
    std::vector<std::string> paras;
    {
        size_t pos = 0;
        while (pos < doc.size()) {
            size_t sep = doc.find("\n\n", pos);
            if (sep == std::string::npos) {
                sep = doc.size();
            }
            std::string p = doc.substr(pos, sep - pos);
            if (!p.empty() && p.back() == '\n') {
                p.pop_back();
            }
            if (!p.empty()) {
                paras.push_back(p);
            }
            pos = sep + 2;
        }
    }

    printf("[build] kv=%s  paragraphs=%zu  outdir=%s\n",
           type_name(o.kv_type), paras.size(), o.outdir);

    std::string index_path = std::string(o.outdir) + "/index.tsv";
    FILE * idx = fopen(index_path.c_str(), "wb");
    if (!idx) {
        fprintf(stderr, "cannot write %s\n", index_path.c_str());
        return 1;
    }
    fprintf(idx, "# block_id\tn_tokens\tn_bytes\tfile\n");

    size_t total_bytes = 0;
    const auto t_all = std::chrono::steady_clock::now();

    for (size_t i = 0; i < paras.size(); i++) {
        const std::vector<llama_token> ids = tokenize(paras[i], true);
        if (ids.empty()) {
            fprintf(stderr, "[build] block %zu is empty after tokenization\n", i);
            return 1;
        }

        // Every block starts at position 0. That is what makes blocks interchangeable
        // in the window: no re-rotation, no position bookkeeping.
        llama_memory_seq_rm(mem, SEQ_MEM, 0, -1);
        const auto t0 = std::chrono::steady_clock::now();
        if (!decode_chunked(s.ctx, ids, 0, SEQ_MEM, false)) {
            fprintf(stderr, "[build] block %zu decode failed\n", i);
            return 1;
        }
        const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

        const llama_pos pm = llama_memory_seq_pos_max(mem, SEQ_MEM);
        if (pm != (llama_pos) ids.size() - 1) {
            fprintf(stderr, "[build] block %zu unexpected pos_max %d\n", i, (int) pm);
            return 1;
        }

        const size_t n_bytes = llama_state_seq_get_size(s.ctx, SEQ_MEM);
        std::vector<uint8_t> blob(n_bytes);
        const size_t got = llama_state_seq_get_data(s.ctx, blob.data(), blob.size(), SEQ_MEM);
        if (got != n_bytes) {
            fprintf(stderr, "[build] block %zu get_data %zu != %zu\n", i, got, n_bytes);
            return 1;
        }

        char name[512];
        snprintf(name, sizeof(name), "%s/b%03zu.kvmem", o.outdir, i);
        FILE * f = fopen(name, "wb");
        if (!f) {
            fprintf(stderr, "cannot write %s\n", name);
            fclose(idx);
            return 1;
        }
        if (fwrite(blob.data(), 1, blob.size(), f) != blob.size()) {
            fprintf(stderr, "short write %s\n", name);
            fclose(f);
            fclose(idx);
            return 1;
        }
        fclose(f);

        fprintf(idx, "%zu\t%zu\t%zu\t%s\n", i, ids.size(), blob.size(), name);
        total_bytes += blob.size();
        printf("[build] block %3zu  %5zu tokens  %6.1f MiB  prefill %5.1f t/s\n",
               i, ids.size(), (double) blob.size() / (1024.0 * 1024.0),
               (double) ids.size() / secs);
    }
    fclose(idx);

    const double total_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t_all).count();
    printf("[build] %zu blocks, %.2f GiB on disk, %.0f s total\n",
           paras.size(), (double) total_bytes / (1024.0 * 1024.0 * 1024.0), total_s);
    printf("[build] index -> %s\n", index_path.c_str());
    return 0;
}

// ---------------------------------------------------------------- query (oracle index)

static int cmd_query(const opts & o) {
    if (!o.qa_path || !o.index_path) {
        fprintf(stderr, "query: -q <qa.tsv> and --index <index.tsv> are required\n");
        return 2;
    }
    std::vector<qa_item> qa;
    if (!read_qa(o.qa_path, qa)) {
        fprintf(stderr, "query: cannot read %s\n", o.qa_path);
        return 1;
    }
    std::vector<block_rec> blocks;
    if (!read_index(o.index_path, blocks)) {
        fprintf(stderr, "query: cannot read %s\n", o.index_path);
        return 1;
    }
    if (o.limit > 0 && (int) qa.size() > o.limit) {
        qa.resize(o.limit);
    }
    if (!o.rank_path.empty() && !read_rank(o.rank_path.c_str())) {
        fprintf(stderr, "query: cannot read rank file %s\n", o.rank_path.c_str());
        return 1;
    }

    session s;
    if (!s.init(o)) {
        return 1;
    }
    llama_memory_t mem = llama_get_memory(s.ctx);

    printf("[query] kv=%s  blocks=%zu  questions=%zu  n_ctx=%d  unified=1\n",
           type_name(o.kv_type), blocks.size(), qa.size(), o.n_ctx);

    FILE * out = o.out_path ? fopen(o.out_path, "wb") : stdout;
    if (!out) {
        fprintf(stderr, "cannot open %s\n", o.out_path);
        return 1;
    }

    int n_ok = 0;
    double load_s = 0.0;
    for (size_t qi = 0; qi < qa.size(); qi++) {
        const qa_item & item = qa[qi];

        // Oracle index: the question's id is the paragraph that holds the answer.
        // --rank FILE replaces the oracle with a real retriever's output
        // (qid<TAB>block_id), which is what turns the 85% ceiling into an end-to-end
        // number. --wrong deliberately fetches a neighbouring block instead, which
        // must drag accuracy back down to the "no memory" floor.
        int want_id = item.id;
        if (!o.rank_path.empty()) {
            auto it = g_rank.find(item.id);
            if (it != g_rank.end()) {
                want_id = it->second;
            }
        }
        if (o.wrong) {
            want_id = (item.id + 1) % (int) blocks.size();
        }
        const block_rec * blk = nullptr;
        for (const auto & b : blocks) {
            if (b.id == want_id) {
                blk = &b;
                break;
            }
        }
        if (!blk) {
            fprintf(stderr, "[query] no block for id=%d\n", item.id);
            return 1;
        }

        std::vector<uint8_t> blob(blk->n_bytes);
        FILE * f = fopen(blk->file.c_str(), "rb");
        if (!f) {
            fprintf(stderr, "cannot open %s\n", blk->file.c_str());
            return 1;
        }
        const size_t got = fread(blob.data(), 1, blob.size(), f);
        fclose(f);
        if (got != blob.size()) {
            fprintf(stderr, "short read %s\n", blk->file.c_str());
            return 1;
        }

        // Swap the block into the window: drop whatever was in the chat seq, then
        // restore this block's KV at its canonical positions (0..n-1).
        llama_memory_seq_rm(mem, SEQ_CHAT, 0, -1);
        const auto t0 = std::chrono::steady_clock::now();
        if (llama_state_seq_set_data(s.ctx, blob.data(), blob.size(), SEQ_CHAT) == 0) {
            fprintf(stderr, "[query] set_data failed for block %d\n", blk->id);
            return 1;
        }
        load_s += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

        const llama_pos pm = llama_memory_seq_pos_max(mem, SEQ_CHAT);
        if (pm != (llama_pos) blk->n_tokens - 1) {
            fprintf(stderr, "[query] block %d pos_max %d != %d\n", blk->id, (int) pm, blk->n_tokens - 1);
            return 1;
        }

        const std::string prompt = item.question + "\n答：";
        const std::vector<llama_token> q_ids = tokenize(prompt, false);
        const llama_pos pos0 = (llama_pos) blk->n_tokens;
        if (!decode_chunked(s.ctx, q_ids, pos0, SEQ_CHAT, true)) {
            fprintf(stderr, "[query] question decode failed\n");
            return 1;
        }
        llama_pos gen_pos = pos0 + (llama_pos) q_ids.size();
        const std::string answer = generate(s.ctx, s.smpl, SEQ_CHAT, gen_pos, o.n_predict);

        const bool ok = answer.find(item.expect) != std::string::npos;
        if (ok) {
            n_ok++;
        }
        fprintf(out, "%d\tpage\t%s\t%d\t%s\n", item.id, type_name(o.kv_type), blk->n_tokens,
                one_line(answer).c_str());
        fflush(out);

        printf("[query] %2zu/%zu id=%-2d block=%-2d dist=%-5d %s\n", qi + 1, qa.size(),
               item.id, blk->id, blk->n_tokens,
               ok ? "HIT" : "MISS");
    }
    if (o.out_path) {
        fclose(out);
    }

    printf("[query] ---\n");
    printf("[query] hits %d/%zu = %.0f%%   avg block load %.2f s\n",
           n_ok, qa.size(), 100.0 * n_ok / (double) qa.size(),
           load_s / (double) qa.size());
    return 0;
}

int main(int argc, char ** argv) {
    opts o;
    if (!parse_args(argc, argv, o)) {
        fprintf(stderr,
            "usage:\n"
            "  %s build -m model.gguf -f doc.txt --outdir DIR [--kv f16|q8_0] [--gpu N]\n"
            "  %s query -m model.gguf -q qa.tsv --index DIR/index.tsv [--limit K] [--out FILE]\n",
            argv[0], argv[0]);
        return 2;
    }

    llama_log_set(quiet_log, nullptr);
    llama_backend_init();
    int rc = 2;
    if (o.mode == "build") {
        rc = cmd_build(o);
    } else if (o.mode == "query") {
        rc = cmd_query(o);
    } else {
        fprintf(stderr, "unknown mode: %s\n", o.mode.c_str());
    }
    llama_backend_free();
    return rc;
}