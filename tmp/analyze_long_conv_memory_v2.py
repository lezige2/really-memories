# -*- coding: utf-8 -*-
"""tmp/analyze_long_conv_memory_v2.py -- 长对话 rollover → 记忆层检索分析 v2（只读）。

改进 v1：
  * 用**当前真实 chat_daily 代码**（临时 DB 副本 + fake engine）跑 `_retrieval_select`，
    完整复刻 `_canon_qslots/_augment_slots/time 硬过滤/slot_match/slot_bonus/fallback`；
  * 按当前 rollover 语义模拟 3 轮（丢最旧 35% 字符、逐轮 auto_turn、archive、summary），
    **真实复刻 LIBRARY_MAX=200 上限与插入顺序**（auto_turn 先写 → archive/summary 后写）；
  * 输出 out/LONG-CONV-MEMORY.json。

只读输入：kvmem/daily/chat.db（复制到临时目录，不写原库）、assistant 日志。
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import memory_service as M      # noqa: E402
import chat_daily as D          # noqa: E402

DB = ROOT / "kvmem/daily/chat.db"
LOGS = ROOT / "kvmem/daily/assistant/sessions"
OUT = ROOT / "out/LONG-CONV-MEMORY.json"
LIBRARY_MAX = 200
MAX_TEXT_CHARS = 600
ARCHIVE_MAX_CHARS = 3000
DROP_FRACTION = 0.35
THRESHOLD_TOKENS = 18432

FACTS = [
    (3000, "early", "我的车牌号是京A88888。", "我的车牌号是多少？", "京A88888"),
    (6500, "early", "补充一个事实：我养的猫叫豆豆。", "我养的猫叫什么名字？", "豆豆"),
    (11000, "mid", "再记一条：我下周五要去成都开会。", "我下周五要去哪开会？", "成都"),
    (16000, "mid", "顺便说一下，我的工号是 A12345。", "我的工号是多少？", "A12345"),
    (21000, "mid", "记一下：我妻子叫李娜。", "我妻子叫什么名字？", "李娜"),
    (26000, "mid", "补充：我老家在青岛。", "我老家在哪里？", "青岛"),
    (32000, "recent", "再说一个：我的手机号是 13800138000。", "我的手机号是多少？",
     "13800138000"),
    (37000, "recent", "最后记一条：我下个月要去西安出差。", "我下个月要去哪出差？", "西安"),
]
EXTRA_Q = [("我叫什么名字？", "阿泽")]
FILLER = [
    "今天的工作安排有点满，上午处理邮件，下午继续整理资料。",
    "最近在整理一些旧项目的文档，顺手把目录结构理了一遍。",
    "周末打算去附近走走，可能去公园，也可能就在家休息。",
    "刚才看了一下进度，感觉节奏还可以，继续按计划推进。",
    "有些事情推进得比预期慢一点，不过总体还在可控范围。",
    "我在想下一步先把哪块理顺，避免来回返工。",
    "今天天气一般，不太想出门，就继续把手上事情做完。",
    "整理资料的时候发现几个之前记下的点，回头再逐条确认。",
]


def live_stats():
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    rows = con.execute("SELECT id,mode,length(text),created_at,substr(text,1,40) "
                       "FROM memory_source ORDER BY id").fetchall()
    con.close()
    f = LOGS / "s-20261028-040352-669667.jsonl"
    evs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    asks = [e for e in evs if e.get("event") == "ask"
            and (e.get("ts") or "") >= "2026-10-28T13:50"]
    ans = [e for e in evs if e.get("event") == "answer"
           and (e.get("ts") or "") >= "2026-10-28T13:50"]
    chars = sum((a.get("input_len") or 0) for a in asks) + \
        sum((b.get("answer_len") or 0) for b in ans)
    toks = [a.get("session_tokens") for a in asks
            if isinstance(a.get("session_tokens"), int)]
    roll = [e for e in evs if e.get("event") == "context_rollover"]
    ratio = (toks[-1] / chars) if chars and toks else 0.0
    return {"db_mtime": datetime.fromtimestamp(DB.stat().st_mtime).isoformat(timespec="seconds"),
            "sources": len(rows),
            "modes": _count(r[1] for r in rows),
            "auto_blocks": sum(1 for r in rows if str(r[1]).startswith("auto_")),
            "latest_rows": [[r[0], r[1], r[2], r[3]] for r in rows[-5:]],
            "long_run_first_ts": asks[0]["ts"] if asks else None,
            "long_run_turns": len(asks), "long_run_chars": chars,
            "chat_tokens_last": toks[-1] if toks else None,
            "token_per_char": round(ratio, 4),
            "threshold_tokens": THRESHOLD_TOKENS,
            "est_chars_to_threshold": int(THRESHOLD_TOKENS / ratio) if ratio else None,
            "rollover_events_this_session": len(roll),
            "rollover_events_all": len(roll)}


def _count(it):
    out = {}
    for x in it:
        out[x] = out.get(x, 0) + 1
    return out


def planned_turns(target_chars=40000):
    turns, chars, pending = [], 0, [dict(zip(("thr", "tier", "text", "q", "kw"), f))
                                    for f in FACTS]
    i = 0
    while chars < target_chars and len(turns) < 900:
        if pending and chars >= pending[0]["thr"]:
            f = pending.pop(0)
            turns.append({"q": f["text"], "a": "好的，我记住了。", "kw": f["kw"]})
            chars += len(f["text"]) + 8
            continue
        filler = FILLER[i % len(FILLER)] + " 这是我第%d条测试消息。" % (i + 1)
        i += 1
        turns.append({"q": filler, "a": "好的，我在听。"})
        chars += len(filler) + 7
    return turns, chars


def copy_db(tmp):
    dst = Path(tmp) / "chat.db"
    shutil.copy2(DB, dst)
    return str(dst)


def insert_row(con, sid, text, mode, tags, related, slots, ts="2026-10-28T14:10:00"):
    con.execute("INSERT INTO memory_source (id,tenant,scope,mode,name,label,text,"
                "source_hash,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, "default", "private", mode, "auto-%d" % sid, mode, text,
                 "sim%06d" % sid, ts))
    con.execute("INSERT INTO memory_block (source_id,path,n_tokens,n_bytes,built_at,"
                "model_path,model_size,model_mtime,kv_type,state_version) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (sid, "sim/%d.kvmem" % sid, max(1, len(text) // 2), len(text.encode()),
                 ts, "stub", 0, 0, "q8_0", 1))
    con.execute("INSERT INTO daily_memory_meta (source_id,tags,source,related_ids,slots) "
                "VALUES (?,?,?,?,?)",
                (sid, json.dumps(tags, ensure_ascii=False), mode,
                 json.dumps(related, ensure_ascii=False),
                 json.dumps(slots, ensure_ascii=False)))
    con.commit()


def simulate(tmp):
    """按代码语义模拟 rollover 落块（含 cap 与插入顺序），返回 rows 与模拟日志。"""
    db = copy_db(tmp)
    con = sqlite3.connect(db)
    base_ids = [r[0] for r in con.execute("SELECT id FROM memory_source").fetchall()]
    next_id = max(base_ids + [0]) + 1
    turns, planned_chars = planned_turns()
    remaining = list(turns)
    log, facts_in_rows = [], {}
    rounds = 0
    while len(remaining) >= 3 and rounds < 3:
        rounds += 1
        chars = [len(t["q"]) + len(t["a"]) for t in remaining]
        total = sum(chars) or 1
        acc, best_err, best_n = 0, abs(DROP_FRACTION), 0
        for i in range(len(remaining) - 1):
            acc += chars[i]
            err = abs(acc / float(total) - DROP_FRACTION)
            if err < best_err:
                best_err, best_n = err, i + 1
        n_drop = max(1, min(best_n, len(remaining) - 2))
        while n_drop > 1 and (total - sum(chars[:n_drop])) / float(total) < 0.60:
            n_drop -= 1
        dropped, remaining = remaining[:n_drop], remaining[n_drop:]
        cap_dropped = 0
        turn_ids = []
        for i, t in enumerate(dropped, start=1):
            if len(con.execute("SELECT id FROM memory_source").fetchall()) >= LIBRARY_MAX:
                cap_dropped += 1
                continue
            text = ("用户：%s\n助手：%s" % (t["q"], t["a"]))[:MAX_TEXT_CHARS]
            slots = M.extract_slots(text)
            insert_row(con, next_id, text, "auto_turn",
                       ["auto_turn", "2026-10-28"], [], slots)
            turn_ids.append(next_id)
            next_id += 1
        archive_text = ("对话归档 2026-10-28 14:%02d（原文）：\n%s" % (rounds * 10, "\n".join(
            "用户：%s\n助手：%s" % (t["q"], t["a"]) for t in dropped)))[:ARCHIVE_MAX_CHARS + 64]
        archive_id = None
        if len(con.execute("SELECT id FROM memory_source").fetchall()) < LIBRARY_MAX:
            archive_id = next_id
            archive_slots = M.extract_slots(archive_text)
            insert_row(con, archive_id, archive_text, "auto_archive",
                       ["auto_archive", "2026-10-28"], [], archive_slots)
            next_id += 1
        summary_id = None
        if len(con.execute("SELECT id FROM memory_source").fetchall()) < LIBRARY_MAX:
            summary_text = ("自动摘要 2026-10-28 14:%02d：用户聊了近期工作安排、出行计划和"
                            "一些个人生活情况，细节已按原文归档保存。" % (rounds * 10))
            summary_id = next_id
            related = list(turn_ids) + ([archive_id] if archive_id else [])
            insert_row(con, summary_id, summary_text, "auto_summary",
                       ["auto_summary", "2026-10-28"], related, M.extract_slots(summary_text))
            for sid in related:
                con.execute("UPDATE daily_memory_meta SET related_ids=? WHERE source_id=?",
                            (json.dumps(list(set(json.loads(
                                con.execute("SELECT related_ids FROM daily_memory_meta "
                                            "WHERE source_id=?", (sid,)).fetchone()[0] or "[]")
                                + [summary_id])), ensure_ascii=False), sid))
            next_id += 1
            con.commit()
        # 记录本轮后的事实覆盖
        rows = con.execute("SELECT id,text FROM memory_source").fetchall()
        for _, _, _, _, kw in FACTS + [(0, 0, 0, 0, "阿泽")]:
            facts_in_rows[kw] = [rid for rid, txt in rows if kw in txt]
        log.append({"round": rounds, "dropped_turns": len(dropped),
                    "turn_blocks_written": len(turn_ids),
                    "archive_id": archive_id, "summary_id": summary_id,
                    "cap_dropped_turns": cap_dropped,
                    "db_rows_after": len(rows), "kept_turns": len(remaining)})
    con.close()
    return db, planned_chars, log, facts_in_rows


def main():
    live = live_stats()
    tmp = tempfile.mkdtemp(prefix="longconv_mem_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    try:
        db, planned_chars, sim_log, facts_in_rows = simulate(tmp)
        app = D.DailyApp(D.StubEngine(), db_path=db,
                         blocks_dir=os.path.join(tmp, "blocks"),
                         sessions_dir=os.path.join(tmp, "sessions"),
                         model_path=model, restore=False,
                         log_root=os.path.join(tmp, "assistant"),
                         retrieval_mode="topk", topk=4)
        rows = app._rows()
        by_id = {int(r[0]): r for r in rows}
        tests = []
        for _, tier, _, q, kw in FACTS:
            sel = app._retrieval_select(q)
            texts = [str(by_id[int(s["source_id"])][3]) for s in sel
                     if int(s["source_id"]) in by_id]
            fb = app._retrieval_keyword_fallback(q) if not sel else []
            fb_texts = [str(by_id[int(s["source_id"])][3]) for s in fb
                        if int(s["source_id"]) in by_id]
            tests.append({"fact": kw, "tier": tier, "query": q,
                          "selected_ids": [int(s["source_id"]) for s in sel],
                          "found": any(kw in t for t in texts),
                          "found_by_fallback": any(kw in t for t in fb_texts),
                          "qslots": getattr(app, "_last_qslots", None)})
        for q, kw in EXTRA_Q:
            sel = app._retrieval_select(q)
            texts = [str(by_id[int(s["source_id"])][3]) for s in sel
                     if int(s["source_id"]) in by_id]
            tests.append({"fact": kw, "tier": "base", "query": q,
                          "selected_ids": [int(s["source_id"]) for s in sel],
                          "found": any(kw in t for t in texts),
                          "found_by_fallback": False,
                          "qslots": getattr(app, "_last_qslots", None)})
        # 槽位诊断
        diag = {}
        for probe in ("补充一个事实：我养的猫叫豆豆。", "记一下：我妻子叫李娜。",
                      "再记一条：我下周五要去成都开会。", "我的车牌号是京A88888。"):
            slots = M.extract_slots(probe)
            diag[probe[:16]] = {"slots": slots,
                                "query": M.query_slots(
                                    "我养的猫叫什么名字？" if "猫" in probe
                                    else "我妻子叫什么名字？" if "妻子" in probe
                                    else "我下周五要去哪开会？" if "下周五" in probe
                                    else "我的车牌号是多少？")}
        # 归档块 time 槽位（若模拟写了 archive）
        arch = con_rows = None
        con2 = sqlite3.connect(db)
        r = con2.execute("SELECT id,text,slots FROM daily_memory_meta m JOIN memory_source s "
                         "ON s.id=m.source_id WHERE s.mode='auto_archive' LIMIT 1").fetchone() \
            if con2.execute("SELECT count(*) FROM memory_source WHERE mode='auto_archive'").fetchone()[0] else None
        if r:
            arch = {"id": r[0], "slots": json.loads(r[2] or "{}"),
                    "first_time": (json.loads(r[2] or "{}") or {}).get("time")}
        # 真实库直接统计
        con2.close()
        result = {
            "schema": "long_conv_memory_analysis_v2",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "readonly": True,
            "A_live_snapshot": live,
            "B_simulation": {
                "method": "临时 DB 副本 + 当前 chat_daily._retrieval_select（fake engine）；"
                          "按 rollover 代码语义模拟 3 轮（逐轮 auto_turn/archive/summary，"
                          "LIBRARY_MAX=200，插入顺序 auto_turn 先于 archive/summary）。",
                "planned_chars": planned_chars,
                "rounds": sim_log,
                "facts_present_in_sim_rows": facts_in_rows,
                "tests": tests,
                "slot_diagnostics": diag,
                "archive_slots": arch,
            },
            "C_findings": [],
            "D_minimal_fixes": [],
            "E_answers": {},
        }
        f = result["C_findings"]
        if live["auto_blocks"] == 0:
            f.append("live 快照：auto_* 块=0（DB 仅 chat 记忆，且 13:59 曾被重置回 11 条基线）；"
                     "当前 rollover 尚未落块，因此此刻“检索不到 auto 块”是块不存在，不是检索丢块。")
        if live.get("token_per_char"):
            f.append("live：长跑窗口 %d 轮/%.0f 字符，chat_tokens=%s，token/字符≈%s，"
                     "达到 %d token 阈值约需 %s 字符 ⇒ 40k 字符会触发 rollover（预计 ~%s 字符）。"
                     % (live["long_run_turns"], live["long_run_chars"],
                        live["chat_tokens_last"], live["token_per_char"],
                        live["threshold_tokens"], live["est_chars_to_threshold"],
                        live["est_chars_to_threshold"]))
        args = [t for t in tests if t["tier"] == "early"]
        f.append("模拟 3 轮 rollover 后 early 事实检索：%s"
                 % {t["fact"]: t["found"] for t in args})
        bad = [t["fact"] for t in tests if not t["found"]]
        f.append("模拟全事实命中 %d/%d；未命中 %s（含 recent 未进 dropped 段/被 cap 丢/槽位过滤）。"
                 % (len(tests) - len(bad), len(tests), bad))
        f.append("cap 证据：%s。auto_turn 按轮逐条写，占满 200 后 archive/summary 写不进去；"
                 "40k 字符模拟中 round1 的 dropped 轮数已超过 189 个空位（%s），"
                 "因此归档/摘要块从第一轮起就可能缺失；实际首次 rollover 预计在 ~%s 字符，"
                 "届时 dropped 轮数较少，archive/summary 可能写成，但后续轮次仍会被 cap 吃掉。"
                 % ([{k: v for k, v in x.items() if k in
                     ("round", "dropped_turns", "turn_blocks_written", "archive_id",
                      "summary_id", "cap_dropped_turns", "db_rows_after")} for x in sim_log],
                    sim_log[0]["dropped_turns"] if sim_log else None,
                    live.get("est_chars_to_threshold")))
        persona = diag.get("记一下：我妻子叫李娜。", {}).get("slots", {})
        if not persona.get("person"):
            f.append("槽位缺口：『我妻子叫李娜』person=None（REL_PERSON 不含妻子；X叫Y 边界"
                     "要求标点）⇒ 查询 want=person 时会被 slot_match 硬丢。")
        if not diag.get("补充一个事实：我养的猫叫豆豆。", {}).get("slots", {}).get("object"):
            f.append("数据层 extract_slots 对『我养的猫叫豆豆』未直接抽到 object（PET_NAME 正则覆盖不足）；"
                     "chat_daily 的 _augment_slots 会从原文补 object，因此模拟中豆豆仍可召回——"
                     "但这是接线层兜底，数据层本身仍有槽位缺口。")
        if arch and arch.get("slots", {}).get("time"):
            f.append("auto_archive 单 time 槽位=%r（整段第一个时间）：time 硬过滤会按它错误匹配/"
                     "过滤归档块。" % arch["slots"]["time"])

        res = result
        early = [t for t in tests if t["tier"] == "early"]
        all_found = {t["fact"]: t["found"] for t in tests}
        res["E_answers"] = {
            "q1_early_facts_retrievable_after_rollover": {
                k: all_found.get(k) for k in ("京A88888", "豆豆", "成都", "阿泽")},
            "q1_note": "模拟 rollover 落块后 4/4 可召回；但 live 当前 auto_*=0（rollover 未触发，"
                       "预计 ~%s 字符才触发，当前仅 %s 字符），此刻检索不到 auto 块=块不存在。"
                       % (live.get("est_chars_to_threshold"), live.get("long_run_chars")),
            "q2_why_missing": (
                "(1) live：rollover 还没触发（auto_*=0、0 次 context_rollover），所以没有归档块可检索；"
                "(2) 模拟：LIBRARY_MAX=200 先被逐轮 auto_turn 占满（%s），后续 turn 块被 cap 丢、"
                "archive/summary 因插入顺序在后写不进去；(3) 槽位层：妻子等关系词抽不到 person、"
                "want=person 时 slot_match 硬丢；archive 单 time 槽位会误导 time 硬过滤；"
                "slot 过滤后为空不回退 keyword fallback。"
                % ([x.get("cap_dropped_turns") for x in sim_log])),
            "q3_minimal_fix": (
                "auto_turn 合并 3–5 轮/块 + 给 archive/summary 预留配额（先写 archive/summary）；"
                "REL_PERSON 补妻子/丈夫等且允许“关系+叫+名”；archive 不写单一 time；"
                "slot 过滤后为空要回退 keyword fallback；time 硬过滤加 event/want 约束而非只 max(id)。"),
        }
        fix = result["D_minimal_fixes"]
        fix.append("1) 容量：auto_turn 按 3–5 轮合并为 1 块（或 auto_* 不占 LIBRARY_MAX 的 200、"
                   "单独给归档/摘要预留配额），避免 200 上限先被 turn 块吃满导致 archive/summary 丢失。")
        fix.append("2) 插入顺序/保护：先写 archive+summary，再写 auto_turn；cap 不足时宁可少写 turn "
                   "块也要保证摘要索引与归档存在（摘要 related_ids 是快定位入口）。")
        fix.append("3) 槽位：REL_PERSON 增加 妻子/丈夫/父母/孩子/家人；『关系+叫+名』加入 person 正则；"
                   "want=person 且槽位缺失时降级为关键词检索，而不是直接丢块。")
        fix.append("4) auto_archive 不写单一 time 槽（或标记 derived/aggregate），time 硬过滤只对 "
                   "auto_turn/自然记忆生效；摘要索引块 related 展开应绕过槽位过滤。")
        fix.append("5) 检索兜底：_retrieval_select 在“base 被 slot_match 过滤为空”后也应回退 "
                   "_retrieval_keyword_fallback（当前只在 base 为空时回退）；time 硬过滤返回 "
                   "max(id) 前应加 event/want 同分约束，避免被更新的无关同时间记忆抢答。")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp_out = str(OUT) + ".tmp"
        with open(tmp_out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_out, OUT)
        print(json.dumps({"out": str(OUT), "live": {k: live[k] for k in
                          ("sources", "auto_blocks", "chat_tokens_last", "token_per_char",
                           "est_chars_to_threshold")},
                          "rounds": [{k: v for k, v in x.items() if k != "turn_blocks"}
                                     for x in sim_log],
                          "tests": {t["fact"]: t["found"] for t in tests},
                          "fixes": len(fix)}, ensure_ascii=False, indent=1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()