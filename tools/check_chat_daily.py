# -*- coding: utf-8 -*-
"""check_chat_daily.py -- 改后守卫（调用方权威版）。

核心原则：**以调用方为准**，不再依赖一张“必需方法白名单”：
  1) 内部调用方：解析 chat_daily 内 DailyApp 的每个 `self.<name>(` 调用，要求
     DailyApp 确实定义该 name（方法/staticmethod/classmethod/类属性/实例属性）；
     任何一个未定义 ⇒ error（rc=1）。
  2) 外部调用方：扫描 tools/*.py（排除 chat_daily 自身）里所有 `DailyApp.<name>`
     / `D.DailyApp.<name>` 引用，要求同名定义存在（可捕获测试/服务端先用到、
     而实现被删的情况，如 `_smalltalk_reply`）。
  3) 调用方式一致性：instance 方法被 `DailyApp.<name>(` 且无实例 ⇒ error；
     static 方法被 `DailyApp.<name>(<变量>, ...)` 带首参调用 ⇒ style note；
     static/class 方法经 self 调用 ⇒ style note（可运行、非首选）。
  4) 公开方法清单：remember / forget / memories / status / save / load 必须存在。
  5) 关键模块（memory_service / web_lookup / qq_bridge）仍做 compile/import/必需符号。
额外：`--file PATH` 可对指定 chat_daily 快照做 AST 校验（用于坏版本回归，跳过 import）。

输出：默认人类可读 + `--json`；exit 0=通过，1=有问题，2=内部错误。只读，不改文件。
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

PUBLIC_API = ["remember", "forget", "memories", "status", "save", "load"]
OTHER_TARGETS = {
    "memory_service": {"file": "memory_service.py",
                       "required_symbols": ["tokens", "retrieve", "score_row",
                                            "extract_facts", "plan_upsert",
                                            "needs_auto_remember", "is_fact_question",
                                            "needs_lookup", "introspect"]},
    "web_lookup": {"file": "web_lookup.py",
                   "required_symbols": ["search", "lookup_text", "parse_results",
                                        "_fetch_html", "_safe_url"]},
    "qq_bridge": {"file": "qq_bridge.py",
                  "required_symbols": ["QQBridge", "WSConn", "ws_accept", "ws_connect",
                                       "parse_command", "message_text", "split_reply"],
                  "required_methods": {"QQBridge": ["handle_event", "process",
                                                    "group_trigger", "send_reply",
                                                    "run", "stop"]}},
}


def parse_file(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    compile(src, path, "exec")
    return src, tree


def _class_info(tree, class_name):
    for c in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        if c.name != class_name:
            continue
        methods, kinds = {}, {}
        for m in c.body:
            if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            methods[m.name] = m
            decs = {ast.unparse(d).split("(")[0] for d in m.decorator_list}
            kinds[m.name] = ("staticmethod" if "staticmethod" in decs else
                             "classmethod" if "classmethod" in decs else "instance")
        attrs = set()
        for n in ast.walk(c):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                    and n.value.id == "self" and isinstance(n.ctx, (ast.Store, ast.Del)):
                attrs.add(n.attr)
        for m in c.body:
            if isinstance(m, (ast.Assign, ast.AnnAssign)):
                for t in (m.targets if isinstance(m, ast.Assign) else [m.target]):
                    if isinstance(t, ast.Name):
                        attrs.add(t.id)
        return c, methods, kinds, attrs
    return None, {}, {}, set()


def internal_caller_issues(tree):
    """DailyApp 内 self.<name>( 调用 → DailyApp 是否定义。"""
    c, methods, kinds, attrs = _class_info(tree, "DailyApp")
    if c is None:
        return [{"kind": "missing_class", "symbol": "DailyApp",
                 "detail": "类不存在"}]
    issues, seen = [], set()
    for n in ast.walk(c):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"):
            continue
        name = n.func.attr
        if name.startswith("__"):
            continue
        if name in methods or name in attrs or name in seen:
            continue
        seen.add(name)
        issues.append({"kind": "dangling_self_call", "symbol": "DailyApp.%s" % name,
                       "line": n.lineno,
                       "detail": "self.%s( 在 DailyApp 中无定义/无赋值" % name})
    return issues


def internal_style_notes(tree):
    """DailyApp 内自调用 static/class 方法的风格记录（可运行、非首选，不阻断）。"""
    c, methods, kinds, attrs = _class_info(tree, "DailyApp")
    if c is None:
        return []
    notes, seen = [], set()
    for n in ast.walk(c):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"):
            continue
        name = n.func.attr
        kind = kinds.get(name)
        if kind in ("staticmethod", "classmethod") and name not in seen:
            seen.add(name)
            notes.append({"kind": "static_called_via_self",
                          "symbol": "DailyApp.%s" % name,
                          "detail": "内部经 self 调用 %s 方法（可运行，非首选；建议 %s.%s）"
                                    % (kind, "DailyApp", name)})
    return notes


def _dailyattr_target(func):
    """识别 DailyApp.<name>( / D.DailyApp.<name>(；返回 (name, style)。"""
    if not isinstance(func, ast.Attribute):
        return None
    if isinstance(func.value, ast.Name) and func.value.id == "DailyApp":
        return func.attr, "class"
    if isinstance(func.value, ast.Attribute) and func.value.attr == "DailyApp" \
            and isinstance(func.value.value, ast.Name):
        return func.attr, "class"
    return None


def external_caller_issues(tree):
    """tools/*.py 中 DailyApp.<name> 引用 → 定义是否存在 + 调用方式一致性。"""
    c, methods, kinds, attrs = _class_info(tree, "DailyApp")
    defined = set(methods) | set(attrs)
    if c is None:
        return [], []
    issues, notes = [], []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py") or fn == "chat_daily.py":
            continue
        path = os.path.join(TOOLS, fn)
        try:
            other = ast.parse(open(path, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(other):
            if not isinstance(n, ast.Call):
                continue
            tgt = _dailyattr_target(n.func)
            if tgt is None:
                continue
            name, style = tgt
            if name not in defined:
                hit = next((x for x in issues
                            if x["kind"] == "external_caller_missing"
                            and x["symbol"] == "DailyApp.%s" % name), None)
                if hit is None:
                    issues.append({"kind": "external_caller_missing",
                                   "symbol": "DailyApp.%s" % name, "line": None,
                                   "sites": ["%s:%d" % (fn, n.lineno)],
                                   "detail": "%s:%d 引用了不存在的 DailyApp.%s"
                                             % (fn, n.lineno, name)})
                else:
                    hit["sites"].append("%s:%d" % (fn, n.lineno))
                continue
            kind = kinds.get(name)
            if kind == "instance" and style == "class" and len(n.args) == 0:
                issues.append({"kind": "instance_called_without_instance",
                               "symbol": "DailyApp.%s" % name, "line": None,
                               "detail": "%s:%d 以类方式调用实例方法且未传实例"
                                         % (fn, n.lineno)})
            if kind == "staticmethod" and style == "class" \
                    and n.args and isinstance(n.args[0], ast.Name):
                notes.append({"kind": "static_called_with_leading_arg",
                              "symbol": "DailyApp.%s" % name,
                              "detail": "%s:%d 静态方法首参为变量（疑似把实例当 self）"
                                        % (fn, n.lineno)})
            if kind in ("staticmethod", "classmethod") and style == "self":
                notes.append({"kind": "static_called_via_self",
                              "symbol": "DailyApp.%s" % name,
                              "detail": "经 self 调用 %s 方法（可运行，非首选）" % kind})
    return issues, notes


def public_api_issues(tree):
    c, methods, kinds, attrs = _class_info(tree, "DailyApp")
    if c is None:
        return [{"kind": "missing_class", "symbol": "DailyApp"}]
    return [{"kind": "missing_public_api", "symbol": "DailyApp.%s" % name,
             "line": None, "detail": "公开方法缺失"} for name in PUBLIC_API
            if name not in methods]


def check_other_modules():
    issues, targets = [], {}
    for name, spec in OTHER_TARGETS.items():
        path = os.path.join(TOOLS, spec["file"])
        info = {"file": spec["file"], "compile": "fail", "import": "skip"}
        try:
            parse_file(path)
            info["compile"] = "ok"
        except Exception as exc:              # noqa: BLE001
            issues.append({"module": name, "kind": "compile_fail",
                           "symbol": spec["file"], "detail": str(exc)[:200]})
            targets[name] = info
            continue
        try:
            importlib.invalidate_caches()
            mod = importlib.import_module(name)
            info["import"] = "ok"
        except Exception as exc:              # noqa: BLE001
            issues.append({"module": name, "kind": "import_fail", "symbol": name,
                           "detail": str(exc)[:300]})
            targets[name] = info
            continue
        for sym in spec.get("required_symbols", []):
            if not hasattr(mod, sym):
                issues.append({"module": name, "kind": "missing_required_symbol",
                               "symbol": sym, "detail": "必需符号缺失"})
        for cls_name, meths in spec.get("required_methods", {}).items():
            cls = getattr(mod, cls_name, None)
            for m in meths:
                if cls is None or not hasattr(cls, m):
                    issues.append({"module": name, "kind": "missing_required_method",
                                   "symbol": "%s.%s" % (cls_name, m),
                                   "detail": "必需方法缺失"})
        targets[name] = info
    return issues, targets


def check_chat_daily(file_path=None):
    path = file_path or os.path.join(TOOLS, "chat_daily.py")
    out = {"file": os.path.basename(path), "path": path, "compile": "fail",
           "import": "skip", "issues": [], "style_notes": []}
    try:
        src, tree = parse_file(path)
        out["compile"] = "ok"
    except Exception as exc:                  # noqa: BLE001
        out["issues"].append({"kind": "compile_fail",
                              "symbol": os.path.basename(path),
                              "detail": str(exc)[:300]})
        return out
    if len(src) < 2000:
        out["issues"].append({"kind": "suspect_truncated",
                              "symbol": os.path.basename(path),
                              "detail": "文件过短（%d B）" % len(src)})
    if file_path is None:
        try:
            importlib.invalidate_caches()
            importlib.import_module("chat_daily")
            out["import"] = "ok"
        except Exception as exc:              # noqa: BLE001
            out["import"] = "fail"
            out["issues"].append({"kind": "import_fail", "symbol": "chat_daily",
                                  "detail": str(exc)[:300]})
    out["issues"].extend(internal_caller_issues(tree))
    ext, notes = external_caller_issues(tree)
    out["issues"].extend(ext)
    out["issues"].extend(public_api_issues(tree))
    out["style_notes"] = notes + internal_style_notes(tree)
    return out


def run(file_path=None):
    report = {"schema": "check_chat_daily_v3",
              "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
              "root": ROOT, "mode": "file" if file_path else "default",
              "chat_daily": {}, "targets": {}, "issues": [], "style_notes": [],
              "ok": True}
    cd = check_chat_daily(file_path=file_path)
    report["chat_daily"] = {k: cd[k] for k in ("file", "compile", "import")}
    report["issues"].extend(cd["issues"])
    report["style_notes"].extend(cd["style_notes"])
    if not file_path:
        others, targets = check_other_modules()
        report["issues"].extend(others)
        report["targets"] = targets
    report["n_issues"] = len(report["issues"])
    report["n_style_notes"] = len(report["style_notes"])
    report["ok"] = report["n_issues"] == 0
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="caller-authoritative post-edit guard")
    ap.add_argument("--file", default=None,
                    help="对指定 chat_daily 快照做 AST 校验（跳过 import；用于坏版本回归）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        rep = run(a.file)
    except Exception as exc:                  # noqa: BLE001
        print(json.dumps({"schema": "check_chat_daily_v3", "ok": False,
                          "error": repr(exc)}, ensure_ascii=False))
        return 2
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print("[chat_daily:%s] compile=%s import=%s" %
              (rep["chat_daily"]["file"], rep["chat_daily"]["compile"],
               rep["chat_daily"]["import"]))
        for name, t in rep["targets"].items():
            print("[%s] compile=%s import=%s" % (name, t["compile"], t["import"]))
        for i in rep["issues"]:
            print("[FAIL] %s %s %s %s" % (i.get("module", "chat_daily"), i["kind"],
                                          i["symbol"], i.get("detail", "")))
        for s in rep["style_notes"]:
            print("[NOTE] %s %s %s" % (s["kind"], s["symbol"], s["detail"]))
        print("SUMMARY issues=%d style_notes=%d ok=%s" %
              (rep["n_issues"], rep["n_style_notes"], rep["ok"]))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())