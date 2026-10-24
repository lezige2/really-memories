// kvmem_quality.cpp -- experiment "A": does a 5k-token KV memory actually get read?
//
// Arms (one process run per arm):
//   full  : document prefilled into the chat seq, then the question appended.
//           This is the "stuff everything into the context" baseline, and it is the
//           denominator for the >=90% acceptance bar.
//   kv    : document decoded once into seq 0 (positions 0..N-1), seq_cp 0->1, and the
//           question appended at position N. The prompt holds only the question.
//   none  : question only, no memory at all. Control: if this answers correctly the
//           question leaks its own answer and the run is invalid.
//
// Note on full vs kv: they are *the same token sequence at the same positions*
// (BOS + doc + question). The answers should therefore be identical. A difference
// means a bug, not a finding. The real variables are kv type (f16 vs q8_0) and the
// depth at which a fact sits inside the document.
//
// Modes:
//   run    -m model.gguf -f doc.txt -q qa.tsv --arm full|kv|none [--kv f16|q8_0]
//          [--gpu N] [--ctx N] [--n N] [--limit K] [--out results.tsv]
//   count  -m model.gguf -f doc.txt
//
// results.tsv columns: id  arm  kv  n_doc  answer(one line, tabs/newlines escaped)
//
// Exit code: 0 = ran to completion, 2 = bad arguments, 1 = runtime error.

#include "llama.h"

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static const llama_seq_id SEQ_MEM  = 0;
static const llama_seq_id SEQ_CHAT = 1;

static const llama_vocab * g_vocab = nullptr;

// llama.cpp is extremely chatty on stderr (it dumps the whole metadata table and the
// graph inputs for every reserve). Drop info/debug unless --verbose is passed, so a
// 20-question run does not bury its own results.
static bool g_verbose = false;

static void quiet_log(ggml_log_level level, const char * text, void * /*user_data*/) {
    // Windows PowerShell 5.1 turns *any* stderr line from a native command into a
    // NativeCommandError, which terminates a calling script that sets
    // $ErrorActionPreference='Stop'. llama.cpp emits routine warnings on stderr, so
    // stay silent unless --verbose was asked for.
    if (!g_verbose) {
        return;
    }
    (void) level;
    fputs(text, stderr);
}

struct qa_item {
    int         id = 0;
    std::string question;
    std::string expect;
};

struct opts {
    std::string  mode;
    const char * model_path = nullptr;
    const char * doc_path   = nullptr;
    const char * qa_path    = nullptr;
    const char * out_path   = nullptr;
    std::string  arm        = "full";
    int          n_gpu_layers = 0;
    int          n_ctx        = 8192;
    int          n_predict    = 64;
    int          limit        = 0;   // 0 = all
    ggml_type    kv_type      = GGML_TYPE_F16;
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

// qa.tsv: id <TAB> question <TAB> expected answer. Lines starting with '#' skipped.
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
        if (t1 == std::string::npos) {
            continue;
        }
        const size_t t2 = line.find('\t', t1 + 1);
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

// Decode `ids` starting at `pos0`, in chunks of n_batch so that the `full` and `kv`
// arms feed the graph in exactly the same order (otherwise any difference between
// them would be a batching artefact, not an algorithmic one).
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
            fprintf(stderr, "llama_decode failed (rc=%d) at token %d\n", rc, off);
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
    std::string o;
    o.reserve(s.size());
    for (char c : s) {
        if (c == '\t' || c == '\n' || c == '\r') {
            o += ' ';
        } else {
            o += c;
        }
    }
    // collapse runs of spaces so the output stays readable
    std::string r;
    bool prev_space = false;
    for (char c : o) {
        const bool is_space = (c == ' ');
        if (is_space && prev_space) {
            continue;
        }
        r += c;
        prev_space = is_space;
    }
    return r;
}

