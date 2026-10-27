# RULING-M5C2-B7-A3（b7′ 两读并列与 undecidable 披露 · 冻结 v1）

> 性质：**跑 b7′ 之前的读法预置**；不改 H1 定义/阈值/分母口径，只规定"报什么、怎么降级"。
> 依据：顾问 2026-10-27 两轮复核；`M5C2-REV7-2-CLEANBLIND-DECISION.json 5d27944cb1e02f99`；`RULING-M5C2-B7-A2.md`；`M5C2-REV7-2-FREEZE.json`。

## R1 读法敏感（事实）

- 清盲实现者（未看验收断言）自然选择 **宽读法 B（任意子串包含）**；
- 窄读法 A（整句自证据，去尾标点）与冻结 DEV `a1137c5c` **逐句 diff=0**；
- 宽读法 B 与冻结 DEV **diff=2**（`b5-s4-q1-s01`、`b5-s6-q2-s08`，map `dfdfbeef48c9ca86`）；
- ⇒ 「evidence ⊂ 答案句」**不是唯一自然读法**，rev7.2 的 b5 dev 读数对读法敏感。

## R2 b7′ 必须两读并列报

- 主读数：rev7.2 冻结实现（窄读法 A），`M5C2-B7-DECIDE.json`；
- 敏感性读数：宽读法 B，`M5C2-B7-WIDE-SENSITIVITY.json`（脚本 `616380af352092d8`）；
- 结果件必须并列两组：四档计数、两率+Wilson、`n_fp`/`n_leak`、以及逐句 diff（B vs A）。

## R3 结论降级规则

- 两读的**判定档一致** ⇒ 按该档报，并在正文写明"两读一致"；
- 两读判定档**不一致** ⇒ 结论**降级为「擦边/不可判」**（取较重档），并写明"结论对读法敏感"；
- 禁止只报对自己有利的那一读。

## R4 undecidable 披露（分母免检问题）

- 结果件必须并列：`n_fp_eligible`（= gold support 总数）、`undecidable_on_gold_support{k,n,rate}`、`fp_readings{canonical: k/n, undecidable_in_denominator: k/(n−und)}`；
- b5 参照：`16/72 = 22.2%`，两读 `2/72=2.78%` 与 `2/56=3.57%`；
- **预置规则**：b7′ 若 `undecidable_on_gold_support / n_fp_eligible > 15%` ⇒ FP 读数必须带 caveat「分母含高比例免检」，且**不得仅凭 FP 达标宣称判据可用**；
- 该规则**不是改门槛**：H1 的判定仍按冻结定义，caveat 只约束"可用性宣称"。

## R5 禁止

- 不得在 b7′ 读数出来后选择读法或改降级规则；
- 不得用 b5 dev 的 2.78% 当作 b7′ 预期（见 A2）；
- 不得据 b7′ 调参重跑 rev7.2。
