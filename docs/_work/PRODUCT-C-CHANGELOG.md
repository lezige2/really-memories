# PRODUCT-C-CHANGELOG

C 版「14B 本地记忆助手」交付变更记录。口径冻结在
`docs/_work/PRODUCT-C-SPEC.md`（`694ebbad136efbec`）与 `docs/_work/PRODUCT-C-LOG-SPEC.md`
（`56a7fca2b169bcf3`）；本文件只记录**实现决定、与原型差异、发现的 bug**，不放宽验收。

## 1 交付件

| 文件 | 作用 |
|---|---|
| `tools/chat_daily.py` | 日常入口：REPL + 可复用 `DailyApp` API（记忆/会话/日志/状态） |
| `start_chat.cmd` | 双击启动（`python -X utf8 tools/chat_daily.py`；失败 `pause`） |
| `tools/chat_service.py` | 本地 HTTP 服务：REST + **OpenAI 兼容** `/v1/models`、`/v1/chat/completions`（SSE） |
| `tools/assistant_log.py` | 个体日志（append-only JSONL + chain + 隐私模式 + 身份 manifest） |
| `tools/inspect_logs.py` | 日志校验/汇总/tail/grep/导出（CPU-only） |
| `tools/test_chat_daily_cpu.py` | REPL/记忆/会话/拒答/异常输入，零 GPU |
| `tools/test_chat_service_cpu.py` | REST 端点/串行/错误码/读超时/端口释放，零 GPU |
| `tools/test_logging_cpu.py` | S7a/S7b/S7c：完整性、崩溃恢复、脱敏、篡改检测，零 GPU |
| `tools/test_openai_compat_cpu.py` | OpenAI 兼容（非流式/SSE/记忆前缀/截断告警/错误映射/串行），零 GPU |
| `docs/USER-GUIDE-C.md` | 使用指南（含三类日常记忆、服务模式、DSH 接入、日志） |

复用而非复制：`tools/kvslots.py`（引擎，仅真实模式 import）、`tools/memory_source.py`
（source/block 权威层、`build_block`/`load_into`）、`tools/session_state.py`
（`save_session`/`restore_session`）、`tools/chat_lease.py`（`GuardedLeases`，reset 必经）、
`tools/retrieval.py`（检索）、`tools/evidence.py`（三态证据决策）。
**未修改**上述既有 tools 文件、任何冻结件、任何 PREREG；未 git commit。

## 2 实现决定

1. **独立数据面**：C 版用 `kvmem/daily.db` + `kvmem/daily_blocks/` + `kvmem/sessions/daily.json`，
   不碰研究库 `kvmem/chat.db`（避免 10 条 M5 源被当成用户记忆挂载）。会话/块/日志默认都在
   `kvmem/` 下，可用 `--db/--blocks/--sessions/--data-dir` 覆盖。
2. **记忆表示**：`memory_source` 行（`text_kind=human_memory`、`contains_model_turns=0`）
   + `memory_block`（KV 块）。`put_source()` 的默认值是 conversation/1（会被 M5 门拒绝），
   所以 `DailyApp._put_memory_source()` 按同一张表显式写入 human_memory/0（不改 `memory_source.py`）。
   记忆名 `mem-<sha256(text)[:12]>`：同文本幂等去重，不同文本不会同名。
3. **容量写死**：单条 ≤600 字符；条数 ≤6（seq 1..6，seq 7 留 preflight）；记忆区总 token ≤3840。
   超限返回 `memory_full` 并回滚该条（source 行 + block 行 + 块文件一起清）。
4. **挂载几何**：全部记忆紧凑排布在 `CHAT_START=4096` 下方
   （`session_state.plan_layout(..., slot_capacity=None)`，块紧贴锚点、零间隙），
   与 `tools/chat.py` 的「右对齐 64-token slot」不同——原型 `_place_slots` 每块最多 64 token，
   产品记忆长度不可控，所以用紧排。
5. **拒答语义**：检索命中只用来判「有没有记忆证据」，**不进入 prompt**。
   - 有命中 → 挂载全部记忆（≤6），模型正常生成；
   - 无命中 → `evidence.decide()`；对「个人事实问句」返回固定拒答文本 `PRODUCT_REFUSAL`
     （模型不调用，避免编造）；
   - 在 `evidence.decide` 之外加了一层产品兜底 `_product_fact_question()`（问句 + 非世界知识 +
     无记忆命中 ⇒ 拒答），因为 `evidence.py` 的 `memory_recall` 只认「我的+事实名词」，
     日常问法（「那家店叫什么？」）会漏。**宁可多拒，不编**。
   - 检索绝对门槛（`GATE=1.30`）对单条短记忆偏严；无命中时加一层**逐字内容二元组**兜底
     （过滤「我在/哪家/买的」这类疑问/助词片段），只影响拒答判定，不改 retrieval 阈值。
