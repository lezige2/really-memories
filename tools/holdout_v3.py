# -*- coding: utf-8 -*-
"""holdout_v3.py -- M1.7 held-out set (property schema). SEALED, run ONCE.

Every query that names a property (颜色/额度/油耗/排量/面积/身高/生日/血压/卡号/车位号/
工位号/电话) must be answered only by a block that states that property about that scope.
The absent set is built from the exact failure mode M1.6 had: an entity is recorded, the
property is not.

50 blocks / 80 queries: 45 paraphrase (12 of them property questions), 15 multi,
10 absent, 5 chat_only, 5 distractor.
"""
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

SEALED = False    # unsealed after the freeze record
EVAL = "holdout-v3-m17"

BLOCKS = [
    ("me", "本人", "我叫何砚，工号 D-7714，在仓储部。"),
    ("wife", "家人", "妻子叫林霁，在银行做柜员。"),
    ("daughter", "孩子", "女儿叫何小禾，今年 5岁，读 中班。"),
    ("home", "住处", "住址 是 广陵路 12 号 2 单元 602，两室一厅。"),
    ("area", "面积", "房子面积 89 平，月供不多。"),
    ("rent2", "出租", "老家那套 出租，租金 2600。"),
    ("commute", "通勤", "坐 3号线 直达，单程 35分钟。"),
    ("car", "车", "车是 深灰色 的 速腾，车牌 浙B-3F19K。"),
    ("cartype", "车型", "速腾 是 1.4T，双离合。"),
    ("fueluse", "油耗", "实测油耗 6.8L/100km，市区 多一点。"),
    ("parking", "车位", "车位号 C-108，租的，月租 350。"),
    ("platecolor", "车牌色", "车牌是 蓝色 的。"),
    ("phone", "手机", "手机号 137 0731 5520。"),
    ("desk", "工位", "工位号 D-52，在 3层 东侧。"),
    ("salary", "工资", "工资 税前 19k，每月 8号 到账。"),
    ("bonus", "奖金", "年度奖金 大概 2万4，按考核发。"),
    ("loan", "房贷", "房贷 每月 7400，还剩 19年。"),
    ("credit", "信用卡", "信用卡额度 5万，常用 招行。"),
    ("bank", "银行", "工资卡 是 建行，尾号 3390。"),
    ("card", "卡号", "储蓄卡号 6217 0001 2233 4455 66。"),
    ("bp", "血压", "上个月体检 血压 135/88。"),
    ("height", "身高", "身高 176，比 大学 时 高 一点。"),
    ("weight", "体重", "体重 68 公斤。"),
    ("sleep", "作息", "通常 0点半 睡，8点 起。"),
    ("diet", "饮食", "不吃 香菜，辣的 能吃。"),
    ("allergy", "过敏", "对 芒果 过敏，起疹子。"),
    ("sport", "运动", "每周 两次 游泳，一次 5百米。"),
    ("read", "阅读", "在读《置身事内》，看了 一半。"),
    ("study", "进修", "报了 统计 网课，学费 3800。"),
    ("job", "工作", "入职 三年，管 两个 库区。"),
    ("team", "团队", "团队 9个人，副手 是 老赵。"),
    ("boss", "上级", "上级 是 秦主管，周会 周三 开。"),
    ("meeting", "会议", "部门周会 周三 10点，在 一号 会议室。"),
    ("review", "考核", "考核 一年 两次，上次 A。"),
    ("vendor", "供应商", "承运商 是 顺达，账期 45天。"),
    ("contract", "合同", "和顺达的合同 12月15日 到期。"),
    ("stock", "库存", "库存 周转 22天，准确率 99%。"),
    ("city", "老家", "老家 在 绍兴，清明 回去。"),
    ("parents", "父母", "父母 住 绍兴，母亲 血糖 偏高。"),
    ("brother", "弟弟", "弟弟 在 武汉 读 研二，学 材料。"),
    ("friend", "朋友", "朋友 叫 沈迟，开 一家 修车铺。"),
    ("holiday", "假期", "年假 8天，今年 打算 去 青海。"),
    ("plan", "计划", "明年 想 考 一个 证。"),
    ("shop", "修车铺", "沈迟的 修车铺 叫 顺意，在 环城路。"),
    ("noodle", "面馆", "常去 楼下 那家 面馆，一碗 22。"),
    ("hobby", "爱好", "喜欢 钓鱼，周末 去 河边。"),
    ("pet", "宠物", "养了 一只 橘猫，叫 年糕。"),
    ("laptop", "电脑", "笔记本 32G 内存，1T 硬盘。"),
    ("insurance", "保险", "意外险 保额 50万，年缴 600。"),
    ("boss2", "上级2", "秦主管 今年 调到 二部。"),
]

