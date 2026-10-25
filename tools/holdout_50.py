# -*- coding: utf-8 -*-
"""holdout_50.py -- SEALED. Written now, run later, once.

Why sealed: M1.5 changed retrieval behaviour. Any number produced before the code and the
thresholds are frozen describes a version that is about to be replaced, and the moment you
look at the misses you will want to tune -- which destroys the only unbiased measurement.

The seal enforces the discipline mechanically:

  * SEALED = False     # unsealed 2026-10-24 after the freeze record was written: the runner refuses to execute.
  * Unsealing requires --unseal AND an explicit freeze record (see FREEZE below).
  * Nothing here imports retrieval at module level, so importing this file cannot
    accidentally produce a number.

Run it exactly once, then never again. If it fails, analyse the failure, change the dev
set, and write a NEW 50-block set -- re-running this one after tuning makes it a dev set.

Composition (50 blocks / 50 queries), deliberately harder than the 30-set:

    20 paraphrase   reworded so the block's key term is absent or stated differently
    10 multi        two or three blocks, all required in top-3
    10 absent       incl. near-misses: a block exists that looks related but cannot answer
     5 chat_only    the fact is only in the dialogue; refusing would be wrong
     5 distractor   a near-duplicate block must not outrank the right one
"""

import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import analysis as A                                      # noqa: E402
import os
import sys
from datetime import datetime

SEALED = False    # unsealed 2026-10-24, after the freeze record

FREEZE = """
Before unsealing, all of these must already be true and recorded in STATUS-REPORT.md:

  [ ] retrieval.py / analysis.py / evidence.py unchanged since the freeze commit
  [ ] INDEX_VERSION and ANALYSIS_VERSION bumped to their final values
  [ ] GATE / COV_MIN / REL_CUT frozen (1.30 / 0.35 / 0.55)
  [ ] dev set (30 + 19) re-run and reported
  [ ] p0_2_check 22/22, red line HOLDS, chars_injected = 0
  [ ] nobody has seen this set's misses

Then:  python tools/holdout_50.py --unseal
"""

