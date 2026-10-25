# -*- coding: utf-8 -*-
"""S1 零 GPU 测试床 **v6**（口径 `docs/_work/M2-FULL-S1-SPEC-lead.md@ae2d88ad5ecc25d3`）。

v6 与 v5 的差异（本床吸收）：
  * 几何 = 游标顺延：A home `[4075,4096)`、chat_start_A=4096；
    B project 接 A chat 之后：`[4096+n_chat_A, +18)`、chat_start_B=4096+n_chat_A+18
  * `attach` 的 hi 是**排他上界**（pos_hi 存排他 end）
  * ③ `pos_max_self = chat_start_self + n_tokens_self − 1`（不硬编码 4096）
  * ②a 降级为接线回归（不计交叉分母）；新增 ②c 选择层文本判据（零 GPU）
  * ②b 去空白后判（真机答 `3 月 14`）
  * P-1 拆 P1a(share)/P1b(drop)：P1b 零实例记 `not_triggered`（不许记通过）
  * 未跑的会话 `cap_ok` 记 `not_run`；S1-03 的块 ok 不许默认绿

红证（变体法，只改一处；产物成对）：
    R1 只注入 source_blocks 元数据（不真挂 cells）      ⇒ ②a 红，③④仍绿
    R2 两会话同 seq（B=0）                             ⇒ ③/几何 红，④账目/预算仍绿，
                                                          engine_match ⇒ not_applicable
    R3 记账少记：B 的 chat_cells 记账置 0（不动实际增长）⇒ ④ engine_match 红，③仍绿
    R4a 绕过 leases 直接 eng.share                      ⇒ P1a 红，其余绿
    R4b 同块同区间连续 attach 触发 replay               ⇒ P2 红，P1a 等式仍成立
    R5 删掉每轮 CAP 校验（16 轮构造超 CAP 输入）        ⇒ 无 PlanRefused（CAP 断言红），③仍绿

用法：
    python -X utf8 _test_two_session.py --chat <chat.py> --out <产物.json>
        [--baseline-chat <旧 chat.py>] [--label main]
        [--expect-red S1-02a] [--must-green S1-03,S1-04,P1a,P2]

判据：每例只比 expect（不许 try/except 吞、不许留判据开关）。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
           PYTHONPATH=TOOLS,
           CHAT_DB=os.environ.get("S1_TEST_DB", ""))
CORE_IDS = ("geometry_ok", "geometry_contiguity", "S1-02a", "S1-02c", "S1-03",
            "S1-04", "CAP", "P1a", "P2", "attach_ok")
DENOM = {"sessions": 2, "mounted_blocks": 2, "pool_blocks": 3,
         "cross_assertions_text": "0/2（未做）",
         "cross_assertions_selection_text": 2,
         "note": "v6：②a 降级为接线回归、不计入交叉分母；交叉分母=②b 两条"}
# v6 几何（游标顺延；stub 每轮 +67 ⇒ n_chat_A=670）：
#   A: home [4096-21, 4096) = [4075,4096)；B: project [4096+670, +18) = [4766,4784)
STUB_CHAT_A = 67 * 10
GEOM_EXPECT = [
    {"seq": 1, "name": "home", "base": 4096 - 21, "pos_hi": 4096},
    {"seq": 2, "name": "project", "base": 4096 + STUB_CHAT_A, "pos_hi": 4096 + STUB_CHAT_A + 18},
]
_CACHE = {}
_IMPORT_N = [0]


def sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _install_stub():
    if "kvslots" in sys.modules:
        return
    kv = types.ModuleType("kvslots")

    class _NoEngine:
        def __init__(self, *a, **kw):
            raise RuntimeError("dry-run 不许建引擎（kvslots stub 拦截）")

    kv.KVEngine = _NoEngine
    sys.modules["kvslots"] = kv


def load_chat(path):
    path = os.path.abspath(path)
    if path in _CACHE:
        return _CACHE[path]
    _install_stub()
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    tmp = tempfile.mkdtemp(prefix="s1_chat_")
    dst = os.path.join(tmp, "chat.py")
    shutil.copyfile(path, dst)
    _IMPORT_N[0] += 1
    name = "chat_s1_probe_%d" % _IMPORT_N[0]
    spec = importlib.util.spec_from_file_location(name, dst)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    _CACHE[path] = mod
    return mod


def case(cid, got, expect):
    ok = all(got.get(k) == v for k, v in expect.items())
    return {"case": cid, "ok": bool(ok), "expect": expect, "got": got}


def raised_of(fn):
    try:
        return {"raised": False, "type": None, "msg": "", "value": fn()}
    except Exception as exc:                                    # noqa: BLE001
        return {"raised": True, "type": type(exc).__name__, "msg": str(exc), "value": None}


def run_cli(chat_path, args, timeout=240):
    r = subprocess.run([PY, "-X", "utf8", chat_path] + args, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV,
                       timeout=timeout)
    return {"exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--baseline-chat", default=None)
    ap.add_argument("--label", default="main")
    ap.add_argument("--expect-red", default="")
    ap.add_argument("--must-green", default="")
    args = ap.parse_args()

    chat_path = os.path.abspath(args.chat)
    baseline = os.path.abspath(args.baseline_chat) if args.baseline_chat else chat_path
    expect_red = [x for x in args.expect_red.split(",") if x]
    must_green = [x for x in args.must_green.split(",") if x]
    cap_refused_expected = True      # CAP 执行点不变量：16 轮超 CAP 必须 PlanRefused
    tmp = tempfile.mkdtemp(prefix="s1_case_")
    cases = []

    mod = load_chat(chat_path)
    # 床也走 temp DB 副本，仓库 chat.db 只读（v6 §11.2）
    mod.DB = os.environ.get("S1_TEST_DB", mod.DB)
    h = raised_of(lambda: mod.two_session_run(mod._StubEngine()))
    res = h["value"] or {}
    checks = res.get("checks", {})
    sess = {s["id"]: s for s in res.get("sessions", [])}

    cases.append(case("H_two_session_run", {
        "raised": h["raised"], "raised_type": h["type"], "msg": h["msg"][:120],
        "schema": res.get("schema"), "mode": res.get("mode"),
        "spec": res.get("spec"),
        "n_sessions": len(res.get("sessions", [])),
        "n_pool": len(res.get("pool", [])),
        "n_mounted": sum(len(s.get("mounted_blocks", [])) for s in res.get("sessions", [])),
        "seq_types": sorted(set(type(s.get("seq")).__name__ for s in res.get("sessions", []))),
        "mounted_by": [p.get("mounted_by") for p in res.get("pool", [])],
    }, {"raised": False, "schema": "s1_two_session_v6", "mode": "dry-run",
        "spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@ae2d88ad5ecc25d3",
        "n_sessions": 2, "n_pool": 3, "n_mounted": 2, "seq_types": ["int"],
        "mounted_by": [["A"], ["B"], []]}))

    got_f = {cid: checks.get(cid) for cid in CORE_IDS}
    got_f["fail_ids"] = res.get("fail_ids")
    exp_f = {cid: (cid not in expect_red) for cid in CORE_IDS}
    cases.append(case("F_checks_polarity", got_f, exp_f))

    cases.append(case("F_fail_ids", {
        "fail_ids": res.get("fail_ids", []),
        "expect_red_missing": [c for c in expect_red if c not in res.get("fail_ids", [])],
        "must_green_red": [c for c in must_green if c in res.get("fail_ids", [])],
        "verdict": res.get("verdict"),
    }, {"expect_red_missing": [], "must_green_red": []}))

    # ---- ③ 读数公式（chat_start_self 决定，不许硬编码 4096） ----
    m03 = {}
    for sid in ("A", "B"):
        s = sess.get(sid, {})
        m03["%s_n_tokens" % sid] = s.get("n_tokens")
        m03["%s_pos_max" % sid] = s.get("pos_max")
        m03["%s_pos_expect" % sid] = s.get("pos_max_expect")
        m03["%s_chat_start" % sid] = s.get("chat_start")
    m03["S1-03"] = checks.get("S1-03")
    if "S1-03" in expect_red:
        exp03 = {"S1-03": False}
    else:
        exp03 = {"S1-03": True, "A_n_tokens": 670, "A_pos_max": 4765, "A_pos_expect": 4765,
                 "A_chat_start": 4096,
                 "B_n_tokens": 670, "B_pos_max": 4096 + 670 + 18 + 670 - 1,
                 "B_pos_expect": 4096 + 670 + 18 + 670 - 1,
                 "B_chat_start": 4096 + 670 + 18}
    cases.append(case("M_03_readings", m03, exp03))

    # ---- ③ 块位置读数单列（blocks_geometry；pos_hi 排他） ----
    cases.append(case("M_03_blocks_geometry", {
        "blocks_geometry": res.get("blocks_geometry"),
    }, {"blocks_geometry": GEOM_EXPECT}))

    # ---- ④ 记账 + engine_match（R2 ⇒ not_applicable） ----
    ca = res.get("cells_accounting", {})
    em = ca.get("engine_match", {})
    got04 = {"blocks": ca.get("blocks"), "chat_A": ca.get("chat_A"),
             "chat_B": ca.get("chat_B"), "total": ca.get("total"),
             "within_budget": ca.get("within_budget"),
             "engine_match_status": em.get("status"),
             "engine_match_ok": (em.get("detail") or {}).get("ok"),
             "S1-04": checks.get("S1-04")}
    if "S1-04" in expect_red:
        exp04 = {"S1-04": False}
    elif "S1-03" in expect_red:
        # R2：账目/预算子断言仍绿，engine_match 记 not_applicable
        exp04 = {"blocks": 39, "chat_A": 670, "chat_B": 670, "total": 1379,
                 "within_budget": True, "engine_match_status": "not_applicable",
                 "engine_match_ok": None, "S1-04": True}
    else:
        exp04 = {"blocks": 39, "chat_A": 670, "chat_B": 670, "total": 1379,
                 "within_budget": True, "engine_match_status": "done",
                 "engine_match_ok": True, "S1-04": True}
    cases.append(case("M_04_accounting", got04, exp04))

    # ---- P-1a/P-1b/P-2（v6：P1b 零实例记 not_triggered） ----
    cnt = res.get("counters", {})
    exp_p = {"share": 2, "attach": 2, "drop": 0, "detach_hits": 0,
             "p1_share_eq": "P1a" not in expect_red,
             "p1_drop_eq": "not_triggered",
             "P1a": "P1a" not in expect_red,
             "P1b": "not_triggered"}
    exp_p["attach_replay"] = 2 if "P2" in expect_red else 0
    exp_p["p2_ok"] = "P2" not in expect_red
    if "P1a" in expect_red:
        exp_p["attach"] = 0
    cases.append(case("M_P1_P2", {
        "share": cnt.get("share"), "attach": cnt.get("attach"),
        "drop": cnt.get("drop"), "detach_hits": cnt.get("detach_hits"),
        "attach_replay": cnt.get("attach_replay"),
        "p1_share_eq": cnt.get("p1_share_eq"), "p1_drop_eq": cnt.get("p1_drop_eq"),
        "p2_ok": cnt.get("p2_ok"), "P1a": checks.get("P1a"),
        "P1b": checks.get("P1b"), "P2": checks.get("P2"),
    }, exp_p))

    # ---- ②c 选择层文本（v6 新增，零 GPU） ----
    csel = (res.get("cross") or {}).get("c_selection_text") or {}
    cases.append(case("M_02c_selection_text", {
        "A_ok": (csel.get("A") or {}).get("ok"),
        "B_ok": (csel.get("B") or {}).get("ok"),
        "A_other": (csel.get("A") or {}).get("contains_other_facts"),
        "B_other": (csel.get("B") or {}).get("contains_other_facts"),
        "S1-02c": checks.get("S1-02c"),
    }, {"A_ok": True, "B_ok": True, "A_other": [], "B_other": [],
        "S1-02c": ("S1-02c" not in expect_red)}))

    # ---- dry-run 的 S1-01/02b/05 必须是"未做"（v6：记绿即假绿） ----
    cases.append(case("M_dry_not_done", {
        "S1-01": checks.get("S1-01"), "S1-02b": checks.get("S1-02b"),
        "S1-05": checks.get("S1-05"),
        "sha_stable_status": (res.get("sha_stable") or {}).get("status"),
    }, {"S1-01": "未做", "S1-02b": "未做", "S1-05": "未做",
        "sha_stable_status": "not_done"}))

    # ---- CAP 执行点：16 轮构造超 CAP 输入（R5 删校验 ⇒ 无 PlanRefused） ----
    cap_res = raised_of(lambda: mod.two_session_run(mod._StubEngine(), n_rounds=16))
    cap_val = cap_res["value"] or {}
    cap = cap_val.get("cap", {})
    hit = cap.get("hit") or {}
    max_chat = max([s.get("chat_cells") or 0 for s in cap_val.get("sessions", [])] or [0])
    cap_sess = {s["id"]: s for s in cap_val.get("sessions", [])}
    cap_budget = {b["session"]: b for b in cap_val.get("budget", [])}
    cases.append(case("M_CAP_refuses", {
        "raised": cap_res["raised"], "refused": cap.get("refused"),
        "reason": (cap.get("error") or {}).get("reason"),
        "over_cap_cells": hit.get("chat_cells"), "cap": hit.get("cap"),
        "over_cap_gt_cap": (hit.get("chat_cells") or 0) > (hit.get("cap") or 0),
        "max_chat_cells": max_chat,
        "overshoot_gt_cap": max_chat > 1024,
        "B_rounds": (cap_sess.get("B") or {}).get("rounds"),
        "B_cap_ok": (cap_budget.get("B") or {}).get("cap_ok"),
        "B_reading_ok": (cap_sess.get("B") or {}).get("reading_ok"),
    }, {"raised": False, "refused": cap_refused_expected,
        "overshoot_gt_cap": True,
        "over_cap_gt_cap": cap_refused_expected,
        "B_rounds": 16 if cap_refused_expected is False else 0,
        "B_cap_ok": True if cap_refused_expected is False else "not_run",
        "B_reading_ok": True if cap_refused_expected is False else "not_run"}))

    # ---- C：CLI 干跑 ----
    cli_out = os.path.join(tmp, "cli_dryrun.json")
    cli = run_cli(chat_path, ["two", "--dry-run", "--out", cli_out])
    cli_json = None
    if os.path.exists(cli_out):
        cli_json = json.load(open(cli_out, encoding="utf-8"))
    cases.append(case("C_cli_dryrun", {
        "exit": cli["exit"], "schema": (cli_json or {}).get("schema"),
        "mode": (cli_json or {}).get("mode"),
        "denominators": (cli_json or {}).get("extra_denominators"),
        "sha_stable_status": ((cli_json or {}).get("sha_stable") or {}).get("status"),
        "fail_ids": (cli_json or {}).get("fail_ids"),
        "stderr_tail": cli["stderr"].strip().splitlines()[-1:] if cli["stderr"].strip() else [],
    }, {"exit": 0 if not expect_red else 2, "schema": "s1_two_session_v6", "mode": "dry-run",
        "sha_stable_status": "not_done",
        "denominators": {"sessions": 2, "mounted_blocks": 2, "pool_blocks": 3,
                         "cross_assertions_text": "0/2（未做）",
                         "cross_assertions_selection_text": 2,
                         "cross_assertions_note": "v6：②a 降级为接线回归、不计入交叉分母；"
                                                  "交叉分母=②b 两条"}}))

    # ---- D：默认路径（m1 --explain）新旧逐字节相同 ----
    m1_new = run_cli(chat_path, ["m1", "--explain"])
    m1_old = run_cli(baseline, ["m1", "--explain"])
    cases.append(case("D_default_m1_explain", {
        "new_exit": m1_new["exit"], "old_exit": m1_old["exit"],
        "stdout_identical": m1_new["stdout"] == m1_old["stdout"],
        "new_len": len(m1_new["stdout"]), "old_len": len(m1_old["stdout"]),
        "stdout_head": m1_new["stdout"].strip().splitlines()[:2],
    }, {"new_exit": 0, "old_exit": 0, "stdout_identical": True}))

    fail = [c["case"] for c in cases if not c["ok"]]
    product = {
        "schema": "s1_two_session_cases_v6",
        "label": args.label,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@ae2d88ad5ecc25d3",
        "chat_path": chat_path,
        "baseline_chat": baseline,
        "chat_sha16": sha16(chat_path),
        "baseline_sha16": sha16(baseline),
        "expect_red": expect_red, "must_green": must_green,
        "cases": cases,
        "fail_cases": fail,
        "n_pass": len(cases) - len(fail), "n_fail": len(fail),
        "three_level_denominator": DENOM,
    }
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(product, f, ensure_ascii=False, indent=1)

    print("%s: %d/%d pass, fail=%s -> %s"
          % (args.label, product["n_pass"], len(cases), fail, args.out or "-"))
    return 0 if not fail else 2


if __name__ == "__main__":
    sys.exit(main())