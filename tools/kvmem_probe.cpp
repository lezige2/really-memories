// kvmem_probe.cpp -- 引擎层「记忆住在 KV 里」最小验证探针
//
// 目的：
//   证明一段内容的 K/V 张量可以脱离 prompt 独立存在，并且后续对话能看见它。
//   这是 M1 的验收标准的直接检验（问题内容不在 prompt 里，只在 KV 块里）。
//
// 机制（全部使用 upstream 公开 API，不改引擎）：
//   1. 记忆文本以 seq 0 解码，占据位置 0..M-1
//   2. llama_memory_seq_cp(mem, 0, 1, 0, -1) 把 cell 归属复制给 seq 1（只加引用，不拷贝数据）
//   3. 问题文本以 seq 1 解码，位置从 M 开始
//   4. 因果掩码 (p0 <= p1) 让问题token自动看见 0..M-1 的记忆位置 —— prompt 里没有任何记忆文本
//
// 对照组：全新上下文里只喂问题，应当答不出来。
//
// 用法：
//   kvmem_probe.exe -m <model.gguf> [--gpu N] [--ctx 8192] [--n 24]

#include "llama.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static const char * MEMORY =
    "以下是用户陈默的档案资料。\n"
    "姓名：陈默\n"
    "生日：1993年4月17日\n"
    "住址：杭州市西湖区文三路88号3幢502室\n"
    "车牌尾号：7302\n"
    "宠物：一只叫豆豆的橘猫\n"
    "最喜欢的城市：里斯本\n";

static const char * QUESTION = "用户陈默的车牌尾号是多少？只回答四位数字：";
static const char * ANSWER   = "7302";

static const llama_vocab * g_vocab = nullptr;

static std::vector<llama_token> tokenize(const char * text, bool add_special) {
    std::vector<llama_token> out(8192);
    int n = llama_tokenize(g_vocab, text, (int32_t) strlen(text), out.data(), (int32_t) out.size(), add_special, true);
    if (n < 0) {
        out.resize(-n);
        n = llama_tokenize(g_vocab, text, (int32_t) strlen(text), out.data(), (int32_t) out.size(), add_special, true);
    }
    out.resize(n > 0 ? n : 0);
    return out;
}

// 把一串 token 以指定 seq / 起始位置喂进上下文
static bool decode_tokens(llama_context * ctx, const std::vector<llama_token> & ids,
                          llama_pos pos0, llama_seq_id seq, bool want_logits) {
    const int n = (int) ids.size();
    llama_batch b = llama_batch_init(n, 0, 1);
    for (int i = 0; i < n; i++) {
        b.token[i]      = ids[i];
        b.pos[i]        = pos0 + i;
        b.n_seq_id[i]   = 1;
        b.seq_id[i][0]  = seq;
        b.logits[i]     = (want_logits && i == n - 1) ? 1 : 0;
    }
    b.n_tokens = n;
    const int rc = llama_decode(ctx, b);
    llama_batch_free(b);
    return rc == 0;
}

// 贪心续写 n 个 token，返回文本
static std::string generate(llama_context * ctx, llama_sampler * smpl, llama_seq_id seq,
                           llama_pos & pos, int n_predict) {
    std::string out;
    for (int i = 0; i < n_predict; i++) {
        llama_token id = llama_sampler_sample(smpl, ctx, -1);
        if (llama_vocab_is_eog(g_vocab, id)) {
            break;
        }
        char buf[256];
        int n = llama_token_to_piece(g_vocab, id, buf, sizeof(buf), 0, false);
        if (n > 0) {
            out.append(buf, n);
        }
        std::vector<llama_token> one(1, id);
        if (!decode_tokens(ctx, one, pos, seq, true)) {
            out += "\n[decode error]";
            break;
        }
        pos++;
    }
    return out;
}

static bool contains(const std::string & hay, const char * needle) {
    return hay.find(needle) != std::string::npos;
}

