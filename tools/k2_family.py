# -*- coding: utf-8 -*-
"""K2 同族只留最新（确定性族键，无模型、无副作用）。

纯函数模块：不 import 引擎/sqlite。
行结构兼容 memory_source.block_rows() 的 tuple：
    r[0]=source_id(int), r[1]=name, r[3]=text

行为（B 批准，flag 默认 off）：
  * 族键 = (family, owner, predicate[, day/time])，会议/出差必须带日期；
  * 族内只保留 id 最大者，其余同族块全部不挂（hidden_ids）；
  * 其它族可回退原 topk 补足（由调用方补）；
  * 反向保护：query 带 owner 时，只把同 owner 的行算同族
    （"工作号"不会隐"私人号"；特斯拉不会隐比亚迪）。

定性依据：out/K2-BLOCK-QUALIFY.md（#3/#12/#13 同主体旧值→隐；
#1/#2 与 KVC30 不是同一场会→留）。
"""

import re
from datetime import date, timedelta

# family -> (predicate, 行内规则, query 额外规则)
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

SLOT_FAMILIES = ("会议", "出差")     # 必须带日期；日期不同不并族

# 谓词必须"明确"：查询里要出现本族的实体/属性词（裸"号"/"色"不算）。
# 邮箱/银行卡尤其如此：谓词不明确时宁可回退，也不筛选。
STRICT_KEYWORDS = {
    "车牌": (r"车牌", r"车号"),
    "工位": (r"工位", r"座位"),
    "银行卡": (r"银行卡", r"卡号"),          # 裸"尾号"不算（可能是手机尾号）
    "邮箱": (r"邮箱", r"@"),
    "过敏": (r"过敏",),
    "健身": (r"健身",),
    "出差": (r"出差",),
    "会议": (r"会议", r"开会", r"组会", r"会议室", r"洽谈室", r"会"),
    "公司": (r"公司", r"单位", r"上班", r"跳槽"),
    "老家": (r"老家", r"故乡"),
    "车型": (r"车型", r"两厢", r"三厢", r"suv", r"mpv", r"轿车", r"越野"),
    "车色": (r"颜色", r"车漆", r"车色", r"什么色"),
    "猫": (r"猫",),
    "狗": (r"狗",),
    "手机": (r"手机", r"电话", r"号码", r"工作号", r"私人号", r"备用号", r"常用号"),
}

OWNER_TERMS = (
    ("特斯拉", ("特斯拉",), ("车型", "车色")),
    ("比亚迪", ("比亚迪",), ("车型", "车色")),
    ("油车", ("油车",), ("车型", "车色")),
    ("电车", ("电车",), ("车型", "车色")),
    ("工作", ("工作号", "工作邮箱", "工作手机", "工作用", "工作"), ("手机", "邮箱")),
    ("私人", ("私人号", "私人"), ("手机", "邮箱")),
    ("备用", ("备用号", "备用邮箱", "备用"), ("手机", "邮箱")),
    ("常用", ("常用号", "常用"), ("手机", "邮箱")),
    ("主", ("主邮箱",), ("邮箱",)),
    ("个人", ("个人邮箱", "个人"), ("邮箱",)),
    ("大猫", ("大猫",), ("猫",)),
    ("小猫", ("小猫",), ("猫",)),
    ("白猫", ("白猫",), ("猫",)),
    ("黑猫", ("黑猫",), ("猫",)),
    ("父亲", ("父亲", "爸爸"), ("老家",)),
    ("母亲", ("母亲", "妈妈"), ("老家",)),
    ("爱人", ("爱人", "老婆", "老公"), ("老家",)),
    ("北京", ("北京",), ("工位",)),
    ("上海", ("上海",), ("工位",)),
    ("总部", ("总部",), ("工位",)),
    ("分部", ("分部",), ("工位",)),
)

_DAY_RE = re.compile(
    r"(下下(?:周|星期)[一二三四五六日天]|下(?:周|星期)[一二三四五六日天]|"
    r"(?:周|星期)[一二三四五六日天])")
_TIME_RE = re.compile(r"(上午|下午|晚上|中午|早上)?([一二三四五六七八九十\d]{1,2})点")


def extract_slot(text):
    """会议/出差的日期槽；返回 {day,time} 或 None。"""
    t = str(text or "")
    m = _DAY_RE.search(t)
    day = m.group(1) if m else None
    m2 = _TIME_RE.search(t)
    time = ("%s%s点" % (m2.group(1) or "", m2.group(2))) if m2 else None
    if not day and not time:
        return None
    return {"day": day, "time": time}


