# -*- coding: utf-8 -*-
"""M6b B2a 红证（save 非原子）：已有合法 .kvmem 被 save 覆盖，在写窗口内进程猝死。

只做 B2a，不判 B2b（半文件能否被 load 识别，另单）。

构造（全部在 m6b/out/tmp/ 副本上；不碰 kvmem/blocks、kvmem/sessions、不写已签产物）：
  1. 子进程载入 14B 引擎（save-only，不 decode；用的就是产品 DLL kvshim_vk.dll）
  2. `load(1, profile.kvmem)`（50 cells）→ 正常 save 到 final_ref.kvmem 记录 final_sha/size
  3. 目标 P 先放 project.kvmem 副本（old=3,761,892 字节，合法块）
  4. 子进程对 P 调 `save(1, P)`；watcher 线程忙轮询 P 的 size，一看到 `size < old_size`
     （"wb" 打开即截断的窗口）就立刻 `os._exit(137)`（等价 OOM/进程死，不是真 OOM）
  5. 父进程在猝死后读取 P：existed / size_after / sha_after / truncated
     （父进程另有 watchdog 记录 min_size_seen；只有子进程 watcher 失效时才由父进程 kill）

不做的事：不判半文件 load（B2b）、不改 tools/、不改 llama.cpp、不 rebuild、不碰真库。

用法：
  PY -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2.py --mode p0
  产物：kvmem/m2_visibility/m6b/out/M6B-B2A-RED.json
  台账：kvmem/m2_visibility/m6b/LANDED-m6b-b2a.json
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback

ROOT = r"D:\llama-mem"
M6B = os.path.join(ROOT, "kvmem", "m2_visibility", "m6b")
OUT = os.path.join(M6B, "out")
TMP = os.path.join(OUT, "tmp")
BLOCKS = os.path.join(ROOT, "kvmem", "blocks")
PROFILE = os.path.join(BLOCKS, "profile.kvmem")
PROJECT = os.path.join(BLOCKS, "project.kvmem")
SESSIONS = os.path.join(ROOT, "kvmem", "sessions")
CHAT_ART = os.path.join(OUT, "M6B-B2A-CHAT-RED.json")
BLOCK_ART = os.path.join(OUT, "M6B-B2A-RED.json")
SESSIONS = os.path.join(ROOT, "kvmem", "sessions")
CHAT_ART = os.path.join(OUT, "M6B-B2A-CHAT-RED.json")
BLOCK_ART = os.path.join(OUT, "M6B-B2A-RED.json")
MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
TOOLS = os.path.join(ROOT, "tools")
M6B_ART = os.path.join(OUT, "M6B-B2A-RED.json")
LEDGER = os.path.join(M6B, "LANDED-m6b-b2a.json")
PY = sys.executable

# 静态证据：file:line + 该行必须含的 token
STATIC_SITES = [
    ("tools/kvshim.cpp", 561, "kvshim_save", "kvshim_save 入口"),
    ("tools/kvshim.cpp", 565, "llama_state_seq_save_file", "直接调 save_file，无 temp/rename/fsync"),
    ("llama.cpp/src/llama-context.cpp", 3609, '"wb"', "llama_file(filepath, \"wb\") —— 打开即截断"),
    ("tools/memory_source.py", 349, "os.path.join(blocks_dir", "产品直写最终块路径"),
    ("tools/memory_source.py", 350, "eng.save", "块 save 无 temp/rename"),
    ("tools/session_state.py", 229, "eng.save", "chat 状态直写最终路径"),
    ("tools/session_state.py", 251, 'path + ".tmp"', "同函数 manifest 反而 tmp"),
    ("tools/session_state.py", 254, "os.replace", "manifest 原子替换"),
]


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


def static_evidence():
    rows = []
    for rel, line, token, note in STATIC_SITES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        ok_line = 1 <= line <= len(lines)
        text = lines[line - 1].strip() if ok_line else ""
        rows.append({"file": rel, "line": line, "note": note, "line_text": text[:200],
                     "token": token, "token_ok": bool(ok_line and token in text),
                     "bad": not (ok_line and token in text)})
    # F1 的"无 temp/rename/fsync/锁"要在 kvshim_save 函数体内成立，而不是只 grep 全文
    src = open(os.path.join(TOOLS, "kvshim.cpp"), encoding="utf-8",
               errors="replace").read().splitlines()
    start = next(i for i, l in enumerate(src) if "kvshim_save" in l and "KVSHIM_API" in l)
    end = next(i for i in range(start + 1, len(src))
               if src[i].startswith("}") and "return" in src[i - 1])
    body = "\n".join(src[start:end + 1])
    atoms = ("lock", "temp", "rename", "replace", "fsync", "FlushFile")
    hits = {a: body.lower().count(a.lower()) for a in atoms}
    return {"sites": rows, "bad": sum(1 for r in rows if r["bad"]),
            "kvshim_save_span": [start + 1, end + 1],
            "atomicity_atom_hits_in_save": hits,
            "no_atomicity_atom": sum(hits.values()) == 0}


# ---------------------------------------------------------------- child

def child_main(args):
    """子进程：载引擎、正常 save 一次做基线、然后对已存在目标 save 并等待被 watcher 猝死。"""
    sys.path.insert(0, TOOLS)
    import chat as C                                            # noqa: E402

    target, ref, killinfo = args.target, args.ref, args.killinfo
    arm = args.arm
    seq = 0 if arm == "chat" else 1
    old_size = os.path.getsize(target)
    info = {"child_pid": os.getpid(), "old_size": old_size,
            "attempts": [], "normal_save": None, "completed_save": False}
    try:
        t0 = time.time()
        eng = C.KVEngine(MODEL, n_ctx=C.N_CTX, n_seq=C.N_SEQ, gpu=99, kv="q8_0")
        info["engine_load_ms"] = round((time.time() - t0) * 1000, 1)
        info["gpu_dll"] = os.path.basename(eng.lib._name) if hasattr(eng.lib, "_name") else "?"
        n = int(eng.load(seq, PROFILE))
        info["load_profile_n"] = n
        info["arm"] = arm
        info["seq"] = seq
        t0 = time.time()
        nb = int(eng.save(seq, ref))
        info["normal_save"] = {"seq": seq, "arm": arm,
                               "path": os.path.relpath(ref, ROOT).replace("\\", "/"),
                               "returned": nb, "bytes": os.path.getsize(ref),
                               "sha256": sha256(ref), "ms": round((time.time() - t0) * 1000, 1)}
        info["completed_save"] = True
        # 先落基线（子进程若在写目标时猝死，父进程仍能读到 final_sha/size）
        with open(args.child_info, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(info, fh, ensure_ascii=False, indent=1)

        def watcher(attempt):
            """忙轮询目标文件：wb 打开后 size 会掉到 < old_size，立即留证并猝死。"""
            while True:
                try:
                    size = os.path.getsize(target)
                except OSError:
                    size = -1
                if size < old_size:
                    try:
                        with open(killinfo, "w", encoding="utf-8") as fh:
                            json.dump({"observed_size": size, "old_size": old_size,
                                       "attempt": attempt, "child_pid": os.getpid(),
                                       "fired_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                       "elapsed_in_attempt_ms":
                                           round((time.time() - attempt_t0) * 1000, 2)},
                                      fh, ensure_ascii=False)
                            fh.flush()
                            os.fsync(fh.fileno())
                    except Exception:                       # noqa: BLE001
                        pass
                    os._exit(137)                           # 等价进程死/OOM
                time.sleep(0)

        for attempt in range(1, args.max_attempts + 1):
            shutil.copyfile(PROJECT, target)                # 每次恢复成合法旧文件
            attempt_t0 = time.time()
            th = threading.Thread(target=watcher, args=(attempt,), daemon=True)
            th.start()
            nb = int(eng.save(seq, target))
            attempt_t0 = time.time()
            th.join(timeout=0)
            size = os.path.getsize(target)
            info["attempts"].append({"attempt": attempt, "returned": nb, "size": size,
                                     "completed": True})
            if nb <= 0 or size < old_size:
                info["anomaly_without_watcher"] = {"returned": nb, "size": size}
        eng.close()
        info["note"] = "all attempts completed before watcher fired"
        with open(args.child_info, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(info, fh, ensure_ascii=False, indent=1)
        return 0
    except Exception:                                       # noqa: BLE001
        info["error"] = traceback.format_exc()
        with open(args.child_info, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(info, fh, ensure_ascii=False, indent=1)
        return 5


# ---------------------------------------------------------------- parent

def newest_chat_file():
    rows = []
    for name in os.listdir(SESSIONS):
        if name.endswith(".chat.kvmem"):
            p = os.path.join(SESSIONS, name)
            rows.append((os.path.getmtime(p), p))
    if not rows:
        raise RuntimeError("no .chat.kvmem under %s" % SESSIONS)
    return max(rows)[1]


def p0(args):
    arm = args.arm
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(os.path.join(OUT, "_logs"), exist_ok=True)
    target = os.path.join(TMP, "target.kvmem")
    ref = os.path.join(TMP, ("final_ref_chat.kvmem" if arm == "chat" else "final_ref.kvmem"))
    killinfo = os.path.join(TMP, "killinfo.json")
    child_info = os.path.join(TMP, "child_info.json")
    for p in (target, ref, killinfo, child_info):
        if os.path.exists(p):
            os.remove(p)
    if arm == "chat":
        src_chat = newest_chat_file()
        shutil.copyfile(src_chat, target)
        chat_origin = {"source": os.path.relpath(src_chat, ROOT).replace("\\", "/"),
                       "source_sha256": sha256(src_chat),
                       "source_bytes": os.path.getsize(src_chat),
                       "source_mtime": time.strftime("%Y-%m-%dT%H:%M:%S",
                                                     time.localtime(os.path.getmtime(src_chat)))}
    else:
        shutil.copyfile(PROJECT, target)
        chat_origin = None
    before = {"sha256": sha256(target), "bytes": os.path.getsize(target),
              "existed": os.path.isfile(target)}

    cmd = [PY, "-X", "utf8", os.path.abspath(__file__), "--mode", "child", "--arm", arm,
           "--target", target, "--ref", ref, "--killinfo", killinfo,
           "--child-info", child_info, "--max-attempts", str(args.max_attempts)]
    log = open(os.path.join(OUT, "_logs", "b2a_child.log"), "w", encoding="utf-8")
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    parent_min = {"size": before["bytes"], "at_ms": None}
    stop = False

    def watchdog():
        nonlocal stop
        while not stop and proc.poll() is None:
            try:
                size = os.path.getsize(target)
            except OSError:
                size = -1
            if size < parent_min["size"]:
                parent_min["size"] = size
                parent_min["at_ms"] = round((time.time() - t0) * 1000, 2)
            time.sleep(0.0002)

    wd = threading.Thread(target=watchdog, daemon=True)
    wd.start()
    rc = proc.wait()
    stop = True
    wd.join(timeout=0.5)
    log.close()

    after_size = os.path.getsize(target)
    after_sha = sha256(target)
    kill = None
    if os.path.isfile(killinfo):
        kill = json.load(open(killinfo, encoding="utf-8"))
    child = json.load(open(child_info, encoding="utf-8")) if os.path.isfile(child_info) else None
    final = child.get("normal_save") if child else None
    final_size = final["bytes"] if final else None
    truncated = after_size < before["bytes"]
    artifact = {
        "schema": "m6b_b2a_red_v1",
        "arm": arm,
        "task": "task-38 M6b B2a（save 非原子）红证：只判 B2a，不判 B2b",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "assertion": "目标路径 P 上已有合法 .kvmem；save 进程在返回前终止 ⇒ P 的旧内容不可恢复，"
                     "最终留下 0 ≤ size < old_size 的文件",
        "setup": {
            "tmp_root": os.path.relpath(TMP, ROOT).replace("\\", "/"),
            "target_preloaded_from": (("真实 chat 文件副本: %s" % chat_origin["source"])
                                      if chat_origin else
                                      "kvmem/blocks/project.kvmem（只读复制）"),
            "source_seq_data": ("kvmem/blocks/profile.kvmem load 到 seq0（合成 chat 状态；"
                                "调用形态 = session_state.py:229 eng.save(0, chat_file)）"
                                if arm == "chat" else
                                "kvmem/blocks/profile.kvmem load 到 seq1（只读）"),
            "chat_origin": chat_origin,
            "engine": {"model": MODEL, "n_ctx": 8192, "n_seq": 8, "gpu_layers": 99,
                       "dll": "kvshim_vk.dll（产品 DLL；save-only，不 decode）"},
            "note": "所有写都落 m6b/out/tmp/；不碰 kvmem/blocks、kvmem/sessions、不写已签产物",
        },
        "before": {**before, "path": os.path.relpath(target, ROOT).replace("\\", "/")},
        "after": {"sha256": after_sha, "sha16": after_sha[:16], "bytes": after_size,
                  "exists": os.path.isfile(target)},
        "final_ref": ({"path": final["path"], "sha256": final["sha256"],
                       "sha16": final["sha256"][:16], "bytes": final["bytes"],
                       "save_ms": final["ms"]} if final else None),
        # 顶层扁平读数（交件要求的字段名）
        "before_sha": before["sha256"],
        "before_sha16": before["sha256"][:16],
        "after_sha": after_sha,
        "after_sha16": after_sha[:16],
        "size_before": before["bytes"],
        "size_after": after_size,
        "final_size": final_size,
        "existed": before["existed"],
        "truncated": truncated,
        "readings": {
            "existed": before["existed"],
            "truncated": truncated,
            "size_after_lt_final": (after_size < final_size) if final_size else None,
            "sha_after_ne_before": after_sha != before["sha256"],
        },
        "kill_point": {
            "method": "watcher 线程忙轮询目标 size；见 size < old_size（wb 截断窗口）⇒ 写 killinfo "
                      "后 os._exit(137)（等价 OOM/进程死，不是真 OOM）",
            "watcher_fired": kill is not None,
            "observed_size": (kill or {}).get("observed_size"),
            "attempt": (kill or {}).get("attempt"),
            "elapsed_in_attempt_ms": (kill or {}).get("elapsed_in_attempt_ms"),
            "parent_min_size_seen": parent_min["size"],
            "parent_min_size_at_ms": parent_min["at_ms"],
            "parent_killed": False,
            "child_exit_code": rc,
            "child_attempts": (child or {}).get("attempts"),
            "child_error": (child or {}).get("error"),
        },
        "verdict": {
            "B2a_red": bool(before["existed"] and truncated and after_size < (final_size or 10**18)
                            and after_sha != before["sha256"]),
            "rule": "红 = existed 且 size_after<final_size 且 sha_after≠sha_old；"
                    "本单不判 load（B2b 另单）",
        },
        "static": static_evidence(),
        "not_judged": {"B2b_half_file_load": "本单一律不判（另单）",
                       "B3_concurrency": "不在本单"},
        "discipline": {"engine_changed": False, "rebuild": False,
                       "real_blocks_written": False, "sessions_written": False},
        "no_self_sha": True,
    }
    assert artifact["static"]["bad"] == 0, artifact["static"]["bad"]
    art_path = CHAT_ART if arm == "chat" else BLOCK_ART
    with open(art_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(artifact, fh, ensure_ascii=False, indent=1)
    return 0 if artifact["verdict"]["B2a_red"] else 4


def ledger_main(args):
    """从 block/chat 两份读数重建台账（arms 两条；四态措辞按 inspector 口径）。"""
    paths = {"block": BLOCK_ART, "chat": CHAT_ART}
    arts = {}
    for arm, path in paths.items():
        if not os.path.isfile(path):
            raise RuntimeError("missing artifact for arm %s: %s" % (arm, path))
        arts[arm] = json.load(open(path, encoding="utf-8"))
    script = os.path.abspath(__file__)
    code = {"path": os.path.relpath(script, ROOT).replace("\\", "/"),
            "sha16": sha16(script), "bytes": os.path.getsize(script)}
    ledger = {
        "schema": "landed_m6b_b2a_v2",
        "task": "task-38 M6b B2a（save 非原子）红证：block 臂 + 产品 chat 臂",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifacts": {arm: ent(p) for arm, p in paths.items()},
        "code_sha16": code,
        "arms": {arm: {"artifact": ent(paths[arm]),
                       "before_sha": arts[arm]["before_sha"],
                       "after_sha": arts[arm]["after_sha"],
                       "size_before": arts[arm]["size_before"],
                       "size_after": arts[arm]["size_after"],
                       "final_size": arts[arm]["final_size"],
                       "existed": arts[arm]["existed"],
                       "truncated": arts[arm]["truncated"],
                       "kill_point": arts[arm]["kill_point"],
                       "chat_origin": arts[arm]["setup"].get("chat_origin")}
                 for arm in paths},
        "four_state": {"B2a": "可达（未修；红证已复现）"},
        "fix_candidate": "temp+rename 或 fsync+rename（未实施，单独立项）",
        "static": {"bad": arts["block"]["static"]["bad"],
                   "kvshim_save_span": arts["block"]["static"]["kvshim_save_span"],
                   "atomicity_atom_hits_in_save":
                       arts["block"]["static"]["atomicity_atom_hits_in_save"],
                   "sites": arts["block"]["static"]["sites"]},
        "discipline": {"engine_changed": False, "rebuild": False,
                       "real_blocks_written": False, "sessions_written": False},
        "not_judged": arts["block"]["not_judged"],
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("ledger:", LEDGER, os.path.getsize(LEDGER), sha16(LEDGER))
    for arm, path in paths.items():
        print(" %-5s artifact=%s sha16=%s before=%d after=%d final=%d existed=%s truncated=%s"
              % (arm, os.path.basename(path), sha16(path), arts[arm]["size_before"],
                 arts[arm]["size_after"], arts[arm]["final_size"], arts[arm]["existed"],
                 arts[arm]["truncated"]))
    return 0 if all(a["truncated"] and a["existed"] for a in arts.values()) else 4


def main():
    global OUT, TMP, M6B_ART, LEDGER, CHAT_ART, BLOCK_ART
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["p0", "chat", "child", "ledger"])
    ap.add_argument("--arm", default=None, choices=["block", "chat"])
    ap.add_argument("--blocks", default=BLOCKS)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--target")
    ap.add_argument("--ref")
    ap.add_argument("--killinfo")
    ap.add_argument("--child-info")
    ap.add_argument("--max-attempts", type=int, default=3)
    args = ap.parse_args()
    if args.mode == "child":
        args.arm = args.arm or "block"
        return child_main(args)
    OUT = os.path.abspath(args.out)
    TMP = os.path.join(OUT, "tmp")
    M6B_ART = os.path.join(OUT, "M6B-B2A-RED.json")
    CHAT_ART = os.path.join(OUT, "M6B-B2A-CHAT-RED.json")
    BLOCK_ART = os.path.join(OUT, "M6B-B2A-RED.json")
    if args.mode == "ledger":
        return ledger_main(args)
    args.arm = args.arm or ("chat" if args.mode == "chat" else "block")
    return p0(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:                                       # noqa: BLE001
        traceback.print_exc()
        sys.exit(7)