# PROJECT-STATE —— 当前状态（唯一状态权威）

> **as-of**：2026-10-27 ｜ 工作目录 `D:\llama-mem` ｜ 本机、单用户、**默认离线（仅只读 Bing 检索）** ｜ 原则：**代码 + 冻结产物 > 文档**。
> 本文件不抄历史长文；历史全文见 `docs/archive/PROJECT-STATE-ARCHIVE.md`（移动保留）与 `PROGRESS-AND-ROADMAP-ARCHIVE.md`。
> 引 sha / 读数字前先查 `docs/_work/ANCHORS-CURRENT.md`（坐标现值）与 `docs/_work/ARTIFACTS-KEY.md`（产物清单）。

---

## 1 一句话现状

- **研究线已封闭**：三条数据集的终态已定，**判据操作点超 H1 可达界 ⇒ 当前设计下不可达标（能力上限，非样本量）**；`R10` 终止，不再改判据、不开 b8。
- **产品线 v1.1 = 通过**：本地 14B 记忆助手可用（检索 4/4、强制 rollover、长回答 328 字 / 23.45 s、日志 verify rc=0）。
- **引擎/装置**：单卡 ~10 GB 上，14B Q4_K_M + `n_ctx=16384` / `n_gpu_layers=34` 可用，实测 VRAM 峰 **7.99–8.58 GiB**（b5 8.0423 / b7 抽取 8.2736 / resume 8.5753；fuse 8.6，8.0 仅为目标值）。

**数字出处**：`M5C2-B7-VERDICT.json 1cb7a7961aefe0c6/4165`、`M5C2-B7-VERDICT-SUPPLEMENT.json a58c3c87393a5b0c/3871`、`docs/_work/B7-FINAL-REPORT.md 9b0ed2d3178616d7/5294`、`C-V1-1-REGRESSION.json 611fc849f7cb3118/6084`、`C-V1-ACCEPT.json e8e7521efd36f391/10398`。

---

## 2 装置与参数（以代码常量与实跑产物为准）

| 项 | 值 | 依据 |
|---|---|---|
| GPU / 显存 | 单卡 ~**10 GB**；VRAM 峰 **7.997 GiB**（v1.0 实测，fuse **8.6**）；16k+34 层余量小 | `C-V1-ACCEPT.resources` |
| 模型 | `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` | `tools/memory_source.py:51` |
| 引擎 | llama.cpp fork（分支 `persistent-memory`），补丁 `patches/persistent-memory.patch`；shim `tools/kvshim_vk.dll` | `patches/`、`tools/chat_daily.py:52` |
| 上下文 | `n_ctx=16384`：**对话窗 8192** / **记忆区预算 7680**（= chat_start−512） | `tools/chat_daily.py:59-60` |
| GPU 层数 | `n_gpu_layers=34`（36 层余量仅 0.22 GiB，不选） | `tools/chat_daily.py:68` |
| KV 类型 | `q8_0` | `tools/chat_daily.py:352` |
| 检索 | `--retrieval topk`，`topk=4`（bigram+标签 → top-k → 1 跳关联） | `tools/chat_daily.py:70` |
| 挂载上限 | 同时挂载 **≤6 块**（seq 1..6）；`off` 模式全量 ≤6 | `tools/chat_daily.py:63-64` |
| 库上限 | topk 模式 **≤200 条**（`PRODUCT-C-SPEC`） | `docs/_work/PRODUCT-C-SPEC.md 694ebbad` |
| 输出 | `n_predict` 默认 **192**（≤200 token） | `tools/chat_daily.py:81` |
| 自动压缩 | 对话窗 ≥**75%** 触发（`rollover_at=0.75`）；原文归档 + ≤200 token 摘要索引 | `tools/chat_daily.py:71`；`test_rollover_cpu.py` |
| 数据位置 | 记忆库 `kvmem/daily.db`、块 `kvmem/daily_blocks/`、会话 `kvmem/sessions/`、日志 `kvmem/assistant/` | 代码默认路径（`chat_daily.py:54-57`、`assistant_log.py:43`） |
| 服务 | `127.0.0.1:8765`，`tools/chat_service.py`（HTTP + OpenAI 兼容） | `tools/chat_service.py:61-62,455-530` |

---

## 3 研究线终态表（b5 / b6 / b7′）

