# -*- coding: utf-8 -*-
"""memory_service.py -- C 版记忆数据层（把散在 chat_daily 里的启发式收拢成服务）。

分层：engine(KV/sqlite) -> **memory_service** -> chat_daily/chat_service -> tools。
本模块纯 CPU、零 GPU、零网络、无持久化副作用：只做
  * 提取：extract_facts(text) -> [{kind, subject, predicate, value, time, status}]
  * 去重/冲突：plan_upsert(facts, memories) -> {action, supersedes, keep_new, key}
  * 检索：retrieve(query, rows, topk) -> [{id, score, coverage, text}]（含现行门槛）
  * 判据辅助：needs_auto_remember(text) / is_fact_question(text) / needs_lookup(text)
  * 内省：introspect(rows, meta_fn)
chat_daily 只保留薄适配（DB/KV 写入、挂载、日志），行为与拆分前一致。
文档：docs/MEMORY-LAYER.md。
"""

import re
import unicodedata

VERSION = "memory-service-1.0"

CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
LATIN_RUN = re.compile(r"[A-Za-z0-9_]+")

# ---- 检索门槛（现行口径；chat_daily 曾内联，此处集中且可配）------------------
DEFAULT_TOP_SCORE_MIN = 2.0       # top1 绝对命中数下限
DEFAULT_COVERAGE_MIN = 0.30       # top1 查询覆盖率下限
SHORT_QUERY_MAX_TOKENS = 2        # 短查询例外：token 数 ≤2
SHORT_QUERY_MIN_SCORE = 1.0
SHORT_QUERY_MIN_COVERAGE = 0.5
TAG_WEIGHT = 2.0                  # 标签命中加权（每个命中标签 +2）


class RetrievalConfig:
    def __init__(self, top_score_min=DEFAULT_TOP_SCORE_MIN,
                 coverage_min=DEFAULT_COVERAGE_MIN,
                 tag_weight=TAG_WEIGHT,
                 short_query_max_tokens=SHORT_QUERY_MAX_TOKENS,
                 short_query_min_score=SHORT_QUERY_MIN_SCORE,
                 short_query_min_coverage=SHORT_QUERY_MIN_COVERAGE):
        self.top_score_min = float(top_score_min)
        self.coverage_min = float(coverage_min)
        self.tag_weight = float(tag_weight)
        self.short_query_max_tokens = int(short_query_max_tokens)
        self.short_query_min_score = float(short_query_min_score)
        self.short_query_min_coverage = float(short_query_min_coverage)


DEFAULT_CONFIG = RetrievalConfig()


# ---------------------------------------------------------------------------
# 文本 -> token（中文按字符 bigram；英文/数字按词；单字查询退化单字）
# ---------------------------------------------------------------------------
def tokens(text):
    toks = set()
    s = str(text or "")
    for run in CJK_RUN.findall(s):
        if len(run) == 1:
            toks.add(run)
        else:
            for i in range(len(run) - 1):
                toks.add(run[i:i + 2])
    for w in LATIN_RUN.findall(s):
        if len(w) >= 2:
            toks.add(w.lower())
    return toks


def score_row(row, query_tokens, meta_fn=None, tag_weight=TAG_WEIGHT):
    """单行相关分（bigram 命中数 + 标签命中加权），供 1 跳关联扩展排序复用。"""
    m = to_memory(row, meta_fn)
    toks = query_tokens if not isinstance(query_tokens, str) else tokens(query_tokens)
    blob = (m["text"] + "\n" + str(m.get("label") or "")).lower()
    tags = [str(t).lower() for t in (m.get("tags") or [])]
    hit = len([t for t in toks if t in blob])
    tag = len([t for t in toks
               if any((t in tg) or (tg in t and len(tg) >= 2) for tg in tags)])
    return hit + float(tag_weight) * tag


def coverage_of(hits, query_tokens):
    n = max(1, len(query_tokens))
    return len(set(hits)) / float(n)


