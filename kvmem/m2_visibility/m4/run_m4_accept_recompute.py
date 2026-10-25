# -*- coding: utf-8 -*-
"""M4 验收：九项 acceptance 只读复算 + 三个未闭项现状。

**不跑 14B、不产新锚**：只读既有 JSON / SQLite / 块文件 / 判据文档，逐项给
`{id, claim, expected, recomputed, source, match}`。判据原文取自备份目录
`D:/llama-mem-backup-2026-10-25/kvmem/m2_visibility/mine/inspector/M4-ACCEPT.md`
（工作树内 `docs/`、`mine/` 都没有该文件），计数口径摘要取 `PROGRESS-AND-ROADMAP.md §6.3`。

纪律：
- `match` 只表示"该断言写的值能不能从原件复算出来"，不是"通过/不通过"；
  出现 `match=false` 照实落盘（口径变化或原件缺失都照实写），不凑 true。
- 锚 sha 不符 ⇒ 停手（exit 3，不落产物）；脚本/所读文件跑前跑后 sha 漂移 ⇒ exit 2。
- 本脚本 import 只用标准库，不 import engine / kvslots，保证不碰 GPU。

exit：0 = 产物落地且不变量全过；2 = 所读文件 sha 跑前跑后不一致；3 = 锚/块 sha 与预期不符（停手）。
"""
import hashlib
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
ACCEPT_DOC = r"D:/llama-mem-backup-2026-10-25/kvmem/m2_visibility/mine/inspector/M4-ACCEPT.md"
README_DOC = r"D:/llama-mem-backup-2026-10-25/kvmem/m2_visibility/m4/README.md"
PROGRESS = os.path.join(ROOT, "PROGRESS-AND-ROADMAP.md")
ANCHOR = os.path.join(HERE, "run_m4_verify_a4.json")
BLOCK = os.path.join(HERE, "blocks", "blk_conv_2026-10-25_01.kvmem")
WRITE = os.path.join(HERE, "run_m4_write.json")
JUDGE_EV = os.path.join(HERE, "evidence_m4_judge.json")
DB = os.path.join(HERE, "m4_memory.db")
ABLATE_A7 = os.path.join(HERE, "run_m4_ablate_plate_a7.json")
ABLATE_A5 = os.path.join(HERE, "run_m4_ablate_plate_a5.json")
OUTFILTER_SELFTEST = os.path.join(HERE, "run_m4_outfilter_selftest.json")
OUTFILTER_PY = os.path.join(HERE, "outfilter.py")
DISPLAY_PY = os.path.join(HERE, "m4_display.py")
BEFORE = os.path.join(HERE, "_before")
REGISTER = os.path.join(BEFORE, "REGISTER.json")
OUTDIR = HERE
OUT_NAME = "run_m4_accept_recompute.json"

ANCHOR_SHA16_WANT = "59edbd82d4b9ae44"
BLOCK_SHA16_WANT = "81127d24fd64b96b"
BLOCK_BYTES_WANT = 9507412
BLOCK_HEADER = 1188          # 1188 + 104464*cells（与 M2/M4 块格式一致）
BLOCK_PER_CELL = 104464


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(8 << 20), b""):
            h.update(c)
    return h.hexdigest()


def finfo(path):
    b = os.path.getsize(path)
    return {"path": path.replace("\\", "/"), "sha256": sha256_file(path),
            "sha16": sha256_file(path)[:16], "bytes": b}


READ_FILES = [ACCEPT_DOC, README_DOC, PROGRESS, ANCHOR, BLOCK, WRITE, JUDGE_EV, DB,
              ABLATE_A7, ABLATE_A5, OUTFILTER_SELFTEST, OUTFILTER_PY, DISPLAY_PY]


