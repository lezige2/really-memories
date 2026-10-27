# -*- coding: utf-8 -*-
"""web_lookup 的 CPU 单测：全部用 fake HTML / mock，不联网。

覆盖（≥10 项）：
  解析（标题/摘要/HTML 实体/script 剥离）、去重、max_results、空页、
  结构变化 fail-closed、URL 过滤（javascript:/data:/file:/相对）、
  1 MiB 截断读取、超时/URLError/其它异常降级、日志（sha16、不含原文）、
  摘要截断、时效查询"可能过时"标注（有/无日期两向）、空查询、无结果空串。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import web_lookup as wl  # noqa: E402


def _html(*blocks: str) -> str:
    return "<html><body><ol>" + "".join(blocks) + "</ol></body></html>"


def _block(href: str, title: str, snippet: str = "") -> str:
    p = f"<p>{snippet}</p>" if snippet else ""
    return (f'<li class="b_algo"><h2><a href="{href}">{title}</a></h2>{p}</li>')


class BaseCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wl_test_")
        self.tmp = Path(self._tmp.name)
        self._p = mock.patch.object(wl, "LOG_DIR", self.tmp)
        self._p.start()
        self._q = mock.patch.object(wl, "LOG_FILE", self.tmp / "web_queries.jsonl")
        self._q.start()

    def tearDown(self) -> None:
        self._q.stop()
        self._p.stop()
        self._tmp.cleanup()


class TestParse(BaseCase):
    def test_parse_two_results(self):
        page = _html(
            _block("https://a.example/1", "标题一", "摘要一"),
            _block("https://b.example/2", "标题二", "摘要二"),
        )
        rows = wl.parse_results(page)
        self.assertEqual([r["title"] for r in rows], ["标题一", "标题二"])
        self.assertEqual(rows[0]["url"], "https://a.example/1")
        self.assertEqual(rows[1]["snippet"], "摘要二")

    def test_html_unescape_and_script_stripped(self):
        page = _html(_block("https://a.example/1", "A&amp;B <b>粗</b>",
                            "x<script>alert(1)</script>y&nbsp;z"))
        rows = wl.parse_results(page)
        self.assertEqual(rows[0]["title"], "A&B 粗")
        self.assertNotIn("alert", rows[0]["snippet"])
        self.assertIn("y z", rows[0]["snippet"])

    def test_dedupe_same_url(self):
        page = _html(
            _block("https://a.example/x?q=1", "一", "s1"),
            _block("https://a.example/x?q=1#frag", "一(重复)", "s2"),
            _block("https://a.example/y", "二", "s3"),
        )
        rows = wl.parse_results(page)
        self.assertEqual(len(rows), 2)

    def test_max_results(self):
        page = _html(*[_block(f"https://a.example/{i}", f"t{i}", f"s{i}") for i in range(6)])
        self.assertEqual(len(wl.parse_results(page, max_results=3)), 3)

    def test_empty_page(self):
        self.assertEqual(wl.parse_results(""), [])
        self.assertEqual(wl.parse_results("<html><body>no results</body></html>"), [])

    def test_structural_change_fails_closed(self):
        odd = "<html><body><div><h2><a href='https://a.example/1'>x</a></h2></div></body></html>"
        self.assertEqual(wl.parse_results(odd), [])

    def test_snippet_truncated(self):
        page = _html(_block("https://a.example/1", "t", "字" * 500))
        sn = wl.parse_results(page)[0]["snippet"]
        self.assertLessEqual(len(sn), wl.SNIPPET_MAX)
        self.assertTrue(sn.endswith("…"))


class TestUrls(BaseCase):
    def test_javascript_filtered(self):
        page = _html(_block("javascript:alert(1)", "t", "s"))
        self.assertEqual(wl.parse_results(page), [])

    def test_data_file_relative_filtered(self):
        page = _html(
            _block("data:text/html,<b>x</b>", "t1", "s1"),
            _block("file:///C:/secret.txt", "t2", "s2"),
            _block("ftp://example.com/a", "t3", "s3"),
        )
        self.assertEqual(wl.parse_results(page), [])

    def test_fragment_stripped_and_scheme_kept(self):
        page = _html(_block("HTTPS://A.EXAMPLE/p#frag", "t", "s"))
        rows = wl.parse_results(page)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://A.EXAMPLE/p")


class TestSafeRead(BaseCase):
    def test_read_capped_1mib(self):
        blob = b"x" * (wl.MAX_BYTES + 5000)

        def read(n: int) -> bytes:
            return blob[:n]

        data, truncated = wl._read_capped(read, wl.MAX_BYTES)
        self.assertTrue(truncated)
        self.assertEqual(len(data), wl.MAX_BYTES)

    def test_read_capped_small(self):
        blob, pos = b"abc", [0]

        def read(n: int) -> bytes:
            chunk = blob[pos[0]: pos[0] + n]
            pos[0] += len(chunk)
            return chunk

        data, truncated = wl._read_capped(read, wl.MAX_BYTES)
        self.assertEqual(data, b"abc")
        self.assertFalse(truncated)


class TestSearchFallbacks(BaseCase):
    def test_timeout_returns_empty_and_logs(self):
        with mock.patch.object(wl, "_fetch_html", side_effect=TimeoutError("timed out")):
            self.assertEqual(wl.search("任意查询"), [])
        rec = json.loads((self.tmp / "web_queries.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(rec["reason"], "timeout")
        self.assertFalse(rec["ok"])

    def test_urlerror_returns_empty(self):
        import urllib.error
        with mock.patch.object(wl, "_fetch_html",
                               side_effect=urllib.error.URLError("connection refused")):
            self.assertEqual(wl.search("q"), [])
        rec = json.loads((self.tmp / "web_queries.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertFalse(rec["ok"])
        self.assertIn(rec["reason"], ("url_error", "timeout"))

    def test_generic_exception_returns_empty(self):
        with mock.patch.object(wl, "_fetch_html", side_effect=ValueError("bad content-type")):
            self.assertEqual(wl.search("q"), [])
        rec = json.loads((self.tmp / "web_queries.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(rec["reason"], "ValueError")

    def test_empty_query(self):
        self.assertEqual(wl.search("   "), [])
        rec = json.loads((self.tmp / "web_queries.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(rec["reason"], "empty_query")


class TestLoggingAndText(BaseCase):
    def test_log_has_sha_no_query_text(self):
        secret = "非常秘密的查询词-9527"
        page = _html(_block("https://a.example/1", "t", "s"))
        with mock.patch.object(wl, "_fetch_html", return_value=(page, False)):
            rows = wl.search(secret, max_results=4)
        self.assertEqual(len(rows), 1)
        log_path = self.tmp / "web_queries.jsonl"
        raw = log_path.read_text(encoding="utf-8")
        self.assertNotIn(secret, raw)
        rec = json.loads(raw.strip().splitlines()[-1])
        import hashlib
        self.assertEqual(rec["query_sha16"], hashlib.sha256(secret.encode()).hexdigest()[:16])
        self.assertEqual(rec["n_results"], 1)
        self.assertTrue(rec["ok"])

    def test_lookup_text_stale_marker(self):
        page = _html(_block("https://a.example/1", "A 地天气", "晴 20 度"))
        with mock.patch.object(wl, "_fetch_html", return_value=(page, False)):
            text = wl.lookup_text("今天 A 地天气")
        self.assertIn("可能过时", text)

    def test_lookup_text_no_marker_when_date_present(self):
        page = _html(_block("https://a.example/1", "A 地天气 2026-10-27", "晴 20 度"))
        with mock.patch.object(wl, "_fetch_html", return_value=(page, False)):
            text = wl.lookup_text("今天 A 地天气")
        self.assertNotIn("可能过时", text)

    def test_lookup_text_no_marker_for_static_query(self):
        page = _html(_block("https://a.example/1", "Python 列表", "list 用法"))
        with mock.patch.object(wl, "_fetch_html", return_value=(page, False)):
            text = wl.lookup_text("Python list 用法")
        self.assertNotIn("可能过时", text)

    def test_lookup_text_empty_when_no_results(self):
        with mock.patch.object(wl, "_fetch_html", return_value=("<html></html>", False)):
            self.assertEqual(wl.lookup_text("x"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)