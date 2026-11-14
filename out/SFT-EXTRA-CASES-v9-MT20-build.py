# -*- coding: utf-8 -*-
"""TASK-085：v9 专项 20 条多轮用例（独立值池，训练集 0 出现）+ out/V9-EVAL-VALUES.json。
M-a：EVAL_DIMS 全部使用训练集 0 次、且不与产品 fixture 保留值冲突的独立值。
M-b：history 交错 (user,assistant,...)，3-8 轮；pre_state 同步 remember 旧/新 + N 轮 ask（service 侧真实多轮）。
输出：out/SFT-EXTRA-CASES-v9-MT20.jsonl、out/V9-EVAL-VALUES.json
用法：python -X utf8 out/SFT-EXTRA-CASES-v9-MT20-build.py
"""
import argparse
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v9-MT20.jsonl")
VALUES = os.path.join(ROOT, "out", "V9-EVAL-VALUES.json")
TURNS = [("你平时喜欢干什么？", "我就记记东西，陪你说说话。"),
         ("今天忙不忙？", "还行，刚忙完一阵。"),
         ("晚上有空吗？", "我随时在，你叫我就行。"),
         ("周末有什么计划吗？", "还没定，你有安排吗？"),
         ("最近在忙什么？", "整理点资料，没啥大事。"),
         ("有什么推荐的放松方式吗？", "听听歌或者出去走走都行。"),
         ("你觉得我记性怎么样？", "你记性还行，重要的都记得。"),
         ("今天几号来着？", "我看下时间再告诉你。")]
# 独立值池（必须训练集 0 出现；不得使用 9 个产品保留值/训练池值）
RESERVED = ["雪梨", "商汤", "闽D74185", "18 号", "18号", "洛阳", "137-0000-9527", "E区9号", "E 区 9 号",
            "布洛芬", "十点", "银川", "银色", "两厢", "7418", "豆豆", "字节跳动"]
EVAL_DIMS = [
    ("猫名", "我养了只猫叫安安", "我的猫名是朵朵", "我养的猫叫什么？", "我的猫叫什么名字？", ["朵朵"], ["安安"]),
    ("健身", "我的健身时间是周日上午九点半", "我的健身时间是周二晚上七点四十",
     "我什么时候去健身？", "我几点去健身？", ["周二晚上七点四十"], ["九点半"]),
    ("手机号", "我的手机号是136-1111-3333", "我的手机号是158-0000-2468",
     "我的手机号是多少？", "我的手机号是什么？", ["158-0000-2468", "15800002468"], ["136-1111-3333"]),
    ("工位", "我的工位是B区7号", "我的工位是C区11号", "我的工位在哪？", "我的工位是哪个？",
     ["C区", "11号"], ["B区", "7号"]),
    ("车牌", "我的车牌号是京N32109", "我的车牌号是津D65432", "我的车牌号是多少？", "我的车牌是什么？",
     ["津D65432", "津D 65432"], ["京N32109"]),
    ("公司", "我的公司是中石油", "我的公司是顺丰", "我在哪家公司上班？", "我的公司叫什么？",
     ["顺丰"], ["中石油"]),
    ("出差地", "我下周三要去宜昌开会", "我下周三要去哈尔滨开会", "我下周三要去哪开会？", "我下周三去哪？",
     ["哈尔滨"], ["宜昌"]),
    ("老家", "我老家在襄阳", "我老家在荆州", "我老家在哪？", "我老家是哪里？",
     ["荆州"], ["襄阳"]),
    ("爱吃", "我最爱吃湘菜", "我最爱吃粤菜", "我最爱吃什么？", "我爱吃什么？",
     ["粤菜"], ["湘菜"]),
    ("女儿小名", "我女儿小名叫果果", "我女儿小名叫米朵", "我女儿的小名是什么？", "我女儿叫什么小名？",
     ["米朵"], ["果果"]),
]
HIST_LENS = [3, 4, 5, 6, 7, 8]
# R3（TASK-091）：时间/数值维度用 contains_all（新值完整要素）+ conflict_if_all（新旧同现才 fail）；not_contains 只用于独特值
EXPECT_FIELDS = {
    "猫名": {"contains_all": ["朵朵"], "conflict_if_all": []},
    "健身": {"contains_all": ["周二晚上七点四十"], "conflict_if_all": [["周日上午九点半", "周二晚上七点四十"]]},
    "手机号": {"contains_all": ["158-0000-2468"], "conflict_if_all": [["136-1111-3333", "158-0000-2468"]]},
    "工位": {"contains_all": ["C区", "11号"], "conflict_if_all": []},
    "车牌": {"contains_all": ["津D65432"], "conflict_if_all": []},
    "公司": {"contains_all": ["顺丰"], "conflict_if_all": []},
    "出差地": {"contains_all": ["哈尔滨"], "conflict_if_all": []},
    "老家": {"contains_all": ["荆州"], "conflict_if_all": []},
    "爱吃": {"contains_all": ["粤菜"], "conflict_if_all": []},
    "女儿小名": {"contains_all": ["米朵"], "conflict_if_all": []},
}
TIME_OR_NUM = {"健身", "手机号"}


