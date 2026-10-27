# -*- coding: utf-8 -*-
"""test_verify_wiring_cpu.py -- T3/T4 wiring tests (zero GPU, mock verifier).

Covers: pass / unsupported->repair->pass / repair->unsupported->fallback /
no_evidence / verifier OFF / no-blocks-general / repair budget / blocks identity /
strip_continuation / F2 timeout / F3 seq6-busy / mount-path wiring / real verifier smoke.

Run: python -X utf8 tools/test_verify_wiring_cpu.py   (exit 0 = all pass)
"""
import os
import sys
import tempfile
import time

os.environ["LLAMA_MEM_MODE"] = "natural"       # must be set before importing
os.environ["LLAMA_MEM_VERIFY"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D  # noqa: E402

FAILS = []
TOTAL = [0]


def check(name, cond, detail=""):
    TOTAL[0] += 1
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


class FakeLogger:
    def __init__(self):
        self.events = []

    def log_ask(self, text, session_tokens=None, session_id=None, extra=None):
        return {"seq": 1}

    def log_answer(self, answer, ask_seq, block_ids, engine, latency_ms,
                   vram_gib=None, refused=False, **kw):
        self.events.append(("answer", latency_ms))

    def log_warning(self, code, message, evidence=None):
        self.events.append((code, evidence))

    def codes(self):
        return [e[0] for e in self.events if isinstance(e, tuple)]


class FakeVerifier:
    """Queue-driven mock: verdicts consumed per verify_answer() call."""

    def __init__(self, verdicts, strip=None):
        self.verdicts = list(verdicts)
        self.calls = []
        self.strip_calls = []
        self._strip = strip

    def verify_answer(self, question, answer, blocks, mode):
        self.calls.append({"question": question, "answer": answer,
                           "blocks": list(blocks), "mode": mode})
        v = self.verdicts.pop(0) if self.verdicts else "pass"
        return {"verdict": v, "mismatches": [] if v == "pass" else ["x"],
                "hint": ""}

    def strip_continuation(self, text):
        self.strip_calls.append(text)
        return self._strip(text) if self._strip else text


def make_app(tmp):
    app = D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=os.path.join(tmp, "model.stub"),
        restore=False,
        retrieval_mode="topk",
        logger=False,
    )
    app.logger = FakeLogger()
    return app


def no_repair(prompt):
    raise AssertionError("repair_generate must not be called")


def repair_const(text):
    def _r(prompt):
        return text
    return _r


def _install(av):
    D._get_verifier = lambda: av


