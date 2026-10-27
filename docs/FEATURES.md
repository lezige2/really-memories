# FEATURES —— 当前代码真实具备的功能清单（代码事实优先）

> **as-of**：2026-10-27 ｜ 工作目录 `D:\llama-mem`
> **规则**：只列**代码里能指到实现文件**的功能；**未实跑验证**的标 `未核实`。与 `docs/PROJECT-STATE.md` 冲突时，以代码与冻结产物为准。
> （根目录 `FEATURES.md` 是 v1.0 时代历史台账，**已由本文件取代**；历史台账仅追溯用。）

---

## 1 记忆与检索（C 版产品主线）

| # | 功能 | 状态 | 实现位置（可核对） | 备注 |
|---|---|---|---|---|
| 1 | 记忆写入 `/remember`（立即可用；可带 `#标签`） | **具备** | `tools/chat_daily.py:967`（`DailyApp.remember`）、命令分派 `:1610` | 单条上限 600 字符（SPEC） |
| 2 | 记忆列表 `/memories` | **具备** | `tools/chat_daily.py:1056`、`:1614` | 显示 id/token/时间/首行 |
| 3 | 记忆删除 `/forget <id>|all`（二次确认） | **具备** | `tools/chat_daily.py:1069`、`:1624` | 删除会结束当前对话，避免旧引用 |
| 4 | 记忆挂载进 KV 块（seq 1..6，≤6 块） | **具备** | `tools/chat_daily.py:63-64`；`tools/kvshim_vk.dll`；`patches/persistent-memory.patch` | 挂载上限与显存/块区预算绑定 |
| 5 | 检索式挂载 `--retrieval topk`、`topk=4` | **具备** | `tools/chat_daily.py:70,398-422`；`tools/retrieval.py`（`search` 等） | bigram+标签召回 + 1 跳关联扩展 |
| 6 | 库容量上限 200 条（`off` 模式仍为 6 条全挂载） | **具备** | `tools/chat_daily.py:67`（`LIBRARY_MAX=200`） | 超限报 `memory_full` 并回滚 |
| 7 | 记忆区预算 7,680 token（= chat_start−512） | **具备** | `tools/chat_daily.py:60,80` | 预算超限报错并提示 `/forget` 精简 |
| 8 | 自动压缩（rollover）：≥75% 对话窗 → 归档原文 + ≤200 token 摘要索引块 | **具备** | `tools/chat_daily.py:1126,1137`；测试 `tools/test_rollover_cpu.py` | 实测：`auto_summary id=5 ↔ auto_archive id=4`、`related_ids==[4]`（回归件） |
| 9 | 会话保存/恢复：`/save`、`/load`、`/quit` 自动保存、启动自动恢复 | **具备** | `tools/chat_daily.py:1634-1640`；会话目录 `kvmem/sessions/` | 默认 `kvmem/sessions/daily.json` |
| 10 | 拒答（记忆里没有就不猜） | **具备** | `tools/chat_daily.py:86`（`PRODUCT_REFUSAL`） | 拒答语句固定、可审计 |
| 11 | 引擎参数：16k（8192/7680）、34 层、kv `q8_0`、`n_predict≤200` | **具备** | `tools/chat_daily.py:59-82`；`tools/memory_source.py:51` | VRAM 峰 ≈8.0 GiB（v1.0 实测） |

## 2 日志与审计（个体日志）

| # | 功能 | 状态 | 实现位置 | 备注 |
|---|---|---|---|---|
| 12 | 个体日志身份（`assistant_id` UUID 终身不变）+ 逐事件 JSONL + `chain_sha16` 防篡改 | **具备** | `tools/assistant_log.py`（`DEFAULT_ROOT=kvmem/assistant`、`scrub`、manifest） | 落盘位置见 `docs/USER-GUIDE-C.md` §9 |
| 13 | 隐私模式 `full|redacted|hash_only`（默认 redacted） | **具备** | `tools/assistant_log.py`（`MODES`、`set_mode`） | 打码仅已知模式，不保证全覆盖 |
| 14 | 日志校验/摘要/导出：`--verify`、`--summary`、`--tail`、`--grep`、`--export` | **具备** | `tools/inspect_logs.py:241-249` | 实测 A/B/C 三根 `--verify` 全 rc=0（回归件） |
| 15 | 崩溃恢复（上次未写 `session_end` ⇒ `crash_recovered`） | **具备** | `tools/assistant_log.py`；`tools/inspect_logs.py` | 强杀末个 ask 按 aborted 放行 |
| 16 | `/log` 命令（状态/模式切换/清理） | **具备** | `tools/chat_daily.py:1603,1732-1765` | 清理需二次确认 |

