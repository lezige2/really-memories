# ALIGN blind 40 结果（冻结 sha `008297f4ef3cd9e89f6bd3b175ecb05ba64f0587fd307287fce957f0db672589`，只跑一次）

## 汇总
| 指标 | 结果 |
|---|---|
| 正例 | 14/20 pass，误拒 6 |
| 负例(19) | 14/19 reject，误放行 5 |
| no_asked_predicate | N01, N04, N07 |
| N14 | uncertain，单列不计门 |
| 门 | FAIL |

## 误放行
- N01 cross_slot:车牌 (我的保险到期日是哪天？)
- N04 cross_slot:工位 (我的工牌号是多少？)
- N07 cross_slot:猫 (我是什么血型？)
- N15 subject_mismatch:问张伟答阿泽 (张伟的车牌号是多少？)
- N16 subject_mismatch:问张伟答阿泽 (张伟的手机号是多少？)

## 误拒
- A03 (no_value_for_asked_slot): 我目前的就职单位是哪家？
- A05 (no_value_for_asked_slot): 我的工位在哪？
- A08 (no_value_for_asked_slot): 我的评审会在哪开？
- A12 (no_value_for_asked_slot): 我的座位号是多少？
- A18 (no_value_for_asked_slot): 我周几有组会？
- A20 (no_value_for_asked_slot): 我对什么过敏？

## 按 kind
- cross_slot: 总 8 / 误放行 3
- approx_only: 总 5 / 误放行 0
- subject_mismatch: 总 6 / 误放行 2

## N14
- uncertain（公司简称/全称），单列不计门

## N02
- reject / no_value_for_asked_slot；answer 为公司值，按 other_slot 拒，非敏感语义全功

## 逐条（冻结跑一次）

| id | 组 | decision | reason | 期望 |
|---|---|---|---|---|
| A03 | positive | reject | no_value_for_asked_slot | pass |
| A05 | positive | reject | no_value_for_asked_slot | pass |
| A08 | positive | reject | no_value_for_asked_slot | pass |
| A12 | positive | reject | no_value_for_asked_slot | pass |
| A18 | positive | reject | no_value_for_asked_slot | pass |
| A20 | positive | reject | no_value_for_asked_slot | pass |
| N01 | negative | pass | no_asked_predicate | reject |
| N04 | negative | pass | no_asked_predicate | reject |
| N07 | negative | pass | no_asked_predicate | reject |
| N15 | negative | pass | aligned_block | reject |
| N16 | negative | pass | aligned_block | reject |
