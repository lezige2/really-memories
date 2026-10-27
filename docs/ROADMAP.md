# ROADMAP — llama-mem 的「正确路径」（研究线收口 + 产品线收尾）

> **读者**：当时的我、半年后的我、外部审阅。
> **口径**：本文件给**路径与边界**，不给新结论；研究结论见 `docs/RESEARCH-RESULTS.md`，数字以其冻结件 sha16 为准。
> **一句话**：研究线**已封闭**（负结果成立、判据不可达标），产品线**可交付但要用户试用**；下一步是**用产品、不是再改判据**。

## 0 当前坐标

| 线 | 状态 | 证据 |
|---|---|---|
| 研究线（M5C2 判据） | **封闭**：b5 擦边 / b6 未接上 / b7′ 擦边；rev7.2 为最后版本 | `M5C2-B7-VERDICT.json` `1cb7a7961aefe0c6`；`M5C2-B7-VERDICT-SUPPLEMENT.json` `a58c3c87393a5b0c`；R10 裁定 `3dfafd1253f0a833` |
| 产品线（C 版 14B 助手） | **v1.1 通过**（可用性，非研究证据） | `docs/USER-GUIDE-C.md` `517d557ca9d68e3f`；`C-V1-ACCEPT` `e8e7521efd36f391`（pin `286fcdf7de11b822`）；`C-PRODUCT-ACCEPTANCE.md` `af0adfe3bec6ba39` |
| DSH 接入 | provider **已写入 profile patch**，**待用户重启验证** | `~/.dsh/profiles/desktop/cordis.patch.yml:377–392`（`local14b`）；补丁文本 `docs/_work/DSH-PATCH-local14b.yaml` `9f4ef6b22a26e2f0`；侦察 `docs/_work/DSH-LOCAL-MODEL-RECON.md` `049800039b031646` |
| QQ 接入 | 适配器**已写、待联调** | `docs/QQ-BRIDGE.md` `bed351733afbb5e3`；`tools/qq_bridge.py` `0ed698febc277018` |

## 1 已完成（不要再重做）

1. **研究线封闭**：b5 擦边（`M5C2-B5-VERDICT.json` `fa93b38cdedea58e`）；b6 未接上/样本量不足（`M5C2-B6-COMPONENT-READING.json` `9a0c75529485311f`）；b7′ 擦边（`1cb7a7961aefe0c6` + supplement `a58c3c87…`）。判据层 rev7.2 冻结（`M5C2-REV7-2-FREEZE.json` `87a13b0c9aeae083`），**R10：之后不再改判据**。
2. **C 版 v1.1**：S1–S7 全过、`real_engine` 模式；口径 `PRODUCT-C-SPEC.md` `694ebbad136efbec`、`PRODUCT-C-LOG-SPEC.md` `56a7fca2b169bcf3`；启动 `start_chat.cmd` `026f296773dd4df6` → `tools/chat_daily.py` `639b5497890e110a`。**产品通过 ≠ 判据达标**，两者禁止互引。
3. **DSH 本地模型接入**：在 `llm-pi-ai.providers` 下加兄弟条目 `local14b`（`http://127.0.0.1:8765/v1`，`openai-completions`，8k ctx / 2048 max tokens），**已落盘**；`agent-default-model` 仍指向 bailian（故意不切换）。
4. **QQ 适配器**：OneBot v11 反向 WS → `tools/qq_bridge.py`，已实现 `/ask`、`/remember`、`/memories`、`/forget`、`/status`；**未联调**，且必须用小号（风险披露见 `docs/QQ-BRIDGE.md`）。

## 2 明确「不再做」（硬边界）

- **不开 b8、不加数据、不再修 rev7.x**（R10）；b5/b6/b7′ 均为**一次性**数据集，**不得重跑**。
- 不改任何冻结件；不把 C 版产品验收当研究证据；不用 b5 dev 读数（2.78%）论证能力。
- **禁写**：接近达标 / 就差一点 / 样本量不足导致 / 再多一点数据就能过（研究冻结件 `banned_phrases`）。
- 不写「通过」或「未通过」描述 b7′（擦边是四态之一，不得事后改解释）。

## 3 两条合法的后继（**都不现在做**）

