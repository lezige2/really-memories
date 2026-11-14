# -*- coding: utf-8 -*-
"""生成 2k 关系判定训练数据（合成；值与 gold/held-out 程序化查重）。"""
import json, random, re, hashlib, sys

random.seed(20261029)
GOLD = "out/RELATION-GOLD-60.jsonl"
HELD = "out/RELATION-HELDOUT-60.jsonl"
OUT = "out/relation_train_2k.jsonl"

FAM = {
 "cat":   ("我的猫叫{v}", "我的猫现在叫{v}", "我另一只猫叫{v}", ["团团","球球","年糕","花卷","奶糖","布丁","芝麻","汤圆","锅贴","麻薯","豆沙","椰奶","栗子","糯米","桃酥","杏仁","海苔","肉松","雪碧","可乐"]),
 "dog":   ("我的狗叫{v}", "我的狗现在叫{v}", "我另一条狗叫{v}", ["大黄","黑豆","旺财","来福","可乐","雪球","皮蛋","馒头","花卷","豆包","阿黄","灰灰","毛毛","球球","壮壮","妞妞","旺仔","小七","十一","元宝"]),
 "plate": ("我的车牌号是{v}", "我的车牌号现在换成{v}", "我另一辆车的车牌是{v}", None),
 "phone": ("我的手机号是{v}", "我的手机号现在改成{v}", "我另一个手机号是{v}", None),
 "seat":  ("我的工位在{v}", "我的工位现在搬到{v}", "我另一个工位在{v}", ["A座101","B座302","C座501","3层12号","5层08号","7层701","2层205","D座808","6层16号","1层03号"]),
 "company": ("我在{v}上班", "我现在在{v}上班", "我兼职在{v}", ["云栖科技","星河数据","青柠网络","远山咨询","白鹭传媒","北辰制造","南山教育","东港物流","西岭医疗","中洲建设"]),
 "hometown": ("我老家在{v}", "我老家其实是{v}", "我爱人老家在{v}", ["南京","西安","成都","杭州","武汉","长沙","合肥","福州","昆明","贵阳","太原","石家庄"]),
 "car_color": ("我的车是{v}色", "我的车现在是{v}色", "我另一辆车是{v}色", ["白","黑","银","蓝","红","灰","香槟","绿"]),
 "car_type": ("我的车是{v}", "我的车现在换成{v}", "我另一辆车是{v}", ["SUV","轿车","MPV","两厢车","旅行车","越野车","皮卡","跑车"]),
 "email": ("我的邮箱是{v}", "我的邮箱现在改成{v}", "我工作邮箱是{v}", None),
 "allergy": ("我对{v}过敏", "我其实对{v}过敏", "我孩子对{v}过敏", ["花粉","海鲜","青霉素","布洛芬","尘螨","芒果","花生","鸡蛋","牛奶","酒精"]),
 "gym": ("我每周{v}健身", "我现在每周{v}健身", "我爱人每周{v}健身", ["一晚上七点","二晚上八点","三晚上六点","四晚上九点","五晚上七点","六上午九点","日上午十点"]),
 "travel": ("我下周去{v}出差", "我下周改去{v}出差", "我同事下周去{v}出差", ["北京","上海","广州","成都","杭州","西安","南京","武汉","青岛","厦门"]),
 "bank": ("我的银行卡尾号是{v}", "我的银行卡尾号现在是{v}", "我另一张卡尾号是{v}", None),
 "meeting": ("周三的会在{v}", "周三的会现在改到{v}", "周五的会在{v}", ["7楼会议室","2楼会议室","三楼洽谈室","五楼大会议室","A座101","B座302"]),
}

def gen_plate():
    prov = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return random.choice(prov) + random.choice(letters) + "".join(random.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(5))

def gen_phone():
    return "1" + random.choice("3456789") + "".join(random.choice("0123456789") for _ in range(9))

def gen_email():
    a = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6))
    return f"{a}@example.com"

def gen_bank():
    return "".join(random.choice("0123456789") for _ in range(4))

def value(fam):
    t = FAM[fam][3]
    if fam == "plate": return gen_plate()
    if fam == "phone": return gen_phone()
    if fam == "email": return gen_email()
    if fam == "bank": return gen_bank()
    return random.choice(t)

def corpus():
    s = []
    for p in (GOLD, HELD):
        s.append(open(p, encoding="utf-8").read())
    return "\n".join(s)

def main():
    C = corpus()
    rows = []
    per = 2000 // 3
    fams = list(FAM)
    idx = 0
    while len(rows) < 2000:
        fam = fams[idx % len(fams)]; idx += 1
        kind = ["correct", "new_subject", "ambiguous"][len(rows) % 3]
        v1, v2 = value(fam), value(fam)
        if v1 == v2: v2 = v2 + "X"
        old_t, new_t, other_t, _ = FAM[fam]
        if kind == "correct":
            old, new = old_t.format(v=v1), new_t.format(v=v2)
        elif kind == "new_subject":
            old, new = old_t.format(v=v1), other_t.format(v=v2)
        else:
            style = random.choice(["bare", "pronoun", "two", "neg", "same"])
            if style == "bare":
                old, new = old_t.format(v=v1), f"{v2}。"
            elif style == "pronoun":
                old, new = old_t.format(v=v1), f"它现在是{v2}。"
            elif style == "two":
                old, new = old_t.format(v=v1), f"我另一个是{v2}，之前那个是{v1}。"
            elif style == "neg":
                old, new = old_t.format(v=v1), f"不是{v1}，是{v2}。"
            else:
                old, new = old_t.format(v=v1), old_t.format(v=v1)
        # 程序化查重：整句不得出现在 gold/held-out 语料；值不得是语料子串
        if old in C or new in C: continue
        if v1 in C or v2 in C: continue
        rows.append({"old": old, "new": new, "label": kind, "fam": fam})

    random.shuffle(rows)
    n = len(rows); ntr = 1600; ndev = 200
    train, dev, test = rows[:ntr], rows[ntr:ntr+ndev], rows[ntr+ndev:]
    with open(OUT, "w", encoding="utf-8") as f:
        for r in train: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open("out/relation_dev_200.jsonl", "w", encoding="utf-8") as f:
        for r in dev: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open("out/relation_test_200.jsonl", "w", encoding="utf-8") as f:
        for r in test: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    from collections import Counter
    print("rows", n, Counter(r["label"] for r in rows), "fams", len(set(r["fam"] for r in rows)))
    print("train", len(train), "dev", len(dev), "test", len(test), "sha", h)

if __name__ == "__main__":
    main()