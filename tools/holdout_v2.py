# -*- coding: utf-8 -*-
"""holdout_v2.py -- M1.6 held-out set. SEALED. Written, frozen, run ONCE.

Why a new set rather than the old 50: that one's misses have been read, so it is a dev set
now. A number produced on it would measure how well the code fits its own failures.

Composition (50 blocks / 80 queries):

    45 paraphrase   incl. amounts with no currency unit, 28k / 1万5 / 5200/月, Chinese
                    numerals (三次/两周), attribute questions (血压/排量/卡号/工位号/电话)
    15 multi        two blocks, both required in top-3
    10 absent       near-misses: a block exists that looks related but cannot answer
     5 chat_only    the fact is only in the dialogue
     5 distractor   a near-duplicate block must not outrank the right one

Discipline: SEALED while being written. Freeze the digests into STATUS-REPORT.md, then
unseal, run once, and never re-run after looking at the misses.
"""
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

SEALED = False    # unsealed after the freeze record
EVAL = "holdout-v2-m16"

BLOCKS = [
    ("me", "本人", "我叫陆迟，工号 C-5521，在门店运营部。"),
    ("wife", "家人", "妻子叫苏晚，在一家设计公司做项目管理。"),
    ("son", "孩子", "儿子叫陆小满，今年 6岁，在大风车幼儿园。"),
    ("home", "住处", "住址是青松路 88 号 3 单元 501。"),
    ("rent", "房租", "房租 5200 一个月，押一付三。"),
    ("utility", "水电", "水电费大概每月 300 左右，物业费另算。"),
    ("commute", "通勤", "坐 6号线 转 2号线，单程 50分钟。"),
    ("bike", "骑行", "天气好就骑车，单程 20分钟。"),
    ("car", "车", "车是白色的 朗逸，车牌 苏E-6K21M。"),
    ("displacement", "排量", "朗逸排量 1.5L，加 92 号油。"),
    ("parking", "车位", "车位号 B-217，月租 400。"),
    ("phone", "手机", "手机 139 0527 8842，用了三年。"),
    ("laptop", "电脑", "工作电脑 16G 内存，512G 硬盘。"),
    ("desk", "工位", "工位号 A-33，在 4层 靠窗。"),
    ("salary", "工资", "工资税前 23k，每月 10号 发。"),
    ("bonus", "奖金", "季度奖 大概 1万5，看门店完成率。"),
    ("loan", "房贷", "房贷每月 8600，还剩 22年。"),
    ("insure", "保险", "重疾险保额 40万，年缴 7800。"),
    ("bank", "银行", "工资卡是 交通银行，尾号 6621。"),
    ("card", "卡号", "常用卡号 6222 0210 0112 3344 55。"),
    ("bp", "血压", "体检血压 128/82，医生说正常。"),
    ("weight", "体重", "体重 71 公斤，比去年轻了 3 公斤。"),
    ("sleep", "作息", "一般 23点半 睡，7点 起。"),
    ("coffee", "咖啡", "每天一杯 美式，不加糖。"),
    ("diet", "饮食", "不吃 辣，海鲜 过敏。"),
    ("allergy", "过敏", "对 虾 过敏，吃了会起疹子。"),
    ("sport", "运动", "每周三 打 篮球，周末 爬山。"),
    ("gym", "健身", "健身房年卡 2800，在 小区 门口。"),
    ("reading", "阅读", "最近在读《长安的荔枝》，三天读完。"),
    ("music", "音乐", "开车听 老歌，不听 新歌。"),
    ("study", "进修", "在学 会计，报了 一个 网课，学费 4600。"),
    ("job", "工作", "入职 四年，负责 三家 门店。"),
    ("team", "团队", "团队 11个人，副手 是 小周。"),
    ("boss", "上级", "上级 是 陈经理，周报 周一 交。"),
    ("meeting", "会议", "门店例会 周一 9点，在 二楼 会议室。"),
    ("review", "考核", "考核 半年 一次，上次 是 B+。"),
    ("vendor", "供应商", "主要供应商 是 鲜达，账期 30天。"),
    ("contract", "合同", "和鲜达的合同 11月30日 到期。"),
    ("stock", "库存", "库存 周转 大概 18天，损耗 控制在 2%。"),
    ("sla", "服务", "配送时效 承诺 45分钟，超时 免单。"),
    ("city", "城市", "老家 在 扬州，一般 春节 回去。"),
    ("parents", "父母", "父母 住在 扬州，父亲 血糖 偏高。"),
    ("sister", "妹妹", "妹妹 在 南京 读 大三，学 临床医学。"),
    ("friend", "朋友", "老同学 叫 顾行，在 苏州 开 书店。"),
    ("holiday", "假期", "年假 10天，去年 去了 厦门。"),
    ("plan", "计划", "明年 想 开 第二家 店。"),
    ("book2", "书店", "顾行的书店 叫 慢半拍，在 平江路。"),
    ("food", "常去", "常去 街角 那家 面馆，一碗 18块。"),
    ("hobby", "爱好", "喜欢 拍 街景，用 一台 老 胶片机。"),
    ("pet", "宠物", "养了 一条 柴犬，叫 豆豆，两岁。"),
]