QUERIES = [
    # ---- property questions (the M1.7 target)
    ("我车牌什么颜色", ["platecolor"], "paraphrase", ""),
    ("信用卡额度多少", ["credit"], "paraphrase", ""),
    ("车油耗多少", ["fueluse"], "paraphrase", ""),
    ("车排量多大", ["cartype"], "paraphrase", ""),
    ("房子面积多大", ["area"], "paraphrase", ""),
    ("我身高多少", ["height"], "paraphrase", ""),
    ("我血压多少", ["bp"], "paraphrase", ""),
    ("我的卡号是多少", ["card"], "paraphrase", ""),
    ("车位号是多少", ["parking"], "paraphrase", ""),
    ("工位号是多少", ["desk"], "paraphrase", ""),
    ("我电话是多少", ["phone"], "paraphrase", ""),
    # ---- paraphrase
    ("我住哪", ["home"], "paraphrase", ""),
    ("坐几号线", ["commute"], "paraphrase", ""),
    ("我车牌是多少", ["car"], "paraphrase", ""),
    ("工资多少", ["salary"], "paraphrase", ""),
    ("年度奖金多少", ["bonus"], "paraphrase", ""),
    ("房贷每月还多少", ["loan"], "paraphrase", ""),
    ("工资卡是哪家", ["bank"], "paraphrase", ""),
    ("我几点睡", ["sleep"], "paraphrase", ""),
    ("我不能吃什么", ["diet"], "paraphrase", ""),
    ("我对什么过敏", ["allergy"], "paraphrase", ""),
    ("我一周运动几次", ["sport"], "paraphrase", ""),
    ("最近在读什么书", ["read"], "paraphrase", ""),
    ("学费多少", ["study"], "paraphrase", ""),
    ("我管几个库区", ["job"], "paraphrase", ""),
    ("团队几个人", ["team"], "paraphrase", ""),
    ("我上级是谁", ["boss"], "paraphrase", ""),
    ("周会几点", ["meeting"], "paraphrase", ""),
    ("上次考核什么等级", ["review"], "paraphrase", ""),
    ("账期多久", ["vendor"], "paraphrase", ""),
    ("合同什么时候到期", ["contract"], "paraphrase", ""),
    ("库存周转几天", ["stock"], "paraphrase", ""),
    ("我老家哪的", ["city"], "paraphrase", ""),
    ("我妈血糖怎么样", ["parents"], "paraphrase", ""),
    ("弟弟在哪读研", ["brother"], "paraphrase", ""),
    ("年假几天", ["holiday"], "paraphrase", ""),
    ("我明年打算干什么", ["plan"], "paraphrase", ""),
    ("常去那家面馆一碗多少", ["noodle"], "paraphrase", ""),
    ("我养了什么宠物", ["pet"], "paraphrase", ""),
    ("孩子几岁", ["daughter"], "paraphrase", ""),
    ("出租那套租金多少", ["rent2"], "paraphrase", ""),
    ("意外险保额多少", ["insurance"], "paraphrase", ""),
    ("笔记本内存多大", ["laptop"], "paraphrase", ""),
    ("我车什么颜色", ["car"], "paraphrase", ""),

    # ---- 15 multi
    ("我工号和工位号", ["me", "desk"], "multi", ""),
    ("车位号多少，月租多少", ["parking"], "multi", ""),
    ("身高多少，体重多少", ["height", "weight"], "multi", ""),
    ("血压多少，血糖多少", ["bp"], "multi", ""),
    ("工资多少，奖金多少", ["salary", "bonus"], "multi", ""),
    ("团队几个人，上级是谁", ["team", "boss"], "multi", ""),
    ("承运商是谁，账期多久", ["vendor"], "multi", ""),
    ("合同哪天到期，库存周转几天", ["contract", "stock"], "multi", ""),
    ("弟弟学什么，在哪读", ["brother"], "multi", ""),
    ("我几点睡，几点起", ["sleep"], "multi", ""),
    ("车牌多少，排量多大", ["car", "cartype"], "multi", ""),
    ("朋友叫什么，修车铺在哪", ["friend", "shop"], "multi", ""),
    ("保额多少，年缴多少", ["insurance"], "multi", ""),
    ("房子面积多大，房租多少", ["area", "rent2"], "multi", ""),
    ("我卡号多少，工资卡哪家", ["card", "bank"], "multi", ""),

    # ---- 10 absent: the entity is recorded, the property is not
    # no record at all -- nothing to mount, nothing to refuse wrongly
    ("我的护照号是多少", [], "absent", ""),
    ("我的公积金每月多少", [], "absent", ""),
    ("我的微信号是多少", [], "absent", ""),
    ("我的学号是多少", [], "absent", ""),
    ("我的邮编是多少", [], "absent", ""),
    ("我的会员号是多少", [], "absent", ""),
    # a gated property with no value anywhere (生日)
    ("我生日是哪天", [], "absent", ""),
    ("我女儿的生日", [], "absent", ""),
    ("我妈的生日", [], "absent", ""),
    # a gated property whose scope appears in no block: the fallback across scopes is gone
    ("我头发什么颜色", [], "absent", ""),

    # ---- 5 chat_only
    ("我车牌号是多少", [], "chat_only", "用户：我的车牌号是 浙B-9K77L。"),
    ("我下个月去哪出差", [], "chat_only", "用户：我下个月去 湖州 出差。"),
    ("我说的那家修车铺叫什么", [], "chat_only", "用户：沈迟那家修车铺叫 顺意。"),
    ("我借给沈迟多少钱", [], "chat_only", "用户：我借给沈迟 12000。"),
    ("我周三几点复查", [], "chat_only", "用户：我周三 上午 9点半 复查。"),

    # ---- 5 distractor: near-duplicates must not outrank the right block
    ("浙B-3F19K 是谁的车", ["car"], "distractor", ""),
    ("1.4T 的是哪台车", ["cartype"], "distractor", ""),
    ("尾号 3390 是哪张卡", ["bank"], "distractor", ""),
    ("89 平 那套月供多少", ["area"], "distractor", ""),
    ("顺意 是谁开的", ["shop"], "distractor", ""),
]