BLOCKS = [
    ("me", "本人", "我叫沈聿，工号 B-9032，在城市运力组。"),
    ("sister", "家人", "妹妹叫沈禾，在读研二，学的是建筑。"),
    ("mom", "母亲", "母亲姓顾，退休前是小学老师。"),
    ("home", "住处", "我住在西郊的梅园新村，6 号楼 402。"),
    ("landlord", "房东", "房东姓蒋，房租 5200 一个月，半年付一次。"),
    ("commute", "通勤", "先坐 2号线 到东直门，再换 13号线，全程 55分钟。"),
    ("bike", "单车", "通勤单程骑车 25分钟，车是 捷安特。"),
    ("car", "车", "车是 灰色 卡罗拉，车牌 京N-88F21。"),
    ("parking", "车位", "车位租的，在地下车库 C区 118 号。"),
    ("phone", "手机", "手机是 一加 12，两年一换。"),
    ("laptop", "电脑", "工作电脑是 MacBook Pro 14寸，内存 32G。"),
    ("desk", "工位", "工位在 5层 靠窗，桌上放了个 白瓷杯。"),
    ("sleep", "作息", "一般 1点 睡，早上 8点 起，中午补 20分钟。"),
    ("coffee", "咖啡", "每天两杯 手冲，豆子买 云南 的，不加奶。"),
    ("diet", "饮食", "不吃 内脏，牛肉 可以，海鲜 只吃 虾。"),
    ("allergy", "过敏", "对 青霉素 过敏，芒果 吃了会痒。"),
    ("sport", "运动", "每周二四 打 羽毛球，周六 游泳 1000米。"),
    ("gym", "健身", "健身房在 公司 负一层，年卡 2400。"),
    ("reading", "阅读", "在读 《万历十五年》，一天 15页。"),
    ("music", "音乐", "只听 古典，最喜欢 巴赫。"),
    ("podcast", "播客", "睡前听 《八分》，不听新闻。"),
    ("language", "语言", "在学 德语，A2，每周 两次 网课。"),
    ("study", "进修", "报了 一个 数据分析 的线上课，学费 6800。"),
    ("job", "工作", "在 运力组 做 调度算法，入职 三年。"),
    ("team", "团队", "组里 9个人，实习生 两个，前端 是 小赵。"),
    ("boss", "上级", "直属上级 是 韩工，周报 周五 交。"),
    ("meeting", "会议", "双周会 周四 下午 3点，5层 小会议室。"),
    ("review", "考核", "考核 一年 两次，上一次 是 A。"),
    ("salary", "薪资", "月薪 税前 28k，年终 看 绩效。"),
    ("bonus", "奖金", "项目奖 按 季度 发，最少 5000。"),
    ("bank", "银行", "工资卡 是 中信银行，信用卡 是 招行。"),
    ("loan", "贷款", "房贷 每月 9100，还剩 18年。"),
    ("invest", "理财", "定投 指数基金，每月 3000，风险 承受 中等。"),
    ("insure", "保险", "买了 重疾险，保额 50万，年缴 8600。"),
    ("medical", "就医", "常去 市二院，挂号 用 公众号。"),
    ("travel", "差旅", "出差 坐 飞机 经济舱，酒店 600 以内。"),
    ("visa", "签证", "有 申根签，2027年 到期。"),
    ("hobby", "爱好", "周末 拍照，用 富士 XT5。"),
    ("pet", "宠物", "养了 一只 橘猫，叫 团子，三岁。"),
    ("plant", "植物", "阳台上 养了 六盆 多肉，两周 浇一次。"),
    ("food", "常去", "常去 楼下 的 兰州拉面，加 一份 牛肉。"),
    ("friend", "朋友", "老朋友 叫 郑野，在 成都 做 游戏。"),
    ("college", "学校", "本科 在 哈工大，专业 是 自动化。"),
    ("city", "城市", "老家 在 洛阳，每年 回去 两次。"),
    ("parents", "父母", "父母 住在 洛阳，父亲 血压 高。"),
    ("holiday", "假期", "年假 15天，去年 去了 云南。"),
    ("plan", "计划", "明年 打算 考 一个 驾照 增驾。"),
    ("vendor", "供应商", "对接的 供应商 是 顺捷，账期 30天。"),
    ("sla", "服务", "接口 SLA 是 99.9%，超时 报警 到 群里。"),
    ("deadline", "节点", "Q4 的 交付 节点 是 12月20日。"),
]

