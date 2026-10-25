# -*- coding: utf-8 -*-
"""M7 F2 单元级验收（GPU-free，E2 判据）。

真实 restore_session + 假 eng + 真实 chat 拷贝/尾注入 + 真实 manifest。
- 尾注入：LayoutMismatch，reset_calls==0，load_calls==0，哨兵 n_tokens(0)=7/pos_max(0)=6 不变
  （先 reset 再灌哨兵，不依赖引擎初值）。
- 正常文件：load 成功。
- 老 manifest 4 个（s/live/s_2/bridge）：4/4 load 成功 + stderr `unvalidated:true` JSONL 事件。
- bad_* 3 个：仍 reject。
- variance/o1：只登记 unverifiable（GPU 禁令）。
P4 引擎层对照引用已有 M6B-B2B-P4.json（load_rc>0），本轮不重跑。
"""
import hashlib
import io
import json
import os
import shutil
import sys
import time
from contextlib import redirect_stderr

ROOT = r"D:\llama-mem"
M7 = os.path.join(ROOT, "kvmem", "m2_visibility", "m7")
OUT = os.path.join(M7, "out")
TMP = os.path.join(OUT, "tmp", "unit_f2")
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import memory_source as ms
import session_state as ss

M7B = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
SESS = os.path.join(ROOT, "kvmem", "sessions")
HOST_SAFETY = {
    "bsod_incidents": 3,
    "bugchecks": ["0xA", "0xA", "0x44"],
    "live_kernel": ["141", "141", "144"],
    "gpu": "RX 6750 GRE 10GB / 32.0.21045.1000",
    "policy": "GPU-free evidence; real-machine 14B arm NOT run (host unstable)",
}


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


class FakeEng:
    def __init__(self, seq_n, chat):
        self.seq_n = dict(seq_n)           # seq -> n_tokens after block load
        self.chat = dict(chat)             # chat path -> (n_tokens, chat_end)
        self.tokens = {}
        self.pos = {}
        self.calls = []
        self.reset_calls = []
        self.load_calls = []
        self.saved = []

    def set_sentinel(self, seq, n=7, pos=6):
        self.reset(seq)                    # 先 reset 再灌哨兵
        self.tokens[int(seq)] = n
        self.pos[int(seq)] = pos
        self.reset_calls = []
        self.calls = []

    def reset(self, seq):
        self.reset_calls.append(int(seq))
        self.calls.append(("reset", int(seq)))
        self.tokens[int(seq)] = 0
        self.pos[int(seq)] = -1

    def load_strict(self, seq, path):
        self.calls.append(("load_strict", int(seq), path))
        self.load_calls.append(("load_strict", int(seq), path))
        n, end = self.chat[os.path.abspath(path)]
        self.tokens[int(seq)] = n
        self.pos[int(seq)] = end - 1
        return n

    def load(self, seq, path):
        self.calls.append(("load", int(seq), path))
        self.load_calls.append(("load", int(seq), path))
        n = self.seq_n.get(int(seq), 0)
        self.tokens[int(seq)] = n
        self.pos[int(seq)] = n - 1
        return n

    def n_tokens(self, seq):
        return self.tokens.get(int(seq), 0)

    def pos_max(self, seq):
        return self.pos.get(int(seq), -1)

    def repos_local(self, seq, delta):
        self.calls.append(("repos_local", int(seq), int(delta)))
        self.pos[int(seq)] = self.pos.get(int(seq), -1) + int(delta)
        return self.tokens.get(int(seq), 0)

    def share(self, *a):
        self.calls.append(("share",) + tuple(a))

    def write_at(self, seq, text, pos):
        n = max(1, len(text) // 4)
        self.tokens[int(seq)] = n
        self.pos[int(seq)] = n - 1
        return n

    def save(self, seq, path):
        self.saved.append(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"FAKE" * 64)
        return os.path.getsize(path)

    def close(self):
        pass


def setup_tmp():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP, exist_ok=True)
    # 安全闸：任何意外 rebuild 只能写 tmp，不得触碰产品 kvmem/blocks/
    ms.BLOCKS = os.path.join(TMP, "blocks")
    os.makedirs(ms.BLOCKS, exist_ok=True)
    db = os.path.join(TMP, "chat.db")
    shutil.copyfile(ms.DB, db)
    con = ms.connect(db)
    # 注意：restore_session 内部 ms.load_into(eng,row,seq) 用默认 model_path=14B；
    # DB 行保留真实 14B 指纹，check_compatible 才会通过（假 eng 不读文件内容）。
    # 只把 size 对齐实际文件（真实文件未变，通常已是正确值）。
    rows = con.execute("SELECT source_id,path,n_bytes FROM memory_block").fetchall()
    for sid, path, n_bytes in rows:
        if os.path.exists(path) and os.path.getsize(path) != n_bytes:
            con.execute("UPDATE memory_block SET n_bytes=? WHERE source_id=?",
                        (os.path.getsize(path), sid))
    con.commit()
    return con