| 数据集 | 判据 | 误判（FP） | 漏判 | 判定 | 备注 |
|---|---|---|---|---|---|
| **b5**（8 场景×5 题=40；326 句） | rev7.1 | **9/72 = 12.50%**（Wilson hi 22.08%） | **0/29**（hi 11.70%） | **擦边** | 已**永久降为 dev**，不得再作 H1 证据 |
| **b6**（8 场景×5 题=40；233 句） | rev7.1 | 13/69 = 18.84%（hi 29.61%）可测且越线 | 1/17 **不可测**（分母<20） | **未接上（样本量不足）** | FP 分量指向未通过；`n_leak=17<20` |
| **b7′**（15 场景×5 题=75；623 句） | rev7.2 | **22/147 = 14.97%**（hi **21.62%**） | **10/62 = 16.13%**（hi **27.21%**） | **擦边（两读一致）** | 唯一独立测试；B 宽读 21/147、11/62 同档；diff 11 |

**口径与结论（b7′）**

- 两读点估计均在 H1 线内，但 Wilson 上界均越线 ⇒ **擦边**（A/B 同档 ⇒ 不降级，headline 取 A_narrow）。
- 分母：gold support 148 / fabricated 63；排除 layer0 **42 句**（含 1 support + 1 fabricated）⇒ **n_fp=147、n_leak=62**；layer0 纳入版 148/63 下 A 22/148=14.86%（hi 21.48）、漏判 10/63=15.87%（hi 26.81）——**两版均擦边**。
- **可达界**：`n_fp→∞` 时 H1 可过最大点估计 **12.70%**；rev7.2 操作点 **≈14.97–15.60%** ⇒ 差 ≈2.3 pp；**样本量只能缩 CI、不能移动操作点** ⇒ **不可达标（非样本量不足）**；`terminal_reason = judge_operating_point_exceeds_feasible_bound`。
- **dev→test 过拟合实证**：rev7.2 在 b5 dev 上 **2.78%** → b7′ 实测 **14.97%**（**×5.4**）⇒ b5 永久为 dev。
- `undecidable_on_gold_support = 3/147 = 2.04%`（<15%，无"分母含高比例免检"caveat）。
- **R10 终止**：rev7.2 为最后判据版本；b7′ 失败即停。将来若动，只允许 ①改测量（零 GPU 受控注入，`diagnostic_only`）或 ②改判据设计（新预登记 + 新数据集，等同开新研究）；**不得靠加数据**。
- **禁语**（不得出现）：`接近达标`、`就差一点`、`样本量不足导致`、`再多一点数据就能过`。

**研究线证据链（b7′，现值）**：`GEN 041b51eb`、`SENTS c5a49a69`（623 句）、`GOLD v2 d5726d9c`、`EXTRACT 2804fbbb`、`DECIDE adaf0104`、`WIDE 3e46633a`、`READINGS 15190c2e`、`MERGE-CHECK v3 6048139a`（59/59、falsifiability 3/3 fail_detected）、`INSPECTOR-S5 v2 ee0abc1c`、`SUPPLEMENT a58c3c87`、`B7-FINAL-REPORT 9b0ed2d3`；读法件 `RULING-M5C2-B7-A3-V2.md 75e70358`（pin `daff66d5`）。

---

## 4 产品线 v1.1 验收

| 项 | 结果 | 证据 |
|---|---|---|
| v1.0 可用性 | **通过**（S1–S7 全过，real_engine） | `C-V1-ACCEPT.json e8e7521e/10398`（pin `286fcdf7`） |
| v1.1 回归 | **通过**（`verdict=通过`、`caveats=[]`） | `C-V1-1-REGRESSION.json 611fc849/6084`（外钉 `d2fe383c/878`） |
| V11-1 10 条库检索 | **4/4**；挂载 `[1]`、`[3,4,9,10]`、`[5]`、`[4]`；延迟 1.24–3.48 s | 回归件 `retrieval` |
| V11-2 强制 rollover | 第 4 问触发；`auto_summary id=5 ↔ auto_archive id=4`、`related_ids==[4]`、archive `20261027-135756-b49607.txt` | 回归件 `rollover` |
| V11-3 长回答 | **328 字 / 23.45 s**（<60 s P95 预算）；短问 P50 1.98 s；**长回答多次分布仍待补测（n=1）** | 回归件 `long_answer` |
| V11-4 日志 | A/B/C 三根 `inspect_logs --verify` 全 **rc=0** | 回归件 `logs` |

> **隔离声明**：产品证据（`C-*` 件）**不得进入研究线引用链**，不参与 b5/b6/b7 判定，不构成判据能力结论。

### 4.1 C v1.3 行为变更（代码已改，**待最终测试/LEAD 补实测**）