def _classify(text, query=False):
    low = str(text or "").lower()
    family = predicate = None
    for fam, pred, patterns, extra in FAMILY_RULES:
        hit = next((p for p in patterns if re.search(p, low)), None)
        if hit is None and query:
            hit = next((p for p in extra if re.search(p, low)), None)
        if hit is not None:
            family, predicate = fam, pred
            break
    owner = None
    for name, terms, families in OWNER_TERMS:
        if family is not None and family not in families:
            continue                      # 主体词的适用族（北京只算工位主体，不算出差目的地）
        if any(t in low for t in terms):
            owner = name
            break
    slot = extract_slot(text) if family in SLOT_FAMILIES else None
    return {"family": family, "predicate": predicate, "owner": owner, "slot": slot}


def classify_row(text):
    return _classify(text, query=False)


def classify_query(text):
    return _classify(text, query=True)


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


def _slot_ok(q_slot, row_slot):
    """date 必须相等（无日期的延续块允许并入）；
    时刻：query 无时刻时，带明确时刻的块属另一场会/另一趟差 -> 不并。"""
    q_day = (q_slot or {}).get("day")
    r_day = (row_slot or {}).get("day")
    if r_day is None:
        return True
    if r_day != q_day:
        return False
    q_time = (q_slot or {}).get("time")
    r_time = (row_slot or {}).get("time")
    if q_time is None:
        return r_time is None
    return r_time is None or r_time == q_time


def _meta_entry(times, rid, modes):
    v = (times or {}).get(rid)
    if v is None:
        v = (times or {}).get(str(rid))
    created_at, mode = None, None
    if isinstance(v, dict):
        created_at, mode = v.get("created_at"), v.get("mode")
    elif isinstance(v, (tuple, list)):
        created_at = v[0] if len(v) > 0 else None
        mode = v[1] if len(v) > 1 else None
    else:
        created_at = v
    if modes:
        m = modes.get(rid, modes.get(str(rid)))
        if m:
            mode = m
    return created_at, mode


def _created_at_of(times, rid, modes):
    return _meta_entry(times, rid, modes)[0]


def _mode_of(times, rid, modes):
    return _meta_entry(times, rid, modes)[1]


def _date_of(created_at):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(created_at or ""))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


PERIODIC_RE = re.compile(r"每(?:周|星期|月|年|天|日|晚|个)")
ARCHIVE_MODES = ("auto_archive", "auto_summary", "auto_turn")
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
_WEEK_RE = re.compile(r"(下下|下|这|本)?(?:周|星期)([一二三四五六日天])")


def is_periodic(text):
    """每周/每月/每年/每周X/每天 -> 周期性事实，不参与过期过滤。"""
    return bool(PERIODIC_RE.search(str(text or "")))


def parse_relative_date(text, base):
    """把 "明天/后天/下周三/本周X/周三" 解析成绝对日期（相对 base）。"""
    t = str(text or "")
    m = _WEEK_RE.search(t)
    if m:
        prefix = m.group(1) or ""
        target = _WEEKDAY.get(m.group(2))
        if target is None:
            return None
        monday = base - timedelta(days=base.weekday())
        if prefix == "下":
            monday += timedelta(days=7)
        elif prefix == "下下":
            monday += timedelta(days=14)
        return monday + timedelta(days=target)
    if "大后天" in t:
        return base + timedelta(days=3)
    if "后天" in t:
        return base + timedelta(days=2)
    if "明天" in t:
        return base + timedelta(days=1)
    if "今天" in t:
        return base
    return None


def _is_expired(family, text, created_at, mode, ref_day):
    """只对一次性 meeting/travel：periodic / 归档 / 无法解析 -> 不过滤。"""
    if family not in SLOT_FAMILIES:
        return False
    if (mode or "") in ARCHIVE_MODES:
        return False                     # 归档块只参与排序，不参与相对日期解析
    if is_periodic(text):
        return False                     # 每周/每月... 周期事实不过期
    base = _date_of(created_at)
    if base is None:
        return False
    target = parse_relative_date(text, base)
    if target is None:
        return False
    return target < ref_day


