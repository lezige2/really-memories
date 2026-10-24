# -*- coding: utf-8 -*-
"""retrieval.py -- M1: choose blocks by facet + lexical signal. No model, no prompt.

This module owns the third layer from memory_source's docstring: the facet index. It is a
DERIVED cache, rebuildable from `memory_source.text` at any time, and it never hands text
to a caller that builds a prompt -- it returns block ids and scores, nothing else.

Scoring, in layers:

    bm25      CJK bigrams + latin runs (analysis.terms). The baseline.
    entity    a query that names an exact id/date the block contains gets a hard boost
    facet     query-type routing: 工号 -> blocks with id facets, 什么时候 -> date facets
    value     M1.5: a query that ASKS for a kind of value (money / time / duration / date /
              count / name / location) only admits blocks that SUPPLY that kind. This is
              what separates "topically related" from "able to answer": a block that says
              "15号发工资" has no amount, so "我每个月工资多少" must abstain, not answer
              "每月15号".
    fallback  M1.5: when no bigram matches and the query asks for a value, rank by CJK
              unigrams instead. "我几点睡觉" shares no bigram with "12点半 睡", but it does
              share 睡, and the value gate already narrowed the field.
    gate      if nothing clears the floor, return NOTHING. A companion that always
              remembers a little is a companion that makes things up.

Usage:
    python tools/retrieval.py build
    python tools/retrieval.py --explain "我的工号是多少"
"""
import argparse
import math
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import analysis as A                                     # noqa: E402

INDEX_VERSION = 5          # bump when the schema changes; ANALYSIS_VERSION covers the tables
DEFAULT_DB = os.path.join(ROOT, "kvmem", "chat.db")

ENTITY = re.compile(r"[a-zA-Z]{1,4}[-]?\d+(?:[.\-]\d+)*|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}"
                    r"|[0-9]+(?:\.[0-9]+)?\s*(?:月|日|号|层|楼|人|元|岁|分钟|小时|个|寸|号线)?")

STOP_BIGRAMS = {"什么", "是什", "多少", "怎么", "为什", "我的", "你的", "他是", "我是",
                "号是", "是多", "哪儿", "哪个", "哪些", "又是", "是谁", "我有", "他有",
                "还有", "以及", "分别"}
STOP_UNI = {"u:" + c for s in STOP_BIGRAMS for c in s} | {"u:我", "u:的", "u:是", "u:了"}

GATE = 1.30      # frozen with ANALYSIS_VERSION; do not tune against a held-out set
COV_MIN = 0.35
REL_CUT = 0.55
ABS_CUT = 1.10


def tokenize(text):
    return [t for t in A.terms(text)
            if t not in STOP_BIGRAMS and t not in STOP_UNI]


def facets_of(text):
    """Entities worth routing on. Coarse on purpose: every facet is a claim."""
    t = A.normalize(text)
    out = []
    for m in ENTITY.finditer(t):
        raw = m.group(0).strip()
        low = raw.lower()
        if re.fullmatch(r"[a-z]{1,4}-?\d+([.\-]\d+)*", low) and any(c.isdigit() for c in low):
            out.append(("id", low))
        elif re.search(r"[0-9]\s*(月|日|号)", low) or re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", low):
            out.append(("date", low))
        elif re.search(r"[0-9]", low):
            out.append(("num", low))
    seen, uniq = set(), []
    for k, v in out:
        if (k, v) not in seen:
            seen.add((k, v))
            uniq.append((k, v))
    return uniq


ROUTES = [
    (re.compile(r"工号|编号|学号|账号|身份证|门牌"), "id"),
    (re.compile(r"什么时候|哪天|几月|几号|日期|时间|上线|截止|到期|生日"), "date"),
    (re.compile(r"几[个位人岁天块元]|尺寸|多大|价格|花费|标准"), "num"),
]

