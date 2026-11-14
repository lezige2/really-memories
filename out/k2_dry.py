#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""K2-dry：K2「同族只留最新」的离线预演（不碰产品代码、不跑服务、不写原库）。

输入：
  * kvmem/daily/chat.db 的**副本** out/K2-DRY.sqlite（只读打开）
  * out/KV-CONFLICT-40.jsonl 42 条夹具
规则（B 修订后）：
  * 基座 = 库中 id 1..20（r1 setup 前 memories=20；21/22 是上一轮残留，不参与）
  * 每条 case 把 pre_state 里两条 remember 按顺序注入为 id 21(old) / 22(new)，
    断言与 r1 setup.prelude 的 21/22 一致，共 22 块
  * 族键 = (family, owner, predicate, slot)；slot 只对 会议/出差 生效（日期/时间）
  * 族内默认保留 id 最大者；但以下块**不隐、保留可见**：
      - 带补充属性的块（#3 阿泽+车牌、#1 组会+待办 等，非本族属性）
      - 与 kept 同值的块
  * 省略式新事实（"我换到美团了"/"改到2楼会议室"）继承同 case 上一条的族键与 slot
输出：
  * out/K2-DRY-REPORT.json
"""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_DB = os.path.join(ROOT, "kvmem", "daily", "chat.db")
DRY_DB = os.path.join(HERE, "K2-DRY.sqlite")
FIXTURE = os.path.join(HERE, "KV-CONFLICT-40.jsonl")
R1_RESULT = os.path.join(HERE, "KVC-BASE-r1.json")
REPORT = os.path.join(HERE, "K2-DRY-REPORT.json")

BASE_MAX_ID = 20
INJECT_OLD, INJECT_NEW = 21, 22

# ---------------------------------------------------------------------------
# 确定性族键表：family -> (predicate, 行内规则, query 额外规则)
# ---------------------------------------------------------------------------
FAMILY_RULES = (
    ("车牌", "号码", (r"车牌", r"车号"), ()),
    ("工位", "地点", (r"工位", r"座位"), ()),
    ("银行卡", "尾号", (r"银行卡", r"卡号", r"尾号"), ()),
    ("邮箱", "邮箱", (r"邮箱", r"@"), ()),
    ("过敏", "过敏原", (r"过敏",), ()),
    ("健身", "时间", (r"健身",), ()),
    ("出差", "地点", (r"出差",), ()),
    ("会议", "地点", (r"会议", r"开会", r"组会", r"洽谈室", r"会议室"), (r"会",)),
    ("公司", "名称", (r"公司", r"单位", r"上班", r"跳槽"), ()),
    ("老家", "地点", (r"老家", r"故乡"), ()),
    ("车型", "车型", (r"车型", r"两厢", r"三厢", r"suv", r"mpv", r"轿车", r"越野"), ()),
    ("车色", "颜色", (r"颜色", r"车漆", r"色"), ()),
    ("猫", "名字", (r"猫",), ()),
    ("狗", "名字", (r"狗",), ()),
    ("手机", "号码", (r"手机", r"电话", r"号码", r"号"), ()),
)

SLOT_FAMILIES = ("会议", "出差")     # 这两个族再加日期/时间维度

OWNER_TERMS = (
    ("特斯拉", ("特斯拉",)),
    ("比亚迪", ("比亚迪",)),
    ("油车", ("油车",)),
    ("电车", ("电车",)),
    ("工作", ("工作号", "工作邮箱", "工作手机", "工作用", "工作")),
    ("私人", ("私人号", "私人")),
    ("备用", ("备用号", "备用邮箱", "备用")),
    ("常用", ("常用号", "常用")),
    ("主", ("主邮箱",)),
    ("个人", ("个人邮箱", "个人")),
    ("大猫", ("大猫",)),
    ("小猫", ("小猫",)),
    ("白猫", ("白猫",)),
    ("黑猫", ("黑猫",)),
    ("父亲", ("父亲", "爸爸")),
    ("母亲", ("母亲", "妈妈")),
    ("爱人", ("爱人", "老婆", "老公")),
    ("北京", ("北京",)),
    ("上海", ("上海",)),
    ("总部", ("总部",)),
    ("分部", ("分部",)),
)

_CJK = re.compile(r"[\u4e00-\u9fff]+")
_ALNUM = re.compile(r"[a-z0-9][a-z0-9@._\-]*[a-z0-9]|[a-z0-9]")
_STOP_CHARS = set(
    "的了是我你他她它在有和与及就都也很太不没吗呢吧啊呀哦嗯个一这那可以可能还又再才把被让"
    "给对从向到为以于之其或如需先继续之类说来去上下里外好那些什么多少哪里哪个怎么"
    "补充事实顺便说明记录备注另外号"
)

_DAY_RE = re.compile(
    r"(下下(?:周|星期)[一二三四五六日天]|下(?:周|星期)[一二三四五六日天]|"
    r"(?:周|星期)[一二三四五六日天])")
_TIME_RE = re.compile(r"(上午|下午|晚上|中午|早上)?([一二三四五六七八九十\d]{1,2})点")


# ---------------------------------------------------------------------------
# 抽取
# ---------------------------------------------------------------------------
def extract_slot(text):
    """会议/出差的日期维度：day 必须一致；time 仅在双方都有时才比较。"""
    t = str(text or "")
    m = _DAY_RE.search(t)
    day = m.group(1) if m else None
    m2 = _TIME_RE.search(t)
    time = ("%s%s点" % (m2.group(1) or "", m2.group(2))) if m2 else None
    if not day and not time:
        return None
    return {"day": day, "time": time}


def slot_day(slot):
    return (slot or {}).get("day")


def classify(text):
    """-> {"family","predicate","owner","rule"}；认不出 family 时为 None。"""
    low = str(text or "").lower()
    family = predicate = rule = None
    for fam, pred, patterns, extra in FAMILY_RULES:
        hit = next((p for p in patterns if re.search(p, low)), None)
        if hit is None:
            hit = next((p for p in extra if re.search(p, low)), None)
        if hit is not None:
            family, predicate, rule = fam, pred, hit
            break
    owner = None
    for name, terms in OWNER_TERMS:
        if any(t in low for t in terms):
            owner = name
            break
    return {"family": family, "predicate": predicate, "owner": owner, "rule": rule}


def query_key(text):
    return classify(text)


# 各族的"谓词值"抽取（判断同值/互补；认不出返回 None，不误判）
_CITIES = ("北京|上海|广州|深圳|杭州|南京|成都|西安|武汉|重庆|苏州|天津|长沙|郑州|"
           "山东|河南|湖南|湖北")
VALUE_PATTERNS = {
    "车牌": (r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
             r"[A-HJ-NP-Z][A-HJ-NP-Z0-9]{5}",),
    "手机": (r"1[3-9]\d(?:[-\s]?\d){8}",),
    "邮箱": (r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+",),
    "银行卡": (r"(?<!\d)\d{4,6}(?!\d)",),
    "车色": (r"(白|黑|蓝|红|灰|银|香槟|绿|黄|紫)色?",),
    "车型": (r"(两厢|三厢|SUV|MPV|轿车|越野)",),
    "工位": (r"[A-Za-z]座\s*\d+", r"\d+层\s*\d+号", r"[A-Za-z]-\d+"),
    "老家": (r"(?:老家|故乡)(?:其实)?(?:在|是)([\u4e00-\u9fff]{2,4})",),
    "出差": (r"(?:去|到)([\u4e00-\u9fff]{2,3})(?:出差|开会)",),
    "会议": (r"(\d+楼|[一二三四五六七八九十]+楼|[A-Za-z]座\s*\d+|\d+层)",
             r"(%s)" % _CITIES),
    "公司": (r"(?:在|去|到)([\u4e00-\u9fff]{2,6})(?:上班|公司|了)",
             r"(?:公司|单位)(?:是|在|叫)([\u4e00-\u9fff]{2,6})"),
    "猫": (r"(?:叫|名叫|名字是)([\u4e00-\u9fff]{2,4})",),
    "狗": (r"(?:叫|名叫|名字是)([\u4e00-\u9fff]{2,4})",),
    "过敏": (r"(?:对)?([\u4e00-\u9fff]{2,4})过敏",),
    "健身": (r"(周[一二三四五六日天]|\d+点|[一二三四五六七八九十]+点)",),
}


def extract_value(family, text):
    """该族的谓词值集合；该族无抽取器时返回 None（未知）。"""
    pats = VALUE_PATTERNS.get(family)
    if not pats:
        return None
    low = _norm(text).lower()
    vals = set()
    for pat in pats:
        for m in re.finditer(pat, low, re.I):
            v = m.group(1) if m.groups() else m.group(0)
            v = re.sub(r"^[我你他她的对]", "", v)
            v = _norm(v)
            if v:
                vals.add(v)
    return vals


# ---------------------------------------------------------------------------
# token / 文本工具
# ---------------------------------------------------------------------------
def _tokens(text):
    low = str(text or "").lower()
    toks = set()
    for m in _ALNUM.finditer(low):
        toks.add(m.group(0))
    for run in _CJK.findall(low):
        for ch in run:
            if ch not in _STOP_CHARS:
                toks.add(ch)
    return toks


def _norm(text):
    return re.sub(r"[\s\-_·—]", "", str(text or "")).lower()


def _value_hits(values, text):
    blob = _norm(text)
    return [v for v in values if _norm(v) and _norm(v) in blob]


def _residual(text, kept_text, old_text, family):
    """块内除 族值 + kept + 旧事实 + 停用词 之外的补充属性 token。"""
    toks = _tokens(text) - _tokens(kept_text) - _tokens(old_text)
    vals = extract_value(family, text) or set()
    return {t for t in toks if not any(t in v for v in vals)}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def load_base_rows():
    con = sqlite3.connect("file:%s?mode=ro" % DRY_DB.replace("\\", "/"), uri=True)
    try:
        rows = con.execute(
            "SELECT id,name,text FROM memory_source WHERE id<=? ORDER BY id",
            (BASE_MAX_ID,)).fetchall()
        max_id = con.execute("SELECT MAX(id) FROM memory_source").fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
    finally:
        con.close()
    return ([{"id": int(r[0]), "name": str(r[1]), "text": str(r[2]),
              "role": "base"} for r in rows], int(max_id or 0), int(total))


def load_cases():
    cases = []
    with open(FIXTURE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_r1_prelude():
    try:
        with open(R1_RESULT, encoding="utf-8") as f:
            d = json.load(f)
        first = d["results"][0]
        ids = [int(x.get("id")) for x in (first.get("setup") or {}).get("prelude") or []
               if x.get("action") == "remember"]
        return {"prelude_ids": ids,
                "memory_before": (first.get("setup") or {}).get("memory_before"),
                "memory_delta": (first.get("setup") or {}).get("memory_delta")}
    except (OSError, ValueError, KeyError, IndexError):
        return {"prelude_ids": None, "memory_before": None, "memory_delta": None}


def analyze_case(case, base_rows, r1):
    remembers = [a["text"] for a in case.get("pre_state") or []
                 if a.get("action") == "remember"]
    old_text, new_text = remembers[0], remembers[1]
    rows = base_rows + [
        {"id": INJECT_OLD, "name": "case-old", "text": old_text, "role": "case_old"},
        {"id": INJECT_NEW, "name": "case-new", "text": new_text, "role": "case_new"},
    ]
    # 重放注入断言：基座 20 + 21/22 = 22，且与 r1 setup.prelude 一致
    ids = [r["id"] for r in rows]
    assert ids[:BASE_MAX_ID] == list(range(1, BASE_MAX_ID + 1)), "base ids 不是 1..20"
    assert ids[BASE_MAX_ID:] == [INJECT_OLD, INJECT_NEW], "注入 id 不是 21/22"
    assert len(rows) == BASE_MAX_ID + 2 == 22, "块数不是 22"
    assert r1.get("prelude_ids") in (None, [INJECT_OLD, INJECT_NEW]), \
        "与 r1 setup.prelude id 不一致"

    qk = query_key(case["input"])
    q_slot = extract_slot(case["input"])
    classified = []
    for r in rows:
        c = dict(classify(r["text"]), slot=extract_slot(r["text"]))
        if r["role"] == "case_new":
            prev = next((x for x in classified if x["row"]["role"] == "case_old"), None)
            if prev:
                if c["family"] is None and prev["family"]:
                    # 省略式新事实继承同 case 上一条的族键
                    c = {"family": prev["family"], "predicate": prev["predicate"],
                         "owner": prev["owner"], "slot": prev["slot"],
                         "rule": "inherit:" + str(prev["rule"])}
                elif c["family"] in SLOT_FAMILIES and c["slot"] is None \
                        and prev["slot"] is not None:
                    # 省略式更新（"改到2楼会议室"）继承旧事实的日期槽
                    c["slot"] = prev["slot"]
                    c["rule"] = str(c["rule"]) + "+slot_inherit"
        classified.append(dict(c, row=r))

    q_owner = qk["owner"]

    def in_scope(x):
        if not qk["family"] or x["family"] != qk["family"]:
            return False
        if q_owner is not None and x["owner"] != q_owner:
            return False
        if qk["family"] in SLOT_FAMILIES and slot_day(q_slot):
            if slot_day(x["slot"]) and slot_day(x["slot"]) != slot_day(q_slot):
                return False
        return True

    members = [x for x in classified if in_scope(x)]
    family_found = bool(qk["family"]) and bool(members)
    primary = max(members, key=lambda x: x["row"]["id"]) if members else None
    primary_text = primary["row"]["text"] if primary else ""

    kept_primary_values = (extract_value(qk["family"], primary_text) or set()) \
        if primary else set()
    supplementary, hidden = [], []
    for x in members:
        if x is primary:
            continue
        res = _residual(x["row"]["text"], primary_text, old_text, qk["family"])
        vals = extract_value(qk["family"], x["row"]["text"])
        same_value = bool(vals is not None and kept_primary_values
                          and (vals & kept_primary_values))
        if same_value:
            supplementary.append({"id": x["row"]["id"], "reason": "same_value",
                                  "tokens": []})
        elif res:
            supplementary.append({"id": x["row"]["id"], "reason": "supplementary",
                                  "tokens": sorted(res)[:12]})
        else:
            hidden.append(x)

    visible = [primary] if primary else []
    visible += [x for x in members
                if any(s["id"] == x["row"]["id"] for s in supplementary)]
    visible_text = "\n".join(x["row"]["text"] for x in visible)

    contains_any = [str(v) for v in (case.get("expect") or {}).get("contains_any") or []]
    not_contains = [str(v) for v in (case.get("expect") or {}).get("not_contains") or []]

    expected_in_kept = bool(primary) and bool(_value_hits(contains_any, primary_text))
    expected_in_visible = bool(_value_hits(contains_any, visible_text))
    expected_hidden = (not expected_in_visible) and any(
        _value_hits(contains_any, x["row"]["text"]) for x in hidden)

    # mis_hide_other_subject：同族但主体不同的块被隐（负例护栏）
    mis_hide = any(x["family"] == qk["family"] and q_owner is not None
                   and x["owner"] != q_owner for x in hidden)

    # 同值/互补：这两类块按新规则一律保留可见，故 hidden 侧应为 0
    hidden_same_value = [
        x["row"]["id"] for x in hidden
        if (extract_value(qk["family"], x["row"]["text"]) or set())
        & kept_primary_values]
    hidden_complement = [
        x["row"]["id"] for x in hidden
        if not (extract_value(qk["family"], x["row"]["text"]) or set())]
    same_value_ids = hidden_same_value
    complement_ids = hidden_complement

    # info_loss：hidden 里除"本族值"之外的 token（值被替代不算信息损失）
    lost = _tokens("\n".join(x["row"]["text"] for x in hidden)) - _tokens(visible_text)
    lost_values = set()
    for x in hidden:
        for v in (extract_value(qk["family"], x["row"]["text"]) or set()):
            lost_values |= set(v)
    lost_core = {t for t in lost if t not in lost_values}
    old_chars = set(_norm(old_text)) - _STOP_CHARS
    unexpected = sorted(
        t for t in lost_core
        if t not in old_chars
        and not any(_norm(v) in _norm(t) or _norm(t) in _norm(v) for v in not_contains))

    return {
        "case_id": case["id"],
        "case_class": "negative" if str(case["id"]).startswith("KVN") else "positive",
        "query": case["input"],
        "family": qk["family"],
        "predicate": qk["predicate"],
        "owner": q_owner,
        "slot": q_slot,
        "family_found": family_found,
        "family_members": [{"id": x["row"]["id"], "role": x["row"]["role"],
                            "owner": x["owner"], "slot": x["slot"],
                            "text": x["row"]["text"][:90]}
                           for x in sorted(members, key=lambda x: x["row"]["id"])],
        "kept_id": primary["row"]["id"] if primary else None,
        "kept_text": primary_text[:90],
        "kept_ids": [x["row"]["id"] for x in sorted(visible, key=lambda x: x["row"]["id"])],
        "supplementary_kept": supplementary,
        "hidden_ids": [x["row"]["id"] for x in sorted(hidden, key=lambda x: x["row"]["id"])],
        "hidden_blocks": [{"id": x["row"]["id"], "role": x["row"]["role"],
                           "text": x["row"]["text"][:90]}
                          for x in sorted(hidden, key=lambda x: x["row"]["id"])],
        "expected_value": contains_any,
        "not_contains": not_contains,
        "expected_in_kept": expected_in_kept,
        # --- B 四栏 ---
        "expected_hidden": expected_hidden,
        "mis_hide_other_subject": mis_hide,
        "hide_same_value": bool(same_value_ids),
        "hide_complement": bool(complement_ids),
        "hide_same_value_or_complement": bool(same_value_ids or complement_ids),
        "hide_same_value_ids": same_value_ids,
        "hide_complement_ids": complement_ids,
        # --- info_loss ---
        "info_loss": len(lost_core),
        "info_loss_tokens": sorted(lost_core)[:12],
        "info_loss_unexpected": len(unexpected),
        "info_loss_unexpected_tokens": unexpected[:12],
        "hide_rule": ("family=%s; owner=%s; predicate=%s; slot=%s" %
                      (qk["family"], q_owner, qk["predicate"], q_slot)),
    }


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.exists(SRC_DB):
        print("error: 缺 %s" % SRC_DB)
        return 2
    shutil.copy2(SRC_DB, DRY_DB)          # 副本；原库此后不再打开
    base_rows, db_max_id, db_total = load_base_rows()
    cases = load_cases()
    r1 = load_r1_prelude()

    results = [analyze_case(c, base_rows, r1) for c in cases]

    bad = [r["case_id"] for r in results if not r["expected_in_kept"]]
    no_family = [r["case_id"] for r in results if not r["family_found"]]
    exp_hidden = [r["case_id"] for r in results if r["expected_hidden"]]
    mis_hide = [r["case_id"] for r in results if r["mis_hide_other_subject"]]
    same_or_comp = [r["case_id"] for r in results if r["hide_same_value_or_complement"]]
    info_loss = [r["case_id"] for r in results if r["info_loss"] > 0]
    info_unexp = [r["case_id"] for r in results if r["info_loss_unexpected"] > 0]
    supp_cases = [r["case_id"] for r in results if r["supplementary_kept"]]

    families = sorted({r["family"] for r in results if r["family"]})
    coverage = {f: sum(1 for r in results if r["family"] == f) for f in families}
    negatives = [r for r in results if r["case_class"] == "negative"]
    positives = [r for r in results if r["case_class"] == "positive"]

    summary = {
        "n_cases": len(results),
        "n_positive": len(positives),
        "n_negative": len(negatives),
        "base_blocks": len(base_rows),
        "db_max_id": db_max_id,
        "db_total_rows": db_total,
        "db_residual_ids": [i for i in range(BASE_MAX_ID + 1, db_max_id + 1)],
        "injected_ids": [INJECT_OLD, INJECT_NEW],
        "blocks_per_case": BASE_MAX_ID + 2,
        "r1_prelude": r1,
        "gates": {
            "expected_in_kept_false": bad,
            "expected_hidden_cases": exp_hidden,
            "mis_hide_other_subject_cases": mis_hide,
            "hide_same_value_or_complement_cases": same_or_comp,
            "all_zero": not (bad or exp_hidden or mis_hide or same_or_comp),
        },
        "family_found_false": no_family,
        "family_found_false_count": len(no_family),
        "supplementary_kept_cases": supp_cases,
        "supplementary_kept_count": sum(len(r["supplementary_kept"]) for r in results),
        "info_loss_gt0_cases": info_loss,
        "info_loss_gt0_count": len(info_loss),
        "info_loss_unexpected_gt0_cases": info_unexp,
        "families_covered": families,
        "family_coverage": coverage,
        "family_coverage_count": len(families),
        "hidden_counts": {r["case_id"]: len(r["hidden_ids"]) for r in results},
        "negative_all_zero": all(
            not r["hidden_ids"] and not r["expected_hidden"]
            and not r["mis_hide_other_subject"]
            and not r["hide_same_value_or_complement"] for r in negatives),
        "gate_expected_in_kept_pass": len(bad) == 0,
        "ambiguous_cases": [
            {"ids": ["KVC12"],
             "why": "'我换到美团了' 无族键，按同 case 上一条继承 (公司)；补充规则"},
            {"ids": ["KVC05", "KVC06"],
             "why": "基块 #3/#12 含 阿泽/实验 等非车牌属性：按'保留可见'处理，"
                    "因此旧车牌 京A88888 仍可见（无信息损失，但去旧值不彻底）"},
            {"ids": ["KVC25", "KVC26", "KVC29", "KVC30"],
             "why": "会议/出差已加日期槽（仅 day，无时刻），跨日期不再并族"},
        ],
    }

    report = {
        "schema": "k2_dry_v2",
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "source_db": os.path.relpath(SRC_DB, ROOT).replace("\\", "/"),
        "dry_db": os.path.relpath(DRY_DB, ROOT).replace("\\", "/"),
        "fixture": os.path.relpath(FIXTURE, ROOT).replace("\\", "/"),
        "fixture_sha256": sha256_file(FIXTURE),
        "dry_db_sha256": sha256_file(DRY_DB),
        "definitions": {
            "expected_in_kept": "expect.contains_any 任一项出现在主 kept 块（归一后）",
            "expected_hidden": "期望值在可见块里都没有、只出现在 hidden",
            "mis_hide_other_subject": "hidden 里出现同族但 owner 不同的块（query 带 owner 时评估）",
            "hide_same_value": "同值块被隐（本轮规则：同值块保留可见）",
            "hide_complement": "无谓词值的纯补充块被隐（本轮：带补充属性块保留可见）",
            "hide_same_value_or_complement": "hide_same_value 或 hide_complement",
            "info_loss": "hidden token 集 - 可见 kept token 集，再扣除被替代的本族值 token",
            "info_loss_unexpected": "info_loss 中扣除旧值字符后的剩余 token 数",
        },
        "summary": summary,
        "cases": results,
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("cases=%d base=%d injected=%s blocks/case=%d"
          % (len(results), len(base_rows), summary["injected_ids"],
             summary["blocks_per_case"]))
    print("GATES: expected_in_kept_false=%s expected_hidden=%s "
          "mis_hide_other_subject=%s hide_same_or_complement=%s all_zero=%s"
          % (bad, exp_hidden, mis_hide, same_or_comp, summary["gates"]["all_zero"]))
    print("family_found=false: %s" % no_family)
    print("supplementary_kept(%d): %s" % (summary["supplementary_kept_count"], supp_cases))
    print("info_loss_gt0(%d): %s" % (len(info_loss), info_loss))
    print("info_loss_unexpected_gt0(%d): %s" % (len(info_unexp), info_unexp))
    print("families(%d): %s" % (len(families), coverage))
    print("negative_all_zero=%s" % summary["negative_all_zero"])
    for r in results:
        print("%-6s fam=%-4s owner=%-4s slot=%-14s kept=%-3s supp=%-10s hidden=%-14s "
              "exp=%s/%s loss=%s/%s"
              % (r["case_id"], r["family"], r["owner"], str(r["slot"]),
                 r["kept_id"], [s["id"] for s in r["supplementary_kept"]],
                 r["hidden_ids"], r["expected_in_kept"], r["expected_hidden"],
                 r["info_loss"], r["info_loss_unexpected"]))
    print("dry_db_sha256=%s" % report["dry_db_sha256"])
    print("report_sha256=%s" % sha256_file(REPORT))
    return 0


if __name__ == "__main__":
    sys.exit(main())