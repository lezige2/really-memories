# -*- coding: utf-8 -*-
"""M1.8 一致性断言 A1–A17：A1–A11 出自 `M1.8-CONFLICTS-inspector.md` §3，
A12–A17 出自 `INSPECTOR-M18-3-RESPEC.md` §4.2（M18-3 重出版）；零 GPU、临时库。

原则（照 §3）：
- 每条尽量**双向**：既防「该答不答」，也防「不该答却答」；
- 构造全部在系统临时目录的独立 SQLite 里，**不碰产品库**、不写工作区；
- 阈值/封存文件只读不写；A11 专门盯这件事；
- 构造库统一 10~100 篇（1 篇被测 + 无关陪衬），因为 1 篇的库会把 idf/覆盖率压成退化值
  （试过：1 篇时 `我的手机号是多少` 也会 ABSTAIN，那不是判据行为，是构造失真）。

跑法：`python -X utf8 tools/test_retrieval_judges.py`；全绿 exit 0，否则 exit 2。
产物：`kvmem/m2_visibility/m1/out/M18-A-<ts>.json`（可用 `--out` 指定）。
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import retrieval as R          # noqa: E402
import analysis as A           # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_source (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, label TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat (
    id INTEGER PRIMARY KEY, role TEXT, text TEXT);
"""

# 陪衬块：与任何被测 query 的 bigram/unigram 都不重叠（刻意避开 日/天/点/睡/机/话/身/高 等字）
FILLER = "无关紧要的记录，没有别的事情。"

results = []


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def make_db(blocks):
    """blocks: [(id, text)]，建临时库并建索引。"""
    tmp = tempfile.mkdtemp(prefix="m18a_")
    path = os.path.join(tmp, "t.db")
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    for sid, text in blocks:
        con.execute("INSERT INTO memory_source (id, name, label, text) VALUES (?,?,?,?)",
                    (sid, "conv", "conv", text))
    con.commit()
    R.build_index(con, verbose=False)
    return con


def corpus(main_text, n=10):
    """1 篇被测 + (n-1) 篇无关陪衬。"""
    return [(1, main_text)] + [(i, FILLER) for i in range(2, n + 1)]


def ids(res):
    return [r["source_id"] for r in res]


def case(cid, what, fn):
    t = time.time()
    try:
        ok, detail = fn()
        err = ""
    except BaseException as e:                    # noqa: BLE001
        ok, detail, err = False, None, "%s: %s" % (type(e).__name__, e)
    results.append({"id": cid, "what": what, "pass": bool(ok), "detail": detail,
                    "error": err, "ms": round((time.time() - t) * 1000, 1)})
    print("%-4s %-6s %s" % (cid, "GREEN" if ok else "RED", what))
    if err:
        print("      error:", err)


PHONE_BLOCK = "我的手机号是 13800138000。我在供应链分析组工作。"


def a1():
    """M18-1：① 属性闸门已放行（phone）时，② 不得因二元组不重叠而拒答。"""
    con = make_db(corpus(PHONE_BLOCK))
    holds = A.property_holds(PHONE_BLOCK, "phone")
    got = ids(R.search(con, "我的电话是多少"))
    return (holds is True and got == [1]), {"property_holds_phone": holds, "search": got}


def a2():
    """回归：同一块直接问「手机号」仍要答（不许把 A1 修成只认别名词）。"""
    con = make_db(corpus(PHONE_BLOCK))
    got = ids(R.search(con, "我的手机号是多少"))
    return got == [1], {"search": got}


def a3():
    """放松后的边界：工号块不得被当成电话答出去。"""
    con = make_db([(1, PHONE_BLOCK), (2, "我的工号是 E-2048，在供应链分析组工作。")]
                  + [(i, FILLER) for i in range(3, 11)])
    got = ids(R.search(con, "我的电话是多少"))
    return got == [1], {"search": got, "must_not_contain": [2]}


