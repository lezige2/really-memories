// kvshim.cpp -- flat C ABI over llama.cpp's per-sequence KV state API.
//
// Why a shim instead of ctypes on llama.h directly: llama_context_params and
// llama_batch are structs passed by value, and a single wrong field offset in a
// ctypes definition corrupts the whole context silently. Everything that crosses
// this boundary is int / long long / char*, so the Python side cannot mis-lay-out
// anything.
//
// What it demonstrates (README-HANDOFF-2.md section 6.5):
//
//   1. A conversation can be decoded into a named sequence, its KV state written to
//      a binary file, the context fully dropped, and the state read back into a
//      *different* sequence id -- with no text ever passed through a prompt. The
//      model answers from the restored KV alone.
//
//   2. A memory block can live in its own sequence and be made visible to a chat
//      sequence with llama_memory_seq_cp, which copies *cell indices* (refcount
//      only). Nothing is copied, nothing is re-prefilled, no text is concatenated.
//
// Layout constraint that makes (2) sound: the block occupies positions [0, n) and
// the chat must start at position >= n (the demo uses a fixed window W). Causal
// attention needs memory *below* the dialogue, and positions cannot collide inside
// one sequence.
//
// Build (see build_tools.ps1 -Dll):
//   clang++ -std=c++17 -O2 -static -shared ... -o tools/kvshim.dll

#include "llama.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define KVSHIM_API extern "C" __declspec(dllexport)

struct kvshim {
    llama_model   * model = nullptr;
    llama_context * ctx   = nullptr;
    const llama_vocab * vocab = nullptr;

    int n_seq = 0;
    int n_threads = 0;
    bool q8   = false;

    // The per-seq token list has to be kept: llama_state_seq_save_file() writes it
    // into the file next to the KV payload, and the loader hands it back.
    std::vector<std::vector<llama_token>> tokens;
};

static void quiet_log(ggml_log_level, const char * text, void *) {
    (void) text; // keep stderr clean; the demo prints its own numbers
}

static bool decode_tokens(kvshim * h, int seq, const std::vector<llama_token> & ids,
                          llama_pos pos0, bool want_logits) {
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
        const int rc = llama_decode(h->ctx, b);
        llama_batch_free(b);
        if (rc != 0) {
            return false;
        }
    }
    return true;
}

static std::vector<llama_token> tokenize(const llama_vocab * v, const char * text, bool add_special) {
    const int len = (int) strlen(text);
    if (len == 0) {
        return {};
    }
    std::vector<llama_token> out((size_t) len + 16);
    int n = llama_tokenize(v, text, len, out.data(), (int) out.size(), add_special, true);
    if (n < 0) {
        out.resize((size_t) -n);
        n = llama_tokenize(v, text, len, out.data(), (int) out.size(), add_special, true);
    }
    if (n < 0) {
        return {};
    }
    out.resize((size_t) n);
    return out;
}

static llama_pos next_pos(kvshim * h, int seq) {
    if (h->tokens[seq].empty()) {
        return 0;
    }
    const llama_pos pm = llama_memory_seq_pos_max(llama_get_memory(h->ctx), seq);
    return pm + 1;
}

static std::string generate(kvshim * h, int seq, llama_pos & pos, int n_predict) {
    std::string out;
    const int n_vocab = llama_vocab_n_tokens(h->vocab);
    for (int i = 0; i < n_predict; i++) {
        const float * logits = llama_get_logits_ith(h->ctx, -1);
        if (!logits) {
            break;
        }
        llama_token best = 0;
        float best_v = logits[0];
        for (int t = 1; t < n_vocab; t++) {
            if (logits[t] > best_v) {
                best_v = logits[t];
                best = t;
            }
        }
        if (llama_vocab_is_eog(h->vocab, best)) {
            break;
        }
        char buf[256];
        const int nb = llama_token_to_piece(h->vocab, best, buf, sizeof(buf), 0, false);
        if (nb > 0) {
            out.append(buf, nb);
        }
        std::vector<llama_token> one(1, best);
        if (!decode_tokens(h, seq, one, pos, true)) {
            break;
        }
        h->tokens[seq].push_back(best);
        pos++;
    }
    return out;
}

// ---------------------------------------------------------------- lifecycle

