# -*- coding: utf-8 -*-
"""sandbox_guard：越界 abort、副本路径全量重写。"""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import sandbox_guard as G  # noqa: E402
import memory_source as ms  # noqa: E402


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="root_")
        self.outside = tempfile.mkdtemp(prefix="outside_")

    def test_assert_under(self):
        inside = os.path.join(self.root, "a", "b.kvmem")
        self.assertTrue(G.assert_under(inside, self.root))
        with self.assertRaises(G.SandboxViolation):
            G.assert_under(os.path.join(self.outside, "x.kvmem"), self.root)
        with self.assertRaises(G.SandboxViolation):
            G.assert_under(os.path.join(self.root, "..", "evil"), self.root)

    def test_rewrite_all_paths(self):
        db = os.path.join(self.root, "copy.db")
        con = sqlite3.connect(db)
        con.executescript(ms.SCHEMA)
        for i, p in ((1, "/orig/a.kvmem"), (2, "C:/old/b.kvmem")):
            con.execute("INSERT INTO memory_block (source_id,path,n_tokens,n_bytes,"
                        "built_at,model_path,model_size,model_mtime,kv_type,"
                        "state_version) VALUES (?,?,8,100,'t','m',1,1,'q8_0',1)",
                        (i, p))
        con.commit()
        dst = os.path.join(self.root, "blocks")
        m = G.rewrite_block_paths(con, dst)
        self.assertEqual(len(m), 2)
        for sid, p in con.execute("SELECT source_id,path FROM memory_block"):
            self.assertTrue(p.startswith(dst))
            self.assertTrue(os.path.basename(p))
        self.assertTrue(G.verify_all_under(con, dst))
        con.close()


if __name__ == "__main__":
    unittest.main()
