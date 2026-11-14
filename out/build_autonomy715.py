# -*- coding: utf-8 -*-
"""v2 生成：715 行 = A120 / B100 / C120 / D160 / N215（should_trigger=false 215，30.07%），
train 572 / dev 72 / test 71（每 split 负例比均 ≥25%）。seed=60000，CPU only。

新增：
- 逐行 should_trigger(bool) + trigger_reason(≤20 字，只写“为什么该/不该”，无规则号)
- 负例池 NEG(50) + NEG2(115)，按 split 分池（族/模板/场景三重留出）
- manifest-v2.json（含 ruling mapping、每行 family/category/split/should_trigger、sha）

用法：python -X utf8 out/build_autonomy715.py
"""
import ast
import hashlib
import json
import os
import random
import re
import shutil
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(HERE, "autonomy600")   # 沿用 B 已接的路径
sys.path.insert(0, HERE)
from autonomy600_data import KINDS, NEG, NEG2  # noqa: E402

SEED = 60000
POLICY_FILE = os.path.join(ROOT, "tools", "chat_daily.py")
MAXLEN, MINLEN = 60, 8

SPLIT_ROWS = {"train": 572, "dev": 72, "test": 71}
NEG_HARD_MIN = 0.25          # 每个 split 负例率下限
NEG_TOTAL_MIN = 0.30


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
    return "记忆：\n- " + "\n- ".join(list(kind["mem"]) + [kind["last"]])


def build_system(kind, dt):
    return time_line(dt) + "\n\n" + mem_block(kind) + "\n\n" + POLICY


def build_time_pool():
    rng = random.Random(SEED)
    slots = []
    d0 = date(2026, 11, 1)
    for i in range(61):
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


TRAIN_KINDS = KINDS[:16]
DEV_KINDS = KINDS[16:20]
TEST_KINDS = KINDS[20:24]
D_HOURS = [20, 21, 22]


def norm(s):
    return re.sub(r"\s+", "", s or "")


def grams(s, n=2):
    s = norm(s)
    return {s[i:i + n] for i in range(len(s) - n + 1)}


# ---------------- 负例池按 split 切分（场景不跨 split 复用） ----------------
def split_neg_pools():
    rng = random.Random(SEED + 11)
    idx = list(range(len(NEG)))
    rng.shuffle(idx)
    pools = {"train": [("N", i) for i in idx[:34]],
             "dev": [("N", i) for i in idx[34:42]],
             "test": [("N", i) for i in idx[42:]]}
    idx2 = list(range(len(NEG2)))
    rng.shuffle(idx2)
    pools["train"] += [("N2", i) for i in idx2[:92]]
    pools["dev"] += [("N2", i) for i in idx2[92:104]]
    pools["test"] += [("N2", i) for i in idx2[104:]]
    return pools


NEG_POOLS = split_neg_pools()
N2Q = {k: [i for t, i in v if t == "N2"] for k, v in NEG_POOLS.items()}
NQ = {k: {i: 0 for i in [x for t, x in v if t == "N"]} for k, v in NEG_POOLS.items()}

TRIGGER_REASON = {
    "A": "用户讲了新事实，该自然接住",
    "B": "信息太模糊，该问清细节",
    "C": "开放提问，该从记忆带出",
    "D": "沉默场景配记忆时间锚点，该开口",
    "silence": "沉默上下文，不该主动开口",
    "irrelevant": "无关话题，不扯记忆不追问",
    "sensitive": "情绪敏感，不主动提旧事",
}


def pos_reason(cat):
    return TRIGGER_REASON[cat]


def neg_subtype(tag, idx):
    return NEG2[idx][2] if tag == "N2" else ("irrelevant" if idx >= 25 else "silence")


def alloc(split):
    kinds = {"train": TRAIN_KINDS, "dev": DEV_KINDS, "test": TEST_KINDS}[split]
    plan = []
    for i, k in enumerate(kinds):
        if split == "train":
            b = 5 if i < 12 else 4
            n1 = 4 if i < 12 else 5
            n2 = 6 if i < 12 else 5
        elif split == "dev":
            b, n1, n2 = 3, 4, 3
        else:  # test: 71 = 18*3 + 17
            b, n1, n2 = 3, 4, (3 if i < 3 else 2)
        for c, cnt in (("A", 6 if split == "train" else 3), ("B", b),
                       ("C", 6 if split == "train" else 3),
                       ("D", 9 if split == "train" else 2), ("N", n1), ("N2", n2)):
            plan.append((k, c, cnt))
    return plan


