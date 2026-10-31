# -*- coding: utf-8 -*-
"""P1 模块补全单测：候选扫描 / 月份索引 / fallback / 回热 / CLI dry-run。

Run: python -X utf8 -m unittest discover -s tools -p "test_p1_archive_extra_cpu.py" -v
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import archive_store as A      # noqa: E402

ADMIN = os.path.join(_HERE, "archive_admin.py")
NOW = "2026-10-30T00:00:00"


def row(i, text, subj="阿泽", pred="车牌", created="2026-09-01T10:00:00",
        event_date=None, block_sha=None):
    return {"id": i, "name": "r%d" % i, "text": text, "subject": subj,
            "predicate": pred, "created_at": created,
            "event_date": event_date or "",
            "block_sha": block_sha or hashlib.sha256(("b%d" % i).encode()).hexdigest(),
            "block_bytes": 10 + i}


class ScanTests(unittest.TestCase):
    def test_expired_no_refs(self):
        c = A.scan_candidates([row(1, "旧事实")], NOW, days=21)
        self.assertEqual([x["id"] for x in c], [1])
        self.assertTrue(any(r.startswith("created_at_expired") for r in c[0]["reasons"]))
        self.assertIn("no_refs", c[0]["reasons"])

    def test_access_cannot_trigger_alone(self):
        # 超期但有引用 -> 不候选；未超期有引用 -> 不候选
        c = A.scan_candidates([row(1, "旧事实"), row(2, "新事实", created="2026-10-29T00:00:00")],
                              NOW, days=21, refs={1: 9, 2: 9})
        self.assertEqual(c, [])                      # refs 只加分，不触发
        # 超期 + 0 引用 -> 候选，refs 加分体现在 score
        # 超期但有引用 -> 不是候选（引用阻断，不能靠 access 触发）
        c = A.scan_candidates([row(3, "旧事实2")], NOW, days=21, refs={3: 2})
        self.assertEqual(c, [])
        # 显式标记 + 引用 -> 候选；引用只体现在 access_bonus/score
        c = A.scan_candidates([row(3, "旧事实2")], NOW, days=21, refs={3: 2}, marks=[3])
        self.assertEqual(c[0]["id"], 3)
        self.assertEqual(c[0]["access_bonus"], 2.0)

    def test_superseded_and_mark(self):
        c = A.scan_candidates([row(4, "被替代", created="2026-10-29T00:00:00")],
                              NOW, days=21, superseded={4: 9})
        self.assertIn("superseded_by:9", c[0]["reasons"])
        c = A.scan_candidates([row(5, "显式标记", created="2026-10-29T00:00:00")],
                              NOW, days=21, marks=[5])
        self.assertIn("explicit_mark", c[0]["reasons"])

    def test_month_prefers_event_date(self):
        c = A.scan_candidates([row(6, "x", created="2026-01-05T00:00:00",
                                    event_date="2025-12-20")], NOW, days=21)
        self.assertEqual(c[0]["month"], "2025-12")


class IndexFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="p1_idx_")
        self.zip = os.path.join(self.tmp, "a.zip")
        self.side = os.path.join(self.tmp, "a.sidecar.json")
        rows = [row(1, "十月事实", event_date="2026-10-02"),
                row(2, "九月事实", created="2026-09-03T00:00:00")]
        self.man = A.archive_rows(rows, self.zip, self.side)
        self.idx = A.month_index_from_archives([dict(self.man, zip=self.zip)])

    def test_index_months_and_sha(self):
        self.assertIn("2026-10", self.idx["months"])
        self.assertIn("2026-09", self.idx["months"])
        v = A.verify_index(self.idx)
        self.assertTrue(v["ok"], v)

    def test_fallback_located_and_blind(self):
        r = A.fallback_months("2026-10 的事", self.idx)
        self.assertTrue(r["located"])
        self.assertEqual(r["months"][0]["month"], "2026-10")
        self.assertTrue(r["months"][0]["sha_ok"])
        r = A.fallback_months("去年那个事", self.idx)
        self.assertTrue(r["unlocated"])
        self.assertEqual(r["strategy"], "reverse_blind")
        self.assertEqual([m["month"] for m in r["months"]], ["2026-10", "2026-09"])

    def test_restore_only_sha(self):
        with open(self.zip, "ab") as f:
            f.write(b"tamper")
        self.assertFalse(A.verify_index(self.idx)["ok"])
        r = A.fallback_months("2026-10 的事", self.idx)
        self.assertFalse(r["located"])
        self.assertFalse(r["months"][0]["sha_ok"])


class ReheatTests(unittest.TestCase):
    def test_chain_superseded(self):
        tmp = tempfile.mkdtemp(prefix="p1_re_")
        z = os.path.join(tmp, "c.zip"); s = os.path.join(tmp, "c.sidecar.json")
        rows = [row(1, "旧车牌A", pred="plate"), row(2, "旧车牌B", pred="plate"),
                row(3, "旧手机", pred="phone")]
        A.archive_rows(rows, z, s)
        live = [row(9, "新车牌", pred="plate", created="2026-10-29T00:00:00")]
        p = A.reheat_plan(live, z, s)
        self.assertEqual(p["summary"], {"restore": 1, "superseded": 2})
        sup = [x for x in p["plan"] if x["action"] == "skip_superseded"]
        self.assertEqual(sorted(x["id"] for x in sup), [1, 2])
        self.assertTrue(all(x["superseded_by"] == 9 for x in sup))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="p1_cli_")
        self.rows = os.path.join(self.tmp, "rows.json")
        rows = [row(1, "旧事实"), row(2, "新事实", created="2026-10-29T00:00:00")]
        json.dump(rows, open(self.rows, "w", encoding="utf-8"), ensure_ascii=False)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-X", "utf8", ADMIN] + list(args),
                              capture_output=True, text=True, cwd=_ROOT)

    def test_scan_dryrun_and_apply(self):
        out = os.path.join(self.tmp, "scan.json")
        r = self.run_cli("scan", "--rows", self.rows, "--now", NOW,
                         "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(out))          # dry-run 不写
        r = self.run_cli("scan", "--rows", self.rows, "--now", NOW,
                         "--out", out, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.load(open(out, encoding="utf-8"))
        self.assertEqual(data["n_candidates"], 1)

    def test_archive_updates_index(self):
        idx = os.path.join(self.tmp, "index.json")
        z = os.path.join(self.tmp, "a.zip"); s = os.path.join(self.tmp, "a.json")
        r = self.run_cli("archive", "--rows", self.rows, "--zip", z,
                         "--sidecar", s, "--index", idx, "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.load(open(idx, encoding="utf-8"))
        self.assertIn("2026-09", data["months"])

    def test_local_only_rejects_url(self):
        r = self.run_cli("archive", "--rows", self.rows,
                         "--zip", "https://evil/x.zip", "--sidecar", "s.json")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("local-only", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