def collect():
    a = json.load(open(ANCHOR, encoding="utf-8"))
    w = json.load(open(WRITE, encoding="utf-8"))
    ev = json.load(open(JUDGE_EV, encoding="utf-8"))
    a7 = json.load(open(ABLATE_A7, encoding="utf-8"))
    a5 = json.load(open(ABLATE_A5, encoding="utf-8"))
    st = json.load(open(OUTFILTER_SELFTEST, encoding="utf-8"))
    con = sqlite3.connect(DB)          # 只执行 SELECT；不写库
    cur = con.cursor()
    rows_mem = cur.execute(
        "SELECT mem_id, attr, value, type, status, anchored_time, unit_id FROM memory "
        "ORDER BY mem_id").fetchall()
    rows_src = cur.execute(
        "SELECT id, name, label, fanout FROM memory_source ORDER BY id").fetchall()
    rows_block = cur.execute(
        "SELECT block_id, cells, pos_lo, pos_hi, sha256 FROM block").fetchall()
    units = cur.execute(
        "SELECT id, name, label, fanout, text FROM memory_source WHERE id != "
        "(SELECT id FROM memory_source WHERE name LIKE 'conv%' ORDER BY id LIMIT 1) "
        "ORDER BY id").fetchall()
    n_conv = cur.execute(
        "SELECT COUNT(*) FROM memory_source WHERE name LIKE 'conv%'").fetchone()[0]
    cols_mem = [r[1] for r in cur.execute("PRAGMA table_info(memory)")]
    con.close()
    return a, w, ev, a7, a5, st, rows_mem, rows_src, rows_block, units, n_conv, cols_mem


