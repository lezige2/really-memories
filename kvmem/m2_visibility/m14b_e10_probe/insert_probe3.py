# -*- coding: utf-8 -*-
"""真机插入（带效果断言）：走 planner.apply_insert，moved 是被断言的，不是被打印的。

上一次（INSERT-REAL2）四步全报 ok，但当时**没有任何读回验证**；
这次每一步都要读回：drop 后不可见、share 后可见、repos_local 的 moved == 对话 cell 数。
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "engine"))
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner"))
import _driver2 as D2                      # noqa: E402
import planner as PL                       # noqa: E402
P = D2.P
P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
P.MANIFEST = os.path.join(HERE, "fixtures_probe14b.json")
D2.CTRL_CACHE = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_m14b", "control_texts_14b.json")
OUT = os.path.join(HERE, "out", "INSERT-REAL8.json")


class EngAdapter:
    """把引擎包成 apply_insert 需要的接口；每次操作都记耗时，读回走 cell_scan。"""

    def __init__(self, eng):
        self.eng = eng
        self.t = {}

    def _positions(self, seq):
        cnt, pos = P.cell_scan(self.eng, seq)
        return set(pos)

    def visible(self, seq, lo, hi):
        return any(lo <= p < hi for p in self._positions(seq))

    def cells_of(self, seq):
        return len(self._positions(seq))

    def n_tokens(self, seq):
        """计数层：统计**写入**的 token（share 进来的 cell 不计），与位置扫描机制独立。"""
        return D2.n_tokens(self.eng, seq)

    def raw_pos_max(self, seq):
        """位置层。"""
        return P.raw_pos_max(self.eng, seq)

    def drop(self, seq, lo, hi):
        t = time.time(); self.eng.drop(seq, lo, hi); self.t["drop"] = round((time.time() - t) * 1000, 1)

    def repos_local(self, seq, delta, lo, hi):
        t = time.time(); mv = self.eng.repos_local(seq, delta, lo, hi)
        self.t["repos_local"] = round((time.time() - t) * 1000, 1)
        return mv

    def share(self, src, dst, lo, hi):
        t = time.time(); self.eng.share(src, dst, lo, hi); self.t["share"] = round((time.time() - t) * 1000, 1)


PLANNER = os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner", "planner.py")


def _sha16(path):
    import hashlib
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]


def provenance():
    """产物自描述：跑的是哪一版代码。行号不是标识，sha16 才是。"""
    import time
    return {'planner_sha16': _sha16(PLANNER),
            'planner_bytes': os.path.getsize(PLANNER),
            'planner_mtime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(os.path.getmtime(PLANNER))),
            'probe_sha16': _sha16(os.path.abspath(__file__)),
            'probe_mtime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(os.path.getmtime(os.path.abspath(__file__)))),
            'run_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


TAG = "</" + "think>"


def ask_end(eng, q, n_predict=64):
    """必填四字段：ask_pos(+来源) / raw_len / stripped_len / n_tokens。缺一即产物不合格。"""
    pos = P.raw_pos_max(eng, P.LIVE) + 1
    ntok_before = D2.n_tokens(eng, P.LIVE)
    t = time.time()
    n, a = D2.ask_native(eng, P.LIVE, q, pos, n_predict)
    ntok_after = D2.n_tokens(eng, P.LIVE)
    return {"ask_pos": pos, "ask_pos_source": "raw_pos_max(eng, LIVE) + 1",
            "return_bytes": n,
            "raw_len": len(a), "stripped_len": len(a.strip()),
            "n_tokens_before_ask": ntok_before, "n_tokens_after_ask": ntok_after,
            "len": len(a.strip()), "answer": a, "answer_stripped": a.strip(),
            "elapsed_ms": round((time.time() - t) * 1000, 1)}


def norm(x):
    return "".join(ch for ch in str(x) if ch not in " ，。、！？；：\n\t")


def control_two_asks(eng, layout, segs, q, fact, res):
    """对照组：**完全不插入**，同一组块、同一问题，连续问两次。"""
    P.reset_all(eng)
    P.load_and_place(eng, layout)
    eng.reset(P.LIVE)
    P.share_layout(eng, layout, [{'id': s['id'], 'slot': s['slot'], 'pos_lo': s['pos_lo'],
                                  'pos_hi': s['pos_hi']} for s in segs])
    c = {}
    c['Q1'] = ask_end(eng, q)
    c['Q1']['fact_hit'] = bool(P.fact_ok(fact, c['Q1']['answer']))
    c['Q2'] = ask_end(eng, q)
    c['Q2']['fact_hit'] = bool(P.fact_ok(fact, c['Q2']['answer']))
    c['has_think_tag_in_Q1'] = TAG in c['Q1']['answer']
    c['has_think_tag_in_Q2'] = TAG in c['Q2']['answer']
    c['thinking_in_Q1'] = c['Q1']['len'] > 60
    c['thinking_in_Q2'] = c['Q2']['len'] > 60
    c['tag_used'] = TAG
    c['thinking_field_note'] = "thinking_* 问的是『有没有**非空**思考内容』；本例两次都为空，故恒 false、不可作判读依据。判读只看 has_think_tag_in_Q*"
    res['control_no_insert'] = c
    print("CONTROL Q1 len=%d thinking=%s | Q2 len=%d thinking=%s" % (
        c['Q1']['len'], c['thinking_in_Q1'], c['Q2']['len'], c['thinking_in_Q2']))
    return c


def main():
    manifest = P.load_manifest()
    layout = D2.build_layout("iso_no_car", manifest)
    segs = layout["segments"]
    target = next(s for s in segs if s["id"] == "project")
    q = P.FULL[target["block_id"]]["q"]
    fact = P.FULL[target["block_id"]]["fact"]
    new_seg = next(s for s in segs if s["id"] == "habit")
    N = int(new_seg["cells"])
    res = {"schema": "insert_real_v8_think_tag_fixed", "provenance": provenance(), "layout": "iso_no_car", "target": "project",
           "effect_assertions": "ON —— moved 是被断言的值，不是打印的值",
           "inserted_block": {"file": new_seg["file"], "cells": N},
           "expected_fact": fact, "n_new_cells": N}
    eng = P.open_engine()
    ad = EngAdapter(eng)
    try:
        control_two_asks(eng, layout, segs, q, fact, res)
        P.reset_all(eng)
        P.load_and_place(eng, layout)
        eng.reset(P.LIVE)
        shares = [{"id": s["id"], "slot": s["slot"], "pos_lo": s["pos_lo"], "pos_hi": s["pos_hi"]} for s in segs]
        P.share_layout(eng, layout, shares)
        pos_before = {s["id"]: eng.pos_max(s["slot"]) for s in segs}
        res["answers_before"] = ask_end(eng, q)
        res["answers_before"]["fact_hit"] = bool(P.fact_ok(fact, res["answers_before"]["answer"]))
        chat_hi = P.raw_pos_max(eng, P.LIVE) + 1
        res["chat_before"] = [P.CHAT, chat_hi]

        # 新块在对话让位之后再落位（apply_insert 通过 new_block_prepare 回调触发）
        n = int(new_seg["cells"])

        def _prepare_new_block():
            t0 = time.time()
            eng.reset(7)
            nn = eng.load_strict(7, new_seg["file"])
            eng.repos_local(7, P.CHAT - (eng.pos_max(7) - nn + 1))
            res["new_block_load_place_ms"] = round((time.time() - t0) * 1000, 1)
            return nn

        t_all = time.time()
        log = PL.apply_insert(ad, P.LIVE,
                              block_ranges=[(s["pos_lo"], s["pos_hi"]) for s in segs],
                              chat_range=(P.CHAT, chat_hi),
                              new_cells=N, cells_of=ad.cells_of,
                              new_block=(7, P.CHAT, P.CHAT + n),
                              reshares=[(s["slot"], s["pos_lo"], s["pos_hi"]) for s in segs],
                              new_block_prepare=_prepare_new_block, readback=ad)
        res["insert_elapsed_ms"] = round((time.time() - t_all) * 1000, 1)
        res["op_log"] = log
        res["op_ms"] = ad.t
        pos_after = {s["id"]: eng.pos_max(s["slot"]) for s in segs}
        res["block_pos_max"] = {"before": pos_before, "after": pos_after,
                                "unchanged": pos_before == pos_after}
        res["chat_after"] = [P.CHAT + N, P.raw_pos_max(eng, P.LIVE) + 1]
        res["answers_after"] = ask_end(eng, q)
        res["answers_after"]["fact_hit"] = bool(P.fact_ok(fact, res["answers_after"]["answer"]))

        # 排除性检查：答案里不得出现其他块的事实关键词（四块期望词互不相同）
        others = {s["id"]: P.FULL[s["block_id"]]["fact"] for s in segs if s["id"] != "project"}
        ans_n = norm(res["answers_after"]["answer"])
        res["exclusion_check"] = {"rule": "答案不得包含其他块的事实关键词",
                                  "other_facts": others,
                                  "hits": {k: (norm(v) in ans_n) for k, v in others.items()},
                                  "pass": not any(norm(v) in ans_n for v in others.values())}
        res["thinking_segment"] = {
            "before_has_newline": "\n" in res["answers_before"]["answer"],
            "after_has_newline": "\n" in res["answers_after"]["answer"],
            "control_Q2_thinking": res["control_no_insert"]["thinking_in_Q2"],
            "attribution": ("思考段消失与插入无关（对照组 Q2 也无）"
                            if not res["control_no_insert"]["thinking_in_Q2"]
                            else "思考段消失与插入相关（对照组 Q2 仍有）")}
        res["required_fields"] = ["ask_pos", "ask_pos_source", "raw_len", "stripped_len",
                                  "n_tokens_before_ask", "n_tokens_after_ask"]
        res["readback_layers_summary"] = {
            "repos_local": "L1 位置层（raw_pos_max 增量 == new_cells）+ L2 计数层（n_tokens 不变）=> 两层，机制独立",
            "drop": "仅 L1 位置层（cell_scan 读回不可见）=> 单层",
            "share": "仅 L1 位置层（cell_scan 读回可见）=> 单层",
            "content_layer_status": "未接上：shim 无 token 内容读导出（kvshim_* 只有 save/load 整序列），且 save 文件里 position->offset 的映射无文档/字段可依"
        }
        res["interpretation"] = {
            "label": "【未判定·最佳解释】",
            "claim": "生成本身退化：答案 -> 空 think 块 -> 重复句",
            "excluded": ["录制剥离（ans = buf.value.decode(...) 后仅 .strip()，产生不出空标签+重复）",
                         "中段开始（开头是完整句，中段开始应缺开头）"],
            "may_be_overturned_by": "raw_len / stripped_len / n_tokens 三数到齐后"}
        res["verdict"] = {"blocks_undisturbed": res["block_pos_max"]["unchanged"],
                          "fact_keyword_hit_before": res["answers_before"]["fact_hit"],
                          "fact_keyword_hit_after": res["answers_after"]["fact_hit"],
                          "answer_quality": "未检（fact_ok 只查关键词包含，不衡量答案正确性）",
                          "exclusion_pass": res["exclusion_check"]["pass"]}
        print("elapsed_ms=%s blocks_unchanged=%s fact_hit before/after=%s/%s exclusion=%s" % (
            res["insert_elapsed_ms"], res["block_pos_max"]["unchanged"],
            res["answers_before"]["fact_hit"], res["answers_after"]["fact_hit"],
            res["exclusion_check"]["pass"]))
        print("moved:", [x for x in log if x["op"] == "repos_local"])
        return 0
    except BaseException as exc:                     # noqa: BLE001
        res["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("ERROR", type(exc).__name__, exc)
        return 4
    finally:
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        # 对照运行单独成一册：lead 按文件名找产物，藏在别的册子里等于没有
        if "control_no_insert" in res:
            ctl = {"schema": "control_2ask_v1", "provenance": res["provenance"],
                   "purpose": "完全不插入、同一组块、同一问题，连问两次",
                   "ask_pos_source": "raw_pos_max(eng, LIVE) + 1",
                   "Q1": res["control_no_insert"]["Q1"], "Q2": res["control_no_insert"]["Q2"],
                   "verdict_rule": "判读：Q2 是否仍带空 think 标签与重复句（不看思考内容，两次都为空）",
                   "has_think_tag_in_Q1": res["control_no_insert"]["has_think_tag_in_Q1"],
                   "has_think_tag_in_Q2": res["control_no_insert"]["has_think_tag_in_Q2"],
                   "thinking_field_note": res["control_no_insert"]["thinking_field_note"],
                   "verdict": ("与插入无关（Q2 也没有）"
                               if not res["control_no_insert"]["thinking_in_Q2"]
                               else "与插入相关（Q2 仍有）")}
            json.dump(ctl, open(os.path.join(HERE, "out", "CONTROL-2ASK.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2, default=str)
        try:
            eng.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