static bool parse_args(int argc, char ** argv, opts & o) {
    if (argc < 2) {
        return false;
    }
    o.mode = argv[1];
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "-m") && i + 1 < argc)        { o.model_path = argv[++i]; }
        else if (!strcmp(argv[i], "-f") && i + 1 < argc)   { o.doc_path   = argv[++i]; }
        else if (!strcmp(argv[i], "-q") && i + 1 < argc)   { o.qa_path    = argv[++i]; }
        else if (!strcmp(argv[i], "--out") && i + 1 < argc) { o.out_path  = argv[++i]; }
        else if (!strcmp(argv[i], "--arm") && i + 1 < argc) { o.arm       = argv[++i]; }
        else if (!strcmp(argv[i], "--gpu") && i + 1 < argc) { o.n_gpu_layers = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--ctx") && i + 1 < argc) { o.n_ctx        = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--n") && i + 1 < argc)   { o.n_predict    = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--limit") && i + 1 < argc) { o.limit      = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--verbose"))            { g_verbose = true; }
        else if (!strcmp(argv[i], "--kv") && i + 1 < argc) {
            const char * kv = argv[++i];
            if (!strcmp(kv, "f16")) {
                o.kv_type = GGML_TYPE_F16;
            } else if (!strcmp(kv, "q8_0")) {
                o.kv_type = GGML_TYPE_Q8_0;
            } else {
                fprintf(stderr, "unknown --kv type: %s\n", kv);
                return false;
            }
        } else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            return false;
        }
    }
    return o.model_path != nullptr && o.doc_path != nullptr;
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
        cparams.kv_unified = true;    // one shared pool: n_ctx_seq == n_ctx
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

static int cmd_count(const opts & o) {
    session s;
    if (!s.init(o)) {
        return 1;
    }
    std::string doc;
    if (!read_text(o.doc_path, doc)) {
        return 1;
    }
    const std::vector<llama_token> ids = tokenize(doc, true);
    printf("doc chars   = %zu\n", doc.size());
    printf("doc tokens  = %zu\n", ids.size());
    printf("chars/token = %.2f\n", (double) doc.size() / (double) (ids.empty() ? 1 : ids.size()));
    return 0;
}

