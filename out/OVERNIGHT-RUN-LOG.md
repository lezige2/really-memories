# 通宵运行日志（D：记录 / 监控 / 交接）· 2026-10-29 22:31 → 2026-10-30 08:00

> ## 🔴 断电倒计时横幅（2026-10-29 23:21 起生效，取代此前所有"缓办"口径）
>
> **宿舍 08:00 断电。07:30 前所有流程必须跑完并落盘；07:30 之后禁止任何新实验（含"再跑一次看看"）。**
> 时间线以 **§0.0** 为准；任何"晚一点再跑""明早再说"的提案一律按**不可行**处理。
>
> **倒计时（D 每轮更新）**：23:22 → **距 07:30 封盘 T-8h08m**，**距 08:00 断电 T-8h38m**。
> **下一硬点**：**23:35 数据 v2 截止（T-13min）→ 未到即 fallback**。

> **角色**：D（文档 + 监控）。**性质**：只读观察 + 记录。**不跑 GPU、不改代码、不 commit、不 push、不切默认、不连远程执行命令、不启停服务**。
> **时间口径**：本机 +08:00（Asia/Shanghai）。用户休息至 **2026-10-30 08:00**；期间 A/B/C/E 继续，D 每 3–5 轮追加"交接摘要"。
> **本文件是增量日志**：不改写既有文档；冲突时以 `out/ROUND1-HANDOVER.md` §2 与 `out/FINAL-HANDOFF-2026-10-29.md` 的实测权威为准。

---

## 0.0 ⏱ 断电时间线（硬约束；23:21 A 下达，取代 §5.1 原 E1/E2 时刻）

| 时刻 | 事项 | 硬判据 / 失败处理 | 状态（23:22） |
|---|---|---|---|
| **23:35** | **数据 v2 硬截止** | 715 行 + 负例 ≥30%（215/715 = 30.07%）+ 逐行 `should_trigger` + `sft_data_gate.py` exit 0。**未到 → 启用 fallback**：v1 600 行 + C7 增量补丁拼装，产物与报告**必须标注"未达 v2 规格"**，不得当 v2 引用 | **未到**（T-13min） |
| **23:45** | **B 100 锚交付** | 100 条、sha 冻、与训练集不重叠。**来不及 → n=40**：文件名与报告显式标 `n40`，结论按 40 条口径出并写清置信区间 | 未到 |
| **00:15** | **训 / 不训结论** | 四齐才训：①数据冻结（v2 或 fallback）②B 锚（100 或 n40）③非作者 simulator ④用户授权。**缺一 → 不训**，窗口转"评测 + 文档" | 未到 |
| **00:30** | **开训（若判训）** | A10 起 job；job 前后 `nvidia-smi`/进程/出站快照 + 脚本与数据 sha 预登记 | 未到 |
| **02:00** | **adapter 产出** | adapter sha + 训练日志/loss/NaN；未出即按"训练失败"记录，**不追加超时** | 未到 |
| **02:00–04:00** | **评测** | 金标 + 对抗 + 回归；逐条配对，禁虚报 | 未到 |
| **04:00–07:30** | **证据 / 文档 / commit / 冻结** | 分批 commit（**不 push**）、sha 清单、08:00 交接报告 | 未到 |
| **07:30** | **封盘：禁止新实验** | 只允许收尾写盘与报告；任何新跑批/新训练 = **RED** | 未到 |

**降级项（不占训练窗口）**：**TTS**（本轮只保留 CPU 规格，不实现）、**40k 压测**、**E2E 集成**——一律降级，不得挤占 00:30–02:00 训练与 02:00–04:00 评测。

---

## 0 当前状态（最新快照：2026-10-29 23:22）

| 项 | 值 |
|---|---|
| 日志创建 | 2026-10-29 22:31（首轮 22:31–22:38；**最新快照 23:24**） |
| 仓库 HEAD | `c9e3956` `fix(verify): repair prompt 中性化（仅 query+answer，零 KV/hint/time）` |
| 分支/远端 | `main`，**ahead origin/main = 27**，**未 push** |
| 工作区 | modified **2**（`out/FINAL-BASE-EXTRA-NEXT.json`、`out/ROUND1-PREREG.md`）；untracked **520+** |
| out/ 规模 | 630+ 项（含 autonomy600 整包） |
| 产品模型 | `D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf`，8,988,110,976 B，sha `e47ad95d…`（未切默认） |
| 服务 8765 | **单实例存活** PID **3872**（22:35:59 启动，v2 中性 repair c9e3956）；`/status` 200，spec sha16 `694ebbad136efbec`；22:46 复核仍**单**监听 |
| 产品库 memories | **20 ✓（22:56 已回稳）**；轨迹 20（22:36）→21（22:41）→22（22:46 并发注入）→**20**（22:56，`/status` 与 sqlite 双确认，`memory_source` ids 1–20） |
| 在跑任务 | **无（22:56 全部结束）**。本轮 V2b 重跑产物：EXTRA **19/20=95%**（22:45:40，fail L07 邮箱）→ MT20 **18/20=90%**（22:54:38，fail 编造×2）→ REPAIR-PROBE 22:55（L09 银行卡 8899 pass，`after.memories=20`） |
| A10 训练口径 | **已合并裁决**：`A10-TRAINING-DECISION-2026-10-29.md`（用户 22:28 授权），取代 `A10-USE-DECISION` 的"不做任何训练"；关系**不再训第三次**，自主性 SFT **允许**（须 G1–G12 + B 100 锚 + 非作者 simulator） |
| 数据 | **v2 已落盘（23:22–23:23，715 行）**：train 572 / dev 72 / test 71；负例 215（30.07%）；逐行 `should_trigger`（true 500 / false 215）+ `trigger_reason`；`GATE-v2.json` exit 0（详见 §5.2B）。v1（600 行）保留为历史 |
| K2 开关 | `--k2-family` **默认 off**（`tools/chat_service.py:597`），当前进程未显式开启 |
| Verifier | 模块 `tools/answer_verifier.py`（22:38 实测 import OK）；**默认 v1**，v2 需 `VERIFIER_VERSION=v2` |
| `tools/chat_service.py` | sha16 `6377FCDBE50EC78C`（= HEAD c9e3956 中性 repair 版） |
| GPU 可查性 | bash 无 `nvidia-smi`；本会话**未做 GPU 查询**（不跑 GPU 口径） |
| A10 远程 | 本机 key 被拒（password-only），**不可核实**；按"零远程动作"记录 |

### 0.1 受审文档 sha16（本轮读入的 6 份 + 关键代码）

| 文件 | sha256 前 16 |
|---|---|
| `out/PROJECT-DRIFT-A-MEMO.md` | `8747219EE190A5AF` |
| `out/AUTONOMY-TRAIN-A-MEMO.md` | `16987068E5F8FEE4` |
| `out/SFT-AUTONOMY-DATA-SPEC.md` | `B6A3BA192661D345` |
| `out/SCALE-40K-SPEC.md` | `14FEA26CACF2F5B7` |
| `out/A10-TRAINING-DECISION-2026-10-29.md`（新增，裁定） | `D19047D998CBB131` |
| `out/AUTONOMY-TRIGGER-SPEC.md`（新增，规格 v1） | `C22C3B68D919C8AD` |
| `tools/chat_service.py` | `6377FCDBE50EC78C` |
| `out/sft_data_gate.py` | `2F4C94B99B304BC0` |

---

## 1 目标（本轮通宵窗口）

1. **KV-only 主线继续**：K2（同族只留最新，默认 off）→ K3′ 挂载顺序 → K4 块内属性增强 → K6 topk，**不改 prompt、不训全量 SFT**。
2. **autonomy 数据重建**：`out/autonomy600/{train,dev,test}.jsonl` + manifest，过 G1–G12 ≥90%（v3 基线仅 5.33%）。
3. **B 的锚点/评审交付**：`out/autonomy600/B-ANCHOR-100.jsonl`（B 独立锚点集）。
4. **40k 压测**（CPU 优先）：`kvmem/scale40k/` 独立库，不碰真实 `chat.db`。
5. **证据链可审计**：E 分批 commit（**不 push**）。
6. **用户 08:00 回来时**：一份可判定的状态 + 红线清单 + 待裁决项，**不需要用户重新考古**。

---

## 2 A–E 分工（据 `PROJECT-DRIFT` / `AUTONOMY-TRAIN` / `A10-USE-DECISION` / `ROUND1-HANDOVER` 归纳）

| 角色 | 定位 | 本轮职责 | 红线 |
|---|---|---|---|
| **A** | 提案 + 决策 + GPU/训练侧 | K2/K3′/K4/K6 实验设计；autonomy 数据规格与训练提案；A10 用法 | 不切默认、不 push；训练类只标 research-only；无触发器不做 autonomy 训练 |
| **B** | 对抗评审 + 机械门 + 独立锚点 | 反驳提案；G1–G12 门；`B-ANCHOR-100.jsonl`；K2 验收夹具口径 | 门禁不得放水；夹具须冻结 sha；"不可判定"不得记阴性 |
| **C** | 执行 + 评测 + 取证 | 8765 服务与评测跑批；scale40k；数据 build；证据落盘 | 评测前须冻结代码（HEAD 明确）；禁止在污染库/影子服务上出数 |
| **D** | 文档 + 监控 + 交接（本角色） | 本日志；只读快照；RED 上报；08:00 交接 | 不跑 GPU、不改代码、不 commit、不启停服务 |
| **E** | 本地 git / 提交 / 审计 | 分批 commit（**不 push**）；盘面与哈希核对 | 不 push；不覆盖历史未入库件；不删证据 |

---

## 3 红线（命中即 **RED** + 立即上报，不等整轮）

1. **跳过 B 评审**：K2/K4/verifier/训练类变更未经 B 反驳即进评测或产品路径。
2. **未冻结代码就评测**：工作区有未提交的 `tools/*.py`/`kvmem/*.py` 变更仍出评测数字（数字不可归因）。
3. **真实记忆上 A10**：把 `kvmem/daily/chat.db` 或真实记忆原文传到远程。
4. **切默认**：改默认模型 / 改 `start_service*.cmd` 的 `--model` / 让默认脚本落到 DeepSeek-R1。
5. **push**：任何 `git push`（含 force）。

补充口径（沿用既有裁定）：**用裸 `start_service.cmd` 跑验收**（会静默落到 DeepSeek-R1）视同 R4 级别的作废事故；**ADAPTER 合并进产品 / 进产品路径**视同 R4。

