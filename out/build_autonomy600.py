# -*- coding: utf-8 -*-
"""生成 out/autonomy600/{train,dev,test}.jsonl + manifest.json（CPU only，无 GPU/服务）。

seed=60000；600 条 = A120 / B100 / C120 / D160 / N100。
族(train16/dev4/test4)与模板(test 与 train 不重叠)三重留出。
生成后自检（本脚本）+ 机器门 out/sft_data_gate.py G1-G13。
用法：python -X utf8 out/build_autonomy600.py
"""
import ast
import hashlib
import json
import os
import random
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(HERE, "autonomy600")
sys.path.insert(0, HERE)
from autonomy600_data import KINDS, NEG  # noqa: E402

SEED = 60000
POLICY_FILE = os.path.join(ROOT, "tools", "chat_daily.py")
MAXLEN, MINLEN = 60, 8


def policy_from(path):
    src = open(path, encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "SYSTEM_POLICY" for t in n.targets):
            return n.value.value if isinstance(n.value, ast.Constant) else eval(
                ast.get_source_segment(src, n.value).strip("() \n"))
    raise RuntimeError("SYSTEM_POLICY not found")


POLICY = policy_from(POLICY_FILE)
POLICY_SHA16 = hashlib.sha256(POLICY.encode("utf-8")).hexdigest()[:16]

WD = "一二三四五六日"
CN = "零一二三四五六七八九十"


def cn_hour(h):
    h = h % 12
    return "十二" if h == 0 else CN[h] if h <= 10 else "十" + CN[h - 10]


def tp_word(hour, minute):
    """时段口语说法（都以可接“了”结尾），与真实时钟误差 ≤5 分钟。"""
    hw = cn_hour(hour)
    if minute < 20:
        return hw + "点多"
    if minute < 36:
        return hw + "点半"
    return "快" + ("十二" if hour % 12 == 11 else cn_hour(hour + 1)) + "点"


def time_line(dt):
    return "当前时间：%04d-%02d-%02d 星期%s %02d:%02d。" % (
        dt.year, dt.month, dt.day, WD[dt.weekday()], dt.hour, dt.minute)


def mem_block(kind):
    lines = list(kind["mem"]) + [kind["last"]]
    return "记忆：\n- " + "\n- ".join(lines)


def build_system(kind, dt):
    return time_line(dt) + "\n\n" + mem_block(kind) + "\n\n" + POLICY


# ---------------- 时间槽池 ----------------
def build_time_pool():
    rng = random.Random(SEED)
    slots = []
    d0 = date(2026, 11, 1)
    for i in range(61):  # 2026-11-01 .. 2026-12-31
        d = d0 + timedelta(days=i)
        for h in range(7, 24):
            for m in (3, 9, 14, 21, 27, 34, 41, 47, 52, 57):
                slots.append((d, h, m))
    rng.shuffle(slots)
    return slots


SLOTS = build_time_pool()
SLOT_USED = set()


def take_slot(hour=None, dow=None):
    for s in SLOTS:
        key = (s[0], s[1], s[2])
        if key in SLOT_USED:
            continue
        if hour is not None and s[1] != hour:
            continue
        if dow is not None and s[0].weekday() != dow:
            continue
        SLOT_USED.add(key)
        return datetime(s[0].year, s[0].month, s[0].day, s[1], s[2])
    raise RuntimeError("时间槽用尽 hour=%r dow=%r" % (hour, dow))


# ---------------- 分配 ----------------
TRAIN_KINDS = KINDS[:16]
DEV_KINDS = KINDS[16:20]
TEST_KINDS = KINDS[20:24]
D_HOURS = [20, 21, 22]
NEG_BASE = len(NEG) // 3  # 50//3 -> 16,16,18 见下

assert len(KINDS) == 24, len(KINDS)
assert len(TRAIN_KINDS) == 16 and len(DEV_KINDS) == 4 and len(TEST_KINDS) == 4
assert len(NEG) == 50, len(NEG)


def neg_pair_split():
    """把 50 个负例场景切成三段，三 split 不复用同一场景。"""
    idx = list(range(len(NEG)))
    rng = random.Random(SEED + 7)
    rng.shuffle(idx)
    a, b = idx[:34], idx[34:42]
    c = idx[42:]
    assert len(a) == 34 and len(b) == 8 and len(c) == 8
    return {"train": a, "dev": b, "test": c}


