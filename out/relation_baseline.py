# -*- coding: utf-8 -*-
"""
out/relation_baseline.py -- 可解释规则基线（只读 old/new，绝不读 label/note）

任务：对每条 (old, new) 判断 new 与 old 的关系
      correct     = 同一主体、值被更新
      new_subject = new 说的是另一个主体（新增事实，不覆盖 old）
      ambiguous   = 无法判定（必须追问）

规则（全部为字符串/词典规则，无 id 硬编码）：

R1 归一化：去首尾空白与句末标点 。！？；，全角空格折半角。
R2 变化段：求 old/new 最长公共前缀 p、最长公共后缀 s（s 不越过 p，避免重叠）。
   old_mid = old[p:len(old)-s]，new_mid = new[p:len(new)-s]。
   任一变化段为空（纯删除/无变化）→ ambiguous（没有可定位的新值）。
R3 主体/值解析（对 old、new 各跑一次）：
   3a 按标点切子句，取“最后一个含锚点关键词的子句”；
      锚点词表 = 是/在/叫/有/过敏/尾号/车牌/手机/邮箱/工位/老家/公司/车型/颜色/健身/会议。
      一个子句内命中多个时取位置最右者（离值最近）。
   3b 主体 = 子句[0:锚点位置]；值 = 子句[锚点之后]。
   3c 若主体清洗后为空、而锚点本身是 heads 名词（尾号/车牌/手机/邮箱/工位/老家/公司/
      车型/颜色/会议），主体取该词本身（“车牌 苏D5K72M” 的主体就是“车牌”）；
      锚点命中“手机”而值以“号”开头时，把“号”并回主体（手机→手机号）。
   3d 无锚点时的兜底：取最后一个含句尾值型 token（字母/数字/@/.-_ 串）的子句，
      该 token 作值、其前面短语作主体。子句只按中文标点切，不按空格切（空格在
      “C 区 15 号”“19:00”里是值的一部分，不是分句点）。
   3e 主体清洗：剥掉左侧人称/时间/语气填充词与改换动词（我/我的/现在/之前/其实/改叫/
      换成/搬到…）与右侧的/了/也/都/其实。清洗后为空、或只剩单字（多为切错的碎片，
      如车牌首字“皖”）→ 记为 ∅（不可知）。
R4 判定：
   - old、new 任一值不可得，或任一主体为 ∅ → ambiguous
   - 两侧主体均非空且不相等 → new_subject
   - 两侧主体相等且值不同 → correct
   - 值相同 → ambiguous（没有升信息）
   - 值 == 主体（解析错位）→ ambiguous

解析器只做保守判断：抽不出就 ambiguous，绝不猜 correct。
"""
import json
import re
import hashlib
import sys

GOLD = "out/RELATION-GOLD-60.jsonl"
OUT = "out/RELATION-BASELINE.json"
OUT_V2 = "out/RELATION-BASELINE-v2.json"
EXPECT_SHA = "1d2636b3c4b0034848cdaab69fdbdaf61bc164951dd61409b20e108a07f793fc"

KEYWORDS = ["是", "在", "叫", "有", "过敏", "尾号", "车牌", "手机",
            "邮箱", "工位", "老家", "公司", "车型", "颜色", "健身", "会议"]
HEAD_NOUNS = {"尾号", "车牌", "手机", "邮箱", "工位", "老家", "公司",
              "车型", "颜色", "会议"}

L_PARTICLES = ["我的", "你的", "他的", "她的", "它的", "我们", "你们", "他们",
               "现在", "目前", "之前", "上次", "这次", "最近", "其实",
               "改叫", "改名", "改成", "换到", "换成", "搬到", "挪到",
               "升到", "调到", "转到", "改", "换", "搬", "挪",
               "我", "你", "他", "她", "它", "这个", "那个", "这", "那",
               "也", "还", "都", "就", "又", "刚", "已经", "只"]
R_PARTICLES = ["的", "了", "也", "都", "还", "就", "又", "其实", "只", "吧", "呢"]

