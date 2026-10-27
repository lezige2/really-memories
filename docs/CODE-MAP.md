# CODE-MAP（代码地图）

> **原则**：代码 + 冻结产物 > 文档；本图每条都给 `路径:行` 定位，供文档只按代码来写。
> 生成方式：只读源码/产物，未跑 GPU、未联网、未改任何既有文件。工作树 `D:\llama-mem`。
> 与 `docs/PROJECT-STATE.md` 的分工：状态读数看 PROJECT-STATE；**"代码长什么样"看本文件**。

## 1 入口层

### 1.1 Windows 启动器

| 文件 | 位置 | 事实 |
|---|---|---|
| `start_service.cmd` | :6 | 打印"36/34 层实测选型：n_ctx=16384, n_gpu_layers=34, chat_start=8192" |
| `start_service.cmd` | :7 | `python -X utf8 tools\chat_service.py --port 8765 --n-ctx 16384 --chat-start 8192 --n-gpu-layers 34 --retrieval topk --topk 4 --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --session daily.json`，日志 `kvmem\daily\service.log` |
| `start_chat.cmd` | :14 | `python -X utf8 tools\chat_daily.py %*`（交互 REPL；失败提示查模型/dll/GPU） |

### 1.2 `tools/chat_daily.py`（产品 C 版交互入口，89 KB）

- 设计声明 :2-21：记忆 = KV 块、**prompt 里不拼接记忆文本**；复用 kvslots/memory_source/session_state/chat_lease/retrieval/evidence；真实引擎只在 `make_real_engine()` 内 `import kvslots`。
- 与 `tools/chat.py` 的差异 :14-21：独立数据面 `kvmem/daily.db` + `kvmem/daily_blocks/`；记忆前缀 `mem-<sha12>` 按内容去重；同时挂载 ≤6 条；检索无命中 + 具体事实问句 ⇒ 固定拒答（不调模型）；会话默认 `kvmem/sessions/daily.json`。
- 常量：`N_CTX_DEFAULT=16384` :59；`CHAT_START_DEFAULT=8192` :60；`N_SEQ=8` :63；`MAX_MEMORIES=6` :64；`LIBRARY_MAX=200` :67；`N_GPU_LAYERS_DEFAULT=34` :68；`DEFAULT_TOPK=4` :70；`ROLLOVER_AT_DEFAULT=0.75` :71；`N_PREDICT_DEFAULT=192` :81；`MAX_N_PREDICT=200` :82。
- CLI `main()` :1812-1840：`--db --blocks --sessions --session --model --n-predict --control --retrieval {off,topk} --n-ctx --n-gpu-layers --chat-start --rollover-at --topk --dry-run`。
- 引擎装配 `make_real_engine()` :348；检索选择 `_retrieval_select()` :662（topk 上限 :422/:719）；记忆写入 `remember()` :967；库容量按模式取 `MAX_MEMORIES` 或 `LIBRARY_MAX` :1003。

### 1.3 `tools/chat_service.py`（产品 C 版 HTTP 服务）

- 默认 `127.0.0.1:8765`：`DEFAULT_HOST` :61、`DEFAULT_PORT` :62；请求体上限 `MAX_BODY = 1 MiB` :64。
- 端点表 :22-29、路由 :493-494：`GET /health`、`POST /ask {text}`、`POST /remember {text}`、`GET /memories`、`POST /forget {id|"all"}`、`GET /status`；处理器 :148-168。
- 并发：`threading.Lock` 显式排队 :13/:108-112，`in_flight_max` 预期恒为 1 :111-112；队列超时映射 429 :80/:92。
- CLI `main()` :531-563：`--host --port --fake-engine --data-dir --db --blocks --sessions --session --model --n-predict --control --retrieval --topk --rollover-at --n-ctx --chat-start --n-gpu-layers --read-timeout --queue-timeout --max-body`。
- 本文件不直接碰引擎：真实模式经 `chat_daily.make_real_engine`（文档头 :17）。

