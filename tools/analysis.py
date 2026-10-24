# -*- coding: utf-8 -*-
"""analysis.py -- M1.5: one analysis chain for the index and for queries.

Two structural gaps this closes:

  1. "我几点睡觉" vs a block that says "12点半 睡". No bigram matches, so lexical search
     returns nothing. The fix is not a bigger tokenizer: 几点 does not *mean* 12点半, it
     ASKS FOR a time. So a query carries an answer type, and a block either supplies that
     kind of value or it does not.
  2. "我每个月工资多少" vs a block that says "15号 发工资". Topically identical, and the
     amount is simply not recorded. A value-kind gate makes that block inadmissible
     instead of letting term overlap decide.

So the same two notions serve both: `answer_type(query)` and `value_kinds(text)`.
Everything here is pure, deterministic and rebuildable -- no third-party tokenizer state,
because the index has to be reconstructable from memory_source alone.

ANALYSIS_VERSION is part of the index identity: change it, the index is rebuilt.
"""
import re
import unicodedata

ANALYSIS_VERSION = 4

# ------------------------------------------------------------------ normalisation

CN_NUM = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_int(s):
    """十二 -> 12, 三 -> 3, 二十 -> 20, 二十三 -> 23. Small on purpose: dates/times only."""
    if not s:
        return None
    if "十" not in s:
        if len(s) == 1 and s in CN_NUM:
            return CN_NUM[s]
        return None
    head, _, tail = s.partition("十")
    tens = CN_NUM.get(head, 1) if head else 1
    ones = CN_NUM.get(tail, 0) if tail else 0
    return tens * 10 + ones


_CN_TIME = re.compile(r"(?<![有差])([零一二两三四五六七八九十]{1,3})\s*点\s*([零一二三四五六七八九十]{1,3})?"
                      r"(半|一刻)?")
_CN_DATE = re.compile(r"([一二三四五六七八九十]{1,3})\s*月"
                      r"(?:\s*([一二三四五六七八九十]{1,3})\s*[日号]?)?")


def _cn_date_sub(m):
    """"三月十四" -> 3月14日, "三月" -> 3月, but "三个月" is a duration and stays put."""
    if m.string[m.end():m.end() + 1] == "个":
        return m.group(0)
    mon = _cn_int(m.group(1)) or 0
    if m.group(2):
        return "%d月%d日" % (mon, _cn_int(m.group(2)) or 1)
    return "%d月" % mon


def normalize(text):
    """Full-width -> half-width, Chinese numerals in times/dates -> arabic, CJK spacing
    collapsed. Collapsing spaces matters: "12点半 睡" and "12点半睡" are one phrase."""
    t = unicodedata.normalize("NFKC", text or "")
    t = _CN_DATE.sub(_cn_date_sub, t)
    t = _CN_TIME.sub(lambda m: "%d点%s%s" % (_cn_int(m.group(1)) or 0,
                                             _cn_int(m.group(2)) or "",
                                             m.group(3) or ""), t)
    t = re.sub(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])", "", t)
    return t.replace("：", ":").strip()


# ------------------------------------------------------------------ value kinds
# A block "supplies" a kind of value. A question "asks for" one.
ID_NOUNS = ("卡号", "编号", "工号", "学号", "电话", "手机号", "身份证", "车牌", "护照",
            "门牌", "保单号", "订单号", "邮编", "账号", "车位号", "型号", "序列号")

MONEY_NOUNS = ("房租", "房贷", "工资", "月薪", "薪水", "收入", "奖金", "项目奖", "报销",
               "保额", "保费", "学费", "年卡", "价格", "花费", "余额", "存款", "首付",
               "车价", "单价", "费用", "押金", "营业额", "预算", "成本")

_NUM = r"(?:\d+(?:\.\d+)?|[一二三四五六七八九十百千万两]+)"

# An amount, in the shapes people actually write it.
_MONEY_VALUE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:元|块)"
    r"|\d+(?:\.\d+)?\s*[kK](?![a-zA-Z])"
    r"|\d+\s*万(?:\s*\d)?(?=\s*(?:\d|[，,。.;；元块]|$))"
    r"|\d+(?:\.\d+)?\s*/\s*(?:月|年|天)"
    r"|[一二三四五六七八九十百千万两]+\s*(?:元|块)"
    r"|[\u00a5\uffe5]\s*\d+")


def _near(text, start, end, nouns, window=6):
    return any(n in text[max(0, start - window):end + window] for n in nouns)


