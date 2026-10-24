// kvmem_persist.cpp -- 跨进程 KV 记忆持久化（HANDOFF §5 第 1 步）
//
// 目的：
//   证明一段记忆的 K/V 张量可以写盘、进程退出、由**另一个进程**载回并继续被 attention 读到。
//   这是对 §5 第 1 步验收标准的直接检验：
//     进程 A 写入记忆 -> 进程 A 退出 -> 进程 B 启动 -> 只问问题 -> 答对。
//
// 与 kvmem_probe.cpp 的关系：
//   probe 证明「记忆在 KV 里」；本工具证明「这份 KV 能跨进程活下来」。
//   probe 的 [2]->[4] 之间插入一次「写盘 / 清空 / 读回」，就是这里的 write/query 两段式。
//
// 用法（三个子命令，各自独立进程）：
//   kvmem_persist.exe write   -m model.gguf -f mem.kvmem [--gpu N] [--ctx 8192]
//   kvmem_persist.exe query   -m model.gguf -f mem.kvmem [--gpu N] [--ctx 8192] [--n 24] [--no-cp]
//   kvmem_persist.exe control -m model.gguf                [--gpu N] [--ctx 8192] [--n 24]
//
// 退出码：
//   0 = 该子命令的预期成立
//   1 = 预期不成立（或出错）
//   2 = 参数错误
//
// 注意：n_seq_max 保持 8（与 probe 一致）。KV 状态文件里的 n_stream 必须与载入时的
// n_seq_max 一致（n_stream = unified ? 1 : n_seq_max），否则 state_read 会抛 "n_stream mismatch"。

#include "llama.h"

#include <algorithm>
#include <cstdint>
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

// 填充文本：只用来把上下文塞满，触发 context-shift。刻意不含任何与答案相关的信息。
static const char * FILLER =
    "今天早上天气多云，气温大约十八度，适合出门散步。"
    "路上遇到邻居张阿姨，她说小区的桂花开了，味道很好闻。"
    "早餐吃了一碗豆浆和两根油条，一共花了六块钱。"
    "地铁上人不多，找到了座位，看了二十分钟的书。"
    "中午和同事在食堂吃饭，聊了最近上映的一部电影。"
    "下午开了两个会，主要是讨论下个季度的排期安排。"
    "下班后去超市买了鸡蛋、青菜和一袋米，回家做了简单的晚饭。"
    "晚上把阳台的花浇了一遍，又整理了一下书架。"
    "睡前听了一会儿音乐，十一点半关灯休息。";

// 记忆序列与对话序列的编号。记忆常驻 seq 0，对话跑在 seq 1（通过 seq_cp 共享记忆 cell）。
static const llama_seq_id SEQ_MEM  = 0;
static const llama_seq_id SEQ_CHAT = 1;

static const char     MAGIC[8]    = { 'K', 'V', 'M', 'E', 'M', '0', '1', '\0' };
static const uint32_t FILE_VERSION = 1;

struct file_header {
    char     magic[8];
    uint32_t version;
    int32_t  seq_id;
    int32_t  n_pos_max;   // 记忆最后位置（M-1），用于交叉校验
    int32_t  n_tokens;    // 记忆 token 数（仅信息）
    int32_t  type_k;      // ggml_type，用于提前给出可读的错误
    int32_t  type_v;
    uint32_t reserved;
    uint64_t blob_size;   // 紧随其后的 KV blob 字节数
};

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

static bool decode_tokens(llama_context * ctx, const std::vector<llama_token> & ids,
                          llama_pos pos0, llama_seq_id seq, bool want_logits) {
    const int n = (int) ids.size();
    llama_batch b = llama_batch_init(n, 0, 1);
    for (int i = 0; i < n; i++) {
        b.token[i]     = ids[i];
        b.pos[i]       = pos0 + i;
        b.n_seq_id[i]  = 1;
        b.seq_id[i][0] = seq;
        b.logits[i]    = (want_logits && i == n - 1) ? 1 : 0;
    }
    b.n_tokens = n;
    const int rc = llama_decode(ctx, b);
    llama_batch_free(b);
    return rc == 0;
}

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

