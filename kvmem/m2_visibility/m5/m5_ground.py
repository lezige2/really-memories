# -*- coding: utf-8 -*-
"""M5 grounding + abstention verifier -- implements mine/inspector/M5-CRITERIA.md (frozen).

Text layer only: reads memory.db (the authoritative text copy); never a prompt, never a .kvmem.
Family order A -> D -> P -> N; matched spans are masked so nothing is counted twice.
One-directional: source-has/answer-hasn't never accuses.
"""
import json, os, re, sqlite3, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DEFAULT = os.path.join(HERE, "memory.db")
CRITERIA = "mine/inspector/M5-CRITERIA.md (frozen 2026-10-25)"
TOPIC_DEFAULT = "这一点"

FW = {0xFF01 + i: 0x21 + i for i in range(94)}
FW[0x3000] = 0x20
INVIS = re.compile(r"[\s\u00a0\u200b\u200c\u200d\ufeff]+")
SENT_END = "。！？\n"

BLACKLIST = ("车牌号", "车牌照", "手机号", "身份证", "电话号码", "车牌", "电话", "号码",
             "地址", "生日", "年龄", "姓名", "名字", "账号", "密码", "邮编",
             "单位", "公司", "学校", "职业", "血型",
             # §9 R4 (added after data): field words, so 项目代号鲸鱼 cannot become 目代号
             "项目代号", "代号", "编号", "车型", "品牌", "序列号")
INTERROG = ("什么", "多少", "哪里", "哪儿", "哪个", "谁", "怎么", "几点", "几个",
            "多久", "为什么", "怎样", "是不是")
FUNC = set("是的地了在只喝不很会要能就都也和与吗呢吧啊")
P_SUFFIX = tuple(sorted(("小区", "花园", "大厦", "广场", "单元", "路", "街", "道", "巷", "弄",
                         "苑", "城", "村", "镇", "区", "市", "省", "县", "号", "楼", "栋", "室"),
                        key=len, reverse=True))
TRAD = set("廣東話裡個們來時說對開關門問題點麼樣實學國會動無為應該")

D_CN = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9}
D_UNIT = {"十": 10, "百": 100}

RE_PLATE = re.compile(r"[\u4e00-\u9fff][A-Za-z][\-\u00b7 ]?[A-Za-z0-9]{4,6}")
RE_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_\u00b7]{2,}")
RE_LATIN = re.compile(r"[A-Za-z]{3,}")
RE_D_YMD = re.compile(r"(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*[日号]?")
RE_D_MD = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]")
RE_D_SLASH = re.compile(r"(?<!\d)(\d{1,2})[/\-.](\d{1,2})(?!\d)")
RE_D_CN = re.compile(r"([一二三四五六七八九十百]{1,3})月([一二三四五六七八九十百]{1,3})[日号]?")
RE_PB = re.compile(r"[「『《“]([^」』》”]{1,20})[」』》”]")
RE_PC = re.compile(r"(?:代号(?:叫|为|是)?|名字是|名叫|称为|叫作)([\u4e00-\u9fffA-Za-z0-9]{2,6})")
RE_PC_SHI = re.compile(r"(?:是|叫)([\u4e00-\u9fff]{2,6})")
RE_NUM = re.compile(r"\d+(?:\.\d+)?")
RE_NUM_CN = re.compile(r"([一二三四五六七八九十百]{1,4})(?=[月日号年])")


def is_cjk(ch):
    return "\u4e00" <= ch <= "\u9fff"


def prep(s):
    return INVIS.sub("", (s or "").translate(FW))


def cn2int(s):
    total, cur = 0, 0
    for ch in s:
        if ch in D_CN:
            cur = D_CN[ch]
        elif ch in D_UNIT:
            total += (cur or 1) * D_UNIT[ch]
            cur = 0
        else:
            return None
    return total + cur


def alnum_key(s):
    return re.sub(r"[\-\u00b7\u2022\s]", "", s).upper()


def blacklisted(cand):
    for b in BLACKLIST:
        if b in cand and len(cand.replace(b, "")) <= 1:
            return True
    return False


QUANT = set("个些位多几各每")
LEAD_FUNC = "是只喝不很的叫"          # §9 R5: the noun core sits after these


def strip_lead_funcs(c):
    i = 0
    while i < len(c) and c[i] in LEAD_FUNC:
        i += 1
    return c[i:]
CN_NUM = set("零〇一二三四五六七八九十百千")


