# -*- coding: utf-8 -*-
"""P1b Stage A：块可判率（显式 subject + predicate；只读）。

- 显式主体：人名/公司/品牌等确定性别名，**不接受 我/我的 兜底**；
- 默认自我：只有 我/我的 + predicate，单独一栏；
- 其余：不可判，给原因。
- 纯本地规则（无模型）；不 import memory_service/chat_daily；不写 daily、不碰 tags。
输出：out/P1B-STAGE-A.json / .md
"""
import hashlib
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def sha_file(p):
    import hashlib as _h
    return _h.sha256(open(p, "rb").read()).hexdigest()


STOP = {
    "我", "你", "他", "她", "它", "我们", "你们", "他们", "她们", "大家", "自己",
    "这个", "那个", "什么", "怎么", "今天", "昨天", "明天", "现在", "后来", "顺便",
    "补充", "自动", "对话", "用户", "助手", "天气", "屋里", "桌上", "刚才", "这些",
    "那些", "事情", "东西", "地方", "时候", "工作", "资料", "邮件", "会议", "车牌",
    "手机", "银行", "公司", "老家", "座位", "号码", "名字", "猫", "狗", "车", "同事",
    "朋友", "前台", "对方", "物业", "快递", "外卖", "老师", "医生", "司机", "师傅",
    "本周", "下周", "这周", "周末", "上午", "下午", "晚上", "中午", "早上", "第一",
    "第二", "第三", "一个", "两个", "没有", "可以", "然后", "因为", "所以", "但是",
    "每周", "每天", "每年", "每月", "平时", "最近", "目前", "以后", "之前",
}
PRONOUN_SUBJECT = ("我", "我的", "我们", "咱们", "俺")
BRANDS = ("特斯拉", "比亚迪", "理想", "蔚来", "小鹏", "小米")
NAME_SAY = re.compile(r"我叫([\u4e00-\u9fff]{2,3})")
NAME_START = re.compile(
    r"^([\u4e00-\u9fff]{2,3})(?=(?:一开始|后来|再后来|现在|说|家|把|换|改成|的|"
    r"下周|本周|这周|下下周|明天|后天|今晚))")
NAME_POSS = re.compile(
    r"([\u4e00-\u9fff]{2,3})(?=(?:家)?的(?:车|猫|狗|手机|电话|银行卡|车牌|公司|"
    r"老家|会议|座位|号码|名字|邮箱|生日))")
BRANDS = ("特斯拉", "比亚迪", "理想", "蔚来", "小鹏", "小米")
_BAD_NAME_PARTS = ("开始", "后来", "现在", "的", "家", "说", "把", "换", "改成",
                   "每周", "每天", "今年", "去年")


def _ok_name(s):
    if not s or s in STOP or any(p in s for p in _BAD_NAME_PARTS):
        return False
    if s[0] in "\u6211\u4f60\u4ed6\u5979\u5b83\u54b1\u4ffa":   # 我/你/他/她/它/咱/俺 不得当主体
        return False
    if len(s) < 2 or len(s) > 3:
        return False
    return all("\u4e00" <= c <= "\u9fff" for c in s)


def explicit_subjects(text):
    t = str(text or "")
    subs = []
    for s in NAME_SAY.findall(t) + NAME_START.findall(t) + NAME_POSS.findall(t):
        if _ok_name(s) and s not in subs:
            subs.append(s)
    for b in BRANDS:
        if b in t and b not in subs:
            subs.append(b)
    # 前后缀重叠时保留较短（“郑凯一/郑凯”只留 郑凯）
    out = []
    for s in sorted(subs, key=len):
        if not any(s != o and (s in o or o in s) for o in out):
            out.append(s)
    return out


PREDS = (
    ("plate", ("车牌号", "车牌", "牌照")),
    ("phone", ("手机号", "电话号码", "号码")),
    ("bank", ("银行卡", "卡号")),
    ("meeting", ("会议", "开会", "组会")),
    ("travel", ("出差", "旅行")),
    ("seat", ("座位", "工位")),
    ("hometown", ("老家", "故乡")),
    ("company", ("公司", "单位")),
    ("cat", ("猫",)),
    ("dog", ("狗",)),
    ("color", ("颜色", "车漆", "车身颜色")),
    ("email", ("邮箱",)),
    ("address", ("地址", "门牌")),
    ("birthday", ("生日",)),
)


def predicates(text):
    t = str(text or "")
    return [name for name, kws in PREDS if any(k in t for k in kws)]


def classify(text):
    subs = explicit_subjects(text)
    preds = predicates(text)
    has_self = any(p in str(text or "") for p in PRONOUN_SUBJECT)
    if len(subs) > 1:
        return {"kind": "unextractable", "reason": "ambiguous_multi_subject:%s" % "/".join(subs),
                "subjects": subs, "predicates": preds}
    if subs:
        if not preds:
            return {"kind": "unextractable", "reason": "no_predicate",
                    "subjects": subs, "predicates": preds}
        if len(preds) > 1:
            return {"kind": "unextractable", "reason": "multi_predicate:%s" % "/".join(preds),
                    "subjects": subs, "predicates": preds}
        return {"kind": "explicit", "subject": subs[0], "predicate": preds[0],
                "subjects": subs, "predicates": preds}
    if has_self and preds:
        return {"kind": "default_self", "subject": "self", "predicate": preds[0],
                "subjects": [], "predicates": preds}
    return {"kind": "unextractable",
            "reason": "no_subject" if not has_self else "no_predicate",
            "subjects": [], "predicates": preds}