def manifest_copy(name, add_bytes, tail=None):
    src = os.path.join(SESS, name + ".json")
    m = json.load(open(src, encoding="utf-8"))
    chat_state = m["chat"]["state"]
    base = os.path.join(TMP, name)
    man, cp = base + ".json", base + ".chat.kvmem"
    shutil.copyfile(os.path.join(SESS, chat_state), cp)
    if tail == "zero":
        with open(cp, "ab") as f:
            f.write(b"\x00" * 1024)
    elif tail == "random":
        with open(cp, "ab") as f:
            f.write(bytes((i * 131 + 7) & 0xff for i in range(1024)))
    original = os.path.getsize(os.path.join(SESS, chat_state))
    if add_bytes:
        m["chat"]["bytes"] = original          # 声明的原尺寸；尾注入后必然不符
    else:
        m["chat"].pop("bytes", None)
    with open(man, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    return man, cp, m, original


def restore_once(con, manifest, chat_path, m, sentinel=False):
    rows = ms.block_rows(con)
    seq_n = {b["slot_id"] + 1: b["n_tokens"] for b in m["placement"]["blocks"]}
    # 用 DB 行的 n_tokens 覆盖：restore 检查的是 manifest n_tokens，两者应一致
    for r in rows:
        pass
    eng = FakeEng(seq_n, {os.path.abspath(chat_path): (m["chat"]["n_tokens"], m["chat"]["end"])})
    if sentinel:
        eng.set_sentinel(0, 7, 6)
    before = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
              "reset_calls": len(eng.reset_calls), "load_calls": len(eng.load_calls)}
    err = io.StringIO()
    exc, report = None, None
    try:
        with redirect_stderr(err):
            report = ss.restore_session(eng, con, manifest, model_path=M7B)
    except Exception as e:                        # noqa: BLE001
        exc = "%s: %s" % (type(e).__name__, e)
    events = []
    for line in err.getvalue().splitlines():
        try:
            d = json.loads(line)
        except Exception:                         # noqa: BLE001
            continue
        if d.get("event") == "chat_unvalidated":
            events.append(d)
    after = {"n_tokens": eng.n_tokens(0), "pos_max": eng.pos_max(0),
             "reset_calls": len(eng.reset_calls), "load_calls": len(eng.load_calls)}
    return {"exc": exc, "report": report, "events": events,
            "before": before, "after": after,
            "reset_called": after["reset_calls"] > 0,
            "load_called": after["load_calls"] > 0,
            "calls": eng.calls}


