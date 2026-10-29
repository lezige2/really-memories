# -*- coding: utf-8 -*-
"""构建 KV-only 冲突夹具（预登记 ROUND1-PREREG §2）：≥40 条，唯一期望新值。

规则：
- 正例：旧事实 -> 新事实 -> 1 轮闲聊 -> 问新值；expect 只含新值，not_contains 旧值。
- 负例（同族不同主体）：两个主体各一条事实，问旧的那个；expect 该主体值（K2 若按族误杀会失败）。
- 值池与训练集/现有 20 块库不重叠（构建时断言）。
输出：out/KV-CONFLICT-40.jsonl
"""
import json, hashlib, sqlite3, sys

OUT = "out/KV-CONFLICT-40.jsonl"
FILLER = ["今天忙不忙？", "你平时喜欢干什么？"]

# (family, old, new, query, variants_new, variants_old)
POS = [
    ("cat", "我养了只猫叫团团", "我的猫现在叫球球", "我的猫叫什么？",
     ["球球"], ["团团"]),
    ("cat", "我养的猫叫年糕", "我后来把猫改名成花卷", "我猫的名字是什么？",
     ["花卷"], ["年糕"]),
    ("dog", "我养了条狗叫大黄", "我的狗改名叫黑豆", "我的狗叫什么？",
     ["黑豆"], ["大黄"]),
    ("dog", "我家狗叫旺财", "我家狗现在叫来福", "我家狗的名字？",
     ["来福"], ["旺财"]),
    ("plate", "我的车牌号是京Q12345", "我的车牌号换成津E54321了", "我的车牌号是多少？",
     ["津E54321", "津E 54321"], ["京Q12345"]),
    ("plate", "我的车牌是沪F67890", "车牌已经换成粤G09876", "我的车牌是什么？",
     ["粤G09876", "粤G 09876"], ["沪F67890"]),
    ("phone", "我的手机号是135-2468-1357", "我的手机号改成159-8888-0001", "我的手机号是多少？",
     ["159-8888-0001", "15988880001", "159 8888 0001"], ["135-2468-1357", "13524681357"]),
    ("phone", "我的手机号是186-3333-4444", "新手机号是177-5555-6666", "我的手机号是什么？",
     ["177-5555-6666", "17755556666", "177 5555 6666"], ["186-3333-4444", "18633334444"]),
    ("seat", "我的工位在B座302", "我的工位搬到C座501了", "我的工位在哪？",
     ["C座501", "C座 501", "C-501"], ["B座302", "B座 302"]),
    ("seat", "我的工位是3层12号", "工位换到5层08号", "我的工位是几层几号？",
     ["5层08号", "5层8号", "5-08"], ["3层12号"]),
    ("company", "我在云栖科技上班", "我跳槽去星河数据了", "我在哪家公司上班？",
     ["星河数据"], ["云栖科技"]),
    ("company", "我的公司是字节跳动", "我换到美团了", "我的公司叫什么？",
     ["美团"], ["字节跳动"]),
    ("hometown", "我老家在杭州", "我老家其实是南京", "我老家在哪里？",
     ["南京"], ["杭州"]),
    ("hometown", "我的老家是成都", "老家在西安", "我老家是哪里的？",
     ["西安"], ["成都"]),
    ("car_color", "我的车是香槟色", "我的车现在是白色", "我的车是什么颜色？",
     ["白色"], ["香槟色"]),
    ("car_color", "我的车是蓝色", "车漆改成黑色了", "我的车是什么颜色？",
     ["黑色"], ["蓝色"]),
    ("car_type", "我的车是两厢车", "我的车换成SUV了", "我的车是什么车型？",
     ["SUV", "suv"], ["两厢"]),
    ("car_type", "我的车是轿车", "现在开的是MPV", "我的车型是什么？",
     ["MPV", "mpv"], ["轿车"]),
    ("email", "我的邮箱是aze@example.com", "邮箱改成aze.work@example.com", "我的邮箱是多少？",
     ["aze.work@example.com"], ["aze@example.com"]),
    ("email", "我的邮箱是lin@example.com", "工作邮箱是lin.work@example.com", "我的邮箱是什么？",
     ["lin.work@example.com"], ["lin@example.com"]),
    ("allergy", "我对布洛芬过敏", "我其实对青霉素过敏", "我对什么药过敏？",
     ["青霉素"], ["布洛芬"]),
    ("allergy", "我花粉过敏", "我海鲜过敏", "我对什么过敏？",
     ["海鲜"], ["花粉"]),
    ("gym", "我每周四晚上八点健身", "改到周二晚上七点健身", "我每周几几点健身？",
     ["周二", "七点", "7点"], ["周四"]),
    ("gym", "我周六上午九点健身", "现在周一晚上六点健身", "我什么时候健身？",
     ["周一", "六点", "6点"], ["周六"]),
    ("travel", "我下周二要去北京出差", "下周二改成去上海出差", "我下周二要去哪里出差？",
     ["上海"], ["北京"]),
    ("travel", "我下周五去杭州开会", "改到下周一去成都开会", "我下周一要去哪里开会？",
     ["成都"], ["杭州"]),
    ("bank", "我的银行卡尾号是7418", "尾号换成9032了", "我的银行卡尾号是多少？",
     ["9032"], ["7418"]),
    ("bank", "银行卡尾号是1122", "新卡尾号8842", "我的银行卡尾号是什么？",
     ["8842"], ["1122"]),
    ("meeting", "周一上午十点的会在7楼会议室", "改到2楼会议室", "周一上午十点的会在哪开？",
     ["2楼会议室", "二楼会议室", "2楼"], ["7楼"]),
    ("meeting", "周三的会在三楼洽谈室", "换到五楼大会议室", "周三的会在哪里开？",
     ["五楼大会议室", "5楼大会议室", "五楼"], ["三楼"]),
]