def run(rows, label):
    items = []
    for rid, text in rows:
        c = classify(text)
        c.update({"id": int(rid), "text": str(text)[:80]})
        items.append(c)
    n = len(items)
    exp = [x for x in items if x["kind"] == "explicit"]
    sel = [x for x in items if x["kind"] == "default_self"]
    une = [x for x in items if x["kind"] == "unextractable"]
    reason_dist = {}
    for x in une:
        r = x["reason"].split(":")[0]
        reason_dist[r] = reason_dist.get(r, 0) + 1
    pred_dist = {}
    for x in exp:
        pred_dist[x["predicate"]] = pred_dist.get(x["predicate"], 0) + 1
    return {
        "label": label, "n": n,
        "explicit": len(exp), "default_self": len(sel), "unextractable": len(une),
        "explicit_rate": round(len(exp) / float(n), 4) if n else 0.0,
        "default_self_rate": round(len(sel) / float(n), 4) if n else 0.0,
        "predicate_dist": dict(sorted(pred_dist.items())),
        "unextractable_reasons": dict(sorted(reason_dist.items())),
        "extractable_items": exp,
        "unextractable_items": une,
    }


def main():
    daily_db = os.path.join(ROOT, "kvmem", "daily", "chat.db")
    n200_db = os.path.join(ROOT, "kvmem", "scale40k", "n200", "chat.db")
    con = sqlite3.connect("file:%s?mode=ro" % daily_db.replace("\\", "/"), uri=True)
    daily_rows = [(int(r[0]), str(r[1])) for r in
                  con.execute("SELECT id,text FROM memory_source ORDER BY id")]
    con.close()
    con = sqlite3.connect("file:%s?mode=ro" % n200_db.replace("\\", "/"), uri=True)
    n200_rows = [(int(r[0]), str(r[1])) for r in
                 con.execute("SELECT id,text FROM memory_source ORDER BY id")]
    con.close()

    daily = run(daily_rows, "daily")
    n200 = run(n200_rows, "n200")
    gate = {"threshold_explicit_rate": 0.70,
            "daily_explicit_rate": daily["explicit_rate"],
            "pass": daily["explicit_rate"] >= 0.70}
    rep = {
        "schema": "p1b_stage_a_v1",
        "read_only": True,
        "daily_db": daily_db, "daily_sha256": sha_file(daily_db),
        "n200_db": n200_db, "n200_sha256": sha_file(n200_db),
        "definition": "judgeable = deterministic explicit subject + one predicate; "
                      "'我/我的' is default_self, never a fallback subject",
        "gate": gate, "daily": daily, "n200": n200,
    }
    out_json = os.path.join(ROOT, "out", "P1B-STAGE-A.json")
    out_md = os.path.join(ROOT, "out", "P1B-STAGE-A.md")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    md = ["# P1b Stage A：块可判率（只读，无模型）","",
          "- daily `%s` sha `%s`；n200 `%s` sha `%s`" %
          (daily_db, rep["daily_sha256"][:16], n200_db, rep["n200_sha256"][:16]),
          "- 定义：显式 subject + 单一 predicate 才算可判；**我/我的 只记 default_self，不当兜底主体**。",
          "", "## 主门槛（daily 真实文本）","",
          "| 数据集 | n | 显式可判 | 显式率 | 默认自我 | 默认率 | 不可判 |",
          "|---|---|---|---|---|---|---|",
          "| daily | %d | %d | **%.1f%%** | %d | %.1f%% | %d |" %
          (daily["n"], daily["explicit"], daily["explicit_rate"] * 100,
           daily["default_self"], daily["default_self_rate"] * 100, daily["unextractable"]),
          "| n200（补充） | %d | %d | %.1f%% | %d | %.1f%% | %d |" %
          (n200["n"], n200["explicit"], n200["explicit_rate"] * 100,
           n200["default_self"], n200["default_self_rate"] * 100, n200["unextractable"]),
          "", "- 门槛显式率 ≥70%% → daily **%.1f%%**：**%s**" %
          (daily["explicit_rate"] * 100, "PASS" if gate["pass"] else "STOP"),
          "", "## 谓词分布（可判块）",""]
    for label, d in (("daily", daily), ("n200", n200)):
        md.append("- %s：%s" % (label, d["predicate_dist"] or "无"))
    md += ["", "## n200 不可判原因分布","",
           "- %s" % (n200["unextractable_reasons"] or "无"), "",
           "## daily 抽不出的块与原因",""]
    for x in daily["unextractable_items"]:
        md.append("- `%d` %s ← %s" % (x["id"], x["text"][:42], x["reason"]))
    md += ["", "## daily 显式可判块",""]
    for x in daily["extractable_items"]:
        md.append("- `%d` subject=%s predicate=%s ← %s" %
                  (x["id"], x["subject"], x["predicate"], x["text"][:42]))
    md += ["", "## 判定","",
           "- **%s**：daily 显式主体率 %.1f%%（门槛 70%%）；默认自我率 %.1f%%。" %
           ("PASS（可进 Stage B）" if gate["pass"] else "STOP（显式可判率 <70%）",
            daily["explicit_rate"] * 100, daily["default_self_rate"] * 100),
           "- 只读；未写 daily、未碰 tags、未改读写路径、未 commit。"]
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps({"gate": gate,
                      "daily": {k: daily[k] for k in ("n", "explicit", "explicit_rate",
                                                      "default_self", "default_self_rate",
                                                      "unextractable", "predicate_dist")},
                      "n200": {k: n200[k] for k in ("n", "explicit", "explicit_rate",
                                                    "default_self", "default_self_rate",
                                                    "unextractable", "predicate_dist")}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
