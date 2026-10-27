#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""T6: 生成→核对→一次修复→固定兜底 的端到端 A/B 评测（fake engine，零 GPU）。

两组：
  VERIFY=on （默认）  期望：personal 答案不得含块外具体值；错值被核对拦下 → 一次
                      修复后出现正确值；修复仍不符 → 固定兜底；general/无记忆按契约跳过。
  VERIFY=off          期望：基线不核对（final≈primary），用于 A/B 对照。

实现方式：parent 以两个子进程（--worker，各自先 import chat_daily，确保
LLAMA_MEM_VERIFY 在 import 时生效）分别跑全部 case；child 用 ScriptedEngine 按
case 给出 primary/repair 文本。mount 路径决定性验证；child 将 chat_daily._iso
置 None（fake engine 无独立 seq，isolated 路径由 CPU 用例覆盖），web_lookup
mock 为 None（不联网）。

输出：out/VERIFY-E2E.json（逐 case ON/OFF 结果、断言、失败归类、A/B 差异、耗时）
只写该产物；不改代码/冻件、不 commit、不跑 GPU。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
TOOLS = ROOT / "tools"
CASES = ROOT / "tmp" / "verify_e2e_cases.json"
ART = ROOT / "out" / "VERIFY-E2E.json"
FALLBACK = "这条我没法从记忆里核对，先不猜。"


def sha256(b):
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------- worker -----
def worker():
    sys.path.insert(0, str(TOOLS))
    import chat_daily as D          # env already loaded by parent
    try:
        import answer_verifier as AV
    except Exception:                # noqa: BLE001
        AV = None
    D._iso = None                    # deterministic mount path under fake engine
    try:
        D.web_lookup.lookup_text = lambda *a, **k: None
    except Exception:                # noqa: BLE001
        pass

    class ScriptedEngine(D.StubEngine):
        def __init__(self, answers):
            super().__init__()
            self.queue = list(answers)
            self.calls = []

        def ask(self, seq, text, n_predict=32, pos=None):
            self.calls.append(str(text)[-80:])
            if not self.queue:
                return ""
            i = min(len(self.calls) - 1, len(self.queue) - 1)
            return self.queue[i]

    doc = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    for case in doc["cases"]:
        base = Path(tempfile.mkdtemp(prefix="ve2e_%s_" % case["id"]))
        try:
            (base / "blocks").mkdir()
            (base / "sessions").mkdir()
            model = base / "stub.model"
            D.install_fake_model(str(model))
            answers = [case.get("primary") or ""]
            if case.get("repair") is not None:
                answers.append(case["repair"])
            eng = ScriptedEngine(answers)
            app = D.DailyApp(eng, db_path=str(base / "daily.db"),
                             blocks_dir=str(base / "blocks"),
                             sessions_dir=str(base / "sessions"),
                             session_path="case.json", model_path=str(model),
                             control=False, n_predict=D.N_PREDICT_DEFAULT,
                             retrieval_mode="off", topk=D.DEFAULT_TOPK,
                             rollover_at=1.0, n_ctx=D.N_CTX_DEFAULT,
                             chat_start=D.CHAT_START_DEFAULT, n_gpu_layers=0)
            for m in case.get("memory") or []:
                app.remember(m)
            r = app.ask(case["question"])
            ans = str(r.get("answer") or "")
            res = {"id": case["id"], "answer": ans,
                   "state": r.get("state"), "refused": bool(r.get("refused")),
                   "block_ids": list(r.get("block_ids") or []),
                   "latency_s": r.get("latency_s"),
                   "verified": r.get("verified"),
                   "verify": r.get("verify"),
                   "verify_attempts": r.get("verify_attempts"),
                   "engine_calls": len(eng.calls),
                   "engine_prompts_tail": [c[:60] for c in eng.calls[:3]]}
            # 契约层独立复核：personal 非兜底答案不得含块外具体值
            if AV is not None:
                vals = AV.extract_values(ans)
                mem_texts = [str(m) for m in (case.get("memory") or [])]
                unsupported = [v for v in vals
                               if not any("".join(v.replace(",", "").split())
                                          in "".join(t.replace(",", "").split())
                                          for t in mem_texts)]
                res["unsupported_values_contract"] = unsupported
            app.close(save=False, reason="verify_e2e")
        except Exception as exc:      # noqa: BLE001
            res = {"id": case["id"], "error": "%s: %s"
                                       % (type(exc).__name__, exc)}
        finally:
            shutil.rmtree(base, ignore_errors=True)
        results.append(res)
    print(json.dumps({"verify_env": os.environ.get("LLAMA_MEM_VERIFY"),
                      "results": results}, ensure_ascii=False))
    return 0


