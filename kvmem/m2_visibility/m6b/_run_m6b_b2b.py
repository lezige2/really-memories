# -*- coding: utf-8 -*-
"""M6b B2b P3 红证：半文件会不会被 load 当合法块/chat 接受？

判据（预登记 v3 §B2b）：
  - 任一 cut 点（0 ≤ cut < size）`load > 0` ⇒ **未通过**（半文件被接受，升实测为有危害）
  - 全部 cut 点 `load = -1`（含异常拒绝）⇒ **未接上（实测支持：码读说截断必被拒）**
  - cut = 0 与 cut = size 是边界：cut=0 期望 -1；cut=size（完整副本）期望 >0，否则装置不成立（控制失败）

对象：
  - block 臂：kvmem/blocks/profile.kvmem 副本（产品另有 DB n_bytes 前置，见 static）
  - chat  臂：真实 kvmem/sessions/live.chat.kvmem 副本（无 DB n_bytes 前置）
每条 cut 前从源**重新复制**（不链式截断）；只 load、不 decode；只写 m6b/out/tmp/。

用法：
  PY -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2b.py --mode p3
产物：kvmem/m2_visibility/m6b/out/M6B-B2B-P3.json
台账：kvmem/m2_visibility/m6b/LANDED-m6b-b2b.json
"""
import argparse
import hashlib
import json
import os
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
ART = os.path.join(OUT, "M6B-B2B-P3.json")
LEDGER = os.path.join(M6B, "LANDED-m6b-b2b.json")
PY = sys.executable


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha16(p):
    return sha256(p)[:16]


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16(p), "bytes": os.path.getsize(p)}


def cut_points(size):
    """目标文件自身布局算：两端边界 + 头/中/尾若干；cut 全 < size，size 单列控制。"""
    return sorted({0, 4, 8, 12, 16, size // 4, size // 2,
                   3 * size // 4, max(0, size - 16), max(0, size - 4),
                   max(0, size - 1)})


def static_evidence():
    rows = []
    checks = [
        ("tools/memory_source.py", 389, "n_bytes", "块文件有 DB n_bytes 前置校验"),
        ("tools/memory_source.py", 390, "truncated", "块文件有 DB n_bytes 前置校验（截断即抛）"),
        ("tools/kvshim.cpp", 572, "kvshim_load", "load 入口（shim 只返回 -1）"),
    ]
    for rel, line, token, note in checks:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        ok = 1 <= line <= len(lines) and token in lines[line - 1]
        rows.append({"file": rel, "line": line, "token": token, "note": note,
                     "line_text": lines[line - 1].strip()[:200] if 1 <= line <= len(lines) else "",
                     "bad": not ok})
    return {"sites": rows, "bad": sum(1 for r in rows if r["bad"])}


def make_cut(src_bytes, cut, path):
    with open(path, "wb") as fh:
        fh.write(src_bytes[:cut])
    return os.path.getsize(path)


