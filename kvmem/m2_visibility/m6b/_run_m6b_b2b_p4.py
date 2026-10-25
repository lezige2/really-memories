# -*- coding: utf-8 -*-
"""M6b B2b P4：完整文件尾部追加垃圾，load 会不会仍接受（malformed tail-extra）。

判据：任一变体 `load > 0` ⇒ **未通过**（尾部垃圾被接受，malformed-file 可注入）；
全部 `-1` ⇒ tail-extra 变体也拒，B2b scope 可扩到 tail-extra（仍不是全闭环）。

对象：block（profile.kvmem，14B 引擎）、chat（live.chat.kvmem，7B 引擎）。
每例从源重新复制再追加；只 load、不 decode；只写 m6b/out/tmp/。

用法：PY -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2b_p4.py --mode p4
产物：m6b/out/M6B-B2B-P4.json；台账：m6b/LANDED-m6b-b2b-p4.json
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
import traceback

ROOT = r"D:\llama-mem"
M6B = os.path.join(ROOT, "kvmem", "m2_visibility", "m6b")
OUT = os.path.join(M6B, "out")
TMP = os.path.join(OUT, "tmp")
TOOLS = os.path.join(ROOT, "tools")
BLOCK_SRC = os.path.join(ROOT, "kvmem", "blocks", "profile.kvmem")
CHAT_SRC = os.path.join(ROOT, "kvmem", "sessions", "live.chat.kvmem")
MODEL_14B = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
MODEL_7B = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
ART = os.path.join(OUT, "M6B-B2B-P4.json")
LEDGER = os.path.join(M6B, "LANDED-m6b-b2b-p4.json")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def sha16f(p):
    return sha256(open(p, "rb").read())[:16]


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16f(p), "bytes": os.path.getsize(p)}


def cases_for(src_bytes):
    rng = random.Random(1234)
    rand = bytes(rng.randrange(256) for _ in range(1024))
    return [
        {"name": "control_full", "append": b"", "append_desc": "完整原文件（控制）"},
        {"name": "tail_zero_1kb", "append": b"\x00" * 1024, "append_desc": "+1KB 零字节"},
        {"name": "tail_random_1kb", "append": rand,
         "append_desc": "+1KB 随机字节（seed=1234）", "append_sha256": sha256(rand)},
    ]


def run_arm(arm, src, seq, candidates):
    sys.path.insert(0, TOOLS)
    import chat as C
    src_bytes = open(src, "rb").read()
    rows = []
    out = {"arm": arm, "source": os.path.relpath(src, ROOT).replace("\\", "/"),
           "source_bytes": len(src_bytes), "source_sha256": sha256(src_bytes),
           "seq": seq, "engine": None, "control": None, "rows": rows,
           "error": None}
    for model in candidates:
        if not os.path.isfile(model):
            continue
        eng = None
        try:
            eng = C.KVEngine(model, n_ctx=C.N_CTX, n_seq=C.N_SEQ, gpu=99, kv="q8_0")
            armdir = os.path.join(TMP, "p4_%s" % arm)
            os.makedirs(armdir, exist_ok=True)
            # 先验证完整文件控制
            ctl = os.path.join(armdir, "control.bin")
            with open(ctl, "wb") as fh:
                fh.write(src_bytes)
            eng.reset(seq)
            try:
                rc = int(eng.load(seq, ctl))
                ex = None
            except Exception as e:                            # noqa: BLE001
                rc, ex = -99, "%s: %s" % (type(e).__name__, e)
            out["control"] = {"bytes": len(src_bytes), "load_rc": rc, "exception": ex,
                              "n_tokens": int(eng.n_tokens(seq)) if rc > 0 else None}
            if rc <= 0:
                eng.close()
                eng = None
                continue
            out["engine"] = {"model": model, "model_bytes": os.path.getsize(model),
                             "control_rc": rc}
            for c in cases_for(src_bytes):
                p = os.path.join(armdir, c["name"] + ".bin")
                payload = src_bytes + c["append"]
                with open(p, "wb") as fh:
                    fh.write(payload)
                eng.reset(seq)
                try:
                    r = int(eng.load(seq, p))
                    ex = None
                except Exception as e:                        # noqa: BLE001
                    r, ex = -99, "%s: %s" % (type(e).__name__, e)
                nt = int(eng.n_tokens(seq)) if r > 0 else None
                row = {"case": c["name"], "append": c["append_desc"],
                       "append_bytes": len(c["append"]), "file_bytes": len(payload),
                       "load_rc": r, "n_tokens": nt, "exception": ex}
                if "append_sha256" in c:
                    row["append_sha256"] = c["append_sha256"]
                rows.append(row)
            break
        except Exception:                                     # noqa: BLE001
            out["error"] = traceback.format_exc()
        finally:
            if eng is not None:
                try:
                    eng.close()
                except Exception:                             # noqa: BLE001
                    pass
    variants = [r for r in rows if r["case"] != "control_full"]
    bad = [{"case": r["case"], "load_rc": r["load_rc"], "n_tokens": r["n_tokens"]}
           for r in variants if r["load_rc"] > 0]
    out["summary"] = {
        "engine_ok": out["engine"] is not None,
        "control_full_rc": out["control"]["load_rc"] if out["control"] else None,
        "n_variants": len(variants),
        "variant_load_rc": {r["case"]: r["load_rc"] for r in variants},
        "accepted_variants": bad,
        "accepted_count": len(bad),
        "verdict": ("未通过（tail-extra 被接受）" if bad else
                    ("未接上（tail-extra 也被拒）" if out["engine"] else "未做（装置不成立）")),
    }
    return out


def main():
    global OUT, TMP, ART, LEDGER
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["p4"])
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    OUT = os.path.abspath(args.out)
    TMP = os.path.join(OUT, "tmp")
    ART = os.path.join(OUT, "M6B-B2B-P4.json")
    LEDGER = os.path.join(M6B, "LANDED-m6b-b2b-p4.json")
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(os.path.join(OUT, "_logs"), exist_ok=True)
    artifact = {
        "schema": "m6b_b2b_p4_v1",
        "task": "M6b B2b-adjacent：完整文件尾部追加垃圾是否被 load 接受（tail-extra）",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "assertion": "任一变体 load>0 ⇒ 未通过（尾部垃圾被接受）；全部 -1 ⇒ 该变体也被拒",
        "prereg": "M6B-B2B 补充（inspector：llama-context.cpp:3602 不查 file.tell()==file.size()）",
        "setup": {"tmp_root": os.path.relpath(TMP, ROOT).replace("\\", "/"),
                  "per_case": "每例从源重新复制 + 追加；只 load 不 decode",
                  "control": "完整原文件先验 load>0 才继续（否则装置不成立）"},
        "arms": {},
        "not_judged": {"B2a": "另单", "B3": "另单", "n_tokens_ne_cell_count": "未测"},
        "discipline": {"engine_changed": False, "rebuild": False,
                       "real_blocks_written": False, "sessions_written": False,
                       "zero_decode": True},
        "no_self_sha": True,
    }
    try:
        artifact["arms"]["block"] = run_arm("block", BLOCK_SRC, 1, [MODEL_14B, MODEL_7B])
        artifact["arms"]["chat"] = run_arm("chat", CHAT_SRC, 0, [MODEL_7B, MODEL_14B])
    finally:
        with open(ART, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(artifact, fh, ensure_ascii=False, indent=1)
    sums = {a: artifact["arms"][a]["summary"] for a in ("block", "chat")}
    any_bad = any(s["accepted_count"] > 0 for s in sums.values())
    engine_ok = all(s["engine_ok"] for s in sums.values())
    verdict = ("未通过（tail-extra 被接受）" if any_bad else
               ("未接上（tail-extra 也被拒）" if engine_ok else "未做（装置不成立）"))
    ledger = {
        "schema": "landed_m6b_b2b_p4_v1",
        "task": artifact["task"],
        "at": artifact["at"],
        "assertion": artifact["assertion"],
        "artifact": ent(ART),
        "code_sha16": ent(os.path.abspath(__file__)),
        "engine_model_per_arm": {
            "block": "14B（profile.kvmem 是 14B 几何）",
            "chat": "7B（live.chat.kvmem 是 7B 几何）"},
        "arms": {a: {"source": artifact["arms"][a]["source"],
                     "source_bytes": artifact["arms"][a]["source_bytes"],
                     "engine": artifact["arms"][a]["engine"],
                     "control": artifact["arms"][a]["control"],
                     "rows": artifact["arms"][a]["rows"],
                     "summary": artifact["arms"][a]["summary"]}
                 for a in ("block", "chat")},
        "four_state": {"B2b_tail_extra": verdict},
        "not_judged": artifact["not_judged"],
        "discipline": artifact["discipline"],
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("artifact:", ART, os.path.getsize(ART), sha16f(ART))
    print("ledger:  ", LEDGER, os.path.getsize(LEDGER), sha16f(LEDGER))
    for a in ("block", "chat"):
        s = sums[a]
        print(a, "control_rc=%s" % s["control_full_rc"],
              "variants=%s" % s["variant_load_rc"],
              "accepted=%s" % s["accepted_count"],
              "verdict=%s" % s["verdict"])
    print("P4 verdict:", verdict)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        sys.exit(7)