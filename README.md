# llama-mem —— 把长期记忆做进推理引擎的 KV 张量里

> **不拼 prompt，改引擎**：把一段记忆编码成 **KV 张量块**（`.kvmem`）常驻 attention，紧贴其后提问 —— **删掉对话历史，记忆仍可被读出**（「prompt 里一个字都没有也能答对」）。
> 本机、单用户、**默认离线（仅只读 Bing 检索）** ｜ 本地工作树 `D:\llama-mem` ｜ llama.cpp fork（分支 `persistent-memory`）
> **文档入口**：**[`docs/README.md`](docs/README.md)**（先读它，再读 `docs/PROJECT-STATE.md`）

---

## 1 项目是什么（30 秒）

| 项 | 内容 |
|---|---|
| 目标 | 长期记忆进 **KV cache**（引擎层），不靠对话历史/prompt 拼接 |
| 做法 | llama.cpp 补丁（`patches/persistent-memory.patch`）+ shim `tools/kvshim_vk.dll`；记忆块按 `seq` 挂载 |
| 产品形态 | 本地 14B 记忆助手：CLI/HTTP 服务（`127.0.0.1:8765`）+ 个体日志，**单用户/离线** |
| 装置 | 单卡 ~10 GB；14B Q4_K_M；`n_ctx=16384`（对话窗 8192 / 记忆区 7680）；`n_gpu_layers=34`；kv `q8_0`；检索 `topk=4` |

## 2 五分钟状态（as-of 2026-10-27）

**研究线：已封闭。** 三条数据集的终态：

| 数据集 | 判据 | 误判 | 漏判 | 结论 |
|---|---|---|---|---|
| b5（40 题/326 句） | rev7.1 | 9/72 = 12.50%（hi 22.08%） | 0/29（hi 11.70%） | **擦边**（已永久降为 dev） |
| b6（40 题/233 句） | rev7.1 | 13/69 = 18.84%（hi 29.61%） | 1/17 不可测 | **未接上（样本量不足）** |
| **b7′（75 题/623 句）** | **rev7.2** | **22/147 = 14.97%（hi 21.62%）** | **10/62 = 16.13%（hi 27.21%）** | **擦边（两读一致）** |

- **能力结论**：判据操作点 ≈15% > H1 可容纳极限 ≈**12.70%** ⇒ **当前设计下不可达标（能力上限，非样本量问题）**；`R10` 终止，不再改判据/不开 b8。
- 出处（冻结件，引用必带 sha16）：`M5C2-B7-VERDICT.json 1cb7a7961aefe0c6/4165`、`M5C2-B7-VERDICT-SUPPLEMENT.json a58c3c87393a5b0c/3871`、`docs/_work/B7-FINAL-REPORT.md 9b0ed2d3178616d7/5294`。
- **禁语**：不得写「接近达标」「就差一点」「样本量不足导致」「再多一点数据就能过」。

**产品线：C 版 v1.1 通过。**
- 验收：`C-V1-1-REGRESSION.json 611fc849f7cb3118/6084`（外钉 `d2fe383c`）：检索 **4/4**（1.24–3.48 s）、强制 rollover（`auto_summary #5 ↔ auto_archive #4`）、长回答 **328 字 / 23.45 s**、三日志根 `inspect_logs --verify` 全 **rc=0**。
- v1.0 可用性：`C-V1-ACCEPT.json e8e7521e/10398`（pin `286fcdf7`）。
- **隔离**：产品证据不得进入研究线引用链（详见 `docs/_work/ARTIFACTS-KEY.md` §F）。

## 3 目录地图

| 路径 | 是什么 |
|---|---|
| `tools/` | Python/C++ 工具：`chat_daily.py`（CLI 助手）、`chat_service.py`（HTTP/OpenAI 兼容服务）、`inspect_logs.py`（日志校验）、`retrieval.py`、`assistant_log.py`、`qq_bridge.py`、`run_c_acceptance.py`、CPU 单测 `test_*_cpu.py` |
| `kvmem/` | 证据与数据：`daily.db`/`daily_blocks/`/`sessions/`/`assistant/`（运行数据）；`m2_visibility/m5/**` 为研究线冻结件（**只读，勿改**） |
| `patches/` | llama.cpp 补丁（`persistent-memory.patch`） |
| `docs/` | 文档：入口 `docs/README.md`、状态 `docs/PROJECT-STATE.md`、能力 `docs/FEATURES.md`、使用 `docs/USER-GUIDE-C.md`、归档 `docs/archive/`、证据索引 `docs/_work/` |
| `llama.cpp/`、`llama.cpp-upstream/` | 打补丁的构建树 / 上游原件；`bin/llama-vulkan/` 本地构建产物（不入库） |
| `models` | 模型权重在 **`D:\models\`**（`DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`），不在仓库内 |
| `build-vulkan/`、`build-cpu*`、`vulkan-sdk/`、`downloads/` | 构建产物/SDK/安装包（可重建，体积大） |

## 4 常用命令（都在 `D:\llama-mem` 下，Windows）

```bat
:: 1) 启动本地记忆服务（127.0.0.1:8765；参数已固定：16384/8192/34/topk=4）
start_service.cmd

:: 2) 交互式聊天（退出自动保存、启动自动恢复）
start_chat.cmd
::    零 GPU 自测（假引擎，结果不能当真）：python -X utf8 tools\chat_daily.py --dry-run

:: 3) 日志（CPU-only）
python -X utf8 tools\inspect_logs.py --verify
python -X utf8 tools\inspect_logs.py --summary
python -X utf8 tools\inspect_logs.py --tail 30

:: 4) CPU 单测（离线假引擎）
python -X utf8 tools\test_chat_daily_cpu.py
python -X utf8 tools\test_rollover_cpu.py

