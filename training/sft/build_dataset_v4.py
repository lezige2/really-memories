# -*- coding: utf-8 -*-
"""v4 数据：修 v2 已知病灶 + 新增 capability/meta/实时拒答/自主性，1 epoch 训练用。
输出 training/sft/train_v4.jsonl / data_v4.jsonl + out/SFT-DATA-v4-AUDIT.json
"""
import json
import os
import random
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import build_dataset as bd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rng = random.Random(2026)
NOW = datetime(2026, 10, 27, 21, 0)
ANCH = [datetime.strptime(a, "%Y-%m-%d %H:%M") for a in bd.ANCHORS[:8]]
MEM_TOPICS = ("车牌|银行卡|工号|公司|生日|地址|住址|身份证|电话|手机|猫|狗|宠物|组会|"
              "下周三|下个月|爱吃什么|名字|老家|过敏|血压|密码|邮箱|微信|快递|社保|"
              "身高|体重|工位|眼镜|鞋码|年龄|几岁|大学|入职|旅行")
BANNED = ("雪梨", "商汤", "豆豆", "布洛芬", "洛阳", "7418", "京A88888", "阿泽", "字节跳动")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def mk(q, a, mems=None, dt=NOW, empty_user=False):
    return {"messages": [
        {"role": "system", "content": bd.make_system(dt, mems, False)},
        {"role": "user", "content": "" if empty_user else q},
        {"role": "assistant", "content": a}]}


def classify(r):
    q = r["messages"][1]["content"]
    a = r["messages"][2]["content"]
    s = r["messages"][0]["content"]
    if re.search(r"系统提示词|训练数据|身份证|密码|破解|监听|管理员|人肉|盗号|黑进|开房|验证码", q):
        return "privacy"
    if re.search(r"现在几点|今天几号|今天星期几|明天|后天|昨天|前天|下周|本周|周[一二三四五六日]", q):
        return "time"
    if a.startswith("我是你的本地记忆助手"):
        return "identity"
    if re.search(r"帮我|你帮我|能不能|麻烦你|在吗，帮", q) and any(
            w in a for w in ("帮不了", "做不了", "没法", "不能")):
        return "boundary"
    if any(w in a for w in ("没法确认", "没跟我说过", "没提过", "不知道，你没告诉")):
        return "unknown"
    if "当前时间：" in s and not s.startswith("当前时间"):
        head = s.split("\n\n")[0]
        return "latest" if len([x for x in head.split("\n") if x.strip()]) >= 2 else "memory"
    return "chat"


CAP = [(["你能联网吗", "你是联网的吗", "你能上网吗", "你可以联网查东西吗", "你能查到实时信息吗"],
        ["不能，我是本地部署的，不联网。", "我连不了网，查不到实时信息。", "不能哦，我没法联网。"]),
       (["你能操作应用吗", "你会发消息吗", "你能帮我转账吗", "你能登录我的账号吗", "你能删文件吗"],
        ["这个我帮不了哦，我不能操作应用。", "做不了，我没法操作账号或文件。"]),
       (["你能记住事情吗", "你有记忆吗", "你记得住吗", "你会忘事吗"],
        ["能，我会记住你告诉我的事，需要时按记忆回答。", "记得住，你告诉我事实就行。"])]
META = [("你有长期记忆吗", ["有，存在本地，你告诉我事实我就记着。", "有记忆库，记着你的事。"]),
        ("你能记住多少", ["具体上限我不数，常用的我记着。", "能记不少，你告诉我我会记。"]),
        ("你会记住我说的话吗", ["会，你告诉我事实就行。", "记着呢，你直接说。"]),
        ("你记忆里有什么", ["有你告诉我的事，你问哪件我就按记忆答。", "记着一些你的事，你问具体点。"]),
        ("你现在记得几条", ["具体几条我没法随时数，但我记着你告诉我的事。", "我记着一些，你要问哪件？"]),
        ("你还记得我的事吗", ["记着一些，你问具体点，我按记忆回答。", "记得，你直接问我就行。"]),
        ("你会忘记我吗", ["不会故意忘，记不清的时候我不会乱编。", "我会记着，记不清就说不清楚。"]),
        ("你的记忆存在哪", ["存在本地，不上传。", "记忆存在你本地的库文件里。"]),
        ("你记得我们昨天聊了什么吗", ["昨天聊了不少，你提个具体的事我好对上。", "我按记忆找，你给个线索更好。"]),
        ("你记得几条我的信息", ["具体条数我不数，但你问的事我按记忆答。", "我记着你说的，条数不重要。"])]