def unusable_cand(cand):
    if blacklisted(cand):
        return True
    if any(q in cand for q in INTERROG) or "几" in cand:
        return True
    if any(ch.isdigit() for ch in cand):      # 2单元 is an N-family number + unit, not a name
        return True
    if cand and cand[0] in QUANT:             # 个小区 etc.
        return True
    if all(ch in CN_NUM for ch in cand):      # 十单元 -> the numeral is the fact, not the name
        return True
    if len(cand) >= 3 and sum(ch in FUNC for ch in cand) >= 2:
        return True
    return False


def extract(text, source_latin=None):
    s = prep(text)
    mask = [False] * len(s)
    out = []

    def claim(lo, hi, family, key, raw):
        if lo < 0 or hi > len(s) or any(mask[lo:hi]):
            return None
        for i in range(lo, hi):
            mask[i] = True
        f = {"family": family, "raw": raw, "key": key}
        out.append(f)
        return f

    # A -- plates, alnum codes, pure Latin only when it equals a source string
    for m in RE_PLATE.finditer(s):
        claim(m.start(), m.end(), "A", alnum_key(m.group(0)), m.group(0))
    for m in RE_CODE.finditer(s):
        raw = m.group(0)
        if re.search(r"[A-Za-z]", raw) and re.search(r"\d", raw) and len(raw) >= 3:
            claim(m.start(), m.end(), "A", alnum_key(raw), raw)
    if source_latin:
        for m in RE_LATIN.finditer(s):
            if m.group(0).upper() in source_latin:
                claim(m.start(), m.end(), "A", m.group(0).upper(), m.group(0))

    # D -- dates folded to tuples
    for m in RE_D_YMD.finditer(s):
        claim(m.start(), m.end(), "D",
              ("YMD", int(m.group(1)), int(m.group(2)), int(m.group(3))), m.group(0))
    for m in RE_D_MD.finditer(s):
        claim(m.start(), m.end(), "D", ("MD", int(m.group(1)), int(m.group(2))), m.group(0))
    for m in RE_D_CN.finditer(s):
        mo, dd = cn2int(m.group(1)), cn2int(m.group(2))
        if mo and dd:
            claim(m.start(), m.end(), "D", ("MD", mo, dd), m.group(0))
    for m in RE_D_SLASH.finditer(s):
        claim(m.start(), m.end(), "D", ("MD", int(m.group(1)), int(m.group(2))), m.group(0))

    # P -- quotes, fixed patterns, then suffix-anchored minimal core
    for m in RE_PB.finditer(s):
        cand = m.group(1)
        if len(cand) >= 2 and not unusable_cand(cand):
            claim(m.start(1), m.end(1), "P", cand, cand)
    for m in RE_PC.finditer(s):
        raw = m.group(1)
        cand = strip_lead_funcs(raw)
        if len(cand) >= 2 and not unusable_cand(cand):
            f = claim(m.end(1) - len(cand), m.end(1), "P", cand, cand)
            if f:
                f["origin"] = "P-c"
    for m in RE_PC_SHI.finditer(s):
        raw = m.group(1)
        cand = strip_lead_funcs(raw)
        if len(cand) >= 2 and not unusable_cand(cand):
            f = claim(m.end(1) - len(cand), m.end(1), "P", cand, cand)
            if f:
                f["origin"] = "P-c"
    for suf in P_SUFFIX:
        start = 0
        while True:
            i = s.find(suf, start)
            if i < 0:
                break
            start = i + 1
            j = i
            while j > 0 and is_cjk(s[j - 1]) and (i - j) < 6:
                j -= 1
            run = s[j:i]
            if not run:
                continue
            need = max(1, 3 - len(suf))
            core = run[-need:]
            if core and (core[0] in FUNC or core[0] in QUANT):   # 的小区 / 个小区 not names
                continue
            if core and all(ch in CN_NUM for ch in core):        # 十单元 -> numeral, not a name
                continue
            cand = core + suf
            if len(cand) < 3 or unusable_cand(cand):
                continue
            claim(i - len(core), i + len(suf), "P", cand, cand)

    # N -- numbers (Arabic always; CJK numerals only in date/time context)
    for m in RE_NUM.finditer(s):
        raw = m.group(0)
        key = str(int(float(raw))) if "." in raw else str(int(raw))
        claim(m.start(), m.end(), "N", key, raw)
    for m in RE_NUM_CN.finditer(s):
        v = cn2int(m.group(1))
        if v is not None:
            claim(m.start(), m.end(), "N", str(v), m.group(1))
    return out


