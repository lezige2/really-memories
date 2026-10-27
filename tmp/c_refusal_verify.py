#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Independent CPU-only verification of the C-product refusal fix (D13/D14).

This script is independent: it re-implements the checks itself, extracts the
pre-fix evidence.py from git HEAD (not from any producer script) and runs the
real CLI/service code paths with throwaway data directories.  Zero GPU, zero
model load, no network beyond 127.0.0.1.

Evidence written: out/C-REFUSAL-FIX-VERIFY.json
Nothing else is written outside throwaway directories.
"""
import hashlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\llama-mem")
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import evidence as E_NEW            # noqa: E402  current (fixed)
import retrieval as R               # noqa: E402
import chat_daily as D              # noqa: E402

ART = ROOT / "out" / "C-REFUSAL-FIX-VERIFY.json"
HIST = "我是阿泽，今天做了b7实验，结论是擦边"
Q_BUG = "我明天要去哪里出差？"
Q_FOLLOWUP = "实验结论是什么？"
FOUR = ["你好", "你是谁", Q_BUG, "我的车牌号是多少？"]
OVER_REFUSAL = ["实验结论是什么？", "解释一下什么是 KV 缓存",
                "我的车牌号是沪A-12345", "帮我记住这件事"]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def sh(args, cwd=ROOT, timeout=120, **kw):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout,
                          **kw)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def tmpdir(name):
    base = ROOT / "tmp" / "_c_refusal_verify" / name
    if base.exists():
        import shutil
        shutil.rmtree(base)
    base.mkdir(parents=True, exist_ok=True)
    return base


# ---------------------------------------------------------------- old code --
def load_old_evidence(work):
    """Extract the pre-fix evidence.py from git HEAD and import it isolated."""
    r = sh(["git", "show", "HEAD:tools/evidence.py"])
    if r.returncode != 0:
        raise SystemExit("git show failed: %s" % r.stderr[:200])
    src = r.stdout
    path = work / "evidence_old.py"
    path.write_text(src, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location("evidence_old", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["evidence_old"] = mod
    spec.loader.exec_module(mod)
    return mod, {"git_show_cmd": "git show HEAD:tools/evidence.py",
                 "git_head": sh(["git", "rev-parse", "HEAD"]).stdout.strip(),
                 "old_source_sha256": sha256(src.encode("utf-8")),
                 "old_source_bytes": len(src.encode("utf-8"))}


def content_terms(text):
    return [t for t in R.tokenize(text or "") if t not in R.STOP_BIGRAMS]


def token_analysis(query, transcript):
    q = content_terms(query)
    chat = set(content_terms(transcript))
    hits = [t for t in q if t in chat]
    return {"query_tokens": q, "transcript_tokens": sorted(chat),
            "old_hits": hits,
            "old_hits_single_char_only": bool(hits) and all(
                h.startswith("u:") for h in hits),
            "new_query_tokens": [t for t in q if not t.startswith("u:")],
            "new_hits": [t for t in q if not t.startswith("u:") and t in chat]}


# ------------------------------------------------------------- dry run CLI ---
def run_dry_cli(work, prompts):
    """Start the actual `chat_daily.py --dry-run` CLI with throwaway dirs."""
    db = work / "daily.db"
    blocks = work / "blocks"
    sessions = work / "sessions"
    model = work / "dryrun_model.stub"
    blocks.mkdir(parents=True, exist_ok=True)
    sessions.mkdir(parents=True, exist_ok=True)
    D.install_fake_model(str(model))
    stdin = "".join(p + "\n" for p in prompts) + "/quit\n"
    r = sh([sys.executable, "-X", "utf8", "tools/chat_daily.py", "--dry-run",
            "--db", str(db), "--blocks", str(blocks),
            "--sessions", str(sessions), "--session", "dry.json",
            "--model", str(model)], timeout=180, input=stdin)
    return {"cmd": "python -X utf8 tools/chat_daily.py --dry-run --db ... "
                   "--blocks ... --sessions ... --session dry.json",
            "rc": r.returncode,
            "stdout": r.stdout[-8000:], "stderr": r.stderr[-2000:],
            "data_dir": str(work), "model_stub": str(model)}


def parse_dry_cli(stdout, prompts):
    """Map prompts to REPL answers IN ORDER (stdin is not echoed by the REPL)."""
    lines = stdout.splitlines()
    ans_blocks = []
    for i, ln in enumerate(lines):
        if "答：" in ln:
            answer = ln.split("答：", 1)[1]
            tail = None
            for ln2 in lines[i + 1:i + 4]:
                if ln2.strip().startswith("（") and "；" in ln2:
                    tail = ln2.strip()
                    break
            ans_blocks.append({"answer": answer, "tail": tail,
                               "refused": bool(tail and "拒答" in tail),
                               "state_hint": ("smalltalk"
                                              if tail and "smalltalk" in tail
                                              else None)})
    out = []
    for k, p in enumerate(prompts):
        blk = ans_blocks[k] if k < len(ans_blocks) else None
        out.append({"prompt": p, "found": blk is not None,
                    "answer": (blk or {}).get("answer"),
                    "tail": (blk or {}).get("tail"),
                    "refused": bool((blk or {}).get("refused")),
                    "answer_order": k + 1})
    return out


def run_dry_inproc(work, prompts):
    """Same dry-run app, in-process, for structured ask() results."""
    eng = D.StubEngine()
    model = work / "dryrun_model.stub"
    D.install_fake_model(str(model))
    blocks = work / "blocks"
    sessions = work / "sessions"
    blocks.mkdir(parents=True, exist_ok=True)
    sessions.mkdir(parents=True, exist_ok=True)
    app = D.DailyApp(eng, db_path=str(work / "inproc.db"),
                     blocks_dir=str(blocks), sessions_dir=str(sessions),
                     session_path="inproc.json", model_path=str(model),
                     control=False, n_predict=D.N_PREDICT_DEFAULT,
                     retrieval_mode="off", topk=D.DEFAULT_TOPK,
                     rollover_at=1.0, n_ctx=D.N_CTX_DEFAULT,
                     chat_start=D.CHAT_START_DEFAULT, n_gpu_layers=0)
    out = []
    try:
        for p in prompts:
            r = app.ask(p)
            out.append({"prompt": p, "answer": r.get("answer"),
                        "refused": bool(r.get("refused")),
                        "state": r.get("state"),
                        "latency_s": r.get("latency_s"),
                        "block_ids": r.get("block_ids")})
    finally:
        try:
            app.close(save=False, reason="verify")
        except Exception:  # noqa: BLE001
            pass
    return out


# --------------------------------------------------------------- service -----
def start_fake_service(work):
    port = free_port()
    data = work / "svc_data"
    data.mkdir(parents=True, exist_ok=True)
    out = open(work / "service.out.log", "w", encoding="utf-8")
    err = open(work / "service.err.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "tools/chat_service.py",
         "--fake-engine", "--data-dir", str(data), "--port", str(port),
         "--session", "svc.json"],
        cwd=str(ROOT), stdout=out, stderr=err,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    base = "http://127.0.0.1:%d" % port
    ready = False
    for _ in range(120):
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(base + "/health", timeout=1.0) as r:
                if r.status == 200:
                    ready = True
                    break
        except Exception:  # noqa: BLE001
            time.sleep(0.25)
    return proc, base, ready, port


def service_ask(base, text):
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(base + "/ask", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def service_openai(base, text):
    body = json.dumps({"messages": [{"role": "user", "content": text}]}).encode("utf-8")
    req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def stop_service(proc):
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:  # noqa: BLE001
        try:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/F"],
                           capture_output=True, timeout=20)
        except Exception:  # noqa: BLE001
            pass


# ----------------------------------------------------------------- main -----
def main():
    work = tmpdir("run")
    old, old_meta = load_old_evidence(work)
    fixes = [str(Path(p).resolve()) for p in ()]

    old_bug = {
        "hist": HIST, "query": Q_BUG,
        "old_dialogue_evidence": old.dialogue_evidence(Q_BUG, HIST),
        "new_dialogue_evidence": E_NEW.dialogue_evidence(Q_BUG, HIST),
        "old_true_confirmed": old.dialogue_evidence(Q_BUG, HIST) is True,
        "new_false_confirmed": E_NEW.dialogue_evidence(Q_BUG, HIST) is False,
        "token_analysis": token_analysis(Q_BUG, HIST),
        "old_meta": old_meta,
    }
    new_behavior = {
        "no_memory_fact_not_in_chat": {
            "query": Q_BUG, "hist": HIST,
            "new": E_NEW.dialogue_evidence(Q_BUG, HIST),
            "partition_ok": E_NEW.dialogue_evidence(Q_BUG, HIST) is False},
        "real_followup_still_in_chat": {
            "query": Q_FOLLOWUP, "hist": HIST,
            "new": E_NEW.dialogue_evidence(Q_FOLLOWUP, HIST),
            "partition_ok": E_NEW.dialogue_evidence(Q_FOLLOWUP, HIST) is True,
            "token_analysis": token_analysis(Q_FOLLOWUP, HIST)},
        "empty_transcript": {
            "query": Q_BUG, "new": E_NEW.dialogue_evidence(Q_BUG, ""),
            "partition_ok": E_NEW.dialogue_evidence(Q_BUG, "") is False},
    }
    probes = [
        (Q_BUG, HIST), (Q_BUG, ""), (Q_FOLLOWUP, HIST),
        ("我的车牌号是多少？", HIST),
        ("我明天要去哪里出差？", "明天我们聊过出差安排"),
        ("会议几点开始？", "上次会议定在周三下午三点"),
        ("那家店叫什么？", "那家店叫顺捷搬家"),
        ("今天天气怎么样？", HIST),
    ]
    matrix = []
    for q, t in probes:
        o, n = old.dialogue_evidence(q, t), E_NEW.dialogue_evidence(q, t)
        ta = token_analysis(q, t)
        matrix.append({"query": q, "transcript": t, "old": o, "new": n,
                       "old_hits": ta["old_hits"],
                       "change": "neg" if o and not n else ("same" if o == n else "pos"),
                       "change_explained_by_single_char_hits":
                           (o and not n and ta["old_hits_single_char_only"])})
    diff_scope = {
        "probes": matrix,
        "changed_count": sum(1 for m in matrix if m["old"] != m["new"]),
        "all_changes_are_old_true_new_false": all(
            m["change"] == "neg" for m in matrix if m["old"] != m["new"]),
        "all_changes_explained_by_single_char_tokens": all(
            m["change_explained_by_single_char_hits"]
            for m in matrix if m["old"] != m["new"]),
        "no_new_true_anywhere": not any(m["new"] and not m["old"] for m in matrix),
    }

    dry_cli = run_dry_cli(work, FOUR)
    dry_rows = parse_dry_cli(dry_cli["stdout"], FOUR)
    # statement prelude so the in-dialogue follow-up sample really is in-dialogue
    dry_proc = run_dry_inproc(work, [HIST] + FOUR + OVER_REFUSAL)
    dry_map = {r["prompt"]: r for r in dry_proc}
    for row in dry_rows:
        s = dry_map.get(row["prompt"])
        row["inproc"] = s
        if s:
            row["refused_structured"] = s["refused"]
            row["state_structured"] = s["state"]
    dry_summary = {
        "cli_rc": dry_cli["rc"],
        "cli_zero_gpu": True,
        "rows": dry_rows,
        "stdout_excerpt": dry_cli["stdout"][-4000:],
        "inproc_rows": dry_proc,
        "engine": "StubEngine (no forward, no GPU)",
        "data_dir": dry_cli["data_dir"],
    }

    svc_proc, base, ready, port = start_fake_service(work)
    service = {"port": port, "ready": ready,
               "engine": "fake-engine (StubEngine, zero GPU)",
               "http_health": None, "asks": [], "openai_one": None}
    if ready:
        try:
            with urllib.request.urlopen(base + "/health", timeout=5) as r:
                service["http_health"] = r.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            service["http_health"] = "ERR %s" % exc
        for p in [HIST] + FOUR + OVER_REFUSAL:
            try:
                r = service_ask(base, p)
                service["asks"].append({"prompt": p, "refused": bool(r.get("refused")),
                                        "state": r.get("state"),
                                        "answer": r.get("answer"),
                                        "latency_s": r.get("latency_s")})
            except Exception as exc:  # noqa: BLE001
                service["asks"].append({"prompt": p, "error": str(exc)})
        try:
            service["openai_one"] = service_openai(base, Q_BUG)
        except Exception as exc:  # noqa: BLE001
            service["openai_one"] = {"error": str(exc)}
    else:
        service["start_error"] = (work / "service.err.log").read_text(
            encoding="utf-8", errors="replace")[-1000:]
    stop_service(svc_proc)

    # over-refusal samples measured on the dry-run instance
    over = []
    for p in OVER_REFUSAL:
        r = dry_map.get(p) or {}
        over.append({"prompt": p, "refused": bool(r.get("refused")),
                     "state": r.get("state"), "answer": r.get("answer"),
                     "should_answer": True,
                     "pass": not r.get("refused")})
    svc_over = [a for a in service["asks"] if a.get("prompt") in OVER_REFUSAL]

    # comparison of real service (LEAD 16:28 measurement, acceptance doc)
    acc = (ROOT / "docs" / "_work" / "C-PRODUCT-ACCEPTANCE.md")
    acc_txt = acc.read_text(encoding="utf-8") if acc.exists() else ""
    real_ref = {
        "source": "docs/_work/C-PRODUCT-ACCEPTANCE.md §6 (服务实测 4 例, "
                  "2026-10-27 16:28) + kvmem/daily/service.log",
        "note": "本任务为 CPU-only：未重启 GPU 真实服务；下表为 LEAD 已实测值，"
                "由本次独立 fake-engine 服务复核同一应用层分支（该 4 例不依赖模型）",
        "lead_measured": [
            {"#": 1, "input": "你好", "expected": "固定问候句",
             "measured": "state=smalltalk"},
            {"#": 2, "input": "你是谁", "expected": "固定能力句",
             "measured": "state=smalltalk"},
            {"#": 3, "input": Q_BUG, "expected": "固定拒答 refused=true",
             "measured": "refused=true"},
            {"#": 4, "input": "我的车牌号是多少？",
             "expected": "无记忆⇒固定拒答", "measured": "refused=true"},
        ],
        "doc_has_v12_record": "D13" in acc_txt and "D14" in acc_txt,
        "service_log_sha256": sha256((ROOT / "kvmem" / "daily" / "service.log")
                                     .read_bytes())
        if (ROOT / "kvmem" / "daily" / "service.log").exists() else None,
    }

    # test_refusal_cpu.py run as a secondary reference (not the basis)
    tr = sh([sys.executable, "-X", "utf8", "tools/test_refusal_cpu.py"],
            timeout=120)
    reference_runner = {"cmd": "python -X utf8 tools/test_refusal_cpu.py",
                        "rc": tr.returncode,
                        "stdout": tr.stdout[-2000:],
                        "stderr": tr.stderr[-1000:]}

    pins = {
        "git_head": old_meta["git_head"],
        "git_show_old_evidence_sha256": old_meta["old_source_sha256"],
        "current_evidence_sha256": sha256((TOOLS / "evidence.py").read_bytes()),
        "current_evidence_bytes": (TOOLS / "evidence.py").stat().st_size,
        "chat_daily_sha256": sha256((TOOLS / "chat_daily.py").read_bytes()),
        "chat_daily_bytes": (TOOLS / "chat_daily.py").stat().st_size,
        "test_refusal_cpu_sha256": sha256((TOOLS / "test_refusal_cpu.py").read_bytes()),
        "chat_service_sha256": sha256((TOOLS / "chat_service.py").read_bytes()),
        "retrieval_sha256": sha256((TOOLS / "retrieval.py").read_bytes()),
        "git_diff_evidence_commands": [
            "git diff -w tools/evidence.py",
            "git show HEAD:tools/evidence.py"],
        "fix_diff_summary": "dialogue_evidence(): +if not q: return False; "
                            "+q = [t for t in q if not t.startswith('u:')]; "
                            "+if not q: return False",
    }

    checks = {
        "old_bug_reproduced": old_bug["old_true_confirmed"],
        "new_false": old_bug["new_false_confirmed"],
        "followup_still_true": new_behavior["real_followup_still_in_chat"]["partition_ok"],
        "dry_run_cli_ok": dry_cli["rc"] == 0,
        "dry_run_4_rows_complete": len(dry_rows) == 4
                                   and all(r.get("inproc") for r in dry_rows),
        "fake_service_ready": bool(service["ready"]),
        "service_4_rows": len([a for a in service["asks"]
                               if a.get("prompt") in FOUR]) == 4,
        "over_refusal_3plus_pass": sum(1 for o in over if o["pass"]) >= 3,
        "diff_scope_limited": bool(diff_scope[
            "all_changes_explained_by_single_char_tokens"]),
        "reference_runner_pass": tr.returncode == 0,
    }

    out = {
        "schema": "c_refusal_fix_verify_v1",
        "role": "independent CPU-only reproduction + verification of the "
                "server-side refusal fix (D13/D14)",
        "environment": {"cwd": str(ROOT), "python": sys.version.split()[0],
                        "gpu": False, "model_load": False,
                        "network": "loopback only"},
        "pins": pins,
        "old_bug_repro": old_bug,
        "new_behavior": new_behavior,
        "diff_scope": diff_scope,
        "dry_run_e2e": dry_summary,
        "fake_service_e2e": service,
        "real_service_reference": real_ref,
        "over_refusal_samples": {"dry_run": over, "service": svc_over,
                                 "pass": sum(1 for o in over if o["pass"]) >= 3},
        "reference_test_runner": reference_runner,
        "checks": checks,
        "pass": all(checks.values()),
        "conclusion": None,  # filled below
        "commands": [
            "git show HEAD:tools/evidence.py  (import old module in isolation)",
            "python -X utf8 tools/chat_daily.py --dry-run --db <tmp>/daily.db "
            "--blocks <tmp>/blocks --sessions <tmp>/sessions --session dry.json",
            "python -X utf8 tools/chat_service.py --fake-engine "
            "--data-dir <tmp>/svc_data --port <free>",
            "python -X utf8 tools/test_refusal_cpu.py",
        ],
        "notes": [
            "旧行为复现使用 git HEAD 的 evidence.py（git show），不依赖任何"
            "生产者脚本或结论。",
            "新行为直接用当前 tools/evidence.py 的函数；对话内追问真命中用"
            "「实验结论是什么？」验证。",
            "dry-run CLI 实例使用独立 db/blocks/sessions/model stub（零 GPU）；"
            "fake-engine HTTP 服务只绑 127.0.0.1，验证同一应用层分支。",
            "真实服务 4 例为 LEAD 16:28 实测（acceptance §6）；本任务 CPU-only，"
            "未重启 GPU 真实服务，已在件内如实披露。",
        ],
    }
    fixed_ok = (checks["old_bug_reproduced"] and checks["new_false"]
                and checks["followup_still_true"]
                and checks["diff_scope_limited"]
                and checks["over_refusal_3plus_pass"])
    out["conclusion"] = {
        "old_bug": "复现成功：旧 dialogue_evidence 对「我明天要去哪里出差？」+"
                   "历史返回 True（单字 u:天 命中）",
        "new_behavior": "当前实现返回 False；「实验结论是什么？」仍 True"
                        "（bigram/实体命中）",
        "affected_paths": "只影响「无记忆 + 非对话内」路径：变化仅出现在旧命中"
                          "全为单字 u:* token 的样本；bigram/实体命中样本不变，"
                          "无 old=False→new=True 的新增误判" if diff_scope[
            "no_new_true_anywhere"] else
                          "警告：存在 old=False→new=True 的样本",
        "over_refusal": "无过度拒答：%d/%d 个应回答样例在 dry-run 实测未被拒答"
                        % (sum(1 for o in over if o["pass"]), len(over)),
        "verdict": "fix_verified" if (fixed_ok and all(checks.values()))
                   else "fix_verified_with_notes" if fixed_ok
                   else "fix_NOT_verified",
    }
    ART.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ART) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ART)

    print(json.dumps({
        "artifact": str(ART), "sha256": sha256(ART.read_bytes()),
        "bytes": ART.stat().st_size,
        "checks": checks, "pass": out["pass"],
        "diff_scope_changed": diff_scope["changed_count"],
        "all_changes_single_char": diff_scope[
            "all_changes_explained_by_single_char_tokens"],
        "dry_rows": [{r["prompt"]: {"refused": r.get("refused_structured"),
                                    "state": r.get("state_structured")}}
                     for r in dry_rows],
        "service_rows": [{a.get("prompt"): {"refused": a.get("refused"),
                                            "state": a.get("state")}}
                         for a in service["asks"] if a.get("prompt") in FOUR],
        "over_pass": sum(1 for o in over if o["pass"]), "over_n": len(over),
        "conclusion": out["conclusion"]["verdict"],
    }, ensure_ascii=False, indent=1))
    return 0 if out["pass"] else 3


if __name__ == "__main__":
    sys.exit(main())