# ---------------------------------------------------------------------------
# 记忆行归一化：兼容 ms.block_rows() 元组与 dict
# ---------------------------------------------------------------------------
def to_memory(row, meta=None):
    """把一行记忆归一成 {id,text,first_line,name,tags,source,created_at,n_tokens}。"""
    if isinstance(row, dict):
        m = dict(row)
    else:
        # ms.block_rows: (id,name,label,text,source_hash,bid,path,n_tokens,...)
        m = {"id": row[0], "name": row[1], "label": row[2], "text": row[3],
             "n_tokens": row[7] if len(row) > 7 else 0}
    m["id"] = int(m.get("id") or 0)
    m["text"] = str(m.get("text") or "")
    m.setdefault("name", "mem-%d" % m["id"])
    first = m.get("first_line")
    if not first:
        first = m["text"].strip().splitlines()[0] if m["text"].strip() else ""
    m["first_line"] = first[:60]
    m.setdefault("tags", [])
    m.setdefault("source", "manual")
    m.setdefault("created_at", None)
    m.setdefault("n_tokens", 0)
    if meta is not None:
        mm = meta(m["id"]) or {}
        m["tags"] = list(mm.get("tags") or [])
        m["source"] = mm.get("source") or "manual"
        m["related_ids"] = list(mm.get("related_ids") or [])
    return m


# ---------------------------------------------------------------------------
# 检索：bigram + 标签加权 -> 现行门槛 -> topk
# ---------------------------------------------------------------------------
def retrieve(query, rows, topk=4, cfg=None, meta_fn=None, return_stats=False):
    """返回 [{id, score, coverage, text, hits, tags}]（已过门槛、按分数降序/id 升序）。

    门槛（可在 RetrievalConfig 调）：top1 命中数 ≥2 且覆盖率 ≥0.30；
    短查询（token ≤2）例外：命中 ≥1 且覆盖率 ≥0.5。
    """
    cfg = cfg or DEFAULT_CONFIG
    mems = [to_memory(r, meta_fn) for r in rows]
    qt = tokens(query)
    scored = []
    for m in mems:
        blob = (m["text"] + "\n" + str(m.get("label") or "")).lower()
        hits = sorted(t for t in qt if t in blob)
        tags = [str(t) for t in (m.get("tags") or [])]
        tag_hits = sorted(t for t in qt
                          if any((t in tg.lower()) or (tg.lower() in t and len(tg) >= 2)
                                 for tg in tags))
        score = len(hits) + cfg.tag_weight * len(tag_hits)
        if score > 0:
            scored.append({"id": m["id"], "score": float(score),
                           "coverage": round(coverage_of(hits, qt), 4),
                           "text": m["text"], "first_line": m["first_line"],
                           "hits": hits[:8], "tag_hits": tag_hits[:4]})
    stats = {"candidates": len(scored), "query_tokens": len(qt)}
    if not scored:
        stats["gate"] = "no_candidate"
        return ([], stats) if return_stats else []
    scored.sort(key=lambda x: (-x["score"], x["id"]))
    best = scored[0]
    short_ok = (len(qt) <= cfg.short_query_max_tokens
                and best["score"] >= cfg.short_query_min_score
                and best["coverage"] >= cfg.short_query_min_coverage)
    # 标签是用户显式标注 => 强证据，允许仅标签命中（分数/覆盖率口径不变，其它路径照旧）
    tag_ok = bool(best.get("tag_hits")) and best["score"] >= cfg.tag_weight
    gate_ok = short_ok or tag_ok or (best["score"] >= cfg.top_score_min
                                     and best["coverage"] >= cfg.coverage_min)
    stats["gate"] = "pass" if gate_ok else "below_threshold"
    if not gate_ok:
        return ([], stats) if return_stats else []
    out = scored[:max(1, int(topk))]
    return (out, stats) if return_stats else out


# ---------------------------------------------------------------------------
# 规则抽取：结构化事实（允许未核实）
# ---------------------------------------------------------------------------
_ID18 = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
_PHONE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
_PLATE = re.compile(r"(?:我的)?车牌号(?:是|为)?\s*([A-Za-z0-9\u4e00-\u9fff-]{5,10})")
_MODELNO = re.compile(r"型号(?:是|为)?\s*([A-Za-z0-9._-]{2,24})")
_MONEY = re.compile(r"(?:花了|一共|总共|价格是|费用是|收了|付了)[^0-9]{0,8}"
                    r"(\d+(?:\.\d+)?)\s*(?:元|块)")
_DATE = re.compile(r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s*月\s*\d{1,2}\s*[日号]|"
                   r"每周[一二三四五六日天]|每天|每周|每月|今年|明年)")
