# -*- coding: utf-8 -*-
"""K2a 硬键精确检索（确定性、无模型、可回退）。

纯函数模块：不 import 引擎/sqlite/sql，便于 CPU 单测（零 GPU、零服务）。
行结构兼容 memory_source.block_rows() 的 tuple：
    r[0]=source_id(int), r[1]=name, r[2]=label, r[3]=text, ...
本模块只读行，不写库、不改块、不改 id。

对外：
    extract_keys(query) -> dict（plate/phone/email/bank_tail/emp_id/entity）
    select_exact(rows, query, topk) -> list[dict] | None
"""

import re

# ---------------------------------------------------------------------------
# 抽取规则（严格按 out/K2A-SPEC.md §2）
# ---------------------------------------------------------------------------
PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"

# 车牌：省份简称 + 字母（不含 I/O）+ 5 位字母数字；大小写归一大写。
# 查询/行文本先剥掉常见分隔符（· - 空格等），因此"京A·12345"与"京A12345"等价。
_PLATE_SEP_RE = re.compile(r"[\s·•・.\-—_]+")
_PLATE_RE = re.compile(
    r"(?<![A-Z0-9])[%s][A-HJ-NP-Z][A-HJ-NP-Z0-9]{5}(?![A-Z0-9])" % PROVINCES)

# 手机号：1[3-9] 开头 11 位，允许 -/空格（含全角）分隔；归一为 11 位数字。
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d(?:[-\s－—]?\d){8}(?!\d)")

# 邮箱：标准形态，小写归一。
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")

# 卡尾号：问句含 尾号|卡号 时才抽 4–6 位数字。
_BANK_Q_RE = re.compile(r"尾号|卡号")
_BANK_TAIL_RE = re.compile(r"(?<!\d)\d{4,6}(?!\d)")

# 工号：问句含 工号|员工号 时才抽 3–10 位字母数字。
_EMP_Q_RE = re.compile(r"工号|员工号")
_EMP_ID_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{3,10}(?![A-Za-z0-9])")

# 实体别名固定词表：canonical -> 行内可出现的别名（含本名）。
ENTITY_ALIASES = (
    ("宠物", ("猫", "狗", "宠物", "猫咪", "小狗")),
    ("工位", ("工位", "座位")),
    ("公司", ("公司", "单位")),
    ("老家", ("老家", "故乡")),
    ("过敏", ("过敏",)),
    ("健身", ("健身",)),
    ("会议", ("会议", "开会")),
    ("银行卡", ("银行卡",)),
)
_ENTITY_TERMS = dict(ENTITY_ALIASES)

# 谓词词表：问句出现时，候选行必须同时含该词（反向保护：工作号 vs 私人号）。
PREDICATE_TERMS = ("工作", "私人", "家庭", "个人", "备用", "紧急", "临时")

EXACT_SCORE = 9.0
_HARD_KEYS = ("plate", "phone", "email", "bank_tail", "emp_id")


# ---------------------------------------------------------------------------
# 抽取
# ---------------------------------------------------------------------------
def extract_keys(query):
    """从问句抽硬键；抽不到就是 None/[]（不猜、不补）。"""
    q = str(query or "")
    out = {"plate": None, "phone": None, "email": None,
           "bank_tail": None, "emp_id": None, "entity": []}
    if not q.strip():
        return out

    plate_blob = _PLATE_SEP_RE.sub("", q).upper()
    m = _PLATE_RE.search(plate_blob)
    if m:
        out["plate"] = m.group(0)

    m = _PHONE_RE.search(q)
    if m:
        out["phone"] = re.sub(r"\D", "", m.group(0))

    m = _EMAIL_RE.search(q)
    if m:
        out["email"] = m.group(0).lower()

    if _BANK_Q_RE.search(q):
        tails = _BANK_TAIL_RE.findall(q)
        if tails:
            out["bank_tail"] = tails[0]

    if _EMP_Q_RE.search(q):
        m = _EMP_ID_RE.search(q)
        if m:
            out["emp_id"] = m.group(0).upper()

    out["entity"] = [canon for canon, terms in ENTITY_ALIASES
                     if any(t in q for t in terms)]
    return out