:: 5) 一键复算/自检
bash verify.sh
```

交互内命令：`/remember <文本>`、`/memories`、`/forget <id>|all`、`/ask <问题>`、`/save`、`/load`、`/status`、`/log [status|mode …|purge …]`、`/quit`。

## 5 文档与"以什么为准"

- **入口**：[`docs/README.md`](docs/README.md) → [`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md) → [`docs/CODE-MAP.md`](docs/CODE-MAP.md)（代码地图；若未就位以 `tools/` 源码为准）。
- **证据/坐标**：[`docs/_work/ANCHORS-CURRENT.md`](docs/_work/ANCHORS-CURRENT.md)（引 sha 前必查）、[`docs/_work/ARTIFACTS-KEY.md`](docs/_work/ARTIFACTS-KEY.md)（产物清单）、[`docs/_work/INDEX.md`](docs/_work/INDEX.md)（文档索引）。
- **历史**：`docs/archive/PROGRESS-AND-ROADMAP-ARCHIVE.md`（319 KB 长文，原根 `PROGRESS-AND-ROADMAP.md`）、`docs/archive/HANDOFF-ARCHIVE.md`、`docs/archive/PROJECT-STATE-ARCHIVE.md`；根目录旧 `FEATURES.md` 为历史台账（现行能力见 `docs/FEATURES.md`）。完整映射见 [`docs/ARCHIVE-INDEX.md`](docs/ARCHIVE-INDEX.md)。

> **准绳**：**代码 + 冻结产物 > 文档**。文档与代码/产物冲突时，以 `tools/` 源码和 `kvmem/m2_visibility/m5/out/*` 冻结件为准；文档只做导航与解释。

## 7 文档曾经错在哪、现在以什么为准（重要）

过去文档最大的问题是**"用文档写代码"**：把旧结论、目标值、实现选择写成了已验证事实。已确证 12 类问题与整改见 **[`docs/DOC-AUDIT.md`](docs/DOC-AUDIT.md)**，摘要：

| 类型 | 实例 | 现在怎么办 |
|---|---|---|
| 装置可用被写成判据已验证 | 旧 README「36 层已验收」 | 能力宣称必须带两率+CI+数据集 sha |
| 目标值被写成已验证值 | 「8.0 GiB 是安全线」「记忆 6 条」 | 写"目标/实测"两个数；实测 8.04–8.58，fuse 8.6 |
| 冻结只登记不控写 | 冻结后仍写盘、0 字节事故 | 只读位 + 原子写 + 唯一一次解冻授权 |
| 状态词吞掉分量 | b6「未接上」掩盖 FP 18.84% 越线 | 状态词与可测分量并列 |
| 实现选择写成制度 | A3「主读数=A」 | A4/A3-V2：双读并列、取较差档 |

**正确路径**（研究/产品/数据三层）见 **[`docs/ROADMAP.md`](docs/ROADMAP.md)**；研究结论见 **[`docs/RESEARCH-RESULTS.md`](docs/RESEARCH-RESULTS.md)**。一句话：**代码 + 冻结产物 > 文档**；文档只导航，冲突以 `tools/` 与 `kvmem/m2_visibility/m5/out/*` 冻结件为准。

## 8 已知边界（先看，再判断能不能用）

- **单用户、本机、默认离线、无鉴权、无安全审计、输入不净化**；服务只绑回环；**联网仅限** `tools/web_lookup.py` 的只读 Bing 检索（无登录/无写/无脚本；失败回退"不知道"）。
- **显存余量小**：16k+34 层峰 ≈8.0–8.2 GiB（fuse 8.6），不宜与其它 GPU 任务并发。
- **记忆有上限**：库 ≤200 条、同时挂载 ≤6 块、记忆区 7,680 token；不是"无限记忆"。
- **长回答**：单次实测 328 字/23.45 s；多次分布仍待补测。
- **QQ 接入**：安装位置/启动顺序见 `docs/QQ-SETUP.md`（NapCat 隔离实例在 `third_party/`，bridge 8766，先起 8765 助手再起 bridge 再 `napcat.bat` 扫码）；协议细节见 `docs/QQ-BRIDGE.md`；依赖第三方协议端，**只用小号、有封号风险**。
- **研究线**：判据在当前设计下不可达标（见 §2）；不要把产品可用性当作接地能力证明。
- **拒答行为（v1.2 修复）**：问候/能力类（你好/谢谢/再见/你是谁/你能做什么/帮助）走**确定性回复、不调模型**；**无记忆的个人具体事实 = 固定拒答**（`refused=true`）——「我明天要去哪里出差？」不会再被旧上下文误答；**对话内追问仍可答**（`tools/evidence.py::dialogue_evidence` 只认 bigram/实体，不认单字 `u:` token；回归 `tools/test_refusal_cpu.py` 13 checks）。
- **自动记忆（v1.3，静默）**：你陈述"我的事实"会自动写入长期记忆，**不再回复"已记住（id=N）"**、只自然接话；撤销用 `/forget`（/forget all 清空）；`/auto` 开关**预留未实现**（见 `docs/USER-GUIDE-C.md` §4.2）。
- **只读联网（v1.3）**：时间敏感/需查证问题先查 Bing 再答，答案带 **`（来源：Bing 检索）`**；模型不得自称能联网；问"能联网吗"会明确说不能自己联网（`docs/USER-GUIDE-C.md` §4.3）。
- **拒答文案（v1.3 更新）**：「记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。」——不再用"对话历史提过"放行。

---

*发布口径：GitHub 上可只发布本 README；`docs/` 与证据仅本地/full 分支，不随 `main` 发布。*