# -*- coding: utf-8 -*-
"""M4 -- "what is worth remembering": the frozen K/D/U rule engine.

Criteria: kvmem/m2_visibility/mine/inspector/M4-CRITERIA.md (frozen 2026-10-25).
Direction: 宁多记不漏记 (recall 1.0 on K1/K3/K4/K5). This is deliberately the OPPOSITE of M5's
漏判优先; the two must never be "unified".

Every sentence gets an output. undecidable is never silently dropped.
"""
from __future__ import annotations

import datetime as dt
import re

# §6 closed attribute vocabulary. Adding a word here is a criteria revision, not a code change.
VOCAB = (
    "住址 出生地 生日 年龄 姓名 小名 称呼 职业 单位 家庭成员 宠物 车牌 车型 电话 邮箱 账号 设备 "
    "饮食偏好 饮品偏好 忌口 作息 通勤 常去地点 健康 过敏 长期约束 提醒规则 计划 承诺 目标 语言偏好"
).split()

SENT_END = "。！？!?\n"
QUESTION = re.compile(r"(吗|呢|什么时候|哪天|几月|几号|多少|什么|哪里|哪儿|怎么|为什么|是否|有没有)")
GREETING = re.compile(r"^(你好|您好|嗨|hi|hello|在吗|早上好|晚上好|晚安|再见|拜拜|谢谢|多谢|麻烦了)")
PROCEDURAL = re.compile(r"^(嗯|好的|好|收到|明白|稍等|我看看|知道了)[。！!.~ ]*$")
OPS = re.compile(r"(打开|翻译|总结|查一下|查下|帮我查|帮我搜|搜索|列出|计算|写一份|重写)")
REQUEST = re.compile(r"(帮我|请|麻烦|能不能|可以帮我)")
CHITCHAT = re.compile(r"(天气|新闻|股价|热搜|今天好热|今天好冷|下雨了)")
EMOTION = re.compile(r"(我好累|累死了|烦死了|好烦|郁闷|开心|难过|气死|无语)")
LONGTERM = re.compile(r"(长期|一直|总是|每次|每天都|常年)")
CONDITIONAL = re.compile(r"(如果|假如|要是|万一|假设)")
PRONOUN_BARE = re.compile(r"(那个东西|那个人|它|他|她|老地方)")
NEG_NO_OBJ = re.compile(r"(不喜欢|不爱|不要|不接受|受不了)\s*(那个|这个|那样|这样|那种)?[。！!]?$")
JOKE = re.compile(r"(哈哈|开玩笑|逗你|笑死)")

REL_TIME = re.compile(r"(明天|后天|大后天|下周[一二三四五六日天]|下个?月|月底|今晚|明早|"
                      r"三天后|\d+\s*天后|每年|每个?周[一二三四五六日天]|每[天周月])")
WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

CONFIRM = re.compile(r"^(对|是的|没错|就是这样|对的|嗯对|正确)[，,。！! ]*$")


def split_sentences(text):
    """Chinese sentence boundaries 。！？ plus newlines. Punctuation stays on its sentence."""
    out, buf = [], ""
    for ch in text:
        buf += ch
        if ch in SENT_END:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def normalize_record(conv):
    """conversation -> flat sentence list, keeping the turn each sentence came from.

    The output unit is the SENTENCE (§1), but the frozen §11 table counts TURNS, so the turn
    index is kept for a faithful comparison.
    """
    recs = []
    n = 0
    for ti, turn in enumerate(conv, start=1):
        for s in split_sentences(turn.get("text", "")):
            n += 1
            recs.append({"sent_id": n, "turn": ti, "role": turn.get("role", "user"),
                         "text": s, "ts": turn.get("ts")})
    return recs