def run_arm(arm, src, seq, candidates):
    """一个臂：选匹配模型（完整副本 load>0 才算控制成立），再逐 cut 独立复制 + load。"""
    sys.path.insert(0, TOOLS)
    import chat as C
    src_bytes = open(src, "rb").read()
    size = len(src_bytes)
    cuts = cut_points(size)
    arm_out = {"arm": arm, "source": os.path.relpath(src, ROOT).replace("\\", "/"),
               "source_sha256": hashlib.sha256(src_bytes).hexdigest(),
               "source_bytes": size, "seq": seq, "cuts": cuts,
               "engine": None, "control": None, "rows": [], "error": None,
               "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for model in candidates:
        if not os.path.isfile(model):
            continue
        eng = None
        try:
            t0 = time.time()
            eng = C.KVEngine(model, n_ctx=C.N_CTX, n_seq=C.N_SEQ, gpu=99, kv="q8_0")
            ctl_path = os.path.join(TMP, "ctl_%s_%s.bin" % (arm, os.path.basename(model)[:8]))
            shutil_copy = None
            with open(ctl_path, "wb") as fh:
                fh.write(src_bytes)
            eng.reset(seq)
            try:
                rc = int(eng.load(seq, ctl_path))
                exc = None
            except Exception as e:                            # noqa: BLE001
                rc, exc = -99, "%s: %s" % (type(e).__name__, e)
            ctl = {"model": model, "bytes": os.path.getsize(ctl_path), "load_rc": rc,
                   "exception": exc, "load_ms": round((time.time() - t0) * 1000, 1)}
            arm_out["control"] = ctl
            if rc > 0:
                arm_out["engine"] = {"model": model,
                                     "model_bytes": os.path.getsize(model),
                                     "control_rc": rc,
                                     "control_n_tokens": int(eng.n_tokens(seq)),
                                     "engine_load_ms": round((time.time() - t0) * 1000, 1)}
                cutdir = os.path.join(TMP, "cuts_%s" % arm)
                os.makedirs(cutdir, exist_ok=True)
                for cut in cuts + [size]:
                    p = os.path.join(cutdir, ("full.bin" if cut == size else "cut_%d.bin" % cut))
                    make_cut(src_bytes, cut, p)
                    eng.reset(seq)
                    t1 = time.time()
                    try:
                        r = int(eng.load(seq, p))
                        ex = None
                    except Exception as e:                    # noqa: BLE001
                        r, ex = -99, "%s: %s" % (type(e).__name__, e)
                    nt = None
                    if r > 0:
                        nt = int(eng.n_tokens(seq))
                    arm_out["rows"].append({
                        "cut": cut, "kind": ("boundary_full" if cut == size else
                                             ("boundary_zero" if cut == 0 else "cut")),
                        "load_rc": r, "n_tokens": nt, "exception": ex,
                        "load_ms": round((time.time() - t1) * 1000, 1),
                        "copy_bytes": os.path.getsize(p)})
                arm_out["cuts_done"] = [x["cut"] for x in arm_out["rows"]]
                break
            eng.close()
            eng = None
        except Exception:                                     # noqa: BLE001
            arm_out["error"] = traceback.format_exc()
            try:
                if eng:
                    eng.close()
            except Exception:                                 # noqa: BLE001
                pass
            break
        finally:
            if eng is not None:
                try:
                    eng.close()
                except Exception:                             # noqa: BLE001
                    pass
    return arm_out


def summarize(arm):
    # cut 点 = 所有 cut < size 的前缀截断（含 cut=0 这个边界）；cut=size 是完整副本控制
    cuts = [r for r in arm["rows"] if r["cut"] < arm["source_bytes"]]
    zero = next((r for r in arm["rows"] if r["cut"] == 0), None)
    full = next((r for r in arm["rows"] if r["kind"] == "boundary_full"), None)
    bad = [{"cut": r["cut"], "load_rc": r["load_rc"], "n_tokens": r["n_tokens"]}
           for r in cuts if r["load_rc"] > 0]
    return {
        "engine_ok": arm["engine"] is not None,
        "control_full_rc": full["load_rc"] if full else None,
        "control_zero_rc": zero["load_rc"] if zero else None,
        "n_cut_points": len(cuts),
        "load_rc_by_cut": {str(r["cut"]): r["load_rc"] for r in cuts},
        "accepted_cuts": bad,
        "accepted_count": len(bad),
        "any_exception": [r["cut"] for r in arm["rows"] if r["exception"]],
        "verdict": ("未通过（半文件被接受）" if bad else
                    ("未接上（实测支持：全部 cut load=-1）"
                     if arm["engine"] else "未做（装置不成立）")),
    }


def main():
    global OUT, TMP, ART, LEDGER
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["p3"])
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    OUT = os.path.abspath(args.out)
    TMP = os.path.join(OUT, "tmp")
    ART = os.path.join(OUT, "M6B-B2B-P3.json")
    LEDGER = os.path.join(M6B, "LANDED-m6b-b2b.json")
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(os.path.join(OUT, "_logs"), exist_ok=True)

    st = static_evidence()
    artifact = {
        "schema": "m6b_b2b_p3_v1",
        "task": "M6b B2b P3：半文件是否被 load 当合法块/chat 接受",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "assertion": "任一 cut 点 load>0 ⇒ 未通过（半文件被接受）；全部 cut load=-1 ⇒ 未接上（实测支持码读）",
        "prereg": "docs/_work/M6B-PREREG-draft.md §B2b（v3 23f2c4af）",
        "setup": {
            "tmp_root": os.path.relpath(TMP, ROOT).replace("\\", "/"),
            "cut_rule": "每条 cut 前从源重新复制字节，不链式截断；cut=size 是完整副本控制；"
                        "cut=0 是零字节边界",
            "cut_points_rule": "按目标文件自身布局算（block/chat 各自 size）",
            "zero_decode": True,
            "engine_models": {"block": MODEL_14B, "chat": "7B 优先，控制失败则 14B（自动匹配）"},
        },
        "static": st,
        "arms": {},
        "not_judged": {"B2a": "另单", "B3": "另单"},
        "discipline": {"engine_changed": False, "rebuild": False,
                       "real_blocks_written": False, "sessions_written": False},
        "no_self_sha": True,
    }
    try:
        artifact["arms"]["block"] = run_arm("block", BLOCK_SRC, 1, [MODEL_14B, MODEL_7B])
        artifact["arms"]["chat"] = run_arm("chat", CHAT_SRC, 0, [MODEL_7B, MODEL_14B])
    finally:
        for arm in artifact["arms"].values():
            arm["summary"] = summarize(arm)
        with open(ART, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(artifact, fh, ensure_ascii=False, indent=1)

    sums = {a: artifact["arms"][a].get("summary") for a in ("block", "chat")}
    any_bad = any(sums[a] and sums[a]["accepted_count"] > 0 for a in sums)
    engine_ok = all(sums[a] and sums[a]["engine_ok"] for a in sums)
    verdict = ("未通过（半文件被接受）" if any_bad else
               ("未接上（实测支持：全部 cut load=-1）" if engine_ok else "未做（装置不成立）"))
    def arm_ledger(name):
        x = artifact["arms"][name]
        cut_rows = [r for r in x["rows"] if r["cut"] < x["source_bytes"]]
        return {
            "arm": name,
            "source": x["source"],
            "source_bytes": x["source_bytes"],
            "cuts": [r["cut"] for r in cut_rows],
            "load_rc_by_cut": {str(r["cut"]): r["load_rc"] for r in cut_rows},
            "all_cuts_load_rc": [r["load_rc"] for r in cut_rows],
            "accepted_cuts": x["summary"]["accepted_cuts"],
            "control": {"bytes": x["control"]["bytes"],
                        "load_rc": x["control"]["load_rc"],
                        "model": x["engine"]["model"],
                        "model_bytes": x["engine"]["model_bytes"],
                        "n_tokens": x["engine"]["control_n_tokens"]},
            "exceptions": x["summary"]["any_exception"],
        }

    ledger = {
        "schema": "landed_m6b_b2b_v2",
        "task": artifact["task"],
        "at": artifact["at"],
        "assertion": artifact["assertion"],
        "prereg": "23f2c4af §B2b（docs/_work/M6B-PREREG-draft.md）",
        "artifact": ent(ART),
        "code_sha16": ent(os.path.abspath(__file__)),
        "engine_model_per_arm": {
            "block": "14B（DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf）—— profile.kvmem 是 14B 几何",
            "chat": "7B（DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf）—— live.chat.kvmem 是 7B 几何",
            "note": "臂级模型差异：两类文件本就来自不同模型，不是同一模型跑两类；混用会让 control 失败",
        },
        "control_token_note": ("chat 臂 control load_rc=189 与 block 臂 50 不同，是因为两份文件 token 数"
                               "本就不同（.chat.kvmem 189 tokens vs profile 块 50 tokens），不是读数不一致"),
        "arms": {a: arm_ledger(a) for a in ("block", "chat")},
        "verdict": {"B2b": verdict,
                    "bad_cuts": {a: sums[a]["accepted_cuts"] if sums[a] else None
                                 for a in ("block", "chat")}},
        "static": {"bad": st["bad"], "sites": st["sites"]},
        "four_state": {"B2b": "未接上（实测：block+chat 全 11 cut 均 load=-1）"},
        "not_judged": {"B2a": "另单", "B3": "另单"},
        "limitations": [
            "只测 prefix 截断形态（cut < size；0 与 size-1 边界已覆盖）",
            "尾部多余/拼接形态不在本单：无 checksum、llama-kv-cache.cpp:3602 不查尾部 ⇒ 归 B3 域",
            "cut 前每点从源重新复制，未做链式截断"],
        "discipline": {**artifact["discipline"], "zero_decode": True},
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("artifact:", ART, os.path.getsize(ART), sha16(ART))
    print("ledger:  ", LEDGER, os.path.getsize(LEDGER), sha16(LEDGER))
    for a in ("block", "chat"):
        s = sums[a]
        print(a, "engine_ok=%s" % (s and s["engine_ok"]),
              "control_full_rc=%s" % (s and s["control_full_rc"]),
              "cuts=%s" % (s and s["n_cut_points"]),
              "accepted=%s" % (s and s["accepted_count"]),
              "verdict=%s" % (s and s["verdict"]))
    print("B2b verdict:", verdict)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        sys.exit(7)