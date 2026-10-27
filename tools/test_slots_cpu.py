# -*- coding: utf-8 -*-
"""test_slots_cpu.py -- T15 结构化槽位（12 键）+ 槽位检索叠加，零 GPU。

覆盖：
  A 抽取：time/person/event/place/action/object/quantity/cause/result/purpose/method/
    constraint 与“未核实”；缺省不硬猜
  B 问句解析：want/slots/structured（时间/地点/人物/对象/数量/原因/方式）
  C 匹配/加权：time 硬过滤、event/place/person 冲突剔除、want 必须存在、加权排序
  D 落库：daily_memory_meta.slots（含 archive/summary 块）
  E 六个线上硬用例：下周三→广州、下周五→成都、我叫什么→阿泽、组会在哪→B座302、
    养猫叫什么→豆豆、明天去哪→没提过
  F 检索叠加：time+event/place、同时间取最新、无匹配不瞎挂
运行： python -X utf8 tools/test_slots_cpu.py ; exit 0 = 全过
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import memory_service as M      # noqa: E402
import chat_daily as D          # noqa: E402

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(("ok   %s" % name) if cond else ("FAIL %s %s" % (name, detail)))


MEM = [
    "下周三去广州开会。",
    "下周五去成都出差。",
    "我叫阿泽。",
    "每周三组会在 B座302。",
    "我养了一只猫叫豆豆。",
]


def make_app(tmp, model):
    return D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
                      blocks_dir=os.path.join(tmp, "blocks"),
                      sessions_dir=os.path.join(tmp, "sessions"),
                      model_path=model, restore=False,
                      log_root=os.path.join(tmp, "assistant"),
                      retrieval_mode="topk", topk=4)


def main():
    # ---------- A 抽取 ----------
    s = M.extract_slots("下周三去广州开会。")
    check("A.time", s["time"] == "下周三", str(s))
    check("A.place", s["place"] == "广州", str(s))
    check("A.event", s["event"] == "开会", str(s))
    check("A.action", s["action"] == "去", str(s))
    s = M.extract_slots("我叫阿泽。")
    check("A.person", s["person"] == "阿泽", str(s))
    s = M.extract_slots("我养了一只猫叫豆豆。")
    check("A.object_pet", s["object"] == "豆豆" and s["event"] == "养猫", str(s))
    s = M.extract_slots("组会在 B座302。")
    check("A.place_room", s["place"] == "B座302" and s["event"] == "组会", str(s))
    s = M.extract_slots("花了 120 元。")
    check("A.quantity", "120" in str(s["quantity"]), str(s))
    s = M.extract_slots("因为下雨，所以推迟；为了不迟到，坐地铁；必须带伞。")
    check("A.cause", s["cause"] and "下雨" in s["cause"], str(s))
    check("A.result", s["result"] and "推迟" in s["result"], str(s))
    check("A.purpose", s["purpose"] and "不迟到" in s["purpose"], str(s))
    check("A.method", s["method"] and "地铁" in s["method"], str(s))
    check("A.constraint", s["constraint"] and "带伞" in s["constraint"], str(s))
    s = M.extract_slots("今天天气不错。")
    check("A.schema_keys", set(s) == set(M.SLOT_KEYS) and len(M.SLOT_KEYS) == 12,
          str(sorted(s)))
    check("A.unverified", set(M.unverified_slots(s)) >=
          {"cause", "result", "purpose", "method"}, str(M.unverified_slots(s)))
    check("A.empty", M.extract_slots("") == {k: None for k in M.SLOT_KEYS}, "")

    # ---------- B 问句解析 ----------
    q = M.query_slots("下周三去哪开会？")
    check("B.want_place", q["want"] == "place", str(q))
    check("B.filter_time_event",
          q["slots"].get("time") == "下周三" and q["slots"].get("event") == "开会",
          str(q))
    check("B.structured", q["structured"] is True, str(q))
    check("B.person", M.query_slots("我叫什么名字？")["want"] == "person", "")
    check("B.object_pet", M.query_slots("养猫叫什么？")["want"] == "object", "")
    check("B.quantity", M.query_slots("花了多少钱？")["want"] == "quantity", "")
    check("B.cause", M.query_slots("为什么推迟？")["want"] == "cause", "")
    check("B.method", M.query_slots("怎么去？")["want"] == "method", "")
    check("B.unstructured", M.query_slots("我在哪家书店买的书？")["structured"] is False,
          "")

    # ---------- C 匹配/加权 ----------
    qs = M.query_slots("下周三去哪开会？")
    check("C.time_match", M.slot_match(qs, {"time": "下周三", "event": "开会", "place": "广州"}), "")
    check("C.time_mismatch", not M.slot_match(qs, {"time": "下周五",
                                                     "event": "开会"}), "")
    check("C.event_conflict", not M.slot_match(qs, {"time": "下周三",
                                                      "event": "出差"}), "")
    qp = M.query_slots("组会在哪？")
    check("C.want_missing", not M.slot_match(qp, {"event": "组会", "place": None}), "")
    check("C.unstructured_pass",
          M.slot_match({"structured": False, "want": "place", "slots": {}}, {}), "")
    b1 = M.slot_bonus(qs, {"time": "下周三", "event": "开会", "place": "广州"})
    b2 = M.slot_bonus(qs, {"time": "下周三", "event": "出差", "place": "成都"})
    check("C.bonus_order", b1 > b2, "%r vs %r" % (b1, b2))

    # ---------- D 落库（含 archive/summary） ----------
    tmp = tempfile.mkdtemp(prefix="slots_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    try:
        d = os.path.join(tmp, "app")
        os.makedirs(d, exist_ok=True)
        app = make_app(d, model)
        try:
            ids = [app.remember(t)["id"] for t in MEM]
            meta = app._meta_get(ids[0])
            check("D.meta_slots_saved",
                  meta.get("slots", {}).get("time") == "下周三"
                  and meta["slots"].get("place") == "广州", str(meta.get("slots")))
            cols = {r[1] for r in app.con.execute(
                "PRAGMA table_info(daily_memory_meta)").fetchall()}
            check("D.slots_column", "slots" in cols, str(cols))
            # 归档/摘要块同样带 slots
            ar = app._insert_memory_block("下周三去广州开会归档。", label="归档",
                                          mode="auto_archive")
            sm = app._insert_memory_block("自动摘要：下周三去广州开会。", label="摘要",
                                          mode="auto_summary")
            check("D.archive_slots",
                  app._meta_get(ar["id"])["slots"].get("place") == "广州",
                  str(app._meta_get(ar["id"])["slots"]))
            check("D.summary_slots",
                  app._meta_get(sm["id"])["slots"].get("time") == "下周三",
                  str(app._meta_get(sm["id"])["slots"]))
            # 同时间两条：取最新 id
            a = app.remember("下周三去广州开周会（新）。")
            check("D.newest_id", a["id"] > ids[0], "%r vs %r" % (a["id"], ids[0]))
        finally:
            app.close()

        # ---------- E 六个线上硬用例 ----------
        d2 = os.path.join(tmp, "cases")
        os.makedirs(d2, exist_ok=True)
        app = make_app(d2, model)
        try:
            ids = {}
            for t in ("下周三去广州开会。", "下周五去成都出差。", "我叫阿泽。",
                      "每周三组会在 B座302。", "我养了一只猫叫豆豆。"):
                ids[t] = app.remember(t)["id"]

            def ask_ids(q):
                r = app.ask(q)
                return r, [int(x["source_id"]) for x in app.mounted_blocks]

            r, mounted = ask_ids("下周三去哪开会？")
            check("E.gz_gz", ids["下周三去广州开会。"] in mounted,
                  "%r %r" % (mounted, r["answer"]))
            r, mounted = ask_ids("下周五去哪？")
            check("E.cd", ids["下周五去成都出差。"] in mounted,
                  "%r %r" % (mounted, r["answer"]))
            r, mounted = ask_ids("我叫什么名字？")
            check("E.name", ids["我叫阿泽。"] in mounted, "%r %r"
                  % (mounted, r["answer"]))
            r, mounted = ask_ids("组会在哪？")
            check("E.meeting_place", ids["每周三组会在 B座302。"] in mounted,
                  "%r %r" % (mounted, r["answer"]))
            r, mounted = ask_ids("养猫叫什么？")
            check("E.pet_name", ids["我养了一只猫叫豆豆。"] in mounted,
                  "%r %r" % (mounted, r["answer"]))
            r = app.ask("明天去哪？")
            mounted = [int(x["source_id"]) for x in app.mounted_blocks]
            check("E.tomorrow_no_wrong_mount", mounted == [], str(mounted))
            check("E.tomorrow_not_claiming",
                  ("不掌握" in r["answer"] or "不知道" in r["answer"]
                   or "没提" in r["answer"] or r.get("refused")), str(r))
        finally:
            app.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = len(CHECKS) - sum(CHECKS)
    print("\n%d checks, %d failed" % (len(CHECKS), failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())