NEG_SPLIT = neg_pair_split()


def alloc(split):
    """返回 [(kind, category, idx)]，长度 480/60/60，类别配额精确。"""
    kinds = {"train": TRAIN_KINDS, "dev": DEV_KINDS, "test": TEST_KINDS}[split]
    per = []
    for i, k in enumerate(kinds):
        if split == "train":
            b = 5 if i < 12 else 4
            n = 4 if i < 12 else 5
            cat = [("A", 6), ("B", b), ("C", 6), ("D", 9), ("N", n)]
        else:
            cat = [("A", 3), ("B", 3), ("C", 3), ("D", 2), ("N", 4)]
        for c, cnt in cat:
            per.append((k, c, cnt))
    return per


def make_row(kind, cat, k, split, neg_state):
    """k: 该类在本族内的序号(0-based)。"""
    if cat == "A":
        user = kind["facts"][k % 3]
        asst = kind["A"][k % 4]
        tid = "A_%s" % kind["fam"]
    elif cat == "B":
        user = kind["Bf"][k % 2]
        asst = kind["Ba"][k % 3]
        tid = "B_%s" % kind["fam"]
    elif cat == "C":
        user = kind["Cq"][k % 2]
        asst = kind["Ca"][k % 3]
        tid = "C_%s" % kind["fam"]
    elif cat == "D":
        mi, ti = divmod(k, 3)
        hour = kind.get("dhours", D_HOURS)[ti]
        dt = take_slot(hour=hour, dow=kind.get("dow"))
        tp = tp_word(hour, dt.minute)
        user = "（" + kind["Ds"][(mi + ti) % 3].format(tp=tp).replace("你", "我") + "）"
        asst = kind["D"][mi].format(tp=tp)
        sysc = build_system(kind, dt)
        return dict(sysc=sysc, user=user, asst=asst, cat=cat, kind=kind,
                    tid="D_%s" % kind["fam"], dt=dt)
    elif cat == "N":
        pairs = NEG_SPLIT[split]
        total = sum(c for _, c2, c in alloc(split) if c2 == "N")
        use = neg_state["n"]
        neg_state["n"] += 1
        pair_i = pairs[use % len(pairs)]
        variant = 0 if use < total // 2 else 1
        user, replies = NEG[pair_i]
        asst = replies[variant]
        tid = "N_%s" % kind["fam"]
        dt = take_slot()
        sysc = build_system(kind, dt)
        return dict(sysc=sysc, user=user, asst=asst, cat=cat, kind=kind,
                    tid=tid, dt=dt, neg_pair=pair_i, neg_variant=variant)
    else:
        raise ValueError(cat)
    dt = take_slot()
    return dict(sysc=build_system(kind, dt), user=user, asst=asst, cat=cat,
                kind=kind, tid=tid, dt=dt)


# ---------------- 自检规则（与机器门同源，另加更严项） ----------------
RE_G1 = re.compile(r"（[^）]{0,40}请|请主动|模拟|扮演|作为助手|生成一条|现在是.{0,12}，?请")
RE_G3_NUM = re.compile(r"\d+")
RE_G3_DATE = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*[号日]|\d{1,2}:\d{2}|\d{1,2}\s*点(?:半|一刻|\d{1,2}分)?")
RE_G3_PRICE = re.compile(r"\d+\s*(?:元|块|万|千)")
RE_G3_TEMP = re.compile(r"-?\d+\s*(?:℃|度)")
RE_G4 = re.compile(r"我(?:已经)?(?:记下|记住|记录|存|保存)了|已记住|记下来了|收到，我记")
RE_G5 = re.compile(r"天气|气温|温度|下雨|下雪|晴|阴|空气|新闻|股价|汇率|限行|路况|实时|最新")
RE_G6 = re.compile(r"已经帮你|我帮你(?:发|转|订|删|登录|下单|打电话|预约)了|已发送|已转账|已删除")
RE_G11 = re.compile(r"别吃|换药|建议吃|可以吃|换一种药|停药|投资建议|建议投资|可以投|能赚|直接签|可以签|法律建议")
RE_MD = re.compile(r"[\n\r]|^\s*[-*#•]\s|\*\*")
RE_TIME_LINE = re.compile(r"^当前时间：\d{4}-\d{2}-\d{2} 星期[一二三四五六日] \d{2}:\d{2}。")
RE_G12_ABS = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*[号日]|\d{4}-\d{2}-\d{2}|星期[一二三四五六日]")
CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "苏州", "天津",
          "重庆", "长沙", "郑州", "青岛", "银川", "哈尔滨", "洛阳", "厦门", "合肥", "济南", "福州",
          "昆明", "大连"]