| 路径 | 做什么 | 进入条件 | 成本 | 风险 |
|---|---|---|---|---|
| A. **改测量** | 零 GPU **受控注入**：在固定输出上人为植入 fabricated/无关事实，测判据的检出曲线（diagnostic_only） | 有新测量问题且**先写预登记**；不触碰 b5/b6/b7 结论 | CPU 1–2 天 | 仍是诊断读数，**永远不能当 H1 证据**；容易被误读为「能力提升」 |
| B. **改判据设计** | 换范式（如检索-校验/自然语言推理判官）+ **新预登记** + **新数据集**（新题面、新盲标、新 gold） | 有明确新机制假设 + 用户批准开新研究线；判据/题面/数据集三者全部先冻后用 | GPU 天级 + 出题/盲标人力；需远超前两次的样本量 | 重演过拟合与样本量陷阱；一次性数据集烧掉后无退路 |

**为什么现在不做**：A 不改变「判据不可达标」的结论；B 只有在产品线证明「用户真的需要更强接地」之后才值得开新研究线。**先把干净的负结果和可用产品交付，是对当前证据最诚实的处置。**

## 4 产品线下一步（唯一顺序）

1. **用户试用 1–2 天**（最高优先，非 GPU）：`start_chat.cmd` 起服务，按 `docs/USER-GUIDE-C.md` 用；记录三类反馈：答错/绕弯、慢、崩/恢复。
2. **反馈修**：只修真 bug 与体验（日志、提示、恢复），**不动研究线**；每次修给出「改了什么/怎么验证/回退点」。
3. **QQ 联调**（CPU）：装 NapCat（**小号**，我装、你扫码登录）→ `tools/qq_bridge.py` 反向 WS 连上 → 单聊「你好」→ 群聊 @ 机器人 → `/remember`、`/status` 冒烟；跑通后**才**给第二个人用。
4. **稳定性与文档**：补长回答延迟分布（v1.1 仅单次 328 字/23.45 s）；日志/恢复/限流压测；把本文与 `USER-GUIDE-C` 保持同步。
5. **DSH 内嵌验证**：用户**重启 DSH** → 模型选择器出现「本地 14B 记忆」→ 选它发一句话 → 用本地 `/v1/mock` 或真服务验证 → 再决定是否把 `agent-default-model` 切到 `local14b`（建议先不切）。

## 5 数据与文档治理

- **文档以 code + 冻结件为准**：代码 = 当前工作树；冻结件 = `kvmem/m2_visibility/m5/out/**`（带 sha16 的 verdict/readings/gold/freeze）；文档只是索引与解释。
- **索引**：`docs/CODE-MAP.md`、`docs/DOC-AUDIT.md`（若并行整理任务尚未落盘，以它们的产出为准；兜底 `docs/_work/CODE-TRACE-*`、`DOC-HASH-LEDGER-M5C2.md`）。
- **证据链保留**：`m5/out` 全部保留（可复算）；**临时数据清理**：`_raw`/`tmp`/旧中间版本/调试脚本不进交付面。
- **旧文归档**：旧 `PROGRESS-AND-ROADMAP.md` 等长文正被归档，**不再作为权威引用**；需要历史时按 sha 回查冻结件。
- 不 commit；归档与推理由 LEAD 统一做。

## 6 里程碑简表

| 里程碑 | 状态 | 门 |
|---|---|---|
| M5C2 判据研究（b5/b6/b7′ + rev7.x） | **关闭（负结果）** | 结论冻结、R10 生效 |
| C 版产品 v1.1 | **通过（可用性）** | S1–S7 + 验收件冻结 |
| 用户试用反馈 | **待启动** | 用户 1–2 天 |
| QQ 联调 | **待启动** | 小号 + NapCat + 联调清单 |
| DSH 内嵌 | **待用户重启验证** | 重启后模型选择器出现本地 provider |
| b8 / rev7.3 / 新研究线 | **明确不做（当前）** | 仅按 §3 的 A/B 条件另立 |

## 7 验证命令（路径都可在盘核对）

```bash
cd /d/llama-mem
sha256sum docs/RESEARCH-RESULTS.md docs/ROADMAP.md
sha256sum kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT.json \
          kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT-SUPPLEMENT.json \
          kvmem/m2_visibility/m5/out/M5C2-REV7-2-FREEZE.json
python -X utf8 -c "import json;d=json.load(open('kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT.json'));print(d['verdict'])"
# C 版启动
python -X utf8 tools/chat_daily.py
# DSH 侧（重启后）：~/.dsh/profiles/desktop/cordis.patch.yml 中 local14b 是否存在
grep -n "local14b" ~/.dsh/profiles/desktop/cordis.patch.yml
```

**半年后请先读**：本文件 §2（不再做什么）与 `docs/RESEARCH-RESULTS.md` §4（披露）；**不要**从旧长文重开研究线。