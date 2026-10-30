# P0 event_date 迁移 dry-run（两轮 ensure→drop，只读现网）

- 源库 `D:\llama-mem\kvmem\daily\chat.db` sha `0a7eae495c4be89c`；备份 `D:\llama-mem\tmp\p0_dryrun\chat.db.orig` sha `0a7eae495c4be89c`
- 迁移脚本 `tools/memory_source.py` sha `2f6aece4b87546ad`
- 原值：user_version=0，columns=13，memory_meta=absent
- 现网未写、未切 flag、未 commit；写只落 `tmp/p0_dryrun`（local only）。

## 两轮 ensure→drop

| 轮 | uv 中→后 | 列回原 | meta 回原 | 内容 sha 同 | 行 | 块 sha 同 | 全过 |
|---|---|---|---|---|---|---|---|
| 1 | 2→0 | True | True | True | True | True | True |
| 2 | 2→0 | True | True | True | True | True | True |

- 每轮新增 7 列、user_version→2；drop 后 user_version→原值 0。
- 每轮哈希：before/mid/after 内容 sha 见 JSON rounds[].post.content_sha256 等。

## 关键查询静态对比（未调模型）

| suite | case | 一致 | pre ok | post ok |
|---|---|---|---|---|
| daily | daily-plate | True | True | True |
| daily | daily-cat | True | True | True |
| 81 | s01 | True | True | True |
| 81 | s02 | True | True | True |
| MT20 | V9MT05 | True | True | True |
| MT20 | V9MT06 | True | True | True |

## 判定

- **PASS：可迁移**（schema_ok=True, rounds_all_restored=True, query_static_same=True）

## 6 结论补充（B 2026-10-30）

- **现网未迁移、`--event-date` 默认 off；启用需用户点头**。
- `memory_meta` 只有 `created_memory_meta=true` 时才删；迁移前已存在且有其他数据时不得删。
- 回滚恢复原 `user_version`（含 1/5 非 0 原值），连续三轮 ensure→drop 内容 sha 不变。
- 本 dry-run 判 pass，但**不等于启用**；无消费方前不迁移。