6. **立即生效**：`/remember` 先提交 source 行 → 建块（在 seq7 建，不碰已挂载块）→ 重建检索索引
   → 重挂全部记忆；同一进程下一条问题即可命中。
7. **forget 语义**：删 source（级联 block 行）+ 删块文件 + 重建索引 + **结束当前对话**
   （detach → `reset(0)` → 重挂剩余记忆）。理由：S4 要求「删除后同题再问不再引用该事实」，
   若保留旧对话 KV，模型仍可能复述被删事实。
8. **会话**：`/quit` 自动 `save_session`（原子替换+fsync）；启动时 `daily.json` 存在即自动恢复，
   再按数据库记忆集重对齐挂载。额外写 `daily.transcript.json` 旁车保存最近 40 轮**文本**记录，
   供重启后的「对话内证据」判定（KV 恢复不等于文本 transcript 恢复）。
   没有任何记忆时会话用最小 `chat_daily_chat_only_v1` manifest（`session_state` 不接受空 blocks）。
9. **日志**：`assistant_log.AssistantLog` 实现 LOG-SPEC——UUID `assistant_id` 不可变、
   append-only JSONL、每行 `flush+fsync`、`chain_sha16` 逐行链接、日索引/incidents/audit_index、
   `redacted`（身份证 18/手机号 11/密码值打码，保留 `input_sha16`）与 `hash_only`、`/log purge`。
   服务端按 `X-Session-Id` 切会话（无则默认会话），所有 action（ask/answer/refuse/remember/forget/
   save/load/status/memories/error/warning）都落日志。
10. **HTTP 服务**：单线程 `HTTPServer` + `threading.Lock` 显式串行（GPU 单卡，禁止并发推理），
    `/status` 暴露 `in_flight_max`；`--queue-timeout` 超时返回 429 风格错误；
    `--fake-engine` 用 StubEngine（零 GPU）。真实模式只在 `chat_daily.make_real_engine()` 里
    import `kvslots`。
11. **OpenAI 兼容**：`/v1/models` 固定 `local-14b-memory`、`context_window=8192`；
    `/v1/chat/completions` 取 `messages` 最后一条 user 文本（支持 content 分块数组），
    超预算时截断并写 `warning: prompt_truncated`（含 orig/kept 字数），流式用 SSE（块 10 字符 +
    `finish_reason=stop` + `[DONE]`）。自动记忆只认显式前缀 `记住：`/`记一下：`/`/remember `。
    错误统一 OpenAI 风格 `{"error":{"message","type","code"}}` + 非 2xx。
12. **写作纪律**：所有运行期 JSON（日志/会话旁车/导出）用 tmp + `os.replace` 原子替换，
    `open(...,"w",encoding="utf-8",newline="\n")`；未使用 `Path.write_text(newline=...)`。

## 3 与 tools/chat.py 的差异

| 维度 | chat.py（研究原型） | chat_daily.py（C 版） |
|---|---|---|
| 数据面 | `kvmem/chat.db` + `kvmem/blocks`（M5 源 10 行） | `kvmem/daily.db` + `kvmem/daily_blocks`（用户记忆） |
| 记忆条数 | 固定 2 块（`_rows_for_session(limit=2)`） | 全部记忆（≤6），随时增删 |
| 放置 | 右对齐 slot，每块 ≤64 token | 紧贴 `CHAT_START` 下方紧凑排布（`slot_capacity=None`） |
| 选块 | `cmd_m1` 每题按检索选 top-k 挂载 | 全部挂载；检索只决定「是否拒答」 |
| 拒答 | `evidence.decide` 三态（原型无产品兜底） | 三态 + 产品「具体事实问句」兜底（宁可多拒） |
| 输入 | 固定 `QUESTIONS`（L62） | 自由输入 + `/` 命令 |
| 会话 | `save`/`load` 子命令跑固定流程 | `/quit` 自动存、启动自动恢复、`/save `/`/load` 任意路径 |
| 日志 | 无个体日志 | append-only 逐动作日志 + 校验工具 |
| 服务 | 无 | REST + OpenAI 兼容，单线程串行 |

