// GBNF/logprob smoke export.  Reuses the frozen kvshim implementation by
// including it, then adds one additive export; the frozen kvshim_vk.dll is
// not modified.
#include "kvshim.cpp"

extern "C" __declspec(dllexport)
int kvshim_ask_grammar_probs(kvshim * h, int seq, const char * text, int pos_start,
                             const char * grammar_str, const char * grammar_root,
                             int n_predict, char * out, int cap, int n_probs,
                             int * out_tokens, float * out_probs, int * out_n_allowed) {
    if (!h || !text || !grammar_str || !grammar_root || !out || cap <= 0 ||
        !out_tokens || !out_probs || n_probs <= 0) {
        return -1;
    }
    const std::vector<llama_token> ids = tokenize(h->vocab, text, false);
    if (ids.empty()) {
        return -1;
    }
    const llama_pos pos0 = (pos_start < 0) ? next_pos(h, seq) : (llama_pos) pos_start;
    if (!decode_tokens(h, seq, ids, pos0, true)) {
        return -1;
    }
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());
    llama_pos pos = pos0 + (llama_pos) ids.size();

    llama_sampler * gs = llama_sampler_init_grammar(h->vocab, grammar_str, grammar_root);
    if (!gs) {
        return -2;
    }
    const int n_vocab = llama_vocab_n_tokens(h->vocab);
    std::vector<llama_token_data> cur((size_t) n_vocab);
    std::string ans;
    int allowed_count = 0;

    for (int step = 0; step < n_predict; step++) {
        const float * logits = llama_get_logits_ith(h->ctx, -1);
        if (!logits) {
            break;
        }
        for (int t = 0; t < n_vocab; t++) {
            cur[(size_t) t] = llama_token_data{(llama_token) t, logits[t], 0.0f};
        }
        llama_token_data_array arr = {cur.data(), cur.size(), -1, false};
        llama_sampler_apply(gs, &arr);

        // Probabilities over grammar-allowed tokens only.  This is the
        // post-grammar distribution (continuous A/B/C score), not a greedy
        // one-hot and not a full-vocabulary softmax.
        std::vector<std::pair<float, int>> allowed;
        allowed.reserve((size_t) n_vocab);
        float mx = -INFINITY;
        for (int t = 0; t < n_vocab; t++) {
            const float v = arr.data[t].logit;
            if (std::isfinite(v)) {
                allowed.push_back({v, t});
                if (v > mx) { mx = v; }
            }
        }
        if (allowed.empty()) {
            break;
        }
        double z = 0.0;
        for (const auto & a : allowed) {
            z += std::exp((double) (a.first - mx));
        }
        if (z <= 0.0) {
            break;
        }
        if (step == 0) {
            allowed_count = (int) allowed.size();
            std::vector<std::pair<float, int>> ranked;
            ranked.reserve(allowed.size());
            for (const auto & a : allowed) {
                ranked.push_back({(float) (std::exp((double) (a.first - mx)) / z), a.second});
            }
            std::sort(ranked.begin(), ranked.end(),
                      [](const std::pair<float, int> & a, const std::pair<float, int> & b) {
                          if (a.first != b.first) return a.first > b.first;
                          return a.second < b.second;
                      });
            for (int i = 0; i < n_probs; i++) {
                if (i < (int) ranked.size()) {
                    out_tokens[i] = ranked[(size_t) i].second;
                    out_probs[i] = ranked[(size_t) i].first;
                } else {
                    out_tokens[i] = -1;
                    out_probs[i] = 0.0f;
                }
            }
        }
        if (out_n_allowed) {
            *out_n_allowed = allowed_count;
        }

        // Greedy choice over the grammar-allowed set.
        llama_token best = (llama_token) allowed[0].second;
        float best_v = allowed[0].first;
        for (const auto & a : allowed) {
            if (a.first > best_v) {
                best_v = a.first;
                best = (llama_token) a.second;
            }
        }
        if (llama_vocab_is_eog(h->vocab, best)) {
            break;
        }
        char buf[256];
        const int nb = llama_token_to_piece(h->vocab, best, buf, sizeof(buf), 0, false);
        if (nb <= 0) {
            break;
        }
        ans.append(buf, nb);
        std::vector<llama_token> one(1, best);
        if (!decode_tokens(h, seq, one, pos, true)) {
            break;
        }
        h->tokens[seq].push_back(best);
        pos++;
        llama_sampler_accept(gs, best);
    }
    llama_sampler_free(gs);
    const int n = (int) std::min<size_t>(ans.size(), (size_t) cap - 1);
    memcpy(out, ans.data(), (size_t) n);
    out[n] = '\0';
    if (out_n_allowed) {
        *out_n_allowed = allowed_count;
    }
    return n;
}