**Prompt invariant 适用范围（22:41 裁定后澄清，重要）**：
- **产品日常使用**：严格 KV-only——记忆走 KV 块，**不靠 prompt/提示词拼接**；此条不变。
- **训练/研究阶段**：允许记忆文本进 prompt（用户 22:28 原话："prompt 基线只要在落地后的日常使用中不在项目内就行，训练阶段无所谓"）。
- 因此：**训练期出现 prompt 形态的记忆输入 ≠ 红线**；但**产品路径引入 prompt 记忆 / 用 prompt 基线数字充当产品能力**＝红线（R4 级）。

**TTS 输出通道的边界（D10，见 §6.1）**：TTS 属**已授权的新增输出通道**，但仅在"默认关闭 + 只播已生成回答 + 不播块原文/敏感项 + QQ 语音逐次显式开启 + 不占 A10"条件下成立。**注意**：`AUTONOMY-TRAIN-A-MEMO` §3 的"只记录、不发送"红线仍然有效——autonomy 的 D 类消息**不得**借 TTS/QQ 通道变成真实主动发送。

---

## 4 RED 事件记录

### RED-01 · 8765 双监听"影子服务"（2026-10-29 22:18–22:28）— **已处置，数字作废**

| 项 | 内容 |
|---|---|
| 现象 | `127.0.0.1:8765` 同时有两个 LISTENING：**PID 344**（21:34:53 启动，旧代码）与 **PID 13184**（22:18:14 启动，新 v2） |
| 实际接单 | **PID 344（旧代码）**；PID 13184 从未接单（工作集仅 ~155 MB，模型未加载） |
| 根因 | 端口未释放即重启，旧进程未退出；Windows 允许双绑，请求落到先绑者 |
| 影响范围 | **作废**：`KVC-V2b-81`（81/81）、`KVC-K2d-81`、`KVC-K2d-EXTRA`、`KVC-K2d-MT20`（22:26–22:27 三件）——均由旧代码产出，**标 invalid/provisional，不得引用** |
| 不受影响 | K2c / V2（21:31 之前） |
| 处置 | A 已 kill PID 344 / 13184；唯一干净进程 **PID 3872**（22:35:59 启动，v2 中性 repair `c9e3956`，`/status` 正常，memories=20） |
| 残留清理 | 评测注入的 **id21** 已 forget，`after=20`，证据 `out/KVC-V2b-CLEANUP-EVIDENCE.json`（70 B） |
| 重跑状态 | **大部分已重出（干净 PID 3872）**：EXTRA **19/20=95%**（22:45:40，`KVC-V2b-EXTRA.json` sha256 `079025359be48e2a…`，fail 仅 L07 邮箱）；MT20 **18/20=90%**（22:54:38，fail 形态"编造×2"）；REPAIR-PROBE 22:55（L09 银行卡 8899 pass）。**V2b-81 / K2d 三件仍待重跑**，重跑前须登记 HEAD/sha —— 这四件此前的旧代码数字继续标 invalid，不得混用 |
| D 观察 | 首轮快照（22:31）即已捕获双 PID 同端口 + 双实例同命令行（长度均 354，`--k2-family` 后为空值），与 A 的判断一致；**此类事故对"服务是否唯一"是静默的**，必须在每次跑批前显式核验 PID 唯一性 |

**衍生监控项（新增，长期）**：每轮快照必须记录 `netstat -ano | grep :8765` 的**监听 PID 集合**，非单元素即 RED；并在跑批开始前后各记一次 `/status` 的 `memories` 与 `spec_sha16`。

---

## 5 待办 / 监控清单（每轮更新）

| # | 监控项 | 判据 | 当前状态（23:29） |
|---|---|---|---|
| M1 | 数据落盘 + **冻结** | FREEZE 清单存在且 sha 与磁盘 MATCH | **v3 已冻结（00:14）**：715 行（572/72/71），`<SILENCE>` 恰落负例 160/28/27；**`out/autonomy600_v3/FREEZE-v3.json`**（sha16 `45EAF986…`，三文件 sha 全部 MATCH）；v2 保留但 run1 判 exploratory-data-bug；v1 非权威 |
| M2 | GATE 通过率 | exit 0 / real_fail=0 / known_fp 口径明确 | **v3 三 split 门禁齐全（00:13）**：train 572/**0**/fp160、dev 72/**0**/fp28、test 71/**0**/fp27；pass_rate_real 全 1.0；**known_fp 合计 215 = 负例数**（每条 `<SILENCE>` 被 G2/G8 计 known_fp，一一对应）→ **AMBER-lite ① 关闭**；v2 复算见 §5.2B |
| M3 | 负例比 | 总 ≥30% 且每 split ≥25% | **v2 = 30.07%（215/715）**；train 27.97%（160/572）/ dev 38.89%（28/72）/ test 38.03%（27/71）→ **全部达标，不再依赖豁免** |
| M4 | `B-ANCHOR-100.jsonl` | 100 条、sha 绑 FREEZE-v2、与 v2 训练集不重叠、分歧 <10% | **已交付（23:31）并 D 复核 MATCH**：100 行 / 21,215 B / sha256 `047c5ccfd76f8e43…`；分层 A13·B13·C20·D32·N22，split train81/dev8/test11；触发分歧 **0/100**（但 `b_should_trigger` 与 category **同构** → 非独立验证）；内容层 **5/100 无据或矛盾，全 D 类（32 条中 15.6%）、全 S2、无 S1** → B 结论 **可训（附条件）** |
| M5 | A10 训练日志 / adapter sha | 四齐才训：v2 冻结 ✓ + B 锚 ✓ + simulator + 授权 ✓ | **已授权、未开训**；**三缺一：仅缺 simulator 明示**（其余三项已满足） |
| M6 | 服务 8765 存活 | 单 PID + `/status` 200 + memories=20 | **OK**（PID 3872 单监听，22:46 复核仍单） |
| M7 | K2 开关现状 | 默认 off；开启须登记 flag+sha | **off** |
| M8 | Verifier 存活 | import OK + 默认 v1；v2 需显式 env | **OK**（v1 默认，`VERIFIER_VERSION` 控制） |
| M9 | 产品库未被污染 | `memory_source=20`（跑批间隙复核） | **20 ✓（22:56 已回稳）**；轨迹 20→21→22（跑批注入）→20（跑毕清理生效，`/status` + sqlite 双确认） |
| M10 | git 卫生 | 无 push；代码改动须 commit 后评测 | ahead 27、untracked **513**、modified 2（**均未 push**；modified 非代码），HEAD 仍 `c9e3956` |

### 5.1 升级规则（RED / AMBER；23:21 起时刻一律改按 **§0.0 断电时间线**）

> AMBER ≠ RED：不是违规，而是**关键路径阻塞/质量待裁**。记 AMBER 时写清"阻塞项 + 后果 + 兜底"，并在 08:00 报告单列。

| # | 触发条件 | 处置（D 的动作） | 当前状态（23:29） |
|---|---|---|---|
| **E1** | ~~23:10~~ → **23:35** 仍无 v2（715 行 / 负例 ≥30% / `should_trigger`） | 记 **AMBER-关键路径阻塞**，写"**启用 fallback**"；**D 不自己造数据** | **不触发**：v2 于 **23:22–23:23 落盘**（早 12 分钟），已核已冻（FREEZE-v2） |
| **E2** | ~~v1+30min~~ → ~~23:45~~ **23:50** 仍无 `B-ANCHOR-100.jsonl` | 记 **AMBER**，并**催 B**；允许 **n=40** 降级（文件名/报告标 `n40`） | **不触发**：锚 **23:31 交付**（早于 23:50），100 行、sha 实测 MATCH |
| **E2′**（新增，A 23:24 指示） | B 锚与 v2 口径**分歧 ≥10%** | **不开训**（分歧即硬门失败），记 AMBER-口径分歧 | **不触发**：分歧 **0/100**；**但须标注"同构"**——`b_should_trigger` 与 category 完全一致（78 true / 22 false），不构成独立验证 |
| **E3**（沿用） | 跑批结束 `memories != 20` | 记 AMBER（污染库），该批数字标 conditionally-valid | **不触发**：23:29 复核仍 20 ✓ |
| **E4**（沿用） | 8765 监听 PID ≠ 1 个 | **RED**（RED-01 同类） | 1 个 ✓（PID 3872） |
| **E5**（新增，断电） | **07:30 后**出现任何新跑批 / 新训练 / 新实验 | **RED**（封盘违规）；登记是谁、跑了什么、是否污染冻结产物 | 未到 |
| **E6**（新增，倒排） | **00:15** 未出"训/不训"结论，或 **00:30** 未开训 | 记 **AMBER-窗口流失**，按"不训"转评测+文档，**不得拖到 02:00 后补训** | 未到 |
| **E7**（新增，降级） | TTS / 40k / E2E 占用 00:30–04:00 的训练/评测窗口 | 记 **AMBER-挤占**，要求让出窗口 | 未到 |
| **E8**（新增，可证性） | **04:00** 前仍未拿到**远程 train.jsonl 的 sha256** | 记 **AMBER-不可证**（无法证明"训的是冻结 v2"） | **✅ 已关闭（23:53）**：远程 `/root/work/autonomy/` 三文件 sha256 实测与 FREEZE-v2 **逐一一致**（train `9ae27f59…` / dev `15021661…` / test `8d820865…`）→ 绑定成立 |
| **E9**（新增，sim 纪律） | 训练开始后 B 改动 `AUTONOMY-SIM-CASES.jsonl`；或 pred 非 C 从 adapter 生成 | **RED**（验收不可信）：cases sha 失配即作废验收；人填 pred = 伪造证据 | 未触发：cases 已于 23:42 冻结（`2AD36C18…`） |
| **E10**（新增，监督信号） | 训练数据的**标签形态**与目标行为不一致（如"不触发"却给普通接话、目标输出从未出现在 assistant 侧） | 记 **RED 候选（数据标签缺陷）**：该臂结果判 **exploratory-data-bug、不交付**；修数据→重跑门禁→重训，**不得靠调参掩盖** | **已触发（00:05）**：v2 全部 **215/215** 条 `should_trigger=false` 的 assistant **都不是 `<SILENCE>`**，而是普通接话 → 模型学不到"闭嘴" |

### 5.2B `out/autonomy600/` **v2** 审计（D 只读核对，23:23–23:25）

**结论：v2 在 23:35 硬截止前 12 分钟落盘，E1 不触发；规格项大体达标。**

