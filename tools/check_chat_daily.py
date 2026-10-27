# -*- coding: utf-8 -*-
"""check_chat_daily.py -- 改后守卫（通用）：编译 / 导入 / 悬空 self 调用 / 必需符号。

用途：任何对产品侧 Python 的改动后必须运行。覆盖四个关键模块：
  chat_daily / memory_service / web_lookup / qq_bridge
检查项：
  1) py_compile（compile(source)）
  2) import 冒烟（只 import，不跑 GPU/服务）
  3) 悬空 self.<name>( 调用：name 不在本类方法/类属性/实例属性/模块定义中
  4) 必需方法白名单（DailyApp/QQBridge）与必需模块符号
输出：人类可读摘要（默认）+ `--json` 机器可读；exit 0=全部通过，1=有问题，2=内部错误。
只读源码，不改任何文件。
"""
import argparse
import ast
import importlib
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

# 必需方法（DailyApp）——按产品当前口径（缺一即视为改坏）
REQUIRED_DAILY_METHODS = [
    "_rows", "_row_by_id", "_rows_for_selection", "_fit_budget", "_sync_mounts",
    "_unmount_all", "_select", "_retrieval_select", "_product_fact_question",
    "_history_text", "_total_tokens", "_put_memory_source", "_rollback_source",
    "_local_time_reply", "_web_answer", "_explicit_search", "_auto_remember_candidate",
    "_ask_natural", "_ask_strict", "ask", "remember", "forget",
]
REQUIRED_QQ_METHODS = [
    "handle_event", "process", "group_trigger", "send_reply", "run", "stop",
]
TARGETS = {
    "chat_daily": {"file": "chat_daily.py", "class": "DailyApp",
                   "required_methods": REQUIRED_DAILY_METHODS,
                   "required_symbols": ["DailyApp", "clean_answer"]},
    "memory_service": {"file": "memory_service.py", "class": None,
                       "required_symbols": ["tokens", "retrieve", "score_row",
                                            "extract_facts", "plan_upsert",
                                            "needs_auto_remember", "is_fact_question",
                                            "needs_lookup", "introspect"]},
    "web_lookup": {"file": "web_lookup.py", "class": None,
                   "required_symbols": ["search", "lookup_text", "parse_results",
                                        "_fetch_html", "_safe_url"]},
    "qq_bridge": {"file": "qq_bridge.py", "class": "QQBridge",
                  "required_methods": REQUIRED_QQ_METHODS,
                  "required_symbols": ["QQBridge", "WSConn", "ws_accept", "ws_connect",
                                       "parse_command", "message_text", "split_reply"]},
}


def _defs_and_attrs(tree):
    """返回 (module_names, per_class: {name: {"methods":set,"attrs":set}})。"""
    module_names = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_names.add(n.name)
    per_class = {}
    for c in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        methods, attrs = set(), set()
        for m in c.body:
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(m.name)
            elif isinstance(m, (ast.Assign, ast.AnnAssign)):
                targets = m.targets if isinstance(m, ast.Assign) else [m.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        attrs.add(t.id)
                    elif isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) \
                            and t.value.id == "self":
                        attrs.add(t.attr)
        for n in ast.walk(c):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                    and n.value.id == "self" and isinstance(n.ctx, (ast.Store, ast.Del)):
                attrs.add(n.attr)
        per_class[c.name] = {"methods": methods, "attrs": attrs, "node": c}
    return module_names, per_class


def _dangling(tree, module_names, per_class, class_name):
    """class_name 内 self.<attr>( 的悬空调用（只查本类；有基类则跳过）。"""
    info = per_class.get(class_name)
    if not info:
        return []
    c = info["node"]
    if c.bases:   # 有基类：无法静态判定继承方法，跳过（repo-health 另行告警）
        return []
    out, seen = [], set()
    for n in ast.walk(c):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "self":
            a = n.func.attr
            if a.startswith("__"):
                continue
            if a in info["methods"] or a in info["attrs"] or a in module_names:
                continue
            if a in seen:
                continue
            seen.add(a)
            out.append({"symbol": a, "line": n.lineno})
    return out