def source_profile(texts):
    joined = "".join(texts)
    blob = prep(joined)
    latin = set()
    for t in texts:
        p = prep(t)
        for m in RE_CODE.finditer(p):
            if re.search(r"[A-Za-z]", m.group(0)) and re.search(r"\d", m.group(0)) \
                    and len(m.group(0)) >= 3:
                latin.add(alnum_key(m.group(0)))
        for m in RE_LATIN.finditer(p):
            latin.add(m.group(0).upper())
    # R12: the source side must yield the SAME plate key shape as the answer side.
    # RE_PLATE keeps the province character (浙B3F19K) while RE_CODE alone drops it
    # (B3F19K), so a correct plate answer could never match its own source. Separate
    # bucket on purpose: a plate key must never widen the P or N families.
    plate = set()
    for t in texts:
        for m in RE_PLATE.finditer(prep(t)):
            plate.add(alnum_key(m.group(0)))
    nums, dates, props = Counter(), set(), set()
    for t in texts:
        for f in extract(t, source_latin=latin):
            if f["family"] == "N":
                nums[f["key"]] += 1
            elif f["family"] == "D":
                dates.add(f["key"])
            elif f["family"] == "P":
                props.add(f["key"])
        for m in RE_NUM.finditer(prep(t)):
            k = str(int(float(m.group(0)))) if "." in m.group(0) else str(int(m.group(0)))
            nums[k] = max(nums[k], 1)
    return {"blob": blob, "latin": latin, "plate": plate, "nums": nums,
            "dates": dates, "props": props}


def date_hit(key, prof):
    if key in prof["dates"]:
        return True
    if key[0] == "YMD":
        return ("MD", key[2], key[3]) in prof["dates"]
    return False


def p_hit(key, prof):
    """§9 R2: 'a string in the source' means ANY contiguous substring, not the extracted
    candidate set. Search every contiguous substring of key with length >= len(key)-2."""
    if key in prof["blob"]:
        return True
    n = len(key)
    for L in range(n, max(n - 2, 1) - 1, -1):
        for i in range(0, n - L + 1):
            if key[i:i + L] in prof["blob"]:
                return True
    return any((key in s or s in key) and abs(len(key) - len(s)) <= 2 for s in prof["props"])


def a_hit(key, prof):
    plate = prof.get("plate") or ()
    if key in plate or any(key in s for s in plate):
        return True
    return key in prof["latin"] or any(key in s for s in prof["latin"])


def verify_sources(con, mounted):
    problems, texts = [], []
    for bid in mounted:
        r = con.execute("SELECT source_text, sha256, sha_match, source_path FROM blocks "
                        "WHERE block_id=?", (bid,)).fetchone()
        if not r:
            problems.append("block %s not in memory.db (fail closed)" % bid)
            continue
        text, sha_rec, match, path = r
        texts.append(text)
        if not match:
            problems.append("block %s recorded sha != disk at build time" % bid)
            continue
        if not os.path.exists(path):
            problems.append("block %s file missing" % bid)
            continue
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        if h.hexdigest() != sha_rec:
            problems.append("block %s file sha changed since memory.db was built" % bid)
    return texts, problems


def split_sentences(text):
    segs, cur = [], ""
    for ch in text:
        cur += ch
        if ch in SENT_END:
            segs.append(cur)
            cur = ""
    if cur:
        segs.append(cur)
    return segs


def topic_word(question):
    q = prep(question or "")
    best = None
    for b in BLACKLIST:
        if b in q and (best is None or len(b) > len(best)):
            best = b
    return best or TOPIC_DEFAULT