KVSHIM_API kvshim * kvshim_open(const char * model_path, int n_ctx, int n_seq,
                                int n_gpu_layers, int kv_q8) {
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = n_gpu_layers;

    kvshim * h = new kvshim();
    h->model = llama_model_load_from_file(model_path, mp);
    if (!h->model) {
        delete h;
        return nullptr;
    }
    h->vocab = llama_model_get_vocab(h->model);
    h->n_seq = n_seq;
    h->q8    = kv_q8 != 0;

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx      = (uint32_t) n_ctx;
    cp.n_batch    = 512;
    cp.n_ubatch   = 512;
    cp.n_seq_max  = (uint32_t) n_seq;
    cp.kv_unified = true;   // one shared pool; seq_cp is the sharing mechanism
    cp.type_k     = h->q8 ? GGML_TYPE_Q8_0 : GGML_TYPE_F16;
    cp.type_v     = h->q8 ? GGML_TYPE_Q8_0 : GGML_TYPE_F16;
    cp.flash_attn_type = h->q8 ? LLAMA_FLASH_ATTN_TYPE_ENABLED : LLAMA_FLASH_ATTN_TYPE_AUTO;
    // KVSHIM_THREADS: 1..12 overrides the historical 8; unset/invalid keeps 8.
    int n_threads = 8;
    if (const char * ts = getenv("KVSHIM_THREADS")) {
        char * end = nullptr;
        long v = strtol(ts, &end, 10);
        if (end != ts && *end == '\0' && v >= 1 && v <= 12) {
            n_threads = (int) v;
        }
    }
    cp.n_threads       = n_threads;
    cp.n_threads_batch = n_threads;

    h->n_threads = n_threads;
    h->ctx = llama_init_from_model(h->model, cp);
    if (!h->ctx) {
        llama_model_free(h->model);
        delete h;
        return nullptr;
    }
    h->tokens.resize((size_t) n_seq);
    return h;
}

KVSHIM_API int kvshim_threads(kvshim * h) {
    return h ? h->n_threads : 0;
}

KVSHIM_API void kvshim_close(kvshim * h) {
    if (!h) {
        return;
    }
    if (h->ctx)   { llama_free(h->ctx); }
    if (h->model) { llama_model_free(h->model); }
    delete h;
}

// ---------------------------------------------------------------- accounting

// Analytic KV footprint of one token, from the model shape. Qwen2-7B at q8_0:
// 28 layers * 2 (K and V) * 4 kv heads * 128 dim * 34/32 B = 30,464 B.
KVSHIM_API long long kvshim_bytes_per_token(kvshim * h) {
    const int n_layer  = llama_model_n_layer(h->model);
    const int n_head   = llama_model_n_head(h->model);
    const int n_embd   = llama_model_n_embd(h->model);
    const int n_head_kv= llama_model_n_head_kv(h->model);
    if (n_head <= 0) {
        return 0;
    }
    const int    head_dim = n_embd / n_head;
    const size_t elems    = (size_t) n_layer * 2 * (size_t) n_head_kv * (size_t) head_dim;
    return (long long) (h->q8 ? (elems * 34 + 31) / 32 : elems * 2);
}

KVSHIM_API long long kvshim_pool_bytes(kvshim * h) {
    return (long long) llama_n_ctx(h->ctx) * kvshim_bytes_per_token(h);
}

KVSHIM_API int kvshim_n_ctx(kvshim * h) {
    return (int) llama_n_ctx(h->ctx);
}

// Exact size of this sequence's KV payload (what a save file holds, minus header).
KVSHIM_API long long kvshim_seq_bytes(kvshim * h, int seq) {
    if (h->tokens[seq].empty()) {
        return 0;
    }
    return (long long) llama_state_seq_get_size(h->ctx, (llama_seq_id) seq);
}

KVSHIM_API int kvshim_n_tokens(kvshim * h, int seq)  { return (int) h->tokens[seq].size(); }
// Token identities, so a loaded block can be proven to hold exactly the text we
// declared: a matching cell count cannot tell that text apart from text + padding.
KVSHIM_API int kvshim_tokenize(kvshim * h, const char * text, int * out, int cap) {
    if (!h || !text || !out || cap <= 0) { return -1; }
    const std::vector<llama_token> ids = tokenize(h->vocab, text, false);
    const int n = (int) std::min<size_t>(ids.size(), (size_t) cap);
    for (int i = 0; i < n; ++i) { out[i] = (int) ids[i]; }
    return n;
}