## 4 发现的 bug（只记录，未改既有文件）

- **B1 `session_state.restore_session` 预检用默认模型路径**：内部 `ms.load_into(eng,row,scratch)`
  的 `model_path` 默认值在 import 时绑定为 9 GB GGUF 真实路径；非默认模型（测试/fake）会在
  预检被判 `Incompatible` → 走 `ms.rebuild()` → `build_block` 调 `eng.reset(scratch)`，
  而该 scratch seq 未在租约表登记 → `CHAT_LEASE_STRICT=1` 抛
  `LeaseError: refusing reset(seq 2): not a registered block`。
  C 版 workaround：`chat_daily.install_fake_model()` 只在**本进程**给 `ms.load_into` 的默认
  `model_path` 注入占位模型路径（不改文件）；真实模式模型即默认路径，不受影响。建议后续单独立项修
  `session_state.py`（把 `model_path` 透传给预检）。
- **B2 `chat.py:_chat_scratch(rows)` 用 `len(rows)+1`**：当索引里 ≥7 个块时 scratch 撞 `N_SEQ=8`；
  原型只挂 2 块所以没暴露。C 版固定 scratch=seq7、挂载上限 6 条规避。
- **B3 原型 slot 容量 64 token**：`_place_slots`/`slot_capacity=SLOT` 使单块必须 ≤64 token；
  用户记忆长度不可控，C 版改用 `slot_capacity=None` 紧排。
- **B4 空 blocks 无法存会话**：`session_state.check_placement([])` 直接返回
  `placement has no blocks` ⇒ 无记忆时 `/save` 必失败。C 版用最小
  `chat_daily_chat_only_v1` manifest 兜底。
- **B5 慢客户端读超时产生 traceback**：Python 3.14 下 `rfile.read()` 超时抛的是普通
  `OSError("cannot read from timed out object")`（不是 `socket.timeout`），
  `BaseHTTPRequestHandler` 接不住 → `socketserver.handle_error` 打印 traceback。
  C 版重写 `handle_one_request` + `ServiceHTTPServer.handle_error` 兜住（只关连接、留一行告警）。
- **B6 `X-Session-Id` 只在 POST 分支处理**：GET 路径不经过 session 头处理，响应不回显。
  已改为所有请求统一 `_apply_session_header()`。
- **B7 对话窗口 token 估算口径不一致**：服务层截断预算按 `len/2`，`DailyApp.ask` 的窗口检查
  按 `len*2`，导致「截断后仍被判 chat_full」。已统一为 `ceil(len/2)` 并重算两侧余量。
- **B8 日志 `new_session()` 自动写 `session_resume`** 但缺 §3 必填字段（pins/log_config）⇒
  `--verify` 会判 missing_field。已改为 `new_session` 只做文件切换，由调用方写
  `session_start`/`session_resume`（带 pins/log_config）。
- **B9 `queue_timeout` 在单线程服务里不可达**：`HTTPServer` 串行 accept，锁始终空闲，
  只有换 `ThreadingHTTPServer` 才会排队超时。代码路径保留（错误映射 429 已实现），
  但当前部署下不会触发；已在文档说明。
- **B10 `--verify` 对被强杀的会话误报**：崩溃会话末个 `ask` 必然没有 `answer`，
  若按 S7a 逐 ask 配对会判 FAIL。已按「末事件非 `session_end`」认定为 aborted session，
  跳过配对并单列 `aborted_sessions`（S7b 语义）。

## 5 需要 GPU 才能验证的清单（本交付未跑）

1. S1/S3 真实回答 3/3 正确且含具体值（14B + KV 块；CPU 测试只能验证挂载链路）。
2. S2 拒答 ≥5/6（应用层拒答路径 CPU 可测，但「模型不编造」需真机行为）。
3. S5 对照会话（`--control`）真实拒答行为。
4. S6 全程 VRAM ≤8.6 GiB、回答中 `taskkill /F` 后重开记忆仍在；冷启动 ≤120 s、P95 ≤60 s。
5. `C-V1-ACCEPT.json` 的 `resources.peak_gib` 与真实延迟采样（需 GPU 验收臂）。
6. S7b 真强杀（本仓库用子进程 `os._exit(7)` 模拟，真实 `taskkill` 留 GPU 验收臂）。
## 6 GPU 基线冒烟反馈的落地（2026-10-27）

LEAD 用 `tools/chat.py chat` 实测（GPU）暴露两点；C 版按此硬约束实现，**未复制** `chat.py:379`
的收尾基准循环（`repos_local` 惯性回移，属研究基准，不是产品路径）：