def money_spans(text):
    """Where the text states an amount.

    Two ways to qualify: an explicit currency form (4800元, 28k, 1万5, 5200/月), or a bare
    number inside a money context ("房租 5200 一个月"). The second is what real records look
    like, and requiring a currency unit there is how "房贷 9100" became "no amount recorded".

    Identifier context wins over money context: "工资卡号 6222..." is a card, not a salary.
    """
    t = normalize(text)
    spans = [(m.start(), m.end()) for m in _MONEY_VALUE.finditer(t)]
    for m in re.finditer(_NUM, t):
        if any(a <= m.start() < b for a, b in spans):
            continue
        if re.match(r"(?:号|日|点|岁|层|楼|人|次|周|天|页|米)", t[m.end():]):
            continue            # 15号 / 3层 / 7人: a date or a count, not an amount
        if not _near(t, m.start(), m.end(), MONEY_NOUNS):
            continue
        if _near(t, m.start(), m.end(), ID_NOUNS, window=4):
            continue
        spans.append((m.start(), m.end()))
    return spans


COLORS = ("白", "黑", "灰", "银", "红", "蓝", "绿", "黄", "橙", "棕", "紫", "金")

# ONE table. A property is what a question can ask for; scope is the entity the value must
# hang off. Scope is only set where a block could plausibly state the same kind of value
# about something else -- colour most of all, since "白色的朗逸" is a car colour, not a
# plate colour.
PROPERTIES = [
    # name, question words, value pattern, scope nouns (None = value pattern is specific
    # enough on its own), the kind the value belongs to
    ("color", ("颜色",), r"白|黑|灰|银|红|蓝|绿|黄|橙|棕|紫|金", (), None),
    # a limit is a number stated about 额度; a card number alone is not a credit limit
    ("limit", ("额度",), r"\d+(?:\.\d+)?\s*(?:元|块|万)?", ("额度",), "money"),
    ("fuel", ("油耗",), r"\d+(?:\.\d+)?\s*[lL]\s*/\s*100\s*k[mM]|每百公里\s*\d+\s*升",
     ("车",), None),
    ("displacement", ("排量",), r"\d(?:\.\d)?\s*[lLtT](?![a-zA-Z])|\d{3,4}\s*(?:cc|毫升)",
     None, None),
    ("area", ("面积", "多大平"), r"\d+(?:\.\d+)?\s*(?:平|平米|平方米|㎡)", None, None),
    ("height", ("身高",), r"\d{2,3}\s*(?:cm|厘米)|1[.．]\d{2}\s*米", None, None),
    ("birthday", ("生日",), r"\d{1,2}\s*月\s*\d{1,2}|\d{4}\s*[-/年]\s*\d{1,2}", None, None),
    ("blood_pressure", ("血压",), r"\d{2,3}\s*/\s*\d{2,3}|\d{2,3}\s*mmHg", None, None),
    ("plate", ("车牌",), r"[\u4e00-\u9fa5][A-Za-z][-\s]?[A-Za-z0-9]{4,6}", None, None),
    ("card_number", ("卡号",), r"\d(?:[ \-]?\d){11,18}", None, None),
    ("phone", ("电话", "手机号"), r"1[3-9]\d(?:[ \-]?\d){8}", ("手机", "电话"), None),
    ("member_id", ("工号",), r"[A-Za-z]{0,2}[-\s]?\d{2,6}", ("工号",), None),
    ("desk_id", ("工位号", "工位编号"),
     r"[A-Za-z]{1,2}[-\s]\d{1,5}|\d{1,5}\s*号", ("工位",), None),
    ("spot_id", ("车位号", "车位编号"),
     r"[A-Za-z]{1,2}[-\s]\d{1,5}|\d{1,5}\s*号", ("车位",), None),
    ("address", ("住哪", "住在哪", "住址", "地址"),
     r"(?:路|街|号|楼|室|新村|小区|里|栋|园)", None, None),
]

PROP_NAMES = frozenset(pn for pn, _w, _v, _sc, _k in PROPERTIES)


def _prop_value(text, pat):
    if pat is None:
        return [m.start() for m in re.finditer("|".join(COLORS), text)]
    return [m.start() for m in re.finditer(pat, text)]


def property_of(query):
    """Which property the question asks for. Property words only: the entity is the scope,
    not the question. Returns None when the question names no property."""
    q = normalize(query)
    for name, words, _v, sc, _k in PROPERTIES:
        if any(w in q for w in words):
            if sc and not any(n in q for n in sc):
                # a bare "额度" still asks for a limit; scope only sharpens the container
                return name
            return name
    return None


def scope_of(query, prop=None):
    """The entity the question ties the property to, e.g. 车牌 in 我的车牌颜色."""
    q = normalize(query)
    for name, _w, _v, sc, _k in PROPERTIES:
        if prop and name != prop:
            continue
        if sc:
            for n in sc:
                if n in q:
                    return n
    return None


