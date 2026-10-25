# -*- coding: utf-8 -*-
"""T-031 task 2: recover the habit block's text, build a paraphrase block, prove it.

Step 1 recovers tokens from the BLOCK itself (kvshim_load restores the seq's token
vector), then detokenizes with kvshim_piece -- no assumption that the pristine text is
what the block holds.

Step 3 asserts, on the freshly saved block:
  (a) load(seq) cell count == kvshim_tokenize(text) == expected cells
  (b) per-token pieces, concatenated, reproduce the text exactly (token identity)
  (c) encoding + saving twice yields the same sha256 (recomputable block)

The write path is the same one the other blocks used: kvshim_write(add_bos=0) then
kvshim_save.  add_bos=True: measured, not assumed -- the saved habit.kvmem itself starts with BOS
(151646, whose piece is the empty string), so every existing block is 1 + content tokens.
A paraphrase is only comparable to the family if it uses the same convention.
"""
import argparse, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import m2_visibility_probe as P                                  # noqa: E402
import kvslots as K                                              # noqa: E402

M2 = os.path.join(ROOT, "kvmem", "m2_v1")
HABIT = os.path.join(M2, "habit.kvmem")
OUT = os.path.join(M2, "habit_paraphrase.kvmem")
SIDE = os.path.join(M2, "habit_paraphrase.json")
SCRATCH = 5
CHECK = 6

# Same proposition (coffee habit: americano, no sugar), different wording.
CANDIDATES = [
    "咖啡我只喝美式，从不加糖。",
    "我只喝美式咖啡，不加糖。",
    "咖啡我只认美式，不加糖。",
    "我喝咖啡只选美式，糖一律不加。",
]


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def nt(eng, text):
    """Cells the text occupies on the block write path (add_bos=True, as measured)."""
    eng.reset(SCRATCH)
    n = int(eng.write(SCRATCH, text, add_bos=True))
    eng.reset(SCRATCH)
    return n


def seq_tokens(eng, seq, cap=4096):
    import ctypes
    L = eng.lib
    L.kvshim_seq_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_seq_tokens.restype = ctypes.c_int
    buf = (ctypes.c_int * cap)()
    n = int(L.kvshim_seq_tokens(eng.h, seq, buf, cap))
    return n, [int(buf[i]) for i in range(max(n, 0))]


def detok(eng, ids):
    return "".join(eng.piece(t) for t in ids)


def phase_tokens(eng):
    eng.reset(SCRATCH)
    n = int(eng.load(SCRATCH, HABIT))
    ids_n, ids = seq_tokens(eng, SCRATCH)
    text = detok(eng, ids)
    print("[BLOCK] file=%s" % HABIT)
    print("[BLOCK] load_return=%d n_tokens=%d pos_max=%d" % (n, ids_n, eng.pos_max(SCRATCH)))
    print("[BLOCK] token_ids=%s" % json.dumps(ids))
    print("[BLOCK] detokenized=%r" % text)
    print("[BLOCK] pristine_full_text=%r" % P.FULL["habit"]["text"])
    globals()["HABIT_TEXT"] = text
    # is the block's text the pristine sentence?
    print("[BLOCK] text==FULL.habit.text: %s" % (text == P.FULL["habit"]["text"]))
    # token identity vs a fresh tokenization of the recovered text
    import ctypes
    L = eng.lib
    L.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                  ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_tokenize.restype = ctypes.c_int
    buf = (ctypes.c_int * 4096)()
    m = int(L.kvshim_tokenize(eng.h, text.encode("utf-8"), buf, 4096))
    fresh = [int(buf[i]) for i in range(max(m, 0))]
    print("[BLOCK] tokenize(recovered_text) n=%d same_ids=%s" % (m, fresh == ids))
    eng.reset(SCRATCH)
    w = int(eng.write(SCRATCH, text, add_bos=True))
    wn, wids = seq_tokens(eng, SCRATCH)
    print("[BLOCK] write(text,add_bos=True) cells=%d ids=%s matches_block_ids=%s"
          % (w, json.dumps(wids), wids == ids))
    print("[BLOCK] pieces=%s" % json.dumps([eng.piece(t) for t in ids], ensure_ascii=False))
    print("[BLOCK] first_piece=%r (empty => BOS/special)" % eng.piece(ids[0]))
    eng.reset(SCRATCH)
    return ids, text