# --------------------------------------------------------------- parent -----
def run_group(group):
    env = dict(os.environ)
    env["LLAMA_MEM_VERIFY"] = "1" if group == "on" else "0"
    r = subprocess.run([sys.executable, "-X", "utf8", __file__, "--worker"],
                       cwd=str(ROOT), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("worker %s failed rc=%s stderr=%s"
                         % (group, r.returncode, r.stderr[-800:]))
    return json.loads(r.stdout.strip().splitlines()[-1])


def evaluate_on(case, res, av):
    exp = case.get("expect_on") or {}
    problems = []
    cats = []
    ans = str(res.get("answer") or "")
    verify = res.get("verify") if isinstance(res.get("verify"), dict) else None
    verdict = (verify or {}).get("verdict")
    REFUSAL_MARK = ("没有提到", "不想猜", "记忆里没有", "没有这条",
                    "不知道", "不确定", "未提及", "没有记录")
    is_refusal = any(k in ans for k in REFUSAL_MARK)
    # generic
    lat = res.get("latency_s")
    if not isinstance(lat, (int, float)) or lat >= 90:
        problems.append("latency=%r >= 90s" % lat)
        cats.append("latency_exceeded")
    is_question = "？" in case["question"] or "?" in case["question"] \
        or any(k in case["question"] for k in ("多少", "哪", "几点", "几楼",
                                               "什么", "为什么", "什么时候"))
    short_circuit = is_refusal or res.get("state") in ("no_evidence",
                                                       "verify_fallback",
                                                       "ack", "identity",
                                                       "boundary", "smalltalk",
                                                       "capability")
    if (exp.get("state") is None and is_question and verify is None
            and not short_circuit):
        problems.append("verify 字段缺失")
        cats.append("verify_field_missing")
    allow_refusal = bool(exp.get("allow_refusal"))
    if "fallback" in exp:
        is_fb = ans.strip() == FALLBACK
        if exp["fallback"] == "any":
            if not (is_fb or is_refusal):
                problems.append("既非兜底也非拒答: %r" % ans[:60])
                cats.append("unexpected_answer")
        elif bool(exp["fallback"]) != is_fb:
            if not (allow_refusal and is_refusal and not exp["fallback"]):
                problems.append("fallback=%r != expected %r"
                                % (is_fb, exp["fallback"]))
                cats.append("unexpected_fallback" if not is_fb
                            else "missing_fallback")
    if allow_refusal and is_refusal:
        # 拒答/兜底时不要求出现主答案值，但仍要满足 final_not_contains
        pass
    anyof = exp.get("final_contains_any") or []
    if anyof and not any(x in ans for x in anyof):
        problems.append("missing any of %r" % anyof)
        cats.append("missing_expected_value")
    for need in exp.get("final_contains") or []:
        if need not in ans:
            problems.append("missing %r" % need)
            cats.append("missing_expected_value")
    for bad in exp.get("final_not_contains") or []:
        if bad in ans:
            problems.append("contains forbidden %r" % bad)
            cats.append("fabricated_value_leak")
    if "verified" in exp and res.get("verified") != exp["verified"]:
        problems.append("verified=%r != %r" % (res.get("verified"), exp["verified"]))
        cats.append("verified_flag_wrong")
    if "attempts" in exp and res.get("verify_attempts") != exp["attempts"]:
        problems.append("attempts=%r != %r"
                        % (res.get("verify_attempts"), exp["attempts"]))
        cats.append("attempts_wrong")
    if exp.get("state") and res.get("state") != exp["state"]:
        problems.append("state=%r != %r" % (res.get("state"), exp["state"]))
        cats.append("state_wrong")
    if exp.get("state_any") and res.get("state") not in exp["state_any"]:
        problems.append("state=%r not in %r" % (res.get("state"), exp["state_any"]))
        cats.append("state_wrong")
    if exp.get("verify_skipped"):
        if verdict not in ("skipped_general_no_memory", "skipped"):
            problems.append("verify verdict=%r not skipped" % verdict)
            cats.append("verify_not_skipped")
    # 契约层：personal 非兜底不得出现块外具体值
    personal_case = case.get("category") not in ("general_world",
                                                "statement_ack")
    if (personal_case and not ans.strip() == FALLBACK and not is_refusal
            and res.get("state") not in ("no_evidence", "ack", "identity",
                                         "boundary", "smalltalk", "capability",
                                         "verify_fallback")):
        uns = res.get("unsupported_values_contract") or []
        if uns:
            problems.append("块外具体值 %r" % uns)
            cats.append("fabricated_value_leak")
    # 根因提示：有 block_ids 但核对返回 no_evidence ⇒ 疑似 blocks 形态不匹配
    if res.get("block_ids") and verdict == "no_evidence":
        cats.append("suspected_blocks_contract_mismatch")
    return bool(not problems), problems, list(dict.fromkeys(cats))


def evaluate_off(case, on_res, off_res):
    exp = case.get("expect_on") or {}
    ans = str(off_res.get("answer") or "")
    problems = []
    verify = off_res.get("verify") if isinstance(off_res.get("verify"), dict) else None
    if verify and verify.get("verdict") not in ("disabled",):
        problems.append("VERIFY off 但 verify=%r" % verify.get("verdict"))
    if exp.get("state") != "ack" and exp.get("state_any") is None:
        def _nf(x):
            return str(x or "").strip().rstrip("。！？!?.,，；;~～ ")
        primary = _nf(case.get("primary"))
        on_ans = _nf((on_res or {}).get("answer"))
        refusal = any(k in ans for k in ("没有提到", "不想猜", "记忆里没有",
                                         "没有这条", "不知道", "不确定",
                                         "未提及", "没有记录"))
        if refusal and (on_ans == _nf(ans) or exp.get("allow_refusal")):
            pass
        elif primary and primary != _nf(ans):
            problems.append("OFF final != primary (%r vs %r)"
                            % (ans[:60], case.get("primary")[:60]))
    return bool(not problems), problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", action="store_true")
    a = ap.parse_args()
    if a.worker:
        return worker()

    raw = CASES.read_bytes()
    doc = json.loads(raw)
    cases = doc["cases"]
    if len(cases) < 25:
        print(json.dumps({"status": "FAIL", "reason": "cases < 25"},
                         ensure_ascii=False))
        return 2
    t0 = time.time()
    on = run_group("on")
    off = run_group("off")
    on_map = {r["id"]: r for r in on["results"]}
    off_map = {r["id"]: r for r in off["results"]}

    sys.path.insert(0, str(TOOLS))
    try:
        import answer_verifier as AV
    except Exception:                  # noqa: BLE001
        AV = None

    rows = []
    fail_cats = {}
    for case in cases:
        cid = case["id"]
        r_on = on_map.get(cid, {})
        r_off = off_map.get(cid, {})
        ok, problems, cats = evaluate_on(case, r_on, AV)
        ok_off, probs_off = evaluate_off(case, r_on, r_off)
        for c in cats:
            fail_cats[c] = fail_cats.get(c, 0) + 1
        rows.append({
            "id": cid, "category": case["category"],
            "question": case["question"], "memory": case.get("memory"),
            "primary": case.get("primary"),
            "verify_on": {k: r_on.get(k) for k in
                          ("answer", "state", "refused", "block_ids",
                           "latency_s", "verified", "verify",
                           "verify_attempts", "engine_calls",
                           "unsupported_values_contract")},
            "verify_off": {k: r_off.get(k) for k in
                           ("answer", "state", "verify", "latency_s")},
            "pass": bool(ok and ok_off),
            "problems": problems + probs_off,
            "failure_categories": cats,
            "ab_same_answer": (str(r_on.get("answer") or "")
                               == str(r_off.get("answer") or "")),
        })

    n = len(rows)
    npass = sum(1 for r in rows if r["pass"])
    ab_diff = sum(1 for r in rows if not r["ab_same_answer"])
    failures = [r for r in rows if not r["pass"]]
    by_cat = {}
    for r in rows:
        c = r["category"]
        e = by_cat.setdefault(c, {"n": 0, "pass": 0, "fail": 0})
        e["n"] += 1
        e["pass" if r["pass"] else "fail"] += 1
    out = {
        "schema": "verify_e2e_v1",
        "role": "T6 生成→核对→一次修复→固定兜底 端到端 A/B（fake engine，零 GPU）",
        "cases": {"path": "tmp/verify_e2e_cases.json", "sha256": sha256(raw),
                  "bytes": len(raw), "n": n},
        "runner": {"path": "tmp/run_verify_e2e.py",
                   "sha256": sha256(Path(__file__).read_bytes()),
                   "engine": "ScriptedEngine(StubEngine) / fake, zero GPU",
                   "groups": {"on": "LLAMA_MEM_VERIFY=1",
                              "off": "LLAMA_MEM_VERIFY=0"},
                   "isolation": "每条 case 独立 db/blocks/sessions；_iso=None；"
                                "web_lookup=None（不联网）"},
        "pins": {
            "chat_daily_sha256": sha256((TOOLS / "chat_daily.py").read_bytes()),
            "answer_verifier_sha256": sha256((TOOLS / "answer_verifier.py")
                                             .read_bytes())
            if (TOOLS / "answer_verifier.py").exists() else None,
            "fallback_text": FALLBACK,
        },
        "elapsed_s": round(time.time() - t0, 3),
        "summary": {"n": n, "pass": npass, "fail": len(failures),
                    "first_pass_rate": round(npass / n, 6) if n else None,
                    "ab_answer_diff": ab_diff,
                    "by_category": by_cat,
                    "failure_categories": fail_cats},
        "failures": failures,
        "results": rows,
        "notes": [
            "ON 组断言：personal 非兜底不得含块外值；修复后须含正确值；兜底文案固定；"
            "verify 字段存在；每轮 <90s。",
            "OFF 组用于 A/B：应保持 primary 答案且 verify.verdict=disabled。",
            "suspected_blocks_contract_mismatch：有 block_ids 但核对 no_evidence，"
            "通常表示传给核对器的 blocks 形态与接口不符（应 list[dict(text)]）。",
        ],
    }
    ART.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)

    print("== VERIFY E2E: %d/%d pass (%.1f%%), A/B answer-diff=%d =="
          % (npass, n, 100.0 * npass / n if n else 0, ab_diff))
    for r in failures[:12]:
        print("FAIL %-4s [%s] q=%r" % (r["id"], ",".join(r["failure_categories"]),
                                       r["question"]))
        print("     ON  ans=%r state=%r verify=%r attempts=%r"
              % (str((r["verify_on"] or {}).get("answer"))[:80],
                 (r["verify_on"] or {}).get("state"),
                 ((r["verify_on"] or {}).get("verify") or {}).get("verdict"),
                 (r["verify_on"] or {}).get("verify_attempts")))
        print("     OFF ans=%r why=%s"
              % (str((r["verify_off"] or {}).get("answer"))[:80],
                 "; ".join(r["problems"])[:160]))
    print("artifact:", ART)
    print("sha256:", sha256(ART.read_bytes()))
    return 0 if not failures else 3


if __name__ == "__main__":
    sys.exit(main())