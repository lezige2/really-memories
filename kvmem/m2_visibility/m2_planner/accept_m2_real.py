# -*- coding: utf-8 -*-
"""M2 验收**真机臂**（task-16；r2 = task-19 产物加固）：3 块并发 + 第 10 轮后插入 +
未参与块 0 字节 + 顺序断言。

r2 相对 r1 的字段级修复（判据与期望一个都没动）：
  D1 `planner.py` 的 `naming` 字面量不再写死 12/45，按实参生成；
  D2 `pre_eq`/`post_eq` 改为**两次独立比较**（pre↔pre、post↔post），另立 `unchanged` 记
     「pre 与 post 相等」——三个字段不再同源；
  D3 `order_red_probe` 改打本臂真正执行的 `order_assert`（不再打本臂从不调用的
     `planner.check_ops`），op 名与真实 log 一致（`share_new`/`share_existing`）；
  追加 `selection_layer`（`analysis.py`/`retrieval.py` 当次 sha16）与 `supersedes` /
  `r1_comparison`：M2 测量的可归因性要能由产物自证，不能只靠 mtime。

装置（跑前逐项核，不符即 `未接上` 退出，不调参、不换臂）：
  14B `0b319bd0572f2730` / `kvshim_vk.dll` `9edbafa150700614` /
  几何 51 cells、pos 4045-4095、first_q 4096。

判据（`PROGRESS §2.3`/`§13.4` 原文，不改）：
  1. 3–5 块并发挂载（本臂 3 块：home 21 / project 18 / habit 12，插后 4 块）；
  2. 对话进行到第 10 轮后插入一块新记忆（car 19），随后问新块事实 ⇒ `fact_ok`（关键词命中）；
  3. 插入前后**未参与移动的块 0 字节变化**（逐 slot `save()` 后比 sha16：`pre_eq`/`post_eq`）；
  4. 插入顺序 `seq_rm` 先摘引用 → `repos_local(chat,+n)` → 新块落位 → 全部 `seq_cp`，
     顺序错要能红（本臂另跑一次**反序探针**，证明断言在真机上会抛）。

写 `out/M2-ACCEPT-<batch>.json`；退出码：0=通过 / 2=未通过 / 3=未接上。
"""
import hashlib
import json
import os
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
ENGINE = os.path.join(ROOT, "kvmem", "m2_visibility", "engine")
PROBE_DIR = os.path.join(ROOT, "kvmem", "m2_visibility", "m14b_e10_probe")
for p in (os.path.join(ROOT, "tools"), ENGINE, HERE, PROBE_DIR):
    sys.path.insert(0, p)

import m2_visibility_probe as P          # noqa: E402
import _driver2 as D2                    # noqa: E402
import planner as PL                     # noqa: E402
import plan as PLAN                      # noqa: E402
import insert_probe3 as IP               # noqa: E402  （复用其 EngAdapter / ask_end / norm）

MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DLL = os.path.join(ROOT, "tools", "kvshim_vk.dll")
MANIFEST = os.path.join(PROBE_DIR, "fixtures_probe14b.json")
BATCH = os.environ.get("M2_BATCH", "r1")
OUT = os.path.join(HERE, "out", "M2-ACCEPT-%s.json" % BATCH)

WANT = {"model_sha16": "0b319bd0572f2730", "dll_sha16": "9edbafa150700614"}
CHAT_START = P.CHAT                      # 4096
GEOM = {"cells_total": 51, "pos_lo": 4045, "pos_hi": 4095, "first_q": 4096}
MOUNT_KEYS = [("home", 1), ("project", 2), ("habit", 3)]   # (block, distance_key)
INSERT_BLOCK = ("car", 19)
N_TURNS = 10
N_PREDICT = 64
R1_PATH = os.path.join(HERE, "out", "M2-ACCEPT-r1.json")
R1_SHA16 = "76e2783343c3e196"


def sha256_file(p, chunk=1 << 24):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(chunk), b""):
            h.update(c)
    return h.hexdigest()


def sha16(p):
    return sha256_file(p)[:16]