def ground(answer, mounted, question=None, db=DB_DEFAULT, _nested=False):
    con = sqlite3.connect(db)
    try:
        texts, problems = verify_sources(con, mounted)
    finally:
        con.close()
    rep = {"criteria": CRITERIA, "mounted": list(mounted), "question": question,
           "source_problems": problems}
    if problems:
        rep.update({"verdict": "undecidable", "reason": "源校验失败：" + "；".join(problems),
                    "facts": [], "hits": [], "unhit": [], "exempt": [],
                    "rewritten": answer, "rewritten_is_original": True})
        return rep

    prof = source_profile(texts)
    segs = split_sentences(answer)
    facts, hits, unhit, exempt = [], [], [], []
    for idx, seg in enumerate(segs):
        for f in extract(seg, source_latin=prof["latin"]):
            rec = dict(f, sentence=idx)
            k, fam = f["key"], f["family"]
            ok = (a_hit(k, prof) if fam == "A" else date_hit(k, prof) if fam == "D"
                  else p_hit(k, prof) if fam == "P" else k in prof["nums"])
            rec["hit"] = bool(ok)
            facts.append(rec)
            if ok:
                hits.append(rec)
                continue
            pos = prep(seg).find(f["raw"])
            before = prep(seg).max(0, pos - 6) if False else prep(seg)[max(0, pos - 6):pos] if pos >= 0 else ""
            if any(x in before for x in ("不是", "而不是", "应该说", "并非")):
                rec["why"] = "否定/自我更正语境（§5.5）"
                exempt.append(rec)
                continue
            if fam == "N":
                if any(str(k) in (str(d[1]), str(d[2])) for d in prof["dates"] if d[0] in ("MD", "YMD")) \
                        and re.search(r"(单元|楼|栋|室|号|个|次|分)", prep(seg)):
                    rec["why"] = "同一数字在源文日期里也出现（§5.4）"
                    exempt.append(rec)
                    continue
            if fam == "P" and f.get("origin") == "P-c" and all(
                    ch in prof["blob"] for ch in str(f["raw"])):
                rec["why"] = ("P-c 抽到的串未原样出现，但每个字都在源文里；"
                              "它更像普通短语而非专名，按 §5.7 记黄（§5 漏判优先于误判）")
                exempt.append(rec)
                continue
            unhit.append(rec)

    undec = [dict(f, why="含繁体字，不做繁简转换（§2.1.6）")
             for f in facts if any(ch in TRAD for ch in str(f["raw"]))]
    undec += [dict(e, why=e["why"]) for e in exempt if e.get("why", "").startswith("P-c")]
    # §9 R3: subset, not multiset -- repetition of the same number is not a missing fact
    ans_n = Counter(f["key"] for f in facts if f["family"] == "N")
    note = ("重复出现的数字：%s；按 §9 R3 子集判断，不计次数"
            % {k: c for k, c in ans_n.items() if c > 1}) if any(
                c > 1 for c in ans_n.values()) else None

    if unhit:
        verdict, reason = "unsupported", "至少一个硬事实未命中，且不属豁免/黑名单"
    elif undec:
        verdict, reason = "undecidable", "；".join(sorted({u["why"] for u in undec}))
    else:
        verdict = "supported"
        reason = "抽不到硬事实" if not facts else "全部硬事实命中"

    rewritten = answer
    if verdict == "unsupported":
        template = "记忆里没有记录%s。" % topic_word(question)
        involved = {u["sentence"] for u in unhit}
        parts = []
        for i, seg in enumerate(segs):
            if i in involved:
                delim = seg[-1] if seg and seg[-1] in SENT_END else ""
                parts.append(template + (delim if delim == "\n" else ""))
            else:
                parts.append(seg)
        rewritten = "".join(parts)

    rep.update({"verdict": verdict, "reason": reason,
                "facts": [{"family": f["family"], "raw": f["raw"], "key": str(f["key"]),
                           "sentence": f["sentence"], "hit": f["hit"],
                           "origin": f.get("origin")} for f in facts],
                "hits": [{"family": h["family"], "raw": h["raw"]} for h in hits],
                "unhit": [{"family": u["family"], "raw": u["raw"], "sentence": u["sentence"]}
                          for u in unhit],
                "exempt": [{"family": e["family"], "raw": e["raw"], "why": e["why"]} for e in exempt],
                "undecidable_items": undec, "multiset_note": note,
                "rewritten": rewritten,
                "rewritten_is_original": rewritten == answer})
    if verdict == "unsupported" and not _nested:
        rep["recheck"] = recheck(answer, rewritten, mounted, question, db,
                                 {(f["family"], str(f["key"])) for f in facts})
    return rep


def recheck(original, rewritten, mounted, question, db, before):
    r = ground(rewritten, mounted, question, db, _nested=True)
    fresh = {(f["family"], str(f["key"])) for f in r["facts"]}
    added = fresh - before
    segs_r = split_sentences(rewritten)
    untouched = True
    for seg in segs_r:
        if "记忆里没有记录" in seg:
            continue
        if seg not in original:
            untouched = False
    return {"1_no_unhit_fact_left": not r["unhit"],
            "2_no_new_hard_fact": not added, "2_added": sorted(added),
            "3_supported_sentences_byte_identical": untouched,
            "4_no_apology_wording": not any(w in rewritten for w in ("不知道", "抱歉", "对不起")),
            "recheck_verdict": r["verdict"]}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--answer", required=True)
    ap.add_argument("--mounted", required=True)
    ap.add_argument("--question", default=None)
    ap.add_argument("--db", default=DB_DEFAULT)
    a = ap.parse_args()
    r = ground(a.answer, [x for x in a.mounted.split(",") if x], a.question, a.db)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