def a4():
    """M18-2 过宽：合同日期（无「生日」锚）不得判成生日，也不得被答出去。"""
    t = "合同 12月15日到期。"
    holds = A.property_holds(t, "birthday")
    con = make_db(corpus(t))
    got = ids(R.search(con, "我生日是哪天"))
    return (holds is False and got == []), {"property_holds_birthday": holds, "search": got}


def a5():
    """M18-2 收紧不得过头：真写了「生日」的块仍成立。"""
    bday = "我女儿的生日是 5月20日。"
    contract = "合同 12月15日到期。"
    holds = A.property_holds(bday, "birthday")
    con = make_db([(1, bday), (2, contract)] + [(i, FILLER) for i in range(3, 11)])
    got = ids(R.search(con, "我生日是哪天"))
    return (holds is True and got == [1]), {"property_holds_birthday": holds, "search": got}


def a6():
    """M18-2 过窄：身高的「裸数字」与「带单位」两种写法都要认。"""
    bare = "身高 176。"
    unit = "身高 176cm。"
    h1 = A.property_holds(bare, "height")
    h2 = A.property_holds(unit, "height")
    con = make_db(corpus(bare))
    got = ids(R.search(con, "我身高多少"))
    return (h1 is True and h2 is True and got == [1]), {
        "holds_bare": h1, "holds_unit": h2, "search": got}


def a7():
    """M18-2 相对时间：『下周三她生日』要认成生日（锚仍是「生日」本身）。"""
    t = "对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。"
    holds = A.property_holds(t, "birthday")
    return holds is True, {"property_holds_birthday": holds}


def a8():
    """M18-3 过宽：不得凭单字『金』把「公积金」答成「奖金」。"""
    con = make_db([(1, "每月发奖金 5000 元。")] + [(i, FILLER) for i in range(2, 11)])
    got = ids(R.search(con, "我的公积金账户余额多少"))
    return got == [], {"search": got}


def a9():
    """M18-3 收紧不得过头：回退的原始动机（我几点睡觉 → 12点半 睡）仍成立。"""
    con = make_db(corpus("12点半 睡。"))
    got = ids(R.search(con, "我几点睡觉"))
    return got == [1], {"search": got}


def a10():
    """M18-4：`_passes`（cov≥COV_MIN）判「过」，紧接的 `keep` 又用绝对下限 ABS_CUT 删光。

    构造：100 篇，1 篇超长块含查询的 5 个 bigram（df=1 ⇒ idf≈4.2），其余 99 篇很短 ——
    长块的长度归一（len/avg 很大）把 bm25 压到 1.10 以下，而**覆盖率仍 ≥0.35**。
    判法（不靠「改前返回空」这种会随修复消失的读数）：
      在构造块上取到命中后，直接核该命中的 `cov >= COV_MIN` 且 `score < ABS_CUT` ——
      这两个数同时成立就意味着它只能靠 cov 过准入，而这正是旧 `keep` 会删掉的候选；
      然后断言 `search()` 确实把它返回（改后）。改前同一构造返回 [] ⇒ 本断言红。
    """
    query = "喝咖啡的习惯"
    tried = []
    for reps in (100, 200, 300, 400, 600, 800, 1200, 1600, 2400, 3600):
        main = "喝咖啡的习惯。" + ("无关紧要的记录" * reps)
        blocks = [(1, main)] + [(i, FILLER) for i in range(2, 101)]
        con = make_db(blocks)
        got = R.search(con, query)
        hit = got[0] if got else None
        cov = hit["signals"].get("cov") if hit else None
        score = hit["score"] if hit else None
        tried.append({"reps": reps, "main_chars": len(main), "cov": cov,
                      "score": None if score is None else round(score, 3),
                      "search": ids(got)})
        zone = (hit is not None and cov is not None and cov >= R.COV_MIN
                and score is not None and score < R.ABS_CUT)
        if not zone:
            continue
        detail = {"query": query, "n_docs": 100, "construction": tried[-1],
                  "zone_evidence": "cov>=COV_MIN 且 score<ABS_CUT ⇒ 只能由覆盖率路径过准入，"
                                   "旧 keep 会删掉它；现 search 返回了它",
                  "search": ids(got), "expect": [1]}
        return ids(got)[:1] == [1], detail
    return False, {"query": query, "all_tried": tried,
                   "note": "构造未落进『cov 过 / 分低』区，A10 未真正受检（不是判据通过）"}