def shas_now():
    """跑前/跑后各采一次；任何一项不同即 `未通过`（产物必须自证身份）。

    `analysis_py`/`retrieval_py` 是**选择层**：本臂不调用它们，但 M2 的测量要可归因
    （`tools/freeze_check.py` 的存在理由），所以把它们当次 sha 一并登记并纳入稳定性检查。
    """
    return {"model_sha256": sha256_file(MODEL), "dll_sha256": sha256_file(DLL),
            "plan_py": sha16(os.path.join(HERE, "plan.py")),
            "planner_py": sha16(os.path.join(HERE, "planner.py")),
            "script": sha16(os.path.abspath(__file__)),
            "manifest": sha16(MANIFEST),
            "analysis_py": sha16(os.path.join(ROOT, "tools", "analysis.py")),
            "retrieval_py": sha16(os.path.join(ROOT, "tools", "retrieval.py"))}


def plan_geometry(manifest):
    """用本单的冻结 3 参 front door 算布局（gap 全 0 ⇒ 连续堆叠）。"""
    blocks = [{"seq": key, "cells": manifest["blocks"]["m2"][name]["cells"], "key": key}
              for name, key in MOUNT_KEYS]
    placements = PLAN.plan_placements(blocks, CHAT_START, {"n_ctx": P.N_CTX, "chat_len": 500})
    by_seq = {e["seq"]: e for e in placements}
    rows = []
    for name, key in MOUNT_KEYS:
        e = by_seq[key]
        b = manifest["blocks"]["m2"][name]
        rows.append({"name": name, "seq": key, "cells": b["cells"], "base": e["base"],
                     "pos_lo": e["base"], "pos_hi": e["pos_hi"], "path": b["path"],
                     "file_sha256": b["sha256"]})
    rows.sort(key=lambda r: r["pos_lo"])
    return rows


def geometry_reading(rows):
    return {"cells_total": sum(r["cells"] for r in rows),
            "pos_lo": min(r["pos_lo"] for r in rows),
            "pos_hi": max(r["pos_hi"] for r in rows),
            "first_q": CHAT_START,
            "expected": GEOM,
            "match": (sum(r["cells"] for r in rows) == GEOM["cells_total"]
                      and min(r["pos_lo"] for r in rows) == GEOM["pos_lo"]
                      and max(r["pos_hi"] for r in rows) == GEOM["pos_hi"])}


def mount(eng, rows):
    placed = []
    for r in rows:
        eng.reset(r["seq"])
        n = eng.load_strict(r["seq"], r["path"])
        if n != r["cells"]:
            raise RuntimeError("块 %s 载入 %d cells，清单说 %d" % (r["name"], n, r["cells"]))
        base = eng.pos_max(r["seq"]) - n + 1
        moved = eng.repos_local(r["seq"], r["base"] - base)
        if moved != n:
            raise RuntimeError("repos_local moved %d != %d for %s" % (moved, n, r["name"]))
        placed.append(dict(r, loaded_cells=n, base_in_file=base, delta=r["base"] - base))
    return placed


def share_all(eng, rows):
    for r in rows:
        eng.share(r["seq"], P.LIVE, r["pos_lo"], r["pos_hi"] + 1)


def coverage_check(eng, rows):
    n, pos = P.cell_scan(eng, P.LIVE)
    pset = set(pos)
    cov = {}
    for r in rows:
        have = sum(1 for p in range(r["pos_lo"], r["pos_hi"] + 1) if p in pset)
        cov[r["name"]] = {"lo": r["pos_lo"], "hi": r["pos_hi"], "cells": r["cells"],
                          "covered": have, "exact": have == r["cells"]}
    return {"n_cells_live": n, "coverage": cov,
            "all_exact": all(v["exact"] for v in cov.values())}


def save_block(eng, seq, tag, tmpdir):
    p = os.path.join(tmpdir, "seq%d_%s.kvmem" % (seq, tag))
    eng.save(seq, p)
    return {"sha16": sha16(p), "bytes": os.path.getsize(p)}


def order_assert(steps):
    names = [s.get("op") for s in steps]
    i_drop = [i for i, n in enumerate(names) if n == "drop"]
    i_repos = [i for i, n in enumerate(names) if n == "repos_local"]
    i_share = [i for i, n in enumerate(names) if n in ("share_new", "share_existing")]
    passed = bool(i_drop and i_repos and i_share
                  and max(i_drop) < min(i_repos) < min(i_share))
    return {"rule": "所有 drop(seq_rm) 必须早于 repos_local(chat)，且所有 share(seq_cp) 在其后",
            "sequence": names, "passed": passed}


