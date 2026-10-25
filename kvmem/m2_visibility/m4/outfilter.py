# -*- coding: utf-8 -*-
"""M4 output layer: whitelist filter + a failing assertion + counts. New file (M4-A).

Why a separate module instead of extending m4_display:
  m4_display decides how a DISPLAYED string is derived from a raw answer (structure vs
  content). This module answers the narrower question the acceptance asks: does the text we
  hand out still contain a control tag, and if we removed any, how many and which?

Three requirements, each with a machine-checkable form:
  1. WHITELIST ONLY: </?think>, </?response>, <|im_start|>, <|im_end|>, <|endoftext|>,
     <|eot_id|>, <|start_header_id|>, <|end_header_id|> and the generic <|...|> family.
     An unknown angle token is REPORTED, never silently rewritten, and block text never
     passes through this module (guard_not_block_text refuses it).
  2. NO SILENCE: filter_text() returns per-tag counts, before/after lengths and the exact
     spans removed, so a run json can carry the table.
  3. A FAILING ASSERTION: assert_clean() must be able to go red; run_outfilter_selftest.py
     proves it by feeding a tagged string with the filter disabled (discipline 33).

NOTE the regexes avoid backslash escapes on purpose (character classes [|] instead of the
escaped pipe, [ \t] instead of the whitespace escape): they then survive being copied
through shells and templates unchanged. A silently mangled escape is exactly the class of
bug this module exists to catch, and it bit this file once while it was being written.
"""
from __future__ import annotations

import re

TAG_TAIL = "(?:[ \t][^>]*)?>"
WHITELIST = [
    ("think", "</?think" + TAG_TAIL),
    ("response", "</?response" + TAG_TAIL),
    ("im_start", "<[|]im_start[|]>"),
    ("im_end", "<[|]im_end[|]>"),
    ("endoftext", "<[|]endoftext[|]>"),
    ("eot_id", "<[|]eot_id[|]>"),
    ("start_header_id", "<[|]start_header_id[|]>"),
    ("end_header_id", "<[|]end_header_id[|]>"),
]
GENERIC_NAME = "generic_chatml"
GENERIC_SRC = "<[|][A-Za-z0-9_]{1,32}[|]>"
GENERIC_RX = re.compile(GENERIC_SRC)
COMPILED = [(name, re.compile(rx, re.I)) for name, rx in WHITELIST]
ANY_RX = re.compile("|".join(rx for _, rx in WHITELIST) + "|" + GENERIC_SRC, re.I)
OTHER_ANGLE = re.compile("<[^<>" + chr(10) + "]{1,40}>")

ENABLED = True


class ControlTagLeft(AssertionError):
    """The delivered text still contains a control tag."""


class BlockTextWouldChange(AssertionError):
    """A caller tried to run the output filter over block text. Block text stays verbatim."""


def scan(text):
    """Per-tag counts plus unknown angle tokens. Changes nothing."""
    text = text or ""
    per_tag = {}
    known = set()
    for name, rx in COMPILED:
        ms = list(rx.finditer(text))
        if ms:
            per_tag[name] = len(ms)
            for m in ms:
                known.add(m.span())
    # generic chatml counts only tokens the named whitelist did not already claim; otherwise
    # one <|im_start|> would be reported twice and the table would over-report
    gms = [m for m in GENERIC_RX.finditer(text) if m.span() not in known]
    if gms:
        per_tag[GENERIC_NAME] = len(gms)
        for m in gms:
            known.add(m.span())
    unknown = [m.group(0) for m in OTHER_ANGLE.finditer(text) if m.span() not in known]
    return {"per_tag": per_tag, "total": sum(per_tag.values()),
            "unknown_angle_tokens": unknown}


def filter_text(text, enabled=None):
    """Remove whitelisted control tags and account for every removed character."""
    enabled = ENABLED if enabled is None else enabled
    raw = text or ""
    before = scan(raw)
    if not enabled:
        return {"text": raw, "filter_enabled": False, "per_tag": before["per_tag"],
                "total": before["total"], "before_len": len(raw), "after_len": len(raw),
                "removed_chars": 0, "removed_spans": [],
                "unknown_angle_tokens": before["unknown_angle_tokens"]}
    spans = [m.span() for m in ANY_RX.finditer(raw)]
    clean = ANY_RX.sub("", raw)
    # tag_chars_removed is ATTRIBUTABLE: exactly the characters of the matched tags, which is
    # the only thing this filter removes. A raw-to-delivered delta is not attributable here,
    # because the display layer also collapses blank runs -- keep those two apart.
    tag_chars = sum(b - a for a, b in spans)
    return {"text": clean, "filter_enabled": True, "per_tag": before["per_tag"],
            "total": before["total"], "before_len": len(raw), "after_len": len(clean),
            "tag_chars_removed": tag_chars, "removed_chars": tag_chars,
            "removed_spans": spans,
            "unknown_angle_tokens": before["unknown_angle_tokens"]}


def assert_clean(text, where):
    """THE assertion. It must be able to fail; run_outfilter_selftest.py proves it does."""
    left = scan(text)
    if left["per_tag"]:
        raise ControlTagLeft("%s: control tag(s) survived the filter: %s | head=%r"
                             % (where, left["per_tag"], (text or "")[:200]))
    return True


class ConsistencyBroken(AssertionError):
    """Two counts that must agree do not."""


# Each of these two numbers has a failure shape, which is what makes it a check rather than a
# decoration: tag_chars_removed must be > 0 exactly when a tag was found, and a cross-layer delta
# can never be SMALLER than its attributable part.
def check_counts(per_tag, tag_chars_removed, raw_to_delivered_delta=None, where="counts"):
    problems = []
    if bool(per_tag) != (tag_chars_removed > 0):
        problems.append("tag_chars_removed=%r with per_tag=%r: a tag either exists and occupies "
                        "characters, or neither is true" % (tag_chars_removed, per_tag))
    if raw_to_delivered_delta is not None and raw_to_delivered_delta < tag_chars_removed:
        problems.append("raw_to_delivered_delta=%r < tag_chars_removed=%r: removing the tags is "
                        "part of the raw-to-delivered change, so the total cannot be smaller "
                        "than its attributable part" % (raw_to_delivered_delta, tag_chars_removed))
    if problems:
        raise ConsistencyBroken("%s: %s" % (where, " | ".join(problems)))
    return True


def guard_not_block_text(text, where):
    """Block text feeds the M5 ground-truth check verbatim, so it is routed here instead of
    through filter_text: if it ever contained a whitelisted tag, filtering would silently
    change the very text M5 reads."""
    if scan(text)["total"]:
        raise BlockTextWouldChange(
            "%s: this text contains a whitelisted control tag, so the output filter would "
            "change it; block text must stay verbatim. Refusing." % where)
    return True