# --------------------------------------------------------------- time anchoring
def anchor(phrase, ts_iso):
    """§7: relative time -> absolute date. No ts -> None (the caller must call it undecidable).

    Frozen week rule: a week starts on its Monday. "下周X" = next week's Monday + X.
    ts=2026-10-25 (Sunday) + "下周三" => 2026-10-28.
    """
    if not ts_iso:
        return None
    base = dt.datetime.fromisoformat(ts_iso) if "T" in ts_iso else dt.datetime.combine(
        dt.date.fromisoformat(ts_iso), dt.time())
    d = base.date()
    if phrase.startswith("明天"):
        return (d + dt.timedelta(days=1)).isoformat()
    if phrase.startswith("后天") and not phrase.startswith("大后天"):
        return (d + dt.timedelta(days=2)).isoformat()
    if phrase.startswith("大后天"):
        return (d + dt.timedelta(days=3)).isoformat()
    if phrase.startswith("今晚") or phrase.startswith("明早"):
        return (d if phrase.startswith("今晚") else d + dt.timedelta(days=1)).isoformat()
    m = re.match(r"下周([一二三四五六日天])", phrase)
    if m:
        monday = d - dt.timedelta(days=d.weekday())          # this week's Monday
        return (monday + dt.timedelta(days=7 + WEEKDAY[m.group(1)])).isoformat()
    m = re.match(r"三天后|(\d+)\s*天后", phrase)
    if m:
        return (d + dt.timedelta(days=int(m.group(1) or 3))).isoformat()
    if phrase.startswith("下个月") or phrase.startswith("下月"):
        return (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1).isoformat()
    if phrase.startswith("月底"):
        nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        return (nxt - dt.timedelta(days=1)).isoformat()
    return None


def is_recurrence(phrase):
    return bool(re.match(r"(每年|每个?周[一二三四五六日天]|每[天周月])", phrase))


# --------------------------------------------------------------- fact patterns
# (name, attr, regex over the sentence, verbatim value group)
FACT_RULES = [
    ("residence", "住址", re.compile(r"我(?:住在|住在|住|家住在|搬到|搬到了|家的地址是|的地址是)\s*"
                                     r"([^，,。！？]{2,30}?)(?:[，,。！？]|$)")),
    ("plate", "车牌", re.compile(r"我(?:的)?车牌(?:号|号码)?(?:是|为|[:：])?\s*"
                                r"([京津冀晋蒙辽吉黑沪苏浙皖闽赣鲁豫鄂湘粤桂琼渝川贵云藏陕甘青宁新]"
                                r"[A-Z][-·]?[0-9A-Z]{4,6})")),
    ("name", "姓名", re.compile(r"我(?:的名字)?叫\s*([\u4e00-\u9fa5]{2,4})(?:[，,。！？]|$)")),
    ("nickname", "小名", re.compile(r"我(?:的)?小名叫?\s*([\u4e00-\u9fa5]{2,4})(?:[，,。！？]|$)")),
    ("job", "职业", re.compile(r"我是(?:一名|一个|个)?\s*([\u4e00-\u9fa5]{2,10}?"
                              r"(?:工程师|医生|老师|设计师|产品经理|程序员|律师|会计|司机|护士))")),
    ("employer", "单位", re.compile(r"我在\s*([\u4e00-\u9fa5A-Za-z0-9]{2,12}?)\s*(?:上班|工作|实习)")),
    ("pet", "宠物", re.compile(r"我(?:家)?养了?(?:一只|一个|条)?\s*([\u4e00-\u9fa5A-Za-z0-9]{1,10})")),
    ("birthday", "生日", re.compile(r"我(?:的)?生日是\s*([0-9一二三四五六七八九十]{1,2}\s*月\s*"
                                    r"[0-9一二三四五六七八九十]{1,3}\s*[日号])")),
]
FAMILY = re.compile(r"(我)?(女儿|儿子|妻子|老婆|丈夫|老公|爸爸|妈妈|父亲|母亲|孩子|妹妹|弟弟|哥哥|姐姐)"
                    r"[^，,。！？]{0,12}")
PLAN = re.compile(r"(提醒我|打算|计划|准备|约定|约好|别忘了)\s*([^，,。！？]{1,40})")
CONSTRAINT = re.compile(r"(别|不要|以后都|请记住|不要再|总是)\s*([^，,。！？]{2,40}?)"
                        r"(?:[，,。！？]|$)")
PREFER = re.compile(r"(喜欢|爱|讨厌|只喝|只吃|只抽|习惯|受不了|更喜欢|一般选)\s*"
                    r"([^，,。！？]{1,20})")
AVOID = re.compile(r"(不吃|忌口|不碰|过敏)\s*([^，,。！？]{1,20})")
SCHEDULE = re.compile(r"我\s*([每][天周月][^，,。！？]{2,30}?(?:出门|起床|睡觉|上班|下班|吃饭|跑步))")
HEALTH = re.compile(r"(长期|一直|总是|常年|每天晚上)?\s*"
                    r"(失眠|头痛|头疼|胃病|过敏|颈椎|腰疼|焦虑|鼻炎|高血压|糖尿病)")


