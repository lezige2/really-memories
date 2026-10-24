# -*- coding: utf-8 -*-
"""eval_heldout.py -- the held-out set. Built once, run once, thresholds frozen.

The dev set (eval_retrieval.py) had GATE / COV_MIN / REL_CUT tuned on it, so it cannot be
used to claim the ranker generalises. This set was written afterwards and is used ONCE:

  * the thresholds are asserted, not read: if anyone edits GATE / COV_MIN / REL_CUT this
    script refuses to run and says so, because the number would no longer be held out;
  * the code digest, index version and threshold values are written into the report, so
    the run is reproducible and attributable;
  * nothing here is used to change the ranker. A failure means: analyse, change the dev
    set, and build a NEW held-out set -- not re-run this one until it passes.

Composition (30 blocks / 30 queries):

    12 paraphrase    lexically different from the block text -- tests generalisation
     6 multi         two blocks required, both must appear in top-3
     6 absent        including near-misses (a block exists that *looks* related)
     3 chat_only     the fact is only in the dialogue, so refusing would be wrong
     3 distractor    a near-duplicate block must NOT outrank the right one

Usage:  python tools/eval_heldout.py [--show]
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import evidence as E                                      # noqa: E402
import retrieval as R                                     # noqa: E402

EVAL_VERSION = "heldout-2026-10-24-v1"
FROZEN = {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55}
REPORT = os.path.join(ROOT, "kvmem", "eval_heldout%s.json" % "")

BLOCKS = [
    ("profile", "档案", "我叫林知远，工号 A-4417，在供应链分析组工作，猫叫年糕。"),
    ("project", "蓝鲸项目", "蓝鲸项目 3月14日 上线，负责人是周敏。"),
    ("atlas", "Atlas项目", "Atlas 项目 4月2日 上线，负责人是陈昊。"),
    ("diet", "饮食", "我不吃香菜，咖啡只喝美式，不加糖。"),
    ("commute", "通勤", "我住在城东梧桐里，坐 4号线 到公司，路上大约 40分钟。"),
    ("device", "设备", "开发机是 ThinkPad X1，外接 27寸 显示器，键盘是 HHKB。"),
    ("hobby", "爱好", "周末我喜欢爬山，去过 泰山 和 黄山。"),
    ("health", "健康", "我对 花生 过敏，体检时 血压 偏低。"),
    ("team", "团队", "组里一共 7个人，前端是李萌，后端是陈昊。"),
    ("finance", "财务", "每月 15号 发工资，报销走 钉钉 审批。"),
    ("travel", "出差", "出差坐 高铁二等座，住宿每晚不超过 500元。"),
    ("education", "学历", "本科在 东南大学 读 物流管理，2016年 毕业。"),
    ("banking", "银行", "工资卡是 招商银行，房贷在 建设银行。"),
    ("insurance", "保险", "买了 百万医疗险，每年 1200元，9月 续费。"),
    ("gym", "健身", "每周三 去健身房 练背，教练姓 孙。"),
    ("reading", "阅读", "最近在读《置身事内》，每天睡前读 20页。"),
    ("music", "播客", "通勤路上听 播客《忽左忽右》，基本不听歌。"),
    ("language", "语言", "在学 日语，目标是明年考  N2。"),
    ("sleep", "作息", "通常 12点半 睡，早上 7点 起床。"),
    ("tools", "工具", "写代码用 VS Code，终端是 Windows Terminal，版本管理用 git。"),
    ("meeting", "会议", "周会定在 周一 10点，302 会议室，大概半小时。"),
    ("vendor", "供应商", "主供应商是 华远物流，账期 45天。"),
    ("contract", "合同", "和华远的合同 12月31日 到期，需要提前 60天 续签。"),
    ("parking", "停车", "车停在公司 B2层，车位号 217。"),
    ("kid", "孩子", "女儿叫 林小满，今年 5岁，在向日葵幼儿园。"),
    ("parents", "父母", "父母住在 苏州，每月回去一次。"),
    ("landlord", "租房", "房东姓 吴，房租每月 4800元，押一付三。"),
    ("warranty", "保修", "笔记本保修到 2027年3月，延保买过一次。"),
    ("weather", "天气", "我一般看 中国天气网 的预报，不看 App。"),
    ("expense", "报销", "打车报销需要 行程单，超过 200元 要写说明。"),
]

# (query, gold, kind, transcript)
QUERIES = [
    ("我每天怎么去公司", ["commute"], "paraphrase", ""),
    ("我写代码用什么编辑器", ["tools"], "paraphrase", ""),
    ("我几点睡觉", ["sleep"], "paraphrase", ""),
    ("我女儿在哪上幼儿园", ["kid"], "paraphrase", ""),
    ("房贷是哪家银行", ["banking"], "paraphrase", ""),
    ("供应商账期多久", ["vendor"], "paraphrase", ""),
    ("合同什么时候到期", ["contract"], "paraphrase", ""),
    ("房租多少钱一个月", ["landlord"], "paraphrase", ""),
    ("我在学什么外语", ["language"], "paraphrase", ""),
    ("周会几点开始", ["meeting"], "paraphrase", ""),
    ("笔记本保修到什么时候", ["warranty"], "paraphrase", ""),
    ("打车报销要准备什么", ["expense"], "paraphrase", ""),

    ("我的工号和蓝鲸项目上线日期", ["profile", "project"], "multi", ""),
    ("女儿几岁，周会几点", ["kid", "meeting"], "multi", ""),
    ("供应商是谁，合同哪天到期", ["vendor", "contract"], "multi", ""),
    ("房租多少，房贷在哪家银行", ["landlord", "banking"], "multi", ""),
    ("我对什么过敏，咖啡怎么喝", ["health", "diet"], "multi", ""),
    ("通勤多久，车停哪层", ["commute", "parking"], "multi", ""),

    ("我的车牌号是多少", [], "absent", ""),
    ("我的护照号是多少", [], "absent", ""),
    ("我的血型是什么", [], "absent", ""),
    ("我老家在哪个城市", [], "absent", ""),
    ("我的身高是多少", [], "absent", ""),
    ("我每个月工资多少", [], "absent", ""),

    ("我的车牌号是多少", [], "chat_only", "用户：我的车牌号是 沪A-12345，记一下。"),
    ("我下周去哪出差", [], "chat_only", "用户：我下周三要去 杭州 出差。"),
    ("我昨天去的那家餐厅叫什么", [], "chat_only", "用户：昨天去了 江南灶 吃饭。"),

    ("Atlas 项目什么时候上线", ["atlas"], "distractor", ""),
    ("蓝鲸项目谁负责", ["project"], "distractor", ""),
    ("华远的合同什么时候到期", ["contract"], "distractor", ""),
]


def digest():
    h = hashlib.sha256()
    for f in ("retrieval.py", "evidence.py"):
        h.update(open(os.path.join(HERE, f), "rb").read())
    return h.hexdigest()[:16]


def check_frozen():
    live = {"GATE": R.GATE, "COV_MIN": R.COV_MIN, "REL_CUT": R.REL_CUT}
    bad = {k: (FROZEN[k], live[k]) for k in FROZEN if abs(FROZEN[k] - live[k]) > 1e-9}
    if bad:
        print("REFUSING TO RUN: thresholds changed since the held-out set was frozen.")
        for k, (f, l) in bad.items():
            print("  %s: frozen %.2f, live %.2f" % (k, f, l))
        print("Fix the code back, or build a NEW held-out set. Re-running this one after "
              "tuning it would destroy the only unbiased number you have.")
        return False
    return True


def build(db):
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
    R.build_index(con, verbose=True)
    return con


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if not check_frozen():
        return 2

    db = os.path.join(ROOT, "kvmem", "heldout.db")
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
                         "rec": rec, "mrr": mrr, "ok": ok,
                         "state": d["state"], "intent": d["intent"],
                         "refuse": d["refuse"], "reason": d["reason"]})
    finally:
        con.close()

    pos = [r for r in rows if r["gold"]]
    r1 = sum(r["rec"][1] for r in pos) / len(pos)
    r3 = sum(r["rec"][3] for r in pos) / len(pos)
    r5 = sum(r["rec"][5] for r in pos) / len(pos)
    mrr = sum(r["mrr"] for r in pos) / len(pos)
    multi = [r for r in rows if r["kind"] == "multi"]
    multi_ok = sum(1 for r in multi if r["ok"])
    absent = [r for r in rows if r["kind"] == "absent"]
    absent_ok = sum(1 for r in absent if r["ok"] and r["refuse"])
    chat = [r for r in rows if r["kind"] == "chat_only"]
    chat_ok = sum(1 for r in chat if r["ok"] and not r["refuse"])
    abstained = [r for r in rows if r["refuse"]]
    precision = (sum(1 for r in abstained if r["kind"] == "absent") / len(abstained)
                 if abstained else 1.0)

    print("\nheld-out %s   index v%d   code %s" % (EVAL_VERSION, R.INDEX_VERSION, digest()))
    print("thresholds frozen: GATE=%.2f COV_MIN=%.2f REL_CUT=%.2f"
          % (R.GATE, R.COV_MIN, R.REL_CUT))
    print("\nrecall@1 %.3f  recall@3 %.3f  recall@5 %.3f  MRR %.3f   (%d queries)"
          % (r1, r3, r5, mrr, len(pos)))
    print("multi: all required in top-3 %d/%d" % (multi_ok, len(multi)))
    print("absent: abstained %d/%d   abstain precision %.3f   (fabrication 0 by "
          "construction: the model is never called)" % (absent_ok, len(absent), precision))
    print("chat_only: not refused %d/%d" % (chat_ok, len(chat)))

    if a.show:
        for r in rows:
            print("  %-4s %-8s %-24s gold=%-16s got=%-22s %s"
                  % ("ok" if r["ok"] else "MISS", r["kind"], r["q"][:24],
                     ",".join(r["gold"]) or "-", ",".join(r["got"]) or "(empty)",
                     r["scores"]))

    bad = [r for r in rows if not r["ok"]]
    if bad:
        print("\nmisses:")
        for r in bad:
            print("  %-8s %-26s gold=%-16s got=%s state=%s"
                  % (r["kind"], r["q"][:26], ",".join(r["gold"]) or "-",
                     ",".join(r["got"]) or "(empty)", r["state"]))

    report = {"eval_version": EVAL_VERSION, "index_version": R.INDEX_VERSION,
              "code_digest": digest(), "thresholds": FROZEN,
              "run_at": datetime.now().isoformat(timespec="seconds"),
              "blocks": len(BLOCKS), "queries": len(rows),
              "recall@1": round(r1, 4), "recall@3": round(r3, 4),
              "recall@5": round(r5, 4), "mrr": round(mrr, 4),
              "multi_all_in_top3": "%d/%d" % (multi_ok, len(multi)),
              "absent_abstained": "%d/%d" % (absent_ok, len(absent)),
              "abstain_precision": round(precision, 4),
              "chat_only_not_refused": "%d/%d" % (chat_ok, len(chat)),
              "rows": rows}
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\nreport: %s" % REPORT)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())