BAN_USER = ["请", "模拟", "扮演", "作为助手", "生成一条"]


def norm(s):
    return re.sub(r"\s+", "", s or "")


def grams(s, n=2):
    s = norm(s)
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def g3_tokens(asst):
    toks = []
    for pat in (RE_G3_NUM, RE_G3_DATE, RE_G3_PRICE, RE_G3_TEMP):
        toks.extend(pat.findall(asst))
    toks.extend(c for c in CITIES if c in asst)
    return toks


def self_check(rows, neg_rows):
    errs = []

    def bad(i, msg):
        errs.append("line %d: %s" % (i + 1, msg))

    seen_su, aidx = {}, {}
    for i, r in enumerate(rows):
        sysc, user, asst = r["sysc"], r["user"], r["asst"]
        # 结构
        assert sysc.endswith(POLICY), "policy tail"
        parts = sysc.split("\n\n")
        if len(parts) < 3 or not RE_TIME_LINE.match(parts[0]):
            bad(i, "system 结构/时间行异常")
        # G1
        if RE_G1.search(user):
            bad(i, "G1 %r" % user[:40])
        for w in BAN_USER:
            if w in user:
                bad(i, "用户侧禁用词 %s: %r" % (w, user[:40]))
        if r["cat"] != "C" and user.rstrip().endswith(("？", "?")):
            bad(i, "非 C 类 user 带问号: %r" % user[:40])
        if r["cat"] == "C" and not user.rstrip().endswith(("？", "?")):
            bad(i, "C 类 user 未以问号结尾: %r" % user[:40])
        # G2/G9 长度与格式
        if not (MINLEN <= len(asst) <= MAXLEN):
            bad(i, "长度 %d: %r" % (len(asst), asst))
        if RE_MD.search(asst):
            bad(i, "markdown/换行: %r" % asst)
        if RE_G3_NUM.search(asst) and "T14" not in asst:
            bad(i, "assistant 含阿拉伯数字: %r" % asst)
        if "请" in asst:
            bad(i, "assistant 含'请': %r" % asst)
        # G4/G5/G6/G11/G12
        if RE_G4.search(asst):
            bad(i, "G4: %r" % asst)
        if RE_G5.search(asst):
            bad(i, "G5: %r" % asst)
        if RE_G6.search(asst):
            bad(i, "G6: %r" % asst)
        if RE_G11.search(asst) and not re.search(r"医生|专业人士|律师", asst):
            bad(i, "G11: %r" % asst)
        if RE_G12_ABS.search(asst) and norm(asst) not in norm(user + sysc):
            bad(i, "G12 绝对日期: %r" % asst)
        # G3 无锚点具体值
        ctx = norm(sysc) + norm(user)
        for t in g3_tokens(asst):
            if norm(t) not in ctx:
                bad(i, "G3 %r: %r" % (t, asst))
        # G7 记忆锚点（D 必带；A/C 带事实）
        anchor = r["kind"]["anchor"]
        memtext = norm(mem_block(r["kind"]) + user)
        if r["cat"] == "A":
            if not (grams(asst, 2) & grams(memtext, 2)):
                bad(i, "A 未接住事实(无 2-gram 重合) %s: %r" % (anchor, asst))
        if r["cat"] == "C":
            if anchor not in norm(asst + user):
                bad(i, "C 未带出锚点 %s: %r" % (anchor, asst))
            if not (grams(asst, 2) & grams(memtext, 2)):
                bad(i, "C 未召回事实(无 2-gram 重合): %r" % asst)
        if r["cat"] == "D":
            if not (grams(asst, 2) & grams(memtext, 2)):
                bad(i, "D 无记忆 2-gram 锚点: %r" % asst)
        if r["cat"] == "N":
            if anchor in norm(asst):
                bad(i, "N 类不应带锚点 %s: %r" % (anchor, asst))
            if len(grams(asst, 4) & grams(norm(mem_block(r["kind"])), 4)) > 0:
                bad(i, "N 类与记忆有 4-gram 重合: %r" % asst)
        # G10 唯一性
        key = (norm(sysc), norm(user))
        if key in seen_su:
            bad(i, "G10 重复 (system,user)，首次 line %d" % seen_su[key])
        seen_su[key] = i + 1
        aidx.setdefault(norm(asst), []).append(i + 1)
    dup = {a: v for a, v in aidx.items() if len(v) > 3}
    if dup:
        errs.append("G8 assistant 重复 >3 次：%d 组，例 %r" % (len(dup), list(dup.items())[:2]))
    # 负例子类与比例
    sub = {}
    for r in neg_rows:
        sub["irrelevant" if r["neg_pair"] >= 25 else "silence"] = \
            sub.get("irrelevant" if r["neg_pair"] >= 25 else "silence", 0) + 1
    return errs, sub, dup


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows_by_split = {}
    all_rows = []
    for split in ("train", "dev", "test"):
        rows, neg_state = [], {"n": 0}
        counters = {}
        for kind, cat, cnt in alloc(split):
            for k in range(cnt):
                r = make_row(kind, cat, k, split, neg_state)
                r["split"] = split
                r["_k"] = k
                rows.append(r)
        rows.sort(key=lambda x: (x["kind"]["id"], x["cat"], x["_k"]))
        rows_by_split[split] = rows
        all_rows.extend([(split, r) for r in rows])

    # 类别配额核对
    from collections import Counter
    cnt = Counter(r["cat"] for _, r in all_rows)
    want = {"A": 120, "B": 100, "C": 120, "D": 160, "N": 100}
    assert dict(cnt) == want, (dict(cnt), want)
    for split in ("train", "dev", "test"):
        assert len(rows_by_split[split]) == {"train": 480, "dev": 60, "test": 60}[split]

    # 自检
    all_r = [r for _, r in all_rows]
    errs, sub, dup = self_check(all_r, [r for r in all_r if r["cat"] == "N"])
    if errs:
        print("SELF-CHECK FAILED: %d" % len(errs))
        for e in errs[:40]:
            print("  " + e)
        return 2
    print("self-check OK: 600 rows, cat=%r, neg_subtypes=%r, dup>3=%d"
          % (dict(cnt), sub, len(dup)))

    # 写入
    shas, lines = {}, {}
    for split in ("train", "dev", "test"):
        p = os.path.join(OUTDIR, split + ".jsonl")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            for r in rows_by_split[split]:
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": r["sysc"]},
                    {"role": "user", "content": r["user"]},
                    {"role": "assistant", "content": r["asst"]}]}, ensure_ascii=False) + "\n")
        shas[split] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        lines[split] = len(rows_by_split[split])
    # 全体（供门禁一次性跑）
    pall = os.path.join(OUTDIR, "_gate_input_all.jsonl")
    with open(pall, "w", encoding="utf-8", newline="\n") as f:
        for _, r in all_rows:
            f.write(json.dumps({"messages": [
                {"role": "system", "content": r["sysc"]},
                {"role": "user", "content": r["user"]},
                {"role": "assistant", "content": r["asst"]}]}, ensure_ascii=False) + "\n")
    shas["all"] = hashlib.sha256(open(pall, "rb").read()).hexdigest()

    meta = []
    for split in ("train", "dev", "test"):
        for i, r in enumerate(rows_by_split[split]):
            item = {"split": split, "line": i + 1, "category": r["cat"],
                    "family": r["kind"]["fam"], "template_id": r["tid"],
                    "source": "autonomy600/synthetic-fictional-pool",
                    "anchor": r["kind"]["anchor"]}
            if r["cat"] == "N":
                item["neg_subtype"] = "irrelevant" if r["neg_pair"] >= 25 else "silence"
            meta.append(item)

    # 三重留出核验（族 / 模板 / 负例场景池）
    fam = {sp: {k["fam"] for k in ks} for sp, ks in
           (("train", TRAIN_KINDS), ("dev", DEV_KINDS), ("test", TEST_KINDS))}
    tid = {sp: {r["tid"] for r in rows_by_split[sp]} for sp in ("train", "dev", "test")}
    usr = {sp: {norm(r["user"]) for r in rows_by_split[sp]} for sp in ("train", "dev", "test")}
    negp = {sp: set(NEG_SPLIT[sp]) for sp in ("train", "dev", "test")}
    hold = {
        "family_test_vs_train_disjoint": not (fam["test"] & fam["train"]),
        "family_dev_vs_train_disjoint": not (fam["dev"] & fam["train"]),
        "family_dev_vs_test_disjoint": not (fam["dev"] & fam["test"]),
        "template_test_vs_train_disjoint": not (tid["test"] & tid["train"]),
        "template_dev_vs_train_disjoint": not (tid["dev"] & tid["train"]),
        "neg_scene_pool_test_vs_train_disjoint": not (negp["test"] & negp["train"]),
        "user_text_test_vs_train_overlap": len(usr["test"] & usr["train"]),
        "family_sizes": {k: len(v) for k, v in fam.items()},
        "template_sizes": {k: len(v) for k, v in tid.items()},
    }
    assert hold["family_test_vs_train_disjoint"] and hold["family_dev_vs_train_disjoint"]
    assert hold["template_test_vs_train_disjoint"] and hold["template_dev_vs_train_disjoint"]
    assert hold["neg_scene_pool_test_vs_train_disjoint"]
    assert hold["family_dev_vs_test_disjoint"]
    print("holdout OK: " + json.dumps(hold, ensure_ascii=False))

    manifest = {
        "schema": "autonomy600_v1",
        "seed": SEED,
        "spec": "out/SFT-AUTONOMY-DATA-SPEC.md",
        "policy_sha16": POLICY_SHA16,
        "policy_source": "tools/chat_daily.py:SYSTEM_POLICY（逐字，G9 要求）",
        "total": 600,
        "lines": lines,
        "category_counts": dict(cnt),
        "negative": {"count": 100, "ratio_of_all": round(100 / 600, 4),
                     "subtypes": sub,
                     "note": "100 条全部属于“沉默/无关场景不得开口”，assistant 只接当下话题，不带记忆、不主动提醒"},
        "splits": {
            "train": {"rows": 480, "families": [k["id"] + ":" + k["fam"] for k in TRAIN_KINDS]},
            "dev": {"rows": 60, "families": [k["id"] + ":" + k["fam"] for k in DEV_KINDS]},
            "test": {"rows": 60, "families": [k["id"] + ":" + k["fam"] for k in TEST_KINDS]},
        },
        "holdout_check": hold,
        "sha256": shas,
        "files": ["train.jsonl", "dev.jsonl", "test.jsonl", "_gate_input_all.jsonl", "GATE.json"],
        "format": "每行仅 {\"messages\":[system,user,assistant]}；category/family/source 见下方 meta（训练加载器只读 messages）",
        "value_pool": "全虚构：芋圆/仙贝/芒果/内脏/泉州/云启/日语/陶艺/桃酥/柳州/骑车/星岩/望江里/龟背竹/美式/雾中灯塔/口琴/老聂/十一月十七/灰绿色/老港片/池姐/会计",
        "value_pool_overlap_with_train_v8_v9_v10": OVERLAP,
        "gate": "GATE.json（out/sft_data_gate.py G1-G13）",
        "meta": meta,
    }
    with open(os.path.join(OUTDIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(json.dumps({"lines": lines, "sha256": shas,
                      "categories": dict(cnt), "neg": sub}, ensure_ascii=False, indent=1))
    return 0


def value_overlap():
    """与既有 train_v8/v9/v10/v3_autonomy 的值池重叠检查。"""
    corpus = []
    for fn in ("train_v8.jsonl", "train_v9.jsonl", "train_v10.jsonl", "v3_autonomy.jsonl"):
        p = os.path.join(ROOT, "training", "sft", fn)
        if os.path.exists(p):
            corpus.append(open(p, encoding="utf-8").read())
    corpus = "\n".join(corpus)
    vals = ["芋圆", "仙贝", "芒果", "内脏", "泉州", "云启", "陶艺", "桃酥", "柳州",
            "星岩", "望江里", "龟背竹", "雾中灯塔", "口琴", "老聂", "灰绿色", "池姐",
            "老港片", "中级会计", "美式", "桃酥"]
    hit = {v: corpus.count(v) for v in sorted(set(vals)) if corpus.count(v)}
    return hit


OVERLAP = value_overlap()

if __name__ == "__main__":
    sys.exit(main())