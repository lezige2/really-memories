#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repo_health_scan.py -- P1 事故后只读体检（仿 tools/check_chat_daily.py 的逻辑，扫全部 tools/*.py）。

检查：
  A) 每个文件：语法、类方法表、`self.<name>(` 调用 vs 定义（私有 `_x` 悬空 = 事故特征）；
  B) 关键公开方法矩阵：remember/forget/memories/status/save/load、
     bridge 的 handle_event/group_trigger、web 的 search/lookup_text/clean_query；
  C) 跨文件 import：`from <tools 模块> import <符号>` 的目标符号是否存在；
  D) 逐文件 import 冒烟（子进程，超时 10s）；
  E) T15 抽查：memory_service.extract_slots/query_slots/slot_match 存在、可调用、能跑；
  F) 跑 tools/check_chat_daily.py 并记录 rc/输出。

只读：不修改任何仓库源码；唯一写入 out/REPO-HEALTH.json。
用法：python -X utf8 tmp/repo_health_scan.py
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
OUT = ROOT / "out" / "REPO-HEALTH.json"

KEY_PUBLIC = ["remember", "forget", "memories", "status", "save", "load",
              "handle_event", "group_trigger", "search", "lookup_text", "clean_query"]
PER_FILE_REQUIRED = {
    "qq_bridge.py": ["handle_event", "group_trigger", "process"],
    "web_lookup.py": ["search", "lookup_text", "clean_query"],
    "chat_service.py": ["dispatch", "call", "service_info"],
    "memory_service.py": ["extract_slots", "query_slots", "slot_match",
                          "extract_facts", "plan_upsert", "retrieve"],
}
CHAT_DAILY_REQUIRED = [
    "_rows", "_row_by_id", "_rows_for_selection", "_fit_budget", "_sync_mounts",
    "_unmount_all", "_select", "_retrieval_select", "_product_fact_question",
    "_history_text", "_total_tokens", "_put_memory_source", "_rollback_source",
    "_local_time_reply", "_web_answer", "_explicit_search", "_auto_remember_candidate",
    "_ask_natural", "_ask_strict", "ask", "remember", "forget",
]


def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _module_names(files: list[Path]) -> set[str]:
    names = set()
    for f in files:
        names.add(f.stem)
        names.add("tools." + f.stem)
    return names