def order_red_proof_of(steps):
    """判据 4 的「顺序错就红」证明：打**本臂真正执行的** `order_assert`，不是外部纯函数。

    r1 打的是 `planner.check_ops`（本臂从不调用它 ⇒ 证明了另一个门闩承重），且 op 名对不上
    真实 log（`share` vs `share_new`/`share_existing`）。r2 直接拿 `res["steps"]` 过
    `order_assert`：正序必须 True，**同一函数**对反序必须 False。
    """
    forward = order_assert(steps)
    reversed_steps = list(reversed(steps))
    back = order_assert(reversed_steps)
    red_ok = bool(forward["passed"] and not back["passed"])
    return {"forward": forward, "reversed": back,
            "rule": "同一 order_assert：正序 passed=True，反序必须 passed=False（否则断言不承重）",
            "op_names": "came from this arm's real log (drop / repos_local / share_new / share_existing)",
            "red_proof_ok": red_ok}


def _op_names(steps):
    return [s.get("op") for s in (steps or [])]


def compare_r1(res):
    """r2 与 r1 逐项读数对照（判据没变，读数必须不变；变了就照实 false 并列出差在哪）。"""
    out = {"r1_path": R1_PATH, "r1_sha16_expected": R1_SHA16, "checks": {}, "diff": []}
    if not os.path.exists(R1_PATH):
        out["diff"] = ["r1 product missing"]
        out["all_match"] = False
        return out
    r1 = json.load(open(R1_PATH, encoding="utf-8"))
    out["r1_sha16_actual"] = sha16(R1_PATH)

    def chk(key, a, b):
        ok = a == b
        out["checks"][key] = {"r2": a, "r1": b, "equal": ok}
        if not ok:
            out["diff"].append(key)

    for k in ("model_sha16", "dll_sha16"):
        chk("engine." + k, res["engine"][k], r1["engine"][k])
    for k in ("cells_total", "pos_lo", "pos_hi", "first_q", "match"):
        chk("geometry." + k, res["geometry"][k], r1["geometry"][k])
    chk("n_blocks_concurrent", res["n_blocks_concurrent"], r1["n_blocks_concurrent"])
    chk("insert_at_turn", res["insert_at_turn"], r1["insert_at_turn"])
    chk("chat_before_insert", res["chat_before_insert"], r1["chat_before_insert"])
    chk("n_chat_cells_before_insert", res["n_chat_cells_before_insert"],
        r1["n_chat_cells_before_insert"])
    chk("steps.op_sequence", _op_names(res["steps"]), _op_names(r1["steps"]))
    chk("fact_ok.fact", res["fact_ok"]["fact"], r1["fact_ok"]["fact"])
    chk("fact_ok.pass", res["fact_ok"]["pass"], r1["fact_ok"]["pass"])
    chk("fact_ok.ask.fact_hit", res["fact_ok"]["ask"]["fact_hit"],
        r1["fact_ok"]["ask"]["fact_hit"])
    b2 = {u["name"]: u for u in res["byte_equality"]["unmoved_blocks"]}
    b1 = {u["name"]: u for u in r1["byte_equality"]["unmoved_blocks"]}
    chk("byte_equality.block_names", sorted(b2), sorted(b1))
    for name in sorted(set(b2) & set(b1)):
        for f in ("pre_sha16", "post_sha16", "pre_bytes", "post_bytes"):
            chk("byte_equality.%s.%s" % (name, f), b2[name][f], b1[name][f])
    for k in ("coverage_after_mount", "coverage_after_insert"):
        chk(k + ".all_exact", res[k]["all_exact"], r1[k]["all_exact"])
    chk("sha_stable.ok", res["sha_stable"]["ok"], r1["sha_stable"]["ok"])
    out["all_match"] = not out["diff"]
    return out


