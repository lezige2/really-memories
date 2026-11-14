# -*- coding: utf-8 -*-
"""Build 20 adversarial attribute-recency cases (10 phone / 10 fitness).

Each case: 3-4 same-slot values written old->new, expected = the LAST one.
Distractor memories are added so retrieval has noise. expected is frozen into
the JSONL before any run.
"""
import json

PHONES = [
    ["136-1111-3333", "158-0000-2468", "177-2222-9090", "199-3333-1212"],
    ["135-2222-4444", "139-8888-7777", "188-0000-6666"],
    ["137-5555-1212", "150-6666-3434", "186-7777-5656", "133-8888-7878"],
    ["131-4444-9090", "159-5555-1313", "180-6666-3535"],
    ["132-9999-1212", "156-0000-7878", "185-1111-9090", "191-2222-1313"],
    ["134-1212-3434", "157-3434-5656", "189-5656-7878"],
    ["138-0000-0001", "150-0000-0002", "177-0000-0003", "199-0000-0004"],
    ["130-7070-1010", "155-2020-3030", "181-4040-5050"],
    ["133-1234-5678", "158-8765-4321", "186-1357-2468", "199-2468-1357"],
    ["137-3141-5926", "159-2718-2818", "188-4142-1356"],
]
FITNESS = [
    ["周一早上六点", "周三晚上八点", "周二晚上七点四十"],
    ["周日上午九点半", "周五下午四点", "周六早上七点", "周二晚上七点四十"],
    ["周四中午十二点", "周二晚上七点四十"],
    ["周一晚上九点", "周三早上六点半", "周日晚上八点", "周二晚上七点四十"],
    ["周五晚上七点", "周二晚上七点四十"],
    ["周六下午三点", "周一早上五点四十", "周二晚上七点四十"],
    ["周三中午十一点", "周四晚上九点", "周二晚上七点四十"],
    ["周日早上八点", "周二晚上七点四十"],
    ["周一凌晨五点", "周五晚上十点", "周六下午两点", "周二晚上七点四十"],
    ["周三晚上六点", "周二晚上七点四十"],
]
DISTRACT = ["我家猫叫豆豆", "我在宁德时代新能源科技上班", "我的工位是B区7号",
            "我的车是白色SUV", "我的车牌号是京A88888"]

rows = []
for i, vals in enumerate(PHONES, 1):
    pre = [{"action": "remember", "text": "我的手机号是%s" % v} for v in vals]
    for j, d in enumerate(DISTRACT[:3]):
        pre.append({"action": "remember", "text": d})
    pre.append({"action": "ask", "text": "今天忙不忙？"})
    rows.append({"id": "ADV-P%02d" % i, "kind": "phone", "values": vals,
                 "input": "我的手机号是多少？",
                 "expect": {"contains_all": [vals[-1]]}, "pre_state": pre})
for i, vals in enumerate(FITNESS, 1):
    pre = [{"action": "remember", "text": "我的健身时间是%s" % v} for v in vals]
    for d in DISTRACT[2:5]:
        pre.append({"action": "remember", "text": d})
    pre.append({"action": "ask", "text": "晚上有空吗？"})
    rows.append({"id": "ADV-F%02d" % i, "kind": "fitness", "values": vals,
                 "input": "我的健身时间是几点？",
                 "expect": {"contains_all": [vals[-1]]}, "pre_state": pre})

with open("out/POC-ADV20.jsonl", "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("cases", len(rows), "phone", sum(1 for r in rows if r["kind"] == "phone"),
      "fitness", sum(1 for r in rows if r["kind"] == "fitness"))