KVSHIM_API int kvshim_seq_tokens(kvshim * h, int seq, int * out, int cap) {
    if (!h || !out || cap <= 0 || seq < 0 || seq >= h->n_seq) { return -1; }
    const auto & v = h->tokens[seq];
    const int n = (int) std::min<size_t>(v.size(), (size_t) cap);
    for (int i = 0; i < n; ++i) { out[i] = (int) v[i]; }
    return (int) v.size();
}
KVSHIM_API int kvshim_pos_max(kvshim * h, int seq) {
    if (h->tokens[seq].empty()) {
        return -1;
    }
    return (int) llama_memory_seq_pos_max(llama_get_memory(h->ctx), (llama_seq_id) seq);
}

// ------------------------------------------------- raw cell accessors (read-only)
//
// kvshim_pos_max returns -1 whenever tokens[seq] is empty, which is always true for a
// sequence assembled with seq_cp -- share adds cell references, not tokens. So the wrapper
// cannot be used to decide "is the block actually in the cache". These accessors talk to
// llama_memory directly and never look at tokens[].
//
// cell_scan copies the sequence into a scratch seq (the caller owns it, e.g. 7) and then
// peels it one position at a time with seq_rm, which returns whether it removed anything.
// rm on the scratch only clears the scratch's bit, so the source sequence is untouched.

KVSHIM_API int kvshim_seq_pos_max_raw(kvshim * h, int seq) {
    if (!h || !h->ctx || seq < 0 || seq >= h->n_seq) {
        return -1;
    }
    return (int) llama_memory_seq_pos_max(llama_get_memory(h->ctx), (llama_seq_id) seq);
}

KVSHIM_API int kvshim_seq_cell_scan(kvshim * h, int seq, int probe, int * out, int cap) {
    if (!h || !h->ctx || seq < 0 || seq >= h->n_seq || probe < 0 || probe >= h->n_seq) {
        return -1;
    }
    if (seq == probe) {
        return -1;
    }
    auto * mem = llama_get_memory(h->ctx);
    llama_memory_seq_rm(mem, (llama_seq_id) probe, 0, -1);
    llama_memory_seq_cp(mem, (llama_seq_id) seq, (llama_seq_id) probe, 0, -1);

    int n = 0;
    while (n < cap) {
        const llama_pos p = llama_memory_seq_pos_min(mem, (llama_seq_id) probe);
        if (p < 0) {
            break;
        }
        if (out) {
            out[n] = (int) p;
        }
        ++n;
        if (!llama_memory_seq_rm(mem, (llama_seq_id) probe, p, p + 1)) {
            break;                      // removing that position freed nothing: stop
        }
    }
    llama_memory_seq_rm(mem, (llama_seq_id) probe, 0, -1);
    return n;
}

// ---------------------------------------------------------------- decode

KVSHIM_API void kvshim_reset(kvshim * h, int seq) {
    llama_memory_seq_rm(llama_get_memory(h->ctx), (llama_seq_id) seq, 0, -1);
    h->tokens[seq].clear();
}

// Decode text at the sequence's current end. Returns tokens decoded, or -1.
KVSHIM_API int kvshim_write(kvshim * h, int seq, const char * text, int add_bos) {
    const std::vector<llama_token> ids = tokenize(h->vocab, text, add_bos != 0);
    if (ids.empty()) {
        return -1;
    }
    const llama_pos pos0 = next_pos(h, seq);
    if (!decode_tokens(h, seq, ids, pos0, false)) {
        return -1;
    }
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());
    return (int) ids.size();
}

// Decode text at an explicit position (opens a chat above the memory window).
KVSHIM_API int kvshim_write_at(kvshim * h, int seq, const char * text, int pos_start, int add_bos) {
    const std::vector<llama_token> ids = tokenize(h->vocab, text, add_bos != 0);
    if (ids.empty()) {
        return -1;
    }
    if (!decode_tokens(h, seq, ids, (llama_pos) pos_start, true)) {
        return -1;
    }
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());
    return (int) ids.size();
}

KVSHIM_API int kvshim_ask_at(kvshim * h, int seq, const char * text, int pos_start,
                             int n_predict, char * out, int cap);

KVSHIM_API int kvshim_ask(kvshim * h, int seq, const char * text, int n_predict,
                          char * out, int cap) {
    return kvshim_ask_at(h, seq, text, -1, n_predict, out, cap);
}

