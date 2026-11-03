# -*- coding: utf-8 -*-
"""答案-问题对齐（纯离线、零模型、不改写答案）。

三级漏斗：主体 -> 谓词/槽位 -> 数字/值存在性；仅在完全抽不出 asked subject/predicate
时 fail-open。输出 {decision, reason, fail_open, asked, answer_slot, trace_id}。

预注册：out/ANSWER-ALIGNMENT-PREREG.md
"""

import hashlib
import re
import unicodedata

PREDICATES = {
    "密码": r"密码",
    "验证码": r"验证码",
    "IMEI": r"imei",
    "银行卡": r"银行卡|卡号|工资卡|储蓄卡|信用卡",
    "尾号": r"尾号|后四位|末四位",
    "公司": r"公司|单位|上班",
    "工位": r"工位|座位|坐哪",
    "会议号": r"会议号|会议室号|会议编号",
    "分机": r"分机|分机号",
    "年检": r"年检|年审",
    "上牌年份": r"哪年上的|上牌.*(年份|哪年)|哪年买的车",
    "疫苗编号": r"疫苗编号|疫苗批号|批号",
    "邮编": r"邮编|邮政编码",
    "手机": r"手机|电话|号码|工作号",
    "邮箱": r"邮箱",
    "老家": r"老家|哪儿人|哪里人",
    "猫": r"猫",
    "狗": r"狗",
    "车型": r"车型|两厢|三厢|suv|mpv",
    "车色": r"颜色|车色",
    "会议": r"会议|开会|组会|会定",
    "过敏": r"过敏",
    "工资": r"工资|薪资|月薪",
    "地址": r"收货地址|地址|住在哪",
    "余额": r"余额|医保卡余额|卡里.*多少钱",
    "运单号": r"运单编号|运单号|快递单号|单号",
    "出差": r"出差|去.*开会|到.*开会",
    "地点": r"在哪儿开会|哪里开会|开会地点|去哪儿|去哪里",
    "门牌号": r"门牌号|门牌",
    "储物柜": r"储物柜|柜子",
    "学号": r"学号",
    "工号": r"工号",
    "驾照": r"驾照|驾驶证",
    "护照": r"护照",
    "社保号": r"社保号|社保",
    "航班号": r"航班号|航班",
    "订单号": r"订单号|订单",
    "酒店": r"酒店|预订",
    "会员号": r"会员号|会员",
    "教练": r"教练",
    "车牌": r"车牌|车号|牌照|牌子|哪辆车",
}
SYNONYMS = {"单位": "公司", "牌照": "车牌", "座机": "手机", "手机号": "手机",
            "工作号": "手机", "工资卡": "银行卡", "储蓄卡": "银行卡"}
_PRED_RE = {k: re.compile(v, re.I) for k, v in PREDICATES.items()}

TIME_Q = re.compile(r"哪年|哪一年|什么时候|几点|哪天|几号|到期日|哪一天|多久|"
                    r"[上下中晚早凌晨]?[一二三四五六七八九十两\d]{1,2}点")
REFUSAL = re.compile(r"不知道|没记录|没有记录|不清楚|无法|记不清|没法|没提过|先不猜")

_PLATE = re.compile(r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
                    r"[A-HJ-NP-Z][A-HJ-NP-Z0-9]{5}")
_PHONE = re.compile(r"1[3-9]\d{9}")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
_DATE = re.compile(r"\d{4}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*[日号]?|"
                   r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]?|\d{1,2}\s*[点:：]\s*\d{0,2}")
_LONGNUM = re.compile(r"(?<!\d)\d{12,19}(?!\d)")
_TAIL4 = re.compile(r"(?<!\d)\d{4}(?!\d)")
_OTHER = re.compile(r"%s|%s|%s|%s" % (_PLATE.pattern, _PHONE.pattern,
                                      _EMAIL.pattern, _LONGNUM.pattern))