| 项 | v2 实测 | 判据 | 结果 |
|---|---|---|---|
| 规模 | **715 行**（train 572 / dev 72 / test 71） | 715 | ✓ |
| 负例比 | **215/715 = 30.07%**；分 split train 27.97%（160/572）、dev 38.89%（28/72）、test 38.03%（27/71） | ≥30% 总；每 split ≥25% | ✓ **不再依赖豁免** |
| 逐行 trigger | **有**：`should_trigger`（true **500** / false **215**）+ `trigger_reason` | v2 必须逐行可判 | ✓（v1 的 G7 空跑问题已修） |
| 类目 | A120 / B100 / C120 / D160 / N215（manifest-v2） | G10 配额 | 见下（门记 PARTIAL） |
| 门禁 | `GATE-v2.json`：715 行、`real_fail=0`、`known_fp=0`、`pass_rate=1.0`、**exit 0**；G1–G13 仅 G2 命中 4 行（known_fp：短句无谓语），其余 0 | exit 0 | ✓ |
| G10 状态 | **`PARTIAL（不标 pass）`**：门只验证 A189≥100、C120≥60，**B/D 记 N/A**（classify() 仍认不出 B/D）；行级 (system,user) 唯一性 0 命中 | — | **AMBER-lite：结论须写"配额按 manifest 声明，门类目不可用"** |
| 留出 | train 族 k01–k16 / dev k17–k20 / test k21–k24；family+template disjoint（沿用 v1 口径） | 三重留出 | ✓（待 v2 manifest 字段逐项复核） |
| sha | 见 §5.2C（v2 指纹表） | 冻结前登记 | 待冻结 |

**与 v1 的差异（重要）**：v1 的 600 行**无** `should_trigger`、负例靠豁免、G7 逐行不可验；v2 三项全修。→ **B 的 100 锚现在可以对齐 `should_trigger` 了**（此前推迟的理由消失）。

**仍缺**：①**显式 freeze/sha 清单文件**（v2 目录内仍无 SHA256SUMS）；②G10 的 B/D 配额仍需"manifest 声明"背书而非门验证。

### 5.2C v2 冻结指纹（FREEZE-v2.json，23:27 建，D 核验）

> 清单：`out/autonomy600/FREEZE-v2.json`（sha16 `7FEE4DD9311D9F65`）。**已用 sha256 逐文件与磁盘比对，五件全 MATCH**；manifest-v2 内声明的 train/dev/test sha 亦与实测一致（证明清单未事后改写）。

| 文件 | 字节 | 行 | sha256 |
|---|---:|---:|---|
| `train.jsonl` | 677,819 | 572 | `9ae27f59548a258cae046f141eabd246d9fc4932a942b14f11135ce8da893043` |
| `dev.jsonl` | 84,198 | 72 | `150216614430aa39284495e13afdb451427be4706cb1055a74b41816b6043a16` |
| `test.jsonl` | 83,176 | 71 | `8d820865fa91a36e24992348a2751a9752131003cad0adcaaa728e3b462f54e5` |
| `manifest-v2.json` | 228,881 | — | `3ac4441021767d7f3ab975612c7b33db5ddbb8242ee2b9232fac215b74cff93a` |
| `GATE-v2.json` | 4,795 | — | `47205a2801e86a5be6a087f611748e0d9d2a5f1b245fd6718db8c62bf4dcf2a5` |

**冻结规则（已写入 JSON 的 usage_rules）**：训练只能用 `train.jsonl`；任何文件被改写 → sha 失配 → 冻结作废、须重跑门禁；B 锚须绑定本清单 sha，**23:50 未交或与 v2 分歧 ≥10% → 不开训**。

### 5.2A `out/autonomy600/` **v1** 审计（历史留档；v1 已被 v2 取代，仅存指纹）

> ⚠ v1 **不用于训练**，以下仅作回溯对照。

**已确认（正面）**
- 600 行 = train 480 + dev 60 + test 60；包内含 `README.md`、`SAMPLES.md`、`manifest.json`、`GATE.json`、分 split gate 报告（22:47–22:48 定稿）。
- **族/模板双留出**：train 16 族（k01–k16）/ dev 4 族（k17–k20）/ test 4 族（k21–k24），`family_disjoint` 与 `template_disjoint` 全 True；负例场景池也按 split 切（34/8/8）。
- 行形态统一：`system`（时间行 + 记忆块 + `上次聊到` + SYSTEM_POLICY 逐字，`policy_sha16=92e92217a74eb81e`）、`user`（陈述或括号场景，如"（你翻着课本，书签停在上一课）"）、`assistant`；**无空 user、无指令式 input**（G1=0）。
- `GATE.json`（`schema=autonomy600_gate_v1`，22:47 重生成）：rows 600、`real_fail_rows=0`、`known_fp_rows=0`、`pass_rate=1.0`、`gate_exit_code=0`；G1–G13 逐行 0 fail。

**口径说明（不是缺陷，但**引用时必须带口径**，否则任一方都误导）**
- **A. GATE 内部自身给出两套计数且都成立**：`g1_g12.G10.dataset_level` 写"A 类 71<100 / B 类 0<80 / D 类 0<60"（来自门内 `classify()` 启发式：它把"记忆块+问句"一律判 C，把 D 判成"user 含请/主动"——正是本 spec 明令禁止的指令式输入，故 B/D **结构性不可识别**）；同一文件的 `quota_by_manifest` 又写 A120/B100/C120/D160/N100 **全部 ok**，并注明"不经门内 classify 启发式"。→ **"GATE 100%" 与 "G10 命中 3" 同时成立**；对外只能说"逐行门 0 fail；配额以 manifest 声明为准（门类目不可用）"。
- **B. 负例比 16.7% 走的是豁免分支**：`negative={count:100, silence:50, irrelevant:50}`；`quota_by_manifest.neg_ratio` 的判据写"**>=0.30 或 100 条全为沉默/无关场景**"，故判 ok。但 `AUTONOMY-TRIGGER-SPEC` §4 原文是"负例 ≥30% 且由非作者标注"——**豁免是门自定的，需 B 认账**。
- **C. 逐行无 `meta`**：600 行只有 `{"messages":[...]}` 一个键；`README` 明示"训练加载器只读 messages，类别/族/来源/负例子类见 `manifest.json`"。→ spec G7"D 类须带 meta"**在逐行层面不可验**，G7 `n=0` 属"无法命中"而非通过。
- **D. 尚无 freeze/sha 声明**：数据 22:44 首版 → **22:47 被重写**（首版 train 529,238 B / GATE 11,772 B → 现 529,532 B / 4,842 B），sha 已变且**目录内无 SHA256SUMS/freeze 文件**。**开训前必须落 freeze**，否则 09:45 训练的数据不可复现。
- **E. 抽检 D 类一条内容自相矛盾**：user"（你翻着课本，书签停在上一课）"→ assistant"**八点半，周四的课别忘了，八点。**"（同句 8:30/8:00 冲突，且记忆里的课是 20:00）。建议 B 的 100 锚点把"时间自洽"列为判据。

**当前 sha16（v1 · 22:47 定稿版；⚠ 这是 v1，**不冻结**，待 v2 覆盖/并存）**

| 文件 | 字节 | sha16 |
|---|---:|---|
| `train.jsonl` | 529,532 | `F073C2B83B889DFF` |
| `dev.jsonl` | 65,358 | `54909471954131C0` |
| `test.jsonl` | 65,340 | `9860F02DB7E652E2` |
| `manifest.json` | 128,839 | `05298C5912265481` |
| `GATE.json` | 4,842 | `85C30394A3D70A2E` |

> **版本策略（23:05 A 指示）**：v1 的 600 行**不冻结、不作训练依据**；C7 正补 **115 条负例 + `should_trigger` 标注 → v2（715 行、负例 30.1%）**。v2 落盘后：①重跑 `sft_data_gate.py`；②按 v2 生成 sha 清单并冻结；③B 的 100 锚点对齐 `trigger` 字段后再计时。**上表 sha 仅作 v1 存档指纹。**

---

## 6 已知风险（未到 RED，持续观察）

| # | 风险 | 说明 | 触发升级条件 |
|---|---|---|---|
| R1 | ~~A10 租期 vs "不训练"决策冲突~~ → **已合并裁决**（文件自标 22:45；D 22:41 读入收口） | 授权见 `A10-TRAINING-DECISION-2026-10-29.md`（sha16 `D19047D9…`）：用户 22:28 授权训练，**取代** `A10-USE-DECISION` §2.1 的"不做任何训练"，其余条款不变。关系 LoRA **不再训第三次**；自主性 SFT **允许**（前置：G1–G12 数据门 + B 的 100 锚 + 非作者 simulator）；P 臂 68.3% **不构成 DPO 授权**；RL/GRPO 不做 | 偏离该裁决（如训练期用真实记忆、adapter 进产品、跳过 100 锚）→ RED |
| R2 | **影子服务复发** | 端口未释放即重启已发生一次（RED-01） | 双 LISTENING |
| R3 | **评测污染库** | extra/heldout 会向 `daily/chat.db` 注入（id21 残留已清）；`memories!=20` 时所有数字可疑 | memories≠20 |
| R4 | **未入库证据 513 项 / ahead 27** | 不影响运行，但"可审计"要求 E 分批 commit；**绝不 push** | 出现 push 或覆盖未入库件 |
| R5 | **A10 不可核实** | key 被拒、密码不可见；远程状态只能按遗书记录，不能声称"已核实" | 用户提供凭据前，任何"远程已..."表述视为虚报 |
| R6 | ~~关系 14B LoRA 定性未决~~ → **已裁（research-only / do-not-deploy）** | `A10-TRAINING-DECISION` §2：run2/run3 已跑、安全净增益 **−2**、**不再训第三次**；结果不得引用为"训练有效"或产品能力 | 该结果被当作产品能力引用 → RED 级表述错误 |
| R7 | ~~autonomy 训练须先有触发器规格~~ → **spec 已交付** | `AUTONOMY-TRIGGER-SPEC.md`（sha16 `C22C3B68…`）已出：触发源（时间/事件/沉默/显式）、决策输出 `<SILENCE>` 或 ≤120 字、静默窗 23:00–07:00、频率 ≤1/天 ≤3/周、敏感项不播报、误报分级 S1 零容忍 / S2 ≤5% / S3 ≤10%、40 条 B simulator 为唯一判据、负例 ≥30%。**训练前必须存在——现已满足** | 训练仍宣称"产品级主动性"（运行时触发器未实现）→ RED 级表述错误 |
| R8 | **裸 `start_service.cmd`** | 不带 `--model` 会落到 DeepSeek-R1 常量，数字全废 | 验收用裸脚本 |

