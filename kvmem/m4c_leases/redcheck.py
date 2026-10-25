# -*- coding: utf-8 -*-
"""M4-C 红套件：先造红，再让绿。

判据（site=2, place-slots）：
  删掉站点的 leases.reset(...) ⇒ 同一引擎上放置两遍 ⇒ load_into 叠在旧 cell 上
  ⇒ 见证者 _m4c_witness_cells 读到的 n_tokens 应为 2n（期望 n）⇒ 红。

本脚本不改生产文件：它把 tools/chat.py 读进内存/临时副本，**只删目标那一行**，
其余字节不动，然后 import 这个副本并驱动真实函数 _place_slots。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\llama-mem"
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

SRC = os.path.join(TOOLS, "chat.py")
SITES = {
    1: 'leases.reset(i, site="chat.place.fresh")',
    2: 'leases.reset(i, site="slots.place.fresh")',
    3: 'leases.reset(seq, site="m1.unmount.after_detach")',
    4: 'leases.reset(seq, site="m1.mount.before_load")',
}


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def provenance(extra=None):
    p = {"chat_py_sha16": sha16(SRC),
         "redcheck_sha16": sha16(os.path.abspath(__file__)),
         "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if extra:
        p.update(extra)
    return p


def make_variant(site):
    """删掉站点 site 的那一行（换成注释），返回副本路径与删掉的行原文。"""
    text = open(SRC, encoding="utf-8").read()
    lines = text.split("\n")
    needle = SITES[site]
    hits = [i for i, t in enumerate(lines) if needle in t]
    if len(hits) != 1:
        raise SystemExit("STOP: site %d 命中 %d 行（应恰好 1）" % (site, len(hits)))
    i = hits[0]
    removed = lines[i]
    lines[i] = removed.split("leases.reset")[0] + "pass  # M4C-DELETED-SITE-%d" % site
    tmpdir = os.path.join(HERE, "tmp")
    os.makedirs(tmpdir, exist_ok=True)
    path = os.path.join(HERE, "tmp", "variants", "chat_site%d.py.snap" % site)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return path, removed, i + 1


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=int, default=2)
    ap.add_argument("--mode", choices=("red", "green"), default="red")
    ap.add_argument("--passes", type=int, default=2)
    args = ap.parse_args()

    if args.mode == "red":
        path, removed, lineno = make_variant(args.site)
        variant_sha = sha16(path)
    else:
        path, removed, lineno = SRC, None, None
        variant_sha = sha16(SRC)

    chat = load_module(path, "chat_m4c_%s_%d" % (args.mode, args.site))
    eng = chat.KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
    con = chat.ms.connect(chat.DB)
    rows = chat._rows_for_session(con, limit=2)
    con.close()

    rec = {"schema": "m4c_red_v1", "site": args.site, "mode": args.mode,
           "scenario": "同一引擎上连续放置 %d 遍（_place_slots 真实函数）" % args.passes,
           "deleted_line": removed, "deleted_line_no": lineno,
           "variant_sha16": variant_sha, "passes": [],
           "provenance": provenance({"variant_sha16": variant_sha})}
    try:
        for p in range(1, args.passes + 1):
            step = {"pass": p, "blocks": []}
            blocks = chat._place_slots(eng, rows)
            for b in blocks:
                step["blocks"].append({"seq": b["seq"], "name": b["name"],
                                       "n_tokens_declared": b["n_tokens"],
                                       "n_tokens_read": int(eng.n_tokens(b["seq"])),
                                       "pos_max_read": int(eng.pos_max(b["seq"])),
                                       "lo": b["lo"], "hi": b["hi"]})
            rec["passes"].append(step)
        rec["witness"] = "GREEN（未红）"
        rec["exit"] = 0
    except SystemExit as exc:
        rec["witness"] = "RED（见证者 die）"
        rec["die_message"] = str(exc.code) if not isinstance(exc.code, int) else "exit(%s)" % exc.code
        rec["exit"] = exc.code if isinstance(exc.code, int) else 1
    finally:
        rec["at_exit"] = {str(s): {"n_tokens": int(eng.n_tokens(s)),
                                   "pos_max": int(eng.pos_max(s))} for s in (1, 2)}
        out = os.path.join(HERE, "out", "M4C-%s-SITE%d.json" % (args.mode.upper(), args.site))
        json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        print("wrote", out)
        print(json.dumps({k: rec[k] for k in ("mode", "site", "witness", "at_exit")},
                         ensure_ascii=False))
    try:
        eng.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