def t_pass():
    av = FakeVerifier(["pass"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    ans, info = app._verified_finalize("q", "A", ["b"], "personal",
                                       no_repair, time.perf_counter(), "natural")
    check("pass_answer_kept", ans == "A", ans)
    check("pass_verified_true", info["verified"] is True)
    check("pass_verdict", info["verify"]["verdict"] == "pass")
    check("pass_no_repair", info["attempts"] == 0)


def t_repair_pass():
    av = FakeVerifier(["unsupported", "pass"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    prompts = []

    def repair(prompt):
        prompts.append(prompt)
        return "REPAIRED"

    ans, info = app._verified_finalize("我下周去哪", "OLD", ["上海开会"], "personal",
                                       repair, time.perf_counter(), "natural")
    check("repair_answer_used", ans == "REPAIRED", ans)
    check("repair_verified_true", info["verified"] is True)
    check("repair_attempts_1", info["attempts"] == 1)
    check("repair_prompt_has_blocks", "上海开会" in prompts[0])
    check("repair_prompt_has_question", "我下周去哪" in prompts[0])
    check("repair_prompt_has_prev_answer", "OLD" in prompts[0])
    check("repair_event_logged", "verify_repair" in app.logger.codes())


def t_repair_fail_fallback():
    av = FakeVerifier(["unsupported", "unsupported"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    ans, info = app._verified_finalize("q", "OLD", ["b"], "personal",
                                       repair_const("STILL_WRONG"),
                                       time.perf_counter(), "natural")
    check("second_fail_sentence", ans == D.VERIFY_FALLBACK_SENTENCE, ans)
    check("second_fail_state", info["state"] == "verify_fallback")
    check("second_fail_verified_false", info["verified"] is False)
    check("second_fail_attempts_1", info["attempts"] == 1)
    check("fallback_event_logged", "verify_fallback" in app.logger.codes())


def t_no_evidence():
    av = FakeVerifier(["no_evidence"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    ans, info = app._verified_finalize("q", "OLD", ["b"], "personal",
                                       no_repair, time.perf_counter(), "natural")
    check("no_evidence_sentence", ans == D.VERIFY_FALLBACK_SENTENCE)
    check("no_evidence_attempts_0", info["attempts"] == 0)
    check("no_evidence_state", info["state"] == "verify_fallback")


def t_verify_off():
    av = FakeVerifier(["unsupported"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    old = D.VERIFY_ENABLED
    D.VERIFY_ENABLED = False
    try:
        ans, info = app._verified_finalize("q", "A", ["b"], "personal",
                                           no_repair, time.perf_counter(), "natural")
    finally:
        D.VERIFY_ENABLED = old
    check("off_answer_kept", ans == "A")
    check("off_verdict_disabled", info["verify"]["verdict"] == "disabled")
    check("off_verifier_not_called", av.calls == [])


def t_general_no_blocks_skipped():
    av = FakeVerifier(["unsupported"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    ans, info = app._verified_finalize("世界知识问题", "A", [], "general",
                                       no_repair, time.perf_counter(), "natural")
    check("general_skipped_verdict", info["verify"]["verdict"] == "skipped_general_no_memory")
    check("general_verifier_not_called", av.calls == [])


def t_repair_budget():
    av = FakeVerifier(["unsupported", "pass"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    app.verify_repair_budget_s = 0.0
    ans, info = app._verified_finalize("q", "OLD", ["b"], "personal",
                                       no_repair, time.perf_counter(), "natural")
    check("budget_fallback_sentence", ans == D.VERIFY_FALLBACK_SENTENCE)
    check("budget_attempts_0", info["attempts"] == 0)
    check("budget_state", info["state"] == "verify_fallback")


def t_strip_continuation():
    av = FakeVerifier(["pass"], strip=lambda s: s.replace(" STRAY", ""))
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    ans, _info = app._verified_finalize("q", "A STRAY", ["b"], "personal",
                                        no_repair, time.perf_counter(), "natural")
    check("strip_applied", ans == "A", ans)
    check("strip_called", av.strip_calls == ["A STRAY"])


def _fake_iso(ans, evidence=None):
    class _Iso:
        def answer_isolated(self, eng, rows, prompt, n_predict=64, scratch=6,
                            model_path=None, gen_seq=None):
            self.last = {"rows": list(rows), "prompt": prompt,
                         "n_predict": n_predict, "gen_seq": gen_seq}
            return ans, {"isolated_seq": gen_seq or 6, "n_rows": len(rows)}
    return _Iso()


def t_isolated_blocks_identity():
    av = FakeVerifier(["pass"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    old_iso = D._iso
    D._iso = _fake_iso("上海")
    app._row_by_id = lambda sid: (1, "mem", "", "记忆原文：下周三去上海", "h", 1, "p", 5)
    app._unmount_all = lambda: None
    try:
        res = app._try_isolated("我下周三去哪", [{"source_id": 1, "score": 1.0}], time.perf_counter())
    finally:
        D._iso = old_iso
    check("isolated_returns_answer", res and res["answer"] == "上海")
    check("isolated_verified_field", res and res.get("verified") is True)
    check("isolated_blocks_same_as_generation",
          av.calls and av.calls[0]["blocks"] == [{"id": 1, "text": "记忆原文：下周三去上海"}],
          av.calls)


def t_isolated_seq6_busy():
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    old_iso = D._iso
    D._iso = _fake_iso("上海")
    app.eng.cells[6] = 5                    # block occupies seq6
    try:
        res = app._try_isolated("q", [{"source_id": 1}], time.perf_counter())
    finally:
        D._iso = old_iso
        app.eng.cells[6] = 0
    check("seq6_busy_falls_back", res is None)


def t_isolated_timeout():
    av = FakeVerifier(["pass"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    old_iso = D._iso
    D._iso = _fake_iso("上海")
    app._row_by_id = lambda sid: (1, "mem", "", "记忆原文：上海", "h", 1, "p", 2)
    app._unmount_all = lambda: None
    old_budget = D.VERIFY_REPAIR_BUDGET_S
    D.VERIFY_REPAIR_BUDGET_S = -1.0          # force "elapsed > budget"
    try:
        res = app._try_isolated("q", [{"source_id": 1}], time.perf_counter())
    finally:
        D._iso = old_iso
        D.VERIFY_REPAIR_BUDGET_S = old_budget
    check("timeout_answer_fixed", res and res["answer"] == D.VERIFY_FALLBACK_SENTENCE,
          res and res.get("answer"))
    check("timeout_state", res and res["state"] == "verify_timeout")
    check("timeout_event_logged", "verify_timeout" in app.logger.codes())


def t_mount_path_wiring():
    av = FakeVerifier(["unsupported", "pass"])
    _install(av)
    app = make_app(tempfile.mkdtemp(prefix="vw_"))
    old_iso = D._iso
    D._iso = None                            # force the mount/seq0 path
    app._auto_remember_candidate = lambda t: False
    app._retrieval_select = lambda q: [{"source_id": 1, "score": 1.0}]
    app._last_query = None
    app._row_by_id = lambda sid: (1, "mem", "", "记忆原文：车位在 B2", "h", 1, "p", 4)
    app._sync_mounts = lambda: setattr(
        app, "mounted_blocks", [{"source_id": 1, "seq": 1, "n_tokens": 4, "lo": 0, "hi": 4}])
    app._unmount_all = lambda: None
    app._maybe_rollover = lambda: None
    app._should_search = lambda t: False
    answers = iter(["初答", "修复答案"])

    def fake_ask(seq, text, n_predict=32, pos=None):
        return next(answers)
    app.eng.ask = fake_ask
    try:
        res = app._ask_natural("我的车位在哪", time.perf_counter())
    finally:
        D._iso = old_iso
    check("mount_answer_repaired", res["answer"] == "修复答案", res.get("answer"))
    check("mount_verified_true", res.get("verified") is True)
    check("mount_verify_verdict", (res.get("verify") or {}).get("verdict") == "pass")
    check("mount_blocks_from_mounted",
          av.calls and av.calls[0]["blocks"] == [{"id": 1, "text": "记忆原文：车位在 B2"}], av.calls)
    check("mount_repair_event", "verify_repair" in app.logger.codes())


def t_real_verifier_smoke():
    try:
        import answer_verifier as AV
    except Exception as exc:                 # noqa: BLE001
        check("real_verifier_import", False, repr(exc))
        return
    v = AV.verify_answer("我的车停哪", "你停在 B2。", ["我的车停在 B2。"],
                         mode="personal")
    check("real_verifier_shape", isinstance(v, dict) and "verdict" in v
          and isinstance(v.get("mismatches"), list), v)


def main():
    for t in (t_pass, t_repair_pass, t_repair_fail_fallback, t_no_evidence,
              t_verify_off, t_general_no_blocks_skipped, t_repair_budget,
              t_strip_continuation, t_isolated_blocks_identity,
              t_isolated_seq6_busy, t_isolated_timeout, t_mount_path_wiring,
              t_real_verifier_smoke):
        try:
            t()
        except Exception:                    # noqa: BLE001
            import traceback
            traceback.print_exc()
            FAILS.append(t.__name__)
    print("\n%d/%d passed" % (TOTAL[0] - len(FAILS), TOTAL[0]))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())