static bool read_file(const char * path, file_header & hdr, std::vector<uint8_t> & blob) {
    FILE * f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "cannot open %s for reading\n", path);
        return false;
    }
    if (fread(&hdr, sizeof(hdr), 1, f) != 1) {
        fprintf(stderr, "short read: header\n");
        fclose(f);
        return false;
    }
    if (memcmp(hdr.magic, MAGIC, 8) != 0) {
        fprintf(stderr, "bad magic in %s\n", path);
        fclose(f);
        return false;
    }
    if (hdr.version != FILE_VERSION) {
        fprintf(stderr, "unsupported version %u (expected %u)\n", hdr.version, FILE_VERSION);
        fclose(f);
        return false;
    }
    blob.resize((size_t) hdr.blob_size);
    if (hdr.blob_size != 0 && fread(blob.data(), 1, (size_t) hdr.blob_size, f) != hdr.blob_size) {
        fprintf(stderr, "short read: blob (expected %llu bytes)\n", (unsigned long long) hdr.blob_size);
        fclose(f);
        return false;
    }
    fclose(f);
    return true;
}

static bool write_file(const char * path, const file_header & hdr, const std::vector<uint8_t> & blob) {
    FILE * f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "cannot open %s for writing\n", path);
        return false;
    }
    bool ok = fwrite(&hdr, sizeof(hdr), 1, f) == 1;
    ok = ok && (blob.empty() || fwrite(blob.data(), 1, blob.size(), f) == blob.size());
    fflush(f);
    fclose(f);
    return ok;
}

struct opts {
    std::string mode;
    const char * model_path = nullptr;
    const char * file_path  = nullptr;
    int n_gpu_layers = 0;
    int n_ctx        = 8192;
    int n_predict    = 24;
    bool do_cp       = true;
    ggml_type kv_type = GGML_TYPE_F16;   // --kv q8_0 走生产配置（每 token 28 KiB）
    int n_fill       = 900;              // shift 实验：填充多少 token
    int n_keep       = 0;                // 同 server 的 n_keep，0 = 从头开始丢
    int n_discard    = 300;              // 一次 shift 丢掉多少
    bool unified     = false;            // --unified: 所有 seq 共享一个 KV 池
};

static const char * type_name(ggml_type t) {
    return (t == GGML_TYPE_Q8_0) ? "q8_0" : (t == GGML_TYPE_F16 ? "f16" : ggml_type_name(t));
}

static bool parse_args(int argc, char ** argv, opts & o) {
    if (argc < 2) {
        return false;
    }
    o.mode = argv[1];
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "-m") && i + 1 < argc)           { o.model_path = argv[++i]; }
        else if (!strcmp(argv[i], "-f") && i + 1 < argc)      { o.file_path  = argv[++i]; }
        else if (!strcmp(argv[i], "--gpu") && i + 1 < argc)   { o.n_gpu_layers = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--ctx") && i + 1 < argc)   { o.n_ctx        = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--n") && i + 1 < argc)     { o.n_predict    = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--kv") && i + 1 < argc) {
            const char * kv = argv[++i];
            if (!strcmp(kv, "f16")) {
                o.kv_type = GGML_TYPE_F16;
            } else if (!strcmp(kv, "q8_0")) {
                o.kv_type = GGML_TYPE_Q8_0;
            } else {
                fprintf(stderr, "unknown --kv type: %s (use f16 or q8_0)\n", kv);
                return false;
            }
        }
        else if (!strcmp(argv[i], "--fill") && i + 1 < argc)  { o.n_fill    = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--n-keep") && i + 1 < argc) { o.n_keep  = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--n-discard") && i + 1 < argc) { o.n_discard = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--no-cp"))                 { o.do_cp = false; }
        else if (!strcmp(argv[i], "--unified"))               { o.unified = true; }
        else {
            fprintf(stderr, "unknown argument: %s\n", argv[i]);
            return false;
        }
    }
    return o.model_path != nullptr;
}

