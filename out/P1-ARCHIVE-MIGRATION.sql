-- P1 归档迁移（**本轮不执行**；仅归档能力，P1b 主体键/写时冲突另注册）
-- 迁移只建 archive 索引表，不 ALTER memory_source、不加列、不写 daily 库。
-- 回滚：DROP TABLE IF EXISTS archive_index; DROP TABLE IF EXISTS archive_meta;
BEGIN;
CREATE TABLE IF NOT EXISTS archive_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR REPLACE INTO archive_meta(key, value) VALUES ('archive_schema', 'p1_archive_v1');
CREATE TABLE IF NOT EXISTS archive_index (
    archive_id   INTEGER PRIMARY KEY,
    source_id    INTEGER NOT NULL,
    zip_path     TEXT    NOT NULL,
    zip_sha256   TEXT    NOT NULL,
    member       TEXT    NOT NULL,
    text_sha256  TEXT    NOT NULL,
    block_sha256 TEXT,
    block_bytes  INTEGER DEFAULT 0,
    subject      TEXT,
    predicate    TEXT,
    created_at   TEXT,
    is_archived  INTEGER NOT NULL DEFAULT 1,
    superseded_by INTEGER,
    archived_at  TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS archive_index_source_member
    ON archive_index(source_id, member);
COMMIT;