_PLACE = re.compile(r"(?:在|去|住|到)([\u4e00-\u9fffA-Za-z0-9]{2,20}?)"
                    r"(?:店|院|馆|公司|小区|楼|路|街|市|省|区)")
_PREF = re.compile(r"(?:我)?(?:喜欢|不爱|不吃|只喝|偏好|习惯)([^。；;，,\n]{1,24})")
_ORG = re.compile(r"(?:在|去)([\u4e00-\u9fffA-Za-z0-9]{2,16}(?:店|医院|银行|公司|学校|馆))")
_ME = re.compile(r"(?:^|[，,。；;\s])(我|俺)([^。；;\n]{1,40})")


def _fact(kind, subject, predicate, value, time=None, status="未核实"):
    return {"kind": kind, "subject": subject, "predicate": predicate,
            "value": str(value).strip(), "time": time, "status": status}


def extract_facts(text):
    """规则版事实抽取；识别不了的返回空列表（不猜）。"""
    s = str(text or "").strip()
    if not s:
        return []
    facts = []
    for m in _PLATE.finditer(s):
        facts.append(_fact("identifier", "车牌号", "是", m.group(1)))
    for m in _PHONE.finditer(s):
        facts.append(_fact("contact", "手机号", "是", m.group(1)))
    for m in _ID18.finditer(s):
        facts.append(_fact("identifier", "身份证号", "是", m.group(1)))
    for m in _MODELNO.finditer(s):
        facts.append(_fact("identifier", "型号", "是", m.group(1)))
    for m in _MONEY.finditer(s):
        facts.append(_fact("amount", "金额", "花费", m.group(1) + " 元"))
    times = _DATE.findall(s)
    for m in _ORG.finditer(s):
        facts.append(_fact("entity", m.group(1), "位于/属于", "已提及",
                           time=times[0] if times else None))
    for m in _PLACE.finditer(s):
        facts.append(_fact("location", "地点", "在", m.group(1),
                           time=times[0] if times else None))
    for m in _PREF.finditer(s):
        facts.append(_fact("preference", "我", "偏好", m.group(1)))
    if times:
        facts.append(_fact("time", "我", "时间", times[0], time=times[0]))
    if not facts:
        m = _ME.search(s)
        if m:
            facts.append(_fact("statement", m.group(1), "陈述", m.group(2)[:60]))
        elif len(s) <= 200:
            facts.append(_fact("statement", "我", "陈述", s[:60]))
    # 同文本内去重
    uniq, seen = [], set()
    for f in facts:
        k = (f["kind"], f["subject"], f["predicate"], f["value"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return uniq


def fact_key(fact):
    return (str(fact.get("subject")), str(fact.get("predicate")),
            str(fact.get("kind")))


def plan_upsert(facts, memories, meta_fn=None, now=None):
    """按「主体+谓词」去重：同值 => noop；不同值 => update(保留新值, supersedes=旧 id)。

    memories: 已有记忆行（dict/ms 元组）；返回
    {actions:[{key, action, memory_id, supersedes, old_value, new_value, ts}],
     inserts:[fact], noop:[fact], updates:[...]}。
    本函数**只计划**，不写库（append-only 由调用方决定）。
    """
    mems = [to_memory(r, meta_fn) for r in memories]
    existing = []
    for m in mems:
        for f in extract_facts(m["text"]):
            existing.append((m["id"], fact_key(f), f))
    ts = now or None
    actions, inserts, noops, updates = [], [], [], []
    for f in facts or []:
        key = fact_key(f)
        same = [e for e in existing if e[1] == key]
        if not same:
            inserts.append(f)
            actions.append({"key": key, "action": "insert", "memory_id": None,
                            "supersedes": None, "new_value": f.get("value"),
                            "ts": ts})
            continue
        old = same[-1]                       # 最近一条
        if str(old[2].get("value")) == str(f.get("value")):
            noops.append(f)
            actions.append({"key": key, "action": "noop", "memory_id": old[0],
                            "supersedes": None, "new_value": f.get("value"),
                            "ts": ts})
        else:
            updates.append(f)
            actions.append({"key": key, "action": "update", "memory_id": old[0],
                            "supersedes": old[0],
                            "old_value": old[2].get("value"),
                            "new_value": f.get("value"), "ts": ts})
    return {"actions": actions, "inserts": inserts, "noop": noops,
            "updates": updates,
            "summary": {"insert": len(inserts), "noop": len(noops),
                        "update": len(updates)}}


# ---------------------------------------------------------------------------
# 行为判据（从 chat_daily 收拢；保持逐字口径）
# ---------------------------------------------------------------------------
_FACT_HINT = re.compile(
    r"(我|俺)[^。；;\n]{0,10}(在|是|叫|姓|住|去|要|有|每周|每天|每月|明天|后天|下周|"
    r"下个月|今年|生日|电话|邮箱|车牌|工位|开会|上班|下班|喜欢|不爱|不吃|只喝|养|买了|交|要交|约)")
_QUESTION_HINT = re.compile(
    r"[?？]|吗|呢|什么|多少|几|哪|谁|怎么|为什么|是不是|有没有|能不能|会不会|要不要|可不可以")
_SEARCH_HINT = re.compile(
    r"查一?下|查查|搜一下|帮我查|搜索|最新|实时|新闻|天气|气温|股价|汇率|价格|多少钱|"
    r"几点|哪年|出生|是谁|什么是|翻译|怎么读|上映|比分|邮编|电话")
_QUESTION = re.compile(r"[?？]|吗|多少|几|什么|哪|谁|是不是|有没有|多久|多大|几点")
_WORLD = re.compile(r"首都|省会|天气|翻译|写个|写一个|函数|代码怎么写|怎么做|为什么|"
                    r"解释一下|介绍|区别|原理|算法|历史|哪年|谁发明")
_SELF_FACT = re.compile(
    r"(我的|我)(工号|车牌|生日|电话|手机|地址|护照|血型|身高|体重|老家|密码|身份证|"
    r"房贷|利率|工资|薪水|保险|保单|合同|车位|房租|余额|卡号|学号|车牌号|社保|公积金)")
RECALL_VERB = re.compile(r"上次|之前|以前|还记得|记得|我说过|我说的是|刚才说|前面说|"
                         r"刚才提到|前面提到|上回")


def needs_auto_remember(text):
    """陈述「我的事实」=> True（静默写入）；问题/命令/过短过长 => False。"""
    q = str(text or "").strip()
    if not (6 <= len(q) <= 200):
        return False
    if q.startswith("/") or q.startswith("记住") or q.startswith("记一下"):
        return False
    if _QUESTION_HINT.search(q):
        return False
    if "我" not in q[:12] and "俺" not in q[:12]:
        return False
    return bool(_FACT_HINT.search(q))


def is_fact_question(text):
    """应用层拒答判据：个人事实问句 => True（无记忆命中时应拒答）。"""
    q = str(text or "").strip()
    if not q:
        return False
    if _SELF_FACT.search(q) or RECALL_VERB.search(q):
        return True
    if _WORLD.search(q):
        return False
    if not _QUESTION.search(q):
        return False
    return True


def is_memory_recall_intent(text):
    """兼容 evidence.decide 的 memory_recall 口径（供 chat_daily 透传）。"""
    q = str(text or "").strip()
    if not q:
        return False
    if _WORLD.search(q):
        return False
    if not _QUESTION.search(q):
        return False
    return bool(RECALL_VERB.search(q) or _SELF_FACT.search(q))


def needs_lookup(text, control=False):
    """是否该走联网检索（时间敏感/需查证的问题；个人记忆召回不联网）。"""
    q = str(text or "").strip()
    if not q or control:
        return False
    if is_memory_recall_intent(q):
        return False
    return bool(_QUESTION.search(q) and _SEARCH_HINT.search(q))


# ---------------------------------------------------------------------------
# 内省
# ---------------------------------------------------------------------------
def introspect(rows, meta_fn=None):
    """返回记忆清单 [{id, first_line, len, source, tags, related_ids, created_at, n_tokens}]。"""
    out = []
    for r in rows:
        m = to_memory(r, meta_fn)
        out.append({"id": m["id"], "name": m.get("name"),
                    "first_line": m["first_line"],
                    "len": len(m["text"]), "source": m.get("source", "manual"),
                    "tags": list(m.get("tags") or []),
                    "related_ids": list(m.get("related_ids") or []),
                    "created_at": m.get("created_at"),
                    "n_tokens": int(m.get("n_tokens") or 0)})
    out.sort(key=lambda x: x["id"])
    return out

# ===========================================================================
# 结构化槽位（task-32 / T15，schema 扩展）：12 键
# time / person / event / place / action / object /
# cause / result / quantity / purpose / method / constraint
# 槽位只做元数据索引；命中后仍挂**原文块**（KV 保持原文）。
# ===========================================================================
SLOT_KEYS = ("time", "person", "event", "place", "action", "object",
             "cause", "result", "quantity", "purpose", "method", "constraint")
# 连接词类槽位抽不到时明确标“未核实”，不硬猜
UNVERIFIED_SLOT_KEYS = ("cause", "result", "purpose", "method", "constraint")

_CITY_LIST = ("广州", "成都", "北京", "上海", "杭州", "西安", "深圳", "南京", "武汉",
              "重庆", "天津", "苏州", "长沙", "郑州", "青岛", "香港", "台北", "厦门",
              "福州", "昆明", "贵阳", "南宁", "合肥", "济南", "沈阳", "大连", "哈尔滨")
_EVENT_WORDS = ("开会", "会议", "组会", "例会", "出差", "体检", "旅行", "面试", "聚餐",
                "看电影", "上课", "健身", "复盘", "搬家", "装修", "考试", "签证",
                "生日", "婚礼", "看病", "买房", "买车", "还款", "报销", "培训",
                "演讲", "约会", "值班", "加班")
_TIME_RXS = (
    re.compile(r"(?:下|本|这|上)?(?:周|星期)[一二三四五六日天]"),
    re.compile(r"(?:今天|明天|后天|昨天|前天|周末|工作日)"),
    re.compile(r"(?:19|20)\d{2}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*[日号]?"),
    re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]?"),
    re.compile(r"(?:上午|下午|晚上|早上|中午)?\s*\d{1,2}\s*[点时](?:\s*半|\s*\d{1,2}\s*分)?"),
)
_ROOM_RX = re.compile(r"[A-Za-z]?\s*\d{0,3}\s*[座栋楼]\s*\d{1,4}\s*(?:室|号)?")
_PLACE_SUFFIX_RX = re.compile(
    r"[\u4e00-\u9fffA-Za-z0-9]{2,12}(?:会议室|教室|机场|车站|酒店|医院|公司|书店|"
    r"公园|广场|大学|学校|路|街|小区|大厦|中心)")
_PERSON_RXS = (
    re.compile(r"(?:我叫|名字叫|名字是|姓名是?|大家都叫我)\s*([\u4e00-\u9fffA-Za-z]{1,8})"),
    re.compile(r"(?:^|[，,。；;\s])叫\s*([\u4e00-\u9fff]{2,4})"),
)
_REL_PERSON_RX = re.compile(r"(我妈|我爸|我哥|我姐|我弟|我妹|我老婆|我老公|我孩子|"
                            r"我儿子|我女儿|我同事|我朋友|我领导|我老师)")
_PET_RX = re.compile(r"养(?:了)?(?:一)?(?:只|条|头)?(猫|狗|宠物)")
_PET_NAME_RX = re.compile(
    r"(?:猫|狗|宠物)[^。；;\n]{0,8}?叫\s*([\u4e00-\u9fffA-Za-z0-9]{2,8})")
_ACTION_WORDS = ("去", "到", "来", "开会", "出差", "体检", "上课", "买", "吃", "喝",
                 "学", "练", "看", "改签", "订", "报名", "交", "养", "搬家", "装修",
                 "面试", "旅行", "看病", "加班", "复盘")
_QUANTITY_RX = re.compile(
    r"\d+(?:\.\d+)?\s*(?:个|元|块|岁|层|楼|号|节|天|年|月|日|小时|分钟|公里|米|"
    r"吨|度|折|本|杯|份|篇|次|台|件|张|只|条|位|人|公斤|斤|升)|"
    r"[一二两三四五六七八九十百千万]+\s*(?:个|元|块|岁|层|楼|号|节|天|年|月|日|"
    r"小时|分钟|公里|米|吨|度|折|本|杯|份|篇|次|台|件|张|只|条|位|人|公斤|斤|升)")
_CAUSE_RX = re.compile(r"(?:因为|由于|原因是|之所以|起因是)\s*([^，。；;！？!?\n]{2,30})")
_RESULT_RX = re.compile(r"(?:所以|结果|因此|导致|以至于|于是)\s*([^，。；;！？!?\n]{2,30})")
_PURPOSE_RX = re.compile(r"(?:为了|目的是|为的是|用来|以便|好让)\s*([^，。；;！？!?\n]{2,30})")
_METHOD_RX = re.compile(r"(?:通过|用|拿|靠|坐|乘|开车|骑车|走路|拨打|发邮件|线上)\s*"
                        r"([^，。；;！？!?\n]{2,30})")
_CONSTRAINT_RX = re.compile(r"(?:必须|只能|只能先|不要|不能|不得|务必|一定要|除了[^，。]{1,12}外)"
                            r"\s*([^，。；;！？!?\n]{0,30})")
_WANT_PATTERNS = (
    ("time", re.compile(r"什么时候|几点|何时|哪天|日期|时间|多久")),
    ("place", re.compile(r"在哪|哪里|哪儿|什么地方|哪个(?:会议室|房间|地方)|去哪|到哪|地点")),
    ("quantity", re.compile(r"多少|几个|几件|几次|几年|多大")),
    ("cause", re.compile(r"为什么|为何|原因|怎么会")),
    ("result", re.compile(r"结果|后来怎样|最后怎样")),
    ("purpose", re.compile(r"目的|为了什么|干什么用|有什么用")),
    ("method", re.compile(r"怎么(?:去|做|弄|办|样做)|如何|用什么方法|方式")),
    ("action", re.compile(r"做什么|干什么|干嘛|做什么事")),
    ("object", re.compile(r"叫什么|叫啥|什么型号|什么名字|哪个(?:猫|狗|宠物)")),
    ("person", re.compile(r"叫什么|叫啥|名字|姓名|称呼|是谁|谁")),
)


def _slot_norm(s):
    t = unicodedata.normalize("NFKC", str(s or ""))
    t = re.sub(r"\s+", "", t)
    t = t.replace("星期六", "周六").replace("星期日", "周日").replace("星期天", "周日")
    t = re.sub(r"星期([一二三四五六])", r"周\1", t)
    t = re.sub(r"礼拜([一二三四五六日天])", r"周\1", t)
    return t.lower()


def extract_slots(text):
    """从记忆原文抽 12 个槽位（规则版；缺省 None，连接词类记“未核实”）。"""
    s = str(text or "")
    slots = {k: None for k in SLOT_KEYS}
    if not s.strip():
        return slots
    for rx in _TIME_RXS:
        m = rx.search(s)
        if m:
            slots["time"] = m.group(0).strip()
            break
    for city in _CITY_LIST:
        if city in s:
            slots["place"] = city
            break
    if not slots["place"]:
        m = _ROOM_RX.search(s)
        if m and re.search(r"[座栋楼]", m.group(0)):
            slots["place"] = m.group(0).strip()
    if not slots["place"]:
        m = _PLACE_SUFFIX_RX.search(s)
        if m:
            slots["place"] = m.group(0).strip()
    for ev in _EVENT_WORDS:
        if ev in s:
            slots["event"] = ev
            break
    m = _PET_RX.search(s)
    if m:
        slots["event"] = slots["event"] or ("养" + m.group(1))
        nm = _PET_NAME_RX.search(s)
        if nm:
            slots["object"] = nm.group(1)
    if not slots["object"]:
        m = re.search(r"型号(?:是|为)?\s*([A-Za-z0-9][A-Za-z0-9._-]{1,24})", s)
        if m:
            slots["object"] = m.group(1)
    for a in _ACTION_WORDS:
        if a in s:
            slots["action"] = a
            break
    # 人物：先关系称谓，再姓名；“猫叫豆豆”不算人名
    rm = _REL_PERSON_RX.search(s)
    if rm:
        slots["person"] = rm.group(1)
    pet_ctx = bool(_PET_RX.search(s)) or bool(re.search(r"(?:猫|狗|宠物).{0,8}叫", s))
    if not slots["person"]:
        _BAD_NAME = re.compile(r"什么|啥|哪|谁|几|多少|名字|哪位|啥名|什么名字|叫什么")
        for rx in _PERSON_RXS:
            for m in rx.finditer(s):
                name = m.group(1).strip()
                if not name or len(name) < 2 or _BAD_NAME.search(name):
                    continue
                if pet_ctx and re.search(r"(?:猫|狗|宠物).{0,8}叫", m.group(0)):
                    continue
                slots["person"] = name
                break
            if slots["person"]:
                break
    qm = _QUANTITY_RX.search(s)
    if qm:
        slots["quantity"] = qm.group(0).strip()
    for key, rx in (("cause", _CAUSE_RX), ("result", _RESULT_RX),
                    ("purpose", _PURPOSE_RX), ("method", _METHOD_RX),
                    ("constraint", _CONSTRAINT_RX)):
        m = rx.search(s)
        if m:
            cap = m.group(1).strip() if m.groups() else m.group(0).strip()
            slots[key] = cap or m.group(0).strip()
    return slots


def unverified_slots(slots):
    """返回抽不到的具体槽位键（连接词类，按“未核实”处理）。"""
    slots = slots or {}
    return [k for k in UNVERIFIED_SLOT_KEYS if not slots.get(k)]


def query_slots(question):
    """问句 -> {want, slots:{time,event,place,person,...}, structured}。

    structured=False 时调用方不做槽位过滤（保持旧检索行为）。
    """
    q = str(question or "")
    base = extract_slots(q)
    qs = {k: base.get(k) for k in ("time", "event", "place") if base.get(k)}
    want = None
    pet_ctx = bool(re.search(r"猫|狗|宠物", q))
    name_ask = bool(re.search(r"叫什么|叫啥|名字|姓名|称呼|是谁|谁", q))
    if re.search(r"什么型号|哪个(?:猫|狗|宠物)|哪只(?:猫|狗)", q):
        want = "object"
    elif pet_ctx and name_ask:
        want = "object"
    elif name_ask:
        want = "person"
    else:
        for slot, rx in _WANT_PATTERNS:
            if rx.search(q):
                want = slot
                break
    # 只有“明确时间/事件”或“问人名/对象名”才做槽位过滤；数量/原因/方式等
    # 只作为软加权（避免把普通“多少/为什么”问题误过滤成无记忆）。
    structured = bool(qs.get("time") or qs.get("event")
                      or (want in ("person", "object")
                          and re.search(r"叫什么|叫啥|名字|姓名|称呼", q)))
    return {"want": want, "slots": qs, "structured": structured}


def slot_match(qslots, slots):
    """兼容性：time 硬过滤；event/place/person 冲突剔除（无值不拦）；
    want 槽位必须存在（问什么就得有对应槽位）。"""
    if not qslots or not qslots.get("structured"):
        return True
    qs = qslots.get("slots") or {}
    slots = slots or {}
    qt = _slot_norm(qs.get("time"))
    if qt:
        mt = _slot_norm(slots.get("time"))
        if not mt or mt != qt:
            return False
    for key in ("event", "place", "person"):
        qv = _slot_norm(qs.get(key))
        if not qv:
            continue
        mv = _slot_norm(slots.get(key))
        if mv and not (qv in mv or mv in qv):
            return False
    want = qslots.get("want")
    if want and not _slot_norm(slots.get(want)):
        return False
    return True


def slot_bonus(qslots, slots):
    """槽位加权（检索叠加顺序：event/place/person 加权；quantity/cause/purpose/method 命中加分）。"""
    if not qslots or not qslots.get("structured"):
        return 0.0
    qs = qslots.get("slots") or {}
    slots = slots or {}
    score = 0.0
    for key, w in (("event", 3.0), ("place", 2.0), ("person", 2.0)):
        qv = _slot_norm(qs.get(key))
        if qv and _slot_norm(slots.get(key)):
            mv = _slot_norm(slots.get(key))
            score += w if (qv in mv or mv in qv) else -w
    want = qslots.get("want")
    if want and _slot_norm(slots.get(want)):
        score += 1.0
    for key in ("quantity", "cause", "purpose", "method"):
        if _slot_norm(slots.get(key)):
            score += 0.5
    return score


def filter_by_slots(rows, qslots, meta_fn=None):
    """按问句槽位过滤记忆行（dict 或 ms 元组）；structured=False 原样返回。"""
    if not qslots or not qslots.get("structured"):
        return list(rows)
    out = []
    for r in rows:
        m = to_memory(r, meta_fn)
        slots = (m.get("slots") if isinstance(m, dict) else None) or extract_slots(m["text"])
        if slot_match(qslots, slots):
            out.append(r)
    return out