### 6.1 偏差登记（D 区 / DEVIATION REGISTER）

> 记录"与项目书宗旨不同、但**已获授权或已由 B 裁定**"的变更。**D 区条目本身不是 RED**；只有**偏离登记条件**时才升级。

#### D10 · TTS 新增输出通道（2026-10-29 23:0x，B 已裁；**非 RED**）

| 项 | 内容 |
|---|---|
| 性质 | **用户授权的新增输出通道 / 产品路径变更**（项目书原为"纯文本、本机离线、KV-only 记忆"） |
| 授权 | 用户要求"本机播放 + QQ 语音"；B 已裁定可行（登记为偏差，不否决） |
| 硬约束（B 裁定） | ①**默认关闭**、可回滚；②**不触碰记忆路径**（不读 KV、不改 prompt、不进检索链路）；③**只播模型已生成的回答，不播记忆块原文**；④号码/地址/余额**默认不播**；⑤**QQ 语音经桥 = 文本离开本机**，须**用户逐次显式开启**、一键可关；⑥**SAPI 先上（CPU）**，CosyVoice 走 CPU/独立卡，**不占 A10** |
| 用户追加口径（23:05） | **TTS 一律 CPU 推理**：SAPI 先上、CosyVoice 亦走 **CPU**（不再提"独立卡"，避免与 A10/主 GPU 争用）；**A10 与 8765 的 GPU 都不用于 TTS** |
| 依据文件 | `out/TTS-INTEGRATION-SPEC.md`（sha16 `027B9BE18BB8C1E6`，63 行） |
| D 的监控判据 | 出现以下任一即**升级为 RED**：默认开=on（开箱即播）；TTS 文本里出现记忆块原文/块 id；号码/地址/余额被播报；QQ 语音未逐次显式确认即发送；TTS 训练/推理占用 A10；无回滚开关 |
| 当前状态（23:02） | 仅**规格**存在，未实现、未接入、未占用 GPU；`QQ 语音` 尚未连线。**不构成"真实发送"红线**（因默认关闭 + 逐次显式开启） |

---

## 7 交接摘要（按轮追加；每 3–5 轮一条）

### H-00 · 2026-10-29 22:38（首轮：建日志 + 快照）

- **时间**：22:31 建日志 / 22:38 首轮快照完成。
- **产物**：`out/OVERNIGHT-RUN-LOG.md`（本文件，新建）。
- **sha**：HEAD `c9e3956`；`chat_service.py` `6377FCDBE50EC78C`；spec `694ebbad136efbec`；受审 4 文档见 §0.1。
- **异常**：**RED-01 影子服务**（已处置，V2b-81/K2d 三件作废待重跑）；`memories` 曾漂到 21，已清回 20。
- **未交付**：autonomy600 数据、B-ANCHOR-100、A10 训练（未开始，且 P 臂未过门）。
- **下一步（等 A/B/C 落盘）**：盯 M1/M2（autonomy600 + gate）、M5（A10 是否开训）、M10（是否有人 push）。

### H-01 · 2026-10-29 22:42（两条裁定级风险收口）

- **时间**：22:41 收到 A 的两项处置 / 22:42 复核并落档。
- **新产物（2 份裁定/规格，D 只记录、未改）**：
  - `out/A10-TRAINING-DECISION-2026-10-29.md`（sha16 `D19047D998CBB131`，样本 28 行）——**合并裁决**：用户 22:28 授权训练，**取代** `A10-USE-DECISION` 的"不做任何训练"；关系 LoRA 不再训第三次（安全净增益 −2，标 research-only / do-not-deploy）；**自主性 SFT 允许**（前置三件：G1–G12 数据门、B 的 100 锚、非作者 simulator）；RL/GRPO 不做；时间盒 08:00 开训 / 09:45 未启即弃 / 10:30 硬停；abort 含 OOM/NaN/门失败/真实记忆上 A10。
  - `out/AUTONOMY-TRIGGER-SPEC.md`（sha16 `C22C3B68D919C8AD`，38 行）——**触发规格 v1**：四类触发源（时间/事件/沉默/显式）、`<SILENCE>` 或 ≤120 字输出、静默窗 23:00–07:00、频率 ≤1 天/≤3 周、敏感项不播报、误报分级（S1 零容忍 / S2 ≤5% / S3 ≤10%）、40 条 B simulator 唯一判据、训练负例 ≥30% 且非作者标注、**运行时触发器未实现**。
- **结案**：R1（A10 冲突）、R6（关系 LoRA 定性）、R7（缺 spec）**三条转为"已裁定/已交付"**，均**不标 RED**；`§3` 增补 prompt invariant 适用范围（产品日常 KV-only 不变；训练期允许 prompt）。
- **sha**：HEAD `c9e3956`（未变，无新 commit）；`chat_service.py` `6377FCDBE50EC78C`；spec `694ebbad136efbec`；新文档 sha 见上。
- **异常/观察**：
  1. `out/autonomy600/` 目录 22:38 已建但**仍为空**；无 build 进程 → M1 未完成。
  2. `out/B-ANCHOR-100.jsonl` **仍不存在**（M4 未交付，且已成为 autonomy SFT 的硬前置，构成 08:00 前关键路径）。
  3. V2b-EXTRA 重跑进行中（PID 14176）；跑批期 `memories=21` 属**预期注入**，须在跑毕复核回 20，否则按 R3/M9 处置。
  4. 8765 仍**单**监听（PID 3872），RED-01 无复发。
  5. 工作区 untracked 由 505 → **513**（新增 8 项，含上述 2 文档与 V2b 重跑中间件）；**代码仍未改、未 push**。
- **下一步**：盯 M1/M2（autonomy600 + gate）→ M4（B-ANCHOR-100）→ M5（A10 开训：须四齐，缺 B 100 锚即 RED）→ M10（push）。

### H-02 · 2026-10-29 22:48（autonomy600 落盘 + 数据审计 + AMBER 规则入册）

- **时间**：22:44 数据首版落盘 → 22:47 定稿 → 22:48 审计完成。
- **产物**：`out/autonomy600/`（train 480 / dev 60 / test 60 = 600；另 `manifest.json`、`GATE.json`、`README.md`、`SAMPLES.md`、分 split gate 报告、`_gate_input_all.jsonl`）。
- **sha16（22:47 定稿版）**：train `F073C2B83B889DFF`（529,532 B）/ dev `54909471954131C0` / test `9860F02DB7E652E2` / manifest `05298C5912265481` / GATE `85C30394A3D70A2E`。HEAD 仍 `c9e3956`（**无新 commit**）。
- **GATE**：`autonomy600_gate_v1`，600 行、`real_fail_rows=0`、`known_fp=0`、`pass_rate=1.0`、退出码 0；G1–G13 逐行 0 fail（含 G13）。
- **异常/待裁（AMBER 级，已入 §5.2，非 RED）**：
  1. GATE 内 **G10 数据集级 3 条 vs `quota_by_manifest` 全 ok** 并存（B/D 在门内 classify 结构性不可识别）→ 引用"GATE 100%"必须带口径。
  2. 负例比 **16.7%**，靠门自定豁免分支（"或 100 条全为沉默/无关"）判 ok，与 `AUTONOMY-TRIGGER-SPEC` §4 的"≥30%"不一致 → 需 B 认账。
  3. 逐行**无 `meta`**（仅 `messages`），类别信息在 manifest → spec G7 逐行不可验，`G7 n=0` 属无法命中。
  4. **无 freeze/sha 文件**：22:44→22:47 数据被重写，sha 已变 → **开训前必须落 freeze**（否则 09:45 训练不可复现）。
  5. 抽检 D 类"八点半…八点"时间自相矛盾（记忆为 20:00）→ 建议 B 100 锚点加"时间自洽"。
- **跑批**：V2b-EXTRA 重跑 22:45:40 `EXIT=0`；22:46:08 起新一批（PID 3428）；22:54:38 MT20 `18/20`；22:55 REPAIR-PROBE；**22:56 全部结束，`memories` 已回 20**（`/status count=20 / total_tokens=659`，sqlite ids 1–20）→ **E3 不触发**。
- **补记（22:56）**：本轮重跑在干净 PID 3872 上有效：EXTRA 19/20（95%，fail L07 邮箱"僵硬"）、MT20 18/20（90%，fail 编造×2）、REPAIR-PROBE L09 pass（银行卡 8899，`after.memories=20`）。**注意：EXTRA 的 19/20 仍含 L07 记忆读取失败**，与 08:00 交接口径需说明"这是 KVC-V2b 臂、非产品基线 18–20/20 band"。
- **补记（23:01 → 23:05 修正）**：`out/autonomy600/` 自 22:47 起**未再变动**（train `F073C2B8…`、GATE `85C30394…` 复核一致）——但 **A 已明确 v1 不冻结**（C7 将出 v2：715 行 / 负例 30.1% / 带 `should_trigger`），故此处**不记"冻结"**，只记"v1 自 22:47 起未被改写"；freeze 与 sha 清单推迟到 v2。`memories=20` ✓、8765 单监听 ✓、HEAD `c9e3956` / ahead 27 / 0 push ✓。
- **新工作流观察（不属 KV-only 主线，仅登记）**：23:00 出现 `out/TTS-INTEGRATION-SPEC.md`（sha16 `027B9BE18BB8C1E6`，63 行）——本机扬声器 + QQ 语音，链路"14B → verifier → clean_answer → tts_sanitize → TTS"，声明「TTS 只接最终文本、不读 KV、不改 prompt、不进检索链路」「不在 TTS 层做发送」。**待 08:00 澄清**：它是否属本轮范围（会新增 ffmpeg/silk 转码与 QQ 发送面，与"autonomy 只记录不发送"的边界相邻）。
- **AMBER 规则入册（A 下达）**：E1 **23:10** 无 `autonomy600/*.jsonl` → AMBER+fallback 说明（**不触发**，22:44 已落盘）；E2 数据落盘后 **30 分钟（23:14）** 无 `B-ANCHOR-100.jsonl` → AMBER + 催 B（**计时中**）；E3 跑毕 `memories≠20` → AMBER；E4 8765 监听 ≠1 → RED（当前 1 ✓）。
- **补记（23:06，口径变更）**：①**v1 不冻结** → 新增 **E1′**（v2 715 行落盘才算冻结起点）；②**E2 推迟到 v2 落盘 +30min**，23:14 **不判 AMBER**（机制原因：v1 无 `trigger` 字段，锚点对不齐，**非 B 失职**）；③D10 追加**用户口径：TTS 一律 CPU 推理**（SAPI + CosyVoice 均 CPU，不占 A10、不占 8765 的 GPU）；④D10 的"待 08:00 澄清"项**已由 B 裁定关闭**（见 §6.1）。
- **下一步**：等 **v2 落盘**（触发 E1′/E2 计时与重跑门禁）；跑毕复核 memories；盯 M5（开训须四齐：授权✓ / v2 冻结数据 / B 100 锚 / simulator）、M10（push）。

