# -*- coding: utf-8 -*-
"""answer_verifier.py -- 生成后「答案 vs 记忆块」确定性核对器（纯 CPU、零 GPU/零网络）。

用途：模型答完后由代码核对；不通过则把 hint 回给模型自查/重答（接线由 chat app 负责）。
本模块只做规则核对，不调用模型、不读写 DB。

API:
  verify(question, answer, blocks, mode="general") ->
      {verdict, mismatches, hint, checked_values}
      verdict ∈ {"pass","unsupported","no_evidence"}
      mismatches: [{claim, type:"value_not_in_memory", expected_from_block?}]
  strip_continuation(text) -> str   # 去 think 收尾标签 / 「用户：问：答：」续写 / 重复句

核对规则（确定性、可解释）：
  * 从 answer 抽可核对值：数字（含千分位/小数）、日期/星期/时间、地点/城市、
    房间/门牌、车牌、引号词、「是/为/在/去/住/叫/姓」后的名词短语；
  * 每个值在**任一** block 原文（归一化后）出现 => 支持，否则 mismatch；
  * 诚实拒答（不知道/没有/未提及/无法…）=> pass；
  * mode="personal" 且 blocks 为空、answer 含具体值 => no_evidence（不许凭空答）；
  * 其余 unsupported，hint 给模型重答指令（≤200 字）。
"""

import os
import re
import unicodedata

VERSION = "answer-verifier-1.0"
VERIFIER_VERSION_ENV = "VERIFIER_VERSION"


def verifier_version():
    """v1（默认，逐字旧路径）/ v2（槽位唯一值校验）。"""
    return (os.environ.get(VERIFIER_VERSION_ENV) or "v1").strip().lower()

HONEST = re.compile(r"不知道|不晓得|没有|未提及|无法|不清楚|不确定|不想猜|记忆里没有|没记录|没有记录")
THINK_TAG = re.compile(r"</?\s*(?:redacted_thinking|thinking|think|response|end_of_query|end)\b[^>]*>", re.I)
ESC_TAG = re.compile(r"&lt;/?\s*(?:redacted_thinking|thinking|think|response|end_of_query|end)\s*&gt;", re.I)
_REFUSAL = re.compile(
    r"不知道|不晓得|不清楚|不确定|无法回答|无法确认|无法判断|不能确定|不能回答|没法回答|"
    r"未提及|没有提及|没提到|未记录|没有记录|没记录|查不到|记不得|想不起来|"
    r"记忆里没有|记忆中没有|没有相关信息|没有这方面的信息|没有这方面的记录"
)
TEMPLATE_TAIL = re.compile(r"(?:^|[\n。！？!?])\s*(?:用户|问|答|User|Assistant|Q|A)\s*[：:]")
_QUOTED = re.compile(r"[“\"《「]([^”\"》」]{2,20})[”\"》」]")
_PLATE = re.compile(r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
                    r"[A-Z][A-Z0-9]{4,6}")
_CITIES = ("北京", "上海", "杭州", "西安", "广州", "深圳", "成都", "南京", "武汉",
           "重庆", "天津", "苏州", "长沙", "郑州", "青岛", "香港", "台北", "上海")
_WEEK = re.compile(r"(?:下|本|这|上)?(?:周|星期)[一二三四五六日天]")
_PHONE_GROUP = re.compile(r"\d{2,4}(?:-\d{2,4}){1,4}")
_DATE = re.compile(r"(?:(?:19|20)\d{2}\s*[-/年]\s*)?"
                   r"(?:1[0-2]|0?[1-9])\s*[月/-]\s*(?:3[01]|[12]\d|0?[1-9])\s*[日号]?")
_TIME = re.compile(r"(?:上午|下午|晚上|早上|中午)?\s*\d{1,2}\s*[点时]"
                   r"(?:\s*\d{1,2}\s*分|半)?")
_ROOM = re.compile(r"[A-Za-z]?\s*\d{0,3}\s*[座栋楼]\s*\d{1,4}\s*(?:室|号)?")
_NUM = re.compile(r"(?<![A-Za-z0-9.])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![A-Za-z0-9.])")
_AFTER = re.compile(r"(?:是|为|在|去|到|住|叫|姓)([^，。；;,.!?！？\s]{2,12})")
_CN_NUM = re.compile(r"[一二两三四五六七八九十百千万]+\s*(?:个|元|岁|层|楼|号|节|天|年|"
                     r"本|杯|份|篇|次|台|件|张|只|条|位)")