// pos_start < 0 means "continue at the end of this sequence".
KVSHIM_API int kvshim_ask_at(kvshim * h, int seq, const char * text, int pos_start,
                             int n_predict, char * out, int cap) {
    const std::vector<llama_token> ids = tokenize(h->vocab, text, false);
    if (ids.empty() || !out || cap <= 0) {
        return -1;
    }
    const llama_pos pos0 = (pos_start < 0) ? next_pos(h, seq) : (llama_pos) pos_start;
    if (!decode_tokens(h, seq, ids, pos0, true)) {
        return -1;
    }
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());

    llama_pos gen = pos0 + (llama_pos) ids.size();
    const std::string ans = generate(h, seq, gen, n_predict);
    const int n = (int) std::min<size_t>(ans.size(), (size_t) cap - 1);
    memcpy(out, ans.data(), (size_t) n);
    out[n] = '\0';
    return n;
}

// Same prompt path as kvshim_ask_at, plus the FIRST generated step top-k distribution.
// Purely additive: nothing above changes, and when this function is not called the shim
// behaves exactly as before. Probabilities are a full-vocabulary softmax, top-k picked by
// a stable insertion sort (ties keep the lower token id first).
static void topk_probs(const float * logits, int n_vocab, int k, int * out_tok, float * out_prob) {
    float mx = logits[0];
    for (int t = 1; t < n_vocab; t++) {
        if (logits[t] > mx) { mx = logits[t]; }
    }
    double z = 0.0;
    for (int t = 0; t < n_vocab; t++) {
        z += std::exp((double) (logits[t] - mx));
    }
    for (int i = 0; i < k; i++) { out_tok[i] = -1; out_prob[i] = 0.0f; }
    if (z <= 0.0) { return; }
    for (int t = 0; t < n_vocab; t++) {
        const float p = (float) (std::exp((double) (logits[t] - mx)) / z);
        if (p <= out_prob[k - 1]) { continue; }
        for (int i = 0; i < k; i++) {
            if (p > out_prob[i]) {
                for (int j = k - 1; j > i; j--) { out_prob[j] = out_prob[j - 1]; out_tok[j] = out_tok[j - 1]; }
                out_prob[i] = p;
                out_tok[i]  = t;
                break;
            }
        }
    }
}

KVSHIM_API int kvshim_ask_at_topk(kvshim * h, int seq, const char * text, int pos_start,
                                  int n_predict, int k, float * out_prob, int * out_tok,
                                  char * out, int cap) {
    if (!h || !out_prob || !out_tok || !out || cap <= 0) {
        return -1;
    }
    if (k < 1) { k = 1; }
    if (k > 64) { k = 64; }
    const std::vector<llama_token> ids = tokenize(h->vocab, text, false);
    if (ids.empty()) {
        return -1;
    }
    const llama_pos pos0 = (pos_start < 0) ? next_pos(h, seq) : (llama_pos) pos_start;
    if (!decode_tokens(h, seq, ids, pos0, true)) {
        return -1;
    }
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());
    const float * logits = llama_get_logits_ith(h->ctx, -1);
    if (!logits) {
        return -1;
    }
    topk_probs(logits, llama_vocab_n_tokens(h->vocab), k, out_tok, out_prob);
    llama_pos gen = pos0 + (llama_pos) ids.size();
    const std::string ans = generate(h, seq, gen, n_predict);
    const int n = (int) std::min<size_t>(ans.size(), (size_t) cap - 1);
    memcpy(out, ans.data(), (size_t) n);
    out[n] = '\0';
    return n;
}

// ---------------------------------------------------------------- scoring (additive)
//
// Teacher-forced scoring: decode the prompt at pos_start, then walk the answer tokens and
// read each one's logprob out of the CURRENT logits (log_softmax over the full vocabulary)
// BEFORE decoding it in. Nothing above changes behaviour: when these two exports are not
// called the shim behaves exactly as before.
//
// rank is 1-based and dense: 1 = argmax, and tokens whose value is not strictly greater do
// not push the rank up (ties share the better rank, same tie rule as topk_probs).
static void logsoftmax_at(const float * logits, int n_vocab, llama_token tok,
                          double * out_lp, int * out_rank) {
    double mx = (double) logits[0];
    for (int t = 1; t < n_vocab; t++) {
        if ((double) logits[t] > mx) { mx = (double) logits[t]; }
    }
    double z = 0.0;
    for (int t = 0; t < n_vocab; t++) {
        z += std::exp((double) logits[t] - mx);
    }
    const double ref = (double) logits[tok];
    const double lp  = ref - mx - std::log(z);
    int rank = 1;
    for (int t = 0; t < n_vocab; t++) {
        if ((double) logits[t] > ref) { rank++; }
    }
    *out_lp = lp;
    *out_rank = rank;
}

