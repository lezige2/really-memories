# -*- coding: utf-8 -*-
"""test_retrieval_fallback_cpu.py -- P0 检索词面 miss 兜底回归（零 GPU）。

真 DB fixture（StubEngine + install_fake_model）：
  - "我叫阿泽…"        => "我叫什么名字？" 必须命中并挂载
  - "每周三组会B座302" => "我的组会在哪开？" 必须命中并挂载
  - 库里没有车牌      => "我的车牌号是多少？" 不凭空挂载（fail-closed）
  - 非个人问句        => 不触发关键词兜底
  - 正常 bigram 已命中  => signals.fallback 不为 True（不影响原检索）

Run: python -X utf8 tools/test_retrieval_fallback_cpu.py ; exit 0 = pass.
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

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


FACTS = [
    "我叫阿泽，我的常用邮箱是 lin@example.com。",
    "我每周三晚上七点有组会，地点在 B 座 302。",
    "本周待办是交周报、周三体检、周五复盘。",
]


def main():
    tmp = tempfile.mkdtemp(prefix="fb_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    app = D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, retrieval_mode="topk", topk=4, logger=False)
    try:
        ids = {}
        for f in FACTS:
            app.remember(f)
        for r in app._rows():
            ids[str(r[3])] = int(r[0])

        # 1) 名字：bigram 检不到的短问句要走关键词兜底
        sel = app._retrieval_select("我叫什么名字？")
        check("name_fallback_selected", bool(sel), sel)
        check("name_is_name_memory",
              any("阿泽" in str(app._row_by_id(s["source_id"])[3]) for s in sel), sel)
        check("name_fallback_flag",
              any(s["signals"].get("fallback") for s in sel), sel)

        # 2) 组会：词面 miss -> 类型关键词 + 地点词
        sel = app._retrieval_select("我的组会在哪开？")
        check("group_fallback_selected", bool(sel), sel)
        check("group_is_group_memory",
              any("组会" in str(app._row_by_id(s["source_id"])[3]) for s in sel), sel)

        # 3) 库里没有车牌 => 不挂载（不能靠"我的"乱命中）
        sel = app._retrieval_select("我的车牌号是多少？")
        check("no_plate_no_fallback", sel == [], sel)

        # 4) 非个人问句不走关键词兜底
        check("general_not_fallback",
              not any(s["signals"].get("fallback")
                      for s in app._retrieval_select("今天天气怎么样？")), "")

        # 5) 正常 bigram 命中（车牌记忆存在时）不标记 fallback
        app.remember("我的车牌号是京A88888。")
        sel = app._retrieval_select("我的车牌号是多少？")
        plate_id = [int(r[0]) for r in app._rows() if "京A88888" in str(r[3])][0]
        check("normal_hit_present", plate_id in [s["source_id"] for s in sel], sel)
        check("normal_hit_not_fallback",
              all(not s["signals"].get("fallback") for s in sel
                  if s["source_id"] == plate_id), sel)

        # 6) 时间对齐：下周三问句不能挂下周四的记忆
        app.remember("我下周三要去上海出差。")
        app.remember("我下周四要去北京出差。")
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: "你下周三去上海出差。"
        res_t = app._ask_natural("我下周三去哪出差？", time.perf_counter())
        mounted_texts = [str(app._row_by_id(i)[3]) for i in (res_t.get("block_ids") or [])]
        check("time_overlap_mounts_same_weekday",
              mounted_texts and all("下周三" in t for t in mounted_texts), mounted_texts)
        check("time_overlap_excludes_next_thursday",
              all("下周四" not in t for t in mounted_texts), mounted_texts)

        # 6b) v4 新失败例：宠物名 / 工号 / 几点开会 / 明年一月 / 下周四
        app.remember("我养的猫叫豆豆。")
        app.remember("我的工号是 A12345。")
        app.remember("我明年一月要去拉萨出差。")
        app.remember("我下周四要去广州开会。")
        app.remember("我下下周一要去成都开会。")
        cases = [
            ("我养的猫叫什么名字？", "豆豆"),
            ("我的工号是多少？", "A12345"),
            ("在吗，我几点开会？", "组会"),
        ]
        for q, want in cases:
            sel = app._retrieval_select(q)
            ok = any(want in str(app._row_by_id(s["source_id"])[3]) for s in sel)
            check("v4_retrieval_%s" % want, ok,
                  [(s["source_id"], str(app._row_by_id(s["source_id"])[3])[:20]) for s in sel])

        app.eng.ask = lambda seq, text, n_predict=32, pos=None: "你明年一月去拉萨出差。"
        res_m = app._ask_natural("我明年一月要去哪出差？", time.perf_counter())
        mt = [str(app._row_by_id(i)[3]) for i in (res_m.get("block_ids") or [])]
        check("v4_time_year_month", mt and all("拉萨" in t for t in mt), mt)

        app.eng.ask = lambda seq, text, n_predict=32, pos=None: "你下周四去广州开会。"
        res_t2 = app._ask_natural("我下周四要去哪开会？", time.perf_counter())
        mt2 = [str(app._row_by_id(i)[3]) for i in (res_t2.get("block_ids") or [])]
        check("v4_time_next_thursday", mt2 and all("下周四" in t for t in mt2), mt2)
        check("v4_time_excludes_next_next_monday",
              all("下下周一" not in t for t in mt2), mt2)

        # 7) 端到端：自然模式 ask -> 真的挂载（block_ids 非空）
        app.eng.ask = lambda seq, text, n_predict=32, pos=None: "你叫阿泽。"
        res = app._ask_natural("我叫什么名字？", time.perf_counter())
        check("name_ask_mounted", bool(res.get("block_ids")), res.get("block_ids"))

        print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
        return 0 if not FAILS else 1
    finally:
        app.close()


if __name__ == "__main__":
    sys.exit(main())