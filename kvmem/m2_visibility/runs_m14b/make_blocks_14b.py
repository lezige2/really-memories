# -*- coding: utf-8 -*-
"""14B block maker. Writes blocks at base 0 with add_bos=True, same as the 7B batch.

Usage: python -X utf8 make_blocks_14b.py --outdir <dir> --json <path> [--allow-existing]

14B constants are DERIVED and asserted, not fitted:
    fixed  = 12 + 4 + 4 + 16 + 48*24            = 1188
    per cell = 4 + 12 + 48*1088*2               = 104464
    size   = 1188 + 104464*n
If any assertion fails the script stops and prints measured size + the (header, cell)
pair backed out of it; it never adjusts a constant to make a block pass.
"""
import argparse, ctypes, hashlib, json, os, struct, sys

ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P   # noqa: E402

P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"

BOS = 151646
HDR14, CELL14 = 1188, 104464
N_LAYER, N_ROT_K, N_ROT_V, K_TYPE, K_ROW = 48, 128, 64, 8, 1088

FIX = json.load(open(os.path.join(ROOT, "kvmem", "m2_visibility", "fixtures.json"),
                     encoding="utf-8"))
PP18 = FIX["blocks"]["variant"]["project_paraphrase18"]["text"]
PP18_TEXT_SHA = "03835830816bd7de75b9d86ef2e5225f310fb2260fae5316004c3f8983db54aa"

BLOCKS = [
    ("home",     P.FULL["home"]["text"],    21),
    ("project",  P.FULL["project"]["text"], 18),
    ("habit",    P.FULL["habit"]["text"],   12),
    ("project_paraphrase18", PP18,          18),
]