// Token id -> its text piece. Additive; returns bytes written, or -1 on bad input.
// A piece that does not fit in cap is refused rather than silently truncated.
KVSHIM_API int kvshim_piece(kvshim * h, int token, char * out, int cap) {
    if (!h || !h->vocab || !out || cap <= 0) {
        return -1;
    }
    if (token < 0 || token >= llama_vocab_n_tokens(h->vocab)) {
        return -1;
    }
    char buf[256];
    const int nb = llama_token_to_piece(h->vocab, token, buf, sizeof(buf), 0, false);
    if (nb < 0 || nb >= cap) {
        return -1;
    }
    memcpy(out, buf, (size_t) nb);
    out[nb] = 0;
    return nb;
}

// Score the answer tokens under the prompt, teacher-forced.
//
//   out_sum  : sum of the answer tokens' logprobs
//   out_mean : out_sum / out_n
//   out_last : the last scored token's logprob
//   out_n    : answer tokens actually scored (<= cap)
//   out_tok/out_lp/out_rank : per-token id / logprob / rank, first out_n entries written
//
// Every out pointer may be null (that output is then skipped); cap must be >= 1.
// An answer longer than cap is truncated to cap tokens and reported as ret -3, so a
// caller can never mistake a truncated mean for a full one.
// Returns 0 on success, -1 on bad arguments / overflow / engine failure, -3 on truncation.
KVSHIM_API int kvshim_score_at(kvshim * h, int seq, const char * prompt, const char * answer,
                              int pos_start, double * out_sum, double * out_mean,
                              double * out_last, int * out_tok, float * out_lp,
                              int * out_rank, int cap, int * out_n) {
    if (!h || !h->ctx || !h->vocab) {
        return -1;
    }
    if (seq < 0 || seq >= h->n_seq || cap <= 0) {
        return -1;
    }
    if (!prompt || !answer) {
        return -1;
    }
    if (out_n)    { *out_n = 0; }
    if (out_sum)  { *out_sum = 0.0; }
    if (out_mean) { *out_mean = 0.0; }
    if (out_last) { *out_last = 0.0; }

    const std::vector<llama_token> pids = tokenize(h->vocab, prompt, false);
    std::vector<llama_token> aids = tokenize(h->vocab, answer, false);
    if (pids.empty() || aids.empty()) {
        return -1;
    }

    const llama_pos pos0 = (pos_start < 0) ? next_pos(h, seq) : (llama_pos) pos_start;
    if (pos0 < 0) {
        return -1;
    }
    const bool truncated = (int) aids.size() > cap;
    if (truncated) {
        aids.resize((size_t) cap);
    }

    // The whole run (prompt + every answer token) has to fit inside the pool. n_ctx is the
    // per-sequence position ceiling, so this is the real bound, not a guess.
    const long long last_pos = (long long) pos0 + (long long) pids.size()
                             + (long long) aids.size() - 1;
    if (last_pos >= (long long) llama_n_ctx(h->ctx)) {
        return -1;
    }

    if (!decode_tokens(h, seq, pids, pos0, true)) {
        return -1;
    }
    h->tokens[seq].insert(h->tokens[seq].end(), pids.begin(), pids.end());

    const int n_vocab = llama_vocab_n_tokens(h->vocab);
    llama_pos pos = pos0 + (llama_pos) pids.size();
    double sum = 0.0;
    double last = 0.0;
    int n = 0;
    for (int i = 0; i < (int) aids.size(); i++) {
        const float * logits = llama_get_logits_ith(h->ctx, -1);
        if (!logits) {
            return -1;
        }
        double lp = 0.0;
        int rank = 0;
        logsoftmax_at(logits, n_vocab, aids[i], &lp, &rank);
        if (out_tok)  { out_tok[n]  = (int) aids[i]; }
        if (out_lp)   { out_lp[n]   = (float) lp; }
        if (out_rank) { out_rank[n] = rank; }
        sum += lp;
        last = lp;
        n++;

        // Teacher forcing: feed the answer token in unchanged, whatever the model would
        // have picked. One token per batch, so the next step's row is this token's.
        const std::vector<llama_token> one(1, aids[i]);
        if (!decode_tokens(h, seq, one, pos, true)) {
            return -1;
        }
        h->tokens[seq].push_back(aids[i]);
        pos++;
    }

    if (out_n)    { *out_n = n; }
    if (out_sum)  { *out_sum = sum; }
    if (out_mean) { *out_mean = (n > 0) ? sum / (double) n : 0.0; }
    if (out_last) { *out_last = last; }
    return truncated ? -3 : 0;
}