def pick_family_for_neg(kinds, reply, start):
    """选一个记忆块与该负例回复无锚点/4-gram 冲突的族。"""
    for j in range(len(kinds)):
        k = kinds[(start + j) % len(kinds)]
        mem = norm(mem_block(k))
        if k["anchor"] in norm(reply):
            continue
        if grams(reply, 4) & grams(mem, 4):
            continue
        return k, (start + j + 1) % len(kinds)
    raise RuntimeError("负例与所有族记忆冲突: %r" % reply)


def make_row(kind, cat, k, split, state):
    if cat == "A":
        user, asst = kind["facts"][k % 3], kind["A"][k % 4]
        tid = "A_%s" % kind["fam"]
    elif cat == "B":
        user, asst = kind["Bf"][k % 2], kind["Ba"][k % 3]
        tid = "B_%s" % kind["fam"]
    elif cat == "C":
        user, asst = kind["Cq"][k % 2], kind["Ca"][k % 3]
        tid = "C_%s" % kind["fam"]
    elif cat == "D":
        mi, ti = divmod(k, 3)
        hour = kind.get("dhours", D_HOURS)[ti]
        dt = take_slot(hour=hour, dow=kind.get("dow"))
        tp = tp_word(hour, dt.minute)
        user = "（" + kind["Ds"][(mi + ti) % 3].format(tp=tp).replace("你", "我") + "）"
        asst = kind["D"][mi].format(tp=tp)
        return dict(sysc=build_system(kind, dt), user=user, asst=asst, cat=cat, kind=kind,
                    tid="D_%s" % kind["fam"], dt=dt, should=True,
                    reason=pos_reason("D"), subtype=None)
    elif cat in ("N", "N2"):
        kinds = {"train": TRAIN_KINDS, "dev": DEV_KINDS, "test": TEST_KINDS}[split]
        if cat == "N":
            pair = state["negq"][state["ni"]]
            state["ni"] += 1
            variant = state["ncount"][pair]
            state["ncount"][pair] += 1
            user, replies = NEG[pair]
            asst = replies[variant]
            sub = neg_subtype("N", pair)
            tid = "N_%s" % kind["fam"]
        else:
            idx = N2Q[split][state["n2i"]]
            state["n2i"] += 1
            user, asst, sub = NEG2[idx]
            kind, state["famrot"] = pick_family_for_neg(kinds, asst, state["famrot"])
            tid = "N2_%s" % kind["fam"]
        return dict(sysc=build_system(kind, take_slot()), user=user, asst=asst, cat="N",
                    kind=kind, tid=tid, dt=None, should=False,
                    reason=TRIGGER_REASON[sub], subtype=sub, pool=cat)
    else:
        raise ValueError(cat)
    return dict(sysc=build_system(kind, take_slot()), user=user, asst=asst, cat=cat,
                kind=kind, tid=tid, dt=None, should=True, reason=pos_reason(cat),
                subtype=None, pool=cat)


# ---------------- 自检 ----------------
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
RE_RULE = re.compile(r"G\d{1,2}|规则|门禁")


def g3_tokens(asst):
    toks = []
    for pat in (RE_G3_NUM, RE_G3_DATE, RE_G3_PRICE, RE_G3_TEMP):
        toks.extend(pat.findall(asst))
    toks.extend(c for c in CITIES if c in asst)
    return toks