def _scan_file(path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    rec: dict = {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha16": _sha16(path),
        "bytes": path.stat().st_size,
        "lines": src.count("\n") + 1,
        "syntax_error": None,
        "classes": {},
        "module_defs": [],
        "self_calls": [],
        "dangling_private": [],
        "required_missing": [],
    }
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as exc:
        rec["syntax_error"] = f"{exc.msg} (line {exc.lineno})"
        return rec
    module_defs: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_defs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            module_defs.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    module_defs.add(t.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module_defs.add((alias.asname or alias.name).split(".")[0])
    rec["module_defs"] = sorted(module_defs)
    # per-class methods
    class_methods: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
            class_methods[node.name] = methods
    rec["classes"] = class_methods
    all_methods = {m for ms in class_methods.values() for m in ms}
    # self.<name>( calls
    calls: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            if isinstance(base, ast.Name) and base.id in ("self", "cls"):
                calls.setdefault(node.func.attr, []).append(getattr(node, "lineno", 0))
    rec["self_calls"] = [{"name": k, "lines": sorted(set(v))} for k, v in sorted(calls.items())]
    dangling = [{"name": c, "lines": sorted(set(lines))}
                for c, lines in sorted(calls.items())
                if c.startswith("_") and c not in all_methods]
    rec["dangling_private"] = dangling
    req = PER_FILE_REQUIRED.get(path.name, [])
    if path.name == "chat_daily.py":
        req = CHAT_DAILY_REQUIRED
    rec["required_missing"] = [m for m in req if m not in all_methods and m not in module_defs]
    return rec


def _scan_imports(records: dict[str, dict], path: Path) -> list[dict]:
    """同仓库 tools 模块间的 `from X import Y` 符号存在性。"""
    issues = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return issues
    stems = {Path(r["path"]).stem: r for r in records.values()}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        mod = (node.module or "").replace("tools.", "")
        target = stems.get(mod)
        if not target:
            continue
        defined = set(target["module_defs"]) | {m for ms in target["classes"].values() for m in ms}
        # 星号 import 跳过
        for alias in node.names:
            if alias.name == "*":
                continue
            if alias.name not in defined:
                issues.append({
                    "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "line": node.lineno,
                    "from": mod,
                    "symbol": alias.name,
                })
    return issues


def _import_smoke(path: Path) -> dict:
    stem = path.stem
    cmd = [sys.executable, "-X", "utf8", "-c",
           "import sys; sys.path.insert(0, %r); import %s as m; print('IMPORT_OK', getattr(m, 'VERSION', ''))"
           % (str(TOOLS), stem)]
    try:
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                            errors="replace", timeout=10)
        out = ((cp.stdout or "") + (cp.stderr or "")).strip().splitlines()
        return {"rc": cp.returncode,
                "tail": out[-1][:240] if out else ""}
    except subprocess.TimeoutExpired:
        return {"rc": "timeout", "tail": "import timeout >10s"}


def _t15_check() -> dict:
    sys.path.insert(0, str(TOOLS))
    res = {"module": "tools/memory_service.py", "symbols": {}}
    try:
        import memory_service as m  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        res["import_error"] = f"{type(exc).__name__}: {exc}"
        return res
    slots = None
    for name in ("extract_slots", "query_slots", "slot_match"):
        fn = getattr(m, name, None)
        item = {"exists": fn is not None, "callable": callable(fn)}
        try:
            if name == "extract_slots":
                slots = fn("我的车停在 B2 层 37 号，周三下午三点开会")
                item["smoke"] = "ok" if isinstance(slots, dict) else type(slots).__name__
            elif name == "query_slots":
                qs = fn("我的车停哪个位置？")
                item["smoke"] = "ok" if isinstance(qs, (dict, bool)) else type(qs).__name__
            else:
                item["smoke"] = "checked-by-slot_match_smoke"
        except Exception as exc:  # noqa: BLE001
            item["smoke"] = f"{type(exc).__name__}: {exc}"
        res["symbols"][name] = item
    # slot_match 单独按真实签名冒烟（query_slots + slots）
    try:
        qs = m.query_slots("我的车停哪个位置？")
        s = m.extract_slots("我的车停在 B2 层 37 号")
        res["slot_match_smoke"] = repr(m.slot_match(qs, s))[:120]
    except Exception as exc:  # noqa: BLE001
        res["slot_match_smoke"] = f"{type(exc).__name__}: {exc}"
    return res


def main() -> int:
    t0 = time.time()
    files = sorted(p for p in TOOLS.glob("*.py") if p.is_file())
    records = {}
    for p in files:
        records[str(p)] = _scan_file(p)
    imports_issues = []
    for p in files:
        imports_issues.extend(_scan_imports(records, p))
    smoke = {}
    for p in files:
        rec = records[str(p)]
        if rec["syntax_error"]:
            smoke[rec["path"]] = {"rc": "syntax-error", "tail": rec["syntax_error"]}
        else:
            smoke[rec["path"]] = _import_smoke(p)
    # key public matrix
    matrix = {}
    for rec in records.values():
        names = set(rec["module_defs"]) | {m for ms in rec["classes"].values() for m in ms}
        matrix[rec["path"]] = {k: (k in names) for k in KEY_PUBLIC}
    # check_chat_daily
    try:
        cp = subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / "check_chat_daily.py")],
                            cwd=str(ROOT), capture_output=True, text=True,
                            errors="replace", timeout=60)
        chat_daily_check = {"rc": cp.returncode,
                            "stdout": (cp.stdout or "").strip()[:1000],
                            "stderr": (cp.stderr or "").strip()[:1000]}
    except Exception as exc:  # noqa: BLE001
        chat_daily_check = {"rc": "error", "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}

    issues_files = []
    for rec in records.values():
        if rec["syntax_error"] or rec["dangling_private"] or rec["required_missing"]:
            issues_files.append(rec["path"])
    payload = {
        "schema": "repo_health_v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(ROOT),
        "scan": {"files": len(files), "elapsed_s": round(time.time() - t0, 1)},
        "summary": {
            "files_with_issues": len(issues_files),
            "syntax_errors": sum(1 for r in records.values() if r["syntax_error"]),
            "dangling_private_total": sum(len(r["dangling_private"]) for r in records.values()),
            "required_missing_total": sum(len(r["required_missing"]) for r in records.values()),
            "cross_file_missing_symbols": len(imports_issues),
            "import_smoke_failures": sum(1 for v in smoke.values() if v["rc"] not in (0,)),
        },
        "files": list(records.values()),
        "dangling": [{"file": r["path"], "calls": r["dangling_private"]}
                     for r in records.values() if r["dangling_private"]],
        "required_missing": [{"file": r["path"], "missing": r["required_missing"]}
                             for r in records.values() if r["required_missing"]],
        "cross_file_imports": imports_issues,
        "import_smoke": smoke,
        "key_public_matrix": matrix,
        "t15_memory_service": _t15_check(),
        "check_chat_daily": chat_daily_check,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, OUT)
    print("wrote", OUT, hashlib.sha256(OUT.read_bytes()).hexdigest()[:16],
          OUT.stat().st_size, "bytes")
    print("summary:", json.dumps(payload["summary"], ensure_ascii=False))
    print("issues_files:", issues_files)
    if imports_issues:
        print("cross_file_issues:", json.dumps(imports_issues[:10], ensure_ascii=False))
    print("chat_daily_check rc:", chat_daily_check["rc"])
    print("t15:", json.dumps(payload["t15_memory_service"], ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())