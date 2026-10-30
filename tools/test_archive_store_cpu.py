# -*- coding: utf-8 -*-
"""P1 归档能力单测：本地 zip/sidecar、sha-only 恢复、防覆盖、幂等、回滚。

Run: python -X utf8 -m unittest discover -s tools -p "test_archive_store_cpu.py" -v
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import archive_store as A  # noqa: E402


def make_rows(n=20):
    rows = []
    for i in range(1, n + 1):
        text = "合成老块 %d：我的车牌号是京A%05d。" % (i, i)
        rows.append({
            "id": i, "name": "old-%d" % i, "text": text,
            "subject": "王强" if i % 2 else "杨帆",
            "predicate": "车牌", "created_at": "2026-10-01T%02d:00:00" % (i % 24),
            "block_sha": hashlib.sha256(("blk-%d" % i).encode()).hexdigest(),
            "block_bytes": 1000 + i,
        })
    return rows


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="p1_arch_")
        self.zip = os.path.join(self.tmp, "old.zip")
        self.side = os.path.join(self.tmp, "old.sidecar.json")

    def test_roundtrip_20(self):
        rows = make_rows(20)
        before = A.content_hash(rows)
        m = A.archive_rows(rows, self.zip, self.side)
        self.assertEqual(m["n"], 20)
        loaded = A.load_archive(self.zip, self.side)
        self.assertEqual(loaded["zip_sha256"], m["zip_sha256"])
        # id/文本/块 sha/字节 全等
        for orig, ent in zip(rows, loaded["entries"]):
            self.assertEqual(ent["id"], orig["id"])
            self.assertEqual(ent["text_sha256"],
                             hashlib.sha256(orig["text"].encode()).hexdigest())
            self.assertEqual(ent["block_sha256"], orig["block_sha"])
            self.assertEqual(ent["block_bytes"], orig["block_bytes"])
        plan = A.restore_plan([], self.zip, self.side)
        self.assertEqual(sum(1 for x in plan["plan"] if x["action"] == "restore"), 20)
        restored = A.apply_restore([], plan, self.zip)
        self.assertEqual(len(restored), 20)
        self.assertEqual([r["id"] for r in restored], [r["id"] for r in rows])
        # 源内容哈希不变（模块不写 DB）
        self.assertEqual(A.content_hash(rows), before)

    def test_idempotent_archive_and_restore(self):
        rows = make_rows(6)
        a = A.archive_rows(rows, self.zip, self.side)
        b = A.archive_rows(rows, self.zip, self.side)
        self.assertEqual(a["zip_sha256"], b["zip_sha256"])       # 确定性 zip
        p1 = A.restore_plan([], self.zip, self.side)
        p2 = A.restore_plan([], self.zip, self.side)
        self.assertEqual(p1, p2)
        r1 = A.apply_restore([], p1, self.zip)
        r2 = A.apply_restore([], p1, self.zip)
        self.assertEqual(A.content_hash(r1), A.content_hash(r2))

    def test_superseded_not_revived(self):
        rows = make_rows(4)
        for r in rows:                      # 同一条链（subject+predicate 相同）
            r["subject"], r["predicate"] = "王强", "车牌"
        A.archive_rows(rows, self.zip, self.side)
        live = [{"id": 99, "name": "new", "text": "王强的车牌号是京B00001",
                 "subject": "王强", "predicate": "车牌",
                 "created_at": "2026-10-20T00:00:00"}]
        plan = A.restore_plan(live, self.zip, self.side)
        acts = {x["action"] for x in plan["plan"]}
        self.assertEqual(acts, {"skip_superseded"})               # 整链不动
        self.assertTrue(all(x["superseded_by"] == 99 for x in plan["plan"]))
        restored = A.apply_restore(live, plan, self.zip)
        self.assertEqual([r["id"] for r in restored], [99])       # 不复活

    def test_restore_only_on_sha(self):
        rows = make_rows(3)
        A.archive_rows(rows, self.zip, self.side)
        data = bytearray(open(self.zip, "rb").read())
        data[-10] ^= 0xFF
        open(self.zip, "wb").write(bytes(data))
        with self.assertRaises(A.ArchiveError):
            A.load_archive(self.zip, self.side)

    def test_local_only_assertion(self):
        with self.assertRaises(A.ArchiveError):
            A.assert_local_only(["https://example.com/old.zip"])
        info = A.startup_check()
        self.assertTrue(info["local_only"])
        self.assertFalse(info["auto_move"])
        # 模块不含网络对象、无定时/线程
        for bad in ("socket", "urllib", "http", "requests", "threading", "sched"):
            self.assertNotIn(bad, vars(A))

    def test_rollback_delete_restores_hash(self):
        rows = make_rows(5)
        before = A.content_hash(rows)
        A.archive_rows(rows, self.zip, self.side)
        os.remove(self.zip)
        os.remove(self.side)
        os.remove(self.zip + ".manifest.json")
        self.assertEqual(A.content_hash(rows), before)            # 内容哈希回原
        with self.assertRaises(A.ArchiveError):
            A.load_archive(self.zip, self.side)

    def test_migration_sql_frozen(self):
        root = os.path.dirname(_HERE)
        sql = os.path.join(root, "out", "P1-ARCHIVE-MIGRATION.sql")
        sha = os.path.join(root, "out", "P1-ARCHIVE-MIGRATION.sha256")
        self.assertTrue(os.path.exists(sql))
        body = open(sql, encoding="utf-8").read()
        self.assertNotIn("ALTER TABLE memory_source", body)
        self.assertIn("archive_index", body)
        self.assertEqual(hashlib.sha256(open(sql, "rb").read()).hexdigest().strip(),
                         open(sha, encoding="utf-8").read().strip())


if __name__ == "__main__":
    unittest.main()