### H-03 · 2026-10-29 23:22（🔴 断电倒排：时间线整体前移，新增封盘规则）

- **时间**：23:21 收到断电通知 / 23:22 改完并复核。
- **变更（本日志结构性修改，A 下达）**：
  1. 顶部新增 **🔴 断电横幅 + 倒计时**（23:22 → T-8h08m 至 07:30 封盘，T-8h38m 至 08:00）。
  2. 新增 **§0.0 断电时间线**（硬约束）：23:35 v2 截止 → 23:45 B 锚（可 n=40 标注）→ 00:15 训/不训结论 → 00:30 开训 → 02:00 adapter → 02:00–04:00 评测 → 04:00–07:30 证据/commit/冻结 → **07:30 封盘禁新实验**。
  3. **降级项**：TTS（仅 CPU 规格不实现）、40k、E2E —— 不占训练窗口。
  4. 规则重构：E1 时刻 **23:10→23:35**（v2 硬截止，未到即 fallback 并标"未达 v2 规格"）；E2 改为 **23:45 硬点**、允许 n=40 标注降级；**新增 E5（07:30 后新实验=RED）、E6（00:15/00:30 未动作=AMBER-窗口流失）、E7（TTS/40k/E2E 挤占窗口=AMBER）**；删除原 E1′ 独立条目（并入 E1）。
  5. M5 时间盒改为"见 §0.0"，作废原 08:00/09:45/10:30 口径。
- **sha**：HEAD `c9e3956`（无新 commit）；本日志 sha16 见文末记录；v1 数据 sha 不变（`F073C2B8…`）。
- **异常/观察（23:22）**：
  1. **v2 未出**（`out/autonomy600/` 仍是 22:47 的 v1，600 行）→ **距 23:35 硬截止仅 13 分钟**，当前迹象偏 fallback。
  2. `out/B-ANCHOR-100.jsonl` 仍不存在 → 23:45 大概率走 **n=40** 或延期，需 B 明示。
  3. 服务侧正常：8765 单监听 PID 3872；`memories=20` ✓；无跑批在跑。
  4. 仓库：HEAD `c9e3956`、ahead 27、**0 push**。
- **下一步（D 在 23:35 / 23:45 两个硬点必须被唤醒）**：判 E1（fallback 是否触发）、判 E2（锚点 n=100 或 n40），并写 H-04。

---

### H-04 · 2026-10-29 23:31（v2 落盘 + 四项核验 + 冻结；**即 A 指定"写 H-03"的内容**）

> 编号说明：H-03 已被 23:22 的"断电时间线"占用，本条为 A 口中 H-03 的实质内容，故作 H-04。

- **时间**：v2 23:22–23:23 落盘 / D 约 6 分钟完成核验 / 23:27 建 FREEZE-v2 / 23:29 复算门禁。
- **产物**：`out/autonomy600/FREEZE-v2.json`（新建，sha16 `7FEE4DD9311D9F65`）、`out/autonomy600/GATE-v2-D-RECHECK.json`（D 独立复算，2,720 B）、本日志。
- **四项核验（全 PASS）**：
  1. **行数**：715 = train **572** / dev **72** / test **71**（逐行实算，非读 manifest 自述）。
  2. **负例**：`should_trigger=false` **215 → 30.07%**；分 split train **27.97%**（160/572）、dev **38.89%**（28/72）、test **38.03%**（27/71）→ 总 ≥30% 且每 split ≥25% ✓（**v1 的豁免分支已不需要**）。
  3. **逐行字段**：jsonl 行键 = `messages` + `should_trigger` + `trigger_reason`（715/715 均有）；`manifest-v2.rows` 715 条，逐条含 `split / line / category / family / template_id / should_trigger / trigger_reason / source / anchor` ✓。
  4. **门禁复算**：`sft_data_gate.py --input _gate_input_all.jsonl --out GATE-v2-D-RECHECK.json` → **exit 0**、rows 715、**real_fail_rows=0**、`pass_rate=1.0`；G10 仅 2 条**数据集级**（"B 类 0<80 / D 类 0<60"，门内 `classify()` 认不出 B/D），**未冒充 pass**（producer `g10_status=PARTIAL`，与 D 复算一致）。
- **sha**：HEAD `c9e3956`（**无新 commit**）；五文件 sha256 见 §5.2C，且与 `manifest-v2.sha256` 声明逐条一致；`FREEZE-v2.json` = `7FEE4DD9…`。
- **v1 表述已清理**：§5.2A 标"历史留档 / 非权威 / 不用于训练"；§5.2 表头标"⚠ 不冻结"；FREEZE-v2 `supersedes` 写明 v1 作废。
- **异常/观察（23:31）**：
  1. 类目口径仍分裂：门 classify 计 **A189 / unknown406 / C120**，manifest 计 **A120/B100/C120/D160/N215** → 引用必须写"配额按 manifest，门类目不可用"。
  2. `out/B-ANCHOR-100.jsonl` **23:31 已交付**（100 行，sha256 `047c5ccfd76f8e43…`，D 实测 MATCH）→ **E2 不触发**；详见下方"锚点"段。
  3. 服务：8765 单监听 PID 3872；`memories=20` ✓；无跑批。
  4. 仓库：ahead 27、**0 push**。
- **锚点（B，23:31 交付；D 23:36–23:37 复核）**：
  - 文件 100 行 / 21,215 B / sha256 **`047c5ccfd76f8e43fbe394142e4a3ddf3ad91b2e5ec96f2ee489c5bd4f539970`**（与 A 转述的 `047c5ccf…` 一致）；字段 `id/split/line/family/category/b_should_trigger/b_content_ok/severity/note`。
  - 分层：A13 / B13 / C20 / **D32** / N22；split train81 / dev8 / test11。
  - **触发层**：分歧 **0/100**。⚠ **但 `b_should_trigger` 与 category 完全同构**（A/B/C/D 全 true 共 78，N 全 false 共 22）→ **该 0 分歧不是独立验证**，只说明 B 与本数据集映射一致；引用时不得写成"锚点独立验证通过"。
  - **内容层**：`b_content_ok=false` **5 条**（5%），**全部 D 类**（32 条中 **15.6%**），严重度 S2×5（S3×95，**S1=0**）——与"无据/自相矛盾"描述一致。
  - **B 结论：可训（附条件）**；条件 = 训后 simulator 对这 5 条做内容专项复核；锚 sha 绑 FREEZE-v2。
- **FREEZE-v2 已更新（23:37，sha16 `3755DB9F9CCC3BA8`）**：新增 `b_anchor` 块（sha 校验状态/分层/触发与内容两层结论/可训条件）+ `usage_rules` 改为"锚已按期交付、E2 不触发、三项前置已满足、仅缺 simulator 明示"。
- **下一步**：00:15 前出"训/不训"结论；**开训前须 A 明示 simulator**（非作者标注那一项的落地形态）。

---

### H-05 · 2026-10-29 23:50（simulator 定案 + 训练 23:36 开跑 + sim cases 冻结）

- **时间**：训练 **23:36 开跑**（远程，A10）/ simulator 归属 23:41 定案 / D 23:42 冻结 cases、23:49 落档。
- **决策（A 定案，D 记录）**：
  1. **结论=「训」**：三前置（v2 冻结 ✓ + B 100 锚 ✓ + 用户授权 ✓）已满足；**simulator 是训后验收，不是开训前置**。
  2. **simulator 归属**：**作者=B**（非数据作者，独立性成立）｜**执行=C**（用 adapter 产 pred，按映射层 M1–M4 转 `{trigger, content}`，跑 `out/autonomy_trigger_sim.py`）｜**审计/记录=D**（核 cases sha、pred 来源、S1 零容忍、加权 ≤10%）｜**A 只判结论**。
  3. **纪律**：训练开始后 **B 不得再改 `AUTONOMY-SIM-CASES.jsonl`**；**pred 必须由 C 从 adapter 实际生成，禁止人工填写**（人填 pred = 伪造证据，E9→RED）。
- **训练事实（23:36 起，远程）**：包装器 `tmp/a10_exec.py`（PID 13304）→ `a10_autonomy_train.py --train train.jsonl --dev dev.jsonl --test test.jsonl --model /root/models/Qwen2.5-14B-Instruct --out /root/work/autonomy/run1 --epochs 1 --lr 1e-4 --r 8 --dropout 0.1 > train.log`。**D 未登录远程、未核实运行状态**（key 仍被拒）。
- **cases 冻结**：`out/AUTONOMY-SIM-CASES.jsonl` 40 行 / 6,688 B / **sha256 `2ad36c184527ba1b322744df6c37d050c94414495a024fa681c870640221e05c`**（D 实测 MATCH）；严重度 **S1 12 / S2 17 / S3 11**（与 `AUTONOMY-TRIGGER-SPEC` §4 一致）；已写入 FREEZE-v2 的 `sim_cases` + `simulator` 块（FREEZE-v2 现 sha16 **`BA891D05CFD26495`**）。
- **新发现（重要，AMBER 级）**：远程 `train.jsonl` 的 sha256 **尚未与 FREEZE-v2 绑定** → 现无法证明"训的是冻结 v2"。已立 **E8：04:00 前须由 C 回传远程数据 sha / 训练日志指纹**，否则 08:00 报告并列"未绑定"声明。
- **异常**：无新 RED；8765 单监听 PID 3872、`memories=20`；HEAD `c9e3956`、ahead 27、**0 push**；D 仍未登录 A10（不可核实）。
- **下一步**：盯 **02:00 adapter 产出**（adapter sha + loss/NaN）→ **02:00–04:00 C 跑 simulator（D 审计）** → 04:00 前补远程 sha（E8，已关闭）→ 04:00–07:30 证据/commit/冻结。

---

### H-06 · 2026-10-30 00:00（E8 关闭：远程数据 sha 与 FREEZE-v2 绑定一致）

