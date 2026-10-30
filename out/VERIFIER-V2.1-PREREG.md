# Verifier v2.1 预注册（误触发修复，S0）

> 只改 verifier 的“可核对性判定/归一化”；禁止改检索、event_date、prompt、K2。
> 版本：`VERIFIER_VERSION=v2.1`（显式开启）；默认仍 v1。

## 1 误触发反例集（改前/改后各跑）

来源：`out/V9MT11-12-VERIFIER-DIAG.json`（C2，flag on 5×）。

| case | 输入 | kept | 改前 | 期望 |
|---|---|---|---|---|
| V9MT11 | 我在哪家公司上班？ | 22「我的公司是顺丰」 | 5/5 `unsupported`、repair 前答案含“顺丰” | 5/5 pass |
| V9MT12 | 我的公司叫什么？ | 22「我的公司是顺丰」 | 部分 `unsupported`（claim“过你的公司是顺丰”） | 5/5 pass |

根因：v2 把“你在顺丰公司工作 / 顺丰公司上班”当 claim，未归一化“公司是顺丰”↔“在顺丰公司工作”，判 `value_not_in_memory`，触发中性拒答。

## 2 允许的修法

1. 值归一化：全角/空格/标点/单位/格式；“顺丰公司”与“公司是顺丰”按实体值等价；
2. 可核对性默认方向：kept 块里出现该 subject+predicate 的值 → 可核对；只有确实找不到值才弃权；
3. repair 仍中性，不加 hint/期望值/KV 文本。

## 3 防放宽漏判（必须同时满足）

- L09 错值（答 88888、记忆 8899）→ 仍 `wrong_slot_value`，不得 pass；
- L07 显式拒答 → 按规则 pass（不逼答），但不得把“无据”判 pass；
- V9MT05 单块手机 → pass，不拒答；
- 81/extra/MT20 无新增 fail。

## 4 门（S0 过门才 S1）

- V9MT11/12 各 5/5 pass；
- 81=81/81、extra≥19、MT20≥18；
- L09 仍 fail（错值）、V9MT05 pass；
- 版本标签写入所有新数字；旧数字标 v2/旧基线，不混算。

## 5 不做

- 不改检索/K2/event_date/schema/daily；
- 不扩大“有值就 pass”到无槽/多值/否定句；
- 不默认开 v2.1。