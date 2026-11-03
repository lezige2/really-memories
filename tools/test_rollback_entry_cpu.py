# -*- coding: utf-8 -*-
"""rollback_entry 单测：backup sha / restore 成功与坏 sha / 非空拒绝 / drill 等价 / 不碰 daily。"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(HERE, "rollback_entry.py")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import rollback_entry as R      # noqa: E402
DAILY = os.path.join(ROOT, "kvmem", "daily", "chat.db")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def make_db(path):
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE memory_source(id INTEGER PRIMARY KEY, text TEXT, created_at TEXT);"
        "CREATE TABLE daily_memory_meta(source_id INTEGER PRIMARY KEY, tags TEXT);")
    con.executemany("INSERT INTO memory_source VALUES(?,?,?)",
                    [(1, "京A88888", "2026-10-01T00:00:00"),
                     (2, "13910002010", "2026-10-02T00:00:00")])
    con.execute("INSERT INTO daily_memory_meta VALUES(1,'[]')")
    con.commit()
    con.close()


def run(*args):
    return subprocess.run([sys.executable, "-X", "utf8", TOOL] + list(args),
                          capture_output=True, text=True, cwd=ROOT)


class RollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rb_")
        self.db = os.path.join(self.tmp, "src.db")
        make_db(self.db)

    def test_backup_dryrun_and_apply(self):
        out = os.path.join(self.tmp, "b.db")
        r = run("backup", "--db", self.db, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(out))
        r = run("backup", "--db", self.db, "--out", out, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(os.path.exists(out))
        self.assertTrue(os.path.exists(out + ".sha256"))
        self.assertEqual(data["backup_sha256"], sha(out))
        # sqlite backup 会重写页布局，字节 sha 可不同；内容 sha 必须等价
        self.assertEqual(R.content_digest(self.db)["sha256"],
                         R.content_digest(out)["sha256"])
        self.assertEqual(R.content_digest(self.db)["rows"],
                         R.content_digest(out)["rows"])

    def test_restore_ok(self):
        bak = os.path.join(self.tmp, "b.db")
        run("backup", "--db", self.db, "--out", bak, "--apply")
        target = os.path.join(self.tmp, "restored.db")
        r = run("restore", "--backup", bak, "--target", target, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sha(bak), sha(target))
        r = run("drill", "--db", target)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["ok"])

    def test_restore_bad_sha(self):
        bak = os.path.join(self.tmp, "b.db")
        run("backup", "--db", self.db, "--out", bak, "--apply")
        with open(bak + ".sha256", "w") as f:
            f.write("%s  b.db\n" % ("0" * 64))
        target = os.path.join(self.tmp, "bad_target.db")
        r = run("restore", "--backup", bak, "--target", target, "--apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sha 不匹配", r.stdout)
        self.assertFalse(os.path.exists(target))

    def test_restore_refuses_nonempty(self):
        bak = os.path.join(self.tmp, "b.db")
        run("backup", "--db", self.db, "--out", bak, "--apply")
        target = os.path.join(self.tmp, "t.db")
        make_db(target)
        r = run("restore", "--backup", bak, "--target", target, "--apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("需 --force", r.stdout)
        r = run("restore", "--backup", bak, "--target", target, "--force", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sha(bak), sha(target))

    def test_drill_equivalence(self):
        r = run("drill", "--db", self.db)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["checks"]["content_sha_equal"])
        self.assertEqual(data["source"]["rows"], 3)
        self.assertEqual(data["source"]["tables"], {"daily_memory_meta": 1,
                                                   "memory_source": 2})

    def test_local_only(self):
        r = run("backup", "--db", "https://evil/x.db", "--apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("local-only", r.stdout)

    def test_does_not_touch_daily(self):
        before = sha(DAILY) if os.path.exists(DAILY) else None
        run("backup", "--db", self.db, "--out", os.path.join(self.tmp, "x.db"), "--apply")
        run("drill", "--db", self.db)
        after = sha(DAILY) if os.path.exists(DAILY) else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