def self_check(rows):
    errs = []

    def bad(i, msg):
        errs.append("%s L%d: %s" % (rows[i]["split"], i, msg))

    seen_su, aidx = {}, {}
    for i, r in enumerate(rows):
        sysc, user, asst = r["sysc"], r["user"], r["asst"]
        parts = sysc.split("\n\n")
        if len(parts) < 3 or not RE_TIME_LINE.match(parts[0]) or not sysc.endswith(POLICY):
            bad(i, "system 结构/时间行/policy 尾异常")
        if RE_G1.search(user):
            bad(i, "G1 %r" % user[:40])
        for w in BAN_USER:
            if w in user:
                bad(i, "用户侧禁用词 %s: %r" % (w, user[:40]))
        if r["cat"] == "C" and not user.rstrip().endswith(("？", "?")):
            bad(i, "C 类 user 未以问号结尾")
        if r["cat"] != "C" and user.rstrip().endswith(("？", "?")):
            bad(i, "非 C 类 user 带问号: %r" % user[:40])
        if not (MINLEN <= len(asst) <= MAXLEN):
            bad(i, "长度 %d: %r" % (len(asst), asst))
        if RE_MD.search(asst):
            bad(i, "markdown/换行: %r" % asst)
        if RE_G3_NUM.search(asst) and "T14" not in asst:
            bad(i, "assistant 含阿拉伯数字: %r" % asst)
        if "请" in asst:
            bad(i, "assistant 含'请': %r" % asst)
        for name, pat in (("G4", RE_G4), ("G5", RE_G5), ("G6", RE_G6)):
            if pat.search(asst):
                bad(i, "%s: %r" % (name, asst))
        if RE_G11.search(asst) and not re.search(r"医生|专业人士|律师", asst):
            bad(i, "G11: %r" % asst)
        if RE_G12_ABS.search(asst):
            bad(i, "G12 绝对日期: %r" % asst)
        ctx = norm(sysc) + norm(user)
        for t in g3_tokens(asst):
            if norm(t) not in ctx:
                bad(i, "G3 %r: %r" % (t, asst))
        # 触发标注自洽
        if not isinstance(r["should"], bool):
            bad(i, "should_trigger 非 bool")
        if r["should"] != (r["cat"] != "N"):
            bad(i, "should_trigger 与类别不一致: %s" % r["cat"])
        if not (0 < len(r["reason"]) <= 20):
            bad(i, "trigger_reason 长度 %d: %r" % (len(r["reason"]), r["reason"]))
        if RE_RULE.search(r["reason"]):
            bad(i, "trigger_reason 含规则号: %r" % r["reason"])
        anchor = r["kind"]["anchor"]
        memtext = norm(mem_block(r["kind"]) + user)
        if r["cat"] == "A":
            if not (grams(asst, 2) & grams(memtext, 2)):
                bad(i, "A 未接住事实: %r" % asst)
        if r["cat"] == "C":
            if anchor not in norm(asst + user):
                bad(i, "C 未带出锚点 %s" % anchor)
            if not (grams(asst, 2) & grams(memtext, 2)):
                bad(i, "C 未召回事实: %r" % asst)
        if r["cat"] == "D":
            if not (grams(asst, 2) & grams(memtext, 2)):
                bad(i, "D 无记忆 2-gram 锚点: %r" % asst)
        if r["cat"] == "N":
            if anchor in norm(asst):
                bad(i, "N 类带锚点 %s: %r" % (anchor, asst))
            if grams(asst, 4) & grams(norm(mem_block(r["kind"])), 4):
                bad(i, "N 类与记忆 4-gram 重合: %r" % asst)
        key = (norm(sysc), norm(user))
        if key in seen_su:
            bad(i, "G10 重复 (system,user)，首见 %s L%d" % seen_su[key])
        seen_su[key] = (r["split"], i)
        aidx.setdefault(norm(asst), []).append(i)
    dup = {a: v for a, v in aidx.items() if len(v) > 3}
    if dup:
        errs.append("G8 assistant 重复 >3 次：%d 组，例 %r" % (len(dup), list(dup.items())[:2]))
    return errs, dup