- **时间**：23:53 A 报实测结果 / 23:54 D 核对本机 FREEZE-v2 后关闭 E8。
- **E8 关闭依据（逐条比对，D 侧可复核）**：
  | 文件 | 远程实测 sha256 | FREEZE-v2 记录 | 结论 |
  |---|---|---|---|
  | `train.jsonl` | `9ae27f59548a258cae046f141eabd246d9fc4932a942b14f11135ce8da893043` | 同 | **一致 ✓** |
  | `dev.jsonl` | `150216614430aa39284495e13afdb451427be4706cb1055a74b41816b6043a16` | 同 | **一致 ✓** |
  | `test.jsonl` | `8d820865fa91a36e24992348a2751a9752131003cad0adcaaa728e3b462f54e5` | 同 | **一致 ✓** |
  → **"训练用的是冻结 v2" 现在可证**；08:00 报告可直接引用本表，无需"未绑定"声明。
- **训练运行态（A 报，D 不可独立核实）**：远程进程仍活，进度 **65/71（≈92%）**；**本地 job 包装器（`tmp/a10_exec.py`）因断连退出 127，远端 python 未死**。
- **⚠ 解释规则（新增，防止 08:00 误读）**：**本地包装 `EXIT=127` 不得记为"训练失败"**——它只是 SSH 通道断开、`train.log` 回传链断；训练成败必须以**远程进程/`train.log`/adapter 产物**为准。同理，`EXIT=0` 也可能只是包装器正常退出而训练未完成。
- **衍生风险（AMBER-lite）**：回传链断 → 本地拿不到 `train.log` 实时行；**04:00 前须确认能取到 remote `train.log` 与 adapter sha**，否则 02:00 的"adapter 产出"判据只能靠 A 转述。
- **其余状态**：8765 单监听 PID 3872 ✓；`memories=20` ✓；HEAD `c9e3956` / ahead 27 / **0 push**；无新 RED。
- **下一步**：02:00 收 adapter sha（+loss/NaN）→ 02:00–04:00 C 跑 simulator（cases `2AD36C18…`，D 审计 pred 来源）→ 04:00–07:30 commit/冻结（**不 push**）。

---

### H-07 · 2026-10-30 00:00（adapter 已回传并本机校验：回传链闭合）

- **时间**：adapter 落盘 23:54 / tar 23:57 / D 独立校验 23:57。
- **adapter（D 实测，非转述）**：

| 项 | 值 |
|---|---|
| 路径 | `D:\models\autonomy\run1\adapter\adapter_model.safetensors` |
| 大小 | **137,714,904 B** |
| sha256 | **`b02f38c0cd9010e9fbbe68ee36b1f22a565bb706b1bb95ec86b48ec475169495`** |
| 远端一致性 | A 报远端同文件 sha 相同（**D 未登录远程**，此项为转述） |
| tar 包 | `out/AUTONOMY-RUN1-ADAPTER.tgz`，**131,227,625 B**（23:57） |
| 训练配方 | 14B QLoRA 4bit-nf4；**1 epoch / r8 / alpha 16 / dropout 0.1 / lr 1e-4**；target_modules = `q,k,v,o,gate,up,down`（7 个）；bs=1 × grad-accum 8 |
| 数据 | 冻结 v2 `train.jsonl`（sha 已绑，E8 关闭） |
| NaN | `train.log` **原件已回传**，`grep -ic nan` = **0**（D 实测） |

- **补记（23:59，`train.log` 冻结 → AMBER-lite 完全关闭）**：`out/AUTONOMY-RUN1-TRAIN.log` **8,217 B**、sha256 **`09213a8545cbebaa1b6cb022fe6d7c17b0c922be4cb1826862f752788a8bc9b7`**（D 实测 MATCH）；NaN 计数 **0**；已在 FREEZE-v2 增加 `training_run1` 块（adapter/tar/log 三件 sha + 配方 + 曲线）。
  - **loss 曲线**：3.8757 → 2.3795 → 2.2535 → 2.1968 → **1.7005** → 1.799 → 1.7117；`train_loss=2.2655`；`train_runtime=1029.3 s`（≈17.2 min）；`epoch=0.99`（71 step，与"65/71"进度口径一致）；`grad_norm` 2.26–3.37（无尖峰、无 NaN）。
  - **可比性警告**：`train_loss 2.27` **不可与历史 SFT 臂（v2 0.2808 等）横向比较**——数据/任务/损失口径不同，引用即误导。
  - **评测口径**：日志显示 generation `do_sample=False`（greedy），temperature/top_p/top_k 仅告警未生效 → **dev/test 评测是确定性解码**，可复现。
- **回传链完全闭合**：adapter ✓ + `train.log` ✓ + tar ✓ → **AMBER-lite 全关**。剩余：`eval.json`（远端进程 605345 仍在跑）与 simulator 未跑。
- **观测（供 08:00 报告）**：本 adapter **137,714,904 B** 与历史 SFT LoRA **137,671,872 B** 差 **+43,032 B** → 模块集合/配方与历史臂不完全相同（历史臂未登记 target_modules）。**eval 报告须登记 r/alpha/dropout/target_modules**，否则"与历史臂可比"不成立。
- **仍未闭合（AMBER-lite 剩余）**：①`train.log` 原件未取回（仅转述无 NaN）→ 建议 04:00 前拉回并冻 sha；②`eval.json` 未落（远端仍在跑 dev/test）；③adapter 未跑 simulator。
- **其余**：8765 单监听 3872 ✓；`memories=20` ✓；HEAD `c9e3956` / ahead 27 / **0 push**；无新 RED。
- **下一步**：等 `eval.json` + `train.log` → H-08（指标 + 口径）；02:00–04:00 simulator（cases `2AD36C18…`）。

---

### H-08 · 2026-10-30 00:08（**RED-02 数据标签缺陷**：run1 判 exploratory-data-bug；v3 预审通过）

#### 1) 事件（RED-02，已确认，非"模型不行"）
- **现象**：run1 adapter 在 dev/test 上 **`pred_silence = 0`**——一条 `<SILENCE>` 都没生成。
- **D 复算（`out/AUTONOMY-RUN1-EVAL.json`，44+44 正 / 28+27 负）**：

| split | n | true | false | pred_silence | fp | tn | acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev | 72 | 44 | 28 | **0** | **28** | **0** | **61.11%** |
| test | 71 | 44 | 27 | **0** | **27** | **0** | **61.97%** |

（exact_match：dev 0、test 1；正例基本能接话，负例 100% 误触发）→ 与 A 报的 61–62%、fp28/tn0、fp27/tn0 **完全一致**。

- **根因（D 独立验证）**：v2 全部 **215 条 `should_trigger=false`** 的 assistant **都不是 `<SILENCE>`**，而是普通接话（例："嗯，我在，有事你说。" / "玩得挺欢，别让球砸着。"）；`SILENCE` 计数 = **0 / 500 正 + 0 / 215 负**。
  → **监督信号里从未出现"闭嘴"这个目标输出**，模型不可能学会；**run1 的 61% 不是自主性能力指标，是标签缺陷的直接后果**（E10 触发）。

#### 2) run1 处置（A 定，D 记录）
- 标 **`exploratory-data-bug`、不交付**；adapter 与 train.log 仅作**证据留档**（sha 已在 FREEZE-v2 `training_run1` 块），**不得进入任何"自主性模型性能"表述**。
- 训练本身无 NaN、loss 正常下降（3.88→1.71），**训练工程无问题，问题在数据**。

#### 3) v3 预审（D 已实测，`out/autonomy600_v3/`，00:05 生成；**未冻结**）
| 检查 | 结果 |
|---|---|
| 行数/切分 | train 572 / dev 72 / test 71 = **715，与 v2 完全一致** ✓（未新增、未改切分） |
| `should_trigger` 分布 | 412/44/44 true、160/28/27 false —— **与 v2 一致** ✓ |
| 是否只改 assistant | **system+user 0 处差异**（572+72+71 全比对）✓ |
| `<SILENCE>` 落位 | 恰好 = 负例数：train **160**、dev **28**、test **27** ✓（正例行仍未出现 SILENCE） |
| sha16（预审用） | train `7594812bc93d62de` / dev `b34707b0e47afa64` / test `0131c2829cf5ccad` |

→ **"最小标签修复"成立**：只把 false 行 assistant 换成 `<SILENCE>`，其余一字未动。

#### 4) 未决 / 风险
- **待办**：①v3 重跑 `sft_data_gate.py`（须 exit 0；注意 G2/G9 对 `<SILENCE>` 的短答案判定可能误报，**须确认 known_fp 口径**）；②**B 准**；③准后 D 建 **FREEZE-v3**（当前**不建**，避免冻未批准版本）；④重训 run2。
- **AMBER（新，防"用一个错误换另一个错误"）**：v3 负例全给 `<SILENCE>`、正例从不出现 → 模型可能**过度沉默**。**评测必须同时报"漏触发率"**（true 行被答成 `<SILENCE>` 的比例），只看 fp 下降会误判成功。
- **口径**：run1/v3 的 acc 与"记忆问答 79/81"等**不同任务、不可横比**。

#### 5) 状态
- 8765 单监听 3872 ✓；`memories=20` ✓；HEAD `c9e3956` / ahead 27 / **0 push**；FREEZE-v2 未变（run1 产物仅作证据）。
- **下一步**：等 v3 门禁结果 + B 裁定 → FREEZE-v3 → run2 训练（时间盒：02:00 前须起，04:00 前评完；07:30 封盘）。