### 1.4 `tools/chat.py`（研究原型，75 KB）

- 文件头 :1-20：**全文无 prompt splicing**；记忆=KV 块，步骤 load→repos_local→seq_cp→generate；"模型收到的 prompt 只有问题"。
- CLI :1425-1458：位置参数 `cmd ∈ {build, chat, save, load, m1, two}`（默认 chat），`--control --path --explain --save --dry-run --out`。
- 子命令实现：`cmd_build()` :209、`cmd_chat()` :242、`cmd_save()` :443、`cmd_load()` :480、`cmd_m1()` :538、`cmd_two()` :1379。
- 与 chat_daily 的差异：chat.py 是研究原型（M1 选择实验 / two 臂 / 无 HTTP、无 daily DB、无日志审计）；chat_daily 是产品化封装（sqlite 记忆、HTTP 服务、rollover、日志、拒答策略）。

## 2 引擎层

### 2.1 `tools/kvslots.py`（KV 引擎封装，ctypes → kvshim）

- `class KVEngine` :93；`__init__(model, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0", dll=None)` :96；dll 定位 `kvshim<suffix>.dll` :99-101；kv 开关 `1 if kv=="q8_0" else 0` :146-147。
- 绑定 ABI :109-143（`kvshim_open/close/write/write_at/ask/ask_at/save/load/seq_cp/seq_rm/repos/repos_local/can_shift` 等）。
- 方法：`bytes_per_token` :156、`pool_bytes` :159、`seq_bytes` :162、`n_tokens` :165、`reset` :173、`write` :176、`write_at` :179、`ask` :182、`ask_at_topk` :191、`save` :255、`load` :297、`load_strict` :300、`repos` :318、`repos_local` :326、`close` :331。

### 2.2 `tools/chat_lease.py`（租约/守卫，fail-closed）

- 语义 :6-16：**`GuardedLeases`：每次破坏性 reset 都必须过它；块被占用时拒绝**；事件日志 `kvmem/lease_logs/events_<label>_<stamp>.jsonl`。
- 继承：`from m3_lease import BlockLeases` :36；`class GuardedLeases(BlockLeases)` :282。
- 环境开关：`CHAT_LEASE_LOG_DIR` :39、`CHAT_LEASE_STRICT` :47（默认 1）、`CHAT_LEASE_BRIDGE` :132。
- 桥接：`init_run` :50、`run_log` :72、`read_log` :84、`install_bridge` :122、`assert_bridged` :165；`RecordingEngine` :186 记录 `OBSERVED=("load","load_strict","repos_local","save","write_at")` :180。

### 2.3 `tools/session_state.py`（会话原子保存/恢复）

- 设计 :2-22：**detach-before-save**；save = quiesce→detach→save chat→写 manifest→reattach；restore = 重算 layout/placement 并比对，`verify -> repos_local -> seq_cp -> verify -> 才生成` :12。
- 函数：`plan_layout` :134、`resolve` :172、`check_layout` :186、`check_placement` :212、`save_session` :251、`read_manifest` :338、`validate_manifest` :343、`restore_session` :369；搬移 `eng.repos_local(...)` :507-510（计数不符即 `LayoutMismatch`）。
- 原子性：`_durable_replace` :63（write-through 失败回退 `os.replace`）。

### 2.4 `tools/memory_source.py`（记忆权威层，sqlite + KV 块）

- `connect` :155、`put_source` :168、`get_source` :199（可 verify_hash）、`assert_m5_source_allowed` :226、`indexable_sources` :303、`build_block` :334、`block_rows` :372、`check_compatible` :381、`load_into` :402、`classify` :412、`verify` :461、`rebuild` :496。
- origin 往返校验：`format_human_turns_origin` :551、`parse_human_turns_origin` :563、`verify_human_turns_origin` :585、`assert_origin_roundtrip` :634、`main()` :645。

