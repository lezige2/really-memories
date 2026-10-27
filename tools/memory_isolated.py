#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Isolated-sequence memory Q&A (prototype): answer personal facts from KV memory
blocks + question only, with **no dialogue history in the attended context**.

Why: the daily chat path (tools/chat_daily.py) generates on seq 0, whose KV also
holds the conversation.  When a fact question lacked a memory hit, the model could
read an older answer out of the dialogue history and repeat it (the plate-number
loop).  This module keeps generation on a dedicated sequence (default seq 7) that
only ever contains memory blocks + the current question, so the model cannot see
any earlier turn.

Mechanism (same primitives the product mount path uses, tools/chat.py:299-337):
  1. reset(7) and reset(scratch);
  2. for every memory row, in the given order:
       n = memory_source.load_into(eng, row, scratch)   # compat-checked KV load
       base = eng.pos_max(scratch) + 1 - n; move block to [cursor, cursor+n)
       eng.repos_local(scratch, cursor - base)         # rope-local move
       eng.share(scratch, 7, cursor, cursor + n)       # zero-copy seq_cp visibility
       reset(scratch)                                  # drop the scratch reference
       cursor += n
  3. eng.ask(7, question, n_predict=..., pos=cursor)   # question sits ABOVE blocks
  4. reset(7) and reset(scratch)                        # never leave state behind

Failure policy (fail-closed): any exception (incompatible/truncated block, token
count mismatch, empty answer, engine error) resets seq 7 and the scratch seq and
returns ``(None, provenance)`` with ``fallback="normal_path"``; the caller is then
free to use the ordinary dialogue path.  This function never raises for data
problems -- only for programmer errors (bad seq numbers, empty rows).

Zero changes to shim/dll/patch and to any research artifact.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import memory_source as ms  # noqa: E402

ISOLATED_SEQ = 7          # dedicated generation sequence for isolated Q&A
DEFAULT_SCRATCH = 6       # temp seq used only to load one block at a time
FALLBACK = "normal_path"


def _sha16(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _cleanup(eng, seqs):
    """Best-effort reset of every sequence this call may have touched."""
    for seq in seqs:
        try:
            eng.reset(int(seq))
        except Exception:  # noqa: BLE001
            pass


def answer_isolated(eng, rows, question, n_predict=64, scratch=DEFAULT_SCRATCH,
                    model_path=None, gen_seq=None):
    """Answer ``question`` from ``rows`` in a dedicated sequence, no dialogue.

    Parameters
    ----------
    eng : KVEngine-like (needs reset/load/repos_local/share/ask/n_tokens/pos_max)
    rows : iterable of memory_source.block_rows() tuples
    question : str  (plain question; this function does NOT wrap it -- eng.ask does)
    n_predict : int
    scratch : int   temp sequence used to load blocks one at a time (must != 7)
    model_path : str | None  passed to memory_source.load_into for compat check

    Returns
    -------
    (answer, provenance) : (str, dict) on success; (None, dict) with
    ``provenance["fallback"] == "normal_path"`` on any recoverable failure.
    """
    rows = list(rows)
    if not isinstance(question, str) or not question.strip():
        raise ValueError("answer_isolated: empty question")
    seq = int(gen_seq if gen_seq is not None else ISOLATED_SEQ)
    scratch = int(scratch)
    n_seq = int(getattr(eng, "n_seq", 0) or 0)
    if n_seq and seq >= n_seq:
        raise ValueError("answer_isolated: isolated seq %d >= eng.n_seq %d"
                         % (seq, n_seq))
    if scratch == seq:
        raise ValueError("answer_isolated: scratch seq must differ from isolated "
                         "seq %d" % seq)
    if n_seq and scratch >= n_seq:
        raise ValueError("answer_isolated: scratch seq %d >= eng.n_seq %d"
                         % (scratch, n_seq))

    prov = {
        "mode": "isolated_seq",
        "isolated_seq": seq,
        "scratch_seq": scratch,
        "n_rows": len(rows),
        "n_predict": int(n_predict),
        "model_path": os.path.basename(model_path or getattr(ms, "MODEL", "") or ""),
        "blocks": [],
        "question_sha16": _sha16(question.strip()),
        "dialogue_history_in_context": False,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    t0 = time.perf_counter()
    try:
        # 1) a clean isolated context -- both sequences from scratch
        eng.reset(seq)
        eng.reset(scratch)
        cursor = 0
        for idx, row in enumerate(rows, start=1):
            name = row[1] if len(row) > 1 else "row%d" % idx
            path = row[6] if len(row) > 6 else ""
            n_index = int(row[7]) if len(row) > 7 and row[7] is not None else None
            n = ms.load_into(eng, row, scratch, model_path=model_path)
            if int(n) <= 0:
                raise RuntimeError("%s: load_into returned %r" % (name, n))
            if n_index is not None and int(n) != int(n_index):
                raise RuntimeError("%s: block token %d != index %d"
                                   % (name, int(n), int(n_index)))
            base = int(eng.pos_max(scratch)) + 1 - int(n)
            lo = cursor
            delta = lo - base
            if delta:
                moved = int(eng.repos_local(scratch, delta))
                if moved != int(n):
                    raise RuntimeError("%s: repos_local moved %d/%d"
                                       % (name, moved, int(n)))
            hi = lo + int(n)
            eng.share(scratch, seq, lo, hi)
            # the scratch reference is no longer needed: cells stay alive via seq
            eng.reset(scratch)
            pm = int(eng.pos_max(seq))
            if pm != hi - 1:
                raise RuntimeError("%s: seq %d pos_max %d != %d after attach"
                                   % (name, seq, pm, hi - 1))
            prov["blocks"].append({
                "index": idx,
                "source_id": row[0] if len(row) > 0 else None,
                "name": name,
                "path": path,
                "n_tokens": int(n),
                "lo": int(lo),
                "hi": int(hi),
                "attach_seq": "seq_cp(%d->%d,[%d,%d))" % (scratch, seq, lo, hi),
            })
            cursor = hi
        prov["n_tokens_blocks"] = cursor
        prov["question_pos"] = int(cursor)
        # 2) question above the blocks -- the only text the model sees
        answer = eng.ask(seq, question, n_predict=int(n_predict), pos=int(cursor))
        answer = answer if isinstance(answer, str) else ("" if answer is None else str(answer))
        if not answer.strip():
            raise RuntimeError("empty answer from isolated sequence")
        prov.update({
            "answer": answer,
            "answer_chars": len(answer),
            "answer_sha16": _sha16(answer),
            "call_seq": int(seq),
            "call_pos": int(cursor),
            "elapsed_s": round(time.perf_counter() - t0, 3),
            "fallback": None,
        })
        # 3) always hand the sequences back empty
        _cleanup(eng, (scratch, seq))
        prov["cleaned"] = True
        return answer, prov
    except Exception as exc:  # noqa: BLE001
        _cleanup(eng, (scratch, seq))
        prov.update({
            "answer": None,
            "elapsed_s": round(time.perf_counter() - t0, 3),
            "fallback": FALLBACK,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "cleaned": True,
        })
        return None, prov