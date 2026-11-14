# -*- coding: utf-8 -*-
"""Build ALIGN-BLIND-40: blind set for answer_alignment (no labels beyond expected).

20 positives: query asks a slot, answer states the correct value, blocks hold it.
20 negatives in three kinds:
  cross_slot   – answer supplies a value from a different slot than asked
  approx_only  – answer supplies a near-miss value (one digit/char off)
  subject_mismatch – query is about person A, answer states person B's value

All entities/numbers/companies are new; nothing reuses the old 40 / P2 / Q40 / S2.
"""
import hashlib
import json
from pathlib import Path

OUT = Path("out/ALIGN-BLIND-40.jsonl")
rows = []


def row(pid, query, answer, blocks, expected, reason, kind):
    rows.append({"id": pid, "query": query, "answer": answer,
                 "blocks": [{"id": i + 1, "text": t} for i, t in enumerate(blocks)],
                 "expected": expected, "reason": reason, "kind": kind})


# ---------------- positives (20) ----------------
P = [
    ("A01", "我的车牌号是多少？", "你的车牌是皖K·3D7F9。", ["我的车牌号是皖K·3D7F9。"], "车牌"),
    ("A02", "我手机号是哪个？", "你的手机号是 195-7700-3312。", ["我的手机号是 195-7700-3312。"], "手机"),
    ("A03", "我目前的就职单位是哪家？", "你在宁德时代新能源科技上班。", ["我在宁德时代新能源科技上班。"], "公司"),
    ("A04", "我家猫叫什么？", "你的猫叫布蕾。", ["我家猫叫布蕾。"], "猫"),
    ("A05", "我的工位在哪？", "你的工位在 7 楼 B 区 12 号。", ["我的工位在 7 楼 B 区 12 号。"], "工位"),
    ("A06", "我的会议几点开？", "你的会议是 2027-01-12 09:45。", ["我的会议是 2027-01-12 09:45。"], "会议时间"),
    ("A07", "我的组会定在什么时候？", "组会定在周四下午三点半。", ["我的组会定在周四下午三点半。"], "时间"),
    ("A08", "我的评审会在哪开？", "评审会在 3 号会议室开。", ["我的评审会在 3 号会议室开。"], "地点"),
    ("A09", "我的工资卡号是多少？", "你的工资卡号是 6225 7712 3344 8890。", ["我的工资卡号是 6225 7712 3344 8890。"], "银行卡"),
    ("A10", "我的工作邮箱是什么？", "你的工作邮箱是 han.xs@corp.example。", ["我的工作邮箱是 han.xs@corp.example。"], "邮箱"),
    ("A11", "我养的狗叫什么？", "你的狗叫铁蛋。", ["我养的狗叫铁蛋。"], "狗"),
    ("A12", "我的座位号是多少？", "你的座位是 12 排 07 号。", ["我的座位号是 12 排 07 号。"], "座位"),
    ("A13", "我老家在哪？", "你老家在江西赣州。", ["我老家在江西赣州。"], "老家"),
    ("A14", "我的车是什么车型？", "你的车是紧凑型 MPV。", ["我的车是紧凑型 MPV。"], "车型"),
    ("A15", "我的车是什么颜色？", "你的车是墨绿色。", ["我的车是墨绿色。"], "车色"),
    ("A16", "我的备用号码是哪个？", "你的备用号是 133-4400-7788。", ["我的备用号是 133-4400-7788。"], "备用号"),
    ("A17", "我的私人号是多少？", "你的私人号是 188-9900-1122。", ["我的私人号是 188-9900-1122。"], "私人号"),
    ("A18", "我周几有组会？", "你每周二有组会。", ["我每周二晚上七点半有组会。"], "组会时间"),
    ("A19", "我下个月去哪出差？", "你下个月去西宁出差。", ["我下个月去西宁出差。"], "出差地点"),
    ("A20", "我对什么过敏？", "你对芒果过敏。", ["我对芒果过敏。"], "过敏"),
]
for pid, q, a, b, slot in P:
    row(pid, q, a, b, "pass", "aligned_value:%s" % slot, "positive")