def a11():
    """四个冻结阈值 + 两个封存文件锚一律未改。"""
    import eval_heldout as EH
    import freeze_check as FC
    want = {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55, "ABS_CUT": 1.10}
    got = {"GATE": R.GATE, "COV_MIN": R.COV_MIN, "REL_CUT": R.REL_CUT, "ABS_CUT": R.ABS_CUT}
    frozen_ok = (EH.FROZEN == {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55}
                 and FC.FROZEN_THRESHOLDS == {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55})
    anchors = {"eval_heldout.py": "597fd0ca671e898e", "freeze_check.py": "6016085a05890581"}
    anchor_got = {k: sha16(os.path.join(HERE, k)) for k in anchors}
    ok = (got == want and frozen_ok and anchor_got == anchors)
    return ok, {"thresholds_now": got, "thresholds_expected": want,
                "eval_heldout_and_freeze_check_unchanged": frozen_ok,
                "anchor_files": anchor_got}


def a12():
    """M18-3v2 正例：值闸路径（`property_of=None`）的单字回退必须拒 —— 公积金不得答成奖金。

    与 A8 同构，单独列出是因为它是 B 的「收紧面」：非属性查询不许拿例外。
    """
    con = make_db([(1, "每月发奖金 5000 元。")] + [(i, FILLER) for i in range(2, 11)])
    got = ids(R.search(con, "我的公积金账户余额多少"))
    return got == [], {"search": got, "expect": [], "route": "value_gate(money), no property"}


def a13():
    """M18-3v2 反例：单字命中 + 属性闸门已定案 ⇒ 必须放（P2 的合成版，必须走回退）。"""
    text = "我住在广陵路 12 号 2 单元 602。"
    con = make_db(corpus(text))
    res = R.search(con, "我的住址是什么")
    got = ids(res)
    sig = res[0]["signals"] if res else {}
    return (got == [1] and sig.get("fallback") == "unigram"), {
        "search": got, "signals": sig, "expect": [1],
        "went_through_fallback": sig.get("fallback") == "unigram"}


def a14():
    """M18-3v2 命门：块/问句**同义异锚**（块用「家」、问句用「住址」），命中字只剩功能字『在』。

    按 M18-1 的裁决该放；字面词表版（Bp）在这条上会假红 `[]` —— 这就是它被否决的那条反例。
    """
    text = "家在广陵路 12 号。"
    con = make_db(corpus(text))
    res = R.search(con, "我的住址在哪里啊")
    got = ids(res)
    holds = A.property_holds(text, "address")
    sig = res[0]["signals"] if res else {}
    return (holds is True and got == [1]), {
        "property_holds_address": holds, "search": got, "signals": sig,
        "expect": [1], "anchors": "block=家 / query=住址（同义异锚）"}


def a15():
    """M18-3v2 不得张冠李戴：(a) 只有奖金块时问住址 ⇒ []；(b) 有住址块时问公积金 ⇒ []。"""
    q_addr = "我的住址是什么"
    q_fund = "我的公积金账户余额多少"
    ca = make_db([(1, "每月发奖金 5000 元。")] + [(i, FILLER) for i in range(2, 11)])
    ga = ids(R.search(ca, q_addr))
    cb = make_db([(1, "每月发奖金 5000 元。"), (2, "我住在广陵路 12 号 2 单元 602。")]
                 + [(i, FILLER) for i in range(3, 11)])
    gb = ids(R.search(cb, q_fund))
    return (ga == [] and gb == []), {"a": {"q": q_addr, "search": ga, "expect": []},
                                    "b": {"q": q_fund, "search": gb, "expect": []},
                                    "note": "两个方向都不得把错块端上来"}