REAL = [(["北京今天天气怎么样", "明天上海下雨吗", "今天北京限行尾号是多少", "现在股价多少",
          "帮我查一下明天的新闻", "现在汇率是多少", "今天油价多少", "今天天气如何",
          "明天北京什么天气", "最近有什么新闻", "现在的黄金价格是多少", "今天空气质量怎么样"],
         ["我查不到实时信息，你可以看看手机上的天气或新闻。", "这个我没法查，我没有实时数据。",
          "我连不了网，实时信息查不到。"])]
FACTS = [("下周三要去杭州开会", "杭州"), ("周日下午三点去游泳", "游泳"), ("对青霉素过敏", "青霉素"),
         ("儿子小名毛豆", "毛豆"), ("车是白色SUV", "白色SUV"), ("工位在D区3号", "D区3号"),
         ("手机号是138-0000-2468", "138-0000-2468"), ("新家在滨江小区", "滨江"),
         ("最近在学做饭", "做饭"), ("养了只柯基叫可乐", "可乐"), ("周五晚上十点去健身", "健身"),
         ("老家在合肥", "合肥")]
VAGUE = [("我最近在忙一个项目", "我最近在忙什么？"), ("我下周要出差", "我去哪出差？"),
         ("我买了台新电脑", "我买的什么电脑？"), ("我养了只宠物", "我的宠物叫什么？"),
         ("我在准备考试", "我考的哪门？"), ("我换了份工作", "我换到哪家了？")]
D_MSG = ["{m}，别忘了哈。", "{m}，到时候提醒你一下。", "对了，{m}。", "{m}，安排上了吗？",
         "{m}，需要我帮你记着吗？", "{m}，记得留点时间。"]


def gen_capability():
    out = []
    for qs, ans in CAP:
        for q in qs:
            for p in ("", "问一下，", "在吗，"):
                for a in ans:
                    out.append(mk(p + q, a))
    for q in ("你能做什么", "你会什么", "你有什么能力"):
        for p in ("", "问一下，", "在吗，"):
            for a in ("我能帮你记事实、按记忆回答问题；不能操作应用，也不联网。",
                      "我能记事、按记忆答问题；不能联网、不能操作应用。",
                      "我记东西、答问题；不能替你操作应用。"):
                out.append(mk(p + q, a))
    return out


def gen_meta():
    out = []
    for q, ans in META:
        for p in ("", "问一下，", "在吗，"):
            for a in ans:
                out.append(mk(p + q, a))
    return out


def gen_realtime():
    out = []
    for qs, ans in REAL:
        for q in qs:
            for p in ("", "问一下，", "在吗，"):
                for a in ans:
                    out.append(mk(p + q, a))
    return out


def gen_latest():
    out = []
    sets_city = [("北京", "上海", "广州"), ("深圳", "杭州", "成都"), ("武汉", "西安", "南京"),
                 ("苏州", "天津", "重庆"), ("长沙", "郑州", "青岛")]
    sets_time = [("六点", "七点", "八点"), ("七点半", "八点", "八点半"), ("六点半", "七点", "七点半"),
                 ("八点", "八点半", "九点"), ("五点半", "六点", "六点半")]
    topics = [("我下周三去哪开会？", "下周三的会在哪开？", "我下周三要去哪？", sets_city,
               "我下周三要去%s开会", "你下周三要去%s开会。"),
              ("我下周五去哪出差？", "下周五的差去哪出？", "我下周五要去哪？", sets_city,
               "我下周五要去%s出差", "你下周五要去%s出差。"),
              ("我每周三晚上几点有组会？", "组会时间是几点？", "每周三晚上我有什么安排？", sets_time,
               "我每周三晚上%s有组会", "你每周三晚上%s有组会。")]
    for q1, q2, q3, sets, memfmt, ansfmt in topics:
        for vals in sets:
            mems = [memfmt % v for v in vals]
            for q in (q1, q2, q3):
                out.append(mk(q, ansfmt % vals[-1], mems=mems, dt=rng.choice(ANCH)))
    return out


def gen_autonomy():
    out = []
    for i in range(80):
        f, k = FACTS[i % len(FACTS)]
        ack = ["{k}啊，那挺忙的。", "行，{k}，别忘了。", "{k}，记着呢。", "好，{k}，到时候看安排。",
               "{k}，挺好的。", "嗯，{k}，知道了。"][i % 6]
        out.append(mk("我" + f, ack.format(k=k)))
    for i in range(60):
        vg, q = VAGUE[i % len(VAGUE)]
        cl = ["你只说了个大概，具体是哪个？", "方便说下具体是什么吗？", "这个我还不清楚，你说具体点。",
              "具体是哪个项目呀？", "是哪里的？", "什么型号的？"][i % 6]
        out.append(mk(vg + "。" + q, cl))
    for i in range(60):
        f, k = FACTS[i % len(FACTS)]
        q = ["我这周有什么安排？", "我最近有什么固定安排？", "你还记得我那件事吗？"][i % 3]
        out.append(mk(q, "你{0}。".format(f), mems=["我" + f]))
    for i in range(40):
        f, k = FACTS[i % len(FACTS)]
        out.append(mk("", D_MSG[i % len(D_MSG)].format(m=k), mems=["我" + f], empty_user=True))
    out.append(mk("", "你对阿司匹林过敏，吃药前记得问一下医生。",
                  mems=["我对阿司匹林过敏"], empty_user=True))
    return out


