# -*- coding: utf-8 -*-
import os as _os_env
_os_env.environ.setdefault("LLAMA_MEM_MODE", "strict")  # 这些用例验证 strict 模式的既有契约
"""test_memory_graph_cpu.py -- 记忆库「存全文 + 标签 + 关联」零 GPU 测试。

覆盖 LEAD 要求 2：
  T1 打标签：/remember 文本 #tag1 #tag2 → tags 入库、正文不含标签尾巴
  T2 标签加权检索：标签命中即使正文不含该词也能选中
  T3 1 跳关联扩展：related_ids 指向的记忆会被一起挂载（related=True）
  T4 自动压缩：摘要只作索引（auto_summary），原文 auto_archive 全文块 + 归档文件，
     摘要 related_ids 指向归档；检索摘要时同时挂原文
  T5 相似两条：bigram 相近的两条都在 top-k 内并被挂载
  T6 预算截断：memory_budget 压小后按分数截断并记 truncated（不越预算）
  T7 /memories 字段：id/first_line/len/tags/source/related_ids
  T8 全文：记忆 text 是全文（非摘要）

运行： python -X utf8 tools/test_memory_graph_cpu.py ; exit 0 = 全过
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D          # noqa: E402

FAILS = []
CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(name)
    if not cond:
        FAILS.append("%s %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))
    else:
        print("ok   %s" % name)


class RecordingEngine(D.StubEngine):
    def __init__(self):
        super().__init__()
        self.ops = []
        self.attached = {}

    def repos_local(self, seq, delta, p0=0, p1=-1):
        if int(seq) in self.attached:
            self.ops.append(("REPOS_ON_ATTACHED", int(seq)))
            raise RuntimeError("M3 guard: repos_on_attached")
        return super().repos_local(seq, delta, p0, p1)

    def share(self, block_seq, dst_seq, lo, hi):
        self.ops.append(("attach", int(block_seq)))
        self.attached[int(block_seq)] = (int(lo), int(hi))
        return super().share(block_seq, dst_seq, lo, hi)

    def drop(self, dst_seq, lo, hi):
        self.ops.append(("detach", int(dst_seq)))
        if int(dst_seq) == 0:
            for seq, (l, h) in list(self.attached.items()):
                if int(l) == int(lo) and int(h) == int(hi):
                    del self.attached[seq]
        return super().drop(dst_seq, lo, hi)

    def ask(self, seq, text, n_predict=32, pos=None):
        self.ops.append(("ask",))
        return super().ask(seq, text, n_predict, pos)


def make_app(tmp, model, **kw):
    return D.DailyApp(RecordingEngine(), db_path=os.path.join(tmp, "daily.db"),
                      blocks_dir=os.path.join(tmp, "blocks"),
                      sessions_dir=os.path.join(tmp, "sessions"),
                      model_path=model, restore=False,
                      log_root=os.path.join(tmp, "assistant"),
                      retrieval_mode="topk", topk=4, **kw)


def events(tmp):
    out = []
    sdir = os.path.join(tmp, "assistant", "sessions")
    for fn in (os.listdir(sdir) if os.path.isdir(sdir) else []):
        for line in open(os.path.join(sdir, fn), encoding="utf-8"):
            out.append(json.loads(line))
    return out


def t_tags_and_memories(tmp, model):
    app = make_app(tmp, model)
    try:
        r = app.remember("我在云栖书店买了三本旧书，一共 120 元。#购物 #书单")
        check("T1.id", r["id"] >= 1, str(r))
        check("T1.tags", r["tags"] == ["购物", "书单"], str(r.get("tags")))
        row = app.con.execute("SELECT text FROM memory_source WHERE id=?", (r["id"],)).fetchone()
        check("T1.text_no_tags", "#购物" not in row[0] and "120 元" in row[0], row[0])
        mem = [m for m in app.memories() if m["id"] == r["id"]][0]
        for k in ("id", "first_line", "len", "tags", "source", "related_ids"):
            check("T7.memories_%s" % k, k in mem, sorted(mem.keys()))
        check("T7.tags_value", mem["tags"] == ["购物", "书单"], str(mem))
        check("T7.full_text", "120 元" in row[0] and len(row[0]) > 10, row[0][:60])
        # 标签加权：正文不含「购物」也能被选中
        app.remember("书架第二层放着《长夜难明》。", tags=[])
        sel = app._retrieval_select("购物")
        check("T2.tag_boost", any(s["source_id"] == r["id"] for s in sel), str(sel))
        hit = [s for s in sel if s["source_id"] == r["id"]][0]
        check("T2.tag_signal", hit["signals"]["tags"] == ["购物"] or
              "购物" in hit["signals"]["tags"], str(hit["signals"]))
    finally:
        app.close()


def t_related_expansion(tmp, model):
    app = make_app(tmp, model)
    try:
        a = app.remember("训练记录 A：周一练腿，负重 60 公斤。")
        b = app.remember("早餐吃鸡蛋，午餐吃米饭。")
        app._meta_set(a["id"], related_ids=[b["id"]])
        sel = app._retrieval_select("训练记录 A 负重")
        ids = [s["source_id"] for s in sel]
        check("T3.related_included", a["id"] in ids and b["id"] in ids, str(sel))
        rel = [s for s in sel if s["source_id"] == b["id"]][0]
        check("T3.related_flag", rel["signals"].get("related") is True, str(rel))
        r = app.ask("训练记录 A 负重多少？")
        check("T3.related_mounted", b["id"] in [x["source_id"] for x in app.mounted_blocks],
              str([x["source_id"] for x in app.mounted_blocks]))
        st = app.status()["retrieval"]
        check("T3.status_related", st["related"] >= 1 and st["candidates"] >= 1, str(st))
    finally:
        app.close()


def t_rollover_archive(tmp, model):
    app = make_app(tmp, model, rollover_at=0.001)
    try:
        app.remember("我从 2024 年开始记录每周复盘。")
        app.history = [{"q": "介绍一下长城的历史", "a": "长城很长，始建于春秋。", "refused": False},
                       {"q": "介绍一下黄河的历史", "a": "黄河是母亲河。", "refused": False},
                       {"q": "介绍一下故宫的历史", "a": "故宫是明清皇宫。", "refused": False},
                       {"q": "介绍一下颐和园", "a": "颐和园是皇家园林。", "refused": False},
                       {"q": "介绍一下西湖", "a": "西湖在杭州。", "refused": False}]
        app.eng.cells[0] = 300
        app.eng.posmax[0] = D.CHAT_START_DEFAULT + 299
        r = app.ask("介绍一下泰山的历史。")
        check("T4.notice", "上下文已自动压缩" in (r.get("notice") or ""), str(r.get("notice")))
        rows = app.con.execute("SELECT id, text, label FROM memory_source "
                               "WHERE mode='auto_summary'").fetchall()
        check("T4.summary_row", len(rows) == 1, str(rows))
        summ_id = rows[0][0] if rows else None
        arch = app.con.execute("SELECT id, text, label FROM memory_source "
                               "WHERE mode='auto_archive'").fetchall()
        check("T4.archive_row", len(arch) == 1, str(arch))
        arch_id = arch[0][0] if arch else None
        meta = app._meta_get(summ_id) if summ_id else {}
        rel = list(meta.get("related_ids") or [])
        check("T4.summary_related", arch_id in rel and len(rel) >= 2,
              "%r vs %r" % (rel, arch_id))
        turns = app.con.execute("SELECT id FROM memory_source WHERE mode='auto_turn' "
                                "ORDER BY id").fetchall()
        turn_ids = [int(r[0]) for r in turns]
        check("T4.turn_blocks", len(turn_ids) >= 1, str(turn_ids))
        check("T4.summary_related_has_turns", all(t in rel for t in turn_ids),
              "%r vs %r" % (rel, turn_ids))
        check("T4.bidi_turn_to_summary",
              all(app._meta_get(t)["related_ids"] == [summ_id] for t in turn_ids),
              str([app._meta_get(t) for t in turn_ids]))
        check("T4.archive_full_text", arch and "长城很长" in arch[0][1], str(arch)[:200])
        check("T4.archive_tags", (app._meta_get(arch_id)["tags"] or [])[:1] == ["auto_archive"],
              str(app._meta_get(arch_id)))
        adir = app._archive_dir()
        files = sorted(f for f in (os.listdir(adir) if os.path.isdir(adir) else [])
                       if f.endswith(".txt"))
        sidecars = sorted(f for f in (os.listdir(adir) if os.path.isdir(adir) else [])
                          if f.endswith(".meta.json"))
        check("T4.archive_file", len(files) == 1, str(files))
        check("T4.archive_sidecar", len(sidecars) == 1, str(sidecars))
        if files:
            content = open(os.path.join(adir, files[0]), encoding="utf-8").read()
            check("T4.archive_file_full", "长城很长" in content, content[:120])
        if sidecars:
            sc = json.load(open(os.path.join(adir, sidecars[0]), encoding="utf-8"))
            check("T4.sidecar_ids", sc.get("summary_id") == summ_id
                  and sc.get("archive_id") == arch_id
                  and len(sc.get("turn_ids") or []) >= 1, str(sc))
        # 检索命中摘要 => 原文块也被挂载（related 扩展）
        sel = app._retrieval_select("自动摘要")
        ids = [s["source_id"] for s in sel]
        check("T4.summary_hit", summ_id in ids, str(sel))
        check("T4.archive_linked", arch_id in ids, str(sel))
        r2 = app.ask("自动摘要里说了什么？")
        mounted = [x["source_id"] for x in app.mounted_blocks]
        check("T4.archive_mounted", arch_id in mounted, str(mounted))
        ev = [e for e in events(tmp) if e.get("event") == "context_rollover"]
        check("T4.log_event",
              any(e.get("archive_id") == arch_id for e in ev), str(ev)[:200])
        check("T4.no_bad_repos", not any(o[0] == "REPOS_ON_ATTACHED"
                                         for o in app.eng.ops))
    finally:
        app.close()


def t_similar_two(tmp, model):
    app = make_app(tmp, model)
    try:
        a = app.remember("项目代号是 X1，负责人老周，上线时间是 3 月 14 日。")
        b = app.remember("项目代号是 X1，负责人老周，上线时间是 4 月 20 日。")
        sel = app._retrieval_select("项目代号 X1 什么时候上线")
        ids = [s["source_id"] for s in sel]
        check("T5.both_selected", a["id"] in ids and b["id"] in ids, str(sel))
        r = app.ask("项目代号 X1 什么时候上线？")
        mounted = [x["source_id"] for x in app.mounted_blocks]
        check("T5.both_mounted", a["id"] in mounted and b["id"] in mounted, str(mounted))
        check("T5.instruction_disinstruct",
              "相似记忆" in D.ANSWER_INSTRUCTION, D.ANSWER_INSTRUCTION)
    finally:
        app.close()


def t_budget_truncation(tmp, model):
    app = make_app(tmp, model)
    try:
        ids = []
        for i in range(1, 7):
            ids.append(app.remember("预算测试 %d：关键词 BUDGET，正文填充内容 %d。"
                                    % (i, i))["id"])
        app.memory_budget = 20
        r = app.ask("关键词 BUDGET")
        total = sum(int(b["n_tokens"]) for b in app.mounted_blocks)
        check("T6.within_budget", total <= 60, "total=%d" % total)
        check("T6.truncated", r["retrieval"]["truncated"] is True, str(r["retrieval"]))
        check("T6.kept_subset", len(app.mounted_blocks) < 6,
              str(len(app.mounted_blocks)))
    finally:
        app.close()


def main():
    tmp = tempfile.mkdtemp(prefix="memgraph_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    try:
        for name in ("t1", "t3", "t4", "t5", "t6"):
            os.makedirs(os.path.join(tmp, name), exist_ok=True)
        t_tags_and_memories(os.path.join(tmp, "t1"), model)
        t_related_expansion(os.path.join(tmp, "t3"), model)
        t_rollover_archive(os.path.join(tmp, "t4"), model)
        t_similar_two(os.path.join(tmp, "t5"), model)
        t_budget_truncation(os.path.join(tmp, "t6"), model)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d checks, %d failed" % (len(CHECKS), len(FAILS)))
    if FAILS:
        print("FAILURES:")
        for f in FAILS:
            print(" - %s" % f)
        return 1
    print("ALL PASS (zero GPU / fake engine)")
    return 0


if __name__ == "__main__":
    sys.exit(main())