static int cmd_run(const opts & o) {
    if (!o.qa_path) {
        fprintf(stderr, "run: -q <qa.tsv> is required\n");
        return 2;
    }
    std::string doc;
    if (!read_text(o.doc_path, doc)) {
        return 1;
    }
    std::vector<qa_item> qa;
    if (!read_qa(o.qa_path, qa)) {
        fprintf(stderr, "run: cannot read qa table %s\n", o.qa_path);
        return 1;
    }
    if (o.limit > 0 && (int) qa.size() > o.limit) {
        qa.resize(o.limit);
    }

    session s;
    if (!s.init(o)) {
        return 1;
    }
    llama_memory_t mem = llama_get_memory(s.ctx);

    // The document is tokenized once, with BOS, and prefilled in fixed chunks. In the
    // `kv` arm this happens once for the whole run; in `full` it happens per question.
    const std::vector<llama_token> doc_ids = tokenize(doc, true);
    const int n_doc = (int) doc_ids.size();
    if (n_doc + 256 >= o.n_ctx) {
        fprintf(stderr, "document (%d tokens) does not fit in n_ctx=%d\n", n_doc, o.n_ctx);
        return 1;
    }

    printf("[run] arm=%s kv=%s n_ctx=%d n_ctx_seq=%d unified=1\n",
           o.arm.c_str(), type_name(o.kv_type), o.n_ctx, (int) llama_n_ctx_seq(s.ctx));
    printf("[run] doc=%d tokens  questions=%zu  n_predict=%d\n", n_doc, qa.size(), o.n_predict);

    FILE * out = o.out_path ? fopen(o.out_path, "wb") : stdout;
    if (!out) {
        fprintf(stderr, "cannot open %s for writing\n", o.out_path);
        return 1;
    }

    const bool use_kv    = (o.arm == "kv");
    const bool use_full  = (o.arm == "full");
    if (!use_kv && !use_full && o.arm != "none") {
        fprintf(stderr, "unknown arm: %s (use full|kv|none)\n", o.arm.c_str());
        return 2;
    }

    // kv arm: build the memory once, before any question.
    double prefill_s = 0.0;
    if (use_kv) {
        const auto t0 = std::chrono::steady_clock::now();
        if (!decode_chunked(s.ctx, doc_ids, 0, SEQ_MEM, false)) {
            fprintf(stderr, "[run] memory prefill failed\n");
            return 1;
        }
        prefill_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        const llama_pos pm = llama_memory_seq_pos_max(mem, SEQ_MEM);
        printf("[run] memory prefilled: %d tokens, seq%d pos_max=%d, %.1f t/s\n",
               n_doc, (int) SEQ_MEM, (int) pm, (double) n_doc / prefill_s);
        if (pm != (llama_pos) n_doc - 1) {
            fprintf(stderr, "[run] unexpected memory pos_max\n");
            return 1;
        }
    }

    int n_ok = 0;
    for (size_t qi = 0; qi < qa.size(); qi++) {
        const qa_item & item = qa[qi];

        // Reset the chat sequence; the memory sequence keeps its own claim.
        llama_memory_seq_rm(mem, SEQ_CHAT, 0, -1);

        llama_pos pos = 0;
        if (use_full) {
            const auto t0 = std::chrono::steady_clock::now();
            if (!decode_chunked(s.ctx, doc_ids, 0, SEQ_CHAT, false)) {
                fprintf(stderr, "[run] doc prefill failed\n");
                return 1;
            }
            prefill_s += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            pos = n_doc;
        } else if (use_kv) {
            llama_memory_seq_cp(mem, SEQ_MEM, SEQ_CHAT, 0, -1);
            pos = (llama_pos) n_doc;
        }

        // The prompt carries the question only. Each question gets a tiny wrapper so
        // the model answers short instead of rambling.
        const std::string prompt = item.question + "\n答：";
        const std::vector<llama_token> q_ids = tokenize(prompt, use_kv || use_full ? false : true);
        if (!decode_chunked(s.ctx, q_ids, pos, SEQ_CHAT, true)) {
            fprintf(stderr, "[run] question decode failed (id=%d)\n", item.id);
            return 1;
        }
        llama_pos gen_pos = pos + (llama_pos) q_ids.size();
        std::string answer = generate(s.ctx, s.smpl, SEQ_CHAT, gen_pos, o.n_predict);

        const bool ok = answer.find(item.expect) != std::string::npos;
        if (ok) {
            n_ok++;
        }
        fprintf(out, "%d\t%s\t%s\t%d\t%s\n", item.id, o.arm.c_str(), type_name(o.kv_type),
                n_doc, one_line(answer).c_str());
        fflush(out);

        printf("[run] %2d/%zu id=%-2d %-8s %s\n", (int) qi + 1, qa.size(), item.id,
               ok ? "HIT" : "MISS", one_line(answer).substr(0, 60).c_str());
    }

    if (o.out_path) {
        fclose(out);
    }

    printf("[run] ---\n");
    printf("[run] arm=%s kv=%s  exact-substring hits: %d/%zu (%.0f%%)\n",
           o.arm.c_str(), type_name(o.kv_type), n_ok, qa.size(),
           100.0 * (double) n_ok / (double) qa.size());
    printf("[run] prefill time total = %.1f s (%.1f t/s avg)\n",
           prefill_s, prefill_s > 0 ? (double) n_doc * (use_full ? (double) qa.size() : 1.0) / prefill_s : 0.0);
    if (o.out_path) {
        printf("[run] results -> %s\n", o.out_path);
    }
    return 0;
}

int main(int argc, char ** argv) {
    opts o;
    if (!parse_args(argc, argv, o)) {
        fprintf(stderr,
            "usage:\n"
            "  %s run   -m model.gguf -f doc.txt -q qa.tsv --arm full|kv|none [--kv f16|q8_0]\n"
            "          [--gpu N] [--ctx N] [--n N] [--limit K] [--out results.tsv]\n"
            "  %s count -m model.gguf -f doc.txt\n",
            argv[0], argv[0]);
        return 2;
    }

    llama_log_set(quiet_log, nullptr);
    llama_backend_init();
    int rc = 2;
    if (o.mode == "run") {
        rc = cmd_run(o);
    } else if (o.mode == "count") {
        rc = cmd_count(o);
    } else {
        fprintf(stderr, "unknown mode: %s\n", o.mode.c_str());
    }
    llama_backend_free();
    return rc;
}