| # | 变更 | 实现位置 | 状态 |
|---|---|---|---|
| 1 | **自动记忆（静默）**：陈述"我的事实"自动写入长期记忆；**不再回复"已记住（id=N）"**，只自然接话 | `tools/chat_daily.py::_auto_remember_candidate`（`:1009`）、静默写入（`:1406-1415`） | 代码已改；待实测 |
| 2 | **拒答**：个人事实问句无记忆命中一律固定拒答（不再用"对话历史提过"放行）；文案「记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。」 | `tools/chat_daily.py:87`（`PRODUCT_REFUSAL`）、`:1476-1490` | 代码已改；`test_refusal_cpu.py` 13 checks 0 failed |
| 3 | **只读联网**：`tools/web_lookup.py` 只读 Bing 检索；时间敏感/需查证问题先检索再答，答案带「（来源：Bing 检索）」；模型不得自称能联网 | `tools/web_lookup.py`；`tools/chat_daily.py:988-1003,1425` | 代码已改；联网可用性待实测 |
| 4 | **能力/记忆内省**：问"你记得什么/记忆力有什么"列出真实记忆；问"能联网吗"明确说不能自己联网 | `tools/chat_daily.py:1023-1045`（`_capability_reply`） | 代码已改；待实测 |
| 5 | **检索相关性门槛**：命中数+覆盖率双门槛（默认 score≥2.0 且 coverage≥0.30；短查询例外 score≥1.0 且 coverage≥0.5），弱命中不挂载 | `tools/chat_daily.py:663-700`（`_retrieval_select`） | 代码已改；待实测 |
| 6 | **答案核对（v1.4 目标）**：基于记忆的答案先核对再返回；不通过重答 1 次；仍不过给兜底句「这条我没法从记忆里核对，先不猜。」；日志 `verify_repair`/`verify_fallback`；开关 `LLAMA_MEM_VERIFY` | 待 T1–T4 落地（CLI/服务同一路径） | **待实现·待实测**；见 `docs/ANSWER-VERIFY.md`（草稿） |

> `/auto` 开关**预留未实现**（代码无 `/auto` 命令）；撤销自动记忆用 `/forget`。行为变更属**产品可用性**，不改变研究线结论。

---

## 5 未决事项（当前开放项）

1. **b6 漏判侧未测完**：`n_leak=17<20` 不可测；R10 已终止，**不补跑**（保留为样本量不足的终态记录）。
2. **M4（推断/否定）残差**：未进 rev7.2，b7′ 漏判 10 例逐 sid 保留（不剔除、不作废）；记录于 FINAL-REPORT，**不排期修**。
3. **长回答延迟分布**：仅单次实测（328 字/23.45 s）；P50/P95 分布待多次样本（v1.1 边界，非阻塞）。
4. **QQ 接入风险**：`tools/qq_bridge.py` 依赖第三方协议端（NapCat/Lagrange），**可能封号**、风险自担；不用主号。
5. **DSH provider 补丁**：`restart-dsh.cmd` 在本机改 DSH 配置启用 `local14b`；异常时用 `rollback-dsh-local14b.cmd` 回滚（备份 `cordis.patch.yml.bak-20261027-local14b`）。
6. **显存余量小**：16k+34 层峰 ≈8.0–8.2 GiB，fuse 8.6；不宜与其它 GPU 任务并发。
7. **C v1.4 答案核对待实现/实测**：机制见 `docs/ANSWER-VERIFY.md`（T1–T4 接口；开关/日志字段/兜底句已定义，代码未落地）；**C v1.3 行为变更待最终测试**：自动记忆（静默）/拒答文案/只读联网/能力内省/检索双门槛已改代码，**尚待 LEAD 补实测与验收件**（见 §4.1 与 `C-PRODUCT-ACCEPTANCE.md` §7）。
8. **文档迁移收尾**：`PROGRESS/HANDOFF/旧 PROJECT-STATE` 已归档（见 `docs/ARCHIVE-INDEX.md`）；`docs/_work` 内部交叉引用仍可能指向旧根路径，逐步随维护更新（冻结件不动）。

---

## 6 维护规则

- 状态变更 ⇒ 只改本文件 §1–§5，并在 `docs/ARCHIVE-INDEX.md` / `docs/_work/INDEX.md` 留痕；**不复制**大段历史。
- 引 sha/数字前查 `docs/_work/ANCHORS-CURRENT.md`；产物查 `docs/_work/ARTIFACTS-KEY.md`。
- **禁止**：改 `kvmem/m2_visibility/m5/out/` 冻结件、删 `docs/_work` 被 pin 引用的件、git commit（统一由 LEAD 收口）。