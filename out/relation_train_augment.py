# -*- coding: utf-8 -*-
"""补 420 条 held-out 风格数据（B 要求：correct +220、new_subject +100、ambiguous +100）。"""
import json, random, hashlib
from collections import Counter

random.seed(20261030)
BASE = "out/relation_train_2k.jsonl"
GOLD = "out/RELATION-GOLD-60.jsonl"
HELD = "out/RELATION-HELDOUT-60.jsonl"
OUT = "out/relation_train_2420.jsonl"

# 值池（与 base 生成器同源，但重新抽样；生成后仍查重）
POOL = {
 "cat": ["奶盖","布丁","麻薯","椰奶","栗子","桃酥","杏仁","海苔","肉松","雪碧","可乐","糯米","芝麻","汤圆","锅贴","豆沙","蛋挞","泡芙","芝士","抹茶"],
 "dog": ["阿黄","灰灰","毛毛","壮壮","妞妞","旺仔","小七","十一","元宝","豆包","馒头","花卷","雪球","皮蛋","来福","旺财","黑豆","大黄","可乐","球球"],
 "seat": ["A座101","B座302","C座501","3层12号","5层08号","7层701","2层205","D座808","6层16号","1层03号"],
 "company": ["云栖科技","星河数据","青柠网络","远山咨询","白鹭传媒","北辰制造","南山教育","东港物流","西岭医疗","中洲建设","海川软件","木棉设计"],
 "hometown": ["南京","西安","成都","杭州","武汉","长沙","合肥","福州","昆明","贵阳","太原","石家庄","南昌","兰州"],
 "car_color": ["白","黑","银","蓝","红","灰","香槟","绿","紫"],
 "car_type": ["SUV","轿车","MPV","两厢车","旅行车","越野车","皮卡","跑车","跨界车"],
 "allergy": ["花粉","海鲜","青霉素","布洛芬","尘螨","芒果","花生","鸡蛋","牛奶","酒精","磺胺"],
 "gym": ["一晚上七点","二晚上八点","三晚上六点","四晚上九点","五晚上七点","六上午九点","日上午十点"],
 "travel": ["北京","上海","广州","成都","杭州","西安","南京","武汉","青岛","厦门","重庆","苏州"],
 "meeting": ["7楼会议室","2楼会议室","三楼洽谈室","五楼大会议室","A座101","B座302","9楼报告厅"],
}

def gen_plate():
    prov = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
    return random.choice(prov) + random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") + "".join(random.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(5))
def gen_phone(): return "1" + random.choice("3456789") + "".join(random.choice("0123456789") for _ in range(9))
def gen_email(): return "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6)) + "@example.com"
def gen_bank(): return "".join(random.choice("0123456789") for _ in range(4))

def val(f):
    if f=="plate": return gen_plate()
    if f=="phone": return gen_phone()
    if f=="email": return gen_email()
    if f=="bank": return gen_bank()
    return random.choice(POOL[f])

# held-out 风格句型（只借句式，不与 held-out 逐字相同）
CORRECT2 = {
 "cat": ["现在喊它{v}。", "登记成{v}了。"],
 "dog": ["现在喊它{v}。", "登记成{v}了。"],
 "plate": ["重新选号了，车牌以{v}为准。", "旧牌停用，登记成{v}。"],
 "phone": ["旧号停用了，重新选号{v}。", "号码迁移到{v}。"],
 "seat": ["工位重排，现在在{v}。", "座位调整到{v}。"],
 "company": ["现在在{v}上班。", "工作单位换成{v}。"] ,
 "hometown": ["户口迁到{v}。", "老家以{v}为准。"],
 "car_color": ["重新喷漆，现在是{v}色。", "车身按{v}色重喷。"],
 "car_type": ["升级到{v}。", "按{v}配。"],
 "email": ["邮箱迁移，以后用{v}。", "按新域名登记成{v}。"],
 "allergy": ["核对过，对{v}过敏。", "过敏原以{v}为准。"],
 "gym": ["计划重排，{v}。", "健身时间调整到{v}。"],
 "travel": ["行程迁移到{v}。", "出差地以{v}为准。"],
 "bank": ["旧卡停用，新卡尾号{v}。", "卡号以{v}为准。"],
 "meeting": ["会议重排到{v}。", "会场以{v}为准。"],
}
NS2 = {
 "cat": "我另一只猫叫{v}", "dog": "我另一条狗叫{v}", "plate": "我另一辆车的车牌是{v}",
 "phone": "我另一个手机号是{v}", "seat": "我另一个工位在{v}", "company": "我兼职在{v}",
 "hometown": "我爱人老家在{v}", "car_color": "我另一辆车是{v}色", "car_type": "我另一辆车是{v}",
 "email": "我工作邮箱是{v}", "allergy": "我孩子对{v}过敏", "gym": "我爱人每周{v}健身",
 "travel": "我同事下周去{v}出差", "bank": "我另一张卡尾号是{v}", "meeting": "周五的会在{v}",
}
AMB2 = [
 "以{v}为准。", "登记成{v}。", "它现在是{v}。", "按{v}算。", "不是{v1}，按{v2}算。",
 "现在喊它{v}。", "这个号{v}。", "实际是{v}。"
]

