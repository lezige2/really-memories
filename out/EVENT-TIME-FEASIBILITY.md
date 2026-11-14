# 事件时间可行性（离线，10 条）

anchor 统一 `2026-11-06`（除 E09 指定 2026-12-30）；`event_time` 只能抽绝对日期，
相对词由 anchor 规则归一，两者分开记。

| id | 类型 | 块 | event_time | 归一 | 级别 | 判定 |
|---|---|---|---|---|---|---|
| E01 | judgeable | 明年我打算考一个证书。 | — | 2027 | Y | judgeable |
| E02 | judgeable | 下周三我要去上海开会。 | 2026-11-11 | 2026-11-11 | D | judgeable |
| E03 | judgeable | 下个月要交续租合同。 | — | 2026-12 | M | judgeable |
| E04 | judgeable | 后年我打算搬到杭州。 | — | 2028 | Y | judgeable |
| E05 | judgeable | 上周我去南京出差了。 | — | 2026-10-26..2026-11-01 | R | judgeable |
| E06 | judgeable | 三年前我在苏州上班。 | — | 2023 | Y | judgeable |
| E07 | unanswerable | 下个月要交续租合同。 | — | 2026-12 | M | abstain |
| E08 | unanswerable | 我养的猫叫豆豆。 | — | no_time_word | - | abstain |
| E09 | ambiguous | 下周三（2026-11-11）我要去 | 2027-01-06 | conflicting_time:2026-11-11|2027-01-06 | - | fallback |
| E10 | ambiguous | 明年3月和下个月我要去两趟北京。 | — | multi_time_ambiguous:2027|2026-12 | - | fallback |

## 汇总

- 通过 **10/10**；无答案是否全 abstain：**True**；歧义是否全回退：**True**
- `event_time` 自身覆盖：绝对日期 2/10（相对词 0，需 anchor 层补）
- 门（≥8/10 且无答案全 abstain 且歧义全回退）：**通过**

## 口径分离
- **event_time 覆盖**：本表 `event_time_event_date` 列，只对绝对日期有值。
- **普通检索质量**：本轮未跑检索/模型，N/A —— 不与时间抽出混算。