### 2.5 `tools/memory_isolated.py`（独立 seq 记忆问答原型，2026-10-27）

- 目的：个人事实问句不走对话历史，只在专用 seq（`ISOLATED_SEQ = 7`）里挂"记忆块 + 问题"生成；根因是对话历史复读（车牌 loop）。
- 机制 :86-...：`reset(7)/reset(scratch)` → 逐条 `memory_source.load_into(eng,row,scratch)` → `repos_local` 到 `[cursor,cursor+n)` → `eng.share(scratch,7,lo,hi)`（seq_cp 零拷贝可见性）→ `reset(scratch)`；循环结束后 `eng.ask(7, question, pos=cursor)`，问题位于所有块之上；结束/异常都 `reset(7)+reset(scratch)`。
- API：`answer_isolated(eng, rows, question, n_predict=64, scratch=6, model_path=None) -> (answer, provenance)`；失败（块不兼容/计数不符/空回答/引擎错误）清理后返回 `(None, {"fallback":"normal_path",...})`，由调用方回退普通路径；空 rows/空问题/scratch==7 抛 `ValueError`。
- 约束：不改 shim/dll/patch；不碰对话 seq（0）；不写任何研究产物。
- 测试：`tools/test_memory_isolated_cpu.py`（fake engine，零 GPU：位置/顺序/计数/清理/失败回退/隔离性）；`tools/test_memory_isolated_gpu.py`（真机小测：两条相似记忆 + 旧历史基线 vs 隔离臂，需 GPU 窗口）。

### 2.6 日志与审计

- `tools/assistant_log.py` :10-12：`audit_index.json` 记录末条 `chain_sha16`/行数/末写时间；**chain_sha16 = 上一行内容（不含行尾换行）sha256 前 16 位，首行为 ""**；:`492` 仅用户显式命令才删除（append-only 针对常规写入）。
- `tools/inspect_logs.py` :15/:36/:97：校验 `chain_sha16` 连续性（`--verify/--summary/--tail/--grep/--export`）。

## 3 研究脚本（`kvmem/m2_visibility/m5/`）

> 共同约定：确定性产物（无时间戳、indent=1、末尾换行）+ `write_json_atomic`；零网络；GPU 臂有 strict host gate。

| 脚本 | 作用 | 关键事实 |
|---|---|---|
| `run_m5c2_b7_gen.py` | (b7′) one-shot 生成 75 问 | :3-20 协议；one-shot 判据 :30-45（无输出可重跑；任一前向/非空回答⇒consumed 禁重跑）；`write_json_atomic` :125；`n_predict=192`、greedy、temp=0、36 层、n_ctx=8192、N_SEQ=8、q8_0、CHAT_START=4096；输出 GEN/raw |
| `run_m5c2_b7_split.py` | 冻结切句（b5 规则逐字） | :3-20 规则（换行/。！？、丢弃空/`</?think>`/纯符号/问 echo）；`write_json_atomic` :78；输出 SENTS :259 |
| `run_m5c2_b7_extract.py` | GPU 逐句抽取（S4） | :3-20 架构；imports `R4/R41/F/R2/BG6` :46-51；`host_gate()` :200；`--allow-gui-procs` 默认关闭 :24；atomic :93；输出 EXTRACT/RAW/REFUSED |
| `run_m5c2_b7_extract_resume.py` | 超时后续跑（shard1/2 按 sid 集） | :3-25；read-only import 冻结 extract `EX` :44；strict gate `EX.host_gate(None,None,...)` :173；atomic :57；`LIMIT_S=3600` |
| `run_m5c2_b7_decide.py` | 离线判定（rev5.1+rev7.2） | :3-18 架构；imports `R4/R41/R5/R51/R72` :37-41（判据逻辑只 import 不改写）；atomic :109；输出 DECIDE/RATES |
| `run_m5c2_b7_wide_sensitivity.py` | 宽读 B 敏感性（cleanblind 派生） | :3-20 只保留 B=任意子串；atomic :76；CLI :371；输出 WIDE-SENSITIVITY |
| `run_m5c2_b7_readings.py` | 两读并列后处理（A2/A3/A4） | :3-14 流水线；输入 DECIDE/WIDE/GOLD → READINGS；atomic :94；CLI :621 |
| `run_m5c2_b7_readings_audit.py` | 独立复算审计（只读） | :3-12 读 DECIDE/WIDE/READINGS/GOLD，独立重算，不写冻结件 |
| `run_m5c2_rev7_2_offline.py` | rev7.2 机制实现（M1/M2/M3） | :3-20 机制说明；`import run_m5c2_rev7_1_offline as R71` :52；atomic :97；CLI :919 |