- **B11（记录）** `chat.py:379` 在块 seq1 已 attach 到对话 seq0 后调
  `eng.repos_local(1, +64)`，被 M3 守卫 fail-closed 拒绝（`LeaseError: still referenced by
  dialogue seq(s) [0] ... Detach first`）。结论：**任何「先 attach 后 reposition」都必炸**。
  C 版 placement 顺序写死：`detach(0, lo, hi)` → `reset(block seq)` → `preflight load(scratch)` →
  `load(block seq)` → `repos_local(block seq)` → `attach(block seq, 0, lo2, hi2)` → `ask`；
  块集不变时完全不动块（不重排、不 reposition）。
- **无记忆不得编造**：GPU 冒烟里对照问题「我的车牌号是多少？」模型答「京A12345」。C 版：
  无记忆命中 ⇒ `evidence.decide` + 产品兜底直接返回固定拒答 `PRODUCT_REFUSAL`，**模型不调用**；
  命中记忆时在提问前加应用层指令 `ANSWER_INSTRUCTION`（不是记忆文本，prompt 仍不含记忆原文）。
- **`n_predict` 默认 192**（SPEC 输出预算 ≤200；Lead 建议 160–256 省时）。
- **QUIT 前清干净**：`/quit` 自动 save 后 `_unmount_all()`（detach+reset 块 seq）+ 额外 reset
  preflight scratch（seq7），保证下次启动无残留 attach/cell；`--verify` 的 S7 断链判定不受影响。
- **测试补强** `t_placement_guard`：用 `GuardedStubEngine` 模拟 M3 守卫（attach 后 repos_local 即抛），
  证明「remember→ask→remember→ask」走的是 detach-first 路径且守卫真实生效；并验证关闭后
  `attached=={}`、seq1–7 cells 全 0、prompt 以指令开头且不含记忆原文。

## 7 真引擎服务冒烟反馈的落地（2026-10-27 第二轮）

- **B12 `--session` 相对路径落错**：`DailyApp.__init__` 只在 `session_path` 为空时拼 sessions 目录，
  传 `--sessions <dir> --session smoke.json` 时 `smoke.json` 被当成 cwd 相对路径 ⇒ 写到 D:\llama-mem\smoke.json。
  已改为：`session_path` 非绝对路径 ⇒ `os.path.join(sessions_dir, session_path)`。已加 CPU 测试
  `T10.session_path`（服务端 `/save` 路径应等于 `<sessions>/svc_smoke.json`）。
- **B13 服务端 think 标签/问答复读泄漏**：`chat.py` 原型用 `clean()` 只取第一段；R1-distill 会输出
  ` thinking…`，且答完继续续写「下一问/下一答」模板（如问车牌，回答里出现“我的车型是什么？ 答：…”）。
  统一到 `chat_daily.clean_answer()`：剥 `<think…>`/未闭合 think/孤立标签 → 去 `<|im_end|>` →
  去 `ANSWER_INSTRUCTION` 回显 → 取第一段 → 截断「问：/答：」续写 → 截断答案内回显问句（砍到前一句边界）。
  `chat_service._chat_action()` 再调一次（幂等双保险），REPL/非流式/SSE 三条路径共用同一函数。
  指令本身也加严为「只回答当前这一个问题，不要复述问题也不要续写问答模板」。
- **remember 不写对话 seq**（复核结论）：`/remember` 建块只用 preflight scratch seq7，不碰 seq0；
  实测 `GuardedStubEngine.last_ask_text` = 指令前缀 + 用户问题，且不含记忆原文（测试 T10.no_memory_text_in_prompt）。
- **`/status` 显存字段语义显式化**：`vram_gib=null` + `vram_gib_source="external_sampler_required"` +
  `vram_gib_note`（说明峰值由验收臂外部采样写入 `C-V1-ACCEPT.json:resources.peak_gib`），并保留 `kv_pool_gib`。
- **新增验收臂 `tools/run_c_acceptance.py`**：子进程驱动 S1–S6 + S7a–S7d；每问 ≤90s/每场景 ≤10min；
  `--dry-run` 用 StubEngine 验框架（13 项 framework checks：子进程/命令/save-load/强杀/crash_recovered/
  verify/redacted/answer-block_ids），打印 `dry-run framework = PASSED` 且 exit 0；
  真机模式外部 `nvidia-smi` 采样 VRAM 峰值，产物 `C-V1-ACCEPT.json`（SPEC §6 字段，原子写）。
  dry-run 的内容型断言一律 `[framework]`、场景记 `未接上`；S2 场景判定按「≥5/6 拒答」聚合，
  个体 q 仅作诊断（避免个体 case 与聚合口径打架）。