// 每个子命令都是完整的「载模型 -> 建上下文 -> 做事 -> 退出」，进程之间不共享任何状态。
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
        cparams.n_ctx     = (uint32_t) o.n_ctx;
        cparams.n_batch   = 512;
        cparams.n_ubatch  = 512;
        cparams.n_seq_max = 8;   // 记忆 seq 0 / 对话 seq 1；必须 >= 2
        cparams.kv_unified = o.unified;
        cparams.type_k    = o.kv_type;
        cparams.type_v    = o.kv_type;
        // 量化 V cache 需要 flash attention
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

        printf("[ctx] n_ctx=%u  n_ctx_seq=%u  n_seq_max=8  unified=%d\n",
               llama_n_ctx(ctx), llama_n_ctx_seq(ctx), (int) o.unified);
        return true;
    }

    ~session() {
        if (smpl)  { llama_sampler_free(smpl); }
        if (ctx)   { llama_free(ctx); }
        if (model) { llama_model_free(model); }
    }
};

// ---------------------------------------------------------------- write

static int cmd_write(const opts & o) {
    if (!o.file_path) {
        fprintf(stderr, "write: -f <file> is required\n");
        return 2;
    }

    session s;
    if (!s.init(o)) {
        return 1;
    }

    const std::vector<llama_token> m_ids = tokenize(MEMORY, false);

    printf("[write] model      = %s\n", o.model_path);
    printf("[write] kv type    = %s\n", type_name(o.kv_type));
    printf("[write] memory     = %zu tokens, seq %d, pos 0..%zu\n",
           m_ids.size(), (int) SEQ_MEM, m_ids.size() - 1);

    if (!decode_tokens(s.ctx, m_ids, 0, SEQ_MEM, false)) {
        fprintf(stderr, "[write] memory decode failed\n");
        return 1;
    }

    llama_memory_t mem = llama_get_memory(s.ctx);
    const llama_pos pos_max = llama_memory_seq_pos_max(mem, SEQ_MEM);
    printf("[write] seq%d pos_max = %d\n", (int) SEQ_MEM, (int) pos_max);
    if (pos_max != (llama_pos) m_ids.size() - 1) {
        fprintf(stderr, "[write] unexpected pos_max\n");
        return 1;
    }

    const size_t n_bytes = llama_state_seq_get_size(s.ctx, SEQ_MEM);
    if (n_bytes == 0) {
        fprintf(stderr, "[write] llama_state_seq_get_size returned 0\n");
        return 1;
    }

    std::vector<uint8_t> blob(n_bytes);
    const size_t n_written = llama_state_seq_get_data(s.ctx, blob.data(), blob.size(), SEQ_MEM);
    if (n_written != n_bytes) {
        fprintf(stderr, "[write] get_data wrote %zu bytes, expected %zu\n", n_written, n_bytes);
        return 1;
    }

    file_header hdr;
    memset(&hdr, 0, sizeof(hdr));
    memcpy(hdr.magic, MAGIC, 8);
    hdr.version   = FILE_VERSION;
    hdr.seq_id    = (int32_t) SEQ_MEM;
    hdr.n_pos_max = (int32_t) pos_max;
    hdr.n_tokens  = (int32_t) m_ids.size();
    hdr.type_k    = (int32_t) o.kv_type;
    hdr.type_v    = (int32_t) o.kv_type;
    hdr.blob_size = (uint64_t) blob.size();

    if (!write_file(o.file_path, hdr, blob)) {
        return 1;
    }

    printf("[write] bytes/token= %.0f\n", (double) blob.size() / (double) m_ids.size());
    printf("[write] KV blob    = %.2f MiB -> %s\n", (double) blob.size() / (1024.0 * 1024.0), o.file_path);
    printf("[write] done, process exits now\n");
    return 0;
}

// ---------------------------------------------------------------- query / control

