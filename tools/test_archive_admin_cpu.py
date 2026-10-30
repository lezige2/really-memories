# -*- coding: utf-8 -*-
"""archive_admin CLI：dry-run 不写、--apply 写、restore sha、坏 zip 拒绝、local-only。"""
import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import archive_admin as AD  # noqa: E402
import archive_store as A  # noqa: E402


def rows():
    return [{"id": i, "name": "m%d" % i,
             "text": "我的车牌号是京A%05d" % i,
             "subject": "self", "predicate": "车牌",
             "created_at": "2026-10-01T10:00:00",
             "block_sha": "b%d" % i, "block_bytes": 100 + i}
            for i in range(1, 6)]


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="archadmin_")
        self.rows_file = os.path.join(self.tmp, "rows.json")
        json.dump(rows(), open(self.rows_file, "w", encoding="utf-8"))
        self.zip = os.path.join(self.tmp, "a.zip")
        self.side = os.path.join(self.tmp, "a.sidecar.json")

    def test_dry_run_does_not_write(self):
        rc = AD.main(["archive", "--rows", self.rows_file,
                      "--zip", self.zip, "--sidecar", self.side])
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.zip))
        self.assertFalse(os.path.exists(self.side))

    def test_apply_writes(self):
        rc = AD.main(["archive", "--rows", self.rows_file,
                      "--zip", self.zip, "--sidecar", self.side, "--apply"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(self.zip))
        self.assertTrue(os.path.exists(self.side))
        rc = AD.main(["list", "--zip", self.zip, "--sidecar", self.side])
        self.assertEqual(rc, 0)

    def test_restore_sha_and_superseded(self):
        AD.main(["archive", "--rows", self.rows_file, "--zip", self.zip,
                 "--sidecar", self.side, "--apply"])
        live = os.path.join(self.tmp, "live.json")
        json.dump([{"id": 99, "name": "new", "text": "我的车牌号是京B99999",
                    "subject": "self", "predicate": "车牌",
                    "created_at": "2026-10-20T10:00:00"}], open(live, "w"))
        out = os.path.join(self.tmp, "plan.json")
        rc = AD.main(["restore", "--zip", self.zip, "--sidecar", self.side,
                      "--live", live, "--out", out, "--apply"])
        self.assertEqual(rc, 0)
        plan = json.load(open(out, encoding="utf-8"))
        self.assertTrue(all(x["action"] == "skip_superseded" for x in plan["plan"]))

    def test_bad_zip_rejected(self):
        AD.main(["archive", "--rows", self.rows_file, "--zip", self.zip,
                 "--sidecar", self.side, "--apply"])
        data = bytearray(open(self.zip, "rb").read())
        data[-8] ^= 0xFF
        open(self.zip, "wb").write(bytes(data))
        rc = AD.main(["list", "--zip", self.zip, "--sidecar", self.side])
        self.assertNotEqual(rc, 0)

    def test_local_only(self):
        with self.assertRaises(A.ArchiveError):
            A.assert_local_only(["https://example.com/a.zip"])
        rc = AD.main(["list", "--zip", "https://example.com/a.zip",
                      "--sidecar", self.side])
        self.assertNotEqual(rc, 0)

    def test_restore_dry_run_no_out(self):
        AD.main(["archive", "--rows", self.rows_file, "--zip", self.zip,
                 "--sidecar", self.side, "--apply"])
        out = os.path.join(self.tmp, "plan.json")
        AD.main(["restore", "--zip", self.zip, "--sidecar", self.side, "--out", out])
        self.assertFalse(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