def resolve_family(query, rows, times=None, modes=None, today=None):
    """-> {"family","owner","predicate","slot","members","kept_id","hidden_ids"} 或 None。

    times: id -> created_at 字符串（或 {"created_at","mode"} / (created_at, mode)）；
           有 times 时族内按 created_at DESC, id DESC 排序，否则退回 id。
    modes: id -> mode（可选，auto_archive/auto_summary/auto_turn 视为归档）。
    today: 查询日（date），默认 date.today()；仅用于一次性 meeting/travel 的过期判断。
    None = 认不出族 / 会议出差缺日期 / 族内无行（调用方回退原逻辑）。
    """
    q = str(query or "").strip()
    if not q or not rows:
        return None
    qk = classify_query(q)
    family = qk["family"]
    if not family:
        return None
    q_slot = qk["slot"]
    if family in SLOT_FAMILIES and not (q_slot or {}).get("day"):
        return None                      # 会议/出差必须带日期
    q_owner = qk["owner"]

    members = []
    for r in rows:
        c = classify_row(_row_text(r))
        if c["family"] != family:
            continue
        # 反向保护：query 带 owner 时只并同 owner；query 无 owner 时同族各行都算
        #（"我的邮箱是什么" 可命中"工作邮箱"这条最新事实）
        if q_owner is not None and c["owner"] != q_owner:
            continue
        if family in SLOT_FAMILIES and not _slot_ok(q_slot, c["slot"]):
            continue
        members.append((_row_id(r), _row_name(r), r, c))

    if not members:
        return None
    # 排序：created_at DESC, id DESC（无 times 时退回 id，兼容旧行为）
    members.sort(key=lambda m: (_created_at_of(times, m[0], modes) or "", m[0]))
    ref_day = today or date.today()
    expired = []
    live = []
    for m in members:
        if _is_expired(family, _row_text(m[2]), _created_at_of(times, m[0], modes),
                       _mode_of(times, m[0], modes), ref_day):
            expired.append(m[0])
        else:
            live.append(m)
    if not live:
        return None                      # 全过期：无 kept 可挂，交回原逻辑
    kept = live[-1]
    hidden = [m[0] for m in live[:-1]] + expired
    return {"family": family,
            "owner": q_owner,
            "predicate": qk["predicate"],
            "slot": q_slot,
            "members": [m[0] for m in members],
            "member_owners": [m[3]["owner"] for m in members],
            "kept_id": kept[0],
            "kept_name": kept[1],
            "kept_row": kept[2],
            "expired_ids": expired,
            "hidden_ids": hidden}


def _predicate_clear(family, query):
    """查询里必须出现本族的实体/属性词（裸"号"/"色"等不算明确谓词）。"""
    pats = STRICT_KEYWORDS.get(family) or ()
    low = str(query or "").lower()
    return any(re.search(p, low) for p in pats)


def select_k2(rows, query, topk=4, times=None, modes=None, today=None):
    """命中族 -> [kept 的候选 dict]；任一条件不明确 -> None（回退原逻辑）。

    返回筛选结果必须同时满足：
      * family 明确（且会议/出差带日期槽）；
      * owner/predicate 明确（谓词词表命中；owner 歧义则不筛）；
      * kept 非空，且确有同族旧块可隐（hidden 非空，避免只做重排）。
    times/modes/today 见 resolve_family：有 times 时按 created_at DESC, id DESC 排序，
    一次性 meeting/travel 早于 today 的块进 hidden（不挂）。
    """
    fam = resolve_family(query, rows, times=times, modes=modes, today=today)
    if not fam:
        return None
    if not fam["hidden_ids"]:
        return None                      # 没有同族旧块可隐 -> 交给原逻辑
    if not _predicate_clear(fam["family"], query):
        return None                      # 谓词不明确（如只说"尾号"）
    q_owner = fam["owner"]
    owners = {o for o in (fam.get("member_owners") or []) if o}
    if q_owner is None and len(owners) > 1:
        return None                      # 同族出现多个主体：歧义，不筛
    try:
        limit = max(1, int(topk))
    except (TypeError, ValueError):
        limit = 1
    row = fam["kept_row"]
    return [{
        "name": fam["kept_name"],
        "score": 9.0,
        "source_id": fam["kept_id"],
        "signals": {
            "hits": [], "tags": [], "related": False,
            "k2": True, "why": "k2_family",
            "family": fam["family"], "owner": fam["owner"],
            "predicate": fam["predicate"], "slot": fam["slot"],
            "members": fam["members"][:limit * 4] if limit else fam["members"],
            "hidden_ids": fam["hidden_ids"],
            "expired_ids": fam.get("expired_ids") or [],
            "kept_id": fam["kept_id"],
            "library": len(rows),
        },
    }]