def main():
    os.makedirs(OUT, exist_ok=True)
    con = setup_tmp()
    art = {"schema": "m7_f2_unit_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "task": "M7 F2 产品入口长度闸门（E2，GPU-free）",
           "host_safety": HOST_SAFETY,
           "device": {"gpu_used": False, "dll_loaded": False, "model_loaded": False,
                      "impl": "FakeEng records calls; real chat copies; real manifests"},
           "engine_layer_reference": {
               "source": "kvmem/m2_visibility/m6b/out/M6B-B2B-P4.json",
               "source_sha16": "47907ef7b88e6c94",
               "control_full_load_rc": 50, "tail_zero_1kb_load_rc": 50,
               "tail_random_1kb_load_rc": 50, "n_tokens": 50,
               "conclusion": "引擎接受 tail-extra（load_rc>0）；故产品入口必须在 reset 前用 bytes 拦截",
               "why": "P4 已证引擎接受 tail-extra；本轮 GPU 禁令不重跑",
               "rerun": False},
           "criteria": "E2: reset_calls==0 + load_calls==0 + sentinel n_tokens=7/pos_max=6 unchanged"}

    tails = {}
    for kind in ("zero", "random"):
        man, cp, m, orig = manifest_copy("live", add_bytes=True, tail=kind)
        r = restore_once(con, man, cp, m, sentinel=True)
        tails[kind] = {
            "manifest": os.path.basename(man), "chat_bytes_original": orig,
            "chat_bytes_after_tail": os.path.getsize(cp),
            "exc": r["exc"], "reset_called": r["reset_called"],
            "load_called": r["load_called"],
            "before": r["before"], "after": r["after"],
            "n_tokens_unchanged": r["before"]["n_tokens"] == r["after"]["n_tokens"],
            "pos_max_unchanged": r["before"]["pos_max"] == r["after"]["pos_max"],
            "pass": bool(r["exc"] and "LayoutMismatch" in r["exc"]
                         and not r["reset_called"] and not r["load_called"]
                         and r["before"]["n_tokens"] == 7 and r["after"]["n_tokens"] == 7
                         and r["before"]["pos_max"] == 6 and r["after"]["pos_max"] == 6),
        }
    art["tail_cases"] = tails

    old_rows = []
    for name in ("s", "live", "s_2", "bridge"):
        src_man = os.path.join(SESS, name + ".json")
        src_man_sha = sha16(src_man)
        man, cp, m, orig = manifest_copy(name, add_bytes=False)
        try:
            ss.validate_manifest(m, model_path=M7B)
            val = "ok"
        except Exception as e:                    # noqa: BLE001
            val = "%s: %s" % (type(e).__name__, e)
        r = restore_once(con, man, cp, m)
        old_rows.append({
            "session": name, "validate_manifest": val,
            "bytes_field": m["chat"].get("bytes"), "chat_file_bytes": orig,
            "load_ok": bool(r["exc"] is None and r["report"]),
            "exc": r["exc"], "unvalidated_events": len(r["events"]),
            "report_unvalidated": (r["report"] or {}).get("unvalidated_chat_bytes"),
            "chat_n_tokens": (r["report"] or {}).get("chat_n_tokens"),
            "original_manifest_sha16": src_man_sha,
            "original_manifest_unchanged": sha16(src_man) == src_man_sha,
            "events": r["events"],
        })
    art["old_manifests"] = old_rows

    # bad_* 三个负样本仍 reject（validate 即失败）
    bad_rows = []
    for name in ("bad_head", "bad_render", "bad_schema"):
        man, cp, m, orig = manifest_copy(name, add_bytes=False)
        # bad_schema 在 validate 就拒绝；bad_head/bad_render 由 layout/placement 拒绝。
        # 三者都必须经真实 restore_session 入口被拒，且拒绝发生在 reset 前。
        r = restore_once(con, man, cp, m, sentinel=True)
        try:
            ss.validate_manifest(m, model_path=M7B)
            val = "passed"
        except Exception as e:                    # noqa: BLE001
            val = "%s: %s" % (type(e).__name__, e)
        rejected = bool(r["exc"] and "LayoutMismatch" in r["exc"]
                        and not r["reset_called"] and not r["load_called"])
        bad_rows.append({"session": name, "validate_manifest": val,
                         "exc": r["exc"], "rejected": rejected,
                         "reset_called": r["reset_called"],
                         "load_called": r["load_called"],
                         "sentinel": r["before"], "after": r["after"]})
    art["bad_manifests"] = bad_rows

    man, cp, m, orig = manifest_copy("live", add_bytes=True)
    r = restore_once(con, man, cp, m)
    art["new_format_control"] = {
        "chat_bytes": orig, "load_ok": bool(r["exc"] is None and r["report"]),
        "exc": r["exc"],
        "chat_bytes_verified": (r["report"] or {}).get("chat_bytes_verified"),
        "unvalidated_events": len(r["events"]),
    }

    o1 = os.path.join(ROOT, "kvmem", "variance", "o1", "s.json")
    o1c = os.path.join(ROOT, "kvmem", "variance", "o1", "s.chat.kvmem")
    art["fifth_session"] = {
        "path": "kvmem/variance/o1/s.json", "exists": os.path.exists(o1),
        "sha16": sha16(o1) if os.path.exists(o1) else None,
        "chat_file": "kvmem/variance/o1/s.chat.kvmem",
        "chat_sha16": sha16(o1c) if os.path.exists(o1c) else None,
        "chat_bytes": os.path.getsize(o1c) if os.path.exists(o1c) else None,
        "status": "unverifiable",
        "reason": "GPU 禁令：不在本机加载真实引擎；只登记存在性与 sha",
    }

    # 事件落盘（只收老 manifest 的 unvalidated 行，逐字 JSONL）
    ev_path = os.path.join(OUT, "M7-F2-EVENTS.jsonl")
    n_ev = 0
    with open(ev_path, "w", encoding="utf-8", newline="\n") as f:
        for row in old_rows:
            for e in row["events"]:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
                n_ev += 1
    art["events_artifact"] = {"path": "kvmem/m2_visibility/m7/out/M7-F2-EVENTS.jsonl",
                              "lines": n_ev, "sha16": sha16(ev_path)}

    tail_ok = all(x["pass"] for x in tails.values())
    old_ok = all(x["load_ok"] and x["unvalidated_events"] >= 1 for x in old_rows)
    bad_ok = all(x["rejected"] for x in bad_rows)
    new_ok = (art["new_format_control"]["load_ok"]
              and art["new_format_control"]["chat_bytes_verified"] is True
              and art["new_format_control"]["unvalidated_events"] == 0)
    art["verdict"] = {
        "tail_fail_closed_before_reset": tail_ok,
        "four_old_manifests_load_and_unvalidated": old_ok,
        "bad_three_still_rejected": bad_ok,
        "new_format_verified": bool(new_ok),
        "F2": ("绿：tail 在 reset/load 前 fail-closed，4 老 manifest 兼容且事件可见，"
               "bad_* 仍 reject，新格式通过" if tail_ok and old_ok and bad_ok and new_ok
               else "未成立，见 rows"),
    }
    path = os.path.join(OUT, "M7-F2-UNIT.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    print(path, os.path.getsize(path), sha16(path))
    print(ev_path, os.path.getsize(ev_path), sha16(ev_path), "lines", n_ev)
    print(json.dumps(art["verdict"], ensure_ascii=False))
    for k, v in tails.items():
        print("tail", k, "exc=", v["exc"], "reset=", v["reset_called"],
              "load=", v["load_called"], "sentinel", v["before"], "->", v["after"],
              "pass", v["pass"])
    for x in old_rows:
        print("old", x["session"], "val", x["validate_manifest"], "load", x["load_ok"],
              "events", x["unvalidated_events"], "report", x["report_unvalidated"])
    for x in bad_rows:
        print("bad", x["session"], x["rejected"], x.get("reason") or x.get("exc"))
    print("new", art["new_format_control"])
    return 0


if __name__ == "__main__":
    sys.exit(main())