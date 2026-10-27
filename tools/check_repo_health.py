# -*- coding: utf-8 -*-
"""check_repo_health.py -- 扫 tools/ 全部 .py：编译、悬空 self 调用、必需符号。

用途：改后守卫的第二道网（比 check_chat_daily 更广、更浅）。
规则：
  * 所有 tools/*.py：ast.parse + compile；失败 = error
  * 非 test_*.py 的类（仅无基类的类，避免继承误报）：
      self.<name>( 且 name 不在本类方法/类属性/实例属性/模块级定义 ⇒ 悬空
  * 关键模块（chat_daily/memory_service/web_lookup/qq_bridge）：import 冒烟 +
    必需方法/必需符号白名单（缺失 = error）
  * test_*.py 的悬空调用只记 warning（测试桩常见假属性），不阻断
输出：默认 JSON 到 stdout；`--out PATH` 同时写文件；exit 0=无 error，1=有 error。
只读，不改任何文件。
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
import check_chat_daily as GUARD          # noqa: E402  (复用同一份必需白名单)


def _class_issues(tree, module_names):
    out = []
    for c in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        if c.bases:                        # 继承类：静态无法判定，跳过
            continue
        methods, attrs = set(), set()
        for m in c.body:
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(m.name)
            elif isinstance(m, (ast.Assign, ast.AnnAssign)):
                targets = m.targets if isinstance(m, ast.Assign) else [m.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        attrs.add(t.id)
        for n in ast.walk(c):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                    and n.value.id == "self" and isinstance(n.ctx, (ast.Store, ast.Del)):
                attrs.add(n.attr)
        seen = set()
        for n in ast.walk(c):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id == "self"):
                continue
            a = n.func.attr
            if a.startswith("__") or a in methods or a in attrs or a in module_names:
                continue
            if a in seen:
                continue
            seen.add(a)
            out.append({"class": c.name, "symbol": a, "line": n.lineno})
    return out


def scan_file(path):
    name = os.path.basename(path)
    rec = {"file": name, "compile": "fail", "classes": 0, "issues": []}
    try:
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        compile(src, path, "exec")
        rec["compile"] = "ok"
    except (SyntaxError, UnicodeDecodeError) as exc:
        rec["issues"].append({"kind": "compile_fail", "severity": "error",
                              "symbol": name, "line": getattr(exc, "lineno", None),
                              "detail": str(exc)[:200]})
        return rec
    module_names = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_names.add(n.name)
    rec["classes"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    is_test = name.startswith("test_")
    for d in _class_issues(tree, module_names):
        rec["issues"].append({"kind": "dangling_self_call",
                              "severity": "warning" if is_test else "error",
                              "symbol": "%s.%s" % (d["class"], d["symbol"]),
                              "line": d["line"],
                              "detail": "self.%s( 无对应方法/类属性/实例属性/模块定义"
                                        % d["symbol"]})
    rec["n_issues"] = len(rec["issues"])
    rec["ok"] = not any(i["severity"] == "error" for i in rec["issues"])
    return rec


def check_key_modules(files_rec):
    """关键模块：复用 check_chat_daily（调用方权威）做 chat_daily，其余模块查必需符号。"""
    # chat_daily：调用方权威检查（内部 self 调用 + 外部 DailyApp 引用 + 公开 API）
    rec = files_rec.get("chat_daily.py")
    if rec is not None:
        try:
            importlib.invalidate_caches()
            importlib.import_module("chat_daily")
            rec["import"] = "ok"
        except Exception as exc:                  # noqa: BLE001
            rec["import"] = "fail"
            rec["issues"].append({"kind": "import_fail", "severity": "error",
                                  "symbol": "chat_daily", "line": None,
                                  "detail": str(exc)[:300]})
        try:
            cd = GUARD.check_chat_daily()
        except Exception as exc:                  # noqa: BLE001
            cd = {"issues": [{"kind": "guard_error", "symbol": "chat_daily",
                              "detail": repr(exc)}]}
        for i in cd.get("issues", []):
            rec["issues"].append({"kind": i["kind"], "severity": "error",
                                  "symbol": i.get("symbol"), "line": i.get("line"),
                                  "detail": i.get("detail", "")})
    for mod, spec in GUARD.OTHER_TARGETS.items():
        rec = files_rec.get(spec["file"])
        if rec is None:
            continue
        try:
            importlib.invalidate_caches()
            m = importlib.import_module(mod)
            rec["import"] = "ok"
        except Exception as exc:                  # noqa: BLE001
            rec["import"] = "fail"
            rec["issues"].append({"kind": "import_fail", "severity": "error",
                                  "symbol": mod, "line": None,
                                  "detail": str(exc)[:300]})
            continue
        for s in spec.get("required_symbols", []):
            if not hasattr(m, s):
                rec["issues"].append({"kind": "missing_required_symbol",
                                      "severity": "error", "symbol": s,
                                      "line": None, "detail": "必需符号缺失"})
        for cls_name, meths in spec.get("required_methods", {}).items():
            cls = getattr(m, cls_name, None)
            for meth in meths:
                if cls is None or not hasattr(cls, meth):
                    rec["issues"].append({"kind": "missing_required_method",
                                          "severity": "error",
                                          "symbol": "%s.%s" % (cls_name, meth),
                                          "line": None, "detail": "必需方法缺失"})
    return files_rec


def run():
    files_rec = {}
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py"):
            continue
        files_rec[fn] = scan_file(os.path.join(TOOLS, fn))
    check_key_modules(files_rec)
    # 同名符号合并（dangling + missing 同一方法只报一条，附双重证据）
    for rec in files_rec.values():
        merged = {}
        for i in rec["issues"]:
            key = i["symbol"].split(".")[-1]
            if key not in merged:
                merged[key] = dict(i)
                merged[key]["lines"] = ([i["line"]] if i.get("line") else [])
                merged[key].pop("line", None)
            else:
                m = merged[key]
                m["severity"] = "error"
                if i["kind"] != m["kind"]:
                    m["kind"] = "missing_symbol+dangling_call"
                m["detail"] = (m.get("detail", "") + "；" +
                               i.get("detail", "")).strip("；")
                if i.get("line"):
                    m["lines"].append(i["line"])
        rec["issues"] = list(merged.values())
        rec["n_issues"] = len(rec["issues"])
        rec["ok"] = not any(i["severity"] == "error" for i in rec["issues"])
    all_issues = []
    for fn, rec in files_rec.items():
        for i in rec["issues"]:
            all_issues.append({"file": fn, **i})
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    return {
        "schema": "check_repo_health_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": ROOT, "tools_dir": TOOLS,
        "files_scanned": len(files_rec),
        "summary": {"errors": len(errors), "warnings": len(warnings),
                    "files_with_errors": sorted({i["file"] for i in errors}),
                    "ok": not errors},
        "issues": all_issues,
        "files": {k: {"compile": v["compile"], "import": v.get("import", "skip"),
                      "classes": v["classes"], "n_issues": v["n_issues"],
                      "ok": v["ok"]} for k, v in files_rec.items()},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="repo-wide post-edit health scan")
    ap.add_argument("--out", default=None, help="另存 JSON 到该路径")
    ap.add_argument("--strict", action="store_true", help="warning 也计为失败")
    a = ap.parse_args(argv)
    try:
        rep = run()
    except Exception as exc:                      # noqa: BLE001
        print(json.dumps({"schema": "check_repo_health_v1", "ok": False,
                          "error": repr(exc)}, ensure_ascii=False))
        return 2
    txt = json.dumps(rep, ensure_ascii=False, indent=1)
    print(txt)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8", newline="\n").write(txt + "\n")
    bad = rep["summary"]["errors"] > 0 or (a.strict and rep["summary"]["warnings"] > 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())