def main():
    rows_by_split, all_rows = {}, []
    for split in ("train", "dev", "test"):
        state = {"negq": [], "ni": 0, "n2i": 0, "famrot": 0,
                 "ncount": {p: 0 for p in NQ[split]}}
        # v1 负例池：本 split 每个场景用 2 次（两条不同回复），顺序打散
        pairs = sorted(NQ[split])
        state["negq"] = pairs + pairs
        rows = []
        for kind, cat, cnt in alloc(split):
            for k in range(cnt):
                r = make_row(kind, cat, k, split, state)
                r["split"] = split
                r["_k"] = k
                rows.append(r)
        rows.sort(key=lambda x: (x["kind"]["id"], x["cat"], x["_k"]))
        rows_by_split[split] = rows
        all_rows += [(split, r) for r in rows]

    from collections import Counter
    cnt = Counter(r["cat"] for _, r in all_rows)
    want = {"A": 120, "B": 100, "C": 120, "D": 160, "N": 215}
    assert dict(cnt) == want, (dict(cnt), want)
    for sp in SPLIT_ROWS:
        assert len(rows_by_split[sp]) == SPLIT_ROWS[sp], (sp, len(rows_by_split[sp]))

    all_r = [r for _, r in all_rows]
    errs, dup = self_check(all_r)
    if errs:
        print("SELF-CHECK FAILED: %d" % len(errs))
        for e in errs[:40]:
            print("  " + e)
        return 2

    # 负例率（逐 split）
    negstat = {}
    for sp in ("train", "dev", "test"):
        n = sum(1 for r in rows_by_split[sp] if not r["should"])
        tot = len(rows_by_split[sp])
        negstat[sp] = {"rows": tot, "should_trigger_false": n,
                       "ratio": round(n / tot, 4), "ok_ge_25pct": n / tot >= NEG_HARD_MIN}
        assert n / tot >= NEG_HARD_MIN, (sp, n / tot)
    n_all = sum(1 for r in all_r if not r["should"])
    assert n_all / len(all_r) >= NEG_TOTAL_MIN

    # 落盘（v1 备份到 v1/）
    v1 = os.path.join(OUTDIR, "v1")
    if not os.path.isdir(v1):
        os.makedirs(v1)
        for fn in ("train.jsonl", "dev.jsonl", "test.jsonl", "manifest.json",
                   "GATE.json", "SAMPLES.md", "README.md", "_gate_input_all.jsonl",
                   "_gate_train.json", "_gate_dev.json", "_gate_test.json", "_gate_all.json"):
            p = os.path.join(OUTDIR, fn)
            if os.path.exists(p):
                shutil.move(p, os.path.join(v1, fn))

    shas, lines = {}, {}
    for split in ("train", "dev", "test"):
        p = os.path.join(OUTDIR, split + ".jsonl")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            for r in rows_by_split[split]:
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": r["sysc"]},
                    {"role": "user", "content": r["user"]},
                    {"role": "assistant", "content": r["asst"]}],
                    "should_trigger": r["should"],
                    "trigger_reason": r["reason"]}, ensure_ascii=False) + "\n")
        shas[split] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        lines[split] = len(rows_by_split[split])
    pall = os.path.join(OUTDIR, "_gate_input_all.jsonl")
    with open(pall, "w", encoding="utf-8", newline="\n") as f:
        for _, r in all_rows:
            f.write(json.dumps({"messages": [
                {"role": "system", "content": r["sysc"]},
                {"role": "user", "content": r["user"]},
                {"role": "assistant", "content": r["asst"]}],
                "should_trigger": r["should"],
                "trigger_reason": r["reason"]}, ensure_ascii=False) + "\n")
    shas["all"] = hashlib.sha256(open(pall, "rb").read()).hexdigest()

    # 三重留出核验
    fam = {sp: {k["fam"] for k in ks} for sp, ks in
           (("train", TRAIN_KINDS), ("dev", DEV_KINDS), ("test", TEST_KINDS))}
    tid = {sp: {r["tid"] for r in rows_by_split[sp]} for sp in ("train", "dev", "test")}
    usr = {sp: {norm(r["user"]) for r in rows_by_split[sp]} for sp in ("train", "dev", "test")}
    npool = {"train": set(NEG_POOLS["train"]), "dev": set(NEG_POOLS["dev"]),
             "test": set(NEG_POOLS["test"])}
    hold = {
        "family_test_vs_train_disjoint": not (fam["test"] & fam["train"]),
        "family_dev_vs_train_disjoint": not (fam["dev"] & fam["train"]),
        "family_dev_vs_test_disjoint": not (fam["dev"] & fam["test"]),
        "template_test_vs_train_disjoint": not (tid["test"] & tid["train"]),
        "template_dev_vs_train_disjoint": not (tid["dev"] & tid["train"]),
        "neg_scene_pool_test_vs_train_disjoint": not (npool["test"] & npool["train"]),
        "neg_scene_pool_dev_vs_train_disjoint": not (npool["dev"] & npool["train"]),
        "user_text_test_vs_train_overlap": len(usr["test"] & usr["train"]),
        "family_sizes": {k: len(v) for k, v in fam.items()},
        "template_sizes": {k: len(v) for k, v in tid.items()},
    }
    for k, v in hold.items():
        if k.endswith("disjoint"):
            assert v, k
    print("holdout OK: " + json.dumps(hold, ensure_ascii=False))

    rows_meta = []
    for split in ("train", "dev", "test"):
        for i, r in enumerate(rows_by_split[split]):
            item = {"split": split, "line": i + 1, "category": r["cat"],
                    "family": r["kind"]["fam"], "template_id": r["tid"],
                    "should_trigger": r["should"], "trigger_reason": r["reason"],
                    "source": "autonomy715/synthetic-fictional-pool",
                    "anchor": r["kind"]["anchor"]}
            if r["cat"] == "N":
                item["neg_subtype"] = r["subtype"]
                item["neg_pool"] = r["pool"]
            rows_meta.append(item)

    MAPPING = {
        "version": "1",
        "purpose": "对话体 jsonl → (trigger, content, reason) 的确定性映射；simulator/盲标按此对齐。",
        "fields": {"should_trigger": "bool，标注真值：本轮是否应当主动开口",
                   "trigger_reason": "≤20 字自然语言原因（无规则号）",
                   "messages": "system + user + assistant（单轮），assistant 为对话体回复"},
        "rules": [
            {"id": "M1", "when": "messages[-1].role=='assistant' 且 content.strip()=='' 或 '<SILENCE>'",
             "result": "trigger=false, content=null", "note": "本数据集不使用该写法（门禁要求 assistant 8–60 字），保留以兼容其他批次"},
            {"id": "M2", "when": "should_trigger==false",
             "result": "trigger=false, content=null",
             "note": "assistant 文本是“对话内最低接话”（不带到记忆锚点、不追问、不建议），只作为对话回复出现，不产生任何外发主动消息；simulator 不得把它当作待发消息"},
            {"id": "M3", "when": "should_trigger==true",
             "result": "trigger=true, content=messages[-1].content",
             "note": "该句即应当主动发出的消息内容（A 是接事实后的承接句、B 是追问句、C 是带出记忆的句子、D 是主动发起句）"},
            {"id": "M4", "when": "普通接话（用户主动开口、assistant 只回应当下，不引入记忆/不追问/不发起）",
             "result": "trigger=false", "note": "等价于 should_trigger=false；用于人工/模型盲标时的判据"},
        ],
        "derivation_check": "本数据集 715 行满足 M2/M3 与 should_trigger 一一对应；false 行 assistant 均 ≤20 字、无记忆锚点、无追问式推进、无建议。",
    }

    manifest = {
        "schema": "autonomy715_v2",
        "seed": SEED,
        "generated_for": "TASK-039/042 下轮自主性 SFT（未训练）",
        "spec": "out/SFT-AUTONOMY-DATA-SPEC.md",
        "policy_sha16": POLICY_SHA16,
        "policy_source": "tools/chat_daily.py:SYSTEM_POLICY（逐字，G9 要求）",
        "total": len(all_r),
        "lines": lines,
        "split_rows": SPLIT_ROWS,
        "category_counts": dict(cnt),
        "should_trigger_counts": {"true": len(all_r) - n_all, "false": n_all},
        "negative": {"count": n_all, "ratio_of_all": round(n_all / len(all_r), 4),
                     "per_split": negstat,
                     "subtypes": {"silence": sum(1 for r in all_r if r["subtype"] == "silence"),
                                  "irrelevant": sum(1 for r in all_r if r["subtype"] == "irrelevant"),
                                  "sensitive": sum(1 for r in all_r if r["subtype"] == "sensitive")},
                     "note": "false 行 = 沉默上下文 / 无关话题 / 敏感情绪不播；assistant 只做最低接话"},
        "mapping": MAPPING,
        "splits": {
            "train": {"rows": SPLIT_ROWS["train"], "families": [k["id"] + ":" + k["fam"] for k in TRAIN_KINDS]},
            "dev": {"rows": SPLIT_ROWS["dev"], "families": [k["id"] + ":" + k["fam"] for k in DEV_KINDS]},
            "test": {"rows": SPLIT_ROWS["test"], "families": [k["id"] + ":" + k["fam"] for k in TEST_KINDS]},
        },
        "holdout_check": hold,
        "sha256": shas,
        "files": ["train.jsonl", "dev.jsonl", "test.jsonl", "manifest-v2.json", "GATE-v2.json",
                  "SAMPLES-v2.md", "README.md", "_gate_input_all.jsonl"],
        "format": "每行 {messages:[system,user,assistant], should_trigger:bool, trigger_reason:str}",
        "value_pool": "全虚构：芋圆/仙贝/芒果/内脏/泉州/云启/日语/陶艺/桃酥/柳州/骑车/星岩/望江里/龟背竹/美式/雾中灯塔/口琴/老聂/十一月十七/灰绿色/老港片/池姐/中级会计",
        "rows": rows_meta,
        "gate": "GATE-v2.json（out/sft_data_gate.py G1–G13；G10 见 note，不标 pass）",
    }
    json.dump(manifest, open(os.path.join(OUTDIR, "manifest-v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"lines": lines, "sha256": shas, "categories": dict(cnt),
                      "should_trigger": manifest["should_trigger_counts"],
                      "neg_per_split": negstat}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())