def a16():
    """M18-3v2 回归：A9 不许破 —— 非属性查询仍靠 `need=2` + 现 cov 口径放行。"""
    con = make_db(corpus("12点半 睡。"))
    res = R.search(con, "我几点睡觉")
    got = ids(res)
    sig = res[0]["signals"] if res else {}
    return (got == [1]), {"search": got, "signals": sig, "expect": [1]}


def a17():
    """M18-3v2 回归：A1 不许破 —— 非回退路径的属性放行不得被杀。"""
    con = make_db(corpus(PHONE_BLOCK))
    res = R.search(con, "我的电话是多少")
    got = ids(res)
    sig = res[0]["signals"] if res else {}
    return (got == [1]), {"search": got, "signals": sig, "expect": [1],
                          "fallback": sig.get("fallback")}


CASES = [
    ("A1", "① 放行后 ② 不得杀（phone：我的电话是多少）", a1),
    ("A2", "回归：我的手机号是多少 仍绿", a2),
    ("A3", "放松后不得放错块（工号块不得被当成电话）", a3),
    ("A4", "M18-2 过宽：合同日期不得判成生日", a4),
    ("A5", "M18-2 收紧不得过头：真生日仍成立", a5),
    ("A6", "M18-2 过窄：身高裸数字 + 单位两种写法", a6),
    ("A7", "M18-2 相对时间（下周三生日）", a7),
    ("A8", "M18-3 过宽：公积金不得答成奖金", a8),
    ("A9", "M18-3 收紧不得过头：我几点睡觉 仍成立", a9),
    ("A10", "M18-4 两闸矛盾：cov 过而分低不得被 ABS_CUT 删光", a10),
    ("A11", "四个冻结阈值 + 封存文件锚未改", a11),
    ("A12", "M18-3v2 正例：值闸路径单字回退必须拒（公积金）", a12),
    ("A13", "M18-3v2 反例：单字命中 + 属性闸门已定案 ⇒ 放（住址，走回退）", a13),
    ("A14", "M18-3v2 命门：同义异锚（家 / 住址）且只剩功能字 ⇒ 仍须放", a14),
    ("A15", "M18-3v2 不得张冠李戴（奖金块问住址 / 公积金）", a15),
    ("A16", "M18-3v2 回归：我几点睡觉 不许破（need=2 + cov）", a16),
    ("A17", "M18-3v2 回归：我的电话是多少 不许破（非回退路径）", a17),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    for cid, what, fn in CASES:
        case(cid, what, fn)
    n_pass = sum(1 for r in results if r["pass"])
    n_fail = len(results) - n_pass
    res = {"schema": "m18_judges_test_v2",
           "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "code": {"analysis_sha16": sha16(os.path.join(HERE, "analysis.py")),
                    "retrieval_sha16": sha16(os.path.join(HERE, "retrieval.py"))},
           "thresholds": {"GATE": R.GATE, "COV_MIN": R.COV_MIN,
                          "REL_CUT": R.REL_CUT, "ABS_CUT": R.ABS_CUT},
           "cases": results, "n_pass": n_pass, "n_fail": n_fail,
           "fail_ids": [r["id"] for r in results if not r["pass"]],
           "exit": 0 if n_fail == 0 else 2}
    out = args.out or os.path.join(ROOT, "kvmem", "m2_visibility", "m1", "out",
                                   "M18-A-%s.json" % time.strftime("%H%M%S"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("n_pass=%d/%d fail=%s -> %s" % (n_pass, len(results), res["fail_ids"], out))
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())