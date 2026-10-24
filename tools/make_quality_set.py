# -*- coding: utf-8 -*-
"""Generate the "A" experiment corpus: a long Chinese document with 20 planted facts,
plus the 20 questions that target them, at a chosen length.

Why generated instead of hand-written:
  * the facts must be *only* in the document and nowhere in the prompt (that is the
    whole point of the KV-memory test);
  * each fact has to land at a known position so we can measure position sensitivity;
  * it has to be reproducible (fixed seed) and re-sizable without re-authoring.

Output (all UTF-8, no BOM, LF):
  tools/quality/doc[_<tag>].txt   the document
  tools/quality/qa[_<tag>].tsv    id <TAB> question <TAB> expected answer
  tools/quality/meta[_<tag>].tsv  id <TAB> char offset <TAB> segment index

Usage:
  python tools/make_quality_set.py                       # 5k tokens
  python tools/make_quality_set.py --target-chars 28000 --tag 20k
  python tools/make_quality_set.py --target-chars 138000 --tag 100k
"""

import argparse
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "quality")

# (fact sentence placed in the document, question, expected short answer)
FACTS = [
    ("他的工号是 A-4417。", "林知远的工号是多少？", "A-4417"),
    ("他是 2019 年 7 月正式入职的。", "林知远是哪一年入职的？", "2019"),
    ("他每天早上固定在「三点半」买一杯美式。", "林知远每天早上在哪家店买咖啡？", "三点半"),
    ("他开的是一辆灰色的沃尔沃 XC40。", "林知远开的是什么车？", "XC40"),
    ("家里那只橘猫叫年糕。", "林知远家的猫叫什么名字？", "年糕"),
    ("他出生在泉州，后来才搬到杭州。", "林知远出生在哪个城市？", "泉州"),
    ("他现在挂在供应链分析组。", "林知远在哪个部门？", "供应链分析组"),
    ("每周三的例会固定在 7 楼西侧会议室。", "林知远每周三的例会在哪个会议室？", "7 楼西侧"),
    ("上次体检他的血压是 128/82。", "林知远上次体检的血压是多少？", "128/82"),
    ("女儿的生日是 3 月 9 日。", "林知远女儿的生日是哪天？", "3 月 9 日"),
    ("他对花粉过敏，常备氯雷他定。", "林知远对花粉过敏常吃哪种药？", "氯雷他定"),
    ("去年出差最多的城市是青岛。", "林知远去年出差最多的城市是哪里？", "青岛"),
    ("新换的门锁密码是 0527。", "林知远家的门锁密码是多少？", "0527"),
    ("本科读的是厦门大学。", "林知远本科读的是哪所大学？", "厦门大学"),
    ("专业是高分子材料。", "林知远的专业是什么？", "高分子材料"),
    ("第一份工作在宁波的一家模具厂。", "林知远的第一份工作在哪个城市？", "宁波"),
    ("手机尾号是 9031。", "林知远的手机尾号是多少？", "9031"),
    ("现在住的房子月租 4200 元。", "林知远的房子月租多少？", "4200"),
    ("健身教练姓魏，大家都叫他老魏。", "林知远的健身教练叫什么？", "老魏"),
    ("他常去的那家书店叫琥珀书店。", "林知远常去的书店叫什么？", "琥珀书店"),
]

# Combinatorial filler. A hand-written pool of 40 sentences is fine for 5k tokens but
# turns into the same paragraph 170 times at 100k, which would be an unrealistically
# repetitive document. Composing time + actor + action + detail gives >20k distinct
# sentences with no Arabic digits and none of the answer strings.
TIME = ["早上", "上午", "中午", "下午", "傍晚", "晚上", "深夜", "周一", "周三", "周末",
        "月底", "月初", "年初", "入秋之后", "降温那天", "下雨的那天", "出差回来", "搬家之后"]
WHO  = ["他", "同事", "家人", "朋友", "楼下的邻居", "行政", "客户", "师傅", "老板", "他自己"]
ACT  = ["整理资料", "核对单据", "改了一版方案", "去超市补货", "在楼下等车", "把阳台收拾了一遍",
        "给花浇水", "翻了两页书", "把旧照片归档", "试了家新开的店", "走了很远的路",
        "把车送去保养", "重新排了一遍日程", "把仓库的货点了一遍", "把邮件回完了"]