def property_holds(text, prop, scope=None):
    """Does this text state `prop` about `scope`?

    The anchor is the scope the question named, or the property's own word. The record's
    other synonyms for the scope are only a fallback, so "车牌颜色" is not satisfied by
    "车是白色的" -- 白色 hangs off the car, not the plate.
    """
    t = normalize(text)
    spec = next((x for x in PROPERTIES if x[0] == prop), None)
    if spec is None:
        return False
    _n, words, pat, scs, _k = spec
    pos = _prop_value(t, pat)
    if not pos:
        return False
    anchors = ([scope] if scope else []) + list(words)
    anchors = [a for a in anchors if a and a in t]
    if not anchors and scs:
        anchors = [n for n in scs if n in t]
    if not anchors:
        return not scs and not scope
    hits = [m.start() for a in anchors for m in re.finditer(re.escape(a), t)]
    return any(abs(v - h) <= 5 for v in pos for h in hits)


def properties_of(text):
    """Which properties this block states a value for, honouring the scope when one is set.

    "车是白色的 朗逸，车牌 苏E-6K21M" states the *car's* colour. It does not state the
    plate's colour, and with scope=车牌 this returns no colour at all.
    """
    t = normalize(text)
    out = set()
    for name, _w, pat, sc, kind in PROPERTIES:
        pos = _prop_value(t, pat)
        if not pos:
            continue
        if sc is None:
            out.add(name)
            continue
        scope_hits = [m.start() for n in sc for m in re.finditer(re.escape(n), t)]
        if not scope_hits:
            continue
        if any(abs(v - h) <= 10 for v in pos for h in scope_hits):
            out.add(name)
    return out


def _legacy_attributes_of(text):

    """Which attributes this text actually supplies (noun + a value, not the noun alone)."""
    t = normalize(text)
    spans = money_spans(t)
    out = set()
    for attr, nouns, vpat, kind in ATTRS:
        if not any(n in t for n in nouns):
            continue
        if vpat:
            if re.search(vpat, t):
                out.add(attr)
        elif kind == "money":
            if any(_near(t, a, b, nouns) for a, b in spans):
                out.add(attr)
    return out


VALUE_ASK = re.compile(r"多少|几|多大|多长|多高|多重")


def _legacy_attribute_of(query):
    """Which attribute a question asks for a VALUE of, if any.

    The VALUE_ASK requirement is what keeps "房贷是哪家银行" out of the money gate: it names
    the loan but asks for a bank, and gating it on "has an amount" would reject the block
    that answers it.
    """
    q = normalize(query)
    if not VALUE_ASK.search(q):
        return None
    for attr, nouns, _v, kind in ATTRS:
        if any(n in q for n in nouns):
            return attr
    return None


VALUES = [
    # Chinese numerals count only when a currency unit follows: "五千元" is money,
    # "一万步" is a step count. Everything here is a claim, so it stays narrow.
    # Chinese numerals require 元/块: "五千元" is money, "一万步" and "一万二千米" are not,
    # because 万/千 inside the numeral class can otherwise be consumed as the unit itself.
    ("time_of_day", re.compile(r"\b\d{1,2}\s*:\s*\d{2}|\d{1,2}\s*点(?:\s*\d{1,2}\s*分|半|一刻)?|"
                               r"早上|上午|中午|下午|晚上|凌晨")),
    ("duration", re.compile(r"(?:\d+(?:\.\d+)?|[一二三四五六七八九十两]+)\s*"
                            r"(?:分钟|小时|天|周|个月|年|岁|页|站)")),
    # 15号 / 3月14 / 3月14日 / 下个月 / 月底. "2号线" is a metro line, not a date.
    ("date", re.compile(r"\d{1,2}\s*月(?!\s*个)\s*\d{0,2}|\d{1,2}\s*[日号](?!\s*线)|"
                        r"\d{4}\s*[-/年]\s*\d{1,2}|(?:周|星期)[一二三四五六日天]|"
                        r"下个?月|本月|月底|月初|年底|下月")),
    ("count", re.compile(r"(?:\d+|[一二三四五六七八九十两]+)\s*(?:个|人|次|层|号|件|台|条|位)")),
    ("name", re.compile(r"\u300a[^\u300b]{1,20}\u300b|叫\s*[\u4e00-\u9fa5]{1,4}")),
    # Structural only. A bare "在 X" is not a location: "我在做蓝鲸项目" is a project,
    # "在供应链分析组工作" is an org. Without a gazetteer, a loose pattern here buys
    # false positives that then leak through the value gate.
    ("location", re.compile(r"[\u4e00-\u9fa5]{1,6}(?:市|省|区|路|街|里|栋|楼|层|室|园|机场|车站|酒店)|"
                            r"[\u4e00-\u9fa5]{1,6}会议室")),
]