def _digest():
    import hashlib
    return {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
            for f in ("analysis.py", "retrieval.py", "evidence.py", "test_analysis.py")}


def build(db):
    import sqlite3
    import retrieval as R
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
                    (i, name, label, text, "w%d" % i))
    con.commit()
    R.build_index(con, verbose=True)
    return con


def main(argv):
    if SEALED:
        print("SEALED. Freeze the digests into STATUS-REPORT.md, then set SEALED = False.")
        print("digests: %s" % _digest())
        return 2

    import json
    import analysis as A
    import retrieval as R
    import evidence as E

    con = build(os.path.join(ROOT, "kvmem", "holdout_v3.db"))
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
                         "rec": rec, "mrr": mrr, "ok": ok, "state": d["state"],
                         "refuse": d["refuse"]})
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
    rec_ab = absent_ok / len(absent) if absent else 0.0

    print("\n%s  index v%d  analysis v%d" % (EVAL, R.INDEX_VERSION, A.ANALYSIS_VERSION))
    print("digests: %s" % _digest())
    print("\nrecall@1 %.3f  recall@3 %.3f  recall@5 %.3f  MRR %.3f   (%d queries)"
          % (r1, r3, r5, mrr, len(pos)))
    print("multi: all required in top-3 %d/%d"
          % (sum(1 for r in multi if r["ok"]), len(multi)))
    print("absent: abstain recall %.3f (%d/%d)   abstain precision %.3f"
          % (rec_ab, absent_ok, len(absent), prec))
    print("chat_only: over-refused %d/%d   wrongly mounted %d/%d"
          % (sum(1 for r in chat if r["refuse"]), len(chat),
             sum(1 for r in chat if r["state"] == "memory_hit"), len(chat)))

    bad = [r for r in rows if not r["ok"]]
    if bad:
        print("\nmisses:")
        for r in bad:
            print("  %-11s %-26s gold=%-14s got=%-18s state=%s"
                  % (r["kind"], r["q"][:26], ",".join(r["gold"]) or "-",
                     ",".join(r["got"]) or "(empty)", r["state"]))

    path = os.path.join(ROOT, "kvmem", "holdout_v3_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"eval": EVAL, "ran_at": datetime.now().isoformat(timespec="seconds"),
                   "index_version": R.INDEX_VERSION,
                   "analysis_version": A.ANALYSIS_VERSION, "digests": _digest(),
                   "blocks": len(BLOCKS), "queries": len(rows),
                   "recall@1": round(r1, 4), "recall@3": round(r3, 4),
                   "recall@5": round(r5, 4), "mrr": round(mrr, 4),
                   "multi_all_in_top3": "%d/%d" % (sum(1 for r in multi if r["ok"]),
                                                   len(multi)),
                   "abstain_recall": round(rec_ab, 4), "abstain_precision": round(prec, 4),
                   "chat_only_over_refused": "%d/%d"
                   % (sum(1 for r in chat if r["refuse"]), len(chat)),
                   "rows": rows}, f, ensure_ascii=False, indent=1)
    print("\nreport: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))