def phase_build(eng, cells_expect, allow_pad):
    for c in CANDIDATES:
        print("[CAND] %d cells  %r" % (nt(eng, c), c))
    picked, picked_n = None, None
    for c in CANDIDATES:
        n = nt(eng, c)
        if n == cells_expect:
            picked, picked_n = c, n
            break
    if picked is None:
        for c in CANDIDATES:
            n = nt(eng, c)
            if n <= cells_expect:
                picked, picked_n = c, n
                break
    if picked is None:
        raise SystemExit("no candidate fits %d cells" % cells_expect)
    text = picked
    if picked_n != cells_expect:
        if not allow_pad:
            raise SystemExit("picked %r measures %d, want %d (no padding allowed)"
                             % (picked, picked_n, cells_expect))
        text = P.build_exact_text(eng, picked, cells_expect)
    n_text = nt(eng, text)
    if n_text != cells_expect:
        raise SystemExit("text measures %d, need %d" % (n_text, cells_expect))

    # (c) determinism before writing anything final
    shas = []
    for tag in ("a", "b"):
        tmp = os.path.join(M2, "_det_%s.kvmem" % tag)
        if os.path.exists(tmp):
            os.remove(tmp)
        eng.reset(SCRATCH)
        if int(eng.write(SCRATCH, text, add_bos=True)) != cells_expect:
            raise SystemExit("determinism pass %s: cell count changed" % tag)
        eng.save(SCRATCH, tmp)
        shas.append(sha256(tmp))
        os.remove(tmp)
    print("[DET] sha_a=%s sha_b=%s same=%s" % (shas[0][:16], shas[1][:16], shas[0] == shas[1]))
    if shas[0] != shas[1]:
        raise SystemExit("encoding is not deterministic")

    if os.path.exists(OUT):
        raise SystemExit("%s already exists; refusing to overwrite" % OUT)
    eng.reset(SCRATCH)
    w = int(eng.write(SCRATCH, text, add_bos=True))
    b = eng.save(SCRATCH, OUT)
    print("[SAVE] wrote cells=%d bytes=%d -> %s" % (w, b, OUT))
    eng.reset(SCRATCH)

    # (a) + (b) on the saved file
    eng.reset(CHECK)
    loaded = int(eng.load(CHECK, OUT))
    ln, lids = seq_tokens(eng, CHECK)
    dt = detok(eng, lids)
    import ctypes
    L = eng.lib
    L.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                  ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    L.kvshim_tokenize.restype = ctypes.c_int
    buf = (ctypes.c_int * 4096)()
    m = int(L.kvshim_tokenize(eng.h, text.encode("utf-8"), buf, 4096))
    tok = [int(buf[i]) for i in range(max(m, 0))]
    size = os.path.getsize(OUT)
    # reference BOS id, taken from the source block itself (not hard-coded)
    eng.reset(SCRATCH)
    int(eng.load(SCRATCH, HABIT))
    _, hids = seq_tokens(eng, SCRATCH)
    eng.reset(SCRATCH)
    bos = hids[0] if hids else None
    print("[LOAD] block_cells=%d tokenize_n=%d rows=%d sha256=%s"
          % (loaded, m, ln, sha256(OUT)))
    print("[LOAD] bos_ref=%d bos_in_block=%d same_bos=%s"
          % (bos, lids[0], lids[0] == bos))
    print("[LOAD] cells == 1 + tokenize_n: %s (%d == 1 + %d)"
          % (loaded == 1 + m, loaded, m))
    print("[LOAD] per_token_ids_match(tokenize): %s" % (lids[1:] == tok))
    print("[LOAD] detok(content_tokens)==text: %s  detok(all)==text: %s"
          % (detok(eng, lids[1:]) == text, dt == text))
    print("[LOAD] formula_708_30480_n=%d size=%d ok=%s"
          % (708 + 30480 * cells_expect, size, size == 708 + 30480 * cells_expect))
    ok = (loaded == cells_expect == ln and 1 + m == cells_expect
          and lids[0] == bos and lids[1:] == tok and detok(eng, lids[1:]) == text
          and dt == text and size == 708 + 30480 * cells_expect)
    if not ok:
        raise SystemExit("BLOCK ASSERTION FAILED")
    side = {"file": OUT, "cells": cells_expect, "sha256": sha256(OUT),
            "text": text, "candidate": picked, "token_ids": lids, "bos_token": bos,
            "add_bos": True, "tokenize_n_no_bos": m,
            "source_block": HABIT, "source_block_sha256": sha256(HABIT),
            "source_block_token_ids": hids,
            "expected_cells": cells_expect, "padded": picked_n != cells_expect,
            "raw_candidate_cells": picked_n}
    with open(SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, ensure_ascii=False, indent=1)
    print("[SIDE] %s" % SIDE)
    print("[DONE] cells=%d sha=%s" % (cells_expect, side["sha256"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["tokens", "build"])
    ap.add_argument("--cells", type=int, default=12)
    ap.add_argument("--allow-pad", action="store_true")
    a = ap.parse_args()
    eng = P.open_engine()
    try:
        if a.phase == "tokens":
            phase_tokens(eng)
        else:
            phase_build(eng, a.cells, a.allow_pad)
    finally:
        eng.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
