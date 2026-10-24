"""实体与情绪抽取（规则版）。

抽 时间 / 人物 / 地点 / 事件，并记录在原文中的句子编号与字符偏移。
事件与主题另外由关键词+向量通道覆盖，这里只收可命名的事件类型，
避免把噪声词塞进实体表。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .textutil import CJK_RE, normalize, now, split_sentences, tokenize

WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

TIME_ABS = {
    "今天": 0, "昨天": -1, "前天": -2, "大前天": -3,
    "明天": 1, "后天": 2, "大后天": 3,
}

EVENT_WORDS = [
    "生日", "纪念日", "旅行", "旅游", "出差", "加班", "面试", "考试", "毕业",
    "搬家", "换工作", "离职", "入职", "结婚", "订婚", "分手", "和好", "吵架",
    "看病", "住院", "手术", "看电影", "打游戏", "健身", "跑步", "唱歌",
    "春节", "中秋", "圣诞", "元旦", "跨年", "过年", "聚餐", "约会",
]

EMOTION_STRONG = {
    "崩溃": 0.9, "绝望": 0.9, "大哭": 0.85, "想哭": 0.75, "心碎": 0.9,
    "痛苦": 0.85, "暴怒": 0.9, "狂喜": 0.85, "激动": 0.7, "害怕": 0.75,
    "恐惧": 0.85, "焦虑": 0.75, "抑郁": 0.9, "孤独": 0.7, "委屈": 0.75,
    "感动": 0.7, "幸福": 0.8, "开心": 0.7, "难过": 0.75, "伤心": 0.8,
    "生气": 0.7, "愤怒": 0.8, "烦": 0.55, "很累": 0.6, "好累": 0.6,
    "压力": 0.65, "内耗": 0.75, "讨厌": 0.6, "喜欢": 0.6, "爱": 0.6,
}
INTENSIFIERS = ("特别", "非常", "超级", "极其", "真的", "太", "巨", "贼", "好")

RELATIONS = (
    "妈妈", "爸爸", "老妈", "老爸", "母亲", "父亲", "老婆", "老公", "妻子", "丈夫",
    "女朋友", "男朋友", "对象", "儿子", "女儿", "弟弟", "妹妹", "哥哥", "姐姐",
    "朋友", "同事", "同学", "室友", "老板", "领导", "老师", "客户",
)

NAME_CHARS = r"[^\s，。！？、,.!?；;：:（）()\[\]【】\"'“”‘’]{1,12}"


@dataclass
class Mention:
    type: str            # time | person | place | event
    value: str           # 归一化值（时间存 ISO 日期）
    surface: str
    sentence_idx: int
    start: int
    end: int
    meta: dict = field(default_factory=dict)


@dataclass
class Extraction:
    mentions: list[Mention] = field(default_factory=list)
    emotion: float = 0.0
    topics: list[str] = field(default_factory=list)
    correction: bool = False


def _clean_name(raw: str) -> str:
    s = raw.strip()
    s = re.split(r"[，。！？、,.!?；;：:\s]", s)[0]
    for tail in ("啦", "啊", "呀", "哦", "呢", "吧", "哈", "嘛", "的"):
        if s.endswith(tail) and len(s) > len(tail) + 1:
            s = s[: -len(tail)]
    return s.strip()


def _resolve_weekday(base: date, wd: int, which: str) -> date:
    monday = base - timedelta(days=base.weekday())
    if which == "last":
        monday -= timedelta(days=7)
    elif which == "next":
        monday += timedelta(days=7)
    return monday + timedelta(days=wd)


def _time_mentions(text: str, base: datetime, sent_idx: int, offset: int) -> list[Mention]:
    out: list[Mention] = []

    def add(m: re.Match, value: str, precision: str, label: str) -> None:
        out.append(Mention("time", value, m.group(0), sent_idx,
                           offset + m.start(), offset + m.end(),
                           {"precision": precision, "label": label}))

    for word, delta in TIME_ABS.items():
        for m in re.finditer(re.escape(word), text):
            d = base.date() + timedelta(days=delta)
            add(m, d.isoformat(), "day", word)

    for m in re.finditer(r"(上周|这周|本周|下周|上星期|这星期|下星期)", text):
        w = m.group(1)
        delta_weeks = -1 if w.startswith("上") else (1 if w.startswith("下") else 0)
        d = base.date() + timedelta(weeks=delta_weeks)
        add(m, d.isoformat(), "week", w)

    for m in re.finditer(r"(上个月|这个月|本月|下个月)", text):
        w = m.group(1)
        delta = -1 if w.startswith("上") else (1 if w.startswith("下") else 0)
        y, mo = base.year, base.month + delta
        while mo < 1:
            mo += 12
            y -= 1
        while mo > 12:
            mo -= 12
            y += 1
        add(m, f"{y:04d}-{mo:02d}", "month", w)

    for m in re.finditer(r"(去年|今年|明年|前年|后年)", text):
        w = m.group(1)
        delta = {"去年": -1, "前年": -2, "明年": 1, "后年": 2}.get(w, 0)
        add(m, f"{base.year + delta:04d}", "year", w)

    for m in re.finditer(r"(上|这|本|下)?(?:周|星期)([一二三四五六日天])", text):
        which = "last" if m.group(1) == "上" else ("next" if m.group(1) == "下" else "this")
        d = _resolve_weekday(base.date(), WEEKDAYS[m.group(2)], which)
        add(m, d.isoformat(), "day", m.group(0))

    for m in re.finditer(r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]", text):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        add(m, d.isoformat(), "day", m.group(0))

    for m in re.finditer(r"(?<!\d)(\d{1,2})月(\d{1,2})[日号]", text):
        try:
            d = date(base.year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            continue
        if d < base.date() - timedelta(days=180):
            d = date(base.year + 1, d.month, d.day)
        add(m, d.isoformat(), "day", m.group(0))

    for m in re.finditer(r"(生日|纪念日)", text):
        # 无具体日期时只记「年度事件」，供时间通道按最近纪念日加权
        out.append(Mention("time", m.group(1), m.group(0), sent_idx,
                           offset + m.start(), offset + m.end(),
                           {"precision": "annual", "label": m.group(1)}))

    return out


def _person_mentions(text: str, sent_idx: int, offset: int,
                     known_people: dict[str, str]) -> list[Mention]:
    out: list[Mention] = []

    def add(m: re.Match, value: str, group: int = 1, role: str | None = None) -> None:
        surface = m.group(0)
        out.append(Mention("person", value, surface, sent_idx,
                           offset + m.start(), offset + m.end(),
                           {"role": role} if role else {}))

    for m in re.finditer(r"我叫(" + NAME_CHARS + r")", text):
        name = _clean_name(m.group(1))
        if name:
            add(m, name)

    for m in re.finditer(r"叫我(" + NAME_CHARS + r")", text):
        name = _clean_name(m.group(1))
        if name:
            add(m, name)

    for m in re.finditer(r"(?:我的)?名字(?:是|叫)(" + NAME_CHARS + r")", text):
        name = _clean_name(m.group(1))
        if name:
            add(m, name)

    for m in re.finditer(
        r"(?:我的)?(" + "|".join(RELATIONS) + r")(?:叫|是|名字叫)(" + NAME_CHARS + r")", text
    ):
        role, name = m.group(1), _clean_name(m.group(2))
        if name and name != role:
            out.append(Mention("person", name, m.group(0), sent_idx,
                               offset + m.start(), offset + m.end(),
                               {"role": role}))

    # 别名表中的已知人物：直接做子串匹配
    for alias, canonical in sorted(known_people.items(), key=lambda kv: -len(kv[0])):
        if not alias or len(alias) < 2:
            continue
        for m in re.finditer(re.escape(alias), text):
            out.append(Mention("person", canonical, m.group(0), sent_idx,
                               offset + m.start(), offset + m.end(),
                               {"alias": alias}))

    # 去重（同一位置只保留一个）
    seen: set[tuple[int, int, str]] = set()
    uniq: list[Mention] = []
    for mm in out:
        key = (mm.start, mm.end, mm.value)
        if key not in seen:
            seen.add(key)
            uniq.append(mm)
    return uniq


def _place_mentions(text: str, sent_idx: int, offset: int) -> list[Mention]:
    out: list[Mention] = []
    patterns = [
        r"我(?:住在|住|老家在|来自)([^\s，。！？,.!?；;]{2,12})",
        r"我(?:在|去|到)([^\s，。！？,.!?；;]{2,10}?)(?:上班|工作|读书|上学|玩|住|出差)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            place = _clean_name(m.group(1))
            if len(place) < 2 or place in ("家", "这里", "那里", "公司", "学校"):
                continue
            out.append(Mention("place", place, m.group(0), sent_idx,
                               offset + m.start(), offset + m.end()))
    # 已知城市后缀（X市 / X省）只收 2-4 字 + 后缀，避免「市场」类误报
    for m in re.finditer(r"([\u4e00-\u9fff]{2,4})(市|省|区|县)(?=[，。！？\s]|$)", text):
        name = m.group(1) + m.group(2)
        if m.group(1) in ("城", "超", "夜", "上", "下", "门"):
            continue
        out.append(Mention("place", name, m.group(0), sent_idx,
                           offset + m.start(), offset + m.end()))
    return out


def emotion_score(text: str) -> float:
    score = 0.0
    hits = 0
    for word, w in EMOTION_STRONG.items():
        if word in text:
            score = max(score, w)
            hits += 1
    if hits >= 2:
        score = min(1.0, score + 0.08)
    if any(x in text for x in INTENSIFIERS) and score > 0:
        score = min(1.0, score + 0.08)
    if re.search(r"[!！]{2,}", text):
        score = min(1.0, score + 0.06)
    elif re.search(r"[!！]", text) and score > 0:
        score = min(1.0, score + 0.03)
    if re.search(r"(不|没)(开心|高兴|难过|生气|在乎)", text):
        score = max(score, 0.45)
    return round(score, 3)


def extract_topics(text: str, limit: int = 4) -> list[str]:
    counts: dict[str, int] = {}
    for t in tokenize(text):
        if len(t) < 2:
            continue
        counts[t] = counts.get(t, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    return [t for t, _ in ranked[:limit]]


CORRECTION_RE = re.compile(r"(不是|其实|说错|更正|搞错|记错|纠正|准确地说|应该是|改成)")


def extract(text: str, *, base: datetime | None = None,
            known_people: dict[str, str] | None = None) -> Extraction:
    text = normalize(text)
    base = base or now()
    known_people = known_people or {}
    mentions: list[Mention] = []
    for idx, start, _end, sent in split_sentences(text):
        mentions.extend(_time_mentions(sent, base, idx, start))
        mentions.extend(_person_mentions(sent, idx, start, known_people))
        mentions.extend(_place_mentions(sent, idx, start))
        for m in re.finditer("|".join(map(re.escape, EVENT_WORDS)), sent):
            mentions.append(Mention("event", m.group(0), m.group(0), idx,
                                    start + m.start(), start + m.end()))
    # 去重（同一位置只保留一个；不同位置保留，供 span 索引）
    dedup: dict[tuple[str, str, int, int], Mention] = {}
    for mm in mentions:
        dedup.setdefault((mm.type, mm.value, mm.start, mm.end), mm)
    return Extraction(
        mentions=list(dedup.values()),
        emotion=emotion_score(text),
        topics=extract_topics(text),
        correction=bool(CORRECTION_RE.search(text)),
    )