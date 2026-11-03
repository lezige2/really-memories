-- norm_hash 去重：restate 计数（默认开；旧行不受影响）
-- 列默认 restated_count=0 / last_restated_at=NULL；不删任何行、不改 created_at。
BEGIN;
ALTER TABLE memory_source ADD COLUMN restated_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE memory_source ADD COLUMN last_restated_at TEXT;
COMMIT;
