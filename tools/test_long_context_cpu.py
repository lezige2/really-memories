# -*- coding: utf-8 -*-
"""test_long_context_cpu.py -- 长上下文 rollover 配额/合并/召回回归（零 GPU）。

覆盖（对齐 b6-designer 长测 bug 清单）：
  - auto_turn 3–5 轮合并成 1 块（8 轮 => <=2 块），不把 LIBRARY_MAX 先占满
  - rollover 先写 archive + summary（cap 紧时二者仍在，turn 块让位）
  - archive/summary 文本不带时间戳（time 槽为 None，避免 time 硬过滤误杀）
  - 被 rollover 丢掉的早期事实仍能召回（archive/turn 块关键词命中）
  - 关系人称（妻子/丈夫/儿子/女儿…+叫/是+名字）抽出 person，问答可命中
  - 槽位过滤为空时回退纯关键词（空槽不丢正确块）

Run: python -X utf8 tools/test_long_context_cpu.py ; exit 0 = pass.
"""
import os
import sys
import tempfile
import time

os.environ["LLAMA_MEM_MODE"] = "natural"
os.environ["LLAMA_MEM_VERIFY"] = "0"

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D  # noqa: E402
import memory_service as memo  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


def make_app(tmp):
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    return D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, retrieval_mode="topk", topk=4,
        rollover_at=0.001, logger=False)


def seed_rollover_hist(app, n=10):
    app.history = [{"q": "第%d轮的问题" % i, "a": "第%d轮的回答" % i, "refused": False}
                   for i in range(1, n + 1)]
    app.history[0] = {"q": "我的护照号是 E1234567 吗", "a": "护照号 E1234567 记下了。",
                      "refused": False}
    app.eng.cells[0] = 300
    app.eng.posmax[0] = D.CHAT_START_DEFAULT + 299


def t_merge_and_quota(tmp):
    app = make_app(os.path.join(tmp, "a"))
    try:
        # 留出 cap 空间，验证合并与 archive/summary 先写
        app.remember("背景记忆 A。")
        seed_rollover_hist(app, 10)
        info = app._maybe_rollover()
        check("rollover_triggered", bool(info), str(info))
        modes = dict()
        for row in app.con.execute("SELECT mode, count(*) FROM memory_source GROUP BY mode"):
            modes[row[0]] = row[1]
        check("archive_written", modes.get("auto_archive", 0) >= 1, str(modes))
        check("summary_written", modes.get("auto_summary", 0) >= 1, str(modes))
        # 10 轮丢 ~35%（>=3），每 4 轮 1 块 => turn 块 <= 2
        check("turn_merged", modes.get("auto_turn", 0) <= 2, str(modes))
        check("turn_nonempty", modes.get("auto_turn", 0) >= 1, str(modes))
        # archive/summary 不带时间戳 -> time 槽 None
        aid = app.con.execute("SELECT id FROM memory_source WHERE mode='auto_archive' "
                              "ORDER BY id DESC LIMIT 1").fetchone()[0]
        check("archive_time_neutral", not app._slots_of(int(aid)).get("time"),
              app._slots_of(int(aid)))
        # 早期事实仍可召回：护照号（可能落在 archive 或 turn 块）
        sel = app._retrieval_select("我的护照号是多少")
        texts = [str(app._row_by_id(s["source_id"])[3]) for s in sel]
        check("early_fact_recallable", any("E1234567" in t for t in texts), texts)
    finally:
        app.close()


def t_cap_reserve(tmp):
    old = D.LIBRARY_MAX
    D.LIBRARY_MAX = 8
    app = None
    try:
        app = make_app(os.path.join(tmp, "b"))
        for i in range(6):
            app.remember("占用记忆 %d。" % i)
        seed_rollover_hist(app, 8)
        app._maybe_rollover()
        rows = len(app._rows())
        modes = dict((r[0], r[1]) for r in app.con.execute(
            "SELECT mode, count(*) FROM memory_source GROUP BY mode"))
        check("cap_respected", rows <= 8, "rows=%d" % rows)
        check("archive_before_turn", modes.get("auto_archive", 0) >= 1, str(modes))
        check("summary_before_turn", modes.get("auto_summary", 0) >= 1, str(modes))
    finally:
        D.LIBRARY_MAX = old
        if app is not None:
            app.close()