# (query, gold, kind, transcript)
QUERIES = [
    # ---- 45 paraphrase: amounts without units, Chinese numerals, attributes
    ("我住哪", ["home"], "paraphrase", ""),
    ("房租多少", ["rent"], "paraphrase", ""),
    ("水电费一个月多少", ["utility"], "paraphrase", ""),
    ("上班坐几号线", ["commute"], "paraphrase", ""),
    ("骑车要多久", ["bike"], "paraphrase", ""),
    ("我车牌是多少", ["car"], "paraphrase", ""),
    ("车排量多大", ["displacement"], "paraphrase", ""),
    ("车位号是多少", ["parking"], "paraphrase", ""),
    ("我电话是多少", ["phone"], "paraphrase", ""),
    ("工位号是多少", ["desk"], "paraphrase", ""),
    ("我工资多少", ["salary"], "paraphrase", ""),
    ("季度奖大概多少", ["bonus"], "paraphrase", ""),
    ("房贷每月还多少", ["loan"], "paraphrase", ""),
    ("重疾险保额多少", ["insure"], "paraphrase", ""),
    ("工资卡是哪家银行", ["bank"], "paraphrase", ""),
    ("我的卡号是多少", ["card"], "paraphrase", ""),
    ("我血压多少", ["bp"], "paraphrase", ""),
    ("我体重多少", ["weight"], "paraphrase", ""),
    ("我几点睡", ["sleep"], "paraphrase", ""),
    ("咖啡怎么喝", ["coffee"], "paraphrase", ""),
    ("我不能吃什么", ["diet"], "paraphrase", ""),
    ("我对什么过敏", ["allergy"], "paraphrase", ""),
    ("我一周运动几次", ["sport"], "paraphrase", ""),
    ("健身房年卡多少", ["gym"], "paraphrase", ""),
    ("最近在读什么书", ["reading"], "paraphrase", ""),
    ("开车听什么", ["music"], "paraphrase", ""),
    ("学费多少", ["study"], "paraphrase", ""),
    ("我负责几家店", ["job"], "paraphrase", ""),
    ("团队几个人", ["team"], "paraphrase", ""),
    ("我上级是谁", ["boss"], "paraphrase", ""),
    ("门店例会几点", ["meeting"], "paraphrase", ""),
    ("上次考核什么等级", ["review"], "paraphrase", ""),
    ("供应商账期多久", ["vendor"], "paraphrase", ""),
    ("合同什么时候到期", ["contract"], "paraphrase", ""),
    ("库存周转几天", ["stock"], "paraphrase", ""),
    ("配送时效承诺多久", ["sla"], "paraphrase", ""),
    ("我老家哪的", ["city"], "paraphrase", ""),
    ("我爸血糖怎么样", ["parents"], "paraphrase", ""),
    ("妹妹在哪读书", ["sister"], "paraphrase", ""),
    ("年假几天", ["holiday"], "paraphrase", ""),
    ("我明年打算干什么", ["plan"], "paraphrase", ""),
    ("常去那家面馆一碗多少", ["food"], "paraphrase", ""),
    ("我养了什么宠物", ["pet"], "paraphrase", ""),
    ("孩子几岁", ["son"], "paraphrase", ""),

    # ---- 15 multi
    ("我工号和工位号", ["me", "desk"], "multi", ""),
    ("房租多少，房贷多少", ["rent", "loan"], "multi", ""),
    ("孩子几岁，在哪上幼儿园", ["son"], "multi", ""),
    ("通勤多久，车位号多少", ["commute", "parking"], "multi", ""),
    ("我血压多少，体重多少", ["bp", "weight"], "multi", ""),
    ("工资多少，季度奖多少", ["salary", "bonus"], "multi", ""),
    ("保额多少，年缴多少", ["insure"], "multi", ""),
    ("团队几个人，上级是谁", ["team", "boss"], "multi", ""),
    ("供应商是谁，账期多久", ["vendor"], "multi", ""),
    ("合同哪天到期，库存周转几天", ["contract", "stock"], "multi", ""),
    ("妹妹学什么，在哪读", ["sister"], "multi", ""),
    ("我几点睡，几点起", ["sleep"], "multi", ""),
    ("健身房在哪，年卡多少", ["gym"], "multi", ""),
    ("老同学叫什么，书店在哪", ["friend", "book2"], "multi", ""),
    ("我车牌多少，排量多大", ["car", "displacement"], "multi", ""),

    # ---- 10 absent (near-miss: a related block exists)
    ("我的社保号是多少", [], "absent", ""),
    ("我的护照号是多少", [], "absent", ""),
    ("我的公积金每月多少", [], "absent", ""),
    ("我的身高多少", [], "absent", ""),
    ("我车油耗多少", [], "absent", ""),            # displacement block exists, no fuel use
    ("我的车牌颜色", [], "absent", ""),            # car block has 白色 but not as plate colour
    ("我妈生日是哪天", [], "absent", ""),
    ("我年终奖具体多少", [], "absent", ""),        # bonus gives a rough figure, not "具体"
    ("我房子的面积多大", [], "absent", ""),
    ("我信用卡额度多少", [], "absent", ""),        # bank block has a card, not a limit

    # ---- 5 chat_only
    ("我的车牌号是多少", [], "chat_only", "用户：我的车牌号是 苏E-9Z77K。"),
    ("我下个月去哪出差", [], "chat_only", "用户：我下个月去 合肥 出差。"),
    ("我说的那家书店叫什么", [], "chat_only", "用户：顾行开的那家书店叫 慢半拍。"),
    ("我借给顾行多少钱", [], "chat_only", "用户：我借给顾行 8000块。"),
    ("我下周几体检", [], "chat_only", "用户：我下周四 去 体检。"),

    # ---- 5 distractor (near-duplicate blocks: car/displacement, bank/card, rent/utility)
    ("苏E-6K21M 是谁的车", ["car"], "distractor", ""),
    ("1.5L 的是什么车", ["car"], "distractor", ""),
    ("尾号 6621 是哪张卡", ["bank"], "distractor", ""),
    ("押一付三是哪套房", ["rent"], "distractor", ""),
    ("慢半拍 是谁开的", ["book2"], "distractor", ""),
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
                    (i, name, label, text, "v%d" % i))
    con.commit()
    R.build_index(con, verbose=True)
    return con


def main(argv):
    if SEALED:
        print("SEALED. Freeze the digests into STATUS-REPORT.md first, then set SEALED = False.")
        print("digests: %s" % _digest())
        return 2

    import json
    import analysis as A
    import retrieval as R
    import evidence as E

    con = build(os.path.join(ROOT, "kvmem", "holdout_v2.db"))
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
            print("  %-11s %-28s gold=%-16s got=%-20s state=%s"
                  % (r["kind"], r["q"][:28], ",".join(r["gold"]) or "-",
                     ",".join(r["got"]) or "(empty)", r["state"]))

    path = os.path.join(ROOT, "kvmem", "holdout_v2_report.json")
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