def train_files():
    return sorted(glob.glob(os.path.join(ROOT, "training", "sft", "*.jsonl")))


def train_blob():
    return "".join(open(f, encoding="utf-8", errors="replace").read() for f in train_files())


def load_cases(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if os.path.isfile(path) else []


def values_from_cases(cases):
    out = {}
    for c in cases:
        cid, src = c.get("id"), os.path.basename(c.get("_source", ""))
        for v in ((c.get("expect") or {}).get("contains_any") or []):
            out.setdefault(str(v), []).append({"source": src, "id": cid, "kind": "expect"})
        for v in ((c.get("expect") or {}).get("not_contains") or []):
            out.setdefault(str(v), []).append({"source": src, "id": cid, "kind": "not_contains"})
        for act in c.get("pre_state") or []:
            if act.get("action") == "remember" and act.get("text"):
                out.setdefault("MEM:" + str(act["text"]), []).append({"source": src, "id": cid, "kind": "remember"})
    return out


def assert_history(rows):
    """S2：history 必须偶数长度且严格 user,assistant 交替。"""
    for r in rows:
        h = r.get("history") or []
        assert len(h) % 2 == 0, "history 长度非偶数：%s" % r.get("id")
        roles = [str(x.get("role")) for x in h]
        assert roles == ["user", "assistant"] * (len(h) // 2), \
            "history 非严格交替 user/assistant：%s" % r.get("id")
        assert len(h) // 2 in (3, 4, 5, 6, 7, 8), "history 轮数不在 3-8：%s" % r.get("id")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="只校验现有 MT20（不覆盖文件）")
    args = ap.parse_args()
    if args.check_only:
        rows = [json.loads(l) for l in open(DST, encoding="utf-8") if l.strip()]
        assert_history(rows)
        sha = hashlib.sha256(open(DST, "rb").read()).hexdigest()
        print(json.dumps({"check_only": True, "file": DST, "rows": len(rows),
                          "sha16": sha[:16], "assert_history": "ok"}, ensure_ascii=False))
        return
    blob = train_blob()
    bad = []
    for dim, old, new, *_ in EVAL_DIMS:
        for val in re.split(r"[，。！？、\s]+", old + " " + new):
            if len(val) < 2:
                continue
            if blob.count(val):
                bad.append((dim, val, blob.count(val)))
            for r in RESERVED:
                if r in val:
                    bad.append((dim, val, "RESERVED:" + r))
    for dim, fields in EXPECT_FIELDS.items():
        for v in fields["contains_all"] + [x for pair in fields["conflict_if_all"] for x in pair]:
            if len(v) >= 2 and blob.count(v):
                bad.append((dim, "expect-field", v, blob.count(v)))
    if bad:
        raise SystemExit("EVAL_DIMS_CONTAMINATED: %r" % bad)
    rows, sources = [], {}
    idx = 0
    for dim, old, new, qa, qb, exp, bad_vals in EVAL_DIMS:
        for q in (qa, qb):
            idx += 1
            n = HIST_LENS[(idx - 1) % len(HIST_LENS)]
            turns = TURNS[:n]
            pre = [{"action": "remember", "text": old}, {"action": "remember", "text": new}]
            pre += [{"action": "ask", "text": u} for u, _ in turns]
            rows.append({
                "id": "V9MT%02d" % idx, "category": "multi_turn_memory", "input": q,
                "history": [x for u, a in turns for x in ({"role": "user", "content": u},
                                                          {"role": "assistant", "content": a})],
                "pre_state": pre,
                "expect": {"contains_any": exp,
                           "not_contains": [] if dim in TIME_OR_NUM else bad_vals,
                           "contains_all": EXPECT_FIELDS[dim]["contains_all"],
                           "conflict_if_all": EXPECT_FIELDS[dim]["conflict_if_all"],
                           "refusal": False},
                "note": "[v9-MT] 维度 %s：%d 轮闲聊+最后提问；上下文旧事实「%s」→新事实「%s」，"
                        "expect 最新值、not_contains 旧值（独立值池，训练集 0 出现）" % (dim, n, old, new)})
            for v in exp:
                sources.setdefault(str(v), []).append({"source": os.path.basename(DST),
                                                       "id": "V9MT%02d" % idx, "kind": "expect_new"})
            for v in bad_vals:
                sources.setdefault(str(v), []).append({"source": os.path.basename(DST),
                                                       "id": "V9MT%02d" % idx, "kind": "old_not_contains"})
    assert_history(rows)
    with open(DST, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # 全量 fixture 值收集（81/heldout/extra v2/v3/v3-dempty/MT20），供 C 机械断言
    import importlib.util
    spec = importlib.util.spec_from_file_location("rh_v", os.path.join(ROOT, "training/heldout/run_heldout.py"))
    rh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rh)
    fixtures = {}
    cs = load_cases(os.path.join(ROOT, "training", "dialog_cases.jsonl"))
    for c in cs:
        c["_source"] = "dialog_cases.jsonl"
    fixtures.update(values_from_cases(cs))
    fixtures.update(values_from_cases([dict(c, _source="run_heldout.py:CASES") for c in rh.CASES]))
    for name in ("SFT-EXTRA-CASES-v2.jsonl", "SFT-EXTRA-CASES-v3.jsonl", "SFT-EXTRA-CASES-v3-dempty.jsonl"):
        cs = load_cases(os.path.join(ROOT, "out", name))
        for c in cs:
            c["_source"] = name
        fixtures.update(values_from_cases(cs))
    for c in rows:
        c["_source"] = os.path.basename(DST)
    fixtures.update(values_from_cases(rows))
    overlap_train = {v: blob.count(v) for v in sources if blob.count(v)}
    overlap_reserved = {v: r for v in sources for r in RESERVED if r in v}
    evidence = {"schema": "v9_eval_values_v1", "task": "TASK-085",
                "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "train_blob": {"files": [os.path.basename(f) for f in train_files()],
                               "bytes": len(blob.encode("utf-8")),
                               "sha16": hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]},
                "eval_values_independent": sources,
                "fixture_values": fixtures,
                "assertions": {"independent_values_n": len(sources),
                               "independent_vs_train_blob": overlap_train,
                               "independent_vs_reserved": overlap_reserved,
                               "pass": not overlap_train and not overlap_reserved},
                "mt20": {"path": os.path.basename(DST), "rows": len(rows),
                         "sha256": hashlib.sha256(open(DST, "rb").read()).hexdigest(),
                         "sha16": hashlib.sha256(open(DST, "rb").read()).hexdigest()[:16],
                         "history_lens_distinct": sorted({HIST_LENS[i % len(HIST_LENS)] for i in range(len(rows))})}}
    json.dump(evidence, open(VALUES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not (not overlap_train and not overlap_reserved):
        raise SystemExit("EVAL_VALUES_ASSERT_FAIL: %r" % evidence["assertions"])
    print(json.dumps({"mt20": evidence["mt20"], "values_file": VALUES,
                      "independent_values_n": len(sources),
                      "train_blob_sha16": evidence["train_blob"]["sha16"],
                      "assert_pass": evidence["assertions"]["pass"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()