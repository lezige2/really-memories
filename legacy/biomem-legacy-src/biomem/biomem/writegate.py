"""写入门控：不每句话都进长期记忆。

候选条件：明确事实、高情绪事件、用户纠正、关系变化、明确要求记住。
产出的候选带来源、置信度、情绪权重与结构化谓词，供巩固阶段去重/合并冲突。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .entities import Extraction
from .textutil import normalize, split_sentences

ROLE_WORDS = (
    "程序员", "工程师", "设计师", "产品经理", "运营", "老师", "学生", "医生",
    "护士", "律师", "会计", "司机", "厨师", "自由职业", "公务员", "销售",
    "研究生", "博士生", "大学生", "高中生", "创业者", "店主",
)

REMEMBER_RE = re.compile(r"(记住|记一下|记下来|别忘了|别忘记|帮我记)")
RELATION_CHANGE_RE = re.compile(
    r"我(?:们)?(分手|和好|结婚|订婚|离婚|离职|辞职|入职|换工作|搬家|毕业|转学|退学)了?"
)
PREFERENCE_RE = re.compile(
    r"我(?:最|很|超|特别|挺|有点)?(喜欢|爱|讨厌|烦|受不了|习惯|不喜欢|害怕)([^，。！？,.!?；;]{1,30})"
)
NAME_RE = re.compile(r"(?:我叫|叫我|我的名字(?:是|叫))([^\s，。！？,.!?；;]{1,12})")
CALLNAME_RE = re.compile(r"(?:以后|就)?叫我([^\s，。！？,.!?；;]{1,12})")
HOME_RE = re.compile(r"我(?:住在|住|老家在|来自)([^\s，。！？,.!?；;]{2,14})")
WORK_RE = re.compile(r"我在([^\s，。！？,.!?；;]{2,12})(?:上班|工作|读书|上学)")
PET_RE = re.compile(
    r"(?:我)?(?:养了|养着|有一只|有个|有一条|有只)([^，。！？,.!?；;]{1,16})"
)
BIRTHDAY_RE = re.compile(r"我(?:的)?生日(?:是|在)?([^，。！？,.!?；;]{2,16})")
AGE_RE = re.compile(r"我今年(\d{1,2})岁")
JOB_RE = re.compile(r"我是(?:一个|一名)?(" + "|".join(map(re.escape, ROLE_WORDS)) + r")")
FAMILY_RE = re.compile(
    r"我(?:的)?(妈妈|爸爸|老妈|老爸|老婆|老公|女朋友|男朋友|对象|儿子|女儿|弟弟|妹妹|哥哥|姐姐)"
    r"(?:叫|是|名字叫)([^\s，。！？,.!?；;]{1,12})"
)


@dataclass
class Candidate:
    text: str
    kind: str
    source: str
    confidence: float
    emotion: float
    salience: float
    meta: dict = field(default_factory=dict)
    rationale: str = ""
    correction: bool = False


@dataclass
class GateResult:
    write: bool
    candidates: list[Candidate]
    score: float
    reasons: list[str]

    def explain(self) -> str:
        return ("写入" if self.write else "跳过") + f"（{self.score:.1f}）：" + \
               "、".join(self.reasons or ["无候选"])


def _sentence_of(text: str, start: int) -> str:
    for _idx, s, e, sent in split_sentences(text):
        if s <= start < e or (start >= s and start < e):
            return sent
    return text


def fact_sentence(predicate: str, obj: str, extra: dict | None = None) -> str:
    """把结构化谓词还原成自然中文，供卡片摘要与上下文使用。"""
    extra = extra or {}
    relation = extra.get("relation")
    if predicate == "名字":
        return f"用户的名字是{obj}"
    if predicate == "居住地":
        return f"用户住在{obj}"
    if predicate == "工作地":
        return f"用户在{obj}工作或上学"
    if predicate == "宠物/养着":
        return f"用户养着{obj}"
    if predicate == "生日":
        return f"用户的生日是{obj}"
    if predicate == "年龄":
        return f"用户{obj}"
    if predicate == "职业":
        return f"用户是{obj}"
    if predicate in ("喜欢", "讨厌", "习惯", "害怕"):
        return f"用户{predicate}{obj}"
    if predicate == "关系/状态变化":
        return f"用户{obj}了"
    if relation and predicate.endswith("的名字"):
        return f"用户的{relation}叫{obj}"
    return f"用户{predicate}：{obj}"


def _clause_of(text: str, start: int, end: int) -> str:
    """取命中片段所在的逗号/句号分句，避免一句话里多个事实共用同一张卡。"""
    delims = "，。！？；;,.!?\n"
    left = max((text.rfind(d, 0, start) for d in delims), default=-1) + 1
    rights = [text.find(d, end) for d in delims]
    rights = [r for r in rights if r != -1]
    right = min(rights) if rights else len(text)
    clause = text[left:right].strip()
    return clause if len(clause) >= 2 else text.strip()


class WriteGate:
    def __init__(self, settings) -> None:
        self.s = settings

    def evaluate(self, text: str, *, extraction: Extraction,
                 utterance_id: int | None = None) -> GateResult:
        text = normalize(text)
        emotion = extraction.emotion
        correction = extraction.correction
        candidates: list[Candidate] = []
        reasons: list[str] = []
        score = 0.0

        def add(match: re.Match, *, predicate: str, obj: str, kind: str = "semantic",
                confidence: float | None = None, extra: dict | None = None) -> None:
            sent = _clause_of(text, match.start(), match.end())[:300]
            meta = {
                "subject": "用户",
                "predicate": predicate,
                "object": obj.strip(),
            }
            if extra:
                meta.update(extra)
            meta["fact"] = fact_sentence(predicate, obj.strip(), extra)
            # 语义卡用第三人称陈述，避免「我叫林澈」这类句子被模型当成自己的身份
            body = meta["fact"] if kind == "semantic" else sent
            candidates.append(Candidate(
                text=body[:300],
                kind=kind,
                source="user",
                confidence=confidence or self.s.auto_fact_confidence,
                emotion=emotion,
                salience=min(1.0, 0.45 + emotion * 0.4 + (0.1 if correction else 0)),
                meta=meta,
                rationale=f"明确事实：{predicate}",
                correction=correction,
            ))

        for m in NAME_RE.finditer(text):
            name = m.group(1).strip("，。！？,.!? ")
            # 「我叫什么」是提问，不是自报姓名
            if name and not re.search(r"(什么|谁|啥|哪|多少|几|吗|呢)$", name):
                add(m, predicate="名字", obj=name)
                reasons.append("自报姓名")

        for m in HOME_RE.finditer(text):
            add(m, predicate="居住地", obj=m.group(1))

        for m in WORK_RE.finditer(text):
            add(m, predicate="工作地", obj=m.group(1))

        for m in PET_RE.finditer(text):
            add(m, predicate="宠物/养着", obj=m.group(1))

        for m in BIRTHDAY_RE.finditer(text):
            add(m, predicate="生日", obj=m.group(1))

        for m in AGE_RE.finditer(text):
            add(m, predicate="年龄", obj=m.group(1) + "岁")

        for m in JOB_RE.finditer(text):
            add(m, predicate="职业", obj=m.group(1))

        for m in PREFERENCE_RE.finditer(text):
            verb, obj = m.group(1), m.group(2).strip()
            if len(obj) < 1:
                continue
            pred = "喜欢" if verb in ("喜欢", "爱") else ("讨厌" if verb in ("讨厌", "烦", "受不了", "不喜欢") else "习惯")
            if verb == "害怕":
                pred = "害怕"
            add(m, predicate=pred, obj=obj, confidence=0.85)

        for m in FAMILY_RE.finditer(text):
            role, name = m.group(1), m.group(2).strip()
            add(m, predicate=f"{role}的名字", obj=name, kind="relational",
                extra={"relation": role})

        for m in RELATION_CHANGE_RE.finditer(text):
            add(m, predicate="关系/状态变化", obj=m.group(1), kind="relational",
                confidence=0.85)
            reasons.append("关系变化")

        if REMEMBER_RE.search(text):
            score += 1.2
            reasons.append("用户明确要求记住")

        if correction:
            score += 1.0
            reasons.append("用户纠正/改口")

        explicit = len(candidates)
        score += explicit * 1.6
        if explicit:
            reasons.append(f"{explicit} 条明确事实")

        if emotion >= self.s.emotion_event_threshold and len(text) >= 8:
            score += 1.5
            reasons.append(f"情绪强度 {emotion:.2f}")
            if not any(c.kind == "episodic" for c in candidates):
                candidates.append(Candidate(
                    text=text[:300],
                    kind="episodic",
                    source="user",
                    confidence=0.6,
                    emotion=emotion,
                    salience=min(1.0, 0.5 + emotion * 0.5),
                    meta={"subject": "用户", "predicate": "情绪事件", "object": text[:60]},
                    rationale="高情绪情景",
                ))

        # 去重：同谓词同宾语只留一条
        uniq: list[Candidate] = []
        seen: set[tuple[str, str]] = set()
        for c in candidates:
            key = (str(c.meta.get("predicate")), str(c.meta.get("object")))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(c)

        write = bool(uniq) and score >= self.s.write_threshold
        return GateResult(write=write, candidates=uniq if write else [],
                          score=round(score, 2), reasons=reasons)