def parse14(path):
    raw = open(path, "rb").read()
    magic, ver, n = struct.unpack_from("<3I", raw, 0)
    off = 12
    toks = list(struct.unpack_from("<%di" % n, raw, off)); off += 4 * n
    n_stream, = struct.unpack_from("<I", raw, off); off += 4
    info = {"magic": hex(magic), "version": ver, "n_tokens": n,
            "first_token": toks[0], "n_stream": n_stream,
            "tokens": toks, "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}
    for _ in range(n_stream):
        cell, = struct.unpack_from("<I", raw, off); off += 4
        info["cell_count"] = cell
        for _i in range(cell):
            pos, nseq = struct.unpack_from("<Ii", raw, off); off += 8 + 4 * nseq
        vt, nl, nrk, nrv = struct.unpack_from("<4I", raw, off); off += 16
        info.update({"v_trans": vt, "n_layer": nl, "n_rot_k": nrk, "n_rot_v": nrv})
        for il in range(nl):
            kt, = struct.unpack_from("<i", raw, off); off += 4
            kr, = struct.unpack_from("<Q", raw, off); off += 8
            if il == 0:
                info["k_type"], info["k_row"] = kt, kr
            off += cell * kr
        for il in range(nl):
            vty, = struct.unpack_from("<i", raw, off); off += 4
            vr, = struct.unpack_from("<Q", raw, off); off += 8
            if il == 0:
                info["v_type"], info["v_row"] = vty, vr
            off += cell * vr
    info["consumed"] = off
    info["consumed_to_eof"] = (off == len(raw))
    return info


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--allow-existing", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    for name, _t, _n in BLOCKS:
        p = os.path.join(a.outdir, name + ".kvmem")
        if os.path.exists(p) and not a.allow_existing:
            raise SystemExit("refusing to overwrite existing block: %s" % p)

    guard = {"pp18_text_sha256": hashlib.sha256(PP18.encode("utf-8")).hexdigest()}
    if guard["pp18_text_sha256"] != PP18_TEXT_SHA:
        raise SystemExit("STOP: pp18 text from fixtures.json does not match the recorded "
                         "text sha256: got %s want %s"
                         % (guard["pp18_text_sha256"], PP18_TEXT_SHA))

    dll = r"D:/llama-mem/tools/kvshim_vk.dll"
    meta = {"schema": "blocks_14b_v1", "outdir": os.path.abspath(a.outdir),
            "model": P.MODEL, "model_size": os.path.getsize(P.MODEL),
            "dll": dll, "dll_sha256": sha_file(dll),
            "assert_constants": {"header": HDR14, "per_cell": CELL14,
                                 "n_layer": N_LAYER, "n_rot_k": N_ROT_K,
                                 "n_rot_v": N_ROT_V, "k_type": K_TYPE, "k_row": K_ROW},
            "guard": guard, "blocks": []}

    eng = P.open_engine()
    try:
        # kvslots does not declare these two; make_t032_blocks.py:68-71 sets them the same way.
        eng.lib.kvshim_seq_tokens.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                              ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        eng.lib.kvshim_seq_tokens.restype = ctypes.c_int
        eng.lib.kvshim_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                            ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        eng.lib.kvshim_tokenize.restype = ctypes.c_int
        meta["loaded_path"] = eng.lib._name
        meta["bytes_per_token"] = eng.bytes_per_token()
        P.measure(eng, "x")   # warm
        for name, text, want in BLOCKS:
            path = os.path.join(a.outdir, name + ".kvmem")
            rec = {"name": name, "path": os.path.abspath(path), "text": text,
                   "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                   "declared_cells": want}
            n_meas = P.measure(eng, text)
            rec["measure_with_bos"] = n_meas
            if n_meas != want:
                raise SystemExit("STOP %s: measures %d cells (add_bos=True), declared %d. "
                                 "No padding, nothing written." % (name, n_meas, want))
            eng.reset(2)
            written = eng.write_at(2, text, 0, add_bos=True)
            rec["written_return"] = written
            if written != want:
                raise SystemExit("STOP %s: wrote %d, expected %d" % (name, written, want))
            seq_toks = (ctypes.c_int * 4096)()
            n_seq = int(eng.lib.kvshim_seq_tokens(eng.h, 2, seq_toks, 4096))
            seq_list = [int(seq_toks[i]) for i in range(n_seq)]
            rec["n_tokens_in_seq"] = n_seq
            rec["pos_max_in_seq"] = eng.pos_max(2)
            if eng.save(2, path) <= 0:
                raise SystemExit("STOP %s: save failed" % name)
            eng.reset(2)

            txt = (ctypes.c_int * 4096)()
            n_txt = int(eng.lib.kvshim_tokenize(eng.h, text.encode("utf-8"), txt, 4096))
            txt_list = [int(txt[i]) for i in range(n_txt)]
            rec["tokenize_n"] = n_txt
            rec["token_ids"] = txt_list

            eng.reset(5)
            n_load = eng.load_strict(5, path)
            rb = (ctypes.c_int * 4096)()
            n_rb = int(eng.lib.kvshim_seq_tokens(eng.h, 5, rb, 4096))
            rb_list = [int(rb[i]) for i in range(n_rb)]
            eng.reset(5)

            h = parse14(path)
            rec["parsed"] = {k: h[k] for k in
                             ("magic", "version", "n_tokens", "first_token", "n_stream",
                              "cell_count", "v_trans", "n_layer", "n_rot_k", "n_rot_v",
                              "k_type", "k_row", "v_type", "v_row", "size", "sha256",
                              "consumed", "consumed_to_eof")}
            rec["size"] = h["size"]
            rec["sha256"] = h["sha256"]
            rec["cells"] = h["n_tokens"]
            rec["first_token"] = h["first_token"]
            rec["has_bos"] = h["first_token"] == BOS
            rec["content_tokens"] = h["n_tokens"] - 1 if rec["has_bos"] else h["n_tokens"]

            derived_hdr = h["size"] - CELL14 * h["n_tokens"]
            rec["size_derived_header"] = derived_hdr
            checks = {
                "a_measure_equals_declared": n_meas == want,
                "b_written_equals_declared": written == want,
                "c_reload_cells": n_load == want,
                "c_first_token_is_bos": h["first_token"] == BOS,
                # kvshim_tokenize() excludes BOS; the block does not. Same comparison as
                # make_t032_blocks.py:107-108.
                "c_tokens_match_tokenize": rb_list[1:] == txt_list and rb_list[0] == BOS,
                "c_inmemory_tokens_match": seq_list[0] == BOS and seq_list[1:] == txt_list,
                "d_bos_position_zero": eng.pos_max(2) is not None,
                "e_size_is_1188_plus_104464n": h["size"] == HDR14 + CELL14 * h["n_tokens"],
                "f_n_layer_48": h["n_layer"] == N_LAYER,
                "f_n_rot_k_128": h["n_rot_k"] == N_ROT_K,
                "f_n_rot_v_64": h["n_rot_v"] == N_ROT_V,
                "f_k_type_q8_0": h["k_type"] == K_TYPE,
                "f_k_row_1088": h["k_row"] == K_ROW,
                "f_v_row_1088": h["v_row"] == K_ROW,
                "f_consumed_to_eof": h["consumed_to_eof"],
                "f_v_trans_0": h["v_trans"] == 0,
            }
            rec["checks"] = checks
            if not all(checks.values()):
                bad = [k for k, v in checks.items() if not v]
                raise SystemExit("STOP %s: assertions failed %s | measured size=%d n=%d "
                                 "backed-out (header,cell)=(%d,%d) derived=(%d,%d)"
                                 % (name, bad, h["size"], h["n_tokens"],
                                    h["size"] - CELL14 * h["n_tokens"], CELL14,
                                    HDR14, CELL14))
            meta["blocks"].append(rec)
            print("%-22s cells=%-3d content=%-3d first=%d size=%-9d header=%d nl=%d "
                  "nrot=%d/%d k=%d/%d v=%d/%d eof=%s sha16=%s"
                  % (name, h["n_tokens"], rec["content_tokens"], h["first_token"],
                     h["size"], derived_hdr, h["n_layer"], h["n_rot_k"], h["n_rot_v"],
                     h["k_type"], h["k_row"], h["v_type"], h["v_row"],
                     h["consumed_to_eof"], h["sha256"][:16]))
    finally:
        eng.close()

    json.dump(meta, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2,
              default=str)
    print("WROTE", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