def gen_memmulti():
    out = []
    facts = ["我下周三要去杭州开会", "我养了只猫叫团子", "我每周三晚上七点有组会",
             "我用的手机是 iPhone 15", "我的车牌号是沪B12345", "我在网易上班",
             "我最爱吃火锅", "我老家在合肥", "我女儿小名葡萄", "我下个月去网易出差"]
    qs = [("我下周三去哪开会？", "你下周三要去杭州开会。", "我下周三要去杭州开会"),
          ("我养的猫叫什么名字？", "你养的猫叫团子。", "我养了只猫叫团子"),
          ("我们组会几点开？", "你每周三晚上七点有组会。", "我每周三晚上七点有组会"),
          ("我用的什么手机？", "你用的是 iPhone 15。", "我用的手机是 iPhone 15")]
    for i in range(60):
        q, a, rel = qs[i % len(qs)]
        others = [f for f in facts if f != rel]
        rng.shuffle(others)
        mems = [rel] + others[:rng.randint(1, 2)]
        rng.shuffle(mems)
        out.append(mk(q, a, mems=mems))
    return out


def gen_unknown_hardneg():
    out = []
    qs = ["我的生日是哪天？", "我的身份证号是多少？", "我的工资是多少？", "我妈妈生日是哪天？",
          "我的银行卡号是多少？", "我血压多少？", "我大学在哪读的？", "我什么时候入职的？",
          "我对什么过敏？", "我的快递到哪了？", "我的社保号是多少？", "我穿多大码的鞋？"]
    mems_pool = ["我下周三要去杭州开会", "我养了只猫叫团子", "我每周三晚上七点有组会",
                 "我用的手机是 iPhone 15", "我的车牌号是沪B12345", "我最爱吃火锅",
                 "我老家在合肥", "我在网易上班"]
    for i in range(60):
        q = qs[i % len(qs)]
        rng.shuffle(mems_pool)
        mems = mems_pool[:rng.randint(1, 2)]
        out.append(mk(q, "这个我没法确认：你没跟我说过。", mems=mems))
    return out


def load_v2():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "training", "sft", "train.jsonl"),
                                        encoding="utf-8")]
    pool = {}
    for r in rows:
        pool.setdefault(classify(r), []).append(r)
    return pool


def take(pool, cat, n, flt=None):
    arr = [r for r in pool.get(cat, []) if (flt is None or flt(r))]
    rng.shuffle(arr)
    return arr[:n]


def main():
    pool = load_v2()
    unknown_safe = lambda r: not re.search(MEM_TOPICS, r["messages"][1]["content"])
    parts = [("v2_identity", take(pool, "identity", 80)),
             ("v2_boundary", take(pool, "boundary", 300)),
             ("v2_privacy", take(pool, "privacy", 100)),
             ("v2_time", take(pool, "time", 180)),
             ("v2_chat", take(pool, "chat", 160)),
             ("v2_memory", take(pool, "memory", 450)),
             ("gen_latest", gen_latest()),
             ("v2_unknown_safe", take(pool, "unknown", 160, unknown_safe)),
             ("new_capability", gen_capability()[:140]),
             ("new_meta", gen_meta()),
             ("new_realtime", gen_realtime()),
             ("new_multi_mem", gen_memmulti()),
             ("new_unknown_hardneg", gen_unknown_hardneg()),
             ("new_autonomy", gen_autonomy())]

    def clean(arr):
        out = []
        for r in arr:
            txt = json.dumps(r, ensure_ascii=False)
            if any(w in txt for w in BANNED):
                continue
            out.append(r)
        return out

    parts = [(n, clean(a)) for n, a in parts]
    rows, cats = [], {}
    for name, arr in parts:
        cats[name] = len(arr)
        rows += arr
    seen, uniq = set(), []
    for r in rows:
        k = (norm(r["messages"][0]["content"]), norm(r["messages"][1]["content"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    rng.shuffle(uniq)
    out_dir = os.path.join(ROOT, "training", "sft")
    for fn in ("train_v4.jsonl", "data_v4.jsonl"):
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
            for r in uniq:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    audit = {"schema": "sft_data_v4_audit", "rows": len(uniq), "planned": cats}
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    with open(os.path.join(ROOT, "out", "SFT-DATA-v4-AUDIT.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(json.dumps(audit, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()