static int cmd_query(const opts & o) {
    if (!o.file_path) {
        fprintf(stderr, "query: -f <file> is required\n");
        return 2;
    }

    file_header hdr;
    std::vector<uint8_t> blob;
    if (!read_file(o.file_path, hdr, blob)) {
        return 1;
    }

    session s;
    if (!s.init(o)) {
        return 1;
    }
    llama_memory_t mem = llama_get_memory(s.ctx);

    printf("[query] kv file    = %s (seq %d, pos_max %d, %.2f MiB, %s)\n",
           o.file_path, (int) hdr.seq_id, (int) hdr.n_pos_max,
           (double) blob.size() / (1024.0 * 1024.0), type_name((ggml_type) hdr.type_k));
    printf("[query] prompt     = %s\n", QUESTION);

    if ((ggml_type) hdr.type_k != o.kv_type) {
        fprintf(stderr, "[query] KV type mismatch: file is %s, context is %s (pass --kv %s)\n",
                type_name((ggml_type) hdr.type_k), type_name(o.kv_type), type_name((ggml_type) hdr.type_k));
        return 1;
    }

    const size_t n_set = llama_state_seq_set_data(s.ctx, blob.data(), blob.size(), SEQ_MEM);
    if (n_set == 0) {
        fprintf(stderr, "[query] llama_state_seq_set_data failed\n");
        return 1;
    }

    const llama_pos pos_max = llama_memory_seq_pos_max(mem, SEQ_MEM);
    printf("[query] restored seq%d pos_max = %d  (expected %d)\n",
           (int) SEQ_MEM, (int) pos_max, (int) hdr.n_pos_max);
    if (pos_max != (llama_pos) hdr.n_pos_max) {
        fprintf(stderr, "[query] restored positions do not match the file\n");
        return 1;
    }

    llama_seq_id chat_seq = SEQ_MEM;
    if (o.do_cp) {
        llama_memory_seq_cp(mem, SEQ_MEM, SEQ_CHAT, 0, -1);
        chat_seq = SEQ_CHAT;
        printf("[query] seq_cp %d -> %d, chat pos_max = %d\n",
               (int) SEQ_MEM, (int) SEQ_CHAT, (int) llama_memory_seq_pos_max(mem, SEQ_CHAT));
    }

    const std::vector<llama_token> q_ids = tokenize(QUESTION, true);
    const llama_pos start = pos_max + 1;
    if (!decode_tokens(s.ctx, q_ids, start, chat_seq, true)) {
        fprintf(stderr, "[query] question decode failed\n");
        return 1;
    }

    llama_pos gen_pos = start + (llama_pos) q_ids.size();
    const std::string answer = generate(s.ctx, s.smpl, chat_seq, gen_pos, o.n_predict);
    printf("[query] answer     = %s\n", answer.c_str());

    const bool ok = contains(answer, ANSWER);
    printf("[query] contains %s : %s\n", ANSWER, ok ? "YES" : "NO");
    printf(ok ? "=> PASS: KV restored from disk in a fresh process is still readable by attention.\n"
             : "=> FAIL: memory did not survive the process boundary.\n");
    return ok ? 0 : 1;
}

// ---------------------------------------------------------------- shift (第 2 步现状实验)