_CLASSROOM = re.compile(r"(?:[A-Za-z]?\d{1,4}\s*号?\s*(?:教室|课室)|"
                        r"[一二三四五六七八九十\d]+\s*教\s*[A-Za-z]?\d{2,4}|"
                        r"[A-Za-z]\s*教\s*[A-Za-z]?\d{2,4})")
_EN_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ID_AFTER = re.compile(r"(?:工号|学号|卡号|编号|账号|订单号|单号|运单号|保单号|发票号|型号)"
                       r"\s*(?:是|为|[:：])?\s*([A-Za-z0-9][A-Za-z0-9._\-]{1,24})")
_ALNUM_ID = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,6}[-_]?\d{3,12}(?![A-Za-z0-9])")
_MODEL_SPACE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{2,12}\s+\d{1,4})(?![A-Za-z0-9])")
_CLOCK = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)")
_NUM_WAN = re.compile(r"\d+(?:\.\d+)?\s*(?:万|亿)(?:元|块)?")
_CN_DIGIT_RUN = re.compile(r"[零一二三四五六七八九]{5,}")
_CN_BARE = re.compile(r"[一二两三四五六七八九十百千万]{2,}")
_CN_UNITS = ("个|元|块|岁|层|楼|号|节|天|年|月|日|小时|分钟|公里|米|吨|度|折|"
             "本|杯|份|篇|次|台|件|张|只|条|位|人|公斤|斤|升")
_CN_NUM_UNIT = re.compile(r"[一二两三四五六七八九十百千万]+\s*(?:%s)" % _CN_UNITS)
_CN_METER = re.compile(r"([一二两三四五六七八九十])\s*(米|公里)\s*([一二三四五六七八九])")
_CN_MONTH = re.compile(r"[一二三四五六七八九十\d]{1,2}\s*月")
_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_AFTER_CONNECTORS = ("以", "按", "根据", "按照", "依据", "为准", "是", "说", "写", "称",
                     "认为", "觉得", "应该", "大概", "可能", "可以", "需要", "要", "有",
                     "没有", "不", "还", "就", "也", "都", "这", "那", "其", "此",
                     "或", "与", "和", "及", "第一条", "第二条", "记忆", "原文", "回答")


def _cn2int(text):
    """中文数字（含十/百/千/万）-> 整数；失败返回 None；两=2。"""
    total, section, number = 0, 0, 0
    for ch in str(text or ""):
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif ch == "十":
            section += (number if number else 1) * 10
            number = 0
        elif ch == "百":
            section += (number if number else 1) * 100
            number = 0
        elif ch == "千":
            section += (number if number else 1) * 1000
            number = 0
        elif ch == "万":
            total += (section + number) * 10000
            section, number = 0, 0
        else:
            return None
    return total + section + number


