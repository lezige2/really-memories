# -*- coding: utf-8 -*-
"""event_time.py -- 写入时间归一化（P0，确定性、无模型）。

语义按 out/P0-EVENTDATE-SPEC.md §8 写死：
  * 基准 = created_at_utc 转 Asia/Shanghai 的本地日期；
  * 下周X = 下一 ISO 周的周X（今天恰为周X → +7）；
  * 这周X 已过 → ambiguous（不回填、不下移）；今天 = 该周X → 当天；
  * 裸“周X/星期X”：今天恰为周X → +7；否则取本周内未来那天；
  * 下个月 N 号（12→1 月）；月底 = 当月最后一天，已过 → ambiguous；
  * 晚上/半夜 12 点 = 次日 00:00；凌晨 N 点 = 当天；晚上 11:59 = 当天；
  * periodic（每天/每周/每月/每年/每工作日）不写 event_date；
  * 归档/回填由调用方 allow_parse=False 跳过。

对外：
  parse_event_time(text, created_at_utc, tz="Asia/Shanghai") -> dict
  is_time_query(query) -> bool              # 检索侧确定性词表
  is_periodic(text) -> bool
  is_expired(event_date, today) -> bool      # event_date < today 才算过期
  filter_expired(rows_meta, query, today)    # 仅“问时间”时用
"""

import re
from datetime import date, datetime, timedelta, timezone

EVENT_PARSER_VERSION = "event-time-1.0"
EVENT_TZ_NAME = "Asia/Shanghai"
# 固定 +08:00（中国无夏令时），避免依赖 tzdata 安装
_SH = timezone(timedelta(hours=8))
_ARCHIVE_MODES = ("auto_archive", "auto_summary", "auto_turn")

_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6,
           "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}

PERIODIC_RE = re.compile(r"每(?:天|日|周|星期|礼拜|月|年|个?工作日)")
_DATE_RE = re.compile(
    r"(?:(?P<this>这|本)(?:周|星期|礼拜)|"
    r"(?P<next>下下|下)(?:周|星期|礼拜)|"
    r"(?:周|星期|礼拜))(?P<wd>[一二三四五六日天])")
_DAY_OFFSET_RE = re.compile(r"大后天|后天|明天|今天|今晚|今早|今晨")
_DAY_OFFSET = {"今天": 0, "今晚": 0, "今早": 0, "今晨": 0,
               "明天": 1, "后天": 2, "大后天": 3}
_WEEK_ONLY_RE = re.compile(r"下下(?:周|星期|礼拜)|下(?:周|星期|礼拜)")
# 裸周X 当天可判定“就是今天”的时刻/截止词（§8.3）
_SAME_DAY_RE = re.compile(r"下班前|上班前|今晚|今夜|中午前")
_MONTH_DAY_RE = re.compile(r"(?P<next>下个?月)\s*(?P<d>\d{1,2}|[一二三四五六七八九十]{1,3})\s*[号日]")
_MONTH_END_RE = re.compile(r"(?P<next>下个?月)?月底")
_TIME_RE = re.compile(
    r"(?P<period>上午|下午|晚上|夜里|半夜|凌晨|早上|中午|今晚|今夜)?\s*"
    r"(?P<h>\d{1,2}|[一二三四五六七八九十]{1,3})\s*[点時时]"
    r"(?:\s*(?P<m>\d{1,2})\s*分|(?P<half>半))?")

# 检索侧“明确问时间”的确定性词表（不含模型判断）
_TIME_QUERY_RE = re.compile(
    r"今天|明天|后天|大后天|本周|这周|下周|下下周|周[一二三四五六日天]|"
    r"星期[一二三四五六日天]|礼拜[一二三四五六日天]|几号|哪天|什么时候|"
    r"什么时间|几点|多久|到期|截止|deadline|会议时间|约在|定在")


CREATED_AT_SEMANTICS = "v1_local_naive"