// ---------------------------------------------------------------- state <-> file

// Returns bytes written (>0), or 0 on failure. The file holds KV + this seq's tokens.
KVSHIM_API long long kvshim_save(kvshim * h, int seq, const char * path) {
    if (h->tokens[seq].empty()) {
        return 0;
    }
    const size_t n = llama_state_seq_save_file(h->ctx, path, (llama_seq_id) seq,
                                               h->tokens[seq].data(), h->tokens[seq].size());
    return (long long) n;
}

// Two-phase load, same order the server uses: first ask for the token count,
// then load with a buffer of that size. Returns token count, or -1.
KVSHIM_API int kvshim_load(kvshim * h, int seq, const char * path) {
    kvshim_reset(h, seq);

    size_t n_packed = 0;
    size_t nread = llama_state_seq_load_file(h->ctx, path, (llama_seq_id) seq,
                                             nullptr, 0, &n_packed);
    if (nread == 0) {
        return -1;
    }
    std::vector<llama_token> toks(std::max<size_t>(1, n_packed));
    nread = llama_state_seq_load_file(h->ctx, path, (llama_seq_id) seq,
                                      toks.data(), toks.size(), &n_packed);
    if (nread == 0) {
        return -1;
    }
    h->tokens[seq].assign(toks.begin(), toks.begin() + (long) n_packed);
    return (int) n_packed;
}

// ---------------------------------------------------------------- sharing

// Zero-copy visibility: dst starts referencing src's cells in [p0, p1).
// Refcount bump only -- no K/V is copied and nothing is re-decoded.
KVSHIM_API void kvshim_seq_cp(kvshim * h, int src, int dst, int p0, int p1) {
    llama_memory_seq_cp(llama_get_memory(h->ctx), (llama_seq_id) src, (llama_seq_id) dst, p0, p1);
}

KVSHIM_API void kvshim_seq_rm(kvshim * h, int seq, int p0, int p1) {
    llama_memory_seq_rm(llama_get_memory(h->ctx), (llama_seq_id) seq, p0, p1);
}

// Reposition: add `delta` to every position in [p0,p1) of this sequence.
//
// This is NOT a bookkeeping trick. llama_kv_cache::seq_add records the delta per
// cell (cells.pos_add -> has_shift), and the next decode runs build_graph_shift,
// which applies RoPE with that per-cell shift -- so the cached K is re-rotated to
// the new position. Quantized caches go dequant -> rope -> requant inside
// build_rope_shift, i.e. the WHOLE K tensor is rewritten, not just the moved cells.
//
// Requires hparams.n_pos_per_embd() == 1 (true for Qwen2 and other plain RoPE
// models; M-RoPE models assert).
KVSHIM_API void kvshim_repos(kvshim * h, int seq, int p0, int p1, int delta) {
    llama_memory_seq_add(llama_get_memory(h->ctx), (llama_seq_id) seq, p0, p1, delta);
}

// Whether this cache supports shifting at all (rope-based caches do).
KVSHIM_API int kvshim_can_shift(kvshim * h) {
    return llama_memory_can_shift(llama_get_memory(h->ctx)) ? 1 : 0;
}

// Local reposition: rotate ONLY the cells that move, no whole-tensor rewrite.
// Returns the number of cells touched (0 = unsupported). Unlike kvshim_repos,
// this completes immediately -- no pending K-shift, nothing else is touched.
KVSHIM_API int kvshim_repos_local(kvshim * h, int seq, int p0, int p1, int delta) {
    return (int) llama_memory_seq_repos_local(
            llama_get_memory(h->ctx), (llama_seq_id) seq, p0, p1, delta);
}

KVSHIM_API void kvshim_init_log(void) {
    llama_log_set(quiet_log, nullptr);
    llama_backend_init();
}

KVSHIM_API void kvshim_free_log(void) {
    llama_backend_free();
}