## 4 不变式（代码位置）

1. **prompt 不拼接记忆**：`tools/chat_daily.py:6`（"prompt 里不拼接任何记忆文本；问句原样交给引擎"）；`tools/chat.py:4`（"There is no prompt splicing anywhere in this file"）。
2. **attach 后不许 reposition（未经验证）**：`tools/session_state.py:12`（verify→repos_local→seq_cp→verify→only then generate）；`:507-510` 对 `repos_local` 后计数逐项校验，不符即 `LayoutMismatch`；`tools/chat_lease.py:180` 只记录 `repos_local` 等等价破坏性操作。
3. **one-shot 判定**：`run_m5c2_b7_gen.py:30-45`；产物字段 `one_shot_consumed`；下游 extract/decide/readings 不消耗第二次（extract 仅在产物里转记 gen 的字段 :180）。
4. **strict gate 无 opt-in**：`run_m5c2_b7_extract.py:24`（`--allow-gui-procs` 显式、默认关闭）；`run_m5c2_b7_extract_resume.py:15/:173`（`host_gate(None,None, n_forward=0)` 严格无例外）。
5. **日志 append-only + chain_sha16**：`tools/assistant_log.py:10-12`；`tools/inspect_logs.py:15/:36/:97`。
6. **records 不变性**：`M5C2-B7-PROVENANCE-V2.json:665-667`（`records_sha256_before == after`，`records_identical=true`，`no_forward=true`）。
7. **原子写**：gen:125、split:78、extract:93、resume:57、decide:109、readings:94、rev7_2:97、wide:76（全部 `write_json_atomic`：tmp + `os.replace`）。

## 5 依赖与外部

- 模型：`D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`，**8,988,110,240 B**、sha16 `0b319bd0572f2730`（GEN/extract gate 钉住；本图只复核实测大小）。
- DLL：`tools/kvshim_vk.dll`，**50,007,552 B**、sha16 `9edbafa150700614`（本图实测复算一致）。
- KV 量化：`q8_0`（`tools/kvslots.py:96/:146`）；`n_seq=8`（`tools/kvslots.py:96`、`tools/chat_daily.py:63`）。
- 判据层冻结：`M5C2-REV7-2-FREEZE.json` `87a13b0c`；b7′ 终态件见 `docs/PROJECT-STATE.md:39-57`。

## 6 只读入口速查

- 研究复现：`kvmem/m2_visibility/m5/run_m5c2_b7_gen.py` → `_split` → `_extract` → `_resume(必要时)` → `_decide` → `_wide_sensitivity` → `_readings` → `_readings_audit`。
- 产品运行：`start_service.cmd`（HTTP）或 `start_chat.cmd`（REPL）。
- 日志核验：`python -X utf8 tools\inspect_logs.py --verify`。
- 独立 seq 原型验证：`python -X utf8 tools/test_memory_isolated_cpu.py`（零 GPU，fake）；`python -X utf8 tools/test_memory_isolated_gpu.py`（需 GPU 窗口）。