def check_module(name, spec):
    path = os.path.join(TOOLS, spec["file"])
    result = {"module": name, "file": spec["file"], "compile": "skip",
              "import": "skip", "missing": [], "dangling": [], "issues": []}
    if not os.path.exists(path):
        result["issues"].append({"module": name, "kind": "missing_file",
                                 "symbol": spec["file"], "detail": "文件不存在"})
        return result
    src = open(path, encoding="utf-8").read()
    if len(src) < 200:
        result["issues"].append({"module": name, "kind": "suspect_truncated",
                                 "symbol": spec["file"],
                                 "detail": "文件过短（%d B）" % len(src)})
    try:
        tree = ast.parse(src)
        compile(src, path, "exec")
        result["compile"] = "ok"
    except SyntaxError as exc:
        result["compile"] = "fail"
        result["issues"].append({"module": name, "kind": "compile_fail",
                                 "symbol": "%s:%s" % (exc.lineno, exc.offset),
                                 "detail": str(exc)})
        return result
    try:
        importlib.invalidate_caches()
        mod = importlib.import_module(name)
        result["import"] = "ok"
    except Exception as exc:                      # noqa: BLE001
        result["import"] = "fail"
        result["issues"].append({"module": name, "kind": "import_fail",
                                 "symbol": type(exc).__name__, "detail": str(exc)[:300]})
        return result

    module_names, per_class = _defs_and_attrs(tree)
    cls_name = spec.get("class")
    if cls_name:
        cls = getattr(mod, cls_name, None)
        for m in spec.get("required_methods", []):
            if cls is None or not hasattr(cls, m):
                result["missing"].append({"symbol": "%s.%s" % (cls_name, m),
                                          "line": None, "kind": "required_method"})
    for s in spec.get("required_symbols", []):
        if not hasattr(mod, s):
            result["missing"].append({"symbol": s, "line": None,
                                      "kind": "required_symbol"})
    if cls_name and cls_name in per_class:
        result["dangling"] = _dangling(tree, module_names, per_class, cls_name)

    by_symbol = {}
    for m in result["missing"]:
        key = m["symbol"].split(".")[-1]
        by_symbol.setdefault(key, {"module": name, "kind": m["kind"],
                                   "symbol": m["symbol"], "detail": "",
                                   "lines": []})
    for d in result["dangling"]:
        key = d["symbol"]
        if key in by_symbol:
            by_symbol[key]["detail"] = "同时存在悬空 self.%s( 调用" % key
            by_symbol[key]["lines"] = [d["line"]]
            by_symbol[key]["kind"] = "missing_required+dangling_call"
        else:
            by_symbol[key] = {"module": name, "kind": "dangling_self_call",
                              "symbol": key,
                              "detail": "self.%s( 无对应方法/属性/模块定义" % key,
                              "lines": [d["line"]]}
    result["issues"] = list(by_symbol.values())
    return result


def run():
    report = {"schema": "check_chat_daily_v2",
              "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
              "root": ROOT, "targets": {}, "issues": [], "ok": True}
    for name, spec in TARGETS.items():
        r = check_module(name, spec)
        report["targets"][name] = {k: r[k] for k in ("file", "compile", "import")}
        report["issues"].extend(r["issues"])
    report["n_issues"] = len(report["issues"])
    report["ok"] = report["n_issues"] == 0
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="post-edit guard for key product modules")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    a = ap.parse_args(argv)
    try:
        rep = run()
    except Exception as exc:                      # noqa: BLE001
        print(json.dumps({"schema": "check_chat_daily_v2", "ok": False,
                          "error": repr(exc)}, ensure_ascii=False))
        return 2
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        for name, t in rep["targets"].items():
            print("[%s] compile=%s import=%s" % (name, t["compile"], t["import"]))
        for i in rep["issues"]:
            print("[FAIL] %s %s %s %s" % (i["module"], i["kind"], i["symbol"],
                                          i.get("detail", "")))
        print("SUMMARY issues=%d ok=%s" % (rep["n_issues"], rep["ok"]))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())