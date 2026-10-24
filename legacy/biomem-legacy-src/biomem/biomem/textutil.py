"""文本工具：中文友好的分词、FTS 查询构造、相似度、时间与 token 估算。

不依赖第三方库。中文用「双字切分 + FTS5」做关键词召回，
足够轻、零额外服务，也比单字切分精确得多。
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Iterable

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
TOKEN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+|[A-Za-z0-9_]+")
SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;…])|\n+")

# 只用于查询侧降噪，不影响正文索引
_STOP_BIGRAMS = {
    "我们", "你们", "他们", "她们", "什么", "怎么", "这个", "那个", "一个",
    "是不", "不是", "了吗", "的吗", "你的", "我的", "他的", "她的", "就是",
    "还是", "可以", "因为", "所以", "但是", "然后", "现在", "时候", "觉得",
    "知道", "一下", "有点", "真的", "其实", "已经", "可能", "应该", "如果",
    "这样", "那样", "这些", "那些", "自己", "别人", "东西", "事情",
}
_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
    "in", "on", "at", "it", "this", "that", "i", "you", "me", "my", "your",
    "do", "did", "does", "be", "for", "with", "about", "what", "how",
}
STOP_CHARS = set("我你他她它的了是在有和就都也很吗呢吧啊哦嗯呀哈这那")


def normalize(text: str) -> str:
    # 用 NFC 而不是 NFKC：保留中文全角标点（，。！？）不被改成半角
    return unicodedata.normalize("NFC", text or "").strip()


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    """返回 [(sentence_idx, start, end, sentence)]，offset 相对整段文本。"""
    out: list[tuple[int, int, str]] = []
    pos = 0
    for i, chunk in enumerate(SENT_SPLIT_RE.split(text)):
        if chunk is None:
            continue
        s = chunk.strip()
        if not s:
            pos += len(chunk or "")
            continue
        start = text.find(s, pos)
        if start < 0:
            start = pos
        end = start + len(s)
        out.append((len(out), start, end, s))
        pos = end
    if not out and text.strip():
        out.append((0, 0, len(text), text.strip()))
    return out


def _cjk_bigrams(run: str) -> list[str]:
    if len(run) == 1:
        return [] if run in STOP_CHARS else [run]
    return [run[i:i + 2] for i in range(len(run) - 1)]


def tokenize(text: str, *, drop_stop: bool = True) -> list[str]:
    """中文双字 + 英文/数字词。用于 FTS body 和查询。"""
    text = normalize(text)
    tokens: list[str] = []
    for m in TOKEN_RE.finditer(text):
        s = m.group(0)
        if CJK_RE.match(s[0]):
            tokens.extend(_cjk_bigrams(s))
        else:
            w = s.lower()
            if len(w) == 1 and w.isalpha():
                continue
            if drop_stop and w in _STOP_WORDS:
                continue
            tokens.append(w)
    if drop_stop:
        tokens = [t for t in tokens if t not in _STOP_BIGRAMS]
    return tokens


def fts_body(text: str) -> str:
    return " ".join(tokenize(text))


def fts_match(query: str) -> str:
    """把自然语言查询转成 FTS5 MATCH 表达式（bigram OR）。"""
    toks = tokenize(query)
    if not toks:
        # 全是停用词/单字时退化为单字
        toks = [c for c in normalize(query) if CJK_RE.match(c) and c not in STOP_CHARS][:8]
    seen: list[str] = []
    for t in toks:
        if t not in seen:
            seen.append(t)
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in seen[:24])


def char_ngrams(text: str, n: int = 3) -> set[str]:
    t = re.sub(r"\s+", "", normalize(text).lower())
    if not t:
        return set()
    if len(t) <= n:
        return {t}
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def jaccard(a: str, b: str, n: int = 3) -> float:
    sa, sb = char_ngrams(a, n), char_ngrams(b, n)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def estimate_tokens(text: str) -> int:
    """粗略 token 估算：中文按字，英文按 4 字符一词。"""
    if not text:
        return 0
    cjk = len(CJK_RE.findall(text))
    ascii_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    other = max(0, len(text) - cjk - sum(len(w) for w in re.findall(r"[A-Za-z0-9_]+", text)))
    return int(cjk * 1.0 + ascii_words * 1.3 + other * 0.35 + 0.5)


def clip_tokens(text: str, max_tokens: int) -> str:
    if estimate_tokens(text) <= max_tokens:
        return text
    # 逐段收缩，保留开头（记忆卡片通常重点在前）
    ratio = max(0.1, max_tokens / max(1, estimate_tokens(text)))
    cut = max(1, int(len(text) * ratio))
    return text[:cut].rstrip() + "…"


def stable_hash(text: str) -> int:
    return int(hashlib.blake2b(text.encode("utf-8"), digest_size=8).hexdigest(), 16)


# ----------------------------------------------------------------------
# 时间
# ----------------------------------------------------------------------
def now() -> datetime:
    return datetime.now().astimezone()


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.astimezone()
    except ValueError:
        return None


def days_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 86400.0


def human_date(s: str | None, now_dt: datetime | None = None) -> str:
    dt = parse_iso(s)
    if not dt:
        return "未知时间"
    now_dt = now_dt or now()
    d = (now_dt.date() - dt.date()).days
    if d == 0:
        return "今天"
    if d == 1:
        return "昨天"
    if d == 2:
        return "前天"
    if 0 < d < 7:
        return f"{d}天前"
    if dt.year == now_dt.year:
        return dt.strftime("%m月%d日")
    return dt.strftime("%Y年%m月%d日")