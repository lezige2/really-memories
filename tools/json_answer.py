# -*- coding: utf-8 -*-
"""强制 JSON 输出（默认 off）：解析 / 单次重试 / 唯一渲染。

记忆类回答格式：{"status":"found|not_found","answer":"...","source_block_id":N|null}
非记忆/闲聊可纯文本。模型自报 source_block_id 只进日志，不作证据。
"""

import json
import re

VALID_STATUS = ("found", "not_found")
INSTRUCTION = (
    "【输出格式】涉及记忆事实的回答必须只输出严格 JSON："
    '{"status":"found|not_found","answer":"给用户看的回答","source_block_id":N|null}；'
    "非记忆/闲聊回答可以纯文本。不要输出 JSON 以外的解释。")

_THINK_RE = re.compile(r"<think[^>]*>.*?</think\s*>", re.S | re.I)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)
_BRACE_RE = re.compile(r"[{}]")


def strip_wrappers(raw):
    s = _THINK_RE.sub(" ", str(raw or ""))
    m = _FENCE_RE.search(s)
    if m:
        s = m.group(1)
    return s.strip()


def parse(raw):
    """-> {status, answer, source_block_id} 或 None（缺字段/非法 JSON）。"""
    s = strip_wrappers(raw)
    if not s:
        return None
    try:
        obj = json.loads(s)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    status = obj.get("status")
    answer = obj.get("answer")
    if status not in VALID_STATUS or not isinstance(answer, str):
        return None
    sid = obj.get("source_block_id")
    if sid is not None and (isinstance(sid, bool) or not isinstance(sid, int)):
        return None
    return {"status": status, "answer": answer,
            "source_block_id": sid, "reported_block_id": sid}


def looks_like_json(raw):
    s = strip_wrappers(raw)
    return s.startswith("{") or s.startswith("[")


def render_answer(raw, parsed=None):
    """唯一展示入口：JSON -> answer 文本；任何情况展示层不含 JSON 花括号。"""
    if parsed is None:
        parsed = parse(raw)
    if parsed is not None:
        return _BRACE_RE.sub("", str(parsed["answer"])).strip()
    s = strip_wrappers(raw)
    if looks_like_json(s):
        s = _BRACE_RE.sub("", s)
    return s.strip()