def main():
    HELDTEXT = open(HELD, encoding="utf-8").read()
    corpus = open(GOLD, encoding="utf-8").read() + "\n" + HELDTEXT
    rows = [json.loads(l) for l in open(BASE, encoding="utf-8")]
    corpus += "\n" + "\n".join(r["old"] + "\n" + r["new"] for r in rows)
    fams = list(CORRECT2)
    add = {"correct": [], "new_subject": [], "ambiguous": []}
    i = 0
    while len(add["correct"]) < 220:
        f = fams[i % len(fams)]; i += 1
        v = val(f)
        if len(v) >= 3 and v in HELDTEXT: continue
        old = random.choice(["我的%s是%s。", "我现在的%s是%s。"]) % (f, v)
        # 用族专属旧句更自然
        old = {"cat":"我的猫叫%s。","dog":"我的狗叫%s。","plate":"我的车牌号是%s。","phone":"我的手机号是%s。","seat":"我的工位在%s。","company":"我在%s上班。","hometown":"我老家在%s。","car_color":"我的车是%s色。","car_type":"我的车是%s。","email":"我的邮箱是%s。","allergy":"我对%s过敏。","gym":"我每周%s健身。","travel":"我下周去%s出差。","bank":"我的银行卡尾号是%s。","meeting":"周三的会在%s。"}[f] % v
        v2 = val(f)
        if (len(v2) >= 3 and v2 in HELDTEXT) or v2 == v: continue
        new = random.choice(CORRECT2[f]).format(v=v2)
        if old in corpus or new in corpus: continue
        add["correct"].append({"old":old,"new":new,"label":"correct","fam":f})
        corpus += "\n" + old + "\n" + new
    i = 0
    while len(add["new_subject"]) < 100:
        f = fams[i % len(fams)]; i += 1
        v1, v2 = val(f), val(f)
        if (len(v1) >= 3 and v1 in HELDTEXT) or (len(v2) >= 3 and v2 in HELDTEXT) or v1 == v2: continue
        old = {"cat":"我的猫叫%s。","dog":"我的狗叫%s。","plate":"我的车牌号是%s。","phone":"我的手机号是%s。","seat":"我的工位在%s。","company":"我在%s上班。","hometown":"我老家在%s。","car_color":"我的车是%s色。","car_type":"我的车是%s。","email":"我的邮箱是%s。","allergy":"我对%s过敏。","gym":"我每周%s健身。","travel":"我下周去%s出差。","bank":"我的银行卡尾号是%s。","meeting":"周三的会在%s。"}[f] % v1
        new = NS2[f].format(v=v2)
        if old in corpus or new in corpus: continue
        add["new_subject"].append({"old":old,"new":new,"label":"new_subject","fam":f})
        corpus += "\n" + old + "\n" + new
    i = 0
    while len(add["ambiguous"]) < 100:
        f = fams[i % len(fams)]; i += 1
        v1, v2 = val(f), val(f)
        if (len(v1) >= 3 and v1 in HELDTEXT) or (len(v2) >= 3 and v2 in HELDTEXT) or v1 == v2: continue
        old = {"cat":"我的猫叫%s。","dog":"我的狗叫%s。","plate":"我的车牌号是%s。","phone":"我的手机号是%s。","seat":"我的工位在%s。","company":"我在%s上班。","hometown":"我老家在%s。","car_color":"我的车是%s色。","car_type":"我的车是%s。","email":"我的邮箱是%s。","allergy":"我对%s过敏。","gym":"我每周%s健身。","travel":"我下周去%s出差。","bank":"我的银行卡尾号是%s。","meeting":"周三的会在%s。"}[f] % v1
        new = random.choice(AMB2).format(v=v2, v1=v1, v2=v2)
        if old in corpus or new in corpus: continue
        add["ambiguous"].append({"old":old,"new":new,"label":"ambiguous","fam":f})
        corpus += "\n" + old + "\n" + new

    allrows = rows + add["correct"] + add["new_subject"] + add["ambiguous"]
    random.shuffle(allrows)
    ntr, ndev = 1616, 202
    train, dev, test = allrows[:ntr], allrows[ntr:ntr+ndev], allrows[ntr+ndev:]
    for path, part in ((OUT, train), ("out/relation_dev_242.jsonl", dev), ("out/relation_test_242.jsonl", test)):
        with open(path, "w", encoding="utf-8") as fh:
            for r in part: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print("total", len(allrows), Counter(r["label"] for r in allrows))
    print("train", len(train), "dev", len(dev), "test", len(test), "sha", h)

if __name__ == "__main__":
    main()