## 3 服务与接入

| # | 功能 | 状态 | 实现位置 | 备注 |
|---|---|---|---|---|
| 17 | 本地 HTTP 服务 `127.0.0.1:8765`：`/health /status /memories /ask /remember /forget /save /load` | **具备** | `tools/chat_service.py:455-530`（路由表 `KNOWN_ROUTES`） | 单用户、只绑回环、无鉴权 |
| 18 | OpenAI 兼容接口：`GET /v1/models`、`POST /v1/chat/completions` | **具备** | `tools/chat_service.py:455-465,362` | 供 DSH 桌面端 `api: openai-completions` 使用；`test_openai_compat_cpu.py` |
| 19 | 一键启动服务（固定参数 16384/8192/34/topk=4） | **具备** | `start_service.cmd` | 日志 `kvmem\daily\service.log` |
| 20 | 交互式聊天（双击启动、`--dry-run` 假引擎自测） | **具备** | `start_chat.cmd`；`tools/chat_daily.py:1837` | `--dry-run` 落 `kvmem/_dryrun_daily`，不能当真模型结果 |
| 21 | QQ 接入（OneBot v11 反向 WebSocket → 本地服务） | **具备（未实网核实）** | `tools/qq_bridge.py`、`tools/qq_bridge.example.json` | **第三方协议端，有封号风险**（见 `docs/QQ-BRIDGE.md`）；实网连通性 `未核实` |
| 22 | DSH provider 切换（`local14b`）+ 回滚 | **具备（本机脚本）** | `restart-dsh.cmd`、`rollback-dsh-local14b.cmd` | 依赖本机 DSH 配置与备份文件；不同机器 `未核实` |

## 4 验收与测试（可重跑）

| # | 功能 | 状态 | 实现位置 | 备注 |
|---|---|---|---|---|
| 23 | C 版验收（S1–S7，真实引擎） | **具备** | `tools/run_c_acceptance.py` | 产物 `C-V1-ACCEPT.json e8e7521e/10398`（v1.0 通过） |
| 24 | C 版 v1.1 回归（检索/rollover/长回答/日志） | **具备** | 回归脚本（LEAD 执行，件 `C-V1-1-REGRESSION.json 611fc849/6084`） | v1.1 通过；脚本路径 `未核实`（件在盘可查） |
| 25 | CPU 单测（离线、假引擎） | **具备** | `tools/test_chat_daily_cpu.py`、`test_chat_service_cpu.py`、`test_logging_cpu.py`、`test_memory_graph_cpu.py`、`test_openai_compat_cpu.py`、`test_qq_bridge_cpu.py`、`test_retrieval_cpu.py`、`test_rollover_cpu.py` | 需本机 Python 3.11+ |
| 26 | 一键复算/自检 | **具备** | `verify.sh` | 覆盖范围以脚本内容为准（未逐项复核） |

## 5 研究工具（研究线已封闭，仅留档）

| # | 功能 | 状态 | 实现位置 | 备注 |
|---|---|---|---|---|
| 27 | 研究线判据/离线复算脚本（rev5/rev7/rev7.1/rev7.2、b5/b6/b7 生成与判定） | **具备（历史）** | `kvmem/m2_visibility/m5/run_m5c2_*.py`、`out/m5c2_*.py` | 研究线 **R10 终止**，不再改判据；勿据 b7′ 调参重跑 |
| 28 | 显存/块布局/检索探针与旧实验脚本（M1–M7） | **具备（历史）** | `tools/block_info.py`、`tools/kv_audit.py`、`tools/eval_retrieval.py`、`tools/*.py` | 数字属历史；引用前查 `docs/_work/ANCHORS-CURRENT.md` |
| 29 | 模型下载 | **具备** | `tools/dl_14b.py`、`tools/dl_14b_par.py` | 目标 `D:\models\*.gguf` |
| 30 | 构建脚本（工具链/ Vulkan 构建；GBNF 路线已作废） | **具备（部分历史）** | `tools/build_tools.ps1`、`tools/build_gbnf.ps1`、`verify.sh` | GBNF 路线仅历史溯源 |

