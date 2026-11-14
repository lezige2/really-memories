# coverage 过滤顺序诊断（只读）

- DB `kvmem/scale40k/n200/chat.db` sha `2d84aefda3c76ece`；未改阈值/未写码/未写库。
- gate 代码：`memory_service.py:157-170`（`best = scored[0]`，coverage>=0.30）。

| query | tokens | top1(id/score/cov) | target rank | target(score/cov) | scored | cov>=.3 |
|---|---|---|---|---|---|---|
| q048 | 10 | 8/2.0/0.2 | 3 | 2.0/0.2 | 50 | 0 |
| q052 | 7 | 12/1.0/0.1429 | 4 | 1.0/0.1429 | 10 | 0 |
| q060 | 11 | 25/3.0/0.2727 | 1 | 3.0/0.2727 | 70 | 0 |
| q070 | 6 | 12/1.0/0.1667 | 10 | 1.0/0.1667 | 10 | 0 |

## 诊断

- **不是过滤顺序 bug**：coverage=|hits|/|qt|，score=|hits|(+tag)；按 score 排序时 top1 已是最大 coverage。
- 这 4 条全集中 **0 条 cov>=0.30**（max 即 top1 的 0.20/0.143/0.273/0.167），所以 gate 清空不是丢掉高 cov target。
- q060 特殊：target **就是 top1**，cov 0.273，距阈值 0.30 只差 0.027；q048/q052/q070 target 与 top1 同分同 cov。
- 仅当 tag 加分把少命中块抬到 top1 时，才可能出现“top1 非最大 cov”；现库 tags 为空，未触发。

## 修正方案（未实施）

- `best = max(scored[:N], key=lambda x:(x['coverage'], x['score']))` 用于 gate；对这 4 条**无效**（max cov 未变）。
- 影响面：只影响 tag/其它加分造成 top1 非最大 cov 的库；不改阈值；风险是弱证据池被放行，需用 20 条负例（P2-NEG）复核。

## 结论

- **不是顺序 bug，是阈值与口语覆盖上限不匹配**；不改阈值、不写码；本诊断只读。
