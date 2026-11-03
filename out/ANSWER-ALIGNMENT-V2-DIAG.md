# answer_alignment v2 逐条诊断

## 20 负例

| id | asked_pred | answer_slot | decision | reason | fail_open | cause | 含别槽值 |
|---|---|---|---|---|---|---|---|
| P2-N01 | 车牌 | 车牌 | reject | facet_time_mismatch | False | - | 验证码,IMEI,车牌 |
| P2-N02 | 门牌号 | 门牌号 | pass | no_value_for_asked_slot | True | answer_no_value | - |
| P2-N03 | 密码 | 密码 | reject | other_slot_value:公司 | False | - | 公司 |
| P2-N04 | None | None | pass | no_asked_predicate | True | query_no_predicate | 公司 |
| P2-N05 | 学号 | 学号 | pass | no_value_for_asked_slot | True | answer_no_value | - |
| P2-N06 | 公司 | 公司 | reject | no_aligned_block | False | - | 公司 |
| P2-N07 | None | None | pass | no_asked_predicate | True | query_no_predicate | - |
| P2-N08 | 上牌年份 | 上牌年份 | reject | other_slot_value:IMEI | False | - | 验证码,IMEI,车牌 |
| P2-N09 | 护照 | 护照 | pass | no_value_for_asked_slot | True | answer_no_value | - |
| P2-N10 | None | None | pass | no_asked_predicate | True | query_no_predicate | - |
| P2-N11 | 密码 | None | pass | no_asked_subject | True | query_no_subject | 验证码,IMEI,银行卡,尾号,分机 |
| P2-N12 | None | None | pass | no_asked_predicate | True | query_no_predicate | - |
| P2-N13 | 年检 | 年检 | pass | no_value_for_asked_slot | True | answer_no_value | - |
| P2-N14 | IMEI | IMEI | reject | no_aligned_block | False | - | 验证码,IMEI |
| P2-N15 | 公司 | 公司 | reject | no_aligned_block | False | - | 公司 |
| P2-N16 | 银行卡 | 银行卡 | reject | other_slot_value:公司 | False | - | 公司 |
| P2-N17 | 会议号 | 会议号 | pass | no_value_for_asked_slot | True | answer_no_value | - |
| P2-N18 | 猫 | 猫 | pass | no_value_for_asked_slot | True | answer_no_value | - |
| P2-N19 | 工位 | 工位 | reject | other_slot_value:公司 | False | - | 公司 |
| P2-N20 | 邮编 | 邮编 | pass | no_value_for_asked_slot | True | answer_no_value | - |

## 10 正例

| id | decision | reason | fail_open | 原答案含 expected |
|---|---|---|---|---|
| P2-H01 | reject | no_aligned_block | False | False |
| P2-H02 | reject | no_aligned_block | False | False |
| P2-H03 | reject | no_aligned_block | False | False |
| P2-H04 | reject | no_aligned_block | False | False |
| P2-H05 | pass | no_asked_subject | True | False |
| P2-H06 | pass | aligned_block | False | True |
| P2-H07 | pass | no_value_for_asked_slot | True | False |
| P2-H08 | pass | no_value_for_asked_slot | True | False |
| P2-H09 | pass | aligned_block | False | False |
| P2-H10 | pass | aligned_block | False | True |

## 汇总
- 负拒 8/20；fail_open 12（{'query_no_predicate': 4, 'query_no_subject': 1, 'answer_no_value': 7}）；正过 6/10；误拒 ['P2-H01', 'P2-H02', 'P2-H03', 'P2-H04']；原答案不支持 ['P2-H01', 'P2-H02', 'P2-H03', 'P2-H04', 'P2-H05', 'P2-H07', 'P2-H08', 'P2-H09']