def _mk(attr, value, span, confidence=0.9, **kw):
    m = {"subject": "用户", "attr": attr, "value": value, "type": None,
         "evidence_span": span, "anchored_time": None, "confidence": confidence}
    m.update(kw)
    return m


def _verbatim(value, text):
    return value in text


# --------------------------------------------------------------- the judge
def judge(sentence, role, ts, prev_assistant=None):
    """One sentence -> {verdict, code, reason, memories[]}. Never silently drops."""
    t = sentence["text"] if isinstance(sentence, dict) else sentence
    out = {"verdict": "drop", "code": None, "reason": "", "memories": []}

    if role == "assistant":
        out.update(code="D4", reason="assistant 发言默认不记（判据 D4）")
        return out

    # user confirmation of an assistant-provided fact -> the only D4 exception
    if prev_assistant and CONFIRM.match(t):
        facts = _assistant_facts(prev_assistant)
        if facts:
            out.update(verdict="keep", code="K1",
                       reason="用户明确确认 assistant 上一句给出的事实（D4 唯一例外）",
                       memories=[dict(_mk(f["attr"], f["value"], f["value"], 0.6),
                                      derived_from="assistant") for f in facts])
            return out

    question = bool(QUESTION.search(t)) or t.endswith("？") or t.endswith("?")
    greeting = bool(GREETING.match(t))
    procedural = bool(PROCEDURAL.match(t))
    ops = bool(OPS.search(t))
    chitchat = bool(CHITCHAT.search(t))
    emotion = bool(EMOTION.search(t))
    longterm = bool(LONGTERM.search(t))
    conditional = bool(CONDITIONAL.search(t))
    joke = bool(JOKE.search(t))

    # order matters: the frozen expectations put U2 above D3 ("如果我搬到杭州，你会记得吗？")
    if conditional and not _has_assertion(t):
        out.update(verdict="undecidable", code="U2",
                   reason="条件句/假设，不是既成事实（判据 U2）")
        return out
    if NEG_NO_OBJ.search(t):                    # §11: "我不喜欢那个" must be U4, not K2
        out.update(verdict="undecidable", code="U4",
                   reason="否定/偏好但对象缺失，不许猜（判据 U4）")
        return out
    if ops and REQUEST.search(t):
        out.update(code="D3+D6", reason="纯索取 + 一次性操作指令，都不记（判据 D3+D6）")
        return out
    if question:
        code = "D3+D6" if ops else "D3"
        out.update(code=code, reason="问句/纯索取本身不记，句内实体也不记（判据 D3%s）"
                   % ("+D6" if ops else ""))
        return out
    if greeting:
        out.update(code="D1", reason="寒暄客套，无持久信息（判据 D1）")
        return out
    if procedural:
        out.update(code="D2", reason="过程性应答，无新信息（判据 D2）")
        return out
    if ops:
        out.update(code="D6", reason="一次性操作指令（判据 D6）")
        return out
    if chitchat:
        out.update(code="D5", reason="时效性闲聊，无持久面（判据 D5）")
        return out
    if emotion and not longterm:
        out.update(code="D7", reason="纯情绪表达（判据 D7）")
        return out
    if joke and not _attr_from_text(t):
        out.update(verdict="undecidable", code="U5",
                   reason="玩笑/反讽标记且无事实可对齐（判据 U5）")
        return out
    if PRONOUN_BARE.search(t) and not _attr_from_text(t):
        out.update(verdict="undecidable", code="U1",
                   reason="指代无锚（判据 U1）")
        return out

    mems, codes, unknown_attr = _extract(t, ts)
    if unknown_attr:
        out.update(verdict="undecidable", code="U-attr",
                   reason="判据 §6 词表外的新属性 %r：不许自建属性名，进待审清单" % unknown_attr)
        return out
    if not mems:
        out.update(code="D5", reason="无 K1–K6 触发点，无持久信息")
        return out
    out.update(verdict="keep", code="+".join(dict.fromkeys(codes)), memories=mems,
               reason="命中 %s" % "+".join(dict.fromkeys(codes)))
    return out


def _has_assertion(t):
    return bool(re.search(r"(已经|已|确实|现在|真的)", t))