static int cmd_shift(const opts & o) {
    if (!o.file_path) {
        fprintf(stderr, "shift: -f <file> is required\n");
        return 2;
    }

    file_header hdr;
    std::vector<uint8_t> blob;
    if (!read_file(o.file_path, hdr, blob)) {
        return 1;
    }

    session s;
    if (!s.init(o)) {
        return 1;
    }
    llama_memory_t mem = llama_get_memory(s.ctx);

    if (llama_state_seq_set_data(s.ctx, blob.data(), blob.size(), SEQ_MEM) == 0) {
        fprintf(stderr, "[shift] restore failed\n");
        return 1;
    }
    const llama_pos mem_len = llama_memory_seq_pos_max(mem, SEQ_MEM) + 1;
    llama_memory_seq_cp(mem, SEQ_MEM, SEQ_CHAT, 0, -1);

    // 1) 用闲聊把对话区填满（不含任何与答案有关的信息）
    std::vector<llama_token> filler;
    while ((int) filler.size() < o.n_fill) {
        const std::vector<llama_token> part = tokenize(FILLER, false);
        if (part.empty()) {
            break;
        }
        filler.insert(filler.end(), part.begin(), part.end());
    }
    filler.resize(std::min((size_t) o.n_fill, filler.size()));

    llama_pos pos = mem_len;
    const size_t chunk = 256;
    for (size_t i = 0; i < filler.size(); i += chunk) {
        const size_t n = std::min(chunk, filler.size() - i);
        const std::vector<llama_token> part(filler.begin() + i, filler.begin() + i + n);
        if (!decode_tokens(s.ctx, part, pos, SEQ_CHAT, false)) {
            fprintf(stderr, "[shift] filler decode failed at %zu\n", i);
            return 1;
        }
        pos += (llama_pos) n;
    }

    printf("[shift] n_ctx=%d  memory=%d tokens (pos 0..%d)  filler=%zu tokens\n",
           o.n_ctx, (int) mem_len, (int) mem_len - 1, filler.size());
    printf("[shift] before: chat pos_min=%d pos_max=%d  |  mem seq%d pos_min=%d pos_max=%d\n",
           (int) llama_memory_seq_pos_min(mem, SEQ_CHAT), (int) llama_memory_seq_pos_max(mem, SEQ_CHAT),
           (int) SEQ_MEM,
           (int) llama_memory_seq_pos_min(mem, SEQ_MEM), (int) llama_memory_seq_pos_max(mem, SEQ_MEM));

    // 2) 完全照 server-context.cpp:3698-3699 的做法做一次 context shift
    const llama_pos pos_next = llama_memory_seq_pos_max(mem, SEQ_CHAT) + 1;

    int n_keep = o.n_keep;
    if (n_keep < 0)                 { n_keep = 0; }
    if (n_keep > (int) pos_next)    { n_keep = (int) pos_next; }

    const int n_left = (int) pos_next - n_keep;
    int n_discard = o.n_discard;
    if (n_discard < 0)              { n_discard = 0; }
    if (n_discard > n_left - 1)     { n_discard = std::max(0, n_left - 1); }

    printf("[shift] seq_rm(%d, %d, %d) + seq_add(%d, %d, %d, %d)\n",
           (int) SEQ_CHAT, n_keep, n_keep + n_discard,
           (int) SEQ_CHAT, n_keep + n_discard, (int) pos_next, -n_discard);

    llama_memory_seq_rm (mem, SEQ_CHAT, n_keep, n_keep + n_discard);
    llama_memory_seq_add(mem, SEQ_CHAT, n_keep + n_discard, pos_next, -n_discard);

    const llama_pos chat_min = llama_memory_seq_pos_min(mem, SEQ_CHAT);
    const llama_pos chat_max = llama_memory_seq_pos_max(mem, SEQ_CHAT);
    printf("[shift] after:  chat pos_min=%d pos_max=%d  |  mem seq%d pos_min=%d pos_max=%d\n",
           (int) chat_min, (int) chat_max,
           (int) SEQ_MEM,
           (int) llama_memory_seq_pos_min(mem, SEQ_MEM), (int) llama_memory_seq_pos_max(mem, SEQ_MEM));

    // 记忆还挂在这个对话序列上吗？（记忆占据 0..mem_len-1）
    // 注意：pos_min==0 只是必要条件 —— shift 之后闲聊 cell 也会被搬到 0..，
    // 所以「pos_min==0」不能证明记忆还在，真正的判据是下面的问答结果。
    const bool chat_starts_at_zero = (chat_min == 0);
    printf("[shift] chat pos_min==0: %s (necessary, not sufficient)\n",
           chat_starts_at_zero ? "yes" : "no");

    const bool range_covers_mem = (n_keep < (int) mem_len);
    printf("[shift] seq_rm starts at %d, memory occupies 0..%d -> %s\n",
           n_keep, (int) mem_len - 1,
           range_covers_mem ? "MEMORY EXPOSED" : "memory protected");

    if (chat_max < 0) {
        fprintf(stderr, "[shift] chat sequence is empty after the shift\n");
        return 1;
    }

    // 3) 在 shift 之后的上下文里问同一个问题
    const std::vector<llama_token> q_ids = tokenize(QUESTION, true);
    const llama_pos start = chat_max + 1;
    if (!decode_tokens(s.ctx, q_ids, start, SEQ_CHAT, true)) {
        fprintf(stderr, "[shift] question decode failed\n");
        return 1;
    }
    llama_pos gen_pos = start + (llama_pos) q_ids.size();
    const std::string answer = generate(s.ctx, s.smpl, SEQ_CHAT, gen_pos, o.n_predict);
    printf("[shift] answer   = %s\n", answer.c_str());

    const bool ok = contains(answer, ANSWER);
    if (ok) {
        printf("=> PASS: memory survived the context shift (n_keep=%d).\n", n_keep);
    } else if (range_covers_mem) {
        printf("=> FAIL: the discard range starts at %d, inside the memory (0..%d), so the shift\n"
               "          removed the chat sequence's claim on the memory cells.\n",
               n_keep, (int) mem_len - 1);
    } else {
        printf("=> FAIL: cells are still attached but the memory no longer reads back.\n");
    }
    return ok ? 0 : 1;
}

