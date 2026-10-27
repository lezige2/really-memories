#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""真实对话驱动的行为回归评测（零 GPU；dry-run StubEngine，独立数据目录）。

读 tmp/behavior_eval_cases.json（≥40 条，来自 2026-10-27 真实使用 + 用户贴出的
真实对话），每条用独立实例跑 chat_daily 应用层：寒暄/身份/记忆库查询/联网/感叹/
陈述自动记忆/记忆问答（fake rows）/未知事实拒答/混合句/对话内追问/世界知识。

判分只覆盖应用层可判定的东西：state、refused、答案包含/排除、记忆增量、block_ids。
stub 引擎的答案正文不参与语义判分（对记忆命中类只判 state/block_ids）。

输出：out/BEHAVIOR-EVAL.json（逐条 pass/fail + 失败归类 + 汇总率 + 实际输出摘要）
只写 tmp/out；不改冻结件、不 commit、不跑 GPU。
"""
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import chat_daily as D  # noqa: E402

# 确定性：产品声明"不联网"，评测在进程内把联网检索 mock 成 None（不访问网络）。
# 这样 --dry-run 的行为完全可复现；联网可用时"web 分支抢占记忆"的现象另见
# artifact.diagnostics（手工探针记录）。
WEB_OFFLINE_MOCKED = True
try:
    D.web_lookup.lookup_text = lambda *a, **k: None
except Exception:  # noqa: BLE001
    WEB_OFFLINE_MOCKED = False

CASES = ROOT / "tmp" / "behavior_eval_cases.json"
ART = ROOT / "out" / "BEHAVIOR-EVAL.json"


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def new_app(tag):
    base = Path(tempfile.mkdtemp(prefix="beval_%s_" % tag))
    (base / "blocks").mkdir(parents=True, exist_ok=True)
    (base / "sessions").mkdir(parents=True, exist_ok=True)
    model = base / "stub.model"
    D.install_fake_model(str(model))
    eng = D.StubEngine()
    app = D.DailyApp(eng, db_path=str(base / "daily.db"),
                     blocks_dir=str(base / "blocks"),
                     sessions_dir=str(base / "sessions"),
                     session_path="case.json", model_path=str(model),
                     control=False, n_predict=D.N_PREDICT_DEFAULT,
                     retrieval_mode="off", topk=D.DEFAULT_TOPK,
                     rollover_at=1.0, n_ctx=D.N_CTX_DEFAULT,
                     chat_start=D.CHAT_START_DEFAULT, n_gpu_layers=0)
    return app, base


def run_case(case):
    cid = case["id"]
    app, base = new_app(cid)
    prelude_log = []
    try:
        for act in case.get("prelude") or []:
            action = act.get("action")
            text = act.get("text") or ""
            if action == "remember":
                r = app.remember(text)
                prelude_log.append({"action": "remember", "ok": True,
                                    "result": {k: r.get(k) for k in
                                               ("id", "duplicate")} if isinstance(r, dict) else r})
            elif action == "ask":
                r = app.ask(text)
                prelude_log.append({"action": "ask", "state": r.get("state"),
                                    "refused": r.get("refused")})
            else:
                raise ValueError("unknown prelude action %r" % action)
        mem_before = len(app.memories())
        t0 = time.perf_counter()
        res = app.ask(case["input"])
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        mem_after = len(app.memories())
    finally:
        try:
            app.close(save=False, reason="behavior_eval")
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(base, ignore_errors=True)

    answer = str(res.get("answer") or "")
    state = res.get("state")
    refused = bool(res.get("refused"))
    blocks = list(res.get("block_ids") or [])
    delta = mem_after - mem_before

    problems = []
    categories = []
    if "expect_refusal" in case:
        exp = bool(case["expect_refusal"])
        if exp and not refused:
            categories.append("under_refusal")
            problems.append("应拒答但未拒答")
        if not exp and refused:
            categories.append("over_refusal")
            problems.append("不应拒答但被拒答")
    allowed_states = []
    if "expect_state" in case:
        allowed_states = [case["expect_state"]]
    if "expect_state_any" in case:
        allowed_states += list(case["expect_state_any"])
    if allowed_states and state not in allowed_states:
        categories.append("state_mismatch")
        problems.append("state=%r 不在预期 %r" % (state, allowed_states))
    if case.get("expect_block_ids_nonempty") and not blocks:
        categories.append("memory_miss")
        problems.append("预期记忆命中但 block_ids 为空")
    if "expect_memory_delta" in case and delta != case["expect_memory_delta"]:
        categories.append("memory_delta_mismatch")
        problems.append("记忆增量 %d != 预期 %d"
                        % (delta, case["expect_memory_delta"]))
    contains = case.get("expect_contains") or []
    miss = [s for s in contains if s not in answer]
    if miss:
        categories.append("content_missing")
        problems.append("缺少内容 %r" % miss)
    anyof = case.get("expect_contains_any") or []
    if anyof and not any(s in answer for s in anyof):
        categories.append("content_missing_any")
        problems.append("未包含任一 %r" % anyof)
    forbidden = [s for s in (case.get("expect_not_contains") or [])
                 if s in answer]
    if forbidden:
        categories.append("content_forbidden")
        problems.append("出现禁止内容 %r" % forbidden)
    passed = not problems
    return {
        "id": cid, "category": case.get("category"), "input": case["input"],
        "prelude": prelude_log,
        "expect": {k: case[k] for k in case
                   if k.startswith("expect_")},
        "actual": {"answer": answer, "state": state, "refused": refused,
                   "block_ids": blocks, "memory_delta": delta,
                   "memory_before": mem_before, "memory_after": mem_after,
                   "latency_ms": latency_ms},
        "pass": passed, "failure_categories": categories,
        "problems": problems, "note": case.get("note", ""),
    }


def main():
    if not CASES.exists():
        print(json.dumps({"status": "FAIL", "reason": "cases missing"},
                         ensure_ascii=False))
        return 2
    raw = CASES.read_bytes()
    doc = json.loads(raw)
    cases = doc.get("cases") or []
    ids = [c.get("id") for c in cases]
    if len(cases) < 40:
        print(json.dumps({"status": "FAIL",
                          "reason": "cases < 40: %d" % len(cases)},
                         ensure_ascii=False))
        return 2
    if len(set(ids)) != len(ids):
        print(json.dumps({"status": "FAIL", "reason": "duplicate ids"},
                         ensure_ascii=False))
        return 2

    t0 = time.time()
    results = []
    for c in cases:
        try:
            results.append(run_case(c))
        except Exception as exc:  # noqa: BLE001
            results.append({
                "id": c.get("id"), "category": c.get("category"),
                "input": c.get("input"), "pass": False,
                "failure_categories": ["exception"],
                "problems": ["%s: %s" % (type(exc).__name__, exc)],
                "actual": {}, "expect": {}, "note": c.get("note", ""),
            })

    n = len(results)
    npass = sum(1 for r in results if r["pass"])
    failures = [r for r in results if not r["pass"]]
    by_cat = {}
    for r in results:
        c = r.get("category") or "unknown"
        e = by_cat.setdefault(c, {"n": 0, "pass": 0, "fail": 0})
        e["n"] += 1
        e["pass" if r["pass"] else "fail"] += 1
    fail_cat = {}
    for r in failures:
        for c in r["failure_categories"] or ["unknown"]:
            fail_cat[c] = fail_cat.get(c, 0) + 1
    out = {
        "schema": "behavior_eval_v1",
        "role": "真实对话驱动的应用层行为回归（2026-10-27 真实使用；零 GPU）",
        "source_cases": {
            "path": "tmp/behavior_eval_cases.json",
            "sha256": sha256(raw), "bytes": len(raw),
            "n_cases": len(cases), "schema": doc.get("schema"),
            "source": doc.get("source"),
        },
        "runner": {
            "path": "tmp/run_behavior_eval.py",
            "sha256": sha256(Path(__file__).read_bytes()),
            "app_version": getattr(D, "VERSION", None),
            "engine": "StubEngine (dry-run; no forward, no GPU)",
            "isolation": "每条 case 独立 db/blocks/sessions 临时目录",
            "eval_scope": "应用层 state/refused/内容包含/记忆增量/block_ids；"
                          "stub 正文不做语义判分",
            "web_offline_mocked": WEB_OFFLINE_MOCKED,
        },
        "pins": {
            "chat_daily_sha256": sha256((TOOLS / "chat_daily.py").read_bytes()),
            "evidence_sha256": sha256((TOOLS / "evidence.py").read_bytes())
            if (TOOLS / "evidence.py").exists() else None,
        },
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)),
        "elapsed_s": round(time.time() - t0, 3),
        "summary": {
            "n": n, "pass": npass, "fail": len(failures),
            "pass_rate": round(npass / n, 6) if n else None,
            "by_category": by_cat,
            "failure_categories": fail_cat,
        },
        "failures": failures,
        "results": results,
        "diagnostics": {
            "network_on_observation": "手工探针（未 mock 联网）显示："
                "「我几点开会？」及「谢谢/在吗 + 我几点开会？」会走 web 检索"
                "（state=web、block_ids 为空），即 search 分支抢占已命中的记忆；"
                "默认评测把联网 mock 成 None 以保持确定性，该现象需单独修复。",
            "retrieval_recall_note": "记忆问答为词面 bigram 检索；"
                "「我爱吃什么」与记忆「只喝美式咖啡，不吃香菜」无 bigram 重合，"
                "属已知词面召回限制（不是拒答策略 bug）。",
        },
        "notes": [
            "失败清单即下一轮修复候选；按 failure_categories 归类。",
            "真号/产品验收另见 docs/QQ-ACCEPTANCE.md；本件不进研究线引用链。",
        ],
    }
    ART.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)

    print("== BEHAVIOR EVAL: %d/%d pass (%.1f%%) =="
          % (npass, n, 100.0 * npass / n if n else 0))
    print("failures: %d" % len(failures))
    for r in failures:
        a = r.get("actual") or {}
        print("FAIL %-4s [%s] %r" % (r["id"], ",".join(r["failure_categories"]),
                                     r["input"]))
        print("      state=%r refused=%r blocks=%r mem_delta=%r"
              % (a.get("state"), a.get("refused"), a.get("block_ids"),
                 a.get("memory_delta")))
        print("      answer=%r" % (str(a.get("answer"))[:160],))
        print("      why=%s" % "; ".join(r["problems"]))
    print("artifact:", ART)
    print("sha256:", sha256(ART.read_bytes()))
    return 0 if not failures else 3


if __name__ == "__main__":
    sys.exit(main())