def t_relation_person(tmp):
    app = make_app(os.path.join(tmp, "c"))
    try:
        app.remember("我妻子叫小芳。")
        app.remember("我儿子叫王小明。")
        check("rel_person_slot",
              memo.extract_slots("我妻子叫小芳。").get("person") == "小芳",
              memo.extract_slots("我妻子叫小芳。"))
        sel = app._retrieval_select("我妻子叫什么名字")
        texts = [str(app._row_by_id(s["source_id"])[3]) for s in sel]
        check("rel_person_retrieval", any("小芳" in t for t in texts), texts)
        app.eng.ask = lambda *a, **k: "你妻子叫小芳。"
        r = app._ask_natural("我妻子叫什么名字", time.perf_counter())
        check("rel_person_mounted", bool(r.get("block_ids")), r.get("block_ids"))
    finally:
        app.close()


def t_slot_empty_keyword_fallback(tmp):
    app = make_app(os.path.join(tmp, "d"))
    try:
        app.remember("我每周三晚上七点有组会，地点在 B 座 302。")
        # 造一个"槽位抽到但 base 检索无命中"的问句：问句词面只在原文里
        sel = app._retrieval_keyword_fallback("我几点开会")
        check("keyword_fallback_nonempty", bool(sel), sel)
        sel2 = app._retrieval_select("我几点开会")
        check("retrieval_fallback_nonempty", bool(sel2), sel2)
    finally:
        app.close()


def t_io_budget(tmp):
    """Step1/2/3：rollover 期间索引只重建 1 次；archive 块 token 很小；/save 超限拒绝。"""
    import retrieval as R
    app = make_app(os.path.join(tmp, "e"))
    try:
        app.remember("背景 A。")
        seed_rollover_hist(app, 10)
        app._db_commit_count = 0
        calls = {"n": 0}
        orig = R.build_index
        def _count(*a, **k):
            calls["n"] += 1
            return orig(*a, **k)
        R.build_index = _count
        try:
            app._maybe_rollover()
        finally:
            R.build_index = orig
        check("index_rebuild_le_1", calls["n"] <= 1, calls["n"])
        check("batch_commit_le_1", app._db_commit_count <= 1, app._db_commit_count)
        row = app.con.execute(
            "SELECT s.text, b.n_tokens FROM memory_source s JOIN memory_block b "
            "ON b.source_id=s.id WHERE s.mode='auto_archive' ORDER BY s.id DESC LIMIT 1"
        ).fetchone()
        check("archive_source_has_original", row and "用户：" in row[0], row and row[0][:40])
        check("archive_block_tokens_small", row and int(row[1]) <= 512, row and row[1])
        # summary/turn 块 token 上限 + 单块 <15MB（按 104,448 B/token 估算）
        srow = app.con.execute(
            "SELECT b.n_tokens FROM memory_source s JOIN memory_block b "
            "ON b.source_id=s.id WHERE s.mode='auto_summary' ORDER BY s.id DESC LIMIT 1"
        ).fetchone()
        check("summary_block_tokens_small", srow and int(srow[0]) <= 256, srow and srow[0])
        mx = app.con.execute("SELECT max(n_tokens) FROM memory_block").fetchone()[0] or 0
        check("block_under_15mb", int(mx) * 104448 < 15 * 1024 * 1024, mx)
        check("block_cap_constant", D.BLOCK_MAX_CHARS == 140, D.BLOCK_MAX_CHARS)
        # /save >1GiB 守卫（伪造 bytes_per_token）
        app.eng.cells[0] = 2000
        app.eng.bytes_per_token = lambda: (1 << 20)
        try:
            app.save()
            check("save_too_large_refused", False, "no error")
        except D.DailyError as exc:
            check("save_too_large_refused", exc.code == "save_too_large", exc.code)
    finally:
        app.close()
        # 清理缓存索引影响


def t_rollover_no_sync_save(tmp):
    """real 引擎 rollover 不应同步保存会话 KV。"""
    app = make_app(os.path.join(tmp, "f"))
    try:
        app.eng.mode = "real"
        called = {"save": 0}
        def _boom(*a, **k):
            called["save"] += 1
            raise RuntimeError("sync save must not be called")
        app.save = _boom
        seed_rollover_hist(app, 8)
        app._maybe_rollover()
        check("rollover_skips_sync_save", called["save"] == 0, called)
    finally:
        app.close()


def main():
    tmp = tempfile.mkdtemp(prefix="longctx_")
    t_merge_and_quota(tmp)
    t_cap_reserve(tmp)
    t_relation_person(tmp)
    t_slot_empty_keyword_fallback(tmp)
    t_io_budget(tmp)
    t_rollover_no_sync_save(tmp)
    print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())