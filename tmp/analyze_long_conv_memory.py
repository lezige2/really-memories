# -*- coding: utf-8 -*-
"""tmp/analyze_long_conv_memory.py -- 长对话 rollover 后记忆层检索能力分析（只读）。

只读输入：kvmem/daily/chat.db、kvmem/daily/assistant/sessions/*.jsonl（不写库、不改服务）。
输出：out/LONG-CONV-MEMORY.json
内容：
  A 实时快照：auto_turn/auto_archive/auto_summary 块数、rollover 事件、chat_tokens/阈值、
    会话字符数/token 增长比例（判断 rollover 是否/何时触发）。
  B 代码级模拟：按当前 rollover 语义（丢最旧 35% 字符、逐轮 auto_turn、3000 字归档、
    摘要索引+related、LIBRARY_MAX=200 上限）在内存构造块（不写 DB），
    用 memory_service.retrieve/query_slots/slot_match/slot_bonus 测 9 个事实查询，
    记录命中/排序/落选原因。
  C 结论与最小修复建议（只改数据层/检索权重/预算，不改提示词）。
"""
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import memory_service as M  # noqa: E402

DB = ROOT / "kvmem/daily/chat.db"
LOGS = ROOT / "kvmem/daily/assistant/sessions"
OUT = ROOT / "out/LONG-CONV-MEMORY.json"
LIBRARY_MAX = 200
MAX_TEXT_CHARS = 600
ARCHIVE_MAX_CHARS = 3000
DROP_FRACTION = 0.35