_SURNAMES = set("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")
_POSSESS = re.compile(r"([\u4e00-\u9fff]{2,3})(?:的|家|养的|那辆|那台|说起过|现在)")
_PRONOUN = re.compile(r"^(他|她|它|那个|那辆|那台|那家|他们|她们)")
_CN_NUM = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _cn_int(s):
    s = str(s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (_CN_NUM.get(a, 1) if a else 1) * 10 + (_CN_NUM.get(b, 0) if b else 0)
    return _CN_NUM.get(s[-1]) if s else None


_CLOCK = re.compile(r"(上午|下午|晚上|中午|早上|凌晨)?\s*"
                    r"([一二三四五六七八九十两\d]{1,2})\s*点"
                    r"(半|\s*(\d{1,2})\s*分)?")
_HHMM = re.compile(r"(\d{1,2})\s*[:：]\s*(\d{2})")


def clock_values(text):
    """中文时刻/数字时刻 -> {"HH:MM"}（支持 点/点半/上午/下午/晚上）。"""
    out = set()
    for m in _HHMM.finditer(str(text or "")):
        out.add("%02d:%02d" % (int(m.group(1)), int(m.group(2))))
    for m in _CLOCK.finditer(str(text or "")):
        part, num, half, mins = m.group(1), m.group(2), m.group(3), m.group(4)
        h = _cn_int(num)
        if h is None or h > 23:
            continue
        if part in ("下午", "晚上") and h < 12:
            h += 12
        mm = 30 if half == "半" else (int(mins) if mins else 0)
        out.add("%02d:%02d" % (h, mm))
    return out


def _norm(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = s.replace("·", "").replace("‐", "-")
    return re.sub(r"[\s,，。．.、:：;；!！?？\-—_]+", "", s)


def _cn_to_num(s):
    s = str(s or "")
    if len(s) > 4 or not all(c in _CN_NUM or c == "十" for c in s):
        return s
    if s == "十":
        return "10"
    if all(c in _CN_NUM for c in s):
        return "".join(str(_CN_NUM[c]) for c in s)
    if "十" in s:
        a, _, b = s.partition("十")
        return str((_CN_NUM.get(a, 1) if a else 1) * 10 + (_CN_NUM.get(b, 0) if b else 0))
    return str(_CN_NUM.get(s, s))


def norm_value(v):
    return _cn_to_num(_norm(v))


def ask(query):
    q = str(query or "")
    pred, facet = None, "value"
    for name, rx in _PRED_RE.items():
        if rx.search(q):
            pred, facet = name, "value"
            break
    if re.search(r"在哪|哪里|哪儿|地点|哪开", q) and pred in ("会议", "工位", None):
        pred = "地点"
    if pred in ("保险到期", "有效期", "到期日") or (pred and TIME_Q.search(q)):
        if TIME_Q.search(q):
            facet = "time"
    if pred in ("密码", "验证码", "IMEI"):
        facet = "secret"
    if pred == "尾号":
        facet = "tail"
    subject, pronoun = "self", False
    if _PRONOUN.search(q.strip()):
        pronoun = True
        subject = None
    else:
        bad = set("周天年月日点号上下今明昨后前")
        subject = "self" if "我" in q else None
        for m in _POSSESS.finditer(q):
            name = m.group(1).rstrip("养家说现")
            if len(name) >= 2 and name[0] in _SURNAMES \
                    and name not in ("我的", "我家") \
                    and not (set(name) & bad):
                subject = "name:" + name
                break
        if subject is None and "我" not in q:
            for m in re.finditer(r"([\u4e00-\u9fff]{2,3})(?:在|去|到)", q):
                name = m.group(1)
                if len(name) >= 2 and name[0] in _SURNAMES:
                    subject = "name:" + name
                    break
    explicit = {norm_value(m.group(0))
                for m in re.finditer(r"\d{2,}|\d{1,2}\s*月\s*\d{1,2}", q)}
    return {"subject": subject, "predicate": pred, "facet": facet,
            "explicit_values": explicit, "pronoun": pronoun}


def _answer_values(answer, pred):
    t = str(answer or "")
    n = _norm(t)
    vals = set()
    if pred == "车牌":
        vals |= set(_PLATE.findall(n))
    elif pred == "手机":
        vals |= set(_PHONE.findall(n))
    elif pred == "银行卡":
        vals |= {v[-4:] for v in _LONGNUM.findall(n)} | set(_TAIL4.findall(n))
    elif pred == "尾号":
        vals |= set(_TAIL4.findall(n))
    elif pred == "邮箱":
        vals |= set(_EMAIL.findall(t))
    elif pred == "车色":
        vals |= set(re.findall(r"(珍珠白|白|黑|蓝|红|灰|银|香槟|绿|黄|紫)色?", t))
    elif pred == "车型":
        vals |= set(re.findall(r"(两厢|三厢|SUV|MPV|轿车|越野)", t, re.I))
    elif pred in ("保险到期", "有效期", "到期日"):
        vals |= set(_DATE.findall(t))
    elif pred == "会议":
        vals |= clock_values(t) | set(_DATE.findall(t))
    elif pred in ("密码", "初始密码", "验证码"):
        vals |= set(re.findall(r"[A-Za-z0-9]{4,20}", t))
    elif pred == "IMEI":
        vals |= set(re.findall(r"(?<!\d)\d{15}(?!\d)", n))
    elif pred == "信用代码":
        vals |= set(re.findall(r"(?<![A-Za-z0-9])[A-Za-z0-9]{18}(?![A-Za-z0-9])", t))
    elif pred == "会议号":
        vals |= {v for v in re.findall(r"(?<!\d)\d{6,12}(?!\d)", n)}
    elif pred == "疫苗编号":
        vals |= set(re.findall(r"[A-Za-z0-9\-]{6,24}", t))
    elif pred == "分机":
        m = re.search(r"(?:分机|转|ext\.?|电话)[^\d]{0,6}(\d{3,6})(?!\d)", t, re.I)
        if m:
            vals.add(m.group(1))
    elif pred == "邮编":
        vals |= {v for v in re.findall(r"(?<!\d)\d{6}(?!\d)", n)}
    elif pred in ("年检", "上牌年份"):
        vals |= set(re.findall(r"\d{4}\s*年|\d{4}-\d{2}-\d{2}", t))
    elif pred in ("猫", "狗"):
        m = re.search(r"(?:叫|名叫|名字是)([\u4e00-\u9fff]{2,4})", t)
        if m:
            vals.add(m.group(1))
    elif pred == "公司":
        m = re.search(r"([\u4e00-\u9fff]{2,24}(?:公司|集团|银行|学校|单位))", t)
        if m:
            vals.add(m.group(1))
    elif pred == "工位":
        m = re.search(r"[A-Za-z]座\s*\d+|\d+层\s*\d+号|\d+排\s*\d+号", t)
        if m:
            vals.add(m.group(0))
    elif pred == "工号":
        vals |= set(re.findall(r"(?<![A-Za-z0-9])[A-Za-z]{0,3}-?\d{3,12}(?![A-Za-z0-9])", t))
    elif pred == "出差":
        m = re.search(r"(?:去|在|到)([\u4e00-\u9fff]{2,6}?)(?:开会|出差|旅游|办事|上班)", t)
        if m:
            vals.add(m.group(1))
        else:
            m2 = re.search(r"(?:去|到)([\u4e00-\u9fff]{2,4})", t)
            if m2:
                vals.add(m2.group(1))
    elif pred == "地点":
        vals |= set(re.findall(r"[A-Za-z]座\s*\d+|\d+楼\s*\d*|\d+层\s*\d+号", t))
        m = re.search(r"(?:去|在|到)([\u4e00-\u9fff]{2,6}?)(?:开会|出差|集合|见)", t)
        if m:
            vals.add(m.group(1))
    elif pred == "老家":
        m = re.search(r"老家(?:是|在)?([\u4e00-\u9fff]{2,4})", t)
        if m:
            vals.add(m.group(1))
    return {v for v in vals if v}


def _other_slot_values(answer):
    """答案里出现的任何已知别槽值（用于“被问槽无值但含别槽值 -> FAIL”）。"""
    found = {}
    for pred in PREDICATES:
        if pred == "密码":
            continue
        vs = _answer_values(answer, pred)
        if vs:
            found[pred] = sorted(vs)[:3]
    return found


def _block_subject(text):
    for m in _POSSESS.finditer(str(text or "")):
        name = m.group(1)
        if name[0] in _SURNAMES:
            return "name:" + name
    return None


def _subject_match(a, b):
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return None
    return na == nb or na in nb or nb in na


def decide(query, answer, blocks):
    a = ask(query)
    ans = str(answer or "")
    out = {"decision": "pass", "reason": "", "fail_open": False,
           "asked": a, "answer_slot": None,
           "trace_id": hashlib.sha256((str(query) + "\u0000" + ans)
                                      .encode("utf-8")).hexdigest()[:16]}
    if not a["predicate"]:
        out.update(fail_open=True, reason="no_asked_predicate")
        return out
    qsub = a["subject"]
    if qsub is None and not a["pronoun"]:
        vs = _answer_values(ans, a["predicate"])
        if vs:
            out.update(decision="reject", reason="unresolved_subject")
        else:
            out.update(decision="reject", reason="no_asked_subject")
        return out
    if a["pronoun"]:
        subs = [s for s in (_block_subject((b or {}).get("text")) for b in blocks or []) if s]
        if not subs:
            out.update(fail_open=True, reason="unresolved_pronoun")
            return out
        qsub = subs[0]
    nans = _norm(ans)
    for v in a["explicit_values"]:
        if len(v) >= 2 and v not in nans:
            out.update(decision="reject", reason="explicit_value_missing:%s" % v)
            return out
    avals = _answer_values(ans, a["predicate"])
    out["answer_slot"] = a["predicate"]
    if not avals and a["predicate"] in ("公司", "老家"):
        short = re.sub(r"[\s，,。．.]+", "", ans)
        if 2 <= len(short) <= 12 and re.fullmatch(r"[\u4e00-\u9fff]+", short):
            avals = {short}
    if not avals:
        others = _other_slot_values(ans)
        if others:
            out.update(decision="reject",
                       reason="other_slot_value:%s" % sorted(others)[0])
            return out
        out.update(decision="reject", reason="no_value_for_asked_slot")
        return out
    if a["facet"] == "time" and not any(
            _DATE.fullmatch(_norm(v)) or re.fullmatch(r"\d{1,2}:\d{2}", str(v))
            for v in avals):
        out.update(decision="reject", reason="facet_time_mismatch")
        return out
    if blocks is None:
        out.update(decision="pass", reason="aligned_no_blocks")
        return out
    for b in blocks or []:
        text = str((b or {}).get("text") or "")
        bsub = _block_subject(text)
        if _subject_match(qsub, bsub) is False:
            continue
        bn = _norm(text)
        if a["facet"] == "time":
            if avals & clock_values(text):
                out.update(decision="pass", reason="aligned_block")
                return out
            continue
        if any(_norm(v) and _norm(v) in bn for v in avals):
            out.update(decision="pass", reason="aligned_block")
            return out
    out.update(decision="reject", reason="no_aligned_block")
    return out