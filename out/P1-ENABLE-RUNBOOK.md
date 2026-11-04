# P1 开启运行手册（默认仍 off；待用户选 1/2/3）

## 0 当前基线
- HEAD `3f6b354`；382 tests OK；P1 技术门 6/6。
- daily：20 source / 20 block / 0 缺失；id14 为 reconstructed（原块不可恢复，Qwen 重建）。
- 默认全 off：`--lifecycle-cap`、`--memory-access`、`--lifecycle-archive`、`--lifecycle-fallback`、`--audit`。

## 1 开启前（必须）
```bash
# 1) 备份 daily DB + blocks
tools/rollback_entry.py backup --db kvmem/daily/chat.db --out out/p1-enable/chat.db --apply
powershell -Command "Copy-Item -Recurse -Force kvmem/daily/blocks out/p1-enable/blocks"
# 2) 备份 sha
sha256sum kvmem/daily/chat.db > out/p1-enable/chat.db.sha256
# 3) 建表（不 ALTER memory_source）
python -X utf8 - <<'PY'
import sqlite3,sys; sys.path.insert(0,'tools')
import memory_lifecycle as ml
con=sqlite3.connect('kvmem/daily/chat.db'); ml.ensure_schema(con); con.commit()
print(con.execute("select name from sqlite_master where name like 'memory_%'").fetchall())
PY
# 4) 回滚演练
tools/rollback_entry.py drill --db kvmem/daily/chat.db
```
要求：drill PASS、备份 sha 记录、daily 未被改写。

## 2 方案 1：全开（cap+access+archive+fallback）
运行时（不改默认）：
```bash
python tools/chat_service.py \
  --db kvmem/daily/chat.db --blocks kvmem/daily/blocks \
  --retrieval topk --topk 4 --n-gpu-layers 28 \
  --model "D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf" \
  --lifecycle-cap --memory-access --lifecycle-archive --lifecycle-fallback
```
说明：
- 20 条 < soft 200，archive 不会触发；仅建表/写 access；
- 200 后 `auto_archive` 按月归档；fallback 仅主池空时查归档；
- 回热仍是手动 `DailyApp.reheat`，未自动回写。

## 3 方案 2：先开 cap+access（推荐）
```bash
python tools/chat_service.py ... \
  --lifecycle-cap --memory-access
```
- 只改容量语义 + 访问记录；
- archive/fallback 保持 off，观察一轮；
- 200 后不自动归档，达到 2000 才拒。

## 4 方案 3：继续全 off
不动；P1 保持技术门通过但未启用。

## 5 开启后验收
1. 81/extra/MT20（K2 off/v1）：81 81/81、extra 17/19（剔 L05）、MT20 11；
2. daily 20 条：行/块不变、无丢失、`memory_access` 可写；
3. 200+ 副本：201 不 409、无淘汰、账目一致；
4. audit（若开）：约 1 条/ask、无原文、轮转/清理生效；
5. 任何一项回归 → 关 flag + 恢复备份。

## 6 回滚
```bash
# 关 flag（重启服务）
# 可选 drop 新表（不影响 memory_source）
sqlite3 kvmem/daily/chat.db "DROP TABLE IF EXISTS memory_access; DROP TABLE IF EXISTS memory_archive;"
# 若内容异常，整库恢复
tools/rollback_entry.py restore --backup out/p1-enable/chat.db --target kvmem/daily/chat.db --force --apply
```
注意：`memory_archive` 删表不会删 zip；zip 在 `out/archive/`，按需保留/删除。

## 7 已知边界
- answer 层 3/6（C1 检索冲突、C2/C5 verifier），P1 门不含答案，但产品默认仍弱；
- 200/2000 是临时软硬水位，未按真实容量曲线定；
- id14 为 reconstructed，逐字节比对作废；
- 回热未自动，仍手动。

## 8 待用户决策
1. 全开；
2. 先开 cap+access；
3. 继续全 off。

选 1/2 前必须完成第 1 节备份+drill；未完成不切默认。