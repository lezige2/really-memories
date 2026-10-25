# PREREG — 14B E10 探针（先写预测，后跑）

写下时间：2026-10-25（S1–S3 开跑之前）。**A3/A6/C1 的三次 run 早于本文件**，它们的预测是事后补记的，
在此明确标注：那些不是预登记，只有 S1/S2/S3 是。

## 臂级预测（S 单块臂，本文件写下后才跑）

| 臂 | 布局 | 总 cells | 预测 | 依据 |
|---|---|---:|---|---|
| S1 | `iso_home_only` 只挂 home(21) | 21 | **hit 3/3 期望 → 只有 1 问** | evidence_4cell.json 的 run0（iso_home_only, 21 cells）在 14B 上 fact_ok=true；C1(51) 也 hit。单块是最宽松条件 |
| S2 | `iso_project_only` 只挂 project(18) | 18 | **hit** | C1(51) 含 project 时 hit；4-cell 阶段 iso_fac_pp18 用的是同一 project 事实且 hit |
| S3 | `iso_habit_only` 只挂 habit(12) | 12 | **hit** | C1(51) 含 habit 时 hit；habit 是 7B 唯一恒过的段 |

止损条款（lead 定）：S1 失败而 S2 通过 ⇒ 问题不在注意力分配，立即停手上报。
**本装置上该条款不适用**：三臂预测全 hit，若真出现 S1 miss / S2 hit 我会按条款停。

## 事后补记（早于本文件，非预登记）

| 臂 | 布局 | 总 cells | 当时预测 | 实测 |
|---|---|---:|---|---|
| C1 | `iso_no_car` home+project+habit | 51 | （未预登记）本轮 brief 说 14B 基线已知通过 | hit 3/3 |
| A3 | `iso_dup4` + project2 副本(18) | 69 | （未预登记）7B 上通过 | hit 3/3 |
| A6 | `iso_habit_bot` + habit2 副本(12) | 63 | （未预登记）7B 上失败；三条候选机制都预测失败 | **hit 3/3（与 7B 相反）** |
