# -*- coding: utf-8 -*-
"""facet_index.py -- the pointer index that decides which KV block to wake up.

README-HANDOFF-2.md section 6.2 showed that paging the right block restores recall from
20% to 85%; section 6.4 showed a character-bigram BM25 already picks the right block
19/20. So this file is not trying to beat BM25 on its own turf. It adds the one thing
BM25 structurally cannot do:

    BM25 scores *shared words*. A question that asks "在哪个部门" against a block that
    says "挂在供应链分析组" shares almost no bigrams with it -- that was BM25's only
    miss. What connects them is not wording but *type*: the question asks for an
    organisation, and the block contains one.

So the index stores, per segment, a handful of typed descriptors (time / place / org /
num) -- short extracted values, never the segment text -- plus a BM25 posting list.
At query time the asked-attribute noun is mapped to a type, and that type is used as a
*hard narrowing* of the candidate set before lexical ranking. No tuned weights: the
facet either narrows or it doesn't (a facet that most segments carry carries no
information, so it is ignored).

That is the section 6.3 design in its smallest honest form: content unit = segment,
index = multi-facet pointers, rank = facet agreement then lexical score, and the index
never stores content it could regenerate.

Usage:
  python tools/facet_index.py build  --tag 20k
  python tools/facet_index.py query  --tag 20k -q "林知远在哪个部门？"
  python tools/facet_index.py eval   --tag 20k [--emit-rank FILE] [--no-filter]
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
QUAL = os.path.join(HERE, "quality")

CJK = "\u4e00-\u9fa5"

# ---------------------------------------------------------------------------
# facet extraction -- rules, not a model: the red line says nothing may require
# training to run, so every extractor here is a regex over the segment text.
# ---------------------------------------------------------------------------

FACET_PATTERNS = {
    "time": [
        r"\d{4}\s*年", r"\d{1,2}\s*月", r"\d{1,2}\s*[日号]",
        r"去年|今年|明年|前年|年初|年底|月底|上个月|下个月|这个月|当月",
        r"上周|下周|这周|本周|周末",
        r"(?:周|星期)[一二三四五六日天]",
        r"上午|下午|中午|晚上|凌晨|早上|傍晚|半夜",
        r"\d{1,2}\s*点(?:\s*\d{1,2}\s*分)?",
        r"\d+\s*(?:分钟|小时|个月|周)",
    ],
    "place": [
        # a place name is a short CJK span ending in an administrative/venue suffix
        r"[%s]{2,5}(?:市|区|县|镇|村|路|街|道|巷|广场|大厦|机场|车站|校区|园区|小区)" % CJK,
        r"[%s]{1,5}(?:楼|层)" % CJK,
        r"[%s]{2,4}(?:室|厅|馆|店|酒店|饭店|餐厅|公园|医院|学校)" % CJK,
    ],
    "org": [
        r"[%s]{2,7}(?:公司|集团|事业部|研究院|研究所|实验室|大学|学院|委员会|协会|学会|工厂)" % CJK,
        r"[%s]{2,6}(?:事业部|分公司|分部|科室|车间)" % CJK,
        # "供应链分析组" / "增长组": the suffix that BM25 missed for question 5
        r"[%s]{2,5}(?:分析组|项目组|小组|团队)" % CJK,
    ],
    "num": [
        r"[A-Za-z]{1,3}\s*-\s*\d{2,6}",          # A-4417 style ids
        r"\d{2,3}\s*/\s*\d{2,3}",                # 128/82 (blood pressure) -- was missed
        r"\d{4,}",                                # 9031, 4200, years
        r"\d+(?:\.\d+)?\s*(?:元|块|万|岁|米|公斤|人|次|天)",
    ],
}

# facet values that are too generic to be pointers
FACET_STOP = {
    "这个月", "下个月", "上个月", "这个", "那个", "公司", "小组", "团队", "市区",
    "地方", "时间", "今年", "去年", "明年",
}

# What does the question want? The noun decides the type, not the wording.
QUERY_TYPES = [
    # "哪家" used to live here and stole "在哪家店买咖啡" from the place facet.
    ("org",   r"部门|单位|哪个组|哪个团队|什么组|隶属|归属"),
    ("place", r"哪里|哪儿|在哪|哪家|什么地方|哪个城市|哪个会议室|地点|位置|住在|去的是"),
    ("time",  r"什么时候|哪天|几点|哪年|哪个月|星期几|多久|什么时间|日期"),
    ("num",   r"多少|几岁|多大|价格|月租|房租|尾号|号码|电话|金额|工资|身高|体重|编号|工号"),
    ("name",  r"叫什么|叫啥|名字|是谁|哪位"),
]


def norm(s):
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return "".join(ch for ch in s if ch.isalnum())


def bigrams(s):
    s = norm(s)
    if len(s) < 2:
        return [s] if s else []
    return [s[i:i + 2] for i in range(len(s) - 1)]


def extract_facets(text):
    out = {}
    for ftype, pats in FACET_PATTERNS.items():
        vals = set()
        for pat in pats:
            for m in re.finditer(pat, text):
                v = norm(m.group(0))
                if len(v) >= 2 and v not in FACET_STOP:
                    vals.add(v)
        if vals:
            out[ftype] = sorted(vals)
    return out


def asked_types(question):
    return [t for t, pat in QUERY_TYPES if re.search(pat, question)]


def load_blocks(path):
    """Paragraph == segment. Must match how kvmem_page build split the document."""
    doc = open(path, encoding="utf-8").read()
    out, pos = [], 0
    while pos < len(doc):
        sep = doc.find("\n\n", pos)
        if sep == -1:
            sep = len(doc)
        p = doc[pos:sep].strip()
        if p:
            out.append(p)
        pos = sep + 2
    return out


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

class FacetIndex:
    def __init__(self, data):
        self.data = data
        self.blocks = data["blocks"]
        self.n = len(self.blocks)
        self.dl = data["dl"]
        self.avgdl = sum(self.dl) / max(1, self.n)
        self.df = data["df"]
        # term -> [[block, tf], ...] so scoring never needs the source text
        self.post = data["post"]
        self.idf = {t: math.log(1.0 + (self.n - d + 0.5) / (d + 0.5)) for t, d in self.df.items()}

    # -- build ----------------------------------------------------------

    @staticmethod
    def build(tag, kv_dir="blocks%s"):
        docs = load_blocks(os.path.join(QUAL, "doc_%s.txt" % tag))
        blocks = []
        df = Counter()
        post = {}
        dl = []
        for i, text in enumerate(docs):
            tf = Counter(bigrams(text))
            dl.append(sum(tf.values()))
            for t, c in tf.items():
                df[t] += 1
                post.setdefault(t, []).append([i, c])
            blocks.append({
                "id": i,
                # a pointer, not content: the segment's KV lives in this file
                "kv": os.path.join(kv_dir % tag, "b%03d.kvmem" % i),
                "facets": extract_facets(text),
            })
        data = {"tag": tag, "n": len(docs), "blocks": blocks, "dl": dl,
                "df": dict(df), "post": post}
        return FacetIndex(data)

    def save(self, path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(self.data, f, ensure_ascii=False, separators=(",", ":"))
        return os.path.getsize(path)

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as f:
            return FacetIndex(json.load(f))

    # -- scoring --------------------------------------------------------

    def bm25(self, question, k1=1.2, b=0.75):
        scores = [0.0] * self.n
        q = Counter(bigrams(question))
        for t, qf in q.items():
            plist = self.post.get(t)
            if not plist:
                continue
            idf = self.idf[t]
            for i, tf in plist:
                denom = tf + k1 * (1.0 - b + b * self.dl[i] / self.avgdl)
                scores[i] += idf * (tf * (k1 + 1)) / denom * qf
        return scores

    def has_type(self, bid, ftype):
        f = self.blocks[bid]["facets"]
        if ftype == "name":
            # names are not extractable without a model; treat "has a proper noun" as
            # always true and let the lexical channel decide
            return True
        return bool(f.get(ftype))

    def candidates(self, question, ratio=0.3, min_keep=3):
        """Narrow by asked type. A facet carried by most segments carries no information."""
        types = asked_types(question)
        if not types:
            return list(range(self.n)), []
        best = None
        for t in types:
            keep = [i for i in range(self.n) if self.has_type(i, t)]
            if not keep or len(keep) >= max(min_keep, ratio * self.n):
                continue        # uninformative or empty -> ignore this type
            if best is None or len(keep) < len(best[1]):
                best = (t, keep)
        if best is None:
            return list(range(self.n)), []
        return best[1], [best[0]]

    def rank(self, question, use_filter=True):
        scores = self.bm25(question)
        if use_filter:
            cand, used = self.candidates(question)
        else:
            cand, used = list(range(self.n)), []
        order = sorted(cand, key=lambda i: (-scores[i], i))
        return order, scores, used

    def facet_of(self, bid, ftype):
        return self.blocks[bid]["facets"].get(ftype, [])


def load_qa(tag):
    rows = []
    for line in open(os.path.join(QUAL, "qa_%s.tsv" % tag), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            rows.append((int(p[0]), p[1], p[2]))
    return rows


def cmd_build(a):
    idx = FacetIndex.build(a.tag)
    path = a.out or os.path.join(QUAL, "index_%s.json" % a.tag)
    size = idx.save(path)
    print("tag=%s  blocks=%d  terms=%d  index=%s (%.0f KiB)"
          % (a.tag, idx.n, len(idx.df), path, size / 1024.0))
    for b in idx.blocks[:3]:
        f = b["facets"]
        print("  block %d: %s" % (b["id"], {k: v[:4] for k, v in f.items()}))
    return 0


def cmd_query(a):
    idx = FacetIndex.load(a.out or os.path.join(QUAL, "index_%s.json" % a.tag))
    order, scores, used = idx.rank(a.q, use_filter=not a.no_filter)
    print("q: %s" % a.q)
    print("asked types: %s   narrowed by: %s" % (asked_types(a.q), used or "none"))
    for r, i in enumerate(order[:5], 1):
        f = idx.blocks[i]["facets"]
        print("  #%d block %2d  score %6.3f  %s"
              % (r, i, scores[i], {k: v[:3] for k, v in f.items()}))
    return 0


def cmd_eval(a):
    idx = FacetIndex.load(a.out or os.path.join(QUAL, "index_%s.json" % a.tag))
    qa = load_qa(a.tag)
    mode = "lexical only" if a.no_filter else "facet-narrowed + lexical"
    print("tag=%s  blocks=%d  questions=%d  mode=%s" % (a.tag, idx.n, len(qa), mode))
    print()
    print("%-4s %-34s %-6s %-6s %s" % ("id", "question", "rank", "narrow", "verdict"))
    print("-" * 76)
    hit1 = hitk = 0
    for qid, question, expect in qa:
        order, scores, used = idx.rank(question, use_filter=not a.no_filter)
        rank = order.index(qid) + 1 if qid in order else -1
        if rank == 1:
            hit1 += 1
        if 1 <= rank <= a.k:
            hitk += 1
        mark = "OK" if rank == 1 else ("top%d" % a.k if rank <= a.k else "MISS")
        print("%-4d %-34s %-6d %-6s %s"
              % (qid, question[:32], rank, ",".join(used) or "-", mark))
    print("-" * 76)
    print("retrieval@1 = %d/%d = %.0f%%" % (hit1, len(qa), 100.0 * hit1 / len(qa)))
    print("retrieval@%d = %d/%d = %.0f%%" % (a.k, hitk, len(qa), 100.0 * hitk / len(qa)))

    if a.emit_rank:
        with open(a.emit_rank, "w", encoding="utf-8", newline="\n") as f:
            f.write("# qid\tblock_id\t(facet index: %s)\n" % mode)
            for qid, question, _ in qa:
                order, _, _ = idx.rank(question, use_filter=not a.no_filter)
                f.write("%d\t%d\n" % (qid, order[0]))
        print()
        print("rank file -> %s  (feed to kvmem_page query --rank)" % a.emit_rank)
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build")
    b.add_argument("--tag", default="20k")
    b.add_argument("--out", default="")
    b.set_defaults(fn=cmd_build)

    q = sub.add_parser("query")
    q.add_argument("--tag", default="20k")
    q.add_argument("--out", default="")
    q.add_argument("-q", required=True)
    q.add_argument("--no-filter", action="store_true")
    q.set_defaults(fn=cmd_query)

    e = sub.add_parser("eval")
    e.add_argument("--tag", default="20k")
    e.add_argument("--out", default="")
    e.add_argument("--k", type=int, default=3)
    e.add_argument("--no-filter", action="store_true")
    e.add_argument("--emit-rank", default="")
    e.set_defaults(fn=cmd_eval)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())