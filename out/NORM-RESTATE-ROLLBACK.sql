-- 回滚：删两列（SQLite >= 3.35）；如需保留计数可先导出。
BEGIN;
ALTER TABLE memory_source DROP COLUMN last_restated_at;
ALTER TABLE memory_source DROP COLUMN restated_count;
COMMIT;