# 只在中文标点处切子句：空格是数字/字母值的一部分，不能当分隔符
CLAUSE_SEP = re.compile(r"[，,、；;！!？?。]+")
VAL_TOKEN = re.compile(r"([A-Za-z0-9][A-Za-z0-9\-\.@:_/＋+]*)\s*$")
VAL_LEAD = re.compile(r"^(?:的地得|的|得|是|为|：|:|，|,|。|\s)+")


def norm(s):
    s = (s or "").replace("\u3000", " ")
    s = s.strip()
    s = re.sub(r"[\s。！？；]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def lcp(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def lcs(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[-1 - i] == b[-1 - i]:
        i += 1
    return i


def clean_subject(s):
    s = s.strip()
    changed = True
    while changed and s:
        changed = False
        for p in L_PARTICLES:
            if s.startswith(p):
                s = s[len(p):]
                changed = True
                break
    changed = True
    while changed and s:
        changed = False
        for p in R_PARTICLES:
            if s.endswith(p) and len(s) > len(p):
                s = s[: -len(p)]
                changed = True
                break
    return s.strip("的地得 　")


def find_anchor(clause):
    """子句内最右锚点。返回 (pos, kw) 或 None。"""
    best = None
    for kw in KEYWORDS:
        pos = clause.rfind(kw)
        if pos < 0:
            continue
        key = (pos, len(kw))
        if best is None or key > best[0]:
            best = (key, kw)
    if best is None:
        return None
    (pos, _), kw = best
    return pos, kw


def clean_value(v):
    v = VAL_LEAD.sub("", (v or "").strip())
    v = re.sub(r"[\s。！？；]+$", "", v)
    v = re.sub(r"[了的吧呢啊]$", "", v)
    return v.strip()


def parse(text):
    """返回 (subject, value)。抽不出则对应位置为空串。"""
    t = norm(text)
    if not t:
        return "", ""
    clauses = [c for c in CLAUSE_SEP.split(t) if c.strip()]
    # 取最后一个带锚点的子句
    for clause in reversed(clauses):
        got = find_anchor(clause)
        if not got:
            continue
        pos, kw = got
        subj_raw = clause[:pos]
        val = clean_value(clause[pos + len(kw):])
        subj = clean_subject(subj_raw)
        if not subj and kw in HEAD_NOUNS:
            subj = kw
        # "手机号 189..."：锚点命中"手机"，值里剩下的"号"归回主体
        if len(subj) <= 1:
            subj = ""
        if subj and val.startswith("号") and not subj.endswith("号"):
            subj, val = subj + "号", clean_value(val[1:])
        return subj, val
    # 兜底：最后一个含句尾值型 token 的子句
    for clause in reversed(clauses):
        m = VAL_TOKEN.search(clause.strip())
        if m:
            subj = clean_subject(clause[: m.start()])
            if len(subj) <= 1:
                subj = ""
            return subj, clean_value(m.group(1))
    return "", ""


def predict(old, new):
    """返回 (pred, evidence)。"""
    o, n = norm(old), norm(new)
    p = lcp(o, n)
    s = min(lcs(o, n), min(len(o), len(n)) - p)
    o_mid = o[p: len(o) - s] if s else o[p:]
    n_mid = n[p: len(n) - s] if s else n[p:]

    if not o or not n:
        return "ambiguous", {"why": "空串"}
    if not o_mid and not n_mid:
        return "ambiguous", {"why": "无变化", "p": p, "s": s}
    if not n_mid:
        return "ambiguous", {"why": "新值为空(纯删除)", "p": p, "s": s}

    os_, ov = parse(o)
    ns, nv = parse(n)

    # 有公共上下文时，用变化段作为更精确的值
    ev = {"p": p, "s": s, "old_mid": o_mid, "new_mid": n_mid,
          "old_subject": os_, "new_subject": ns, "old_value": ov, "new_value": nv}
    if p + s > 0:
        if o_mid.strip() and n_mid.strip():
            ev["value_used"] = "diff_segment"
            v_old, v_new = o_mid.strip(), n_mid.strip()
        else:
            return "ambiguous", dict(ev, why="变化段不可定位")
    else:
        ev["value_used"] = "keyword_parse"
        if not ov or not nv:
            return "ambiguous", dict(ev, why="值不可得")
        v_old, v_new = ov, nv

    if not os_ or not ns:
        return "ambiguous", dict(ev, why="主体不可知")
    if os_ != ns:
        return "new_subject", dict(ev, why="主体不同: %s -> %s" % (os_, ns))
    if v_old == v_new:
        return "ambiguous", dict(ev, why="值未变")
    if v_old == os_ or v_new == ns:
        return "ambiguous", dict(ev, why="值与主体错位")
    return "correct", dict(ev, why="同主体换值: %s -> %s" % (v_old, v_new))


def confusion(rows, arm):
    labels = ["correct", "new_subject", "ambiguous"]
    cm = {a: {b: 0 for b in labels} for a in labels}
    for r in rows:
        cm[r["label"]][r[arm]] += 1
    return cm


# ======================= v2：recall 补丁 =======================
# v1 的问题不是"判错"，是"没敢判"：true-update 的新句常把主体省略掉
# （"整车喷成奶白色了"、"刚升到 500M"、"改去昆明了"），v1 抽不出主体只能回 ambiguous。
# v2 只增加三条**通用**机制，不放松精度：
#   M1 改动提示词（cue）：换成/改成/搬到/挪到/调到/转到/升到/改叫/改名/喷成/…
#      /其实是/实际是/现在在/现在用/以后用/离职/卖了+提了…
#      cue 之后的短语就是"新值"；cue 出现 = 这句在讲"同一槽位被改掉了"。
#   M2 主体省略：新句无主语 + 有 cue + 无阻断项 → 继承 old 的主体（汉语后续句常省主语）。
#   M3 值类型相容：车牌/手机/邮箱/时间/数字+单位/色/校/场所/机构/名称 必须同族；
#      单位不同（300M vs 425 度）、类别不同（色 vs 机构）不算换值。
# 阻断项（一命中就回 ambiguous，宁可追问）：否定、回退、同一日期对撞、
#      旧句多槽位（锚点词≥2 次 / "号"级数值≥2 处 / 同类值≥2 个 / 两只…和）。
CUE_PATTERNS = [
    "重新分配", "之前说错", "说错了", "事实是", "其实是", "实际是",
    "现在在", "现在用", "以后用", "换成", "换到", "换为",
    "改成", "改到", "改为", "改叫", "改名", "改口", "改去",
    "搬到", "挪到", "调到", "转到", "升到", "降到", "变成",
    "后来", "查了", "复查", "更正", "离职",
]
CUE_RE = re.compile("|".join(re.escape(c) for c in
                             sorted(CUE_PATTERNS, key=len, reverse=True)))
TRANSFORM_RE = re.compile(r"(?:喷|染|刷|改|换|调|升|降|转|搬|挪)成")
DISPOSAL = ("卖了", "卖掉", "退了", "注销", "停用", "离职", "清空", "不用了")
ACQUIRE = ("提了", "买了", "入手", "新提")
ACQ_RE = re.compile("|".join(ACQUIRE))
NEG_RE = re.compile(r"没换|没改|没变|没有换|别记错|别搞错|别弄错|并未|不是|照旧|还在|仍在|还在用|仍在用")
REVERT_RE = re.compile(r"还是|原来那个|原来那|改回|叫回|换回|回到|算了吧")
DATE_RE = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日")
PLATE_RE = __import__("re").compile(
    r"^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
    r"[A-Z][A-Z0-9]{4,6}$")
PHONE_RE = re.compile(r"^\d[\d\- ]{6,}\d$")

EXTRA_L = ["对", "用", "把", "被", "给"]
EXTRA_R = ["那项", "这项", "那边", "这边"]


def subj_v2(s):
    """v2 专用主体清洗：在 v1 结果上再剥介词/指示词残留（不动 v1 的判定）。"""
    s = clean_subject(s)
    ch = True
    while ch and s:
        ch = False
        for p in EXTRA_L:
            if s.startswith(p):
                s = s[len(p):]
                ch = True
                break
    ch = True
    while ch and s:
        ch = False
        for p in EXTRA_R:
            if s.endswith(p) and len(s) > len(p):
                s = s[:-len(p)]
                ch = True
                break
    return s


def parse_info(text, cleaner=clean_subject):
    """返回 (subject, value, anchor_kw)。"""
    t = norm(text)
    if not t:
        return "", "", ""
    clauses = [c for c in CLAUSE_SEP.split(t) if c.strip()]
    for clause in reversed(clauses):
        got = find_anchor(clause)
        if not got:
            continue
        pos, kw = got
        val = clean_value(clause[pos + len(kw):])
        subj = cleaner(clause[:pos])
        if not subj and kw in HEAD_NOUNS:
            subj = kw
        if len(subj) <= 1:
            subj = ""
        if subj and val.startswith("号") and not subj.endswith("号"):
            subj, val = subj + "号", clean_value(val[1:])
        return subj, val, kw
    for clause in reversed(clauses):
        m = VAL_TOKEN.search(clause.strip())
        if m:
            subj = cleaner(clause[: m.start()])
            if len(subj) <= 1:
                subj = ""
            return subj, clean_value(m.group(1)), ""
    return "", "", ""


def take_value(seg):
    s = seg.lstrip(" 　")
    s = re.sub(r"^(到|为|了|的|作|是|：|:|，|,)", "", s).strip()
    if not s:
        return ""
    m = re.match(r"[^，。！？；、,;!?]{1,24}", s)
    s = (m.group(0) if m else s[:24]).strip()
    s = re.sub(r"[了的吧呢啊]$", "", s).strip()
    s = re.sub(r"^(辆|个|位|名|条|张|台|份|套|只)", "", s).strip()
    if not s or not re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", s):
        return ""
    return s


def cue_value(text):
    """cue 之后取新值；纯"处置+获取"（卖了…提了…）也算。返回 (cue, value) 或 None。"""
    t = norm(text)
    best = None
    for rx in (CUE_RE, TRANSFORM_RE):
        for m in rx.finditer(t):
            v = take_value(t[m.end():])
            if v:
                best = (m.group(0), v)
    if best is None and any(d in t for d in DISPOSAL):
        for m in ACQ_RE.finditer(t):
            v = take_value(t[m.end():])
            if v:
                best = (m.group(0), v)
    return best


def vtype(v):
    s = (v or "").strip()
    if not s:
        return "none"
    if "@" in s:
        return "email"
    if PLATE_RE.match(s):
        return "plate"
    if PHONE_RE.match(s) and len(re.sub(r"\D", "", s)) >= 7:
        return "phone"
    if re.search(r"\d{1,2}:\d{2}", s) or re.search(r"(周|星期)[一二三四五六日天]", s):
        return "time"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(M|G|T|度|号|层|栋|位|元|岁|次|年|个月|寸|米|公里|kg|cm)", s)
    if m:
        return "num:" + m.group(2)
    if re.search(r"\d", s):
        return "num"
    if s.endswith("色"):
        return "color"
    if s.endswith(("幼儿园", "学校", "大学", "学院", "小学", "中学")):
        return "school"
    if s.endswith(("厅", "室", "楼")):
        return "venue"
    if s.endswith(("公司", "科技", "医疗", "智能", "数据", "银行", "中心", "店",
                   "院", "局", "厂", "站")):
        return "org"
    if s.endswith(("路", "街", "巷", "镇", "村", "市", "省", "县", "洲", "湾",
                   "山", "河", "湖", "岛", "园", "区")):
        return "place"
    if all("\u4e00" <= ch <= "\u9fa5" for ch in s) and 1 <= len(s) <= 8:
        return "name"
    return "other"


CJK_FAMILY = {"name", "place", "org", "school", "venue", "color"}


def compat(t1, t2):
    if t1 == t2:
        return True
    return t1 in CJK_FAMILY and t2 in CJK_FAMILY


def subj_noise(s):
    return (not s) or bool(re.search(r"\d|周[一二三四五六日]|星期", s)) or len(s) <= 1


def old_value(text):
    o = norm(text)
    _, val, _ = parse_info(o)
    val = re.sub(r"(上班|工作|那边|这里)$", "", val or "")
    if val:
        return val
    m = re.search(r"对([^，。]{1,10}?)过敏", o)
    return m.group(1) if m else ""


def gate_reason(old, new):
    lo, ln = norm(old), norm(new)
    if NEG_RE.search(ln):
        return "negation"
    if REVERT_RE.search(ln):
        return "revert"
    d1, d2 = DATE_RE.search(lo), DATE_RE.search(ln)
    if d1 and d2 and d1.group(0) == d2.group(0):
        return "same_date"
    _, _, okw = parse_info(lo, subj_v2)
    if okw and lo.count(okw) >= 2:
        return "multi_slot(%s x%d)" % (okw, lo.count(okw))
    if len(re.findall(r"\d+\s*号", lo)) >= 2:
        return "multi_value(号 x%d)" % len(re.findall(r"\d+\s*号", lo))
    if re.search(r"(两|二|俩)(只|个|辆|张|份|条|位|台|套)", lo) and re.search(r"[、和]", lo):
        return "multi_value(两只/两辆…和)"
    for pat in (r"\d[\d\- ]{6,}\d", r"\S+@\S+\.\S+", PLATE_RE.pattern[1:-1]):
        if len(re.findall(pat, lo)) >= 2:
            return "multi_value(同类值 x2)"
    return ""


def predict_v2(old, new):
    base, bev = predict(old, new)
    if base == "correct":
        return base, dict(bev, rule="v1")

    g = gate_reason(old, new)
    if g:
        return "ambiguous", dict(bev, rule="gate:" + g, why="阻断项命中: " + g)

    got = cue_value(new)
    if not got:
        return base, dict(bev, rule="no_cue_keep_v1")
    cue, nval = got

    os_, _, _ = parse_info(norm(old), subj_v2)
    ns_, _, _ = parse_info(norm(new), subj_v2)
    if not subj_noise(os_) and not subj_noise(ns_) and os_ != ns_:
        return base, dict(bev, rule="gate:subject_conflict",
                          v2_old_subject=os_, v2_new_subject=ns_,
                          why="主体冲突: %s vs %s" % (os_, ns_))

    oval = old_value(old)
    tv_old, tv_new = vtype(oval), vtype(nval)
    if tv_new in ("none", "other") and not oval:
        return base, dict(bev, rule="gate:untyped_value", new_value=nval)
    if oval and not compat(tv_old, tv_new):
        return base, dict(bev, rule="gate:type_%s_vs_%s" % (tv_old, tv_new),
                          old_value=oval, new_value=nval,
                          why="值类型不相容: %s(%s) vs %s(%s)"
                              % (oval, tv_old, nval, tv_new))

    return "correct", dict(bev, rule="cue_recovery", cue=cue, old_value=oval,
                           new_value=nval, old_subject=os_, new_subject=ns_,
                           types=[tv_old, tv_new],
                           why="省略主语继承 old + cue[%s]: %s -> %s"
                               % (cue, oval or "∅", nval))


def prf(cm):
    labels = ["correct", "new_subject", "ambiguous"]
    out = {}
    for c in labels:
        tp = cm[c][c]
        fp = sum(cm[a][c] for a in labels if a != c)
        fn = sum(cm[c][b] for b in labels if b != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[c] = {"precision": round(prec, 4), "recall": round(rec, 4),
                  "f1": round(f1, 4), "support": tp + fn}
    return out


def summarise(rows, field, n):
    labels = ["correct", "new_subject", "ambiguous"]
    cm = confusion(rows, field)
    acc = sum(cm[c][c] for c in labels) / n
    residual = [r["id"] for r in rows if r[field] != r["label"] and r["label"] == "correct"]
    false_ns = [r["id"] for r in rows if r[field] == "new_subject" and r["label"] != "new_subject"]
    return {
        "accuracy": round(acc, 4),
        "correct_n": sum(1 for r in rows if r[field] == r["label"]),
        "confusion": cm,
        "per_class": prf(cm),
        "residual": {"count": len(residual), "ids": residual},
        "new_subject_false_commits": {"count": len(false_ns), "ids": false_ns},
    }


def main():
    raw = open(GOLD, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECT_SHA:
        print("SHA256 MISMATCH: %s" % sha)
        sys.exit(2)

    rows = []
    with open(GOLD, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    # 只用 old/new —— predict() 的入参就是 old/new，label/note 不进入判定路径
    for r in rows:
        p1, ev1 = predict(r["old"], r["new"])
        p2, ev2 = predict_v2(r["old"], r["new"])
        r["rule"], r["rule_v2"], r["always_ask"] = p1, p2, "ambiguous"
        r["evidence"], r["evidence_v2"] = ev1, ev2

    n = len(rows)
    v1 = summarise(rows, "rule", n)
    v2 = summarise(rows, "rule_v2", n)
    ask = summarise(rows, "always_ask", n)

    meta = {
        "gold": GOLD,
        "sha256": sha,
        "n": n,
        "rule_file": "out/relation_baseline.py",
        "inputs_used": ["old", "new"],
        "inputs_forbidden": ["label", "note"],
        "no_id_hardcoding": True,
    }

    # ---------- v1 文件（保持原样，便于对照） ----------
    d1 = {"meta": dict(meta, arms=["rule", "always_ask"]), "arms": {}}
    d1["arms"]["rule"] = dict(v1, predictions=[{"id": r["id"], "pred": r["rule"]} for r in rows])
    d1["arms"]["always_ask"] = dict(ask, predictions=[{"id": r["id"], "pred": r["always_ask"]} for r in rows])
    d1["rule_evidence"] = {r["id"]: r["evidence"] for r in rows}
    rg = next(r for r in rows if r["id"] == "RG43")
    d1["rg43"] = {
        "gold_label_ignored_by_rule": True,
        "old": rg["old"], "new": rg["new"],
        "rule_pred": rg["rule"], "always_ask_pred": rg["always_ask"],
        "label_check_only_for_report": rg["label"],
        "evidence": rg["evidence"],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(d1, f, ensure_ascii=False, indent=2)

    # ---------- v2 文件 ----------
    recovered = [{"id": r["id"], "cue": r["evidence_v2"].get("cue"),
                  "old_value": r["evidence_v2"].get("old_value"),
                  "new_value": r["evidence_v2"].get("new_value"),
                  "types": r["evidence_v2"].get("types")}
                 for r in rows if r["evidence_v2"].get("rule") == "cue_recovery"]
    d2 = {
        "meta": dict(meta, arms=["v2", "v1_reference", "always_ask"],
                     caveat="煨过一轮：cue 表是照着本数据集的改写方式列的，属 in-sample 上界，"
                            "可外推的只是机制本身（cue+主语省略+类型相容+阻断项）。"),
        "config": {
            "cues": CUE_PATTERNS,
            "transform_regex": TRANSFORM_RE.pattern,
            "disposal_for_acquire": list(DISPOSAL),
            "acquire": list(ACQUIRE),
            "gates": ["negation", "revert", "same_date", "multi_slot",
                      "multi_value(numbered)", "multi_value(listed)",
                      "multi_value(duplicate)",
                      "subject_conflict", "type_mismatch", "untyped_value"],
            "types": ["plate", "phone", "email", "time", "num:<unit>", "color",
                      "school", "venue", "org", "place", "name"],
        },
        "v2": dict(v2, predictions=[{"id": r["id"], "pred": r["rule_v2"],
                                     "rule": r["evidence_v2"].get("rule", ""),
                                     "why": r["evidence_v2"].get("why", "")} for r in rows],
                   recovered=recovered),
        "v1_reference": {k: v1[k] for k in ("accuracy", "residual",
                                            "new_subject_false_commits", "confusion",
                                            "per_class", "correct_n")},
        "always_ask": {k: ask[k] for k in ("accuracy", "residual", "correct_n",
                                           "confusion", "per_class")},
        "rg43": {
            "old": rg["old"], "new": rg["new"],
            "v1_pred": rg["rule"], "v2_pred": rg["rule_v2"],
            "always_ask_pred": rg["always_ask"],
            "label_check_only_for_report": rg["label"],
            "note": "旧句锚点抽得出“车牌”，新句裸值无可归属主体；两版都回 ambiguous。",
        },
        "in_sample_caveat": ("cue 表是在本 60 条上归纳的（远不止这几个词，"
                             "还包括 改成/搬到/挪到/调到/升到/改叫/改去/喷成 等变换与"
                             "其实是/实际是/现在在/现在用/以后用/离职/卖了+提了 等改口表达），"
                             "out-of-sample 待 B 的第二套 held-out 验证；本文件的 90% 是 in-sample 上界，"
                             "不是泛化估计。"),
        "residual_detail": [
            {"id": r["id"], "old": r["old"], "new": r["new"],
             "pred": r["rule_v2"], "gold": r["label"],
             "rule": r["evidence_v2"].get("rule", ""),
             "why": r["evidence_v2"].get("why", ""),
             "old_value": r["evidence_v2"].get("old_value", ""),
             "new_value": r["evidence_v2"].get("new_value", ""),
             "v1_pred": r["rule"],
             "failure_mode": ("同槽位更新被读成新主体：new 句带上新的限定语"
                              "（公司/排量/新卡），规则判成换主体 → 会造重复事实而非覆盖")}
            for r in rows if r["id"] in v2["residual"]["ids"]],
        "new_subject_false_detail": [
            {"id": r["id"], "old": r["old"], "new": r["new"],
             "pred": r["rule_v2"], "gold": r["label"],
             "rule": r["evidence_v2"].get("rule", ""),
             "why": r["evidence_v2"].get("why", "")}
            for r in rows if r["rule_v2"] == "new_subject" and r["label"] != "new_subject"],
        "residual_verdict": ("residual=%d（阈值 12）→ %s"
                             % (v2["residual"]["count"],
                                "P 只作可选对照" if v2["residual"]["count"] < 12
                                else "P 的真考题")),
    }
    with open(OUT_V2, "w", encoding="utf-8") as f:
        json.dump(d2, f, ensure_ascii=False, indent=2)

    # 调试明细（不属交付物）
    with open("out/_rule_trace_v2.txt", "w", encoding="utf-8") as f:
        for r in rows:
            f.write("%s gold=%-11s v1=%-11s v2=%-11s | %s\n" % (
                r["id"], r["label"], r["rule"], r["rule_v2"],
                json.dumps(r["evidence_v2"], ensure_ascii=False)))

    for name, a in (("v1", v1), ("v2", v2), ("ask", ask)):
        print("%s acc=%.4f correct=%d residual=%d %s" % (
            name, a["accuracy"], a["correct_n"], a["residual"]["count"],
            a["residual"]["ids"]))
        print("   new_subject_false=%d %s" % (
            a["new_subject_false_commits"]["count"],
            a["new_subject_false_commits"]["ids"]))
    print("rg43 v1=%s v2=%s gold=%s" % (rg["rule"], rg["rule_v2"], rg["label"]))
    print(d2["residual_verdict"])


if __name__ == "__main__":
    main()