---

## 6 明确"未核实 / 不承诺"清单

- QQ 实网连通（NapCat/Lagrange 版本差异）、群聊行为、封号风险：**未核实/不承诺**。
- 长回答延迟分布（P50/P95）：仅单次实测（328 字/23.45 s），**多次分布未核实**。
- 多用户/鉴权/网络暴露：**不支持**（单用户、只绑回环、无鉴权）。
- 跨机器/换驱机的 DSH provider 补丁：**未核实**（脚本按本机路径写死）。
- 研究线判据能力：**已封口**（b5 擦边 / b6 未接上 / b7′ 擦边；操作点超可达界 ⇒ 不可达标），不在本清单宣称能力。

> 维护：新增/删除功能 ⇒ 同时改本文件与 `docs/PROJECT-STATE.md`；**不要**把"研究线读数"写进本清单。

## 7 行为变更（v1.3：自动记忆 / 拒答 / 只读联网 / 内省 / 检索门槛）

> 代码已改（2026-10-27），**待最终测试**；测试后在此更新状态。

| # | 功能 | 状态 | 实现位置 | 备注 |
|---|---|---|---|---|
| 31 | **自动记忆（静默）**：陈述"我的事实"自动写入长期记忆，不回复"已记住 id=N" | **已改·待实测** | `tools/chat_daily.py::_auto_remember_candidate`（`:1009`）；静默写入 `:1406-1415` | 判定：6–200 字、前 12 字含「我/俺」、含事实提示、非问句/非命令；`/auto` 开关**预留未实现** |
| 32 | **拒答文案与行为**：无记忆个人事实固定拒答，不再用"对话历史提过"放行 | **已改·已在 CPU 断言** | `tools/chat_daily.py:87`（`PRODUCT_REFUSAL`）、`:1476-1490`；`tools/test_refusal_cpu.py` | 文案：「记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。」 |
| 33 | **只读联网检索**：时间敏感/需查证问题先查 Bing 再答，答案带「（来源：Bing 检索）」 | **已改·待实测**（联网可用性） | `tools/web_lookup.py`（只读 GET，8 s 超时）；`tools/chat_daily.py::_should_search/_web_answer`（`:975-1003,1425`） | 无登录/无写/无脚本；失败回退"不知道"；模型不得自称能联网 |
| 34 | **能力/记忆内省**：问"你记得什么"列真实记忆；问"能联网吗"明确说不能 | **已改·待实测** | `tools/chat_daily.py::_capability_reply`（`:1023-1045`） | 确定性回复、不调模型 |
| 35 | **检索相关性门槛**：命中数+覆盖率双门槛，弱命中不挂载 | **已改·待实测** | `tools/chat_daily.py::_retrieval_select`（`:663-700`） | 默认 score≥2.0 且 coverage≥0.30；短查询例外 score≥1.0 且 coverage≥0.5 |

## 8 行为变更（v1.4：答案核对，待实现）

| # | 功能 | 状态 | 实现位置 | 备注 |
|---|---|---|---|---|
| 36 | **答案核对**：基于记忆的答案先生成→核对→通过才返回；不通过重答 1 次；仍不过给兜底句「这条我没法从记忆里核对，先不猜。」 | **待实现（T1–T4 接口）· 待实测** | 待落地（CLI/服务同一路径）；开关 `LLAMA_MEM_VERIFY`；日志 `verify_repair` / `verify_fallback` | 机制图/触发/限制见 `docs/ANSWER-VERIFY.md`（草稿）；关闭开关=退回 v1.3 行为 |