# A bounded gazetteer, because "去上海出差" has no structural suffix. Explicitly a list,
# not an inference: an unknown city simply does not match, and location is never gated.
CITIES = frozenset("""
北京 上海 广州 深圳 杭州 南京 苏州 成都 重庆 武汉 西安 天津 青岛 长沙 郑州 合肥
福州 厦门 济南 沈阳 大连 哈尔滨 昆明 贵阳 南宁 海口 兰州 西宁 银川 乌鲁木齐 拉萨
太原 石家庄 南昌 长春 洛阳 无锡 宁波 温州 佛山 东莞 珠海 三亚 桂林 大理 丽江 咸阳
宝鸡 开封 常州 徐州 烟台 潍坊 唐山 保定 秦皇岛 包头 鄂尔多斯 株洲 湘潭 惠州 中山
""".split())

# Only these kinds are trustworthy enough to GATE on. location and name are ranking
# signals: their detectors are the least reliable, and a wrong gate either drops the right
# block or admits a wrong one. Gate what you can prove.
GATED = frozenset({"money", "time_of_day", "date", "count", "duration"})

# What the question asks for. Order matters: the first match wins.
ASKS = [
    # money: "工资/房租/房贷... 多少" as well as "多少钱". Missing the noun+多少 form is
    # how "我工资是多少" slipped through as no-answer-type and then matched 工资卡.
    ("money", re.compile(r"多少钱|价格|花费|花了|余额|费用多少|"
                         r"(?:工资|薪水|月薪|收入|奖金|房租|房贷|报销|费用)[^，。？！?]{0,6}"
                         r"(?:多少|几|是多|大概)")),
    ("time_of_day", re.compile(r"几点|什么时间|几点钟|"
                               r"什么时候(?:上班|下班|开会|吃饭|起床|睡觉|睡|出门|开始|结束)")),
    ("duration", re.compile(r"多久|多长时间|几个小时|几天|几年")),
    ("date", re.compile(r"(?:什么时候|哪天|几号|几月|何时)[^，。？！?]{0,6}"
                        r"(?:上线|截止|到期|交付|发布|发工资)|"
                        r"(?:上线|截止|到期|生日)[^，。？！?]{0,2}(?:时间|日期)|"
                        # 生日: a regression from the previous table, which had a bare 生日
                        r"生日[^，。？！?]{0,4}(?:是什么时候|是哪天|哪一天|几号|几月)|"
                        r"日期|哪年")),
    ("count", re.compile(r"几个人|多少人|几次|几层|几页|几个|多少位")),
    ("location", re.compile(r"在哪|哪里|哪儿|哪个城市|哪个会议室|哪个楼|住哪|去哪|去哪个")),
    ("name", re.compile(r"叫什么|什么名字|谁负责|负责人是谁|是谁|叫什么名字")),
]

def answer_type(query):
    """The kind of value the question expects, or None when it does not expect one.

    "多少" alone is deliberately None: "我的车牌号是多少" asks for an identifier, not an
    amount, and treating it as a number request is how a ranker starts guessing.

    KNOWN LIMITATION: returns the FIRST matching kind, so a query that asks two things
    ("什么时候发工资，多少钱") is classified by whichever test comes first in ASKS. It is
    recorded as a limitation rather than papered over: the per-clause splitter usually
    separates such questions before they reach here, and a wrong kind now only affects
    ranking for location/name, or gating for the five gated kinds.
    """
    q = normalize(query)
    for kind, rx in ASKS:
        if rx.search(q):
            return kind
    return None




def value_kinds(text):
    """Which kinds of value a block actually supplies."""
    t = normalize(text)
    out = {kind for kind, rx in VALUES if rx.search(t)}
    if money_spans(t):
        out.add("money")
    if any(c in t for c in CITIES):
        out.add("location")
    return out


# ------------------------------------------------------------------ analysis chain
_BIGRAM = re.compile(r"[\u3400-\u9fff]+")
_LATIN = re.compile(r"[a-z]+")


def terms(text):
    """CJK bigrams + latin runs + CJK unigrams (prefixed 'u:').

    Unigrams exist because Chinese is written without spaces: "睡觉" and a block that
    says "睡" share no bigram, yet they are the same topic. Unigrams are weak evidence
    and are only ever used as a fallback, gated by the answer type.
    """
    t = normalize(text).lower()
    out = []
    for run in _BIGRAM.findall(t):
        if len(run) == 1:
            out.append(run)
        else:
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
        out.extend("u:" + c for c in run)
    out.extend(_LATIN.findall(t))
    return out