def canon_text(text):
    """同义格式归一（用于匹配；不改写在答案里的原文）：
    星期/礼拜→周、HH:MM→H点、下午/晚上H点→24h、日期分隔符统一、
    中文数字+单位→阿拉伯（一周/一米八等）、号↔日、楼/层。"""
    s = unicodedata.normalize("NFKC", str(text or ""))
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)   # 千分位剥离；其它逗号保留为分隔符
    s = re.sub(r"\s+", "", s)
    s = s.lower()
    # 万/亿 -> 数字（12万元 -> 120000元；1.2亿 -> 120000000）
    def _unit_num(m):
        try:
            v = float(m.group(1)) * (10000 if m.group(2) == "万" else 100000000)
        except ValueError:
            return m.group(0)
        return ("%d" % int(v)) if abs(v - int(v)) < 1e-9 else ("%g" % v)
    s = re.sub(r"(\d+(?:\.\d+)?)(万|亿)", _unit_num, s)
    s = re.sub(r"(?:星期|礼拜)\s*([一二三四五六日天七])", r"周\1", s)
    s = _CN_METER.sub(lambda m: "%d.%d米" % (_cn2int(m.group(1)) or 0,
                                             _cn2int(m.group(3)) or 0), s)
    s = _CN_NUM_UNIT.sub(lambda m: _replace_cn_unit(m.group(0)), s)
    # 时间：HH:MM -> H点[MM分]；下午/晚上 H点 -> +12
    def _clock(m):
        h, mm = int(m.group(1)), int(m.group(2))
        return "%d点" % h if mm == 0 else "%d点%d分" % (h, mm)
    s = re.sub(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", _clock, s)
    s = re.sub(r"(下午|晚上|傍晚)\s*(\d{1,2})\s*[点时]",
               lambda m: "%d点" % ((int(m.group(2)) % 12) + 12), s)
    s = re.sub(r"(上午|早上|早晨)\s*(\d{1,2})\s*[点时]", r"\2点", s)
    s = re.sub(r"(\d{1,2})\s*[点时]\s*(\d{1,2})\s*分", r"\1点\2分", s)
    # 日期：2026/10/27、2026.10.27、2026年10月27日 -> 2026-10-27
    s = re.sub(r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})\s*[日号]?",
               r"\1-\2-\3", s)
    s = re.sub(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", r"\1-\2", s)
    s = re.sub(r"(\d+)\s*号", r"\1日", s)
    # 电话/分组数字的分隔符：先保护 ISO 日期，再删数字之间的 "-"
    s = re.sub(r"\d{4}-\d{1,2}-\d{1,2}",
               lambda m: m.group(0).replace("-", "\u0001"), s)
    s = re.sub(r"(?<=\d)-(?=\d)", "", s)
    s = s.replace("\u0001", "-")
    return s


def _replace_cn_unit(token):
    m = re.match(r"([一二两三四五六七八九十百千万]+)\s*(.+)", token)
    if not m:
        return token
    v = _cn2int(m.group(1))
    if v is None:
        return token
    return "%d%s" % (v, m.group(2))


def _english_numbers(text):
    """英文数字 -> 阿拉伯数字串（one/two/…/hundred/thousand 组合）。"""
    words = re.findall(r"[A-Za-z]+", str(text or "").lower())
    out, total, cur = [], 0, 0
    for w in words:
        if w in _EN_WORDS:
            cur += _EN_WORDS[w]
        elif w == "hundred":
            cur = max(1, cur) * 100
        elif w == "thousand":
            total += max(1, cur) * 1000
            cur = 0
        else:
            if cur or total:
                out.append(str(total + cur))
            total, cur = 0, 0
    if cur or total:
        out.append(str(total + cur))
    return out


def _norm(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = s.replace(",", "")          # 千分位：1,200 -> 1200
    s = re.sub(r"\s+", "", s)
    return s.lower()


def _kind(value):
    if value in _CITIES or re.fullmatch(r"[\u4e00-\u9fff]{2,4}(?:市|省)", value):
        return "city"
    if _ROOM.fullmatch(value):
        return "room"
    if _PLATE.fullmatch(value):
        return "plate"
    if re.search(r"[日号月]|周|星期", value):
        return "date"
    if re.search(r"[点时]", value):
        return "time"
    if re.fullmatch(r"[0-9,.]+", value.replace(" ", "")):
        return "number"
    return "entity"


def extract_values(answer):
    """从 answer 抽可核对值（去重、保序）。"""
    s = unicodedata.normalize("NFKC", str(answer or ""))
    vals = []
    for rx in (_PLATE, _ROOM, _CLASSROOM, _PHONE_GROUP, _NUM_WAN, _DATE, _CLOCK,
               _TIME, _WEEK):
        for m in rx.finditer(s):
            vals.append(m.group(0).strip())
    for c in _CITIES:
        if c in s:
            vals.append(c)
    for m in _QUOTED.finditer(s):
        vals.append(m.group(1).strip())
    for rx in (_EMAIL, _ID_AFTER, _ALNUM_ID, _MODEL_SPACE):
        for m in rx.finditer(s):
            vals.append((m.group(1) if m.groups() else m.group(0)).strip())
    for m in _CN_METER.finditer(s):
        vals.append(m.group(0).strip())
    for m in _CN_NUM_UNIT.finditer(s):
        if s[max(0, m.start() - 1):m.start()] == "第":      # 第X条/第X名 不是可核值
            continue
        numpart = re.match(r"[一二两三四五六七八九十百千万]+", m.group(0)).group(0)
        if numpart in ("万", "千", "百", "十"):
            continue                                       # 单位词本身不是值
        vals.append(m.group(0).strip())
    for m in _CN_MONTH.finditer(s):
        ctx = s[max(0, m.start() - 2):m.start()]
        val = (ctx + m.group(0)).strip() if re.fullmatch(r"(?:今|明|后|去|前|上|下)年", ctx) \
            else m.group(0).strip()
        vals.append(val)
    for m in _CN_DIGIT_RUN.finditer(s):
        tok = m.group(0)
        vals.append("".join(str(_CN_DIGITS.get(ch, ch)) for ch in tok))
    for m in _CN_BARE.finditer(s):
        if s[max(0, m.start() - 1):m.start()] == "第":
            continue
        vals.append(m.group(0).strip())

    def _overlaps(v, pool):
        nv = _norm(v)
        return any(nv in _norm(x) or _norm(x) in nv for x in pool if _norm(x))

    for m in _AFTER.finditer(s):
        frag = m.group(1).strip()
        # 排除“以第一条为准：1200 元”这类连接词/冒号片段（fuzz mode: verbose_connective）
        if re.search(r"[：:]", frag):
            continue
        frag = re.split(r"(?:为准|说的|写的|记载|记录|回答)", frag)[0].strip()
        if not frag or frag.startswith(_AFTER_CONNECTORS):
            continue
        # 否定式（不是…）、形容词/语气尾巴（确定的/别的/对的/好的…）不是事实值
        if s[max(0, m.start() - 1):m.start()] == "不":
            continue
        if frag in ("别的", "确定", "确定的", "真的", "对的", "好的", "是的", "一样",
                    "这样", "那样", "没错", "大概", "可能", "应该", "重要", "清楚"):
            continue
        if frag.endswith(("的", "吧", "呢", "吗", "了")):
            continue
        if len(frag) >= 2 and not HONEST.search(frag) and not _overlaps(frag, vals):
            vals.append(frag)
    for m in _NUM.finditer(s):
        tok = m.group(0).strip()
        if not _overlaps(tok, vals):
            vals.append(tok)
    for num in _english_numbers(s):
        if not _overlaps(num, vals):
            vals.append(num)
    # 去重 + 去掉被更长值包含的短值（如 302 vs B座302）
    uniq, seen = [], set()
    for v in vals:
        nv = _norm(v)
        if not nv or nv in seen:
            continue
        seen.add(nv)
        uniq.append(v)
    longer = [v for v in uniq if len(_norm(v)) >= 3]
    out = []
    for v in uniq:
        nv = _norm(v)
        if any(nv != _norm(w) and nv in _norm(w) for w in longer):
            continue
        out.append(v)
    return out


_NUM_TOKEN = re.compile(r"\d+(?:\.\d+)?")


def _num_canon(tok):
    try:
        f = float(tok)
    except ValueError:
        return tok
    return ("%d" % int(f)) if abs(f - int(f)) < 1e-9 else ("%g" % f)


def _supported(value, blocks):
    """匹配（fuzz 加固）：
      * 数值型值（数字/日期/时间/楼层/房间号/中文数字单位）按**数值相等**比较，
        禁止「子串」：1200 vs 11200、302 vs 1302、15 vs 2015 都 unsupported；
      * 含字母/邮箱/ID/型号/车牌的值按 token 边界整体匹配（A456 vs A123 失败）；
      * 其它（城市/引文/纯中文短语）用 canon 后的子串。
    """
    cv = canon_text(value)
    if not cv:
        return False
    has_letters = bool(re.search(r"[a-z@]", cv))
    for b in blocks:
        cb = canon_text((b or {}).get("text") or "")
        if not cb:
            continue
        if has_letters:
            idx = cb.find(cv)
            if idx < 0:
                continue
            before = cb[idx - 1] if idx > 0 else ""
            after = cb[idx + len(cv)] if idx + len(cv) < len(cb) else ""
            # 边界只看 ASCII 字母数字（中文 token 边界不应阻止匹配）
            if not re.match(r"[A-Za-z0-9]", before or " ") and \
                    not re.match(r"[A-Za-z0-9]", after or " "):
                return True
            continue
        nums = [_num_canon(x) for x in _NUM_TOKEN.findall(cv)]
        if nums:
            bnums = {_num_canon(x) for x in _NUM_TOKEN.findall(cb)}
            if all(n in bnums for n in nums):
                return True
            continue
        if cv in cb:
            return True
    return False


def match_values(values, blocks):
    """逐个值在任一 block 原文中匹配（数值相等/边界规则同 _supported）。

    返回 [{"value":str,"supported":bool,"block_id":int|None}]（保序）。
    """
    out = []
    for v in values or []:
        block_id = None
        for b in blocks or []:
            if not isinstance(b, dict):
                continue
            if _supported(v, [b]):
                try:
                    block_id = int(b.get("id")) if b.get("id") is not None else None
                except (TypeError, ValueError):
                    block_id = None
                break
        out.append({"value": v, "supported": block_id is not None,
                    "block_id": block_id})
    return out


def verify_answer(question, answer, blocks, mode="personal"):
    """对外接口（verdict/hint 由 task-19 细化；当前委托 verify 的判定）。"""
    return verify(question, answer, blocks, mode)


def _expected_from_blocks(value, blocks):
    kind = _kind(value)
    for b in blocks:
        text = unicodedata.normalize("NFKC", str((b or {}).get("text") or ""))
        if kind == "city":
            for c in _CITIES:
                if c in text and c != value:
                    return c
        elif kind == "room":
            m = _ROOM.search(text)
            if m:
                return m.group(0).strip()
        elif kind == "date":
            m = _DATE.search(text) or _WEEK.search(text)
            if m:
                return m.group(0).strip()
        elif kind == "time":
            m = _TIME.search(text)
            if m:
                return m.group(0).strip()
        elif kind == "number":
            m = _NUM.search(text)
            if m:
                return m.group(0).strip()
    return None


def _is_honest_refusal(answer):
    """诚实拒答：仅**整句拒答**才短路；拒答后又补具体/陈述主张的仍需核对。"""
    s = str(answer or "").strip()
    if not s:
        return False
    # 整句就是短拒答（允许句末标点）
    if re.fullmatch(r"(?:没有|没|无|不知道|不清楚|不知道了|没记录)[。.!！?？\s]*", s):
        return True
    if not _REFUSAL.search(s):
        return False
    cleaned = _REFUSAL.sub("", s)
    cleaned = re.sub(r"[。.!！?？，,、；;：:\s]", "", cleaned)
    # 拒答之外只剩“这个/我/相关/等信息”之类少量成分 => 仍算整句拒答
    return len(cleaned) <= 6 and "不过" not in s and "但是" not in s and "但" not in s


def verify(question, answer, blocks, mode="general"):
    """核对答案与记忆块；返回 {verdict, mismatches, hint, checked_values}。"""
    if verifier_version() == "v2":
        return verify_v2(question, answer, blocks, mode)
    blocks = [b for b in (blocks or []) if isinstance(b, dict)]
    ans = str(answer or "")
    values = extract_values(ans)
    # 1) 诚实拒答且无具体值 => pass（拒答不是错误；夹带具体值则照常核对）
    if _is_honest_refusal(ans) and not values:
        return {"verdict": "pass", "mismatches": [], "hint": "",
                "checked_values": 0}
    # 2) personal 模式无记忆：含具体值 => no_evidence（不许凭空答）
    if str(mode) == "personal" and not blocks:
        if values:
            return {"verdict": "no_evidence",
                    "mismatches": [{"claim": v, "type": "no_evidence"}
                                   for v in values[:8]],
                    "hint": _hint_no_evidence(values[:8]),
                    "checked_values": len(values)}
        return {"verdict": "pass", "mismatches": [], "hint": "",
                "checked_values": 0}
    # 3) 无块且答案含可核对值：personal/general 一律 no_evidence（fuzz:
    #    general 模式不能把个人问题里编造的具体值放行）
    if not blocks:
        if values:
            return {"verdict": "no_evidence",
                    "mismatches": [{"claim": v, "type": "no_evidence"}
                                   for v in values[:8]],
                    "hint": _hint_no_evidence(values[:8]),
                    "checked_values": len(values)}
        return {"verdict": "pass", "mismatches": [], "hint": "",
                "checked_values": 0}
    mismatches = []
    for v in values:
        if _supported(v, blocks):
            continue
        item = {"claim": v, "type": "value_not_in_memory"}
        exp = _expected_from_blocks(v, blocks)
        if exp:
            item["expected_from_block"] = exp
        mismatches.append(item)
    if not mismatches:
        return {"verdict": "pass", "mismatches": [], "hint": "",
                "checked_values": len(values)}
    return {"verdict": "unsupported", "mismatches": mismatches,
            "hint": _hint(mismatches), "checked_values": len(values)}


HINT_MAX = 200
HINT_PREFIX = "下面这些内容在记忆中找不到依据："
HINT_SUFFIX = "；请只使用记忆原文重答，或直接说不知道。"
HINT_NO_EVIDENCE_PREFIX = "没有可用的记忆块，但答案里出现了具体内容："
HINT_NO_EVIDENCE_SUFFIX = "；请直接说不知道，或只复述用户明确给过的信息。"


def _compose_hint(prefix, claims, suffix, limit=HINT_MAX):
    """拼 hint 并保证 <= limit、且后缀（重答指令）总保留。"""
    claims = [str(c).strip() for c in claims if str(c or "").strip()]
    if not claims:
        return (prefix + suffix)[:limit]
    budget = limit - len(prefix) - len(suffix)
    if budget <= 0:
        return (prefix + suffix)[:limit]
    body = ""
    for c in claims[:5]:
        cand = c if not body else body + "；" + c
        if len(cand) > budget:
            if not body:
                body = c[:budget]
            break
        body = cand
    return (prefix + body + suffix)[:limit]


def _hint(mismatches):
    """unsupported 的 hint：列不匹配项 + 重答指令；<=200 字。"""
    claims = []
    for m in mismatches:
        c = str(m.get("claim") or "").strip()
        exp = m.get("expected_from_block")
        if c and c not in claims:
            claims.append(c + ("（记忆里是 %s）" % exp if exp else ""))
    return _compose_hint(HINT_PREFIX, claims, HINT_SUFFIX)


def _hint_no_evidence(values):
    """no_evidence 的 hint：无记忆块却给了具体值；<=200 字。"""
    return _compose_hint(HINT_NO_EVIDENCE_PREFIX, list(values), HINT_NO_EVIDENCE_SUFFIX)


# ---------------------------------------------------------------------------
# 续写/标签清理（修 chat_daily isolated 后处理显示 bug；不改 chat_daily）
# ---------------------------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[。！？!?])")
MIN_DUP_KEY = 4          # 重复句比较键的最小长度：短句重复（“好。好。”）视为强调，不删
_DUP_STRIP = re.compile(r"[\W_]+", re.UNICODE)


def _dup_key(text):
    """重复句比较键：NFKC（全半角）+ 去空白/标点/符号 + 小写。"""
    s = unicodedata.normalize("NFKC", str(text or ""))
    return _DUP_STRIP.sub("", s).lower()


def strip_continuation(text):
    """去三类续写/残留：
      1) ``…thought`` 类收尾标签与 ``<think/>`` 标签；
      2) 「用户：/问：/答：/Q:/A:」模板续写（答案之后又起一轮对话）；
      3) 重复句：末尾句与前面某句（归一化后）相同则删除。
    不动正常内容与合法省略号。
    """
    s = str(text or "")
    orig = s
    s = THINK_TAG.sub("", s)
    s = ESC_TAG.sub("", s)
    # 1b) 裸 "response" 尾巴（如 "…58 元。 response" / 行首 response）：仅句界/行首/行尾处删除
    s = re.sub(r"(?:(?<=[\n。！？!?])|^)\s*response\s*(?=$|[\n。！？!?]|…)",
               "", s, flags=re.I)
    s = re.sub(r"\s*response[…\.\s]*$", "", s, flags=re.I)
    # 1c) 若确实删过尾部标签/标记，清掉留下的孤立句末标点（不误伤正文）
    if s != orig:
        s = re.sub(r"[。，,；;、\s]+$", "", s)
    # 2) 模板续写：只在答案之后（非开头）出现时截断
    for m in list(TEMPLATE_TAIL.finditer(s)):
        if m.start() > 0:
            s = s[:m.start()].rstrip("。,.，；; \n")
            break
    # 3) 重复句（从末尾删）：比较键=去空白/标点/全半角归一后的字符序列；
    #    只有重复键 >= MIN_DUP_KEY 才删，避免误伤“好。好。”这类合法强调。
    parts = [p for p in _SENT_SPLIT.split(s) if p.strip()]
    changed = True
    while changed and len(parts) >= 2:
        changed = False
        last = _dup_key(parts[-1])
        if not last:
            parts.pop()
            changed = True
            continue
        if len(last) < MIN_DUP_KEY:
            break
        for i in range(len(parts) - 1):
            if _dup_key(parts[i]) == last:
                parts.pop()
                changed = True
                break
    s = "".join(parts) if parts else s
    # 3b) 无句末标点的重复（如 “3楼开会 3楼开会”）：按空白切分，全部同键才保留第一段。
    if s.strip() and not re.search(r"[。！？!?]", s):
        segs = [x for x in re.split(r"[\s\u3000]+", s.strip()) if x]
        if len(segs) >= 2:
            keys = [_dup_key(x) for x in segs]
            if all(k == keys[0] for k in keys) and len(keys[0]) >= MIN_DUP_KEY:
                s = segs[0]
    return s.strip()


# ---------------------------------------------------------------------------
# v2：只在「查询槽位明确 + kept 里该槽位值唯一」时校验（v1 路径逐字不动）
# ---------------------------------------------------------------------------
_V2_REFUSAL = re.compile(
    r"不知道|不清楚|不确定|没有记录|没记录|记不清|记不得|想不起来|查不到|"
    r"没有这方面的|没这方面的|无法|没法|不能确定|未提及|没提到|没有提到|没有这")
_V2_TIME_Q = re.compile(r"几点|什么时候|什么时间|何时|哪天")
_V2_PLACE_Q = re.compile(r"哪|地点|在哪|哪里")
_V2_BANK_TAIL = re.compile(r"(?:尾号|卡号|银行卡)[^0-9]{0,6}(\d{4,6})")
_V2_TIME = re.compile(r"((?:上午|下午|晚上|中午|早上)?"
                      r"[一二三四五六七八九十\d]{1,2}点)")
_V2_NAME = re.compile(r"(?:名叫|名字是|名是|叫)([\u4e00-\u9fff]{2,4})")
_V2_PLATE = re.compile(r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
                       r"[A-HJ-NP-Z][A-HJ-NP-Z0-9]{5}", re.I)
_V2_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_V2_PHONE = re.compile(r"1[3-9]\d{9}")
_V2_PLACE = re.compile(
    r"(?:[A-Za-z]\s*座\s*\d{1,4}(?:\s*号)?|"
    r"[A-Za-z]区\s*\d{1,4}\s*号?|"
    r"[一二三四五六七八九十\d]{1,3}\s*楼(?:会)?|"
    r"[一二三四五六七八九十\d]{1,3}\s*层\s*\d{1,4}\s*号?)")
_V2_CITY = re.compile(r"北京|上海|广州|深圳|杭州|南京|成都|西安|武汉|重庆|苏州|天津|"
                      r"长沙|郑州|山东|河南|湖南|湖北")
_V2_COLOR = re.compile(r"(?:白|黑|蓝|红|灰|银|香槟|绿|黄|紫)色?")
_V2_MODEL = re.compile(r"(?:两厢|三厢|SUV|MPV|轿车|越野)", re.I)
_V2_TIME_CN = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6,
               "七": 7, "八": 8, "九": 9, "十": 10}


def _v2_k2():
    try:
        import k2_family
        return k2_family
    except Exception:                                # noqa: BLE001
        return None


def _v2_compact(text):
    s = unicodedata.normalize("NFKC", str(text or ""))
    s = re.sub(r"(?<=\d)[-\s－—](?=\d)", "", s)
    s = re.sub(r"\s+", "", s)
    return s.lower()


def _v2_time_canon(token):
    m = re.search(r"([一二三四五六七八九十\d]{1,2})点", token)
    if not m:
        return token
    n = m.group(1)
    if n.isdigit():
        hour = int(n)
    else:
        hour = _V2_TIME_CN.get(n, 0) or 0
    return "%d点" % hour


def _v2_company(text):
    t = _v2_compact(text)
    vals = set(re.findall(r"(?:在|去|到)([\u4e00-\u9fff]{2,6})(?:上班|公司|工作|了)", t))
    vals |= set(re.findall(r"(?:公司|单位)(?:是|在|叫)([\u4e00-\u9fff]{2,6})", t))
    return vals


def _v2_values(family, text, intent="value"):
    """该族在文本里的槽位值（族内专用抽取，避免把车牌数字当卡尾号）。"""
    t = _v2_compact(text)
    if family == "手机":
        return set(_V2_PHONE.findall(t))
    if family == "车牌":
        return {v.upper() for v in _V2_PLATE.findall(t)}
    if family == "邮箱":
        return {v.lower() for v in _V2_EMAIL.findall(t)}
    if family == "银行卡":
        return set(_V2_BANK_TAIL.findall(t))
    if family == "工位":
        return set(_V2_PLACE.findall(t))
    if family == "会议":
        if intent == "time":
            return {_v2_time_canon(v) for v in _V2_TIME.findall(t)}
        if intent == "place":
            return set(_V2_PLACE.findall(t)) | set(_V2_CITY.findall(t))
        return set()
    if family == "出差":
        return set(_V2_CITY.findall(t)) | set(_V2_PLACE.findall(t))
    if family == "健身":
        return {_v2_time_canon(v) for v in _V2_TIME.findall(t)}
    if family == "车色":
        return set(_V2_COLOR.findall(t))
    if family == "车型":
        return {v.upper() for v in _V2_MODEL.findall(t)}
    if family in ("猫", "狗"):
        return set(_V2_NAME.findall(t))
    if family == "过敏":
        return {re.sub(r"^[我你他她的对]", "", v)
                for v in re.findall(r"([\u4e00-\u9fff]{2,4})过敏", t)}
    if family == "老家":
        return set(re.findall(r"(?:老家|故乡)(?:其实)?(?:在|是)([\u4e00-\u9fff]{2,4})", t))
    if family == "公司":
        return _v2_company(t)
    return set()


def _v2_same(family, a, b):
    if family in ("手机", "银行卡"):
        return a == b
    if family in ("车牌", "车型", "邮箱"):
        return a.upper() == b.upper()
    return _v2_compact(a) == _v2_compact(b)


def _v2_contains(family, value, text):
    blob = _v2_compact(text)
    v = _v2_compact(value)
    if not v:
        return False
    if family in ("手机", "银行卡"):
        return v in blob
    if family in ("车牌",):
        return v.upper() in blob.upper()
    return v in blob


def _v2_intent(family, question):
    q = str(question or "")
    if family == "会议":
        if _V2_TIME_Q.search(q):
            return "time"
        if _V2_PLACE_Q.search(q):
            return "place"
        return None
    if family == "出差":
        return "place"
    if family == "健身":
        return "time" if _V2_TIME_Q.search(q) else None
    return "value"


def verify_v2(question, answer, blocks, mode="general"):
    """v2 判定：查询槽位明确 + kept 中该槽位值唯一 时才校验；否则 pass。"""
    ok = {"verdict": "pass", "mismatches": [], "hint": "",
          "checked_values": 0, "version": "v2"}
    k2 = _v2_k2()
    if k2 is None:
        return ok
    q = str(question or "")
    qk = k2.classify_query(q)
    family = qk.get("family")
    if not family:
        return ok
    try:
        if not k2._predicate_clear(family, q):
            return ok                                  # 谓词不明确
    except Exception:                                  # noqa: BLE001
        return ok
    if family in ("会议", "出差") and not (k2.extract_slot(q) or {}).get("day"):
        return ok                                      # 槽位不明确（无日期）
    intent = _v2_intent(family, q)
    if intent is None:
        return ok
    kept = []
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        text = str(b.get("text") or "")
        if k2.classify_row(text).get("family") == family:
            kept.append(text)
    if not kept:
        return ok
    values = set()
    for text in kept:
        values |= _v2_values(family, text, intent)
    if len(values) != 1:
        return ok                                      # 无值/多值：不校验
    value = next(iter(values))
    ans = str(answer or "")
    if _v2_contains(family, value, ans):
        return dict(ok, checked_values=1)
    ans_vals = _v2_values(family, ans, intent)
    if ans_vals:
        if any(_v2_same(family, v, value) for v in ans_vals):
            return dict(ok, checked_values=1)          # 同值（含格式归一）
        if family == "健身":
            return dict(ok, checked_values=1)          # 日期/时刻不作错值证据
        return {"verdict": "unsupported",
                "mismatches": [{"claim": sorted(ans_vals)[0],
                                "type": "wrong_slot_value",
                                "expected_from_block": value}],
                "hint": "记忆里的对应值是「%s」，请只依据记忆原文重答。" % value,
                "checked_values": 1, "version": "v2"}
    if _V2_REFUSAL.search(ans):
        return dict(ok, checked_values=1)              # 显式拒答不算遗漏
    return {"verdict": "unsupported",
            "mismatches": [{"claim": value, "type": "missing_slot_value"}],
            "hint": "记忆里有「%s」，答案没有用上，请只依据记忆原文重答。" % value,
            "checked_values": 1, "version": "v2"}


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser(description="answer verifier (CPU only)")
    ap.add_argument("--question", default="")
    ap.add_argument("--answer", required=True)
    ap.add_argument("--block", action="append", default=[])
    ap.add_argument("--mode", default="general", choices=["personal", "general"])
    a = ap.parse_args()
    blocks = [{"id": i, "text": t} for i, t in enumerate(a.block, start=1)]
    print(json.dumps(verify(a.question, a.answer, blocks, a.mode),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())