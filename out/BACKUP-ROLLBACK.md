# 备份 / 回滚 / 观察期

## 1 日常备份（DB）
```powershell
python -X utf8 tools/rollback_entry.py backup --db kvmem/daily/chat.db --out out/backup/chat.db --apply
python -X utf8 tools/rollback_entry.py drill --db kvmem/daily/chat.db
```
- 备份写 `.sha256` sidecar；
- drill：备份→临时恢复→表/行/内容 sha 比对，输出 PASS/FAIL。

## 2 块文件备份
```powershell
Copy-Item -Recurse -Force kvmem/daily/blocks out/backup/blocks
```
块文件不在 SQLite 里，必须单独备份；`healthcheck` 会验路径存在。

## 3 归档前自动备份
- `auto_archive` 触发前写 `out/p1/backup/<ts>/chat.db` + blocks sha；
- audit `stage=archive decision=backup` 记 db_sha/blocks_sha；
- 首次真实归档还需 `--confirm-first-archive`（或状态文件）；签署条件：容量有压力/≥150 条 + 副本 200 条 archive→restore→回滚演练通过。
- 触发时必须显示“已归档 N 条，可回滚”，禁止静默搬。

## 4 回滚命令
```powershell
# 单条/整库
python -X utf8 tools/rollback_entry.py restore --backup out/backup/chat.db --target kvmem/daily/chat.db --force --apply
# 归档包恢复（dry-run 先）
python -X utf8 tools/archive_admin.py restore --zip out/archive/2026-08.zip --sidecar out/archive/2026-08.zip.sidecar.json --live live.json --out plan.json --apply
```
- 恢复前先停服务；
- 归档 restore 只对副本/计划，绝不直接无脑写 daily；
- 回滚后跑 `healthcheck` + 81/extra/MT20。

## 5 观察期（前 3 次真实归档 / 第一周）
判回滚的证据（任一）：
1. `healthcheck` 行/块/路径不一致；
2. 81 或 extra 出现**新增 fail**（不在冻结 flaky 清单）；
3. `memory_source` 行数减少/文本被改；
4. 归档 zip/sha 不匹配、fallback 命中错块；
5. audit 出现 `archive_blocked` 以外的异常，或回热旧值复活。

谁判：A/B 先判，用户最终确认；回滚执行人 E/D，A 复核。
回滚动作：停服务 → 关 flag → 恢复 DB/blocks → drill → 验收。