# -*- coding: utf-8 -*-
"""S1-b 默认路径回归臂（m1 真机一次）+ 旧副本对照（v6 口径 ae2d88ad5ecc25d3）。

背景（v6 §11.4，缺口 G4，**非 S1 引起**）：task-5 重建后 selection 会命中
`conv_2026-10-25#L5` 这类没有块行的 conv 源，`cmd_m1` 在 `rows[name]` 处 KeyError。
本脚本的用途是**把这个事实落成产品**（不是把它修绿）：
  * 新 `tools/chat.py`（含 S1）跑 `m1` 真机 ⇒ 期望与旧副本**同样的异常**
  * 旧 `_before/chat.py@cb70be52eef253fa` 跑 `m1` 真机 ⇒ 逐字对照
  * 同时记录 `m1 --explain`（默认路径的非引擎分支）新旧逐字节相同
  * 全程用 temp DB 副本，仓库 chat.db 只读

用法： PY -X utf8 _run_m1_regression.py --out ...json [--db ...]
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime

ROOT = r"D:\llama-mem"
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import chat  # noqa: E402

DEFAULT_DB = os.path.join(ROOT, "kvmem", "m2_visibility", "chat_lease", "tmp_db",
                          "chat@237d8e1f.db")
OLD = os.path.join(ROOT, "kvmem", "m2_visibility", "chat_lease",
                   "_before", "chat.py@cb70be52eef253fa")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_module(path, name):
    tmp = tempfile.mkdtemp(prefix="m1_reg_")
    dst = os.path.join(tmp, "chat.py")
    shutil.copyfile(path, dst)
    spec = importlib.util.spec_from_file_location(name, dst)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_m1(mod, db):
    """跑 cmd_m1（真机）；不吞异常：把异常类型/消息/最后帧行号原样记下来。"""
    mod.DB = db
    buf = io.StringIO()
    t0 = time.time()
    rec = {"started_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        with contextlib.redirect_stdout(buf):
            mod.cmd_m1(explain=False, control=False, save_path=None)
        rec.update({"raised": False, "type": None, "msg": "",
                    "frame": None, "last_line": None})
    except BaseException as exc:                                # noqa: BLE001
        tb = traceback.extract_tb(exc.__traceback__)
        last = tb[-1] if tb else None
        rec.update({"raised": True, "type": type(exc).__name__, "msg": str(exc),
                    "frame": {"file": os.path.basename(last.filename) if last else None,
                              "line": last.lineno if last else None,
                              "func": last.name if last else None},
                    "last_line": last.line if last else None})
    rec["elapsed_s"] = round(time.time() - t0, 1)
    rec["stdout_tail"] = buf.getvalue().strip().splitlines()[-6:]
    rec["stdout_bytes"] = len(buf.getvalue())
    return rec


def cli_m1_explain(path, db):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               PYTHONPATH=TOOLS, CHAT_DB=db)
    r = subprocess.run([sys.executable, "-X", "utf8", path, "m1", "--explain"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=180)
    return {"exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def main():
    ap = argparse.ArgumentParser(description="S1-b default-path regression (m1 real)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    prod = {"schema": "s1_default_regression_v1",
            "spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@" + sha16(
                os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")),
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "db_copy": {"path": args.db, "sha16": sha16(args.db)},
            "repo_db_sha16": sha16(os.path.join(ROOT, "kvmem", "chat.db")),
            "chat_py": {"new": {"path": os.path.join(TOOLS, "chat.py"),
                                "sha16": sha16(os.path.join(TOOLS, "chat.py"))},
                        "old": {"path": OLD, "sha16": sha16(OLD)}},
            "note": "G4（v6 §11.4）：m1 真机 KeyError 是 task-5 重建后的既有缺口，"
                    "非 S1 引起；本产品把它落证，不修绿。M4-C 绿臂当前不可直接重跑。"}
    t0 = time.time()
    prod["m1_explain"] = {"new": cli_m1_explain(os.path.join(TOOLS, "chat.py"), args.db),
                          "old": cli_m1_explain(OLD, args.db)}
    del prod["m1_explain"]["new"]["stderr"], prod["m1_explain"]["old"]["stderr"]
    prod["m1_explain"]["identical"] = (
        prod["m1_explain"]["new"]["stdout"] == prod["m1_explain"]["old"]["stdout"])
    prod["m1_explain"]["stdout_sha16"] = sha16_text(prod["m1_explain"]["new"]["stdout"])

    new_mod = load_module(os.path.join(TOOLS, "chat.py"), "chat_m1_new")
    old_mod = load_module(OLD, "chat_m1_old")
    prod["m1_real_new"] = run_m1(new_mod, args.db)
    prod["m1_real_old"] = run_m1(OLD and old_mod, args.db)
    n, o = prod["m1_real_new"], prod["m1_real_old"]
    prod["g4_confirmed"] = bool(
        n["raised"] and o["raised"] and n["type"] == o["type"] == "KeyError"
        and n["msg"] == o["msg"] and (n["frame"] or {}).get("line") == (o["frame"] or {}).get("line"))
    prod["default_path_equiv"] = bool(
        n["raised"] == o["raised"] and n["type"] == o["type"] and n["msg"] == o["msg"])
    prod["elapsed_s"] = round(time.time() - t0, 1)
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prod, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (out, os.path.getsize(out), sha16(out)))
    print("g4_confirmed=%s default_path_equiv=%s"
          % (prod["g4_confirmed"], prod["default_path_equiv"]))
    print("new m1: %s" % json.dumps({k: n[k] for k in ("raised", "type", "msg", "frame",
                                                       "elapsed_s")}, ensure_ascii=False))
    print("old m1: %s" % json.dumps({k: o[k] for k in ("raised", "type", "msg", "frame",
                                                       "elapsed_s")}, ensure_ascii=False))
    print("m1 --explain identical=%s" % prod["m1_explain"]["identical"])
    return 0 if prod["g4_confirmed"] else 3


def sha16_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    sys.exit(main())