# (query, gold, kind, transcript)
QUERIES = [
    ("我住哪", ["home"], "paraphrase", ""),
    ("我坐什么车上班", ["commute"], "paraphrase", ""),
    ("骑车要多久", ["bike"], "paraphrase", ""),
    ("我的车什么颜色", ["car"], "paraphrase", ""),
    ("车位在哪个区", ["parking"], "paraphrase", ""),
    ("我用什么手机", ["phone"], "paraphrase", ""),
    ("工作电脑多少内存", ["laptop"], "paraphrase", ""),
    ("我几点睡", ["sleep"], "paraphrase", ""),
    ("咖啡怎么喝", ["coffee"], "paraphrase", ""),
    ("我不能吃什么", ["diet"], "paraphrase", ""),
    ("我对什么药过敏", ["allergy"], "paraphrase", ""),
    ("我一周运动几次", ["sport"], "paraphrase", ""),
    ("健身房年卡多少", ["gym"], "paraphrase", ""),
    ("最近读什么书", ["reading"], "paraphrase", ""),
    ("我在学哪门语言", ["language", "language"], "paraphrase", ""),
    ("我上级是谁", ["boss"], "paraphrase", ""),
    ("会议几点开", ["meeting"], "paraphrase", ""),
    ("月薪多少", ["salary"], "paraphrase", ""),
    ("房贷每月还多少", ["loan"], "paraphrase", ""),
    ("我老家哪的", ["city"], "paraphrase", ""),

    ("我工号和住址", ["me", "home"], "multi", ""),
    ("妹妹学什么专业，母亲以前做什么", ["sister", "mom"], "multi", ""),
    ("房租多少，房贷多少", ["landlord", "loan"], "multi", ""),
    ("通勤多久，车位在哪", ["commute", "parking"], "multi", ""),
    ("我几点睡，咖啡怎么喝", ["sleep", "coffee"], "multi", ""),
    ("对什么过敏，不能吃什么", ["allergy", "diet"], "multi", ""),
    ("健身房在哪，年卡多少", ["gym"], "multi", ""),
    ("上级是谁，周报什么时候交", ["boss"], "multi", ""),
    ("房贷多少，保险保额多少", ["loan", "insure"], "multi", ""),
    ("供应商是谁，交付节点哪天", ["vendor", "deadline"], "multi", ""),

    ("我的护照号是多少", [], "absent", ""),
    ("我的社保号是多少", [], "absent", ""),
    ("我的银行卡号是多少", [], "absent", ""),
    ("我的身份证号是多少", [], "absent", ""),
    ("我孩子的生日是哪天", [], "absent", ""),          # near-miss: pets/parents exist
    ("我车的排量是多少", [], "absent", ""),            # near-miss: car block has no engine
    ("我年终奖具体多少", [], "absent", ""),            # near-miss: bonus has a floor, not a figure
    ("我公积金每月多少", [], "absent", ""),
    ("我血压多少", [], "absent", ""),                  # near-miss: parents' BP only
    ("我的工位编号是多少", [], "absent", ""),          # near-miss: desk has no number

    ("我的车牌号是多少", [], "chat_only", "用户：我的车牌号是 京N-88F21。"),
    ("我下个月去哪出差", [], "chat_only", "用户：我下个月去 西安 出差。"),
    ("我说过的那家面馆叫什么", [], "chat_only", "用户：楼下有一家 兰州拉面 很好吃。"),
    ("我借给郑野多少钱", [], "chat_only", "用户：我借给郑野 3000块。"),
    ("我下周几体检", [], "chat_only", "用户：我下周三 去 体检。"),

    ("团子是什么品种", ["pet"], "distractor", ""),     # vs plant/food near-dupes
    ("团子几岁了", ["pet"], "distractor", ""),
    ("我老家在哪", ["city"], "distractor", ""),        # vs parents (洛阳 also)
    ("我在哪上的本科", ["college"], "distractor", ""),
    ("顺捷的账期多久", ["vendor"], "distractor", ""),
]


def _digest():
    import hashlib
    out = {}
    for f in ("analysis.py", "retrieval.py", "evidence.py", "test_analysis.py"):
        out[f] = hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
    return out


