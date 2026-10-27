# -*- coding: utf-8 -*-
"""test_web_clean_cpu.py -- P0 联网查询清洗回归（零网络：monkeypatch search）。

覆盖：
  - clean_query: "帮我查一下明天的新闻" -> "明天的新闻"（去掉礼貌前缀/检索动词/尾巴）
  - query_keywords: 保留主题词（明天/新闻/天气）
  - lookup_text(keywords=...): 只保留与 query 相关的结果；全不相关 => ""（不跑偏）
  - 结果格式化仍含 标题/摘要/链接

Run: python -X utf8 tools/test_web_clean_cpu.py ; exit 0 = pass.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import web_lookup as W  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


CLEAN_CASES = [
    ("帮我查一下明天的新闻", "明天的新闻"),
    ("请帮我搜一下今天的天气", "今天的天气"),
    ("查查北京天气", "北京天气"),
    ("我想查一下汇率", "汇率"),
    ("搜一下 最新消息", "最新消息"),
    ("明天的新闻", "明天的新闻"),
]

ROWS_RELEVANT = [
    {"title": "明天新闻早知道", "url": "https://example.com/news1",
     "snippet": "明天国内外要闻汇总，天气转凉。"},
    {"title": "今日要闻", "url": "https://example.com/news2",
     "snippet": "新闻联播摘要，关注明天天气。"},
]
ROWS_IRRELEVANT = [
    {"title": "百度百科", "url": "https://baike.baidu.com/item/...",
     "snippet": "百度（Nasdaq：BIDU）是全球最大的中文搜索引擎。"},
    {"title": "汽车之家", "url": "https://example.com/car",
     "snippet": "汽车报价与购车指南。"},
]


def t_clean():
    for raw, want in CLEAN_CASES:
        got = W.clean_query(raw)
        check("clean_%s" % want, got == want, "%r -> %r" % (raw, got))
    kws = W.query_keywords("明天的新闻")
    check("keywords_topic", "明天" in kws and "新闻" in kws, kws)
    check("keywords_weather", "天气" in W.query_keywords("今天的天气"), W.query_keywords("今天的天气"))


def _fake_search(rows):
    def _s(q, max_results=4):
        return [dict(r) for r in rows]
    return _s


def t_lookup_relevance():
    orig = W.search
    try:
        W.search = _fake_search(ROWS_RELEVANT)
        txt = W.lookup_text("明天的新闻", max_results=3,
                            keywords=W.query_keywords("明天的新闻"))
        check("relevant_kept", "明天新闻早知道" in txt and "来源" not in txt, txt[:80])
        check("relevant_has_two", txt.count(")") >= 2, txt[:80])

        W.search = _fake_search(ROWS_IRRELEVANT)
        txt2 = W.lookup_text("明天的新闻", max_results=3,
                             keywords=W.query_keywords("明天的新闻"))
        check("irrelevant_filtered_empty", txt2 == "", txt2[:80])

        # 无 keywords 参数时保持原行为（兼容旧调用）
        W.search = _fake_search(ROWS_RELEVANT)
        txt3 = W.lookup_text("明天的新闻", max_results=2)
        check("no_keywords_compat", "明天新闻早知道" in txt3, txt3[:80])
    finally:
        W.search = orig


def main():
    t_clean()
    t_lookup_relevance()
    print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())