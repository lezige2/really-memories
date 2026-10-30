# S2 闸代价诊断（n200 副本，只测量）

- 源 `D:\llama-mem\kvmem\scale40k\n200\chat.db` sha `2d84aefda3c76ece`；副本 `D:\llama-mem\tmp\s2_gate\chat.db`；未改阈值/默认、未写库、未起服务。
- 开闸=现状 `retrieve(topk=20)`（coverage 0.30 等 gate）；关闸=诊断脚本内绕过 gate，只按 score 取 top20。

| suite | id | target | 开闸 in/rank | 关闸 in/rank | target score/cov |
|---|---|---|---|---|---|
| repro | q048 | 53 | False / None | True / 3 | 2.0 / 0.2 |
| repro | q052 | 70 | False / None | True / 4 | 1.0 / 0.143 |
| repro | q060 | 25 | False / None | True / 1 | 3.0 / 0.273 |
| repro | q062 | 130 | False / None | False / 22 | 1.0 / 0.2 |
| repro | q063 | 144 | False / None | False / 26 | 1.0 / 0.2 |
| heldout | S2H01 | 58 | True / 13 | True / 13 | 2.0 / 0.2 |
| heldout | S2H02 | 71 | False / None | True / 4 | 1.0 / 0.125 |
| heldout | S2H03 | 124 | False / None | True / 3 | 2.0 / 0.182 |
| heldout | S2H04 | 129 | True / 1 | True / 1 | 3.0 / 0.429 |
| heldout | S2H05 | 121 | True / 1 | True / 1 | 3.0 / 0.333 |

## 汇总
- repro：开闸 0/5，关闸 3/5；empty 开/关 = 3/0
- heldout：开闸 3/5，关闸 5/5；empty 开/关 = 2/0
- 关闸救回：['q048', 'q052', 'q060', 'S2H02', 'S2H03']
- 关闸仍不进池：['q062', 'q063']

## 结论
- 关闸后能救回：repro=3/5, heldout=5/5；仍有目标不进 top20 → 闸之外还有排序/词面问题，需再评估 C