# ---------------- negatives (20) ----------------
# cross-slot (8): answer gives another slot's value
X = [
    ("N01", "我的保险到期日是哪天？", "你的车牌是皖K·3D7F9。", ["我的车牌号是皖K·3D7F9。"], "cross_slot:车牌"),
    ("N02", "我银行卡的密码是什么？", "你在宁德时代新能源科技上班。", ["我在宁德时代新能源科技上班。"], "cross_slot:公司"),
    ("N03", "我护照号是多少来着？", "你的手机号是 195-7700-3312。", ["我的手机号是 195-7700-3312。"], "cross_slot:手机"),
    ("N04", "我的工牌号是多少？", "你的工位在 7 楼 B 区 12 号。", ["我的工位在 7 楼 B 区 12 号。"], "cross_slot:工位"),
    ("N05", "我的包裹运单号是多少？", "你的工资卡号是 6225 7712 3344 8890。", ["我的工资卡号是 6225 7712 3344 8890。"], "cross_slot:银行卡"),
    ("N06", "我学号是哪个？", "你的工作邮箱是 han.xs@corp.example。", ["我的工作邮箱是 han.xs@corp.example。"], "cross_slot:邮箱"),
    ("N07", "我是什么血型？", "你的猫叫布蕾。", ["我家猫叫布蕾。"], "cross_slot:猫"),
    ("N08", "我车牌是哪一年上的？", "你的车是墨绿色。", ["我的车是墨绿色。"], "cross_slot:车色"),
]
for pid, q, a, b, why in X:
    row(pid, q, a, b, "reject", why, "negative")
# approx-only (6): near-miss values
N = [
    ("N09", "我的车牌号是多少？", "你的车牌是皖K·3D7F8。", ["我的车牌号是皖K·3D7F9。"], "approx_only:车牌差一位"),
    ("N10", "我手机号码多少？", "你的手机号是 195-7700-3313。", ["我的手机号是 195-7700-3312。"], "approx_only:手机尾号差一"),
    ("N11", "我的工资卡号是多少？", "你的工资卡号是 6225 7712 3344 8890 1。", ["我的工资卡号是 6225 7712 3344 8890。"], "approx_only:卡号多一位"),
    ("N12", "我的座位号是多少？", "你的座位是 12 排 70 号。", ["我的座位号是 12 排 07 号。"], "approx_only:数字换位"),
    ("N13", "我的会议几点开？", "你的会议是 2027-01-12 19:45。", ["我的会议是 2027-01-12 09:45。"], "approx_only:同日期异时刻"),
    ("N14", "我现在的公司是哪家？", "你在宁德时代新能源科技有限公司。", ["我在宁德时代新能源科技上班。"], "approx_only:公司名近似但不同"),
]
for pid, q, a, b, why in N:
    row(pid, q, a, b, "reject", why, "negative")
# subject mismatch (6): asks person A, answer states B's value
S = [
    ("N15", "张伟的车牌号是多少？", "阿泽的车牌是京A·88888。", ["阿泽的车牌是京A·88888。"], "subject_mismatch:问张伟答阿泽"),
    ("N16", "张伟的手机号是多少？", "阿泽的手机号是 136-0000-2468。", ["阿泽的手机号是 136-0000-2468。"], "subject_mismatch:问张伟答阿泽"),
    ("N17", "柳如烟在哪家公司上班？", "韩雪松在宁德时代新能源科技上班。", ["韩雪松在宁德时代新能源科技上班。"], "subject_mismatch:问柳如烟答韩雪松"),
    ("N18", "傅思远的猫叫什么？", "柳如烟的猫叫布蕾。", ["柳如烟的猫叫布蕾。"], "subject_mismatch:问傅思远答柳如烟"),
    ("N19", "阿泽的工位在哪？", "张伟的工位在 7 楼 B 区 12 号。", ["张伟的工位在 7 楼 B 区 12 号。"], "subject_mismatch:问阿泽答张伟"),
    ("N20", "邵嘉的座位号是多少？", "白露的座位是 12 排 07 号。", ["白露的座位号是 12 排 07 号。"], "subject_mismatch:问邵嘉答白露"),
]
for pid, q, a, b, why in S:
    row(pid, q, a, b, "reject", why, "negative")

# ---------------- validate ----------------
old = set()
for f in ("out/P1B-HELDOUT-v1.jsonl", "out/P1B-HELDOUT-R2.jsonl",
          "out/P2-HELDOUT-20.jsonl", "out/P2-HELDOUT-20-NEG.jsonl",
          "out/S2-GATE-HELDOUT-20.jsonl", "kvmem/scale40k/n200/queries.jsonl",
          "out/SHADOW-PAIRS-100.jsonl", "out/SHADOW-PAIRS-100-R2.jsonl",
          "out/SHADOW-PAIRS-50-REAL.jsonl"):
    for line in Path(f).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        for k in ("text", "query", "text_a", "text_b"):
            if d.get(k):
                old.add(d[k])
assert len(rows) == 40, len(rows)
overlap = [r["id"] for r in rows if r["query"] in old or r["answer"] in old
           or any(b["text"] in old for b in r["blocks"])]
pos = [r for r in rows if r["expected"] == "pass"]
neg = [r for r in rows if r["expected"] == "reject"]
assert len(pos) == 20 and len(neg) == 20
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
               encoding="utf-8")
print("n", len(rows), "sha", hashlib.sha256(OUT.read_bytes()).hexdigest())
print("overlap", overlap)
print("kinds", {k: sum(1 for r in neg if r["kind"] == "negative" and r["reason"].startswith(k))
                for k in ("cross_slot", "approx_only", "subject_mismatch")})