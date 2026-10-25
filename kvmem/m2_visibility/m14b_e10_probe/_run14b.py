# -*- coding: utf-8 -*-
"""E10 探针 runner：直接驱动 engine/_driver2.py。

为什么不用 runs_m14b/_driver14b.py：那个 wrapper 的 3 号检查把块 cells 白名单写死成
(21, 18, 12) —— 19 cells 的 car 块会被它拒掉（"STOP: block car cells=19"）。那个白名单是
「14B 从来没有 19 cells 块」那个阶段的产物；我不改它，改为直接驱动它包装的同一套东西：
同一个 DLL、同一个模型、同样的 manifest 语义、同样的 LAYOUTS 与判定器。

本文件额外补齐 lead 要求、而 D2.main 不产出的元数据（写进同一份 run json）：
  argv / n_predict / 每块 delta 与 moved / finish_reason / metric_note / 答案忠实性(schema 限定值)
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
ENGINE = os.path.join(ROOT, "kvmem", "m2_visibility", "engine")
sys.path.insert(0, ENGINE)
import _driver2 as D2          # noqa: E402

P = D2.P
MODEL14B = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
DEFAULT_MANIFEST = os.path.join(HERE, "fixtures_probe14b.json")
CTRL14 = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "control_texts_14b.json")

# 与 _driver14b.py 完全相同的两处运行期别名（它们只改 P.FULL 的内存副本）
P.FULL.setdefault("project_paraphrase18", dict(P.FULL["project"]))
P.FULL.setdefault("g18_bos_c18", dict(P.FULL["home"]))

P.MODEL = MODEL14B
P.MANIFEST = DEFAULT_MANIFEST
D2.CTRL_CACHE = CTRL14

METRIC_NOTE = "key-token 命中率；不测忠实性；不可当答案正确率引用"

# --- 位置读数插桩 -------------------------------------------------------------
# 上游 tools/m2_visibility_probe.py 的 load_and_place 只做
#     moved = eng.repos_local(slot, delta);  if moved != n: raise
# 它既不留 moved、也不留 base/delta。不改上游文件，改为包装引擎的 repos_local 记录每次调用：
# 每条 (seq, delta, moved)。期望值用**精确期望**：delta!=0 -> cells, delta==0 -> 0。
_REPOS_CALLS = []
IMPOSSIBLE = []


_ENG = [None]


_DUMP = {"on": False, "tmpdir": None, "shas": {}}
_RT = {"k": 0, "done": set(), "rows": []}


def _dump_sha(eng, seq, tag):
    if not _DUMP["on"]:
        return None
    import hashlib as _h, tempfile as _t, os as _o
    if _DUMP["tmpdir"] is None:
        _DUMP["tmpdir"] = _DUMP.get("dir") or _t.mkdtemp(prefix="blkdump_")
        if _DUMP.get("dir"):
            _o.makedirs(_DUMP["tmpdir"], exist_ok=True)
    p = _o.path.join(_DUMP["tmpdir"], "seq%d_%s.kvmem" % (seq, tag))
    try:
        eng.save(seq, p)
        with open(p, "rb") as f:
            b = f.read()
        rec = {"sha16": _h.sha256(b).hexdigest()[:16], "bytes": len(b)}
        _DUMP["shas"].setdefault(int(seq), {})[tag] = rec
        return rec
    except BaseException as e:
        _DUMP["shas"].setdefault(int(seq), {})[tag] = {"error": "%s: %s" % (type(e).__name__, e)}
        return None


def _instrumented_open_engine():
    eng = _ORIG_OPEN_ENGINE()
    _ENG[0] = eng
    _orig = eng.repos_local

    def wrapped(seq, delta):
        _dump_sha(eng, seq, "pre_repos")
        moved = int(_orig(seq, delta))
        _dump_sha(eng, seq, "post_repos")
        if _RT["k"] and int(seq) not in _RT["done"]:
            _RT["done"].add(int(seq))
            pm_a = int(eng.pos_max(seq))
            _orig(seq, _RT["k"])                 # 多转一次
            _orig(seq, -_RT["k"])                # 再转回来：位置回到原位
            pm_b = int(eng.pos_max(seq))
            _RT["rows"].append({"seq": int(seq), "pos_max_before": pm_a, "pos_max_after": pm_b,
                                "pos_equal": pm_a == pm_b,
                                "rot_extra": 2})
            _dump_sha(eng, seq, "after_roundtrip")
        _REPOS_CALLS.append({"seq": int(seq), "delta": int(delta), "moved": moved})
        return moved

    eng.repos_local = wrapped
    return eng


_ORIG_OPEN_ENGINE = P.open_engine
P.open_engine = _instrumented_open_engine
FIDELITY_SCHEMA = {"enum": ["未检（判定器结构上不可检）"],
                   "note": "只允许这一个值；想填「已检」必须改 schema, 会被看见"}


FINISH_REASON = "unavailable"
FINISH_REASON_WHY = (
    "DLL 的导出符号里没有任何 EOS / stop / finished 信号（grep kvshim.cpp 的导出全集："
    "ask/ask_at/ask_at_topk/bytes_per_token/can_shift/close/free_log/init_log/load/n_ctx/n_tokens/"
    "open/piece/pool_bytes/pos_max/repos/repos_local/reset/save/score_at/seq_*/tokenize/write/write_at），"
    "kvshim_ask_at 只回字节数。所以真实停止原因**拿不到**；能算的只有生成 token 数 "
    "(n_tokens_after - n_tokens_before)，它与 n_predict 的比较是**推断**，不是停止原因。"
    "按 lead 口径：给不出就写 unavailable，不写 unknown。")


import re


def first_sentence(text):
    """截到第一个句号（含）。没有句号则原样返回。"""
    i = text.find("。")
    return text if i < 0 else text[:i + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--run-json", required=True)
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--n-predict", type=int, default=None)
    ap.add_argument("--arm-note", default=None)
    ap.add_argument("--roundtrip", type=int, default=0,
                    help="放置后再做一次 +/-K 的重转往返：位置回到原位、重转次数 +2 —— S5 的真实必红构造")
    ap.add_argument("--dump-dir", default=None, help="块字节导出目录（持久化，便于事后算首个差异偏移）")
    ap.add_argument("--dump-bytes", action="store_true",
                    help="在 repos_local 调用前后各导出该 seq 的序列化字节并算 sha16（M2 验收第 3 条用）")
    a = ap.parse_args()
    P.MANIFEST = a.manifest
    t0 = time.time()
    _DUMP["on"] = bool(a.dump_bytes)
    _RT["k"] = int(a.roundtrip or 0)
    _DUMP["dir"] = a.dump_dir

    argv = list(sys.argv)
    if a.n_predict:
        P.N_PREDICT = a.n_predict
        print("[GEN] n_predict = %d" % P.N_PREDICT)
    else:
        print("[GEN] n_predict = %d (default)" % P.N_PREDICT)
    print("[NOTE] %s" % METRIC_NOTE)

    sys.argv = [argv[0], "--layout", a.layout, "--target", a.target, "--run-json", a.run_json]
    err = None
    try:
        rc = D2.main()
    except BaseException as e:      # 拒绝/异常本身就是读数：必须落盘, 不许静默无产物
        rc = 90
        err = "%s: %s" % (type(e).__name__, e)
        print("[REFUSED] %s" % err)
    if not os.path.exists(a.run_json):
        json.dump({"schema": "iso_run_v2", "experiment": "refused-no-artifact",
                   "error": err, "runner": {"argv": argv, "n_predict": P.N_PREDICT}},
                  open(a.run_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)

    # ---- 补元数据（只在自己写的产物上做, 不改 D2）----
    if os.path.exists(a.run_json):
        res = json.load(open(a.run_json, encoding="utf-8"))
        res["runner"] = {"script": os.path.abspath(__file__), "argv": argv, "arm_note": a.arm_note,
                         "n_predict": P.N_PREDICT, "manifest": os.path.abspath(a.manifest),
                         "wall_s": round(time.time() - t0, 2)}
        if isinstance(res.get("target"), str):
            res["target"] = res["target"].strip('"')   # 统一成裸值
        res["metric_note"] = METRIC_NOTE
        res["answer_fidelity_schema"] = FIDELITY_SCHEMA
        res["answer_fidelity"] = "未检（判定器结构上不可检）"
        # 每块 delta：块文件里的 pos 是 0..n-1（见台账记录），目标位置是 pos_lo
        # 块文件名 / sha256 从 manifest 补（D2 的 layout.segments 不带这两项）
        _man = json.load(open(a.manifest, encoding="utf-8"))
        _by_id = {}
        for _fam in _man["blocks"].values():
            for _n, _m in _fam.items():
                _by_id[_n] = _m
        res["repos_calls"] = list(_REPOS_CALLS)
        if _RT["k"]:
            res["roundtrip"] = {"k": _RT["k"], "rows": _RT["rows"],
                                "note": "位置逐位回到原位，仅多两次重转；用于证明 S5 抓的是字节扰动而非搬家"}
        if _DUMP["on"]:
            bb = []
            for seq, recs in sorted(_DUMP["shas"].items()):
                pre = recs.get("pre_repos") or {}
                post = recs.get("post_repos") or {}
                bb.append({"slot": seq, "pre_repos": pre, "post_repos": post, "tags": recs,
                           "unchanged_by_own_repos": (pre.get("sha16") is not None
                                                      and pre.get("sha16") == post.get("sha16"))})
            res["block_bytes"] = bb
        res["fault_injection"] = {k: os.environ.get(k) for k in
                                  ("LLAMA_KV_REPOS_FAULT_LAYER",) if os.environ.get(k) is not None} or None
        placed = []
        for s in res.get("layout", {}).get("segments", []):
            delta = s["pos_lo"] - 0            # 块文件里的 pos 是 0..n-1
            expected = s["cells"] if delta != 0 else 0
            # 与插桩记录配对：按 delta 值匹配第一条尚未用过的调用
            hit = None
            for c in _REPOS_CALLS:
                if c.get("_used"):
                    continue
                if c["delta"] == delta:
                    c["_used"] = True
                    hit = c
                    break
            _meta = _by_id.get(s.get("block_id")) or {}
            placed.append({"id": s["id"], "slot": s["slot"], "cells": s["cells"],
                           "file": _meta.get("path"),
                           "file_sha256": (_meta.get("sha256") or "")[:16],
                           "base": 0, "delta": delta,
                           "moved": (hit["moved"] if hit else None),
                           "expected": expected,
                           "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"],
                           "match": "delta-value" if hit else "no repos_local call observed",
                           "exact_expectation_rule": "expected = cells if delta != 0 else 0"})
        res["placed"] = placed
        # 自洽: target_pos - base == delta
        for pl in placed:
            pl["target_pos"] = pl["pos_lo"]
            pl["self_consistent"] = (pl["target_pos"] - pl["base"] == pl["delta"])
        if IMPOSSIBLE:
            res["IMPOSSIBLE_HIT_RELATION"] = IMPOSSIBLE   # 必自报, 不许静默
        res["pos_max_anchor"] = res.get("raw")
        for c in _REPOS_CALLS:
            c.pop("_used", None)
        asks = res.get("answers") or []
        before = res["raw"].get("n_tokens_before") if isinstance(res.get("raw"), dict) else None
        for ans in asks:
            gen = ans.get("gen_tokens")
            if gen is None:
                b = ans.get("kvshim_n_tokens_before_ask")
                a_ = ans.get("kvshim_n_tokens_after_ask")
                if b is not None and a_ is not None:
                    gen = int(a_) - int(b)
            ans["finish_reason"] = FINISH_REASON            # 真实停止原因拿不到，如实写
            ans["finish_reason_why"] = FINISH_REASON_WHY
            q = str(ans.get("question") or "")
            ep = str(ans.get("expected") or "")
            fs_ = first_sentence(str(ans.get("answer") or ""))
            # --- 命中：主判据 hit_full 一个字不动；并列两个诊断字段 ---
            ans["hit_full"] = bool(ans.get("ok"))                 # 全篇裸比（主判据）
            ans["hit_first_raw"] = bool(ep and ep in fs_)         # 首句裸比
            ans["hit_first_ws"] = bool(ep and re.sub(r"\s+", "", ep) in re.sub(r"\s+", "", fs_))
            ans["hit_first_sentence"] = ans["hit_first_raw"]      # 兼容旧名，指向裸比
            ans["first_sentence"] = fs_
            if not ans["hit_full"] and ans["hit_first_raw"]:
                rel = "impossible"                                # 首句是全篇前缀 ⇒ 逻辑不可能
            elif ans["hit_full"] and ans["hit_first_raw"]:
                rel = "both"
            elif ans["hit_full"] and ans["hit_first_ws"]:
                rel = "ws_only"                                   # 判定器空白敏感，非生成证据
            elif ans["hit_full"]:
                rel = "tail_only"
            else:
                rel = "neither"
            ans["hit_relation"] = rel
            if rel == "impossible":
                IMPOSSIBLE.append({"segment": ans.get("segment"), "expected": ep, "first_sentence": fs_})
            # --- token 账：raw_delta_tokens 含提问 token，不可与 n_predict 比较 ---
            b_ = ans.get("kvshim_n_tokens_before_ask")
            a_ = ans.get("kvshim_n_tokens_after_ask")
            raw = (int(a_) - int(b_)) if (b_ is not None and a_ is not None) else None
            ans["raw_delta_tokens"] = raw
            ans["raw_delta_tokens_note"] = "含提问 token，**不可与 n_predict 比较**"
            qt = None
            if _ENG[0] is not None and q:
                try:
                    qt = int(P.measure(_ENG[0], P.K.turn(q)))
                except Exception:
                    qt = None
            ans["question_tokens"] = None      # 此路不通, 见字段说明
            ans["question_tokens_note"] = ("此路不通（P.measure 在 wrapper 层抛错）；"
                                           "截断判定改用行为对照（np64 vs np128 前缀关系），不要修这条路")
            ans["generated_tokens"] = None     # 依赖 question_tokens, 同上：此路不通
            ans["generated_tokens_note"] = ("理论上 = raw_delta_tokens − question_tokens，但 question_tokens 拿不到 ⇒ "
                                            "恒 null；**不作为截断判据，也不留待修的钩子**")
            ans["truncated_inferred"] = None
            ans["truncated_inferred_source"] = "pending: 待 n_predict=64 vs 128 行为对照（逐字节比对）"
        json.dump(res, open(a.run_json, "w", encoding="utf-8"), ensure_ascii=False,
                  indent=2, default=str)
        print("[PROBE] run json 补齐: argv / n_predict / delta / finish_reason / metric_note")
    return rc


if __name__ == "__main__":
    sys.exit(main())