FACTS = [
    (3000, "early", "我的车牌号是京A88888。", "我的车牌号是多少？", "京A88888"),
    (6500, "early", "补充一个事实：我养的猫叫豆豆。", "我养的猫叫什么名字？", "豆豆"),
    (11000, "mid", "再记一条：我下周五要去成都开会。", "我下周五要去哪开会？", "成都"),
    (16000, "mid", "顺便说一下，我的工号是 A12345。", "我的工号是多少？", "A12345"),
    (21000, "mid", "记一下：我妻子叫李娜。", "我妻子叫什么名字？", "李娜"),
    (26000, "mid", "补充：我老家在青岛。", "我老家在哪里？", "青岛"),
    (32000, "recent", "再说一个：我的手机号是 13800138000。", "我的手机号是多少？", "13800138000"),
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


def load_rows():
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    rows = []
    for r in con.execute(
            "SELECT s.id,s.name,s.label,s.text,s.created_at,b.n_tokens FROM memory_source s "
            "LEFT JOIN memory_block b ON b.source_id=s.id ORDER BY s.id"):
        if r[5] is None:
            continue
        mode = con.execute("SELECT mode FROM memory_source WHERE id=?", (r[0],)).fetchone()[0]
        meta = {}
        mr = con.execute("SELECT tags,source,related_ids,slots FROM daily_memory_meta "
                         "WHERE source_id=?", (r[0],)).fetchone()
        if mr:
            meta = {"tags": json.loads(mr[0] or "[]"), "source": mr[1],
                    "related_ids": json.loads(mr[2] or "[]"),
                    "slots": json.loads(mr[3] or "{}")}
        rows.append({"id": int(r[0]), "name": r[1], "label": r[2], "text": r[3],
                     "created_at": r[4], "n_tokens": int(r[5]), "mode": mode,
                     "tags": meta.get("tags", []), "source": meta.get("source"),
                     "related_ids": meta.get("related_ids", []),
                     "slots": meta.get("slots") or M.extract_slots(r[3])})
    con.close()
    return rows


def load_events():
    evs = []
    for f in LOGS.glob("*.jsonl"):
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    evs.append(json.loads(line))
        except (OSError, ValueError):
            pass
    evs.sort(key=lambda e: (e.get("ts") or ""))
    return evs


def snapshot(rows, evs):
    modes = {}
    for r in rows:
        modes[r["mode"]] = modes.get(r["mode"], 0) + 1
    asks = [e for e in evs if e.get("event") == "ask"]
    answers = [e for e in evs if e.get("event") == "answer"]
    chars = sum((a.get("input_len") or 0) for a in asks) + \
        sum((b.get("answer_len") or 0) for b in answers)
    toks = [a.get("session_tokens") for a in asks if isinstance(a.get("session_tokens"), int)]
    roll = [e for e in evs if e.get("event") == "context_rollover"]
    # 最近会话的一段（按最后 rollover/最新 ask 取尾部）
    tail = asks[-30:]
    ratio = (tail[-1].get("session_tokens") or 0) / max(1, chars) if tail else None
    return {"db": str(DB), "sources": len(rows), "modes": modes,
            "auto_blocks": sum(v for k, v in modes.items() if str(k).startswith("auto_")),
            "rollover_events": len(roll),
            "asks_all": len(asks), "chars_all": chars,
            "chat_tokens_last": toks[-1] if toks else None,
            "token_per_char_obs": round(ratio, 4) if ratio else None,
            "threshold_tokens": 18432, "rollover_at": 0.75,
            "session_tokens_tail": toks[-8:],
            "rollover_sample": roll[-2:]}


def build_planned_turns(target_chars=40000):
    """按 long_conv_test_v2 的事实阈值与 filler 生成对话轮（问题/答案文本）。"""
    turns, chars, pending = [], 0, [dict(zip(("thr", "tier", "text", "q", "kw"), f))
                                    for f in FACTS]
    i = 0
    while chars < target_chars and len(turns) < 800:
        if pending and chars >= pending[0]["thr"]:
            f = pending.pop(0)
            turns.append({"q": f["text"], "a": "好的，我记住了。", "fact": f["kw"]})
            chars += len(f["text"]) + 8
            continue
        filler = FILLER[i % len(FILLER)] + " 这是我第%d条测试消息。" % (i + 1)
        i += 1
        turns.append({"q": filler, "a": "好的，我在听。"})
        chars += len(filler) + 7
    return turns, chars


def simulate_rollovers(turns):
    """按代码语义模拟 2 次 rollover；返回块 rows/稼接信息（仅内存，不写 DB）。"""
    rows, blocks, next_id = [], [], 1
    base_rows = load_rows()
    rows.extend(base_rows)
    for t in base_rows:
        next_id = max(next_id, t["id"] + 1)
    # 现有库里的 base 记忆（阿泽/车牌等）
    remaining = list(turns)
    archive_count = turn_count = summary_count = cap_dropped = 0
    sim_log = []
    for round_no in (1, 2):
        if len(remaining) < 3:
            break
        chars = [len(t["q"]) + len(t["a"]) for t in remaining]
        total = sum(chars) or 1
        acc, best_err, best_n = 0, abs(DROP_FRACTION), 0
        for i in range(len(remaining) - 1):
            acc += chars[i]
            err = abs(acc / float(total) - DROP_FRACTION)
            if err < best_err:
                best_err, best_n = err, i + 1
        n_drop = max(1, min(best_n, len(remaining) - 2))
        while n_drop > 1:
            kept = total - sum(chars[:n_drop])
            if kept / float(total) >= 0.60:
                break
            n_drop -= 1
        dropped, remaining = remaining[:n_drop], remaining[n_drop:]
        ts = "2026-10-28 14:%02d" % (round_no * 10)
        date_tag = "2026-10-28"
        # auto_turn 逐轮块（受 LIBRARY_MAX 限制：已有 + 新建 <= 200）
        turn_ids = []
        for i, t in enumerate(dropped, start=1):
            if len(rows) >= LIBRARY_MAX:
                cap_dropped += 1
                continue
            text = ("用户：%s\n助手：%s" % (t["q"], t["a"]))[:MAX_TEXT_CHARS]
            rid = next_id
            next_id += 1
            rows.append({"id": rid, "text": text, "first_line": text.splitlines()[0],
                         "tags": ["auto_turn", date_tag], "source": "auto_turn",
                         "related_ids": [], "slots": M.extract_slots(text),
                         "n_tokens": max(1, len(text) // 2), "name": "auto-turn-%d" % rid})
            turn_ids.append(rid)
            turn_count += 1
        # archive 聚合块
        archive_text = ("对话归档 %s（原文）：\n%s" % (ts, "\n".join(
            "用户：%s\n助手：%s" % (t["q"], t["a"]) for t in dropped)))[:ARCHIVE_MAX_CHARS + 64]
        archive_id = None
        if len(rows) < LIBRARY_MAX:
            archive_id = next_id
            next_id += 1
            rows.append({"id": archive_id, "text": archive_text,
                         "first_line": archive_text.splitlines()[0],
                         "tags": ["auto_archive", date_tag], "source": "auto_archive",
                         "related_ids": [], "slots": M.extract_slots(archive_text),
                         "n_tokens": max(1, len(archive_text) // 2),
                         "name": "auto-archive-%d" % archive_id})
            archive_count += 1
        # summary 索引块（模拟模型摘要不含具体事实的最坏情况）
        summary_text = ("自动摘要 %s：用户聊了近期工作安排、出行计划和一些个人生活情况，"
                        "细节已按原文归档保存。" % ts)
        summary_id = None
        if len(rows) < LIBRARY_MAX:
            summary_id = next_id
            next_id += 1
            related = list(turn_ids) + ([archive_id] if archive_id else [])
            rows.append({"id": summary_id, "text": summary_text,
                         "first_line": summary_text,
                         "tags": ["auto_summary", date_tag], "source": "auto_summary",
                         "related_ids": related, "slots": M.extract_slots(summary_text),
                         "n_tokens": max(1, len(summary_text) // 2),
                         "name": "auto-summary-%d" % summary_id})
            summary_count += 1
            for sid in related:
                for r in rows:
                    if r["id"] == sid:
                        r["related_ids"] = list(set(r["related_ids"] + [summary_id]))
        # 块集内同一摘要的索引
        sim_log.append({"round": round_no, "dropped_turns": len(dropped),
                        "turn_blocks": turn_count, "archive": archive_id,
                        "summary": summary_id, "cap_dropped": cap_dropped,
                        "kept_turns": len(remaining), "arch_chars": len(archive_text)})
    return rows, sim_log, {"turn_blocks": turn_count, "archives": archive_count,
                           "summaries": summary_count, "cap_dropped": cap_dropped}


def meta_fn_for(rows):
    by_id = {r["id"]: r for r in rows}

    def meta(sid):
        r = by_id.get(int(sid))
        if not r:
            return {}
        return {"tags": r.get("tags") or [], "source": r.get("source"),
                "related_ids": r.get("related_ids") or [],
                "slots": r.get("slots") or {}}
    return meta


def slots_of(rows, sid):
    for r in rows:
        if r["id"] == int(sid):
            return r.get("slots") or M.extract_slots(r["text"])
    return {}


def emulate_select(rows, q, topk=4, meta_fn=None):
    """复刻 chat_daily._retrieval_select 的槽位叠加（time 硬过滤/加权/同时间最新/1 跳）。"""
    qs = M.query_slots(q)
    structured = bool(qs.get("structured"))
    cand = topk * 3 if structured else topk
    base, stats = M.retrieve(q, rows, topk=cand, meta_fn=meta_fn, return_stats=True)
    scored = []
    dropped_by_slot = []
    for b in base:
        sid = int(b["id"])
        sl = slots_of(rows, sid)
        if not M.slot_match(qs, sl):
            dropped_by_slot.append(sid)
            continue
        scored.append((M.slot_bonus(qs, sl), float(b["score"]), sid, b["text"], sl))
    scored.sort(key=lambda x: (-x[0], -x[1], -x[2] if structured else x[2]))
    picked = scored[:topk]
    picked_ids = [x[2] for x in picked]
    # 1 跳扩展（related_ids / 同标签）
    by_id = {r["id"]: r for r in rows}
    for _, _, sid, _, _ in list(picked):
        r = by_id.get(sid, {})
        for rid in (r.get("related_ids") or []):
            if rid in by_id and rid not in picked_ids:
                picked_ids.append(rid)
    texts = [by_id[i]["text"] for i in picked_ids if i in by_id]
    return {"query": q, "qslots": qs, "candidates": stats.get("candidates"),
            "gate": stats.get("gate"), "base_n": len(base),
            "dropped_by_slot": dropped_by_slot, "picked_ids": picked_ids,
            "picked_texts": texts}


def main():
    rows_live = load_rows()
    evs = load_events()
    snap = snapshot(rows_live, evs)
    turns, planned_chars = build_planned_turns()
    sim_rows, sim_log, sim_counts = simulate_rollovers(turns)
    meta = meta_fn_for(sim_rows)
    # 用 rollover 后块集测事实检索（模拟）；同时测 live 库（当前无 auto 块）
    tests = []
    for _, tier, _, q, kw in FACTS:
        live = emulate_select(rows_live, q, 4, meta_fn_for(rows_live))
        sim = emulate_select(sim_rows, q, 4, meta)
        tests.append({"fact": kw, "tier": tier, "query": q,
                      "live_selected_ids": live["picked_ids"],
                      "live_found": any(kw in t for t in live["picked_texts"]),
                      "live_cand": live["candidates"],
                      "sim_selected_ids": sim["picked_ids"],
                      "sim_found": any(kw in t for t in sim["picked_texts"]),
                      "sim_qslots": sim["qslots"],
                      "sim_cand": sim["candidates"],
                      "sim_dropped_by_slot": sim["dropped_by_slot"]})
    for q, kw in EXTRA_Q:
        sim = emulate_select(sim_rows, q, 4, meta)
        tests.append({"fact": kw, "tier": "base", "query": q,
                      "live_selected_ids": emulate_select(rows_live, q)["picked_ids"],
                      "live_found": any(kw in t for t in emulate_select(rows_live, q)["picked_texts"]),
                      "sim_selected_ids": sim["picked_ids"],
                      "sim_found": any(kw in t for t in sim["picked_texts"]),
                      "sim_qslots": sim["qslots"], "sim_cand": sim["candidates"],
                      "sim_dropped_by_slot": sim["dropped_by_slot"]})
    # 事实块是否在 round1/2 的 auto 块里出现
    auto_texts = [(r["id"], r["mode"] if False else r.get("source"), r["text"])
                  for r in sim_rows if str(r.get("source") or "").startswith("auto_")]
    fact_presence = {}
    for _, _, _, _, kw in FACTS + [(0, 0, 0, 0, "阿泽")]:
        fact_presence[kw] = [rid for rid, src, txt in auto_texts if kw in txt]
    # 现场预判阈值：字符/ token 比例与达到阈值所需字符
    ratio = snap.get("token_per_char_obs") or 0.1
    need_chars = int(snap["threshold_tokens"] / max(1e-6, ratio))
    result = {
        "schema": "long_conv_memory_analysis_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "readonly_live_db_plus_forced_rollover_simulation",
        "A_live_snapshot": snap,
        "B_simulation": {
            "note": "按当前代码语义在内存构造 rollover 块（不写库）：逐轮 auto_turn + "
                    "3000 字 auto_archive + 摘要 auto_summary(related)，LIBRARY_MAX=200。",
            "planned_chars": planned_chars, "planned_turns": len(turns),
            "rollovers": sim_log, "blocks": sim_counts,
            "fact_presence_in_auto_blocks": fact_presence,
            "tests": tests,
        },
        "C_findings": [],
        "D_minimal_fixes": [],
    }
    f = result["C_findings"]
    if snap["auto_blocks"] == 0:
        f.append("live：当前库 auto_* 块=0、rollover 事件=0 ⇒ rollover 尚未触发/未落块；"
                 "“检索不到 auto 块”的首要原因是块不存在（不是检索丢块）。")
    f.append("live：会话 %d asks / %.0f 字符；最后 chat_tokens=%s，阈值 %d；观测 token/字符≈%s"
             % (snap["asks_all"], snap["chars_all"], snap["chat_tokens_last"],
                snap["threshold_tokens"], snap["token_per_char_obs"]))
    f.append("按观测比例，达到 rollover 阈值约需 %d 字符（>4万）⇒ 4万字符压测可能根本触发不了 "
             "rollover（当前比例已偏低）；需以实测 chat_tokens 为准。" % need_chars)
    wrong = [t for t in tests if not t["sim_found"]]
    f.append("模拟 rollover 后：%d/%d 事实可检索到；未命中=%s"
             % (len(tests) - len(wrong), len(tests),
                [t["fact"] for t in wrong] or "无"))
    slot_dropped = [t["fact"] for t in tests if t["sim_dropped_by_slot"]]
    if slot_dropped:
        f.append("槽位过滤会丢块的事实：%s（候选块存在但 slot_match 拒绝）"
                 % slot_dropped)
    cap = sim_counts["cap_dropped"]
    if cap:
        f.append("LIBRARY_MAX=200 触发：模拟中 %d 个 auto_turn 因库满未写入（长对话会丢原文块）。" % cap)
    if fact_presence:
        missing_blocks = [k for k, v in fact_presence.items() if not v]
        if missing_blocks:
            f.append("auto 块中找不到事实：%s（被 cap 丢弃/事实未入 dropped 段/摘要化丢失）"
                     % missing_blocks)
    fix = result["D_minimal_fixes"]
    fix.append("1) 先让 rollover 可触发：按实测 chat_tokens/字符比例校正阈值或压测字符量；"
               "隔离路径（seq6）不计入 seq0 时需把“当前轮 prompt tokens”计入 rollover 预算。")
    fix.append("2) LIBRARY_MAX 对 auto_turn 不友好：改为“按 3–5 轮合并成 1 个 auto_turn 块”"
               "或 auto_* 不计入 200 上限（mount 预算仍由 memory_budget 控）。")
    fix.append("3) 槽位补漏：REL_PERSON 增加 妻子/丈夫/父母/孩子 等；" 
               "“X叫Y”允许关系前缀（我妻子叫李娜）；slot_match 对 want=person 但槽位缺失时"
               "降级为关键词而不是硬丢。")
    fix.append("4) auto_archive 的 time 槽位取整段第一个时间会误导 time 硬过滤：归档块不写单一 "
               "time（或只对 auto_turn 做 time 硬过滤）；auto_summary 仅作索引，related 展开"
               "应绕过 time/slot 过滤。")
    fix.append("5) 长对话检索 topk 候选池：structured 时先按 time 预过滤 rows 再打分（现在先取"
               " topk*3 再过滤，正确块可能不在候选池）。")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(OUT) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, OUT)
    print(json.dumps({"out": str(OUT), "auto_blocks": snap["auto_blocks"],
                      "rollover_events": snap["rollover_events"],
                      "chat_tokens": snap["chat_tokens_last"],
                      "tests": [(t["fact"], t["sim_found"]) for t in tests],
                      "fixes": len(fix)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()