def main():
    t0 = time.time()
    pre = {p: finfo(p) for p in READ_FILES}
    pre["script"] = finfo(os.path.abspath(__file__))
    a, w, ev, a7, a5, st, rows_mem, rows_src, rows_block, units, n_conv, cols_mem = collect()

    anchor_ok = pre[ANCHOR]["sha16"] == ANCHOR_SHA16_WANT
    block_ok = pre[BLOCK]["sha16"] == BLOCK_SHA16_WANT and pre[BLOCK]["bytes"] == BLOCK_BYTES_WANT
    if not (anchor_ok and block_ok):
        print(json.dumps({"STOP": "anchor/block sha mismatch", "anchor": pre[ANCHOR]["sha16"],
                          "anchor_want": ANCHOR_SHA16_WANT, "block": pre[BLOCK]["sha16"],
                          "block_want": BLOCK_SHA16_WANT,
                          "block_bytes": pre[BLOCK]["bytes"]}, ensure_ascii=False))
        return 3

    # ---------------- 九项 ----------------
    items = []

    # 1 真实对话轮数 9
    turns_sample = len(ev.get("sample", []))
    block_lines = len([ln for ln in a["block_text"].split("\n")])
    sent_turns = sorted({s.get("turn") for s in ev.get("sentences", []) if s.get("turn")})
    items.append({
        "id": 1, "claim": "真实对话轮数 = 9（从产品路径进来，不是夹具造串）",
        "expected": 9, "recomputed": turns_sample,
        "source": "evidence_m4_judge.json:.sample(len=%d)；run_m4_verify_a4.json:.block_text(9 行=%d)；"
                  "evidence_m4_judge.json:.sentences[*].turn(max=%s)" % (turns_sample, block_lines,
                                                                        max(sent_turns) if sent_turns else None),
        "match": turns_sample == 9 and block_lines == 9,
        "note": "两条独立口径一致：判定侧 9 轮样本、块正文 9 行。"})

    # 2 判定句数 10（全部有判定，无留白）
    n_sent = w.get("judge", {}).get("sentences")
    per = w.get("judge", {}).get("per_sentence", [])
    # 判定口径：verdict 是词（keep/drop/undecided），code 是码（D1/D4/K1+K5/K4+K3）；
    # 两个口径都接受，空判定才叫留白。
    WORDS = {"keep", "drop", "undecided"}

    def _judged(p):
        v = (p.get("verdict") or "").strip().lower()
        c = (p.get("code") or "").strip().upper()
        return (v in WORDS) or (c[:1] in ("K", "D", "U") and bool(c))

    verdicts = [(p.get("verdict"), p.get("code")) for p in per]
    blanks = [i for i, p in enumerate(per) if not _judged(p)]
    n_ev_sent = len(ev.get("sentences", []))
    items.append({
        "id": 2, "claim": "判定句数 = 进入判定的句子数 = 10（K/D/U 三分类，无漏判留白）",
        "expected": 10, "recomputed": {"write.judge.sentences": n_sent,
                                       "len(judge.per_sentence)": len(per),
                                       "len(evidence.sentences)": n_ev_sent,
                                       "blank_or_nonKDU": blanks,
                                       "verdict_words": [v for v, _ in verdicts]},
        "source": "run_m4_write.json:.judge; evidence_m4_judge.json:.sentences",
        "match": n_sent == 10 and len(per) == 10 and n_ev_sent == 10 and not blanks,
        "note": "逐句 verdict 全部落在 K/D/U（含复合码如 K1+K5/K4+K3），无空判定。"})

    # 3 keep 条数 6
    keeps_judge = w.get("judge", {}).get("keeps")
    keeps_db = w.get("db", {}).get("keeps")
    n_mem = len(rows_mem)
    items.append({
        "id": 3, "claim": "keep 条数 = 6",
        "expected": 6, "recomputed": {"judge.keeps": keeps_judge, "write.db.keeps": keeps_db,
                                      "db memory rows": n_mem,
                                      "a4.dedupe.keeps": a.get("dedupe", {}).get("keeps")},
        "source": "run_m4_write.json:.judge.keeps / .db.keeps；m4_memory.db::memory(count)",
        "match": keeps_judge == 6 and keeps_db == 6 and n_mem == 6,
        "note": "a4.dedupe.keeps=7 是**插入尝试数**（6 条 distinct + 1 条被去重的重复住址），"
                "distinct_keys=6、rows=6；与本项的 keep 条数=6 不是同一量。"})

    # 4 块数 / cells
    cells_file = (pre[BLOCK]["bytes"] - BLOCK_HEADER) // BLOCK_PER_CELL
    n_blocks = len(a.get("blocks", []))
    cells_a4 = a["blocks"][0]["cells"] if n_blocks else None
    items.append({
        "id": 4, "claim": "块数 / cells = 1 块 / 91 cells",
        "expected": {"blocks": 1, "cells": 91},
        "recomputed": {"a4.blocks": n_blocks, "a4.blocks[0].cells": cells_a4,
                       "db block rows": len(rows_block), "db block[0].cells": rows_block[0][1] if rows_block else None,
                       "cells_from_block_bytes": cells_file},
        "source": "run_m4_verify_a4.json:.blocks；m4_memory.db::block；块文件字节数公式 "
                  "1188+104464*cells",
        "match": n_blocks == 1 and cells_a4 == 91 and len(rows_block) == 1
                 and rows_block[0][1] == 91 and cells_file == 91,
        "note": "块文件 9,507,412 B ⇒ (9,507,412-1188)/104464 = 91，与记录 cells 自洽。"})

    # 5 落位与 pos_max
    awa = w.get("lease_chain", {}).get("answer_while_attached", {})
    rng = awa.get("range")
    ask_pos = awa.get("ask_pos")
    steps = {s.get("step"): s for s in w.get("lease_chain", {}).get("steps", [])}
    reload_step = steps.get("reload_and_place", {})
    pos_max_raw = reload_step.get("pos_max_raw")
    items.append({
        "id": 5, "claim": "块落位与 pos_max = [4005,4096) / 4095",
        "expected": {"range": [4005, 4096], "pos_max": 4095},
        "recomputed": {"answer_while_attached.range": rng, "ask_pos": ask_pos,
                       "reload_and_place.pos_max_raw": pos_max_raw,
                       "anchor.blocks[0].pos_lo/pos_hi": [a["blocks"][0]["pos_lo"],
                                                          a["blocks"][0]["pos_hi"]]},
        "source": "run_m4_write.json:.lease_chain.answer_while_attached / .steps[reload_and_place]",
        "match": rng == [4005, 4096] and ask_pos == 4096 and pos_max_raw == 4095,
        "note": "两个口径别混：**attach 到对话时**的落位是 [4005,4096)（pos_max_raw=4095）；"
                "a4.blocks 的 pos_lo/pos_hi=0/90 是块**在文件里**的 position-0 独占落位。"
                "本项按 §6.1 的『delta=+4005』口径核 attach 侧。"})

    # 6 memory 行数与相对时间锚定
    anchored = [r for r in rows_mem if r[5] is not None]
    items.append({
        "id": 6, "claim": "memory 行数 = 6（含相对时间锚定 2026-10-28）",
        "expected": {"rows": 6, "anchored_rows": 1, "anchored_value": "2026-10-28"},
        "recomputed": {"rows": len(rows_mem),
                       "anchored_rows": [(r[0], r[1], r[5]) for r in anchored],
                       "others_none": sum(1 for r in rows_mem if r[5] is None)},
        "source": "m4_memory.db::memory(*, anchored_time)；run_m4_verify_a4.json:.stored",
        "match": len(rows_mem) == 6 and len(anchored) == 1 and anchored[0][5] == "2026-10-28",
        "note": "只有『计划』一行 anchored_time=2026-10-28，其余 5 行 None —— 与 M4-ACCEPT §0 "
                "第 7 项冻结的期望一致（原写法读作六行都有，已收紧）。"})

    # 7 memory_source 行数
    fanout = [r[3] for r in rows_src]
    items.append({
        "id": 7, "claim": "`memory_source` 行数 = 7",
        "expected": 7, "recomputed": {"db memory_source rows": len(rows_src),
                                      "rows": rows_src, "fanout": fanout,
                                      "fanout_sum": sum(fanout),
                                      "conv_rows": n_conv,
                                      "write.db.sources": w.get("db", {}).get("sources"),
                                      "a4.sources": len(a.get("sources", [])),
                                      "retrieval_units.dedup": w.get("retrieval_units", {}).get("dedup")},
        "source": "m4_memory.db::memory_source(count/fanout)；run_m4_write.json:.db.sources / "
                  ".retrieval_units.dedup；run_m4_verify_a4.json:.sources",
        "match": len(rows_src) == 7,
        "note": "实得 5 = 1 段级行(conv) + 4 条去重后检索单元；fanout=[1,2,1,2] 和为 6 = keeps。"
                "7 是 **R9 去重前**的读数（1 段级行 + 6 条单元，README 备份 L9/L63："
                "\"7 行 memory_source（1 块 + 6 条检索单元）\"）。放行条件 3 落地后 "
                "memory_source 加了 UNIQUE(text)+fanout，重复文本的 unit3=unit4、unit6=unit7 合并 ⇒ 5 行。"
                "**这不是回退，是口径变了**；若按『单元数』算，去重前 6 → 去重后 4（fanout 记 6）。"})

    # 8 新进程检索作答
    sc = a.get("search_checks", [])
    ac = a.get("answer_checks", [])
    parent = a.get("parent_pid")
    search_ok = [(c["q"], c["pid"], c.get("new_process"), c["pid"] != parent) for c in sc]
    answer_ok = [(c["q"], c["pid"], c.get("child_of"), c.get("new_process"), c.get("hit"))
                 for c in ac]
    acc = a.get("acceptance", {})
    items.append({
        "id": 8, "claim": "新进程检索并正确作答 = 9/9",
        "expected": "9/9",
        "recomputed": {"search_checks": search_ok, "answer_checks": answer_ok,
                       "parent_pid": parent,
                       "pairs_ok": "%d/%d 检索 + %d/%d 作答" % (
                           sum(1 for x in search_ok if x[2] and x[3]), len(search_ok),
                           sum(1 for x in answer_ok if x[4]), len(answer_ok)),
                       "acceptance_keys_true": "%d/%d" % (sum(1 for v in acc.values() if v), len(acc)),
                       "acceptance_all_pass": acc.get("all_pass"),
                       "judge_sample_9_of_9": "%d/%d" % (sum(1 for t in ev["sample"] if t.get("match")),
                                                         len(ev["sample"]))},
        "source": "run_m4_verify_a4.json:.search_checks / .answers (=answer_checks) / .acceptance；"
                  "evidence_m4_judge.json:.sample[*].match",
        "match": False,
        "note": "**字面 9/9 没有原件**：锚里只有 2 问 2 答（住址/车牌），每次 verify 都是 QUESTIONS=2。"
                "README 备份 L9-10 的原句是『新进程检索到该块、另两个新进程逐字答出住址与车牌。"
                "9/9 验收项全过』——『9/9』指**九项验收全过**，不是 9 个问答。"
                "实质可复算部分：新进程检索 2/2（pid 与 parent 两两不等，new_process=true）、"
                "新进程作答 2/2（hit=true）、a4.acceptance 17/17 全 true（含 all_pass）；"
                "另有 evidence_m4_judge.sample 9/9 逐轮与冻结预期一致（README L41 的另一个 9/9）。"
                "按字面 9/9 记 match=false，不改口径凑 true。"})

    # 9 锚 sha
    items.append({
        "id": 9, "claim": "锚 = run_m4_verify_a4.json = 59edbd82d4b9ae44（块 81127d24fd64b96b / 9,507,412 B）",
        "expected": {"anchor_sha16": ANCHOR_SHA16_WANT, "block_sha16": BLOCK_SHA16_WANT,
                     "block_bytes": BLOCK_BYTES_WANT},
        "recomputed": {"anchor_sha16": pre[ANCHOR]["sha16"], "anchor_bytes": pre[ANCHOR]["bytes"],
                       "block_sha16": pre[BLOCK]["sha16"], "block_sha256": pre[BLOCK]["sha256"],
                       "block_bytes": pre[BLOCK]["bytes"]},
        "source": "对文件字节重算 sha256[:16]",
        "match": anchor_ok and block_ok,
        "note": "锚与块 gcd 与磁盘一致；块只在本机（PROGRESS §6.1 注）。"})

    # ---------------- 三个未闭项 ----------------
    per_field = a.get("output_filter_counts", {}).get("per_field", [])
    tag_fields = [f for f in per_field if f.get("per_tag")]
    deliv_clean = all(f.get("delivered_has_tag") == 0 for f in per_field)
    selftest_cases = {c["case"]: c for c in st.get("cases", [])}
    s2 = selftest_cases.get("S2", {})
    s7 = selftest_cases.get("S7", {})
    disp_dupes = [c["answer_display"] for c in ac]
    open_items = [
        {
            "id": "O1",
            "claim": "放行条件 1：`</think` 泄漏必须记录并处置（输出层白名单过滤 + 计数进 json + "
                     "一条会失败的断言），不许靠改块正文解决；重复句一并处置（交付取首句或同句去重）。",
            "status": "部分覆盖（标签侧已闭；**重复句处置仍缺**）",
            "evidence": [
                "输出层白名单过滤：outfilter.py（sha16 %s）只认 </?think>,</?response>,<|im_start|> 等白名单；"
                "S5 未知尖括号只报告不删、S7 块正文含标签直接 REFUSE（%s）" % (pre[OUTFILTER_PY]["sha16"],
                                                                              s7.get("raw_line")),
                "计数进 json：a4.output_filter_counts.per_field = 2 个字段各 think×1、tag_chars_removed=8、"
                "delivered_has_tag=0；measured_on=raw answer（不在已归一化的 delivered 上量）",
                "会失败的断言：run_m4_outfilter_selftest.json（sha16 %s）S2 = 同一文本关掉 filter ⇒ "
                "raised %r（raw_line=%r），assertion_is_load_bearing=%r，verdict=%r" % (
                    pre[OUTFILTER_SELFTEST]["sha16"], s2.get("raised"), s2.get("raw_line"),
                    st.get("assertion_is_load_bearing"), st.get("verdict")),
                "a4.answer_checks[*]：raw_has_tag=true、display_has_tag=false、raw_kept_unchanged=true、"
                "output_layer_clean=true、idempotent=true",
                "**仍缺（重复句）**：a4.answer_checks[*].answer_display 仍是同一句两遍 —— %r；"
                "content_warnings=[]；m4_display.py 有 first_sentence_only/derive(first_sentence=False) "
                "但交付路径没启用，也没有『重复句命中次数』进 json" % (disp_dupes,),
            ],
            "affects_nine": False,
            "note": "标签污染侧三条处置都已落地且有会红的断言；M4-ACCEPT §1 的第二个污染"
                    "（滤掉标签后 X\\n\\nX 重复两遍）只做到『原样保留 + 可事后看』，没做到『处置 + 计数』。"
                    "它不在九项 acceptance 里，故不影响九项成立性，但按放行条件 1 的原文仍未闭。"},
        {
            "id": "O2",
            "claim": "放行条件 2：跨实验那句改成『支持性观察』，并补上『同一 M4 布局删掉车牌句』的对照实验，"
                     "否则不许升级措辞。",
            "status": "已被覆盖（对照已补；措辞强度=『内容承载』，混淆必须同引）",
            "evidence": [
                "run_m4_ablate_plate_a7.json（sha16 %s，attempt 7，4 臂）" % pre[ABLATE_A7]["sha16"],
                "四臂：product_block_control 91 cells→%r；reencoded_with_sentence 91→%r；"
                "ablated_without_sentence 79 cells→%r；length_matched_control 91→%r" % (
                    a7["comparison"]["answers_side_by_side"][0]["answer_raw"][:20],
                    a7["comparison"]["answers_side_by_side"][1]["answer_raw"][:20],
                    a7["comparison"]["answers_side_by_side"][2]["answer_raw"][:20],
                    a7["comparison"]["length_matched"]["answer_raw"][:20]),
                "comparison: same_position=%r / same_question=%r / encoding_path_controlled=%r / "
                "cells_loaded=%r / answers_plate=%r" % (
                    a7["comparison"]["same_position"], a7["comparison"]["same_question"],
                    a7["comparison"]["encoding_path_controlled"],
                    a7["comparison"]["cells_loaded"], a7["comparison"]["answers_plate"]),
                "版本链：run_m4_ablate_plate_a5.json（sha16 %s，attempt 5，3 臂）" % pre[ABLATE_A5]["sha16"],
                "PROGRESS §6.5 已写：verdict=memory_carried_by_that_sentence_content_not_length，"
                "并强制同引 length_confound_note=%r" % (a7["comparison"]["length_confound_note"][:90],),
            ],
            "affects_nine": False,
            "note": "缺的那个对照实验（同一 M4 布局删掉车牌句再问）已经做过，**没有被静默升级成 A/B 证实**："
                    "等长对照与产品块不同源这一处混淆仍写在产物里，措辞强度停在『内容承载』。"},
        {
            "id": "O3",
            "claim": "放行条件 3：检索单元按 R9 按文本去重 + 记 fanout；memory.type 空列处理掉。",
            "status": "已被覆盖（去重+fanout+type 均已落地）",
            "evidence": [
                "m4_memory.db::memory_source 5 行，fanout=%r（和=6=keeps），conv 段级行 1 行；"
                "去重前是 1 段级+6 单元（README 备份 L9/L63）" % (fanout,),
                "run_m4_write.json:.retrieval_units.dedup=%r（unique_units=4，fanout_sum=6）" % (
                    w.get("retrieval_units", {}).get("dedup"),),
                "memory.type 全有值：%r；memory 列含 resolved/resolved_to（%s）" % (
                    sorted({r[3] for r in rows_mem}),
                    "resolved" in cols_mem and "resolved_to" in cols_mem),
                "a4.acceptance 9_units_deduped_by_text=%r、10_type_and_resolved=%r" % (
                    acc.get("9_units_deduped_by_text"), acc.get("10_type_and_resolved")),
            ],
            "affects_nine": "影响九项第 7 项的**数值口径**（7→5），不构成能力回退",
            "note": "这条落地正是第 7 项 match=false 的原因：memory_source 由 7 行（1+6）变 5 行（1+4，"
                    "fanout 和 6）。九项里第 7 项的『7』是去重前读数，未随实现更新。"},
    ]

    extra_gaps = [{
        "id": "G-anchored",
        "claim": "M4-ACCEPT §3-① 的实用缺口：anchored_time 不在检索单元文本里（单元文本是整句，"
                 "含『下周三』原串），问『2026-10-28 有什么安排』命中不了；建议 unit 侧增加 "
                 "value+anchored_time 派生文本。",
        "status": "仍缺",
        "evidence": ["memory_source 的 4 条单元文本 = %r" % ([u[4] for u in units],),
                     "其中含 2026-10-28 的单元数 = %d" % sum(1 for u in units if "2026-10-28" in (u[4] or ""))],
        "affects_nine": False,
        "note": "不是三条放行条件之一，属记录项；不影响九项。"}]

    # ---------------- 汇总 ----------------
    post = {p: finfo(p) for p in READ_FILES}
    post["script"] = finfo(os.path.abspath(__file__))
    drift = {p: [pre[p]["sha16"], post[p]["sha16"]] for p in pre if pre[p]["sha16"] != post[p]["sha16"]}
    inv = []
    if drift:
        inv.append("所读文件/脚本跑前跑后 sha16 漂移：%s" % json.dumps(drift, ensure_ascii=False))
    matched = [it for it in items if it["match"]]
    mism = [it for it in items if not it["match"]]
    out = {
        "schema": "m4_accept_recompute_v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "readonly": {"gpu_used": False, "model_loaded": False, "new_anchor": False,
                     "note": "只读复算：不跑 14B、不产新锚；只读 JSON/SQLite/块文件/判据文档"},
        "script": post["script"],
        "accept_doc": dict(pre[ACCEPT_DOC], lines=238),
        "readme_doc": pre[README_DOC],
        "progress_ref": {"path": PROGRESS.replace("\\", "/"), "sha16": pre[PROGRESS]["sha16"],
                         "section": "§6.3 L855-872（九项计数口径摘要）"},
        "anchor": dict(pre[ANCHOR], expected_sha16=ANCHOR_SHA16_WANT, match=anchor_ok),
        "block": dict(pre[BLOCK], expected_sha16=BLOCK_SHA16_WANT,
                      expected_bytes=BLOCK_BYTES_WANT, cells_derived=cells_file, match=block_ok),
        "inputs": [{"path": p.replace("\\", "/"), "sha16": pre[p]["sha16"], "bytes": pre[p]["bytes"]}
                   for p in READ_FILES],
        "items": items,
        "open_items": open_items,
        "other_gaps": extra_gaps,
        "match_count": "%d/%d" % (len(matched), len(items)),
        "all_match": len(mism) == 0,
        "mismatches": [{"id": it["id"], "expected": it["expected"], "recomputed": it["recomputed"],
                        "why": it["note"]} for it in mism],
        "sha_stable": {"ok": not drift, "pre": {p: pre[p]["sha16"] for p in pre},
                       "post": {p: post[p]["sha16"] for p in post}},
        "invariant_failures": inv,
        "not_touched": ["kvmem/m4c_leases/**（M4C 台账/产物）", "kvmem/m2_visibility/m5/**（M5 台账/产物）",
                        "docs/_work/**"],
        "device_note": "本轮无 GPU、无 14B 加载；GPU 0 次、模型调用 0 次",
        "exit": 0 if not inv else 2,
        "exit_semantics": "0=产物落地且不变量全过（match=false 照实记录，不等于脚本失败）；"
                          "2=所读文件/脚本 sha 漂移；3=锚/块 sha 不符（停手，不落产物）",
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_path = os.path.join(OUTDIR, OUT_NAME)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    s16 = finfo(out_path)["sha16"]
    os.makedirs(BEFORE, exist_ok=True)
    copy = os.path.join(BEFORE, "%s@%s" % (OUT_NAME, s16))
    with open(out_path, "rb") as f1, open(copy, "wb") as f2:
        f2.write(f1.read())
    reg = {"entries": []}
    if os.path.exists(REGISTER):
        reg = json.load(open(REGISTER, encoding="utf-8"))
        reg.setdefault("entries", [])
    reg["entries"].append({
        "source_name": OUT_NAME, "source_sha16": s16,
        "copy_path": os.path.abspath(copy).replace("\\", "/"), "in_place": False,
        "copy_time": time.strftime("%Y-%m-%dT%H:%M:%S"), "copyist": "executor",
        "reason": "M4 验收九项只读复算产物落档（不跑 14B、不产新锚；第 7/8 项 match=false 照实记录）"})
    with open(REGISTER, "w", encoding="utf-8", newline="\n") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    print(json.dumps({"out": out_path.replace("\\", "/"), "sha16": s16,
                      "bytes": finfo(out_path)["bytes"], "exit": out["exit"],
                      "match_count": out["match_count"], "all_match": out["all_match"],
                      "mismatch_ids": [m["id"] for m in mism],
                      "sha_stable": not drift, "elapsed_s": out["elapsed_s"]},
                     ensure_ascii=False))
    return out["exit"]


if __name__ == "__main__":
    sys.exit(main())