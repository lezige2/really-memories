# -*- coding: utf-8 -*-
"""P1b 修正：多实体族占比（self / explicit-owner 两栏；只读）。

- family = 单一 predicate；entity = 显式 owner，或“我/我的”解析出的 self 身份；
- self 身份由库内“我叫X”确定（无则记 self）；
- 多实体族 = 同族 distinct 实体数 > 1。
不 import 产品模块；不写 daily。
"""
import hashlib
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "out"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import p1b_stage_a as A      # 仅 out/ 内规则复用；产品不 import 它


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def self_identity(rows):
    cnt = {}
    for _i, t in rows:
        for s in A.NAME_SAY.findall(str(t)):
            cnt[s] = cnt.get(s, 0) + 1
    if not cnt:
        return "self", []
    name = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return name, sorted(cnt)


def classify_entities(rows, self_id):
    families = {}
    skipped = 0
    for rid, text in rows:
        preds = A.predicates(text)
        if len(preds) != 1:
            skipped += 1
            continue
        fam = preds[0]
        subs = A.explicit_subjects(text)
        if subs:
            ents = list(subs)
        elif any(p in str(text) for p in ("我", "我的", "我们", "咱们", "俺")):
            ents = [self_id]
        else:
            skipped += 1
            continue
        slot = families.setdefault(fam, {"entities": set(), "explicit": set(), "ids": []})
        slot["entities"].update(ents)
        slot["explicit"].update(subs)
        slot["ids"].append(int(rid))
    return families, skipped


def summarize(families, label, self_id):
    rows = []
    for fam, slot in sorted(families.items()):
        ents = sorted(slot["entities"])
        exp = sorted(slot["explicit"])
        rows.append({"family": fam, "entities": ents, "n_entities": len(ents),
                     "explicit_owners": exp,
                     "multi_entity": len(ents) > 1,
                     "multi_explicit": len(exp) > 1,
                     "ids": sorted(set(slot["ids"])), "label": label})
    n = len(rows)
    multi_all = [x for x in rows if x["multi_entity"]]
    multi_exp = [x for x in rows if x["multi_explicit"]]
    return {"label": label, "self_id": self_id, "n_families": n,
            "multi_entity_families": len(multi_all),
            "multi_entity_rate": round(len(multi_all) / float(n), 4) if n else 0.0,
            "multi_explicit_families": len(multi_exp),
            "multi_explicit_rate": round(len(multi_exp) / float(n), 4) if n else 0.0,
            "families": rows,
            "multi_names": [x["family"] for x in multi_all],
            "multi_explicit_names": [x["family"] for x in multi_exp]}


def load(db):
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    rows = [(int(r[0]), str(r[1])) for r in
            con.execute("SELECT id,text FROM memory_source ORDER BY id")]
    con.close()
    return rows


def main():
    daily_db = os.path.join(ROOT, "kvmem", "daily", "chat.db")
    n200_db = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
    daily_rows, n200_rows = load(daily_db), load(n200_db)
    d_self, d_names = self_identity(daily_rows)
    n_self, n_names = self_identity(n200_rows)
    fam_daily, skip_d = classify_entities(daily_rows, d_self)
    fam_n200, skip_n = classify_entities(n200_rows, n_self)
    daily = summarize(fam_daily, "daily", d_self)
    n200 = summarize(fam_n200, "n200", n_self)
    daily.update({"rows": len(daily_rows), "skipped": skip_d,
                  "self_candidates": d_names})
    n200.update({"rows": len(n200_rows), "skipped": skip_n,
                 "self_candidates": n_names})
    verdict = {
        "rule": "daily 多实体族 ≈0 ⇒ owner 线不适用（不是失败），K2/检索维持永久 off",
        "daily_multi_entity_families": daily["multi_entity_families"],
        "daily_multi_explicit_families": daily["multi_explicit_families"],
        "owner_line": ("not_applicable" if daily["multi_entity_families"] == 0
                       else "needs_review"),
    }
    rep = {"schema": "p1b_multi_entity_v1", "read_only": True,
           "daily_db": daily_db, "daily_sha256": sha_file(daily_db),
           "n200_db": n200_db, "n200_sha256": sha_file(n200_db),
           "definition": "family=single predicate; entity=explicit owner or self; "
                         "multi=distinct entities>1 in a family",
           "daily": daily, "n200": n200, "verdict": verdict}
    json.dump(rep, open(os.path.join(ROOT, "out", "P1B-MULTI-ENTITY.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = ["# P1b 多实体族占比（只读）", "",
          "- daily `%s` sha `%s`；n200 `%s` sha `%s`" %
          (daily_db, rep["daily_sha256"][:16], n200_db, rep["n200_sha256"][:16]),
          "- 定义：family=单一 predicate；entity=显式 owner 或“我/我的”解析出的 self；"
          "同族 distinct 实体 >1 即多实体族。", "",
          "## 汇总", "",
          "| 数据集 | 族数 | 多实体族(all) | 多实体率 | 多显式 owner 族 | self 身份 |",
          "|---|---|---|---|---|---|",
          "| daily | %d | **%d** | %.1f%% | %d | %s |" %
          (daily["n_families"], daily["multi_entity_families"],
           daily["multi_entity_rate"] * 100, daily["multi_explicit_families"], daily["self_id"]),
          "| n200（对照） | %d | %d | %.1f%% | %d | %s |" %
          (n200["n_families"], n200["multi_entity_families"],
           n200["multi_entity_rate"] * 100, n200["multi_explicit_families"], n200["self_id"]),
          "", "## daily 逐族", "",
          "| family | 实体 | 实体数 | 多实体 | ids |", "|---|---|---|---|---|"]
    for x in daily["families"]:
        md.append("| %s | %s | %d | %s | %s |" %
                  (x["family"], "、".join(x["entities"]), x["n_entities"],
                   "**是**" if x["multi_entity"] else "否", x["ids"]))
    md += ["", "## n200 对照（族级）", "",
           "| family | 实体数 | 多实体 |", "|---|---|---|"]
    for x in n200["families"]:
        md.append("| %s | %d | %s |" % (x["family"], x["n_entities"],
                                        "是" if x["multi_entity"] else "否"))
    md += ["", "## 判定", "",
           "- daily 多实体族：%d / %d（显式 owner 多族：%d）" %
           (daily["multi_entity_families"], daily["n_families"],
            daily["multi_explicit_families"]),
           "- **owner 线：%s** → %s" % (verdict["owner_line"],
             "不适用，K2/检索维持永久 off" if verdict["owner_line"] == "not_applicable"
             else "需复核"),
           "- self 身份：daily=%s（候选 %s）；n200=%s。只读；未写 daily、未 commit。" %
           (d_self, d_names, n_self)]
    open(os.path.join(ROOT, "out", "P1B-MULTI-ENTITY.md"), "w",
         encoding="utf-8").write("\n".join(md) + "\n")
    print(json.dumps({"daily": {k: daily[k] for k in
                                ("n_families", "multi_entity_families",
                                 "multi_explicit_families", "self_id")},
                      "n200": {k: n200[k] for k in
                               ("n_families", "multi_entity_families",
                                "multi_explicit_families", "self_id")},
                      "verdict": verdict}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
