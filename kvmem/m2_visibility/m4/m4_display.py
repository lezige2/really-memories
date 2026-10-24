# -*- coding: utf-8 -*-
"""M4 display layer -- strip the model's thinking tags for USER-FACING text only.

Frozen rule (lead 2026-10-25): the raw answer in a run json stays byte-identical; the stripped
text is a DERIVED field (answer_display) and never takes part in any pass/fail decision.
Block text and KV are never touched (block_text_policy: 段内原话逐字).

Why this exists: a conversation-shaped block makes the R1-distilled model emit a closing
thinking tag before answering (evidence_think_tag.json, three-case control).
"""
from __future__ import annotations

import re

# --- the stripping rule, as testable constants -------------------------------
TAG_NAME = "think"
OPEN = "<" + TAG_NAME
CLOSE = "<" + "/" + TAG_NAME

CLOSED = re.compile(OPEN + r"\b[^>]*>.*?" + CLOSE + r"\s*>", re.S | re.I)   # <t>..</t>
OPEN_TAIL = re.compile(OPEN + r"\b[^>]*>.*\Z", re.S | re.I)                 # unclosed, cut to end
STRAY = re.compile(r"</?" + TAG_NAME + r"\b[^>]*>", re.I)                   # any leftover tag
CLOSED_LINE = re.compile(r"^[ \t]*" + OPEN + r"\b[^>]*>.*?" + CLOSE + r"\s*>[ \t]*$\n?",
                         re.S | re.M | re.I)                                # block alone on lines
TAG_LINE = re.compile(r"^[ \t]*(?:</?" + TAG_NAME + r"\b[^>]*>[ \t]*)+$\n?", re.M | re.I)
BLANK_RUN = re.compile(r"\n{3,}")


def has_tag(text):
    return bool(STRAY.search(text or ""))


def strip_think(text):
    """Return display text. When there is no tag the input is returned BYTE-IDENTICAL."""
    if not text or not has_tag(text):
        return text
    out = CLOSED_LINE.sub("", text)            # a tag-only line goes away with its newline
    out = TAG_LINE.sub("", out)
    out = CLOSED.sub("", out)                  # inline <t>..</t>
    out = OPEN_TAIL.sub("", out)               # unclosed: what follows is still thinking
    out = STRAY.sub("", out)
    out = BLANK_RUN.sub("\n\n", out)           # collapse the gap a removed line leaves behind
    return out.strip()


def derive(answer):
    """The pair written into run json: raw evidence + derived display text."""
    return {"answer": answer, "answer_display": strip_think(answer),
            "answer_display_changed": strip_think(answer) != answer}