DET  = ["花了大概一个小时", "中间接了两个电话", "后来发现少了一页", "顺便买了点水果",
        "一直忙到天黑", "比预想的顺利", "结果还是拖到第二天", "弄得一身灰",
        "没花什么钱", "改了三次才定下来", "走的时候忘了关灯", "回头又补了一遍"]

SEED_FILLER = [
    "那天下午他在办公室整理上一季度的报表，窗外的雨下得不大，一直拖到傍晚才停。",
    "同事说楼下新开了一家面馆，味道一般，胜在便宜，中午排队的人不少。",
    "早会开到九点半才散，议题从排期一直绕到空调温度，最后也没形成结论。",
    "他把待办清单重新抄了一遍，划掉几条，又添上几条，心里才稍微踏实一点。",
    "地铁上人挤人，他站在车门边上，把手机里存的长文看完了大半。",
    "周末陪家人去了趟郊外的湿地公园，水边的芦苇刚抽出新穗，风一吹沙沙作响。",
    "晚饭做了番茄炒蛋和清炒菜心，火候有点过，家人还是吃完了。",
    "阳台上那盆薄荷长疯了，他剪了一大把，晾在窗台上准备泡水喝。",
]


def make_filler(rng, seg_index, count):
    """Return `count` filler sentences that vary by segment (no digits, no answers)."""
    out = []
    for i in range(count):
        r = rng.random()
        if r < 0.75:
            s = "%s%s%s，%s。" % (rng.choice(TIME), rng.choice(WHO),
                                 rng.choice(ACT), rng.choice(DET))
        else:
            s = rng.choice(SEED_FILLER)
        out.append(s)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-chars", type=int, default=7500,
                    help="approximate number of Chinese characters in the document")
    ap.add_argument("--tag", default="", help="suffix for the output files, e.g. 20k")
    ap.add_argument("--seed", type=int, default=20261024)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(OUT, exist_ok=True)
    suffix = ("_" + args.tag) if args.tag else ""

    n_seg = len(FACTS)
    per_seg = max(120, args.target_chars // n_seg)

    # Shuffle which fact goes into which segment, so "fact index" is decorrelated
    # from "document position" -- otherwise a position effect could be mistaken
    # for an easy/hard-question effect.
    order = list(range(n_seg))
    rng.shuffle(order)

    paragraphs = []
    meta = []
    offset = 0

    for seg in range(n_seg):
        fact_i = order[seg]
        fact_sentence, question, expected = FACTS[fact_i]

        body = []
        cur = 0
        head_target = int(per_seg * rng.uniform(0.45, 0.8))

        while cur < head_target:
            s = make_filler(rng, seg, 1)[0]
            body.append(s)
            cur += len(s)
        body.append(fact_sentence)
        cur += len(fact_sentence)
        while cur < per_seg:
            s = make_filler(rng, seg, 1)[0]
            body.append(s)
            cur += len(s)

        text = "".join(body)
        fact_off = offset + text.find(fact_sentence)
        meta.append((seg, fact_off, seg))
        paragraphs.append(text)
        offset += len(text) + 2

    doc = "\n\n".join(paragraphs) + "\n"

    with open(os.path.join(OUT, "doc%s.txt" % suffix), "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)

    with open(os.path.join(OUT, "qa%s.tsv" % suffix), "w", encoding="utf-8", newline="\n") as f:
        for seg, fact_i in enumerate(order):
            _, question, expected = FACTS[fact_i]
            f.write("%d\t%s\t%s\n" % (seg, question, expected))

    with open(os.path.join(OUT, "meta%s.tsv" % suffix), "w", encoding="utf-8", newline="\n") as f:
        f.write("# id\tchar_offset\tband\n")
        for seg, off, band in meta:
            f.write("%d\t%d\t%d\n" % (seg, off, band))

    print("doc chars   = %d  ->  doc%s.txt" % (len(doc), suffix))
    print("paragraphs  = %d" % len(paragraphs))
    print("questions   = %d" % len(FACTS))


if __name__ == "__main__":
    main()