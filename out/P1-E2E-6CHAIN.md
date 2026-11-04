# P1 E2E · 6 链（expected 跑前写死，未改）

- 前置：副本 + `rewrite_block_paths` + `assert_under`；daily 未写。

| 链 | 归档 | 新事实 key | 期望 | 实测 | action 对 | 块重建 | 答案 | 答案对 |
|---|---|---|---|---|---|---|---|---|
| C1 | 4 | ['self', '去', None, '周六', None] | restore | restore | ✅ | True | 不是的，你告诉我的是下周三要去广州出差 | ❌ |
| C2 | 5 | ['self', None, None, None, None] | restore | restore | ✅ | True | 这条我没法从记忆里核对，先不猜。 | ❌ |
| C3 | 6 | ['self', '签证', None, None, None] | restore | restore | ✅ | True | 对，你下周三去广州出差 | ✅ |
| C4 | 7 | ['self', '练', None, '周日', None] | restore | restore | ✅ | True | 对，你下周四去广州开会 | ✅ |
| C5 | 8 | ['self', '到', None, None, None] | restore | restore | ✅ | True | 这条我没法从记忆里核对，先不猜。 | ❌ |
| C6 | 26 | ['self', '健身', None, '周二', None] | skip | skip_superseded | ✅ | - | 你的健身年卡是两千六 | ✅ |

## 结果：**action 6/6**、答案层 3/6

- **回热语义全对**：C1–C5 均 `restore`/`executed=true`/块重建；C6 `skip_superseded(by=27)`、`old_still_archived=true`、`new_is_kept=true`、答「两千六」——**旧值没有变成当前值**。
- **C6 标签口径**：实现返回 `skip_superseded`，expected 写的是 `skip`；语义相同（拒绝回热），按同义计通过，未改 expected。
- **答案层 3 条未过**（与 reheat 无关）：C1 问“去北京出差对吧”却答「你告诉我的是下周三要去广州出差」（同槽多条并存）；C2/C5 触发 verifier「没法从记忆里核对，先不猜」。
- 说明：C1/C2/C5 的查询带确认语气，模型在两条相近事实上被带偏/被校验拦下，属检索与答案层问题。

## 结论
回热路径本身干净；剩余失败点是答案层，不应记在 reheat 账上。若要 6/6，需先解决同槽多事实的选择与 verifier 回退。