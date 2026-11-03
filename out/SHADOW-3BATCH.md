# Shadow 三批结果（冻结规则、每批只跑一次）

- 冻结 sha `dde8d66db7dc87bb606a90e9f2af66afe12e61643f62d01bceb1505d891ae9f7`（一致）

| 批次 | n | same/diff | 误合并 | 漏合并 | 一致率 | 盲测 |
|---|---|---|---|---|---|---|
| R1 调参 | 98 | 36/62 | 0 | 0 | 100.00% | 否 |
| R2 盲测 | 98 | 36/62 | 0 | 0 | 100.00% | 是 |
| REAL 盲测 | 49 | 17/32 | 1 | 14 | 69.39% | 是 |

## REAL T001–T017 逐条

| pair | label | pred | ok | risk | score |
|---|---|---|---|---|---|
| T001 | different | False | True | low_similarity | 0.200 |
| T002 | different | False | True | family_mismatch | 0.000 |
| T003 | different | True | False | None | 0.333 |
| T004 | different | False | True | negation | 0.000 |
| T005 | different | False | True | negation | 0.000 |
| T007 | different | False | True | value_mismatch | 0.000 |
| T008 | different | False | True | value_mismatch | 0.000 |
| T009 | different | False | True | low_similarity | 0.600 |
| T010 | different | False | True | low_similarity | 0.556 |
| T011 | different | False | True | low_similarity | 0.375 |
| T012 | different | False | True | value_mismatch | 0.000 |
| T013 | different | False | True | negation | 0.000 |
| T014 | different | False | True | low_similarity | 0.000 |
| T015 | different | False | True | negation | 0.000 |
| T016 | different | False | True | low_similarity | 0.417 |
| T017 | different | False | True | low_similarity | 0.000 |

## 门
- 误合并=0 → **FAIL**（T003 误合并 1）
- 漏合并≤5% → **FAIL**（14/49=28.6%）

## Jaccard 0.80 评估
- 仍不合适：REAL 漏合并的 paraphrase 分数 0.04–0.39（远低于 0.80）；S001–S017 多为换词/省略，非阈值问题。
- 降阈值会放大误合并（T003 类“换牌 vs 又添一辆”已在同族同值下误判）；应先补主体/多实体与值归一，而不是调阈值。

结果 JSON：`out/SHADOW-3BATCH.json`