- **补记（00:14，FREEZE-v3 已建 · B 已准）**：`out/autonomy600_v3/FREEZE-v3.json`（sha16 **`45EAF986BF6A0CEF`**）——只冻数据三件，三文件 sha256 **逐件 MATCH**：
  | 文件 | 行 | sha16 |
  |---|---:|---|
  | `train.jsonl` | 572 | `7594812bc93d62de`（全 sha `7594812b…52be46c`） |
  | `dev.jsonl` | 72 | `b34707b0e47afa64` |
  | `test.jsonl` | 71 | `0131c2829cf5ccad` |
  - **门禁口径已入档**：`GATE-train.json` rows 572、**real_fail 0**、`pass_rate_real 1.0`、known_fp **160**（G2 160 / G8 160 = `<SILENCE>` 短答案误报，**B 已确认按 known_fp 处理，不是 fail**）。
  - **B 批准三条已入档**：①推理端识别并输出 `<SILENCE>`；②判据须报 silence/tn/召回/**漏触发率**；③run1 标 exploratory-data-bug。
  - **eval 规则已写死（我的 AMBER 被采纳）**：必须同时报 **漏触发率 = 正例被答 `<SILENCE>` 的比例**，防"负例全 silence"导致过度沉默；acc 与记忆问答基线禁横比。
  - **遗留 AMBER-lite**：`dev/test` 未见门禁报告（只 `GATE-train.json`）；因不参与训练不阻塞，但 eval 报告须注明。
- **下一步（改）**：run2 训练（v3 train.jsonl）→ adapter/train.log/eval 单独记 **H-09**，不回写 FREEZE-v3。

- **补记（00:19，三 split 门禁补齐 → AMBER-lite ① 关闭）**：`dev` / `test` 门禁已补跑并落盘，D 本机读取核对（非转述）：

| split | 报告 | 行 | real_fail | pass_rate_real | known_fp | 规则分布 |
|---|---|---:|---:|---:|---:|---|
| train | `GATE-train.json` | 572 | **0** | 1.0 | 160 | G2 160 / G8 160 |
| dev | `GATE-dev.json` | 72 | **0** | 1.0 | 28 | G2 28 / G8 28 |
| test | `GATE-test.json` | 71 | **0** | 1.0 | 27 | G2 27 / G8 27 |

- **关键一致性**：known_fp 合计 **215 = 负例总数（160+28+27）** → 每条 `<SILENCE>` 恰好被 G2/G8 各计一次 known_fp，**与负例一一对应、无额外漏网**。→ 结论可直接写"**三 split 门禁齐全，G2/G8 为 `<SILENCE>` known_fp**"。
- **FREEZE-v3 已更新**（sha16 **`AF87B91BDA761802`**）：新增 `gate_by_split` 块（三份报告 + 逐 split 数字 + D 核验声明），`caveat` 改为"无（三 split 门禁齐全）"。数据三件 sha **未变**（冻结仍有效）。
- **run2 进度**：A 报 **29/71（41%）**，预计 ~00:24 训完 → adapter 拉回后写 H-09。

---

### H-09 · 2026-10-30 00:32（run2/v3 产物与评测：**只记录事实，不下通过/失败结论**）

> 结论待 **B 裁**。D 本节只做：产物核验、指标复算、run1 对照、风险标注。

#### 1) 产物（D 本机实测）
| 项 | 值 |
|---|---|
| adapter 路径 | `D:\models\autonomy\run2\adapter\adapter_model.safetensors` |
| 大小 | **137,714,904 B**（与 run1 同尺寸） |
| sha256 | **`c15e3a2c10f95f024e4b998bf82f147fd1a292d39c61f6c5e6925954bf5ce432`**（**实测 MATCH**） |
| 目录其他件 | `adapter_config.json`（r8 / alpha16 / dropout0.1 / peft LORA）、`tokenizer.json`、`merges.txt`、`added_tokens.json`、README |
| tar | `out/AUTONOMY-RUN2-ADAPTER.tgz`（**131,196,353 B**） |
| eval | `out/AUTONOMY-RUN2-EVAL.json`（16,333 B） |
| 训练数据 | **v3**（`train.jsonl` sha `7594812b…`，FREEZE-v3 `AF87B91B`） |

#### 2) 评测（D 从 `AUTONOMY-RUN2-EVAL.json` 独立复算，与 A 报一致）
| split | n | tp | fp | tn | fn | acc | 静默召回(tn/负) | **漏触发(fn/正)** | pred_silence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dev | 72 | 20 | 1 | 27 | 24 | **65.3%** | 96.4%（27/28） | **54.5%**（24/44） | **51**（70.8% 的轮次） |
| test | 71 | 35 | 0 | 27 | 9 | **87.3%** | 100%（27/27） | **20.5%**（9/44） | **36**（50.7%） |

#### 3) 与 run1 对照（同一 eval 口径）
| 项 | run1（v2 标签缺陷） | run2（v3） |
|---|---|---|
| pred_silence | **0 / 0** | **51 / 36** |
| dev acc | 61.1% | 65.3% |
| test acc | 62.0% | 87.3% |
| 负例误触发 | 28+27 全误 | **fp 1 + 0** |

→ v3 的标签修复**确实让模型学会了"闭嘴"这个词**（pred_silence 从 0 到 51/36），run1 的失败确认是数据问题而非模型问题。

#### 4) 风险与观察（供 B 裁量，D 不判）
1. **dev 过度沉默（我的 AMBER 命中）**：dev 只该沉默 38.9%（28/72），实际沉默 **70.8%**（51/72），**+31.9pp**；漏触发 **54.5%**——一半以上的"该说的话"被吞掉。test 也偏保守（50.7% vs 38.0%，+12.7pp）。这印证了 H-08 的预判：**只报 fp 下降会误判成功**。
2. **split 间落差极大**：dev 65.3% vs test 87.3%（**21.9pp**）。dev 族（书/口琴/同事/生日）与 test 族（车/电影/邻居/考试）不同，n 仅 72/71。→ **任何"单点数字"都不成立**，必须按 split band 报告；也不得与记忆问答基线横比。
3. **实现层事实（重要，影响"推理端识别 `<SILENCE>`"的落地）**：tokenizer 词表（151,643）里**没有 `<SILENCE>` 这个 token**（只有 `Ġsilence/ĠSilence/Ġsilenced`）→ `<SILENCE>` 是**普通子词序列**，不是 special token。因此：①判定必须走**字符串匹配**，不能靠 special token id；②需容忍截断残片（如 `<SILEN`）并记录 `max_new_tokens` 是否被截断；③好消息：本次 87 条 silence pred **全部是精确的 `<SILENCE>`、无变体**。
4. **样本量**：dev/test 各 71–72 条、正例各 44 条 → 1 条摆动 = 2.3pp；"87.3% vs 65.3%"这级差异可信，但"65.3% vs 62.0%"这类 3pp 级差异**不可判定**。

#### 5) 状态
- 8765 单监听 3872 ✓；`memories=20` ✓；HEAD `c9e3956` / ahead 27 / **0 push**；FREEZE-v3 未变（数据未动）。
- **D 的立场**：**不写"通过/失败"**。上面第 4 节三项（dev 过度沉默、split 落差、样本量）应作为 B 裁量的输入；若 B 判"通过"，08:00 报告须同时列 dev 的 54.5% 漏触发，否则等于隐藏一半风险。
- **下一步**：B 裁定 → 若需 simulator（40 条 cases `2AD36C18…`）在 run2 adapter 上跑，C 执行、D 审计 pred 来源；04:00 前须出结论，07:30 封盘。

---

# H-10 · 2026-10-30 00:35 · **最终交接（终态，结项）**

> 判定（B）：**run2 不通过 / do-not-deploy；不再训 run3；sim N/A；样本量不支持"达标"；本窗口无可用自主性交付。**
> 本窗口 D 的日志到此结项；08:00 断电前不再开新实验（E5）。

## 10.1 时间线（D 记录，22:31 → 00:35）

| 时刻 | 事件 |
|---|---|
| 22:31 | D 建本日志；首轮快照 |
| 22:18–22:28 | **RED-01 影子服务**（PID 344 旧代码接单 / 13184 空转）→ 处置、V2b/K2d 数字作废 |
| 22:44–22:47 | autonomy600 **v1** 落盘 600 行（后被取代） |
| 23:21 | **08:00 断电通知** → 时间线整体前移，新增 E5（07:30 封盘）等 |
| 23:22–23:23 | **v2** 落盘 715 行（负例 30.07% + 逐行 `should_trigger`）；E1 不触发 |
| 23:27–23:29 | **FREEZE-v2** 建（五文件 sha MATCH）；D 独立复算门禁 |
| 23:31 | B **100 锚**交付（`047c5ccf…`），D 复核 + 指出"同构、非独立验证" |
| 23:36 | **run1 开训**（v2 数据）；23:42 sim cases 冻结；23:53 **E8 关闭**（远程数据 sha 与冻结一致） |
| 23:54–23:59 | run1 adapter + train.log 回传，D 实测 MATCH → **AMBER-lite 全关** |
| 00:04 | run1 eval：**pred_silence=0**、acc 61–62% |
| 00:05 | **RED-02 确认**：v2 全部 215 条 false 行 assistant 无 `<SILENCE>` → 标签缺陷 |
| 00:05–00:13 | **v3** 最小标签修复；三 split 门禁齐全（known_fp 215 = 负例数） |
| 00:12–00:20 | B 准 v3 → **FREEZE-v3** 建（`AF87B91B`） |
| 00:23–00:30 | **run2**（v3）训完；adapter 回传（`c15e3a2c…`）；eval 落盘 |
| 00:32 | **H-09**：只记事实、不下结论；标 dev 过度沉默 / split 落差 / 样本量 |
| 00:32–00:35 | **最终判定**出（`AUTONOMY-FINAL-VERDICT.md`）+ 验收页（`0800-ACCEPTANCE.md`） |

## 10.2 终态产物（D 本机实测 sha16）

| 产物 | 路径 | 字节 | sha16 |
|---|---|---:|---|
| 最终判定 | `out/AUTONOMY-FINAL-VERDICT.md` | 4,038 | `CC2ADA164F83F13B` |
| 验收页 | `out/0800-ACCEPTANCE.md` | 3,132 | `2B8CDE5383E8FD6F` |
| run2 eval | `out/AUTONOMY-RUN2-EVAL.json` | 16,333 | `7F722C9537756A5C` |
| run2 train.log | `out/AUTONOMY-RUN2-TRAIN.log` | 8,301 | `99E3C42BE68BA771` |
| run1 eval | `out/AUTONOMY-RUN1-EVAL.json` | 19,951 | `F3570E562507735D` |
| run1 train.log | `out/AUTONOMY-RUN1-TRAIN.log` | 8,217 | `09213A8545CBEBAA` |
| **FREEZE-v3**（权威） | `out/autonomy600_v3/FREEZE-v3.json` | 5,076 | **`AF87B91BDA761802`** |
| FREEZE-v2 | `out/autonomy600/FREEZE-v2.json` | 10,134 | `B524F97C86B46FFF` |
| B 100 锚 | `out/autonomy600/B-ANCHOR-100.jsonl` | 21,215 | `047C5CCFD76F8E43` |
| sim cases（N/A） | `out/AUTONOMY-SIM-CASES.jsonl` | 6,688 | `2AD36C184527BA1B` |
| v3 数据 | `out/autonomy600_v3/{train,dev,test}.jsonl` | 674,422 / 83,598 / 82,599 | `7594812B…` / `B34707B0…` / `0131C282…` |

**adapter（不交付，仅留证）**
- run2：`D:\models\autonomy\run2\adapter\adapter_model.safetensors`，137,714,904 B，**`c15e3a2c10f95f024e4b998bf82f147fd1a292d39c61f6c5e6925954bf5ce432`**（do-not-deploy）
- run1：`D:\models\autonomy\run1\adapter\adapter_model.safetensors`，137,714,904 B，`b02f38c0cd9010e9fbbe68ee36b1f22a565bb706b1bb95ec86b48ec475169495`（exploratory-data-bug）

## 10.3 RED-02 归档（数据标签缺陷）

- **现象**：run1 `pred_silence=0`，负例 55/55 全误触发，acc 61–62%。
- **根因（D 独立验证）**：v2 **215/215** 条 `should_trigger=false` 的 assistant 是普通接话（"嗯，我在，有事你说。"），全库 `<SILENCE>` 计数 **0/715** → 监督信号里没有"闭嘴"。
- **定性**：**数据缺陷，不是模型能力失败**；run1 判 `exploratory-data-bug`，其 61% 不得作能力引用。
- **修复**：v3 仅改 false 行 assistant → `<SILENCE>`（行数/切分/其余字段零改动，D 逐行核验 system+user 0 差异）。
- **教训**：训练目标必须在 assistant 侧显式出现，评测必须报 tn/fp/静默召回/**漏触发**，否则"全触发"能刷高 acc。

## 10.4 未决（08:00 需用户拍板，见 `0800-ACCEPTANCE.md` §6）

1. **SIM 缺输入（N/A）**：`AUTONOMY-SIM-CASES.jsonl` 40 条只有元数据、无 system/user 字段；`autonomy_trigger_sim.py` 只能对 `--pred` 打分 → **无法用 adapter 生成 pred**；40 条冻结保留、标 `N/A: missing input field`，下一版必须内嵌输入。
2. **D 类内容 5/100（15.6%）无据/矛盾未验证**：因 sim 跑不了，**只能写"未验证"**，不得写"已修/无问题"。
3. **样本量不支持达标**：dev/test 各 4 族×约 10 条，±1 条≈10pp；"每族 ≥30 条 / ≥10 族"才有资格谈论达标。
4. 产品三问：自主性是否下窗口重做、K2/verifier 是否转产品候选、TTS 是否 CPU/SAPI 落地。

## 10.5 08:00 验收清单（D 逐项核对，全部 ✓）

- [x] `out/AUTONOMY-FINAL-VERDICT.md` 存在（判定：不通过 / do-not-deploy）
- [x] `out/0800-ACCEPTANCE.md` 存在（含交付物 sha、关键数字、未决、三问）
- [x] v3 数据三层 sha 与 `FREEZE-v3.json` 一致；`FREEZE-v3` = `AF87B91B…`
- [x] run1/run2 adapter 均在本机、sha 实测 MATCH、均标 do-not-deploy/exploratory
- [x] run1/run2 eval + train.log 落盘（NaN=0、loss 正常、greedy 口径已记）
- [x] B 100 锚 `047c5ccf…` 与 sim cases `2ad36c18…` 均在盘、未被改写
- [x] **未 push**（HEAD `a9b7f99`，origin/main 落后 **29**）
- [x] **未切默认模型**（产品仍 `Qwen2.5-14B-Instruct-Q4_K_M`，sha `e47ad95d…`）
- [x] 8765 单监听 PID 3872、`/status` 200、`memories=20`（无影子服务复发）
- [x] 无真实记忆上 A10；产品路径未改动（KV + K2 off + verifier v1 + 不靠 prompt）

## 10.6 文档一致性提示（给 E commit 用）

- `AUTONOMY-FINAL-VERDICT.md` §2 与 `0800-ACCEPTANCE.md` §2 写的是 `FREEZE-v3 = 45EAF986…`，那是**加 `gate_by_split` 之前的版本**；当前权威为 **`AF87B91B…`**（数据三件 sha 未变，仅元数据增补）。**引用请用 AF87B91B**，两文档建议下次 commit 时对齐，否则同一冻结出现两个 sha。
- 本日志最终 sha 见文末《结项指纹》。

## 10.7 结项指纹

- 本日志（`out/OVERNIGHT-RUN-LOG.md`）：最终 sha256 记录在同目录 **`OVERNIGHT-RUN-LOG.sha256`**（正文若自引用自身哈希会立刻改变哈希，故放旁挂文件）。
- HEAD `a9b7f99`（ahead **29**，未 push）；`memories=20`；8765 单实例。
- D 全程**只读**：未跑 GPU、未改代码、未 commit、未 push、未启停服务、未连远程执行命令。

**D 签名：结项。08:00 断电前无新实验；如需追加，只在 E5 允许的"收尾写盘"范围内。**

---

# H-11 · 2026-10-30 14:02 · **断电后重启段：40k n200 事故重建 + 隔离规则（追加，不撤结项）**

> 说明：08:00 断电已发生；机器恢复后 01:11 起续做 40k/规模测试。本节为 **post-outage 追加**，H-10 的自主性结项不受影响。

## 11.1 新事故（RED-03 候选：实验污染，非产品）

| 项 | 内容 |
|---|---|
| 现象 | 40k **n200** 库在 **8765** 上被 **C2 的 K2E runner 重连**后执行 `/reset` + `/remember` → **200 行 → 115 行、200 块 → 20 块** |
| 根因（四类，D 归纳自 `EXPERIMENT-ISOLATION.md`） | ①**并发隔离缺失**（规模实验复用产品端口 8765）②**旧 runner 未杀** ③**服务重启后客户端自动重连** ④**无 DB 指纹门禁**（写库前不校验库身份） |
| 影响 | n200 的首次建库与 K2E 首轮数据**作废**；产品库 `daily/chat.db` 未受影响的证据：现 `memory_source=20`（需在 8766 侧确认，见 11.4） |
| 定性 | **实验环境事故**，不是产品事故；但属"评测数字不可信"级别——任何在污染期产出的 40k/K2E 数字**不得引用** |

## 11.2 重建结果（D 本机读取 `kvmem/scale40k/n200/DATA-AUDIT-n200.json`）

| 项 | 值 |
|---|---|
| 行 / 块 / 块文件 | **200 / 200 / 200** ✓ |
| 孤儿块 / 缺文件 / 零字节 | 0 / 0 / 0 ✓ |
| token | 合计 **43,205**，mean 216，min 9，max 785；`long_ge_600` = 19 |
| 脏对（dirty pairs） | 5 组均 `ok:true`（差异仅全角/空格） |
| 审计总判 | **`ok: true`、`problems: []`** |
| 隔离环境 | **8766**（PID 3700），库 `kvmem/scale40k/n200/chat.db`，**不再碰 8765** |

## 11.3 规则落档（`out/EXPERIMENT-ISOLATION.md`，D 摘要）

1. **端口/库租约**：8765=K2/verifier 产品验收（`kvmem/daily/chat.db`，C2/A）；**8766=40k 规模（`kvmem/scale40k/n*/chat.db`，C6）**；8767+ 按需独立副本。**禁止复用 8765 跑规模/临时实验**；起服务前写 `out/EXPERIMENT-LEASE.json`（port/db/owner/pid/started_at），结束删除。
2. **停/起服务**：停后须确认 `netstat` 无 LISTENING **且无 runner/客户端进程**；起后记录 PID/uptime/`/health` model_size/memories；**同端口多 PID → RED**。
3. **runner 门禁**：`/health` 校验 `model_size=8988110976` + `memories` 预期值；`/status` 或直读 DB 校验 **DB 指纹（rows/sha256 前缀）**与租约，**不符即 ABORT、不写库**；`--reset-per-case` / `remember` 前再校验 rows。
4. **数据保护**：评测前 `cp chat.db chat.db.bak-<ts>` 并记 sha；污染只能用备份重建，**禁止手改库绕过**；**每次重建后重跑 DATA-AUDIT**（行/块/孤儿/长块/脏对/query target）。
5. **复盘模板**：时间线、PID/端口、被污染文件+sha、根因分类（隔离/进程/门禁/人为）、修复、**复发判据**。

## 11.4 作废与保留（明确口径）

- **作废**：K2E 首轮数据（`out/KVC-K2E-MT20.json`：n=20、valid 17、infra 3、pass **5**、pass_rate **29.4%**）→ **不得引用**；旧 n200 首建库。
- **保留有效**：`n20`（30 行）/`n50`（60 行）在 01:11–01:22 建成、当时未受污染（**但需按新规则复核指纹后才算数**）；`SLOPE-20-50.json`、`RUN-REPORT-20-50.md` 属污染前产物，**引用时标注"污染前"**。
- **在跑**：`RUN-n200-k2off.log` 14:01 到 `[32/40]`；观察到的现象：多条 paraphrase / chain_last 返回"这条我没法从记忆里核对"、q083/q084/q086 出现旧值泄漏（leak=True）→ **D 只记录不解读**，等 C 的正式报告。

## 11.5 当前状态（14:02）

- **8765 未在跑**（仅 8766 LISTENING，PID 3700）→ 产品服务当前**不可用**；如需产品验收须按租约重启并记录。
- 仓库：HEAD **`a499171`**（`docs(autonomy): 对齐 FREEZE-v3 权威 sha AF87B91B`）、**ahead 30**、**0 push**。
- 自主性线仍为 H-10 终态（不通过/do-not-deploy），本节不改判定。
- **证据 sha（D 实测）**：`out/EXPERIMENT-ISOLATION.md` = `8A8C2E9B…`（见 11.6 实测表）；`kvmem/scale40k/n200/DATA-AUDIT-n200.json` 与 `chat.db` 见下表。

## 11.6 实测 sha16（14:02，D 本机）

| 文件 | 字节 | sha16 | 备注 |
|---|---:|---|---|
| `out/EXPERIMENT-ISOLATION.md` | 1,889 | `56ED2AE0FB01B3BD` | 规则正文 |
| `kvmem/scale40k/n200/DATA-AUDIT-n200.json` | 1,950 | `08F896454D79A24A` | 审计通过 |
| `kvmem/scale40k/n200/chat.db` | 339,968 | **不可哈希** | 被 8766（PID 3700）持有 → "文件正被占用"；**这本身是"服务在跑"的旁证**，需停服后再取 sha |
| `out/KVC-K2E-MT20.json`（作废） | 143,465 | `83EAD95D5F871056` | 仅作"作废件"指纹保留 |

## 11.7 给 08:00 页的同步

已同步 `out/0800-ACCEPTANCE.md`：§5 的"40k 未建库/未跑"改为现状，并新增 **§5.1 事故与防复发**（RED-03 + 五条隔离规则 + 作废口径）。