static int cmd_control(const opts & o) {
    session s;
    if (!s.init(o)) {
        return 1;
    }

    printf("[control] fresh context, prompt = %s\n", QUESTION);

    const std::vector<llama_token> q_ids = tokenize(QUESTION, true);
    if (!decode_tokens(s.ctx, q_ids, 0, SEQ_MEM, true)) {
        fprintf(stderr, "[control] question decode failed\n");
        return 1;
    }
    llama_pos gen_pos = (llama_pos) q_ids.size();
    const std::string answer = generate(s.ctx, s.smpl, SEQ_MEM, gen_pos, o.n_predict);
    printf("[control] answer   = %s\n", answer.c_str());

    const bool leaked = contains(answer, ANSWER);
    printf("[control] contains %s : %s\n", ANSWER, leaked ? "YES" : "NO");
    printf(!leaked ? "=> PASS: without the KV file the model cannot answer (memory is the only source).\n"
                   : "=> FAIL: the question itself leaks the answer, the experiment is invalid.\n");
    return leaked ? 1 : 0;
}

int main(int argc, char ** argv) {
    opts o;
    if (!parse_args(argc, argv, o)) {
        fprintf(stderr,
            "usage:\n"
            "  %s write   -m model.gguf -f mem.kvmem [--gpu N] [--ctx N] [--kv f16|q8_0]\n"
            "  %s query   -m model.gguf -f mem.kvmem [--gpu N] [--ctx N] [--n N] [--kv f16|q8_0] [--no-cp]\n"
            "  %s control -m model.gguf              [--gpu N] [--ctx N] [--n N] [--kv f16|q8_0]\n"
            "  %s shift   -m model.gguf -f mem.kvmem [--fill N] [--n-keep N] [--n-discard N] [--ctx N] [--kv f16|q8_0]\n",
            argv[0], argv[0], argv[0], argv[0]);
        return 2;
    }

    llama_backend_init();
    int rc = 2;
    if (o.mode == "write") {
        rc = cmd_write(o);
    } else if (o.mode == "query") {
        rc = cmd_query(o);
    } else if (o.mode == "control") {
        rc = cmd_control(o);
    } else if (o.mode == "shift") {
        rc = cmd_shift(o);
    } else {
        fprintf(stderr, "unknown mode: %s\n", o.mode.c_str());
    }
    llama_backend_free();
    return rc;
}