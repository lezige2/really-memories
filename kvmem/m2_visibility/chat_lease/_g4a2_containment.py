# -*- coding: utf-8 -*-
"""G4a-3 的 containment 证据（lead 裁：explain 硬锚作废，改可逆性 + 三条强证据）。

产物 `out/G4a2-containment.json`：
1) `explain v2` 可逆性：去 `explain_version: 2` 行、`[可挂载]/[无块行→不可挂载]` 标注、
   `可挂载集：…` 行后，与 v1 硬锚 `3e8aae60685d2e55` 逐字节同 ⇒ 分数/名字一行未变。
2) `cmd_chat` 源码 sha 前后同（默认路径零 diff）。
3) `m1` 非 explain 真机臂：改动前（`out/G4a2-red-variant.json`，chat=`bb083a1b`）与
   改动后（`out/M4C-m1-rerun-v2.json`，chat=`22081c41`）的 exit/attaches/loads/skip/sha_stable
   逐项同，唯一差异 = `CONTROL_Q` 的状态与 ask 次数（设计内）。
4) `two --dry-run` 产品字段前后同。
只读 + 一次 explain 运行（temp DB 副本）；不写仓库 DB。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "tmp_db")
BEFORE = os.path.join(HERE, "_before", "chat.py@bb083a1b71165e97")
NEW = os.path.join(TOOLS, "chat.py")
V2 = os.path.join(OUT, "M4C-m1-rerun-v2.json")
VAR = os.path.join(OUT, "G4a2-red-variant.json")
DRY_BEFORE = os.path.join(TMP, "S1-dryrun-g4.json")
DRY_AFTER = os.path.join(TMP, "S1-dryrun-g4a2.json")
OLD_ANCHOR = "3e8aae60685d2e55"
PRODUCT = os.path.join(OUT, "G4a2-containment.json")


def sha16_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha16_file(p):
    with open(p, "rb") as fh:
        return sha16_bytes(fh.read())


def func_src(path, name):
    lines = open(path, encoding="utf-8").read().split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("def %s(" % name):
            start = i
            break
    if start is None:
        raise SystemExit("function %r not found in %s" % (name, path))
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("def ") or lines[j].startswith("class "):
            end = j
            break
    return "\n".join(lines[start:end])


def explain_run(db_copy):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               CHAT_DB=os.path.abspath(db_copy), PYTHONPATH=TOOLS)
    r = subprocess.run([sys.executable, "-X", "utf8", NEW, "m1", "--explain"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return r.returncode, (r.stdout or "").replace("\r\n", "\n")


def strip_annotations(text):
    out = []
    for ln in text.split("\n"):
        if ln == "explain_version: 2":
            continue
        for suffix in ("  [可挂载]", "  [无块行→不可挂载]"):
            if ln.endswith(suffix):
                ln = ln[: -len(suffix)]
                break
        if ln.startswith("  可挂载集："):
            continue
        out.append(ln)
    return "\n".join(out)


def main():
    import shutil
    db = os.path.join(TMP, "chat@g4a2-containment.db")
    if os.path.exists(db):
        os.remove(db)
    shutil.copy2(os.path.join(ROOT, "kvmem", "chat.db"), db)
    db_before = sha16_file(db)
    code, out = explain_run(db)
    db_after = sha16_file(db)
    stripped = strip_annotations(out)
    prod = {
        "schema": "g4a2_containment_v1",
        "task": "task-35 G4a-3 containment（lead 裁定：explain 硬锚作废，改可逆性+强证据）",
        "chat_py": {"before_sha16": sha16_file(BEFORE), "after_sha16": sha16_file(NEW)},
        "explain_v2": {
            "exit": code, "bytes": len(out.encode("utf-8")),
            "sha16": sha16_bytes(out.encode("utf-8")),
            "version_line": out.split("\n", 1)[0],
            "reversible": {
                "stripped_bytes": len(stripped.encode("utf-8")),
                "stripped_sha16": sha16_bytes(stripped.encode("utf-8")),
                "old_anchor_sha16": OLD_ANCHOR,
                "equals_old_anchor": sha16_bytes(stripped.encode("utf-8")) == OLD_ANCHOR,
                "meaning": "去新增标注/可挂载集行后与 v1 硬锚逐字节同 ⇒ 分数与名字一行未变",
            },
            "v1_anchor_retired": {"sha16": OLD_ANCHOR, "bytes": 872,
                                  "status": "v1 已作废（explain_version: 1 坐标不再作为回归锚）"},
        },
        "cmd_chat_zero_diff": {
            "before_len": len(func_src(BEFORE, "cmd_chat")),
            "after_len": len(func_src(NEW, "cmd_chat")),
            "before_sha16": sha16_bytes(func_src(BEFORE, "cmd_chat").encode("utf-8")),
            "after_sha16": sha16_bytes(func_src(NEW, "cmd_chat").encode("utf-8")),
            "identical": func_src(BEFORE, "cmd_chat") == func_src(NEW, "cmd_chat"),
        },
        "m1_nonexplain": {
            "before_product": "out/G4a2-red-variant.json（bb083a1b）",
            "after_product": "out/M4C-m1-rerun-v2.json（22081c41）",
            "same": {},
            "divergence_design": {},
        },
        "two_dryrun": {"before": os.path.relpath(DRY_BEFORE, ROOT).replace("\\", "/"),
                       "after": os.path.relpath(DRY_AFTER, ROOT).replace("\\", "/")},
        "db_copy": {"path": os.path.relpath(db, ROOT).replace("\\", "/"),
                    "sha16_before": db_before, "sha16_after": db_after},
    }
    b = json.load(open(VAR, encoding="utf-8"))
    a = json.load(open(V2, encoding="utf-8"))
    same = prod["m1_nonexplain"]["same"]
    same["exit"] = (b["exit"] == a["exit"] == 0)
    same["attaches_done"] = (b["asserts"]["attaches_done"] == a["asserts"]["attaches_done"] == 2)
    same["loads_exact"] = [x["path"] for x in b["loads"]] == [x["path"] for x in a["loads"]] \
                          and [x["seq"] for x in b["loads"]] == [x["seq"] for x in a["loads"]]
    same["skip_events_exact"] = b["asserts"]["skip_events"] == a["asserts"]["skip_events"]
    same["sha_stable_unchanged"] = (b["sha_stable"]["unchanged"] is True
                                    and a["sha_stable"]["unchanged"] is True)
    nb = [d for d in b["decides"] if d["q"] != b["control_q"]["q"]]
    na = [d for d in a["decides"] if d["q"] != a["control_q"]["q"]]
    same["other_questions_state"] = all(
        (x["state"] == y["state"] and x["refuse"] == y["refuse"])
        for x, y in zip(nb, na)) and len(nb) == len(na)
    same["all"] = all(same.values())
    prod["m1_nonexplain"]["divergence_design"] = {
        "control_state": {"before": b["control_q"]["decide"]["state"],
                          "after": a["control_q"]["decide"]["state"]},
        "control_ask_count": {"before": b["control_q"]["ask_count"],
                              "after": a["control_q"]["ask_count"]},
        "control_refuse": {"before": b["control_q"]["decide"]["refuse"],
                           "after": a["control_q"]["decide"]["refuse"]},
        "note": "CONTROL_Q 差异为 G4a-2 设计内（决策面只认可挂载 selection）",
    }
    if os.path.exists(DRY_BEFORE) and os.path.exists(DRY_AFTER):
        db_ = json.load(open(DRY_BEFORE, encoding="utf-8"))
        da = json.load(open(DRY_AFTER, encoding="utf-8"))
        cb, ca = db_.get("checks", {}), da.get("checks", {})
        prod["two_dryrun"].update({
            "before_exit": db_.get("exit"), "after_exit": da.get("exit"),
            "before_verdict": db_.get("verdict"), "after_verdict": da.get("verdict"),
            "checks_equal": cb == ca,
            "checks": ca,
            "fail_ids": db_.get("fail_ids") if db_.get("fail_ids") == da.get("fail_ids") else "MISMATCH",
        })
    with open(PRODUCT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prod, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (PRODUCT, os.path.getsize(PRODUCT),
                                            sha16_file(PRODUCT)))
    print("explain:", prod["explain_v2"]["sha16"], prod["explain_v2"]["bytes"],
          "| reversible:", prod["explain_v2"]["reversible"]["equals_old_anchor"])
    print("cmd_chat zero diff:", prod["cmd_chat_zero_diff"]["identical"])
    print("m1 nonexplain same:", same)
    print("two dry checks_equal:", prod["two_dryrun"].get("checks_equal"))
    return 0


if __name__ == "__main__":
    sys.exit(main())