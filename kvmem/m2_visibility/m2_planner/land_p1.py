# -*- coding: utf-8 -*-
"""P1（pinned 驱逐）驱动 + 台账：`kvmem/m2_visibility/m2_planner/LANDED-p1.json`。

步骤（顺序不可换）：
① `out/P1-pre.json` 已取（现盘无 `pinned` 形参 ⇒ 两个 pinned 例 TypeError、helper 例 AttributeError）；
② 落地后 ⇒ `out/P1-after.json`；
③ 两个变体 ⇒ `out/P1-variant-no-filter.json` / `out/P1-variant-allpinned-silent.json`；
④ 回归三份（RED-SUITE / GREEN-SUITE / PLAN-SELFTEST）在**临时目录副本**里重跑（仓库 `out/`
   里的签名产物不动），逐份对照：只允许 `at` 时间戳与 `modules.evict_policy.py` 的 sha 变，
   其余字段必须完全一致 ⇒ `out/P1-regression.json`；
⑤ 台账 `LANDED-p1.json`：`_before` 副本、old→new、五份产物、两采样、逐文件复算、`red_proof`、
   `three_level_denominator`、`pin_source_contract`。

本文件不登记自身 sha（§22.3）。
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
BEFORE = os.path.join(HERE, "_before")
LANDED = os.path.join(HERE, "LANDED-p1.json")
GAP_S = 31
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
TEST = os.path.join(HERE, "_test_evict_pinned.py")
OLD_SHA = "aa7cbf3f86df30f8"
REGRESS_MODULES = ["kvsim.py", "assertions.py", "fake_planner.py", "planner.py", "plan.py",
                   "evict_policy.py", "test_planner.py", "red_suite.py", "selftest_plan.py"]
REGRESS_PRODUCTS = {"RED-SUITE.json": "red_suite.py",
                    "GREEN-SUITE.json": "test_planner.py",
                    "PLAN-SELFTEST.json": "selftest_plan.py"}


def mpath(rel):
    """m2_planner 目录内的相对路径（产物都在 m2_planner/out 下）。"""
    return os.path.join(HERE, rel)


def sha16(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def run(args, cwd):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV, cwd=cwd)


def build_variants(tmp):
    src = io.open(os.path.join(HERE, "evict_policy.py"), encoding="utf-8").read()
    anchors = {
        "filter": ("    if pin:                                        # 过滤只做在这里；evict_order 不动\n"
                   "        pinned_skipped = [s for s in order if s in pin]\n"
                   "        order = [s for s in order if s not in pin]\n"
                   "    else:\n"
                   "        pinned_skipped = []\n"),
        "refuse": ("    blocked_all = bool(kept) and over_after and all(int(b[\"seq\"]) in pin for b in kept)\n"
                   "    return dict(base, pinned=sorted(pin),\n"
                   "                refused_reason=\"all_pinned\" if blocked_all else None,\n"),
    }
    for k, a in anchors.items():
        assert src.count(a) == 1, (k, src.count(a))

    nf = src.replace(anchors["filter"], "    pinned_skipped = []\n")
    assert "order = [s for s in order if s not in pin]" not in nf
    nf_dir = os.path.join(tmp, "variant_no_filter")
    os.makedirs(nf_dir, exist_ok=True)
    nf_path = os.path.join(nf_dir, "evict_policy.py")
    io.open(nf_path, "w", encoding="utf-8", newline="\n").write(nf)

    silent = src.replace(
        anchors["refuse"],
        "    if over_after and kept and all(int(b[\"seq\"]) in pin for b in kept):\n"
        "        base = dict(base, evicted=[], over_budget_after=False)   # 静默降级（变体故意）\n"
        "    return dict(base, pinned=sorted(pin),\n"
        "                refused_reason=None,\n")
    assert 'refused_reason="all_pinned"' not in silent
    ap_dir = os.path.join(tmp, "variant_allpinned_silent")
    os.makedirs(ap_dir, exist_ok=True)
    ap_path = os.path.join(ap_dir, "evict_policy.py")
    io.open(ap_path, "w", encoding="utf-8", newline="\n").write(silent)
    return nf_path, ap_path


def flat(o, prefix=""):
    """把嵌套 JSON 摊平成 {路径: 值}，便于逐字段对照。"""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            out.update(flat(v, prefix + "/" + str(k)))
        return out
    if isinstance(o, list):
        out = {}
        for i, v in enumerate(o):
            out.update(flat(v, prefix + "/[%d]" % i))
        return out
    return {prefix: o}


def _flat_diff(a, b):
    fa, fb = flat(a), flat(b)
    return [k for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]


def regression(tmp):
    """三份回归：临时副本里跑两遍（旧/新 evict_policy），仓库 `out/` 的签名产物只读。

    对照分三层，避免把「仓库里已有的陈旧产物」算到 P1 头上：
    1. `p1_isolation`：新 vs 旧模块（同一环境）—— 除 `modules/evict_policy.py` 与 `at` 外必须完全一致；
    2. `drift_vs_signed`：旧模块输出 vs 仓库签名产物 —— **P1 之前就存在的漂移**，逐字段登记；
    3. `residue_vs_signed`：新模块输出 vs 签名产物中，既不是漂移、也不是本单模块/时间戳的字段
       —— 必须为空，否则说明 P1 污染了默认路径。
    """
    def prepare(sub):
        work = os.path.join(tmp, sub)
        os.makedirs(os.path.join(work, "out"), exist_ok=True)
        for m in REGRESS_MODULES:
            shutil.copyfile(os.path.join(HERE, m), os.path.join(work, m))
        return work

    def run_all(work, policy_path):
        shutil.copyfile(policy_path, os.path.join(work, "evict_policy.py"))
        got = {}
        for prod, script in REGRESS_PRODUCTS.items():
            r = run([PY, "-X", "utf8", script], cwd=work)
            path = os.path.join(work, "out", prod)
            assert os.path.exists(path), (script, r.stdout[-600:], r.stderr[-600:])
            with open(path, encoding="utf-8") as f:
                got[prod] = {"json": json.load(f), "path": path, "exit": r.returncode,
                             "tail": (r.stdout.strip().splitlines() or [""])[-1]}
        return got

    old = run_all(prepare("regress_old"), os.path.join(BEFORE, "evict_policy.py@" + OLD_SHA))
    new = run_all(prepare("regress_new"), os.path.join(HERE, "evict_policy.py"))
    allowed = {"/at", "/modules/evict_policy.py"}
    info = {}
    for prod in REGRESS_PRODUCTS:
        with open(os.path.join(OUT, prod), encoding="utf-8") as f:
            signed = json.load(f)
        o, n = old[prod]["json"], new[prod]["json"]
        vs_old = _flat_diff(o, n)                       # 旧/新模块在同一环境下的差
        p1_only = [k for k in vs_old if k not in allowed]
        drift = _flat_diff(signed, o)                   # 签名产物 vs 旧模块输出 = 既有漂移
        vs_signed = _flat_diff(signed, n)
        residue = [k for k in vs_signed if k not in drift and k not in allowed]
        flags = {"all_green": n.get("all_green"), "all_as_designed": n.get("all_as_designed"),
                 "n_pass": n.get("n_pass"), "n_fail": n.get("n_fail"),
                 "n_red": n.get("n_red"), "invariant_failures": n.get("invariant_failures")}
        signed_flags = {"all_green": signed.get("all_green"),
                        "all_as_designed": signed.get("all_as_designed"),
                        "n_pass": signed.get("n_pass"), "n_fail": signed.get("n_fail"),
                        "n_red": signed.get("n_red"),
                        "invariant_failures": signed.get("invariant_failures")}
        info[prod] = {
            "script": REGRESS_PRODUCTS[prod],
            "exit_old": old[prod]["exit"], "exit_new": new[prod]["exit"],
            "old_module_sha16": sha16(os.path.join(
                BEFORE, "evict_policy.py@" + OLD_SHA)),
            "new_module_sha16": sha16(os.path.join(HERE, "evict_policy.py")),
            "p1_isolation_diff": vs_old, "p1_isolation_unexpected": p1_only,
            "drift_vs_signed": drift,
            "residue_vs_signed": residue,
            "flags_new": flags, "flags_signed": signed_flags,
            "flags_same": flags == signed_flags,
            "new_sha16": sha16(new[prod]["path"]),
            "signed_sha16": sha16(os.path.join(OUT, prod)),
            "tail": new[prod]["tail"],
            "verdict": "ok（P1 隔离干净 + 无残留）" if (not p1_only and not residue)
                       else "CHANGED",
        }
    return info


def main():
    tmp = tempfile.mkdtemp(prefix="p1_batch_")
    nf_path, ap_path = build_variants(tmp)
    # 改前模块：`_before` 文件名带 `@` 后缀，importlib 认不出 loader ⇒ 复制成 .py 再跑
    pre_dir = os.path.join(tmp, "pre_module")
    os.makedirs(pre_dir, exist_ok=True)
    pre_path = os.path.join(pre_dir, "evict_policy.py")
    shutil.copyfile(os.path.join(BEFORE, "evict_policy.py@" + OLD_SHA), pre_path)

    jobs = {
        "out/P1-pre.json": [PY, "-X", "utf8", TEST, "--policy", pre_path,
                            "--out", os.path.join(OUT, "P1-pre.json")],
        "out/P1-after.json": [PY, "-X", "utf8", TEST,
                              "--out", os.path.join(OUT, "P1-after.json")],
        "out/P1-variant-no-filter.json": [PY, "-X", "utf8", TEST, "--policy", nf_path,
                                          "--out", os.path.join(OUT, "P1-variant-no-filter.json")],
        "out/P1-variant-allpinned-silent.json": [
            PY, "-X", "utf8", TEST, "--policy", ap_path,
            "--out", os.path.join(OUT, "P1-variant-allpinned-silent.json")],
    }
    runs = {}
    for name, args in jobs.items():
        if os.path.exists(mpath(name)):
            os.remove(mpath(name))   # 只重跑本批产物；仓库签名产物不在此列
        r = run(args, ROOT)
        runs[name] = {"exit": r.returncode,
                      "tail": r.stdout.strip().splitlines()[-1:] if r.stdout.strip() else []}

    reg = regression(tmp)
    reg_res = {"schema": "m3_p1_regression_v2",
               "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "how": "临时目录副本内跑两遍（旧 evict_policy / 新 evict_policy），仓库 out/ 签名产物只读；"
                      "JSON 摊平后逐字段对照",
               "layers": "① P1 隔离（新 vs 旧模块，只许 modules/evict_policy.py + at 变）；"
                         "② 既有漂移（旧模块产出 vs 仓库签名产物，逐字段登记）；"
                         "③ 残留（新模块产出 vs 签名产物里非漂移非本单字段，必须为空）",
               "products": reg,
               "all_ok": all(v["verdict"].startswith("ok") for v in reg.values()),
               "p1_isolation_clean": all(not v["p1_isolation_unexpected"] for v in reg.values()),
               "no_residue_vs_signed": all(not v["residue_vs_signed"] for v in reg.values()),
               "flags_same_as_signed": all(v["flags_same"] for v in reg.values()),
               "red_suite_all_as_designed": reg["RED-SUITE.json"]["flags_new"]["all_as_designed"],
               "green_suite_all_green": reg["GREEN-SUITE.json"]["flags_new"]["all_green"],
               "plan_selftest_invariants": reg["PLAN-SELFTEST.json"]["flags_new"]["invariant_failures"],
               "plan_selftest_n": {k: reg["PLAN-SELFTEST.json"]["flags_new"][k]
                                   for k in ("n_pass", "n_fail", "n_red")}}
    reg_path = os.path.join(OUT, "P1-regression.json")
    with open(reg_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(reg_res, f, ensure_ascii=False, indent=1)

    files = {
        "evict_policy.py": os.path.join(HERE, "evict_policy.py"),
        "_test_evict_pinned.py": TEST,
        "land_p1.py": os.path.join(HERE, "land_p1.py"),
        "before/evict_policy.py@" + OLD_SHA: os.path.join(BEFORE, "evict_policy.py@" + OLD_SHA),
        "plan.py": os.path.join(HERE, "plan.py"),
        "planner.py": os.path.join(HERE, "planner.py"),
        "selftest_plan.py": os.path.join(HERE, "selftest_plan.py"),
        "red_suite.py": os.path.join(HERE, "red_suite.py"),
        "test_planner.py": os.path.join(HERE, "test_planner.py"),
        "tools/chat_lease.py": os.path.join(ROOT, "tools", "chat_lease.py"),
        "tools/freeze_check.py": os.path.join(ROOT, "tools", "freeze_check.py"),
        "kvmem/chat.db": os.path.join(ROOT, "kvmem", "chat.db"),
        "m3/m3_lease.py": os.path.join(HERE, "..", "m3", "m3_lease.py"),
    }
    for name in ("out/P1-pre.json", "out/P1-after.json", "out/P1-variant-no-filter.json",
                 "out/P1-variant-allpinned-silent.json", "out/P1-regression.json"):
        files[name] = mpath(name)

    a = {k: sha16(p) for k, p in files.items()}
    sizes = {k: os.path.getsize(p) for k, p in files.items()}

    def load(name):
        with open(mpath(name), encoding="utf-8") as f:
            return json.load(f)

    pre, aft = load("out/P1-pre.json"), load("out/P1-after.json")
    nf, ap = load("out/P1-variant-no-filter.json"), load("out/P1-variant-allpinned-silent.json")

    print("采样间隔 %ds ..." % GAP_S)
    time.sleep(GAP_S)
    b = {k: sha16(p) for k, p in files.items()}

    ledger = {
        "schema": "landed_p1_v1",
        "batch_id": "m2full-p1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "judge_source": {"path": "docs/_work/M2-FULL-PREREG-draft.md", "section": "§2.3 P1",
                         "sha16": "4978c94474ba050c"},
        "change": {
            "file": "kvmem/m2_visibility/m2_planner/evict_policy.py",
            "old_sha16": OLD_SHA, "new_sha16": a["evict_policy.py"],
            "old_bytes": sizes["before/evict_policy.py@" + OLD_SHA],
            "new_bytes": sizes["evict_policy.py"],
            "what": "① `select_to_evict(..., pinned=())` 新增关键字：过滤只在函数内做，"
                    "pinned 空时逐字段返回旧 dict（键不少不多）；② 新增 `pinned_from_leases` "
                    "(duck-typed `.leased()`，零 GPU)；③ 全 pinned+超预算 ⇒ refused_reason=all_pinned；"
                    "④ `evict_order` / `plan()` 签名与主路径**未动**，淘汰默认仍 off",
        },
        "pin_source_contract": {
            "helper": "pinned_from_leases(leases, n_seq) -> sorted-ish set",
            "definition": "{int(s) for s in range(1, n_seq) if leases.leased(int(s))}",
            "duck_typed": "只要求对象有可调用的 .leased(seq)；不 import 引擎、不看 chat.py、零 GPU",
            "contract": "pin 的对象是「被引用」，不是「重要」——helper 只回答谁还被引用；"
                        "重要性与阈值判定不在本模块，也不许本模块自己看引擎推断",
            "no_leases_table": "对象没有 .leased() ⇒ 显式 TypeError；正确读数是「未接上」，"
                               "不许静默返回空 pinned 冒充绿（`H2_helper_rejects_non_lease` 判此契约）",
        },
        "three_level_denominator": {
            "blocks": aft["three_level_denominator"]["blocks"],
            "pinned": aft["three_level_denominator"]["pinned"],
            "evicted": aft["three_level_denominator"]["evicted"],
            "pre": dict(pre["three_level_denominator"]),
            "note": "总块数 / pinned 数 / 被踢数 三个都报（缺一即读数无效）；pre 与 after 同构",
        },
        "key_cases": {
            "M1_mixed_3p3n": {r["case"]: r["got"] for r in aft["cases"]
                              if r["case"] == "M1_mixed_3p3n"},
            "A1_all_pinned": {r["case"]: r["got"] for r in aft["cases"]
                              if r["case"] == "A1_all_pinned"},
            "O1_off_default": {"keys": next(r["got"]["keys"] for r in aft["cases"]
                                            if r["case"] == "O1_off_default")},
        },
        "red_proof": {
            "pre_red": {"product": "out/P1-pre.json", "sha16": a["out/P1-pre.json"],
                        "fail_cases": pre["fail_cases"],
                        "why": "现盘无 pinned 形参 ⇒ M1/A1 TypeError；无 helper ⇒ H1 AttributeError、"
                               "H2 拿不到 TypeError（契约未实现）",
                        "exit": runs["out/P1-pre.json"]["exit"]},
            "variant_no_filter": {"product": "out/P1-variant-no-filter.json",
                                  "sha16": a["out/P1-variant-no-filter.json"],
                                  "construction": "删掉 select_to_evict 里的 pin 过滤（order 不剔除 pinned）",
                                  "fail_cases": nf["fail_cases"],
                                  "evidence": {r["case"]: r["got"].get("evicted") for r in nf["cases"]
                                               if r["case"] in ("M1_mixed_3p3n", "A1_all_pinned")},
                                  "meaning": "删过滤 ⇒ pinned 出现在 evicted（M1/A1 红）",
                                  "exit": runs["out/P1-variant-no-filter.json"]["exit"]},
            "variant_allpinned_silent": {"product": "out/P1-variant-allpinned-silent.json",
                                         "sha16": a["out/P1-variant-allpinned-silent.json"],
                                         "construction": "全 pinned+超预算时静默 evicted=[]、"
                                                         "over_budget_after=False、refused_reason=None",
                                         "fail_cases": ap["fail_cases"],
                                         "evidence": next(({"over_budget_after": c["got"].get("over_budget_after"),
                                                            "refused_reason": c["got"].get("refused_reason"),
                                                            "caller_action": c["got"].get("caller_action")}
                                                           for c in ap["cases"]
                                                           if c["case"] == "A1_all_pinned"), {}),
                                         "meaning": "静默降级 ⇒ over_budget_after/refused_reason 断言红",
                                         "exit": runs["out/P1-variant-allpinned-silent.json"]["exit"]},
        },
        "products": {
            "out/P1-pre.json": {"sha16": a["out/P1-pre.json"], "bytes": sizes["out/P1-pre.json"],
                                "meaning": "改前红：4 fail（H1/H2/M1/A1）、O1 绿、exit 2"},
            "out/P1-after.json": {"sha16": a["out/P1-after.json"], "bytes": sizes["out/P1-after.json"],
                                  "meaning": "落地后：5/5 绿、分母 13/6/1、exit 0"},
            "out/P1-variant-no-filter.json": {
                "sha16": a["out/P1-variant-no-filter.json"],
                "bytes": sizes["out/P1-variant-no-filter.json"],
                "meaning": "变体①：删 pin 过滤 ⇒ pinned 被踢（红）"},
            "out/P1-variant-allpinned-silent.json": {
                "sha16": a["out/P1-variant-allpinned-silent.json"],
                "bytes": sizes["out/P1-variant-allpinned-silent.json"],
                "meaning": "变体②：全 pinned 静默降级（红）"},
            "out/P1-regression.json": {"sha16": a["out/P1-regression.json"],
                                       "bytes": sizes["out/P1-regression.json"],
                                       "meaning": "回归三份逐字段对照：只允许 at / 模块 sha 变化"},
        },
        "regression": dict(reg_res, products={k: {kk: v[kk] for kk in
                                                 ("verdict", "p1_isolation_unexpected",
                                                  "drift_vs_signed", "residue_vs_signed",
                                                  "flags_new", "flags_same", "new_sha16",
                                                  "signed_sha16", "tail")}
                                             for k, v in reg.items()}),
        "guards": {
            "plan_signature_unchanged": "plan(blocks, chat_start, budget) 未动（plan.py sha 见 files）",
            "evict_order_unchanged": "evict_order(blocks, policy=None) 未动、不接 pinned",
            "default_policy_still_off": "DEFAULT_POLICY='off'；主路径 plan() 不调用本模块",
            "no_new_threshold": "mount_cap=None 即不启用；本单不加任何阈值",
            "no_tools_change": {"chat_lease.py": a["tools/chat_lease.py"] == "619a043215035de7",
                                "chat.db": a["kvmem/chat.db"] == "237d8e1f5de9a382",
                                "m3_lease.py": a["m3/m3_lease.py"] == "33ae679a50d58c93"},
        },
        "tooling": {"land_p1.py": {"sha16": a["land_p1.py"], "bytes": sizes["land_p1.py"]}},
        "files": {k: {"sha16": a[k], "bytes": sizes[k]} for k in files},
        "recompute": {"files_recomputed": len(files),
                      "mismatched": [k for k in files if sha16(files[k]) != a[k]]},
        "two_samples": {"gap_s": GAP_S, "samples": 2, "identical": a == b,
                        "first": a, "second": b},
        "self_registration": "本文件不登记自身 sha16（自指恒假，RESULTS-RED.md §22.3）",
    }
    with open(LANDED, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)

    print(json.dumps({
        "evict_policy": {"old": OLD_SHA, "new": a["evict_policy.py"],
                         "new_bytes": sizes["evict_policy.py"]},
        "products": {k: v["sha16"] for k, v in ledger["products"].items()},
        "denominator": {k: ledger["three_level_denominator"][k]
                        for k in ("blocks", "pinned", "evicted")},
        "pre_fail": pre["fail_cases"], "after_fail": aft["fail_cases"],
        "nf_fail": nf["fail_cases"], "ap_fail": ap["fail_cases"],
        "regression_ok": reg_res["all_ok"],
        "regression_detail": {k: {"verdict": v["verdict"],
                                  "p1_iso": v["p1_isolation_unexpected"],
                                  "drift": v["drift_vs_signed"],
                                  "residue": v["residue_vs_signed"]}
                              for k, v in reg.items()},
        "samples_identical": a == b,
        "mismatched": ledger["recompute"]["mismatched"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()