def extract_predicates(query):
    """问句里的限定谓词（工作/私人/家庭/…）；空表示无谓词约束。"""
    q = str(query or "")
    return [t for t in PREDICATE_TERMS if t in q]


# ---------------------------------------------------------------------------
# 行匹配（只读文本）
# ---------------------------------------------------------------------------
def _row_id(row):
    try:
        return int(row[0])
    except (TypeError, ValueError, IndexError):
        return -1


def _row_name(row):
    try:
        return str(row[1])
    except IndexError:
        return ""


def _row_text(row):
    try:
        return str(row[3] or "")
    except IndexError:
        return ""


def _match_plate(text, key):
    return key in _PLATE_SEP_RE.sub("", text).upper()


def _match_phone(text, key):
    return key in re.sub(r"[-\s－—]", "", text)


def _match_email(text, key):
    return key in text.lower()


def _match_bank_tail(text, key):
    for run in re.findall(r"\d+", text):
        if run == key or (len(run) > len(key) and run.endswith(key)):
            return True
    return False


def _match_emp_id(text, key):
    pat = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(key), re.I)
    return bool(pat.search(text))


def _match_entity(text, canon):
    return any(t in text for t in _ENTITY_TERMS.get(canon, ()))


_MATCHERS = {
    "plate": _match_plate,
    "phone": _match_phone,
    "email": _match_email,
    "bank_tail": _match_bank_tail,
    "emp_id": _match_emp_id,
}


# ---------------------------------------------------------------------------
# 选择
# ---------------------------------------------------------------------------
def select_exact(rows, query, topk=4):
    """硬键命中 -> [{name,score,source_id,signals}]；无命中/歧义 -> None。

    规则（spec §3，B 修订后）：
      1. 抽到硬键：取文本含该键（归一后）的行；
      2. 问句含谓词（工作/私人/…）时只保留含该谓词的行，反向保护（不匹配就不选）；
      3. 只做"按键召回"：保持 rows 输入顺序，score 统一常量，**不按 id 排序、不选最新**；
      4. 无命中 -> None（调用方完全回退原逻辑）。
    """
    q = str(query or "").strip()
    if not q or not rows:
        return None
    try:
        limit = max(1, int(topk))
    except (TypeError, ValueError):
        limit = 1

    keys = extract_keys(q)
    hard = [(k, keys.get(k)) for k in _HARD_KEYS if keys.get(k)]
    hits = {}                      # id -> [row, [label, ...]]
    preds = extract_predicates(q) if hard else []

    if hard:
        for r in rows:
            text = _row_text(r)
            labels = []
            for k, key in hard:
                try:
                    if _MATCHERS[k](text, key):
                        labels.append("%s:%s" % (k, key))
                except Exception:                        # noqa: BLE001
                    continue
            if not labels:
                continue
            # 反向保护：问"工作号"时，只有"私人号"的行不得入选
            if preds and not all(p in text for p in preds):
                continue
            rid = _row_id(r)
            if rid in hits:
                hits[rid][1].extend(labels)
            else:
                hits[rid] = [r, labels]
        if not hits:
            return None
    else:
        ents = [e for e in (keys.get("entity") or []) if e]
        if not ents:
            return None
        for r in rows:
            text = _row_text(r)
            labels = ["entity:%s" % e for e in ents if _match_entity(text, e)]
            if not labels:
                continue
            rid = _row_id(r)
            if rid in hits:
                hits[rid][1].extend(labels)
            else:
                hits[rid] = [r, labels]
        if not hits:
            return None

    # 保持 rows 的原始顺序（不按 id 重排、不挑"最新"）：纯召回，选择留给上层。
    out = []
    for rid, (r, labels) in hits.items():
        name = _row_name(r)
        out.append({
            "name": name,
            "score": EXACT_SCORE,
            "source_id": rid,
            "signals": {
                "hits": labels[:6],
                "tags": [],
                "related": False,
                "exact": True,
                "why": "exact_key",
                "keys": {k: v for k, v in keys.items() if v},
                "predicates": preds,
                "library": len(rows),
            },
        })
        if len(out) >= limit:
            break
    return out or None