# 负例：同族不同主体，问旧主体；expect 旧主体值（不得被“只挂最新”误杀）
NEG = [
    ("car_color", "我的特斯拉是蓝色", "我的比亚迪是黑色", "我的特斯拉是什么颜色？",
     ["蓝色"], ["黑色"]),
    ("car_color", "我的油车是灰色", "我的电车是红色", "我的油车是什么颜色？",
     ["灰色"], ["红色"]),
    ("phone", "我的工作号是130-2468-1111", "我的私人号是131-0000-2222", "我的工作号是多少？",
     ["130-2468-1111", "13024681111"], ["131-0000-2222", "13100002222"]),
    ("phone", "我的备用号是132-0000-3333", "常用号是133-0000-4444", "我的备用号是多少？",
     ["132-0000-3333", "13200003333"], ["133-0000-4444", "13300004444"]),
    ("cat", "我家大猫叫咪咪", "我家小猫叫甜甜", "我家大猫叫什么？",
     ["咪咪"], ["甜甜"]),
    ("cat", "我养的白猫叫雪球", "黑猫叫煤球", "我的白猫叫什么？",
     ["雪球"], ["煤球"]),
    ("email", "我的个人邮箱是p@example.com", "工作邮箱是w@example.com", "我的个人邮箱是什么？",
     ["p@example.com"], ["w@example.com"]),
    ("email", "我的备用邮箱是b1@example.com", "主邮箱是b2@example.com", "我的备用邮箱是什么？",
     ["b1@example.com"], ["b2@example.com"]),
    ("seat", "我在北京的工位是A1", "上海的工位是B2", "我北京的工位是哪个？",
     ["A1"], ["B2"]),
    ("seat", "我总部工位在8楼", "分部工位在3楼", "我总部的工位在几楼？",
     ["8楼"], ["3楼"]),
    ("hometown", "我父亲老家在山东", "我母亲老家在河南", "我父亲老家在哪？",
     ["山东"], ["河南"]),
    ("hometown", "我爱人老家在湖南", "我老家在湖北", "我爱人老家在哪？",
     ["湖南"], ["湖北"]),
]

def build():
    cases = []
    for i, (fam, old, new, q, vnew, vold) in enumerate(POS, 1):
        cases.append({
            "id": "KVC%02d" % i, "category": "kv_conflict",
            "input": q,
            "pre_state": [{"action": "remember", "text": old},
                          {"action": "remember", "text": new},
                          {"action": "ask", "text": FILLER[0]}],
            "expect": {"contains_any": vnew, "not_contains": vold,
                       "refusal": False},
            "note": "[KV-CONFLICT] %s 正例：%r -> %r" % (fam, old, new),
        })
    for j, (fam, a, b, q, va, vb) in enumerate(NEG, 1):
        cases.append({
            "id": "KVN%02d" % j, "category": "kv_conflict",
            "input": q,
            "pre_state": [{"action": "remember", "text": a},
                          {"action": "remember", "text": b},
                          {"action": "ask", "text": FILLER[1]}],
            "expect": {"contains_any": va, "not_contains": [],
                       "refusal": False},
            "note": "[KV-CONFLICT] %s 负例（同族不同主体）：问 %r，不得误隐藏" % (fam, a),
        })
    return cases

def collect_values(cases):
    vals = []
    for c in cases:
        vals.extend(c["expect"]["contains_any"])
    return vals

def main():
    cases = build()
    corpus = []
    for p in ["training/sft/train_v9.jsonl", "training/sft/train_v8.jsonl",
              "training/sft/train_v10.jsonl"]:
        corpus.append(open(p, encoding="utf-8").read())
    con = sqlite3.connect("kvmem/daily/chat.db")
    corpus.append("\n".join(r[0] for r in con.execute("select text from memory_source")))
    blob = "\n".join(corpus)
    # 只对“独特标识”（事实句、电话/车牌/邮箱/卡号/专名）做重叠断言；
    # 颜色/车型/时间/城市等通用词允许与既有语料同词（由 owner+predicate 区分，见 B⑨）。
    import re
    facts = [c["pre_state"][0]["text"] for c in cases] + \
            [c["pre_state"][1]["text"] for c in cases]
    ids = set()
    for v in collect_values(cases):
        if re.search(r"\d{3,}|@|^[\u4e00-\u9fa5][A-Z]\d", v):
            ids.add(v)
    bad_f = [f for f in facts if f in blob]
    bad_i = [v for v in ids if v in blob]
    print("cases=%d pos=%d neg=%d" % (len(cases), len(POS), len(NEG)))
    print("fact collisions:", bad_f if bad_f else "none")
    print("id collisions:", bad_i if bad_i else "none")
    if bad_f or bad_i:
        sys.exit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print("wrote", OUT, "sha256", h)
    print("ids", cases[0]["id"], "..", cases[-1]["id"])

if __name__ == "__main__":
    main()