def build(db):
    import sqlite3
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE memory_source (
        id INTEGER PRIMARY KEY, tenant TEXT NOT NULL DEFAULT 'default',
        scope TEXT NOT NULL DEFAULT 'private', mode TEXT NOT NULL DEFAULT 'chat',
        name TEXT NOT NULL, label TEXT NOT NULL, text TEXT NOT NULL,
        source_hash TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    for i, (name, label, text) in enumerate(BLOCKS, start=1):
        con.execute("INSERT INTO memory_source (id,name,label,text,source_hash,created_at)"
                    " VALUES (?,?,?,?,?,datetime('now'))",
                    (i, name, label, text, "h%d" % i))
    con.commit()
    import retrieval as R
    R.build_index(con, verbose=True)
    return con


def main(argv):
    if SEALED:
        print("SEALED -- do not run until the freeze record exists.")
        print(FREEZE)
        return 2

    import json
    import retrieval as R
    import evidence as E

    db = os.path.join(ROOT, "kvmem", "holdout50.db")
    con = build(db)
    try:
        rows = []
        for q, gold, kind, tr in QUERIES:
            sel = R.search(con, q, k=3)
            names = [s["name"] for s in sel]
            d = E.decide(q, sel, tr)
            if gold:
                ranks = [names.index(g) + 1 for g in gold if g in names]
                rec = {kk: len([g for g in gold if g in names[:kk]]) / len(gold)
                       for kk in (1, 3, 5)}
                mrr = 1.0 / min(ranks) if ranks else 0.0
                ok = rec[3] == 1.0
            else:
                rec = {1: 0.0, 3: 0.0, 5: 0.0}
                mrr = 0.0
                want = "no_evidence" if kind == "absent" else "chat_only"
                ok = (d["state"] == want)
            rows.append({"q": q, "kind": kind, "gold": gold, "got": names,
                         "scores": [round(s["score"], 2) for s in sel],
                         "rec": rec, "mrr": mrr, "ok": ok, "state": d["state"],
                         "intent": d["intent"], "refuse": d["refuse"]})
    finally:
        con.close()

    pos = [r for r in rows if r["gold"]]
    r1 = sum(r["rec"][1] for r in pos) / len(pos)
    r3 = sum(r["rec"][3] for r in pos) / len(pos)
    r5 = sum(r["rec"][5] for r in pos) / len(pos)
    mrr = sum(r["mrr"] for r in pos) / len(pos)
    multi = [r for r in rows if r["kind"] == "multi"]
    absent = [r for r in rows if r["kind"] == "absent"]
    chat = [r for r in rows if r["kind"] == "chat_only"]
    abstained = [r for r in rows if r["refuse"]]
    absent_ok = sum(1 for r in absent if r["refuse"])
    prec = (sum(1 for r in abstained if r["kind"] == "absent") / len(abstained)
            if abstained else 1.0)
    recall_ab = absent_ok / len(absent) if absent else 0.0
    chat_refused = sum(1 for r in chat if r["refuse"])
    chat_mounted = sum(1 for r in chat if r["state"] == "memory_hit")

    print("\nholdout 50/50   index v%d   analysis v%d" % (R.INDEX_VERSION, A.ANALYSIS_VERSION))
    print("digests: %s" % _digest())
    print("\nrecall@1 %.3f  recall@3 %.3f  recall@5 %.3f  MRR %.3f   (%d queries)"
          % (r1, r3, r5, mrr, len(pos)))
    print("multi: all required in top-3 %d/%d"
          % (sum(1 for r in multi if r["ok"]), len(multi)))
    print("absent: abstain recall %.3f (%d/%d)   abstain precision %.3f"
          % (recall_ab, absent_ok, len(absent), prec))
    print("chat_only: over-refused %d/%d   wrongly mounted %d/%d"
          % (chat_refused, len(chat), chat_mounted, len(chat)))

    bad = [r for r in rows if not r["ok"]]
    if bad:
        print("\nmisses:")
        for r in bad:
            print("  %-9s %-26s gold=%-18s got=%-22s state=%s"
                  % (r["kind"], r["q"][:26], ",".join(r["gold"]) or "-",
                     ",".join(r["got"]) or "(empty)", r["state"]))

    report = {"eval": "holdout-50", "ran_at": datetime.now().isoformat(timespec="seconds"),
              "index_version": R.INDEX_VERSION,
              "analysis_version": A.ANALYSIS_VERSION, "digests": _digest(),
              "blocks": len(BLOCKS), "queries": len(rows),
              "recall@1": round(r1, 4), "recall@3": round(r3, 4),
              "recall@5": round(r5, 4), "mrr": round(mrr, 4),
              "multi_all_in_top3": "%d/%d" % (sum(1 for r in multi if r["ok"]), len(multi)),
              "abstain_recall": round(recall_ab, 4),
              "abstain_precision": round(prec, 4),
              "chat_only_over_refused": "%d/%d" % (chat_refused, len(chat)),
              "chat_only_wrongly_mounted": "%d/%d" % (chat_mounted, len(chat)),
              "rows": rows}
    path = os.path.join(ROOT, "kvmem", "holdout50_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\nreport: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