DDL = """
CREATE TABLE IF NOT EXISTS facet (
    source_id INTEGER NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY (source_id, kind, value));
CREATE TABLE IF NOT EXISTS term (
    source_id INTEGER NOT NULL, term TEXT NOT NULL, tf INTEGER NOT NULL,
    PRIMARY KEY (source_id, term));
CREATE INDEX IF NOT EXISTS term_lookup ON term (term);
CREATE TABLE IF NOT EXISTS doc (
    source_id INTEGER PRIMARY KEY, name TEXT NOT NULL, label TEXT NOT NULL,
    n_terms INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attr (
    source_id INTEGER NOT NULL, attr TEXT NOT NULL,
    PRIMARY KEY (source_id, attr));
CREATE TABLE IF NOT EXISTS value_kind (
    source_id INTEGER NOT NULL, kind TEXT NOT NULL,
    PRIMARY KEY (source_id, kind));
CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def ensure(con):
    con.executescript(DDL)


def build_index(con, verbose=True):
    ensure(con)
    for t in ("facet", "term", "doc", "value_kind", "attr"):
        con.execute("DELETE FROM %s" % t)
    rows = con.execute("SELECT id, name, label, text FROM memory_source").fetchall()
    for sid, name, label, text in rows:
        tf = {}
        for t in tokenize(text):
            tf[t] = tf.get(t, 0) + 1
        con.executemany("INSERT INTO term (source_id, term, tf) VALUES (?,?,?)",
                        [(sid, t, c) for t, c in tf.items()])
        con.executemany("INSERT OR REPLACE INTO facet (source_id, kind, value) "
                        "VALUES (?,?,?)", [(sid, k, v) for k, v in facets_of(text)])
        con.executemany("INSERT OR REPLACE INTO value_kind (source_id, kind) VALUES (?,?)",
                        [(sid, k) for k in A.value_kinds(text)])
        con.executemany("INSERT OR REPLACE INTO attr (source_id, attr) VALUES (?,?)",
                        [(sid, a) for a in A.properties_of(text)])
        con.execute("INSERT INTO doc (source_id, name, label, n_terms) VALUES (?,?,?,?)",
                    (sid, name, label, len(tokenize(text))))
    con.execute("INSERT OR REPLACE INTO index_meta (key, value) VALUES ('version', ?)",
                (str(INDEX_VERSION),))
    con.execute("INSERT OR REPLACE INTO index_meta (key, value) VALUES ('analysis', ?)",
                (str(A.ANALYSIS_VERSION),))
    con.commit()
    if verbose:
        print("index v%d (analysis v%d): %d documents, %d facets, %d value kinds, %d terms"
              % (INDEX_VERSION, A.ANALYSIS_VERSION, len(rows),
                 con.execute("SELECT COUNT(*) FROM facet").fetchone()[0],
                 con.execute("SELECT COUNT(*) FROM value_kind").fetchone()[0],
                 con.execute("SELECT COUNT(*) FROM term").fetchone()[0]))
    return len(rows)


def is_stale(con):
    """True when the index was built by different code. Both halves matter: the schema and
    the value tables. A table edit with an unchanged version silently reuses a stale index."""
    try:
        rows = dict(con.execute("SELECT key, value FROM index_meta").fetchall())
    except sqlite3.OperationalError:
        return True
    return (rows.get("version") != str(INDEX_VERSION)
            or rows.get("analysis") != str(A.ANALYSIS_VERSION))


def index_version(con):
    try:
        r = con.execute("SELECT value FROM index_meta WHERE key='version'").fetchone()
    except sqlite3.OperationalError:
        return None
    return int(r[0]) if r else None


K1, B = 1.2, 0.75


def _bm25(con, qterms, n_docs, avg_len):
    if not qterms:
        return {}, {}, {}
    rows = con.execute("SELECT term, source_id, tf FROM term WHERE term IN (%s)"
                       % ",".join("?" * len(qterms)), list(qterms)).fetchall()
    df, doc_terms, idf_map, lens = {}, {}, {}, {}
    for t, sid, _tf in rows:
        df.setdefault(t, set()).add(sid)
    scores = {}
    for t, sid, tf in rows:
        if sid not in lens:
            lens[sid] = con.execute("SELECT n_terms FROM doc WHERE source_id=?",
                                    (sid,)).fetchone()[0]
        idf = math.log(1.0 + (n_docs - len(df[t]) + 0.5) / (len(df[t]) + 0.5))
        denom = tf + K1 * (1 - B + B * lens[sid] / max(1.0, avg_len))
        scores[sid] = scores.get(sid, 0.0) + idf * tf * (K1 + 1) / denom
        doc_terms.setdefault(sid, set()).add(t)
        idf_map[t] = idf
    return scores, doc_terms, idf_map


CLAUSE = re.compile(r"[，,、;；？?！!。.]+|以及|还有|和")


def split_clauses(query):
    parts = [x.strip() for x in CLAUSE.split(query or "")]
    return [x for x in parts if len(x) >= 2]


def search(con, query, k=3, mode="facet", explain=False):
    ensure(con)
    n_docs = con.execute("SELECT COUNT(*) FROM doc").fetchone()[0]
    if not n_docs:
        raise RuntimeError("index is empty -- run: python tools/retrieval.py build")
    avg_len = con.execute("SELECT AVG(n_terms) FROM doc").fetchone()[0] or 1.0

    parts = split_clauses(query) or [query]
    if len(parts) > 1:
        merged = {}
        for part in parts:
            for p in _search_one(con, part, k=k, mode=mode, n_docs=n_docs, avg_len=avg_len):
                cur = merged.get(p["name"])
                if cur is None or p["score"] > cur["score"]:
                    p = dict(p)
                    p["signals"] = dict(p["signals"])
                    p["signals"]["clause"] = part
                    merged[p["name"]] = p
        out = sorted(merged.values(), key=lambda r: (-r["score"], r["name"]))
        if not out:
            return []
        if not _passes(out[0]):
            if explain:
                return [{"source_id": None, "name": "(none)", "score": out[0]["score"],
                         "signals": {"why": "gate on every clause"}}]
            return []
        # each clause already cleared its own gate, so the union IS the answer
        return out[:k]

    return _search_one(con, query, k=k, mode=mode, n_docs=n_docs, avg_len=avg_len,
                       explain=explain)


def _search_one(con, query, k=3, mode="facet", n_docs=1, avg_len=1.0, explain=False):
    qt = tokenize(query)
    if not qt:
        return []
    qterms = sorted(set(qt))
    want_value = A.answer_type(query)

    # value gate: which blocks can even answer this kind of question?
    allowed = None
    want_prop = A.property_of(query)
    if want_prop:
        # A named property is a promise about what the answer looks like. If no block states
        # that property about the thing the question named, refuse -- even if a block names
        # the same entity (车牌号 is not 车牌颜色).
        scope = A.scope_of(query, want_prop)
        allowed = {sid for sid, txt in con.execute("SELECT id, text FROM memory_source")
                   if A.property_holds(txt, want_prop, scope)}
        if not allowed:
            return []
    elif want_value in A.GATED:
        # Only the kinds we can detect reliably are allowed to reject a block. location and
        # name stay advisory (a boost below): guessing wrong there is how "我在做蓝鲸项目"
        # became a place, and how "项目负责人是谁" lost its block.
        allowed = {r[0] for r in con.execute(
            "SELECT source_id FROM value_kind WHERE kind=?", (want_value,))}
        if not allowed:
            return []          # nothing records this kind of value -> abstain

    bigrams = [t for t in qterms if not t.startswith("u:")]
    unigrams = [t for t in qterms if t.startswith("u:")]
    base, doc_terms, idf_map = _bm25(con, bigrams, n_docs, avg_len)
    weak = (not base) or max(base.values()) < 0.5
    used_fallback = False
    if weak and allowed is not None and unigrams:
        df = {t: c for t, c in con.execute(
            "SELECT term, COUNT(*) FROM term WHERE term IN (%s) GROUP BY term"
            % ",".join("?" * len(unigrams)), unigrams)}
        rare = [t for t in unigrams if df.get(t, n_docs + 1) <= max(2, n_docs // 8)]
        if rare:
            base, doc_terms, idf_map = _bm25(con, rare, n_docs, avg_len)
            used_fallback = True

    # In fallback mode the query is represented by its rare unigrams, so coverage must be
    # measured there too. Measuring it over the bigrams (all of which are absent, by
    # definition of a fallback) would drive coverage to zero and undo the fallback.
    active = rare if used_fallback else (bigrams + unigrams)
    absent = [t for t in active if t not in idf_map]
    idf_absent = math.log(1.0 + (n_docs + 0.5) / 0.5)
    cov_den = sum(idf_map.values()) + len(absent) * idf_absent
    cov = {sid: (sum(idf_map[t] for t in ts) / cov_den) if cov_den > 0 else 0.0
           for sid, ts in doc_terms.items()}

    qlow = A.normalize(query).lower()
    want_kind = next((kind for rx, kind in ROUTES if rx.search(query)), None)
    qentities = set(re.findall(r"[a-z]{1,4}-?\d+(?:[.\-]\d+)*", qlow))
    qentities |= set(re.findall(r"\d+\s*(?:月|日|号|层|楼|人|元|寸|号线)", qlow))

    out = []
    for sid, name, label in con.execute("SELECT source_id, name, label FROM doc"):
        if allowed is not None and sid not in allowed:
            continue           # topically related, but cannot supply the asked value
        if used_fallback:
            hits = len(doc_terms.get(sid, ()))
            # Two rare characters is the normal bar. But when the value gate already left
            # only a couple of admissible blocks, that bar is redundant: one rare match
            # plus the gate is enough, and demanding two loses "我几点睡觉" -> sleep.
            need = 1 if (allowed is not None and len(allowed) <= 2) else 2
            if hits < need or cov.get(sid, 0.0) < COV_MIN:
                continue
        s = base.get(sid, 0.0)
        sig = {"bm25": round(s, 3)}
        if used_fallback:
            sig["fallback"] = "unigram"
        if want_value:
            sig["want"] = want_value
        if want_prop:
            sig["prop"] = want_prop
        if mode == "facet":
            fac = con.execute("SELECT kind, value FROM facet WHERE source_id=?",
                              (sid,)).fetchall()
            ent_hit = [v for _kk, v in fac if v in qlow or v in qentities]
            if ent_hit:
                s += 2.5 * (1.0 + math.log(1 + len(ent_hit)))
                sig["entity"] = ent_hit
            if want_kind and any(kk == want_kind for kk, _v in fac):
                s += 1.2
                sig["route"] = want_kind
            if name.lower() in qlow or label.lower() in qlow:
                s += 3.0
                sig["kind"] = name
        sig["cov"] = round(cov.get(sid, 0.0), 2)
        if s > 0:
            sig["score"] = round(s, 3)
            out.append({"source_id": sid, "name": name, "score": s, "signals": sig})

    out.sort(key=lambda r: (-r["score"], r["name"]))
    if not out or not _passes(out[0]):
        if explain:
            return [{"source_id": None, "name": "(none)",
                     "score": out[0]["score"] if out else 0.0,
                     "signals": {"why": "gate: bm25 %.2f and coverage %.2f%s"
                                 % (out[0]["score"] if out else 0.0,
                                    out[0]["signals"].get("cov", 0.0) if out else 0.0,
                                    "; value gate wants %s" % want_value
                                    if want_value else "")}}]
        return []
    top = out[0]["score"]
    keep = [r for r in out if r["score"] >= max(top * REL_CUT, ABS_CUT)]
    return keep[:k]


def _passes(best):
    """Absolute evidence, or explanatory coverage."""
    return best["score"] >= GATE or best["signals"].get("cov", 0.0) >= COV_MIN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="build", choices=["build", "show"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--explain", default=None)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--mode", default="facet", choices=["facet", "bm25"])
    a = ap.parse_args()

    con = sqlite3.connect(a.db)
    try:
        if a.explain:
            if is_stale(con):
                print("index missing or stale -- building")
                build_index(con)
            print("query: %s   (mode=%s, k=%d)" % (a.explain, a.mode, a.k))
            print("normalized: %s" % A.normalize(a.explain))
            print("tokens: %s" % " ".join(tokenize(a.explain)))
            print("answer type: %s" % A.answer_type(a.explain))
            for r in search(con, a.explain, k=a.k, mode=a.mode, explain=True):
                print("%-6.3f %-10s %s" % (r["score"], r["name"],
                                           ", ".join("%s=%s" % kv
                                                     for kv in r["signals"].items())))
            return 0
        if a.cmd == "build":
            build_index(con)
        else:
            for r in con.execute("SELECT source_id, name, n_terms FROM doc"):
                print(r)
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())