def main():
    t_start = time.time()
    res = {"schema": "m2_accept_real_arm_v1", "batch": BATCH,
           "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "acceptance_doc": "PROGRESS §2.3 / §13.4（判据原文，未改）",
           "insert_at_turn": N_TURNS,
           "predicted": {"criteria": ["3-5 块并发", "第10轮后插入+fact_ok", "未参与块 0 字节",
                                      "插入顺序 seq_rm → repos_local → 落位 → seq_cp"]}}
    invariant_failures = []

    def fail(kind, msg):
        invariant_failures.append({"kind": kind, "detail": msg})

    shas_before = shas_now()
    res["engine"] = {"model": MODEL, "model_sha256": shas_before["model_sha256"],
                     "model_sha16": shas_before["model_sha256"][:16],
                     "dll": DLL, "dll_sha256": shas_before["dll_sha256"],
                     "dll_sha16": shas_before["dll_sha256"][:16],
                     "n_ctx": P.N_CTX, "n_seq": P.N_SEQ, "kv": P.KV, "gpu": P.GPU,
                     "expected": WANT,
                     "model_ok": shas_before["model_sha256"][:16] == WANT["model_sha16"],
                     "dll_ok": shas_before["dll_sha256"][:16] == WANT["dll_sha16"]}

    manifest = P.load_manifest(require=True)
    rows = plan_geometry(manifest)
    res["blocks_planned"] = rows
    res["geometry"] = geometry_reading(rows)

    if not (res["engine"]["model_ok"] and res["engine"]["dll_ok"]):
        fail("device", "装置 sha16 不符：%r" % {"model": res["engine"]["model_sha16"],
                                              "dll": res["engine"]["dll_sha16"]})
    if not res["geometry"]["match"]:
        fail("geometry", "规划几何与验收几何不符：%r" % res["geometry"])
    if invariant_failures:
        res["invariant_failures"] = invariant_failures
        res["verdict"] = "未接上"
        res["exit"] = 3
        res["elapsed_s"] = round(time.time() - t_start, 1)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(res, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
        print("STOP 未接上:", invariant_failures)
        return 3

    eng = P.open_engine()
    ad = IP.EngAdapter(eng)
    tmpdir = tempfile.mkdtemp(prefix="m2accept_")
    try:
        # ---- 挂载 3 块 + 几何读回 ----
        P.reset_all(eng)
        eng.reset(P.LIVE)
        placed = mount(eng, rows)
        share_all(eng, rows)
        res["blocks_mounted"] = placed
        res["coverage_after_mount"] = coverage_check(eng, rows)
        first_pos = P.raw_pos_max(eng, P.LIVE) + 1
        res["first_q_pos"] = first_pos
        if first_pos != GEOM["first_q"]:
            fail("geometry", "first_q=%d != %d" % (first_pos, GEOM["first_q"]))
        if not res["coverage_after_mount"]["all_exact"]:
            fail("coverage", "挂载覆盖不全：%r" % res["coverage_after_mount"])

        # ---- 第 1..10 轮对话（真 decode，问三块各自的事实） ----
        rounds = []
        for turn in range(1, N_TURNS + 1):
            name = MOUNT_KEYS[(turn - 1) % len(MOUNT_KEYS)][0]
            q = P.FULL[name]["q"]
            a = IP.ask_end(eng, q, n_predict=N_PREDICT)
            a["turn"] = turn
            a["question"] = q
            a["asked_block"] = name
            a["fact"] = P.FULL[name]["fact"]
            a["fact_hit"] = bool(P.fact_ok(P.FULL[name]["fact"], a["answer"]))
            rounds.append(a)
            print("turn %2d %-8s n_tok=%d->%d fact_hit=%s ans=%r" % (
                turn, name, a["n_tokens_before_ask"], a["n_tokens_after_ask"],
                a["fact_hit"], a["answer"][:40]))
        res["rounds"] = rounds
        res["chat_before_insert"] = [CHAT_START, P.raw_pos_max(eng, P.LIVE) + 1]
        res["n_chat_cells_before_insert"] = D2.n_tokens(eng, P.LIVE)

        # ---- 插入前：未参与块的字节读数（存两次：D2 要求 pre_eq/post_eq 各自独立比较） ----
        pre = {r["name"]: save_block(eng, r["seq"], "pre", tmpdir) for r in rows}
        pre2 = {r["name"]: save_block(eng, r["seq"], "pre2", tmpdir) for r in rows}

        # ---- 插入（car 19 cells，落到让位后的 [CHAT_START, +19)） ----
        car = manifest["blocks"]["m2"][INSERT_BLOCK[0]]
        n_new = int(car["cells"])
        if n_new != INSERT_BLOCK[1]:
            fail("fixture", "car cells=%d != %d" % (n_new, INSERT_BLOCK[1]))
        chat_hi = P.raw_pos_max(eng, P.LIVE) + 1
        car_seq = 4
        holder = {}

        def _prepare_new_block():
            t0 = time.time()
            eng.reset(car_seq)
            nn = eng.load_strict(car_seq, car["path"])
            base_in_file = eng.pos_max(car_seq) - nn + 1
            eng.repos_local(car_seq, CHAT_START - base_in_file)
            holder.update({"load_place_ms": round((time.time() - t0) * 1000, 1),
                           "cells": nn, "base_in_file": base_in_file})
            return nn

        t_ins = time.time()
        steps = PL.apply_insert(
            ad, P.LIVE,
            block_ranges=[(r["pos_lo"], r["pos_hi"] + 1) for r in rows],
            chat_range=(CHAT_START, chat_hi),
            new_cells=n_new, cells_of=ad.cells_of,
            new_block=(car_seq, CHAT_START, CHAT_START + n_new),
            reshares=[(r["seq"], r["pos_lo"], r["pos_hi"] + 1) for r in rows],
            new_block_prepare=_prepare_new_block, readback=ad)
        res["insert_elapsed_ms"] = round((time.time() - t_ins) * 1000, 1)
        res["new_block"] = dict(holder, name=INSERT_BLOCK[0], file=os.path.basename(car["path"]),
                                file_sha256=car["sha256"], placed_range=[CHAT_START, CHAT_START + n_new])
        res["steps"] = steps
        res["op_ms"] = ad.t
        res["order_assertion"] = order_assert(steps)
        if not res["order_assertion"]["passed"]:
            fail("order", "steps 顺序不符：%r" % res["order_assertion"]["sequence"])

        # ---- 插入后：位置/字节/可见性 ----
        res["chat_after_insert"] = [CHAT_START + n_new, P.raw_pos_max(eng, P.LIVE) + 1]
        res["pos_after_insert"] = {r["name"]: eng.pos_max(r["seq"]) for r in rows}
        res["pos_unchanged"] = all(res["pos_after_insert"][r["name"]] == r["pos_hi"] for r in rows)
        if not res["pos_unchanged"]:
            fail("drag", "未参与块位置变了：%r" % res["pos_after_insert"])
        post = {r["name"]: save_block(eng, r["seq"], "post", tmpdir) for r in rows}
        post2 = {r["name"]: save_block(eng, r["seq"], "post2", tmpdir) for r in rows}
        unmoved = []
        for r in rows:
            n = r["name"]
            pre_eq = pre[n]["sha16"] == pre2[n]["sha16"]        # 插入前读两次是否一致
            post_eq = post[n]["sha16"] == post2[n]["sha16"]     # 插入后读两次是否一致
            unchanged = (pre[n]["sha16"] == post[n]["sha16"]
                         and pre[n]["bytes"] == post[n]["bytes"])  # 前后是否 0 字节变化
            unmoved.append({"name": n, "slot": r["seq"],
                            "pre_sha16": pre[n]["sha16"], "post_sha16": post[n]["sha16"],
                            "pre2_sha16": pre2[n]["sha16"], "post2_sha16": post2[n]["sha16"],
                            "pre_bytes": pre[n]["bytes"], "post_bytes": post[n]["bytes"],
                            "pre_eq": bool(pre_eq), "post_eq": bool(post_eq),
                            "unchanged": bool(unchanged)})
        res["byte_equality"] = {
            "unmoved_blocks": unmoved,
            "all_equal": all(u["unchanged"] and u["pre_eq"] and u["post_eq"] for u in unmoved),
            "field_note": "单臂；三个字段不同源：`pre_eq`=插入前两次 save 一致，`post_eq`=插入后两次 save"
                          "一致（读数可重复性），`unchanged`=插入前后同一 slot 的 save sha16 与字节数都相等"
                          "（判据 3 的实质读数）。跨布局对照（M2S3_car_back ↔ M2S3_no_car）不在本臂",
            "caveat_own_repos_rewrite": "挂载时块被 repos_local 重转过（base_in_file -> base）；"
                                        "本臂比的是插入前后，不含挂载期重转"}
        if not res["byte_equality"]["all_equal"]:
            fail("bytes", "未参与块读数不满足：%r" % [u for u in unmoved
                                                    if not (u["unchanged"] and u["pre_eq"] and u["post_eq"])])

        # 新块可见性 + 总数（3 块 + 1 新块 = 4 并发）
        cov_after = coverage_check(eng, rows)
        res["coverage_after_insert"] = cov_after
        n_cells_live = P.cell_scan(eng, P.LIVE)[0]
        res["cells_accounting"] = {"live_cells": n_cells_live,
                                   "expected": sum(r["cells"] for r in rows) + n_new + D2.n_tokens(eng, P.LIVE)}

        # ---- 判据 2：问新块事实（fact_ok）+ 既有块仍可用 ----
        car_q, car_fact = P.FULL["car"]["q"], P.FULL["car"]["fact"]
        a_new = IP.ask_end(eng, car_q, n_predict=N_PREDICT)
        a_new.update({"question": car_q, "fact": car_fact,
                      "fact_hit": bool(P.fact_ok(car_fact, a_new["answer"]))})
        others = {r["name"]: P.FULL[r["name"]]["fact"] for r in rows}
        ans_n = IP.norm(a_new["answer"])
        a_new["exclusion"] = {"other_facts": others,
                              "hits": {k: (IP.norm(v) in ans_n) for k, v in others.items()},
                              "pass": not any(IP.norm(v) in ans_n for v in others.values())}
        res["fact_ok"] = {"inserted_block": INSERT_BLOCK[0], "fact": car_fact,
                          "ask": a_new, "pass": a_new["fact_hit"]}
        if not a_new["fact_hit"]:
            fail("fact_ok", "插入后问新块事实未命中：%r" % a_new["answer"][:80])
        proj = next(r for r in rows if r["name"] == "project")
        a_old = IP.ask_end(eng, P.FULL["project"]["q"], n_predict=N_PREDICT)
        a_old.update({"fact_hit": bool(P.fact_ok(P.FULL["project"]["fact"], a_old["answer"]))})
        res["mounted_still_answers"] = a_old
        res["n_blocks_concurrent"] = len(rows) + 1

        # ---- 判据 4：顺序断言的「错就红」证明（本臂真正执行的 order_assert） ----
        red = order_red_proof_of(steps)
        res["order_red_probe"] = red
        if not red["red_proof_ok"]:
            fail("order", "反序未红：断言不承重（%r）" % red)

        try:
            eng.close()
        except Exception:                                # noqa: BLE001
            pass

        shas_after = shas_now()
        res["sha_stable"] = {"before": shas_before, "after": shas_after,
                             "ok": shas_before == shas_after}
        if not res["sha_stable"]["ok"]:
            fail("sha", "跑前跑后 sha 变了：%r" % {"before": shas_before, "after": shas_after})

        res["invariant_failures"] = invariant_failures
        ok = not invariant_failures
        res["verdict"] = "通过" if ok else "未通过"
        res["exit"] = 0 if ok else 2
        res["elapsed_s"] = round(time.time() - t_start, 1)
        res["three_criteria"] = {
            "1_concurrent_blocks": {"n_blocks": len(rows) + 1, "pass": len(rows) + 1 in (3, 4, 5)},
            "2_insert_at_turn10_fact_ok": {"insert_at_turn": N_TURNS,
                                           "fact_ok": a_new["fact_hit"], "pass": a_new["fact_hit"]},
            "3_unmoved_zero_bytes": {"pre_eq_all": res["byte_equality"]["all_equal"],
                                     "pass": res["byte_equality"]["all_equal"]},
            "4_order_assertion": {"steps_ok": res["order_assertion"]["passed"],
                                  "red_proof": red["red_proof_ok"],
                                  "pass": res["order_assertion"]["passed"] and red["red_proof_ok"]},
        }
        res["supersedes"] = R1_SHA16
        res["selection_layer"] = {
            "analysis_py": shas_before["analysis_py"],
            "retrieval_py": shas_before["retrieval_py"],
            "note": "本臂不调用选择层（块来自冻结清单）；登记它是为了让 M2 测量的可归因性"
                    "由产物自证，而不是靠文件 mtime。跑前跑后由 sha_stable 复查。",
        }
        cmp_r1 = compare_r1(res)
        res["r1_comparison"] = cmp_r1
        res["r1_readings_unchanged"] = cmp_r1["all_match"]
    except BaseException as e:                           # noqa: BLE001 —— 装置/路径不通
        res["error"] = "%s: %s" % (type(e).__name__, e)
        res["traceback"] = traceback.format_exc()[-2000:]
        res["invariant_failures"] = invariant_failures + [{"kind": "exception", "detail": res["error"]}]
        res["verdict"] = "未接上"
        res["exit"] = 3
        res["elapsed_s"] = round(time.time() - t_start, 1)
        try:
            eng.close()
        except Exception:                                # noqa: BLE001
            pass

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({"verdict": res.get("verdict"), "exit": res.get("exit"),
                      "invariant_failures": res.get("invariant_failures"),
                      "three_criteria": res.get("three_criteria")}, ensure_ascii=False))
    return res.get("exit", 3)


if __name__ == "__main__":
    sys.exit(main())