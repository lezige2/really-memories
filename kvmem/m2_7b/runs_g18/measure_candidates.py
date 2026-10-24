# -*- coding: utf-8 -*-
"""Measure candidate sentences for the third true fact (18 cells = 1 BOS + 17 content).

Read-only: opens the engine, measures P.measure() for each candidate, prints a table.
Writes nothing but this stdout.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P   # noqa: E402

FORBID = ["楼下", "阳台", "绿萝", "小区", "家", "咖啡", "项目", "上线"]

CANDIDATES = [
    "我的雨伞收在书柜旁边，伞骨断了一根还留着。",
    "我把旧毛毯搭在书房那把藤椅上，冬天盖着刚好。",
    "晚上睡不着的时候，我会听一会儿收音机里的评书。",
    "我的雨伞放在书桌边，伞骨断了一根还留着。",
    "我的公交卡一直塞在背包侧袋，出门顺手就摸得到。",
    "我把耳机卷好收进抽屉，线材总是缠成一团。",
    "钥匙串上那把小刀是我自己磨过的，随手能刮纸。",
    "我的保温杯一直放在背包里，随手就能喝到温水。",
    "我把备用眼镜放在抽屉里，取用很方便。",
    "我的耳机线总在口袋深处缠成一团，解开要费点劲。",
    "书桌上那盏旧台灯是我从旧货市场换来的。",
    "我把身份证复印件夹在那本厚词典里，找起来方便。",
    "每次洗完澡我都会把拖鞋摆到门边的垫子上。",
    "我会在包里放一包纸巾，出门时顺手拿一张。",
    "那只搪瓷缸我用了很多年，缸沿磕掉一小块。",
    "我把伞挂在门后的铜钩上，雨天出门顺手就拿。",
    "我的旧书包背带磨断了，用粗线自己缝过一道。",
    "睡前我会把窗帘拉开一条缝，早上好透光。",
    "我习惯把袜子卷成一团塞进鞋里，省地方。",
    "那盆薄荷放在窗台，我隔两天浇一次水。",
    "我的钥匙串上挂着一只旧铜铃，走路会响。",
    "我把过期的报纸叠好放在墙角，攒着卖废纸。",
]


def main():
    eng = P.open_engine()
    try:
        rows = []
        for t in CANDIDATES:
            n = P.measure(eng, t)
            bad = [w for w in FORBID if w in t]
            rows.append((n, t, bad))
            print("n=%-3d content=%-3d forbid=%-24s %s" % (n, n - 1, ",".join(bad) or "-", t))
    finally:
        eng.close()
    hit = [(n, t) for n, t, bad in rows if n == 18 and not bad]
    print()
    print("candidates with exactly 18 cells (1 BOS + 17 content) and no forbidden word: %d"
          % len(hit))
    for n, t in hit:
        print("  %s" % t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
