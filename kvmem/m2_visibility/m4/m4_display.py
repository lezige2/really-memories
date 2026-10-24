# -*- coding: utf-8 -*-
"""M4 display layer: structure layer vs content layer (inspector R10, frozen 2026-10-25).

STRUCTURE: control tags and the blank runs their removal creates -> MUST be removed completely;
           leftovers are a FAILURE. Every character that disappears must be explainable.
CONTENT:   the model talking to itself (问/答) and same-sentence repeats -> reported, NEVER
           silently cleaned; the one optional transform is behind an explicit flag.
"""
from __future__ import annotations

import re

TAG_NAME = "think"
OPEN = "<" + TAG_NAME
CLOSE = "<" + "/" + TAG_NAME
TAG = CLOSE + ">"

CLOSED = re.compile(OPEN + r"\b[^>]*>.*?" + CLOSE + r"\s*>", re.S | re.I)
OPEN_TAIL = re.compile(OPEN + r"\b[^>]*>(?:(?!" + CLOSE + r"\s*>).)*\Z", re.S | re.I)
STRAY = re.compile(r"</?" + TAG_NAME + r"\b[^>]*>", re.I)
CLOSED_LINE = re.compile(r"^[ \t]*" + OPEN + r"\b[^>]*>.*?" + CLOSE + r"\s*>[ \t]*$\n?",
                         re.S | re.M | re.I)
TAG_LINE = re.compile(r"^[ \t]*(?:</?" + TAG_NAME + r"\b[^>]*>[ \t]*)+$\n?", re.M | re.I)
BLANK_RUN = re.compile(r"\n{3,}")

SELF_QA = re.compile(r"问[:：].{0,80}答[:：]", re.S)
REPEAT = re.compile(r"^(.{4,}?)\n\s*\n\1$", re.S)
SENT_END = re.compile(r"[。！？!?]")


class DiffNotExplained(AssertionError):
    """answer -> display lost something the tag whitelist does not allow."""


def has_tag(text):
    return bool(STRAY.search(text or ""))


def _spans(text):
    out = []
    for rx in (CLOSED, OPEN_TAIL, STRAY):
        for m in rx.finditer(text):
            out.append((m.start(), m.end()))
    return sorted(out)


def _mask(text):
    mask = bytearray(len(text))
    for a, b in _spans(text):
        for i in range(a, min(b, len(text))):
            mask[i] = 1
    return mask


def strip_think(text):
    if not text or not has_tag(text):
        return text
    out = CLOSED_LINE.sub("", text)
    out = TAG_LINE.sub("", out)
    out = CLOSED.sub("", out)
    out = OPEN_TAIL.sub("", out)
    out = STRAY.sub("", out)
    out = BLANK_RUN.sub("\n\n", out)
    return out.strip()


def _base_and_map(answer):
    """answer with every tag span deleted character-wise, plus base-index -> answer-index."""
    mask = _mask(answer)
    chars, where = [], []
    for i, ch in enumerate(answer):
        if not mask[i]:
            chars.append(ch)
            where.append(i)
    return "".join(chars), where


def _gaps(base, display):
    """Greedy subsequence alignment: returns (aligned, skipped spans of base)."""
    gaps, i = [], 0
    for ch in display:
        j = base.find(ch, i)
        if j < 0:
            return False, gaps
        if j > i:
            gaps.append((i, j))
        i = j + 1
    if i < len(base):
        gaps.append((i, len(base)))
    return True, gaps


def assert_diff_explained(answer, display):
    """Every deleted span must be (a) inside a tag, or (b) whitespace holding >=2 newlines or
    sitting next to a tag. Nothing else may disappear, and nothing may be reordered."""
    answer, display = answer or "", display or ""
    base, where = _base_and_map(answer)
    mask = _mask(answer)
    aligned, gaps = _gaps(base, display)
    if not aligned:
        raise DiffNotExplained("display is not a subsequence of the tag-free answer")
    for a, b in gaps:
        chunk = base[a:b]
        if chunk.strip():
            raise DiffNotExplained("non-whitespace text disappeared: %r" % chunk[:80])
        lo, hi = a, b
        while lo > 0 and base[lo - 1] in " \t\n":
            lo -= 1
        while hi < len(base) and base[hi] in " \t\n":
            hi += 1
        if base[lo:hi].count("\n") >= 3:      # blank-run merge (allowed by the whitelist)
            continue
        left = where[a] - 1 if a < len(where) else len(answer) - 1
        right = where[b] if b < len(where) else len(answer)
        near_tag = (left >= 0 and mask[left]) or (right < len(answer) and mask[right])
        if not near_tag:
            raise DiffNotExplained("whitespace disappeared with no tag or blank-run to explain it")
    if has_tag(display):
        raise DiffNotExplained("control tag survived the structure layer")
    return True


def audit(answer):
    display = strip_think(answer)
    assert_diff_explained(answer, display)
    if strip_think(display) != display:
        raise DiffNotExplained("strip_think is not idempotent")
    return {"answer": answer,
            "answer_display": display,
            "answer_display_changed": display != answer,
            "per_tag_count": len(STRAY.findall(answer or "")),
            "removed_chars": len(answer or "") - len(display),
            "display_len": len(display),
            "display_empty": display == "",
            "diff_explained": True,
            "idempotent": True}


def content_warnings(text):
    w = []
    if SELF_QA.search(text or ""):
        w.append("content_self_qa")
    if REPEAT.match((text or "").strip()):
        w.append("content_same_sentence_repeat")
    return w


def first_sentence_only(text):
    m = SENT_END.search(text or "")
    if not m:
        return text, {"first_sentence_only_applied": False, "removed_chars": 0}
    out = text[:m.end()].strip()
    return out, {"first_sentence_only_applied": True,
                 "removed_chars": len(text) - len(out)}


def derive(answer, first_sentence=False):
    d = audit(answer)
    disp = d["answer_display"]
    extra = {}
    if first_sentence:
        disp, extra = first_sentence_only(disp)
    d["answer_display"] = disp
    d["display_len"] = len(disp)
    d["display_empty"] = disp == ""
    d["content_warnings"] = content_warnings(answer)
    d.update(extra)
    return d
