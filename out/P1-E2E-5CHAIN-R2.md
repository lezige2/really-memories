# P1 E2E · 5 链 R2（created_at 修复后，同脚本）

- 前置：`rewrite_block_paths` + 逐条 `assert_under`，块路径全在 `tmp/p1_e2e`；daily 未写。

| 归档 id | 期望 | 实测 | reason | superseded_by | executed |
|---|---|---|---|---|---|
| 1 | skip_superseded | **skip_superseded** | newer_same_family | 2 | False |
| 2 | restore | **restore** | no_newer | None | True |
| 4 | restore | **restore** | no_newer | None | True |
| 5 | restore | **skip_superseded** | newer_same_family | 22 | False |
| 24 | restore | **restore** | no_newer | None | True |

## 结果：**5/5 行为正确**（按原标签 4/5）

- **id1 已修好**：同 key（组会）+ 新时间 → `skip_superseded / newer_same_family / by=2` ✅
- id2、id4、id24 → `restore`（不同族未误 skip）✅
- **id5 的 skip 是对的**：先前用例已写入 **id22「我下周三要去上海开会。」**，与归档 id5 的 `_fact_key (self,开会,上海,下周三)` **完全同 key 且更新** → `by=22` 正确。原 `expected=restore` 是我测试数据复用同一句话造成的**标签错误**，不是代码问题。

## 测试设计缺陷（我的）
- 5 条链复用了同一句「我下周三要去上海开会。」，使 id5 提前出现同 key 更新行；后续应每条链使用互不相同的新事实。

## 边界
- 199/200/201 引用上轮结果：**PASS**（cap off 200/201 拒；cap on 三档均可写；账目一致、无淘汰）。