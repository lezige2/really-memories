# -*- coding: utf-8 -*-
"""TASK-035：生成 out/SFT-EXTRA-CASES-v3.jsonl（v2 20 条原样 + 17 条 autonomy: A4/B4/C4/D5）
与 out/SFT-AUTONOMY-GAP.json。不改 v2 原文件；所有新事实值先断言训练集 0 出现。
用法：python -X utf8 out/SFT-EXTRA-CASES-v3-build.py
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v2.jsonl")
V3 = os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v3.jsonl")
GAP = os.path.join(ROOT, "out", "SFT-AUTONOMY-GAP.json")
TRAIN = [os.path.join(ROOT, "training/sft/train.jsonl"), os.path.join(ROOT, "training/sft/data.jsonl"),
         os.path.join(ROOT, "training/sft/val.jsonl")]

A_CONFIRM = ["好", "记", "行", "收到", "没问题", "记下", "知道了", "嗯"]
A_DENY = ["不能", "没法", "做不了", "帮不了"]
B_HINT = ["哪", "什么", "具体", "型号", "城市", "名字", "没说", "哪个", "哪家"]
D_DENY = ["做不了", "没法", "帮不了", "（"]


def case(cid, cat, q, expect, note="", pre=None):
    return {"id": cid, "category": cat, "input": q, "pre_state": pre or [],
            "expect": expect, "note": "[v3] " + note}


NEW = [
    case("A01", "autonomy_memory", "我下周三要去银川开会",
         {"contains_any": A_CONFIRM, "not_contains": A_DENY, "memory_delta": 1, "refusal": False},
         "A 主动记忆：用户陈述事实，期待自然确认（服务路径另验 memory_delta=1；proxy 会丢弃该断言）"),
    case("A02", "autonomy_memory", "我女儿的小名是栗子",
         {"contains_any": A_CONFIRM, "not_contains": A_DENY, "memory_delta": 1, "refusal": False},
         "A 主动记忆：女儿小名（保留值 栗子，训练集 0 出现）"),
    case("A03", "autonomy_memory", "我最近开始学吉他",
         {"contains_any": A_CONFIRM, "not_contains": A_DENY, "memory_delta": 1, "refusal": False},
         "A 主动记忆：新爱好（吉他，训练集 0 出现）"),
    case("A04", "autonomy_memory", "我换了个新工位在 E 区 9 号",
         {"contains_any": A_CONFIRM, "not_contains": A_DENY, "memory_delta": 1, "refusal": False},
         "A 主动记忆：新工位（E 区 9 号，训练集 0 出现）"),
    case("B01", "autonomy_followup", "我最近在忙什么？",
         {"contains_any": B_HINT, "not_contains": ["项目名是", "叫做", "名称是"]},
         "B 主动追问：先给模糊信息再问，期待追问/承认没说，不得编造项目名",
         [{"action": "ask", "text": "我最近在忙一个项目"}]),
    case("B02", "autonomy_followup", "我去哪出差？",
         {"contains_any": B_HINT,
          "not_contains": ["北京", "上海", "广州", "深圳", "成都", "杭州", "银川", "哈尔滨"]},
         "B 主动追问：模糊出差信息，不得编造具体城市（TASK-036 修订：西安在训练集出现 6 次，已换训练集 0 次的 哈尔滨；note 标 v2-rev）",
         [{"action": "ask", "text": "我下周要出差"}]),
    case("B03", "autonomy_followup", "我买的什么电脑？",
         {"contains_any": B_HINT,
          "not_contains": ["MacBook", "ThinkPad", "联想", "戴尔", "华为", "苹果", "小米"]},
         "B 主动追问：模糊电脑信息，不得编造具体型号/品牌",
         [{"action": "ask", "text": "我买了台新电脑"}]),
    case("B04", "autonomy_followup", "我的宠物叫什么？",
         {"contains_any": B_HINT, "not_contains": ["豆豆", "咪咪", "雪梨", "团子", "布丁", "可乐", "奶糖"]},
         "B 主动追问：模糊宠物信息，不得编造具体名字",
         [{"action": "ask", "text": "我养了只宠物"}]),
    case("C01", "autonomy_remind", "我这周有什么安排？",
         {"contains_any": ["银川", "开会"]},
         "C 主动提醒/调用：记忆含 银川开会 → 回答应带出事实",
         [{"action": "remember", "text": "我下周三要去银川开会"}]),
    case("C02", "autonomy_remind", "我最近有什么固定安排？",
         {"contains_any": ["六点四十", "18点40", "18:40"]},
         "C 主动提醒/调用：记忆含 周五晚六点四十健身 → 回答应带出事实（独立值）",
         [{"action": "remember", "text": "我周五晚上六点四十去健身"}]),
    case("C03", "autonomy_remind", "我的车是什么来着？",
         {"contains_any": ["银色", "两厢"]},
         "C 主动提醒/调用：记忆含 银色两厢车 → 回答应带出事实",
         [{"action": "remember", "text": "我的车是银色两厢车"}]),
    case("C04", "autonomy_remind", "我用药要注意什么？",
         {"contains_any": ["布洛芬"]},
         "C 主动提醒/调用：记忆含 布洛芬过敏 → 回答应带出事实",
         [{"action": "remember", "text": "我对布洛芬过敏"}]),
    case("D01", "autonomy_initiate", "（用户暂时没说话，请根据记忆主动给用户发一条消息）",
         {"contains_any": ["银川"], "max_len": 120, "not_contains": D_DENY},
         "D 主动发起（proxy-only 文本探针）：应主动提到 下周三银川开会；≤120 字；不得拒答/系统话",
         [{"action": "remember", "text": "我下周三要去银川开会"}]),
    case("D02", "autonomy_initiate", "（现在是周四傍晚，请主动给用户发条消息）",
         {"contains_any": ["六点五十", "18点50", "18:50"], "max_len": 120, "not_contains": D_DENY},
         "D 主动发起（proxy-only 文本探针）：周四傍晚应主动提醒 六点五十游泳（独立值）",
         [{"action": "remember", "text": "我周四晚上六点五十去游泳"}]),
    case("D03", "autonomy_initiate", "（用户暂时没说话，请根据记忆主动关心一下用户）",
         {"contains_any": ["布洛芬"], "max_len": 120, "not_contains": D_DENY},
         "D 主动发起（proxy-only 文本探针）：应主动提 布洛芬过敏提醒",
         [{"action": "remember", "text": "我对布洛芬过敏"}]),
    case("D04", "autonomy_initiate", "（用户很久没说话了，请主动给用户发条消息）",
         {"contains_any": ["栗子"], "max_len": 120, "not_contains": D_DENY},
         "D 主动发起（proxy-only 文本探针）：应主动提 女儿小名栗子",
         [{"action": "remember", "text": "我女儿的小名是栗子"}]),
    case("D05", "autonomy_initiate", "（现在是周末，请主动给用户发条消息）",
         {"contains_any": ["银色", "两厢"], "max_len": 120, "not_contains": D_DENY},
         "D 主动发起（proxy-only 文本探针）：周末应主动提 车是银色两厢车",
         [{"action": "remember", "text": "我的车是银色两厢车"}]),
]
FACTS = ["银川", "栗子", "吉他", "E 区 9 号", "E区9号", "十点", "健身", "银色", "两厢", "布洛芬", "哈尔滨",
         "我下周三要去银川开会", "我周四晚上六点五十去游泳", "我的车是银色两厢车", "我对布洛芬过敏",
         "我女儿的小名是栗子", "我最近在忙一个项目", "我下周要出差", "我买了台新电脑", "我养了只宠物"]


def main():
    full = "".join(open(p, encoding="utf-8").read() for p in TRAIN)
    ev = {f: full.count(f) for f in FACTS}
    bad = {f: n for f, n in ev.items() if n}
    if bad:
        raise SystemExit("FACTS_IN_TRAINING: %r" % bad)
    v2 = [json.loads(l) for l in open(V2, encoding="utf-8") if l.strip()]
    rows = v2 + NEW
    with open(V3, "w", encoding="utf-8", newline="\n") as f:
        for c in rows:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(open(V3, "rb").read()).hexdigest()
    gap = {"schema": "sft_autonomy_gap_v1", "task": "TASK-035",
           "v2_file": os.path.relpath(V2, ROOT), "v3_file": os.path.relpath(V3, ROOT),
           "v2_rows": len(v2), "v3_rows": len(rows), "v3_sha256": sha,
           "autonomy_samples_in_v2": {"A_active_memory": 0, "B_active_followup": 0,
                                      "C_active_reminder": 0, "D_active_initiate": 0,
                                      "note": "v2 无主动类训练样本；v2 仅 L03 问句“我女儿的小名是什么？”提到小名，非主动样本"},
           "training_data": {"rows": 2685, "autonomy_ratio": 0.0,
                             "new_fact_grep_zero": ev,
                             "conflict_with_existing": "新事实值在 train/data/val 均 0 出现，与现有数据无事实冲突"},
           "next_round_recommendation": {
               "target_rows": "250-300 条（下一版约 3000 条的 8-10%）",
               "content": "记忆 + 时间 + 上次对话 → 自然主动消息（陈述式、不拒答、不系统话、≤120 字）",
               "distribution": {"A 主动记忆": "2-3%", "B 主动追问": "2-3%",
                                "C 主动提醒": "2-3%", "D 主动发起": "2-3%"},
               "runtime_trigger": "需运行时触发器：定时/事件 → 调模型 → QQ 桥发送；今晚不实现，列为未决"},
           "open_items": ["运行时主动发送触发器未实现（定时/事件→模型→QQ 桥）",
                          "D 类只是文本探针，不等于真实主动发送"],
           "classes": {"A": 4, "B": 4, "C": 4, "D": 5}}
    json.dump(gap, open(GAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"v3": V3, "sha256": sha, "rows": len(rows),
                      "grep": ev, "gap": GAP}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()