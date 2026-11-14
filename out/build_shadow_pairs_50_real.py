# -*- coding: utf-8 -*-
"""Build SHADOW-PAIRS-50-REAL: hand-written conversational (real-tone) pairs.

The QQ bridge log carries only metadata (no message text), so these 50 pairs are
hand-written in spoken style: omissions, particles, anaphora ("那个", "上次那家"),
fragments. All names/numbers/addresses are invented (anonymised).

No labels. Zero overlap with the previous two batches and Q40/S2/P1B/P2.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

OUT = Path("out/SHADOW-PAIRS-50-REAL.jsonl")
rows = []


def add(pid, a, b, source, why):
    rows.append({"pair_id": pid, "text_a": a, "text_b": b,
                 "source": source, "why_candidate": why})


# ---- S: same fact, conversational rewrite (17) ------------------------
S = [
    ("车牌我记的是苏E8L2M6。", "那块牌就是苏E8L2M6，没错。", "同事实·口语确认"),
    ("我手机 186 那个，尾号 4471。", "联系我就打 186 开头的，4471 结尾。", "同事实·分段报号码"),
    ("媳妇老家安徽的。", "我老婆是安徽人。", "同事实·称谓替换（媳妇/老婆）"),
    ("周二上午十点晨会，别忘了。", "晨会还是周二早上十点。", "同事实·语序与语气词"),
    ("我那猫叫团子。", "猫的名字是团子，一直这么叫。", "同事实·补充说明"),
    ("公司在合肥知微。", "单位就是合肥知微那家。", "同事实·公司/单位"),
    ("工资卡招行的。", "发工资那张卡是招商银行。", "同事实·简称展开"),
    ("座位三排十八。", "我坐三排十八号那个位置。", "同事实·补量词"),
    ("评审会十二月三号，上午十点一刻。", "评审定在 12 月 3 日 10:15。", "同事实·数字写法差异"),
    ("我狗叫黑豆。", "家里那条狗，黑豆。", "同事实·倒装省略"),
    ("老家湖南，我爱人那边的。", "爱人老家在湖南。", "同事实·语序调整"),
    ("健身房还是老地方，周三晚八点。", "健身时间周三晚上八点，没变。", "同事实·“还是老地方”"),
    ("我工位 D 座 0702。", "座位在 D 座 0702，靠窗那个。", "同事实·补充描述"),
    ("邮箱 shen@corp.cn，工作用的。", "工作邮箱是 shen@corp.cn。", "同事实·补充槽位"),
    ("车是灰色两厢。", "我那车，灰的两厢。", "同事实·口语省略"),
    ("备用号注销了，别打了。", "那个备用号已经不能用了。", "同事实·注销/不能用"),
    ("会议改到十点半了。", "晨会推迟到十点半。", "同事实·改到/推迟"),
]
for i, (a, b, why) in enumerate(S, 1):
    add("S%03d" % i, a, b, "handwritten:conversational", why)

# ---- D: different fact (16) -------------------------------------------
D = [
    ("我车是灰的。", "我车是蓝的。", "不同取值·颜色"),
    ("周二晨会十点。", "周四周会下午四点。", "不同会议"),
    ("下个月去合肥。", "下下个月去西安。", "不同时间地点"),
    ("猫叫团子。", "狗叫黑豆。", "不同宠物"),
    ("工资卡招行。", "工资卡建行。", "同槽位不同行"),
    ("我工位 A 座 1108。", "我工位 D 座 0702。", "不同工位"),
    ("手机 186 那个。", "座机 010 那个。", "不同号码槽位"),
    ("评审会 12 月 3 号。", "评审会 12 月 8 号。", "同槽位不同日期"),
    ("老家安徽。", "爱人老家湖南。", "不同主体·同为老家"),
    ("我在合肥知微。", "我在西安格物。", "同槽位不同公司"),
    ("座位三排十八。", "座位九排二。", "同槽位不同座位"),
    ("健身周三晚八点。", "健身周六上午十点。", "同槽位不同时间"),
    ("猫叫团子。", "另一只猫叫布丁。", "不同实体·同为猫"),
    ("周一晨会改十点半。", "周四周会不变。", "一改一不变"),
    ("邮箱 shen@corp.cn。", "私人邮箱 shen@home.cn。", "不同邮箱槽位"),
    ("车灰色两厢。", "车蓝色三厢。", "颜色与车型同时不同"),
]
for i, (a, b, why) in enumerate(D, 1):
    add("D%03d" % i, a, b, "handwritten:conversational", why)

# ---- T: traps with real-tone devices (17) ------------------------------
T = [
    ("我车是灰的。", "我媳妇那辆也是灰的。", "多实体·第二辆车同色（指代“那辆”）"),
    ("我车灰色两厢。", "我又弄了一辆，也是灰的两厢。", "多实体·同款不同车"),
    ("牌子换成苏E8L2M6了。", "又添了辆车，牌是苏E8L2M6。", "换牌 vs 新添一辆（cue 撞车）"),
    ("我车牌不是 8L2M6。", "我车牌是 8L2M6。", "否定 vs 肯定"),
    ("那个号我不用了。", "那个号还在用。", "指代+否定（“那个号”）"),
    ("还是上次那家。", "这次换了一家。", "指代（“上次那家”）vs 换"),
    ("车牌 8L2M6。", "车牌 8L2M7。", "数值差一位"),
    ("手机尾号 4471。", "手机尾号 4472。", "数值差一位"),
    ("评审 12 月 3 号上午。", "评审 12 月 3 号晚上。", "同日不同时段"),
    ("评审 12 月 3 号。", "评审明年 12 月 3 号。", "跨年"),
    ("座位三排十八。", "座位三排八十一。", "数字换位（18 vs 81）"),
    ("卡号 6230 8801 4455 2210。", "卡号 6230 8801 4455 2210 7。", "多一位"),
    ("猫叫团子。", "猫不叫团子。", "否定·名字"),
    ("猫叫团子。", "我压根没养猫。", "否定存在"),
    ("我从知微离职了。", "我在知微上班。", "离开句 vs 在职"),
    ("搬出 A 座 1108 了。", "工位还在 A 座 1108。", "搬走 vs 仍在使用"),
    ("那块旧牌我还收着。", "牌子换成新的了。", "持有≠当前值（旧牌还在手）"),
]
for i, (a, b, why) in enumerate(T, 1):
    add("T%03d" % i, a, b, "handwritten:conversational", why)

# ---- validate ---------------------------------------------------------
old = set()
for f in ("out/SHADOW-PAIRS-100.jsonl", "out/SHADOW-PAIRS-100-R2.jsonl",
          "kvmem/scale40k/n200/queries.jsonl", "out/S2-GATE-HELDOUT-20.jsonl",
          "out/P1B-HELDOUT-v1.jsonl", "out/P1B-HELDOUT-R2.jsonl",
          "out/P2-HELDOUT-20.jsonl", "out/P2-HELDOUT-20-NEG.jsonl"):
    for line in Path(f).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        for k in ("text", "query", "text_a", "text_b"):
            if d.get(k):
                old.add(d[k])
assert len(rows) == 50, len(rows)
overlap = [r["pair_id"] for r in rows if r["text_a"] in old or r["text_b"] in old]
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
               encoding="utf-8")
print("n", len(rows), "sha", hashlib.sha256(OUT.read_bytes()).hexdigest())
print("overlap", overlap, "classes", Counter(r["pair_id"][0] for r in rows))
print("has_label", any(k in r for r in rows for k in ("label", "y", "expected")))