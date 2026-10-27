# RULING-M5C2-B7-ABORT（冻结 v1）：(b7′) 一次性运行的 abort / 重跑 / 归类规则

> 裁定人：LEAD · frozen_rev=1 · frozen_at 2026-10-27T11:20:00+08:00 · 件性质：**新增规则（不改 B7 题面/rev7.2/任何冻结件）**
> 适用对象：`(b7′)` 一次性运行（`M5C2-B7-QUESTIONS.json f1f059539453d562 / 15,964 B`，15 场景 × 5 题 = 75 题；`RULING-M5C2-B7.md 3dfafd1253f0a833`；`RULING-M5C2-B7-A2.md`、`A3.md`）
> 法源：B5-ABORT 的阶段码与检查单，**按新数据集重新冻结**（B5 的 abort 件只管 b5，管不到 b7′）。本件不是对 B5-ABORT 的解释，而是 b7′ 的独立规则。

## 0 开跑前必须齐备（缺一不得开跑）

| # | 件 | 证据 |
|---|---|---|
| 1 | 本件冻结 | `out/RULING-M5C2-B7-ABORT.json` 外钉 |
| 2 | 题面冻结 | `M5C2-B7-QUESTIONS.json f1f05953` / pin `1baeda859bc05549` |
| 3 | rev7.2 冻结 + 读法预置 | `M5C2-REV7-2-FREEZE.json 87a13b0c9aeae083`、`RULING-A2 320b643a`、`A3 10a23960` |
| 4 | 脚本冻结 + 只读 | `M5C2-B7-SCRIPTS-FREEZE.json 558fd9aa`、`M5C2-B7-READINGS-FREEZE.json 1aa290e4` |
| 5 | 严格 host gate 记录 | `M5C2-B7-HOSTGATE-BEFORE.json`（strict gate_ok；仅 lone dwm；未用 v1.1 具名例外） |

## 1 定义

- **一次性**：绑定 **75 题数据集**，不绑机器/驱动/时间窗；换机/换驱动/重装后重跑 = **重跑**（消耗配额）。
- **阶段码**：`S0 环境`（gate 前）、`S1 加载`（模型/dll/上下文初始化）、`S2 首题 prefill`（未生成 token）、`S3 生成`（任一 token 已生成）、`S4 判据/抽取/解析`（离线或在线）、`S5 两读/结果件`（DECIDE/WIDE/READINGS）。
- **token-bearing 产物**：任何含模型生成文本的文件（raw answer、GEN json、含生成文本的日志）。

## 2 消耗判定（以落盘为准）

**A1** 以 token-bearing 产物落盘为准，不以内部分支/意图为准。
**A2** token-bearing 产物数 ≥1 ⇒ 消耗（唯一例外：审计日志证明未读；默认不存在）。
**A3** 仅以下四项**同时**成立才可判「装置未消耗」：①阶段码 ∈ {S0,S1,S2}；②`n_tokens_generated=0`；③token-bearing 产物数=0；④rates/两读产物不存在。

## 3 归类权

**A4** 「装置不合格」只能由 inspector（非执行者、非 LEAD 单独）按 A3 检查单判定并签名；LEAD 复核；证据含 boot_id before/after、gate 四项、阶段码、产物清单（路径+sha256+字节）。
**A5** 执行者自述"没跑起来"不构成装置不合格。
**A6** 若生成中出现 GPU 异常（WATCHDOG/驱动重启/BSOD）：**已有任何 token-bearing 输出** ⇒ 属运行结果，按 B7 预置规则处理，不得重跑；无输出 ⇒ 按 A3 归装置不合格；同时记录 boot_id 是否变化。
**A7** **在途绝不 SIGKILL**：只允许自然结束或失败返回；违反即记 `未接上（违反 GPU 在途纪律）`。

## 4 partial

**A8** 任何 `0<k<75` 已完成的 partial 结果 ⇒ 一次性已消耗；不续跑、不拼接；partial 封存 `_aborted_<UTC ts>/`（只读、永不并入）。
**A9** 仅 A3 四项成立（零输出）时才可重跑。

## 5 重跑配额

**A10** 重跑配额 = **1 次**（全新跑、禁拼接、禁复用 partial）；第二次仍零输出失败 ⇒ 记 `blocked_by_device`，停。
**A11** 每次重跑必须重新记录 gate 四项并 hash。

## 6 阶段分离

**A12** S4/S5（抽取/判定/两读）失败不触发重跑；只允许从已落盘产物做**离线重判**，落盘 rejudge 原因、新老 diff、产物 sha；重判不消耗一次性。
**A13** 只有 S0–S3 故障才可能触发重跑。

## 7 封存与留痕

**A14** 被 abort 的尝试目录封存 `_aborted_<UTC ts>/`：只读、不删、不改；全部产物 sha256 入台账。
**A15** 台账逐次记：attempt_id、时间、gate 四项 hash、阶段码、产物清单、消耗判定、inspector 签名、LEAD 裁决。

## 8 结果件身份（三层并记）

任何 b7′ 结果件必须写：
- 数据集：`M5C2-B7-QUESTIONS.json f1f059539453d562 / 15,964 B` + `RULING-M5C2-B7.md 3dfafd12`
- 判定层：`run_m5c2_rev7_2_offline.py 17c8e32a16b75947` + `M5C2-REV7-2-FREEZE.json 87a13b0c9aeae083`
- 读法层：`RULING-M5C2-B7-A2.md 320b643a`、`A3.md 10a23960`、`run_m5c2_b7_readings.py 5fae02247f8103b2`
- 并注明：b7′ **不是** b5 的 replication（`outside_protocol` 由 RULING B7 处置），结论不得升级 b5。

## 9 样本量兜底（现在冻结）

**A16** 两率分母在盲标后确定：若 `n_fp<20` 或 `n_leak<20` ⇒ 记 `未接上（样本量不足）`；不得改判达标、不得据此重跑。
**A17** `undecidable_on_gold_support / n_fp_eligible >15%` ⇒ FP 读数带 caveat「分母含高比例免检」，不得仅凭 FP 达标宣称判据可用（见 A3 R4）。

## 10 边界

- 不改题面/rev7.2/读法件/任何 b5-b6 冻结件与产物；不跑 GPU 直到 §0 五件齐备。
- 本件是治理裁定，不参与 H1 计算。