int main(int argc, char ** argv) {
    const char * model_path = nullptr;
    int  n_gpu_layers = 0;
    int  n_ctx        = 8192;
    int  n_predict    = 24;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-m") && i + 1 < argc)      { model_path   = argv[++i]; }
        else if (!strcmp(argv[i], "--gpu") && i + 1 < argc) { n_gpu_layers = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--ctx") && i + 1 < argc) { n_ctx        = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--n")   && i + 1 < argc) { n_predict    = atoi(argv[++i]); }
    }
    if (!model_path) {
        fprintf(stderr, "usage: %s -m model.gguf [--gpu N] [--ctx N] [--n N]\n", argv[0]);
        return 2;
    }

    llama_backend_init();

    llama_model_params mparams = llama_model_default_params();
    mparams.n_gpu_layers = n_gpu_layers;

    llama_model * model = llama_model_load_from_file(model_path, mparams);
    if (!model) {
        fprintf(stderr, "failed to load model: %s\n", model_path);
        return 1;
    }
    g_vocab = llama_model_get_vocab(model);

    llama_context_params cparams = llama_context_default_params();
    cparams.n_ctx     = (uint32_t) n_ctx;
    cparams.n_batch   = 512;
    cparams.n_ubatch  = 512;
    cparams.n_seq_max = 8;   // 需要至少 2 个 sequence：0=记忆，1=会话

    llama_context * ctx = llama_init_from_model(model, cparams);
    if (!ctx) {
        fprintf(stderr, "failed to create context\n");
        return 1;
    }
    llama_memory_t mem = llama_get_memory(ctx);

    llama_sampler_chain_params sparams = llama_sampler_chain_default_params();
    llama_sampler * smpl = llama_sampler_chain_init(sparams);
    llama_sampler_chain_add(smpl, llama_sampler_init_greedy());

    printf("=========================================================\n");
    printf("KV 记忆探针   n_ctx=%d  n_gpu_layers=%d  n_predict=%d\n", n_ctx, n_gpu_layers, n_predict);
    printf("=========================================================\n");

    const std::vector<llama_token> q_ids = tokenize(QUESTION, true);
    const std::vector<llama_token> m_ids = tokenize(MEMORY, false);  // 记忆不带 BOS
    printf("记忆 token 数 = %zu   问题 token 数 = %zu\n", m_ids.size(), q_ids.size());

    // ---------------- 1. 对照组：上下文里没有记忆 ----------------
    printf("\n[1] 对照组：全新上下文，prompt 只有问题\n");
    const llama_seq_id SEQ_CTRL = 7;
    llama_memory_seq_rm(mem, SEQ_CTRL, -1, -1);
    decode_tokens(ctx, q_ids, 0, SEQ_CTRL, true);
    llama_pos ctrl_pos = (llama_pos) q_ids.size();
    const std::string a1 = generate(ctx, smpl, SEQ_CTRL, ctrl_pos, n_predict);
    printf("    回答: %s\n", a1.c_str());
    const bool ok1 = contains(a1, ANSWER);
    printf("    命中 %s ? %s\n", ANSWER, ok1 ? "是（实验无效）" : "否（符合预期）");
    llama_memory_seq_rm(mem, SEQ_CTRL, -1, -1);

    // ---------------- 2. 写入记忆（seq 0, 位置 0..M-1） ----------------
    printf("\n[2] 写入记忆：seq 0，位置 0..%zu\n", m_ids.size() - 1);
    if (!decode_tokens(ctx, m_ids, 0, 0, false)) {
        fprintf(stderr, "    记忆解码失败\n");
        return 1;
    }
    printf("    seq0 pos_max = %d\n", (int) llama_memory_seq_pos_max(mem, 0));

    // ---------------- 3. 把记忆的可见性复制给会话 sequence ----------------
    printf("\n[3] seq_cp: seq 0 -> seq 1（只加引用，不拷贝 K/V 数据）\n");
    llama_memory_seq_cp(mem, 0, 1, 0, -1);
    const llama_pos p1max = llama_memory_seq_pos_max(mem, 1);
    printf("    seq1 pos_max = %d  （应等于记忆长度-1）\n", (int) p1max);

    // ---------------- 4. 实验组：只喂问题，位置接在记忆之后 ----------------
    printf("\n[4] 实验组：prompt 里【只有问题】，位置从 %d 开始\n", (int) m_ids.size());
    if (!decode_tokens(ctx, q_ids, (llama_pos) m_ids.size(), 1, true)) {
        fprintf(stderr, "    问题解码失败\n");
        return 1;
    }
    llama_pos exp_pos = (llama_pos) (m_ids.size() + q_ids.size());
    const std::string a2 = generate(ctx, smpl, 1, exp_pos, n_predict);
    printf("    回答: %s\n", a2.c_str());
    const bool ok2 = contains(a2, ANSWER);

    // ---------------- 结论 ----------------
    printf("\n=========================================================\n");
    printf("对照组答出 %s : %s\n", ANSWER, ok1 ? "是（实验无效）" : "否");
    printf("实验组答出 %s : %s\n", ANSWER, ok2 ? "是" : "否");
    int rc = 1;
    if (ok2 && !ok1) {
        printf("=> 通过：答案只可能来自 KV 记忆，prompt 中无此信息。\n");
        rc = 0;
    } else if (ok1) {
        printf("=> 无效：对照组也答对，问题本身泄露了答案。\n");
        rc = 2;
    } else {
        printf("=> 未通过：记忆未生效。\n");
    }
    printf("=========================================================\n");

    llama_sampler_free(smpl);
    llama_free(ctx);
    llama_model_free(model);
    llama_backend_free();
    return rc;
}