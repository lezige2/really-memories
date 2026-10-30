# K2 跳 dup · hygiene 六样证据

## 1 备份与副本

- daily 备份 `kvmem/daily/chat.db.bak-hygiene-20261031T002748`，sha `0a7eae495c4be89c`，192512 B（**daily 全程未改**）
- pre 副本 `kvmem/hygiene/pre/chat.db` sha `d7753b74daec7247`；post 副本 `kvmem/hygiene/post/chat.db` sha `af6e2b466029f745`

## 2 tags 编辑（仅 3 行）

| id | tags |
|---|---|
| 3 | `["plate:京A88888","context:primary"]` |
| 12 | `["plate:京A88888","dup_of:3","context:restatement"]` |
| 13 | `["plate:京A88888","dup_of:3","context:restatement"]` |

- dump 30 行：**只有 3 行变**；pre dump sha `3b171f919b66cbeb`，post dump sha `a2d26e7d1ee468a1`

## 3 42 条逐条 before/after

| 项 | pre | post |
|---|---|---|
| pass | **36/42** | **33/42** |
| 变化条数 | — | 8 |

| id | pre pass | post pass | pre blocks | post blocks |
|---|---|---|---|---|
| KVC05 | True | False | [22] | [22, 12, 13] |
| KVC06 | True | False | [22] | [22, 12, 13] |
| KVC16 | True | True | [22] | [22] |
| KVC18 | False | False | [22] | [22] |
| KVC20 | True | False | [21, 22, 3, 12] | [21, 22, 3, 12, 13] |
| KVC21 | True | True | [22] | [22] |
| KVC23 | True | True | [22] | [22] |
| KVC30 | False | False | [22, 1, 2, 5] | [22, 1, 2, 5] |

- 3 条由 pass→fail：**KVC05、KVC06、KVC20**——post 侧多挂载了 12/13（restatement 块）；其余 5 条 pass 不变但 block_ids 变化。
- 无 fail→pass。

## 4 K2-off 下 id3/12/13 仍可检索

- 查询「我的车牌号是多少？」：rank_off（K2-off 等价）top20 = `[3, 12, 13]`，三 id **全在**（rank 1/2/3）；gate-on retrieve 亦含三 id。

## 5 dup 单测

- `python -X utf8 -m unittest discover -s tools -p "test_k2_dup_cpu.py"` → **Ran 2 tests ... OK**（`tools/test_k2_dup_cpu.py` 已存在）

## 6 回滚

- post_rb 副本还原 tags 后：pre dump sha `3b171f919b66cbeb` = rollback dump sha `3b171f919b66cbeb`，**逐字节相同**（30 行）。
- 回滚 SQL：
```sql
UPDATE daily_memory_meta SET tags='[]' WHERE source_id=3;
UPDATE daily_memory_meta SET tags='[]' WHERE source_id=12;
UPDATE daily_memory_meta SET tags='[]' WHERE source_id=13;
```

## 结论

六样证据齐备；**tags 引入 3 条回归（36→33）**，建议不为 dup 块加 `plate:` 标签（或改为不影响检索排序的元数据），并保留回滚路径。
## 7 post2 变体（dup_of-only，预注册）
- tags：id3 `["context:primary"]`；id12/13 `["dup_of:3","context:restatement"]`（无 `plate:`）
- 预注册：必须逐字等于 pre 的 **36/42**（answer/state/block_ids/pass 全同）
- 实测：pre **36/42** → post2 **33/42**，**6 条不同**，其中 **3 条 pass→fail（KVC05、KVC06、KVC20）**，block_ids 均多出 12/13
- 判定：**FAIL —— 未逐字相同**；`dup_of:` 同样被当检索键（tags 加权），按 B 裁定直接停，不做 5×；不写 daily，仅留证据

## 8 最终判定（2026-10-31 01:05）

- **原 tag（plate:）FAIL**：42 36/42→33/42，3 条 pass→fail；
- **dup_of-only FAIL**：36/42→33/42，同样 3 条 fail；
- 原因：**tags 参与检索加权，标签即检索键**；restatement 12/13 被拉进挂载。
- 处置：不写 daily、不改 tags；daily 保持 `0a7eae49…`；回滚 SQL 留档。
- 教训：语义标签必须放不参与打分的 sidecar，不能塞 `daily_memory_meta.tags`。