def _to_local(created_at_utc, tz=EVENT_TZ_NAME):
    """v1_local_naive：created_at 按**本地朴素时间**解析，**不做任何时区转换**。

    带 +00:00/Z 的旧值也不换算（描述现实：历史 created_at 不保证是 UTC）。
    """
    s = str(created_at_utc or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
        if not m:
            return None
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _cn_int(tok):
    tok = str(tok or "").strip()
    if tok.isdigit():
        return int(tok)
    if tok in _CN_NUM:
        return _CN_NUM[tok]
    if tok.startswith("十") and len(tok) == 2:
        return 10 + _CN_NUM.get(tok[1], 0)
    return None


def is_periodic(text):
    return bool(PERIODIC_RE.search(str(text or "")))


def _last_day(year, month):
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    return nxt - timedelta(days=1)


def _month_shift(base, n=1):
    y = base.year + (base.month - 1 + n) // 12
    m = (base.month - 1 + n) % 12 + 1
    return y, m


def _base_meta(basis, confidence, source, day, time_str):
    return {"event_date": day, "event_time": time_str, "event_source": source,
            "event_tz": EVENT_TZ_NAME, "event_confidence": confidence,
            "event_parser_version": EVENT_PARSER_VERSION, "periodic": False,
            "event_basis_ts": basis, "created_at_semantics": CREATED_AT_SEMANTICS}


def _ambiguous(source, basis=None):
    return _base_meta(basis, "ambiguous", source, None, None)


def _none(source="", basis=None):
    return _base_meta(basis, "none", source, None, None)


def _mk(day, source, time_str=None, basis=None):
    return _base_meta(basis, "high", source, day, time_str)


def _basis_ts(created_at):
    dt = _to_local(created_at)
    return dt.isoformat(timespec="seconds") if dt else None


def _parse_time_of_day(text):
    """-> (time_str|None, date_shift) ；晚上/半夜 12 点 -> 次日 00:00。"""
    m = _TIME_RE.search(str(text or ""))
    if not m:
        return None, 0
    period = m.group("period") or ""
    h = _cn_int(m.group("h"))
    if h is None or not (0 <= h <= 24):
        return None, 0
    minute = 0
    if m.group("m"):
        minute = int(m.group("m"))
    elif m.group("half"):
        minute = 30
    shift = 0
    if period in ("晚上", "夜里", "半夜", "今晚", "今夜") and h == 12:
        h, shift = 0, 1                    # 次日 00:00
    elif period == "凌晨":
        if h == 12:
            h = 0                          # 凌晨 12 点 = 当天 00:00
    elif period in ("下午", "晚上", "夜里", "今晚", "今夜") and h < 12:
        h += 12
    elif period == "中午" and h < 11:
        h += 12
    if h > 23:
        return None, 0
    return "%02d:%02d" % (h, minute), shift


def _resolve_date(text, base):
    """-> (date|None, confidence, source) ；只解析日期部分。"""
    wm = _DATE_RE.search(text)
    m = _DAY_OFFSET_RE.search(text)
    # “周五（今天=周五）”这类：同时出现今天+周X 时以周X为准
    if m and wm and m.group(0) == "今天":
        m = None
    if m:
        word = m.group(0)
        return base + timedelta(days=_DAY_OFFSET[word]), "high", word

    m = _MONTH_DAY_RE.search(text)
    if m and m.group("next"):
        n = _cn_int(m.group("d"))
        y, mo = _month_shift(base, 1)      # 12 月 -> 次年 1 月
        if n is None or not (1 <= n <= _last_day(y, mo).day):
            return None, "ambiguous", m.group(0)
        return date(y, mo, n), "high", m.group(0)

    m = _MONTH_END_RE.search(text)
    if m:
        if m.group("next"):
            y, mo = _month_shift(base, 1)
        else:
            y, mo = base.year, base.month
        last = _last_day(y, mo)
        if not m.group("next") and last < base:
            return None, "ambiguous", m.group(0)      # “月底”已过 -> ambiguous
        return last, "high", m.group(0)

    m = _DATE_RE.search(text)
    if m:
        wd = _WEEKDAY[m.group("wd")]
        monday = base - timedelta(days=base.weekday())
        if m.group("next") == "下下":
            return monday + timedelta(days=14 + wd), "high", m.group(0)
        if m.group("next") == "下":
            return monday + timedelta(days=7 + wd), "high", m.group(0)
        if m.group("this"):
            target = monday + timedelta(days=wd)
            if target < base:
                return None, "ambiguous", m.group(0)  # 这周X 已过
            return target, "high", m.group(0)
        # 裸 周X：今天恰为周X——带明确时刻/“下班前/上班前/今晚”= 当天；
        # 仅日期且无时刻 = +7；本周内未来 -> 本周；已过 -> 下周。
        if wd == base.weekday():
            if _parse_time_of_day(text)[0] or _SAME_DAY_RE.search(text):
                return base, "high", m.group(0)
            return base + timedelta(days=7), "high", m.group(0)
        target = monday + timedelta(days=wd)
        if target >= base:
            return target, "high", m.group(0)
        return monday + timedelta(days=7 + wd), "high", m.group(0)
    if _WEEK_ONLY_RE.search(text):
        return None, "ambiguous", _WEEK_ONLY_RE.search(text).group(0)  # “下周”无星期
    return None, "none", ""


def parse_event_time(text, created_at_utc, tz=EVENT_TZ_NAME, allow_parse=True):
    """-> dict(event_date,event_time,event_source,event_tz,event_confidence,
               event_parser_version,periodic,event_basis_ts,created_at_semantics)。

    v1_local_naive：created_at 按本地朴素时间解析，**不做任何时区转换**；
    allow_parse=False（归档/回填）不解析；periodic 不写 event_date。
    """
    t = str(text or "")
    basis = _basis_ts(created_at_utc)
    if not allow_parse:
        return _none("", basis)
    if is_periodic(t):
        res = _none(PERIODIC_RE.search(t).group(0), basis)
        res.update({"periodic": True,
                    "event_confidence": "none",
                    "event_date": None})
        return res
    local = _to_local(created_at_utc, tz)
    if local is None:
        return _none("", basis)
    base = local.date()
    time_str, shift = _parse_time_of_day(t)
    day, conf, source = _resolve_date(t, base)
    if conf == "ambiguous":
        return _ambiguous(source, basis)
    if day is None and time_str and shift:
        # 只有时刻且跨天（半夜/晚上 12 点）-> 次日 00:00
        return _mk(base + timedelta(days=1), source or time_str, time_str, basis)
    if day is None:
        return _none("", basis)
    if shift:
        day = day + timedelta(days=1)
    src = source + ((" " + time_str) if time_str else "")
    return _mk(day, src, time_str, basis)


def is_time_query(query):
    return bool(_TIME_QUERY_RE.search(str(query or "")))


def is_expired(event_date, today):
    """event_date < today 才算过期；当天不过期；None 不过期。"""
    if not event_date:
        return False
    if isinstance(event_date, str):
        try:
            event_date = date.fromisoformat(event_date[:10])
        except ValueError:
            return False
    return event_date < today


def filter_expired(rows_meta, query, today):
    """检索侧最小实现：只对“明确问时间”的查询过滤过期一次性事件。

    rows_meta: [{id,text,event_date,event_confidence,periodic,mode}]
    periodic / ambiguous / 归档 mode 一律豁免。
    """
    if not is_time_query(query):
        return list(rows_meta)
    out = []
    for r in rows_meta:
        if r.get("periodic"):
            out.append(r)
            continue
        if (r.get("mode") or "") in _ARCHIVE_MODES:
            out.append(r)
            continue
        if (r.get("event_confidence") or "") not in ("high",):
            out.append(r)
            continue
        if is_expired(r.get("event_date"), today):
            continue
        out.append(r)
    return out