def _attr_from_text(t):
    for _n, attr, rx in FACT_RULES:
        if rx.search(t):
            return attr
    if FAMILY.search(t):
        return "家庭成员"
    if re.search(r"(不吃|忌口|不碰|过敏)", t):
        return "忌口"
    if PREFER.search(t):
        return "饮食偏好"
    if CONSTRAINT.search(t):
        return "提醒规则"
    if PLAN.search(t):
        return "计划"
    return None


def _assistant_facts(text):
    """Facts an assistant stated that a user may confirm. Only verbatim, closed-vocab facts."""
    facts = []
    for _n, attr, rx in FACT_RULES:
        m = rx.search(text)
        if m:
            facts.append({"attr": attr, "value": m.group(1).strip()})
    return facts


def _extract(t, ts):
    """Return (memories, codes, unknown_attr). Values are VERBATIM slices of the sentence (§9)."""
    mems, codes, unknown = [], [], None

    def add(attr, value, code, **kw):
        nonlocal unknown
        if attr not in VOCAB:
            unknown = attr
            return
        value = value.strip(" ，,。！？")
        if not value or not _verbatim(value, t):
            return                                              # §9: value must appear verbatim
        mems.append(_mk(attr, value, t, **kw))
        codes.append(code)

    for _name, attr, rx in FACT_RULES:
        for m in rx.finditer(t):
            add(attr, m.group(1), "K1")

    m = SCHEDULE.search(t)
    if m:
        add("作息", m.group(1), "K1")

    m = FAMILY.search(t)
    if m:
        add("家庭成员", m.group(0).lstrip("我"), "K4")

    if LONGTERM.search(t) or re.search(r"(失眠|头痛|头疼|胃病|过敏|颈椎|腰疼|焦虑|鼻炎)", t):
        mh = HEALTH.search(t)
        if mh:
            add("健康", mh.group(0).strip(), "K1")

    if re.search(r"(不吃|忌口|不碰|过敏|只喝|只吃|喜欢|讨厌|受不了|习惯)", t):
        for mm in AVOID.finditer(t):
            add("忌口", mm.group(2), "K2")
        for mm in PREFER.finditer(t):
            attr = "饮品偏好" if re.search(r"(喝|咖啡|茶|酒|奶)", t) else "饮食偏好"
            add(attr, mm.group(2), "K2")

    for mm in CONSTRAINT.finditer(t):
        add("提醒规则", mm.group(0), "K5")

    if re.search(r"(提醒我|打算|计划|约定|别忘记|别忘了)", t):
        mrel = REL_TIME.search(t)
        for mm in PLAN.finditer(t):
            if mrel:
                if is_recurrence(mrel.group(1)):
                    add("计划", mm.group(0), "K3", recurrence=mrel.group(1))
                elif ts:
                    when = anchor(mrel.group(1), ts)
                    if when:
                        add("计划", mm.group(0), "K3", anchored_time=when)
                    else:
                        return mems, codes, unknown
                else:
                    # §7: no ts, relative time cannot be anchored -> undecidable, not stored
                    return [], [], "U3:" + mrel.group(1)
            else:
                add("计划", mm.group(0), "K3")

    if re.search(r"(记住|记一下|存一下|别忘了)", t):
        codes.append("K6")

    # anchoring applies to every memory whose sentence carries a relative time
    mrel = REL_TIME.search(t)
    if mrel and mems and not is_recurrence(mrel.group(1)):
        if not ts:
            return [], [], "U3:" + mrel.group(1)
        when = anchor(mrel.group(1), ts)
        for mm in mems:                        # only planning-type facts inherit the date
            if mm.get("anchored_time") is None and when and mm["attr"] in (
                    "计划", "承诺", "提醒规则", "长期约束", "作息"):
                mm["anchored_time"] = when
    return mems, codes, unknown


def run(conv):
    """Whole conversation -> per-sentence records (§1 output contract)."""
    recs = normalize_record(conv)
    out, prev_assistant = [], None
    for r in recs:
        j = judge(r, r["role"], r["ts"], prev_assistant)
        out.append(dict(sent_id=r["sent_id"], turn=r["turn"], role=r["role"], text=r["text"],
                        verdict=j["verdict"], code=j["code"], reason=j["reason"],
                        memories=j["memories"]))
        prev_assistant = r["text"] if r["role"] == "assistant" else prev_assistant
    return out