## 8 显存采样回退链（本机无 nvidia-smi）

本机 PATH 无 `nvidia-smi`（实测调用失败）。验收臂 `VramSampler` 改为回退链（2 s 一次，线程内异常
全部吞掉、不影响主流程）：
1) `nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits`（MiB→GiB）；
2) 回退 PowerShell `Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory`
   （`DedicatedUsage` 求和 / 1GB，GiB；本机实测可用，空闲约 0.852 GiB）；
3) 两条都不可用 ⇒ 场景 S6 记 `未接上（采样不可用）`，`resources.peak_gib_source="unavailable"`。
本机产物取 `peak_gib_source="powershell-gpuadaptermemory"`；若装了 NVIDIA 驱动则优先 `nvidia-smi`。

## 9 上下文参数化 + 记忆库「存全文/标签/关联」+ 自动压缩（2026-10-27）

- **上下文参数化**：`N_CTX_DEFAULT=8192` / `CHAT_START_DEFAULT=4096` 常量集中；`DailyApp` 实例化
  `n_ctx/chat_start/chat_budget/memory_budget`，全部预算检查、rollover 阈值、`/status`、
  save/load anchor 改用实例值；CLI 加 `--n-ctx/--chat-start/--rollover-at`（daily+service），
  验收臂透传并记录 `engine_meta.n_ctx/chat_start`。GPU 选型后无需改代码即可拉长上下文。
- **记忆记录扩展**：新增独立小表 `daily_memory_meta(source_id,tags,source,related_ids)`（不改
  `memory_source` 结构）；`/remember <文本> #标签…` 支持标签；`/memories` 显示
  id/首行/字数/tags/source/related_ids；记忆**存全文**（不是摘要）。
- **检索升级**：bigram 分数 + 标签命中加权（+2/标签）；top-k 后做 **1 跳关联扩展**
  （related_ids 优先、同标签其次），总挂载 ≤6 条且 ≤记忆预算；`/status.retrieval` 增加
  `candidates/related`；回答指令加“若有多条相似记忆，按标签/时间区分，拿不准就说不确定”。
- **rollover 改为“摘要只做索引”**：被移出的对话**全文**原子写到
  `kvmem/daily/archive/<ts>-<hex>.txt`，并登记为 `source=auto_archive` 记忆块（全文，tag
  `auto_archive,<日期>`）；摘要块 `source=auto_summary`、`related_ids` 指向归档；
  检索命中摘要时通过关联扩展同时挂原文块。`context_rollover` 日志增加 archive_id/archive_path。
- **测试**：新增 `tools/test_memory_graph_cpu.py`（标签/关联/摘要→原文/相似两条/预算截断/字段）
  与 `tools/test_rollover_cpu.py`（触发顺序、摘要失败退化、关闭、硬保护、日志、REPL 提示）。

## 10 上下文/层数定型（GPU 实测选型，2026-10-27）

LEAD 实测 8 组（14B/q8_0/36→28 层 × 8192→16384）后选定默认：
**n_ctx=16384、n_gpu_layers=34、chat_start=8192、kv=q8_0**（11.36 tok/s、VRAM 峰 8.003 GiB，
离 fuse 8.6 留 0.6 GiB；36 层 16384 虽 12.66 tok/s/8.378 GiB 但余量仅 0.22 GiB，不采用）。
- `N_CTX_DEFAULT=16384`、`CHAT_START_DEFAULT=8192`、`N_GPU_LAYERS_DEFAULT=34`、
  `MEMORY_SAFETY_MARGIN=512` ⇒ 块区预算 7,680、对话窗 8,192、rollover 0.75 不变。
- 新增 `--n-gpu-layers`（daily/service 共用）→ `KVEngine(..., gpu=NGL)`；`/status.engine.n_gpu_layers`
  与 `/status.engine_meta`、`session_start` 日志的 `engine` 字段、验收臂 `engine_meta` 均记录实际值。
- `start_service.cmd` 更新为定型参数（`--n-ctx 16384 --chat-start 8192 --n-gpu-layers 34
  --retrieval topk --topk 4`）。
- 全部 7 个 CPU 测试 + `run_c_acceptance --dry-run` 复跑通过（详见交付回报）。
