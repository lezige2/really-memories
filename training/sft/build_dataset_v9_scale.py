# -*- coding: utf-8 -*-
"""v9 规模化数据生成器（TASK-083 定稿规格 v2）。

组成：
  v8b 1602 行底座（原样保留）
  + 底座补强 80 行（银行卡尾号族正样本 40 + meta 变体 40）
  + 新增 10 类 2600 行（A800/B300/C120/D260/E260/F260/G220/H240/I90/J50）
输出：
  training/sft/train_v9.jsonl 与 training/sft/data_v9.jsonl（同内容）
  out/SFT-DATA-v9-AUDIT.json
随机种子 20261029；多轮行按 ≈800 字符 / 估算 ≤470 token 预算自动降级。
运行：python -X utf8 training/sft/build_dataset_v9_scale.py
"""
import collections
import hashlib
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_dataset as bd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
SFT = os.path.join(ROOT, "training", "sft")
OUT = os.path.join(ROOT, "out")
SEED = 20261029
rng = random.Random(SEED)

BASE = os.path.join(SFT, "train_v8b.jsonl")
DTS = [datetime.strptime(a, "%Y-%m-%d %H:%M") for a in bd.ANCHORS[:8]]

# 9 个评测保留值：全数据集出现次数必须为 0
BANNED = ("雪梨", "商汤", "豆豆", "布洛芬", "洛阳", "7418", "京A88888", "阿泽", "字节跳动")
BANNED_RE = re.compile("|".join(re.escape(x) for x in BANNED))

# ---- 训练/评测值池互斥（TASK-086）：评测 fixture 值全部来自 E 的 out/V9-EVAL-VALUES.json
EVAL_FILE = os.path.join(OUT, "V9-EVAL-VALUES.json")


def load_eval_values():
    if not os.path.exists(EVAL_FILE):
        return []
    with open(EVAL_FILE, encoding="utf-8") as f:
        d = json.load(f)
    return list((d.get("eval_values_independent") or {}).keys())


EVAL_VALUES = load_eval_values()
FIXTURE_VALUES = []


def load_fixture_values():
    if not os.path.exists(EVAL_FILE):
        return []
    with open(EVAL_FILE, encoding="utf-8") as f:
        d = json.load(f)
    return list((d.get("fixture_values") or {}).keys())


FIXTURE_VALUES = load_fixture_values()

# E 的 V9-EVAL-VALUES.json 已给出结构化分类：
#   independent_entities（MT20 关键判别实体）/ independent_generic_tokens（明确通用）/
#   fixture_entities（评测 fixture 实体，含 MEM: 包裹与少量通用词）
# 训练侧强制禁用 = independent_entities + BANNED + fixture_entities 中的"标识型实体"
#   （含 ASCII 字母/数字的标识，或城市/人名/宠物/品牌/菜系/颜色等专名）；
#   纯中文通用词/问句/拒答短语列为 exempt（禁用会与定稿规格冲突），逐条写进审计。
CITY_SET = {"北京", "上海", "广州", "深圳", "拉萨", "杭州", "成都", "银川", "哈尔滨", "宜昌",
            "荆州", "襄阳", "洛阳", "西安", "郑州"}
NAME_SET = {"团子", "布丁", "可乐", "奶糖", "咪咪", "栗子", "雪梨", "豆豆", "朵朵", "安安",
            "米朵", "果果", "李静", "阿泽", "糖糖", "糖糖"}
BRAND_SET = {"华为", "苹果", "联想", "戴尔", "小米", "MacBook", "ThinkPad", "顺丰", "中石油",
             "DeepSeek", "DeepSeek-R1", "GPT", "Qwen", "通义", "R1", "Lite-Preview", "深度求索"}
MISC_SET = {"粤菜", "湘菜", "银色", "两厢", "沪A"}


def _structured_eval():
    """返回 (enforced_entities, generic_tokens)。"""
    if not os.path.exists(EVAL_FILE):
        return [], []
    with open(EVAL_FILE, encoding="utf-8") as f:
        d = json.load(f)
    ent = list((d.get("independent_entities") or {}).keys())
    gen = list((d.get("independent_generic_tokens") or {}).keys())
    fx = list((d.get("fixture_entities") or {}).keys())
    if not ent and not fx:  # 兼容旧格式
        ent = list((d.get("eval_values_independent") or {}).keys())
        fx = list((d.get("fixture_values") or {}).keys())
    enforced = []
    for v in ent + list(BANNED):
        nv = re.sub(r"\s+", "", str(v))
        if nv and nv not in enforced:
            enforced.append(nv)
    for v in fx:
        nv = re.sub(r"\s+", "", str(v))
        if nv.startswith("MEM:"):
            continue
        ident = bool(re.search(r"[A-Za-z0-9]", nv)) and not re.fullmatch(r"\d+", nv)
        if ident or nv in CITY_SET or nv in NAME_SET or nv in BRAND_SET or nv in MISC_SET:
            if nv and nv not in enforced:
                enforced.append(nv)
    generic = [re.sub(r"\s+", "", x) for x in gen]
    return enforced, generic


ENFORCED, EVAL_GENERIC = _structured_eval()
EXEMPT = set(EVAL_GENERIC)


def _eval_matchers():
    ms = []
    for v in ENFORCED:
        if re.fullmatch(r"\d+号", v) or re.fullmatch(r"\d+点", v) or re.fullmatch(r"\d+度", v):
            ms.append(re.compile(r"(?<!\d)" + re.escape(v)))
        else:
            ms.append(re.compile(re.escape(v)))
    return ms


EVAL_MATCHERS = _eval_matchers()


def eval_hits(text):
    n = re.sub(r"\s+", "", str(text or ""))
    return [v for v, m in zip(ENFORCED, EVAL_MATCHERS) if m.search(n)]


CJK = re.compile(r"[\u4e00-\u9fff]")
ALNUM = re.compile(r"[A-Za-z0-9]")
BUDGET_CHARS = 650          # A 类多轮行字符预算（TASK-092 M5）
BUDGET_TOKENS = 470         # 估算 token 预算（训练 max_len=512 的保守估计）


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def est_tokens(s):
    """CJK 1.0 / 字母数字 0.34 / 其它 0.55 的保守估算（无本地 tokenizer 时的口径）。"""
    s = str(s or "")
    c = len(CJK.findall(s))
    a = len(ALNUM.findall(s))
    o = len(s) - c - a
    return c + a * 0.34 + o * 0.55


def mem_blocks(sys_text):
    parts = str(sys_text).split("\n\n")
    if len(parts) < 3:
        return 0
    return len([x for x in parts[0].split("\n") if x.strip()])


def row_tokens(row):
    """含 system 的完整 prompt 估算：内容 tokens + 每条消息角色/模板开销 4 + 起始 3。"""
    return sum(est_tokens(m["content"]) for m in row["messages"]) + 4 * len(row["messages"]) + 3


def row_chars(row):
    return sum(len(str(m["content"])) for m in row["messages"])


def sysc(dt, mems=None):
    return bd.make_system(dt, mems, False)


def single(q, a, mems=None, dt=None):
    return {"messages": [
        {"role": "system", "content": sysc(dt or rng.choice(DTS), mems)},
        {"role": "user", "content": q},
        {"role": "assistant", "content": a}]}


def multi(turns, mems, dt):
    msgs = [{"role": "system", "content": sysc(dt, mems)}]
    for u, a in turns:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    return {"messages": msgs}


# ================================================================ A 多记忆长对话 800
# TRAIN 值池（TASK-086/088：与 out/V9-EVAL-VALUES.json 的评测值完全独立）
TRAIN_POOL = {
    "pet": "年糕", "city": "无锡", "plate": "苏A67890", "company": "用友",
    "phone": "135-2222-7777", "desk": "D区5号", "gym": "周日上午九点",
    "food": "烤鱼", "card_tails": ["3046", "8821", "5590"],
}
FAM = [
    dict(name="车牌", old="苏B12345", news=["苏A67890", "苏C88213", "苏E55902"],
         old_mem="我的车牌是%s", new_mem="我换了车牌，现在是%s",
         explicit="我车牌原来是%s，后来换成了%s",
         qs=["我车牌号是多少？", "我车牌是哪个？"], ans="你车牌现在是%s。"),
    dict(name="手机号", old="138-0000-2468", news=["135-2222-7777", "137-4444-8888", "139-5555-6666"],
         old_mem="我的手机号是%s", new_mem="我手机号换了，现在是%s",
         explicit="我手机号从%s换成了%s",
         qs=["我现在手机号是多少？", "我手机号是多少？"], ans="你现在手机号是%s。"),
    dict(name="工位", old="D区12号", news=["D区5号", "A区3号", "D区6号"],
         old_mem="我的工位在%s", new_mem="我工位搬到%s了",
         explicit="我工位原来在%s，现在搬到%s",
         qs=["我工位在哪？", "我现在工位是哪个？"], ans="你工位在%s。"),
    dict(name="健身时间", old="周三晚上八点", news=["周日上午九点", "周六上午九点", "周四晚上八点"],
         old_mem="我%s去健身", new_mem="我现在改成%s去健身",
         explicit="我以前%s健身，后来改成%s",
         qs=["我什么时间去健身？", "我健身时间是几点？"], ans="你现在%s去健身。"),
    dict(name="宠物名", old="饭团", news=["芝麻", "毛豆", "糯米"],
         old_mem="我养的猫叫%s", new_mem="我猫改名了，现在叫%s",
         explicit="我猫改名了，原来叫%s，现在叫%s",
         qs=["我猫叫什么名字？", "我家猫叫啥？"], ans="你养的猫叫%s。"),
    dict(name="公司", old="网易", news=["用友", "浪潮", "携程"],
         old_mem="我在%s上班", new_mem="我跳槽到%s了",
         explicit="我原来在%s上班，后来跳槽到%s",
         qs=["我在哪家公司上班？", "我现在公司是哪家？"], ans="你在%s上班。"),
    dict(name="银行卡尾号", old="1234", news=["3046", "8821", "5590"],
         old_mem="我的银行卡尾号是%s", new_mem="我换了卡，新卡尾号是%s",
         explicit="我换卡了，旧卡尾号%s，新卡尾号%s",
         qs=["我银行卡尾号是多少？", "我卡尾号是哪个？"], ans="你银行卡尾号是%s。"),
    dict(name="备用手机号", old="186-0000-1122", news=["189-0000-3344", "188-0000-5566"],
         old_mem="我的备用手机号是%s", new_mem="我备用号换成%s了",
         explicit="我备用号从%s换成了%s",
         qs=["我备用手机号是多少？", "我备用号是多少？"], ans="你备用手机号是%s。"),
    dict(name="女儿小名", old="葡萄", news=["一一", "乐乐", "团团"],
         old_mem="我女儿小名%s", new_mem="我女儿小名改成%s了",
         explicit="我女儿小名原来叫%s，后来改成%s",
         qs=["我女儿小名是什么？", "我女儿小名叫啥？"], ans="你女儿小名叫%s。"),
    dict(name="车颜色", old="白色", news=["深蓝色", "灰色", "黑色"],
         old_mem="我车是%s的", new_mem="我换车了，现在是%s的",
         explicit="我换车了，以前是%s，现在是%s",
         qs=["我车是什么颜色？", "我车现在什么色？"], ans="你车是%s的。"),
    dict(name="组会时间", old="周三晚上七点", news=["周三晚上八点", "周四晚上六点半"],
         old_mem="我%s有组会", new_mem="我组会改到%s了",
         explicit="我组会原来在%s，后来改到%s",
         qs=["我组会几点开？", "组会时间是几点？"], ans="你组会在%s。"),
    dict(name="出差地", old="青岛", news=["无锡", "常州", "南通"],
         old_mem="我下个月去%s出差", new_mem="我出差地改成%s了",
         explicit="我出差原来去%s，后来改去%s",
         qs=["我下个月去哪出差？", "我出差去哪？"], ans="你下个月去%s出差。"),
    dict(name="爱吃", old="小笼包", news=["烤鱼", "火锅", "酸奶"],
         old_mem="我最爱吃%s", new_mem="我现在爱吃%s",
         explicit="我以前爱吃%s，现在爱吃%s",
         qs=["我最爱吃什么？", "我爱吃啥？"], ans="你最爱吃%s。"),
]
A_DISTRACT = ["我同事的车牌是苏E11111", "我同事手机号是 130-0000-1111",
              "我朋友的工位在 D 区 2 号", "我同事周末也去健身",
              "我邻居家的猫叫芝麻", "我朋友在用友上班", "我同事卡尾号 3399",
              "我爱人的备用号是 187-0000-9900", "我儿子小名豆包", "我同事的车是灰色的",
              "我朋友组会周三下午开", "我同事上个月换了车牌", "我表妹手机号刚换",
              "我同事工位换到 D 区 1 号"]
CHAT_OPEN = ["今天有点累", "刚下班", "在吗，忙不忙", "周末过得咋样", "晚上吃什么", "今天开会开了一天",
             "刚忙完，歇会儿", "今天有点冷", "困了", "有点饿", "地铁人好多", "刚回到家",
             "今天事儿真多", "下午一直在写东西"]
CHAT_RESP = ["累就早点歇着。", "刚下班啊，辛苦了。", "在呢，你说。", "还行，挺清闲的。",
             "还没想好呢。", "开一天会够呛的。", "歇会儿吧，别硬撑。", "嗯，凑合过。",
             "困了就去睡。", "那就先吃点东西。", "晚高峰就这样。", "到家就好，缓缓。",
             "事儿多也得一件件来。", "写东西挺费神的。"]


def a_rounds(row, max_rounds):
    return row


def build_a_turns(idx, rounds, family):
    turns = []
    for r in range(rounds):
        u = CHAT_OPEN[(idx + r * 3) % len(CHAT_OPEN)]
        a = CHAT_RESP[(idx * 2 + r * 5) % len(CHAT_RESP)]
        turns.append((u, a))
    return turns


def fit_budget(turns, mems, dt, fam, mode, val_old, val_new):
    """按字符/token 预算自动降级：先减闲聊轮次（保留最后一问），再减记忆块。"""
    while True:
        final_q = fam["qs"][0]
        final_a = (fam["ans"] % (val_new if mode in ("a", "b") else val_old))
        row = multi(turns + [(final_q, final_a)], mems, dt)
        if row_chars(row) <= BUDGET_CHARS and row_tokens(row) <= 480:
            return row
        if len(turns) > 3:
            turns = turns[:-1]
            continue
        if len(mems) > 2:
            mems = mems[:-1]
            continue
        return row  # 已最小化，交上层过滤


def gen_A():
    out = []
    seen = set()

    def add(row):
        m = row["messages"]
        k = (norm(m[0]["content"]), norm("|".join(x["content"] for x in m if x["role"] == "user")))
        if k in seen:
            return False
        if row_chars(row) > BUDGET_CHARS or row_tokens(row) > BUDGET_TOKENS:
            return False
        seen.add(k)
        out.append(row)
        return True

    # ---- 子集1：6-8 轮 长对话（≥150 条）
    i = 0
    while sum(1 for r in out if (len(r["messages"]) - 1) // 2 >= 6) < 150 and i < 4000:
        fam = FAM[i % len(FAM)]
        new = fam["news"][(i // len(FAM)) % len(fam["news"])]
        dt = DTS[i % len(DTS)]
        mode = "a" if i % 2 == 0 else "b"
        rounds = 5 + (i % 3)  # 5-7 轮闲聊 + 最后一问 = 6-8 轮（子集1）
        if mode == "a":
            mems = [fam["explicit"] % (fam["old"], new)]
        else:
            mems = [fam["old_mem"] % fam["old"], fam["new_mem"] % new]
        others = [d for d in A_DISTRACT]
        rng.shuffle(others)
        mems += others[:1]
        rng.shuffle(mems)
        if mode == "b":  # 位置法必须 old 在前 new 在后
            mems = [fam["old_mem"] % fam["old"]] + [m for m in mems if m not in
                                                    (fam["old_mem"] % fam["old"], fam["new_mem"] % new)]
            mems.append(fam["new_mem"] % new)
        turns = build_a_turns(i, rounds, fam)
        add(fit_budget(turns, mems, dt, fam, mode, fam["old"], new))
        i += 1

    # ---- 子集2：6 块记忆 + 2 冲突 + 相似干扰（≥100 条）
    i = 0
    while sum(1 for r in out if mem_blocks(r["messages"][0]["content"]) >= 6) < 50 and i < 4000:
        fam = FAM[i % len(FAM)]
        new = fam["news"][(i * 2) % len(fam["news"])]
        dt = DTS[(i + 3) % len(DTS)]
        mode = "a" if i % 3 else "b"
        if mode == "a":
            two = [fam["explicit"] % (fam["old"], new)]
        else:
            two = [fam["old_mem"] % fam["old"], fam["new_mem"] % new]
        others = [d for d in A_DISTRACT]
        rng.shuffle(others)
        mems = others[:2] + two + others[2:4]
        rng.shuffle(mems)
        if mode == "a":
            mems = mems[:4]
        else:  # 保持 old 在 new 之前
            rest = [m for m in mems if m not in (fam["old_mem"] % fam["old"], fam["new_mem"] % new)]
            rng.shuffle(rest)
            mems = rest[:4] + [fam["old_mem"] % fam["old"], fam["new_mem"] % new]
        rounds = 3 + (i % 3)
        turns = build_a_turns(i + 77, rounds, fam)
        add(fit_budget(turns, mems[:6], dt, fam, mode, fam["old"], new))
        i += 1

    # ---- 模式 a 补足到 400（显式语义 → 答新值）
    i = 0
    while sum(1 for r in out if r.get("_m") == "a") < 440 and i < 7000:
        fam = FAM[(i * 3) % len(FAM)]
        new = fam["news"][(i // 3) % len(fam["news"])]
        dt = DTS[(i * 5) % len(DTS)]
        mems = [fam["explicit"] % (fam["old"], new)]
        others = A_DISTRACT[:]
        rng.shuffle(others)
        mems += others[:1 + (i % 2)]
        row = fit_budget(build_a_turns(i + 11, 2 + (i % 3), fam), mems, dt, fam, "a", fam["old"], new)
        row["_m"] = "a"
        if add(row):
            pass
        i += 1

    # ---- 模式 b 补足到 240（纯位置 → 答新值），且 a+b 中 b ≤30%
    i = 0
    while sum(1 for r in out if r.get("_m") == "b") < 264 and i < 7000:
        fam = FAM[(i * 7) % len(FAM)]
        new = fam["news"][(i // 7) % len(fam["news"])]
        dt = DTS[(i * 3 + 1) % len(DTS)]
        old_m = fam["old_mem"] % fam["old"]
        new_m = fam["new_mem"] % new
        others = A_DISTRACT[:]
        rng.shuffle(others)
        mems = [old_m] + others[:1 + (i % 2)] + [new_m]
        row = fit_budget(build_a_turns(i + 33, 2 + (i % 3), fam), mems, dt, fam, "b", fam["old"], new)
        row["_m"] = "b"
        add(row)
        i += 1

    # ---- 模式 c 补足到 160（只挂旧值 → 答旧值，不得编造）
    i = 0
    while sum(1 for r in out if r.get("_m") == "c") < 176 and i < 7000:
        fam = FAM[(i * 5 + 2) % len(FAM)]
        dt = DTS[(i * 7 + 2) % len(DTS)]
        mems = [fam["old_mem"] % fam["old"]]
        others = A_DISTRACT[:]
        rng.shuffle(others)
        mems += others[:1]
        row = fit_budget(build_a_turns(i + 55, 2 + (i % 3), fam), mems, dt, fam, "c", fam["old"], fam["old"])
        row["_m"] = "c"
        add(row)
        i += 1

    # 模式 a/b/c 的标记清理，并按配额截断
    for r in out:
        r["_m"] = r.get("_m", "a")
    by = collections.defaultdict(list)
    for r in out:
        by[r["_m"]].append(r)
    picked = []
    picked += by.pop("a", [])
    picked += by.pop("b", [])[:240]
    picked += by.pop("c", [])[:160]
    for k, v in by.items():
        picked += v
    # 若模式 a 超 400 截断；总量目标 800
    a = [r for r in picked if r["_m"] == "a"][:440]
    b = [r for r in picked if r["_m"] == "b"][:264]
    c = [r for r in picked if r["_m"] == "c"][:176]
    res = a + b + c
    # 数量不够则用 b 模式补
    while len(res) < 880:
        fam = FAM[len(res) % len(FAM)]
        new = fam["news"][len(res) % len(fam["news"])]
        dt = DTS[len(res) % len(DTS)]
        row = fit_budget(build_a_turns(len(res) + 91, 3, fam),
                         [fam["old_mem"] % fam["old"], fam["new_mem"] % new], dt, fam, "b", fam["old"], new)
        res.append(row)
    return res[:880]


# ================================================================ B 能力正样本 300
CODE_SHORT = [
    ("快速排序", ["写一个快速排序", "实现一下快排", "帮我写快排的 Python 代码", "用 Python 写个 quicksort",
              "给我一份快速排序实现", "快速排序怎么写"],
     "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n"
     "    left = [x for x in arr if x < pivot]\n    mid = [x for x in arr if x == pivot]\n"
     "    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + mid + quick_sort(right)"),
    ("冒泡排序", ["写一个冒泡排序", "实现冒泡排序", "帮我写个冒泡排序代码", "用 Python 写 bubble sort"],
     "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(n - 1 - i):\n"
     "            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n    return arr"),
    ("素数判断", ["写一个判断素数的函数", "怎么判断一个数是不是素数", "帮我写素数判断的代码",
              "用 Python 判断素数"],
     "def is_prime(n):\n    if n < 2:\n        return False\n    i = 2\n    while i * i <= n:\n"
     "        if n % i == 0:\n            return False\n        i += 1\n    return True"),
    ("斐波那契", ["写一个斐波那契函数", "斐波那契数列怎么实现", "帮我写斐波那契的代码",
              "用 Python 写 fib"],
     "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a"),
    ("二分查找", ["写一个二分查找", "实现二分查找", "帮我写个二分查找代码", "用 Python 写 binary search"],
     "def binary_search(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n"
     "        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n"
     "        if arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n"
     "    return -1"),
]
LONG_CODE = [
    ("实现一个带缓存的斐波那契", (
        "from functools import lru_cache\n\n\n"
        "@lru_cache(maxsize=None)\ndef fib_cached(n):\n"
        "    \"\"\"返回第 n 个斐波那契数，递归加缓存避免重复计算。\"\"\"\n"
        "    if n < 0:\n        raise ValueError(\"n 不能为负数\")\n"
        "    if n < 2:\n        return n\n"
        "    return fib_cached(n - 1) + fib_cached(n - 2)\n\n\n"
        "def fib_list(n):\n"
        "    \"\"\"返回前 n 个斐波那契数组成的列表，使用迭代写法。\"\"\"\n"
        "    out = []\n    a, b = 0, 1\n"
        "    for _ in range(n):\n        out.append(a)\n        a, b = b, a + b\n"
        "    return out\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    print(fib_cached(30))\n    print(fib_list(10))\n")),
    ("实现一个简单的词频统计", (
        "import re\nfrom collections import Counter\n\n\n"
        "def word_count(text):\n"
        "    \"\"\"统计英文文本里每个单词出现的次数，忽略大小写和标点。\"\"\"\n"
        "    words = re.findall(r\"[a-zA-Z']+\", text.lower())\n"
        "    counter = Counter(words)\n    return counter\n\n\n"
        "def top_words(text, k=5):\n"
        "    \"\"\"返回出现次数最多的前 k 个单词及其次数。\"\"\"\n"
        "    counter = word_count(text)\n"
        "    return counter.most_common(k)\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    sample = \"the quick brown fox jumps over the lazy dog the end\"\n"
        "    print(word_count(sample))\n    print(top_words(sample, 3))\n")),
    ("实现一个 CSV 读取并汇总的脚本", (
        "import csv\n\n\n"
        "def load_rows(path):\n"
        "    \"\"\"读取 CSV 文件，返回字典列表；表头作为键。\"\"\"\n"
        "    rows = []\n    with open(path, newline=\"\", encoding=\"utf-8\") as f:\n"
        "        reader = csv.DictReader(f)\n"
        "        for item in reader:\n            rows.append(item)\n"
        "    return rows\n\n\n"
        "def total_by(rows, key, value_key):\n"
        "    \"\"\"按 key 分组，对 value_key 求和，返回字典。\"\"\"\n"
        "    result = {}\n"
        "    for row in rows:\n"
        "        name = row[key]\n        value = float(row[value_key])\n"
        "        result[name] = result.get(name, 0.0) + value\n"
        "    return result\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    rows = load_rows(\"sales.csv\")\n"
        "    print(total_by(rows, \"city\", \"amount\"))\n")),
    ("实现一个栈和队列", (
        "class Stack:\n"
        "    \"\"\"基于列表的栈，后进先出。\"\"\"\n"
        "    def __init__(self):\n        self.items = []\n\n"
        "    def push(self, x):\n        self.items.append(x)\n\n"
        "    def pop(self):\n"
        "        if not self.items:\n            raise IndexError(\"栈是空的\")\n"
        "        return self.items.pop()\n\n"
        "    def peek(self):\n        return self.items[-1] if self.items else None\n\n\n"
        "class Queue:\n"
        "    \"\"\"基于列表的队列，先进先出。\"\"\"\n"
        "    def __init__(self):\n        self.items = []\n\n"
        "    def enqueue(self, x):\n        self.items.append(x)\n\n"
        "    def dequeue(self):\n"
        "        if not self.items:\n            raise IndexError(\"队列是空的\")\n"
        "        return self.items.pop(0)\n\n\n"
        "def demo():\n"
        "    s, q = Stack(), Queue()\n"
        "    for i in range(3):\n        s.push(i)\n        q.enqueue(i)\n"
        "    return s.pop(), q.dequeue()\n")),
    ("实现一个二分查找的变体", (
        "def lower_bound(arr, target):\n"
        "    \"\"\"返回第一个大于等于 target 的下标，找不到返回 len(arr)。\"\"\"\n"
        "    lo, hi = 0, len(arr)\n"
        "    while lo < hi:\n        mid = (lo + hi) // 2\n"
        "        if arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid\n"
        "    return lo\n\n\n"
        "def upper_bound(arr, target):\n"
        "    \"\"\"返回第一个大于 target 的下标。\"\"\"\n"
        "    lo, hi = 0, len(arr)\n"
        "    while lo < hi:\n        mid = (lo + hi) // 2\n"
        "        if arr[mid] <= target:\n            lo = mid + 1\n        else:\n            hi = mid\n"
        "    return lo\n\n\n"
        "def count_range(arr, low, high):\n"
        "    \"\"\"统计落在 [low, high] 区间内的元素个数。\"\"\"\n"
        "    return upper_bound(arr, high) - lower_bound(arr, low)\n")),
    ("实现一个文件去重工具", (
        "import hashlib\nimport os\n\n\n"
        "def file_hash(path, chunk_size=65536):\n"
        "    \"\"\"计算文件的 sha256 值，分块读取避免占内存。\"\"\"\n"
        "    h = hashlib.sha256()\n"
        "    with open(path, \"rb\") as f:\n"
        "        while True:\n"
        "            block = f.read(chunk_size)\n"
        "            if not block:\n                break\n"
        "            h.update(block)\n"
        "    return h.hexdigest()\n\n\n"
        "def find_duplicates(root):\n"
        "    \"\"\"扫描目录，返回内容重复的文件分组。\"\"\"\n"
        "    groups = {}\n"
        "    for dirpath, _, filenames in os.walk(root):\n"
        "        for name in filenames:\n"
        "            path = os.path.join(dirpath, name)\n"
        "            if not os.path.isfile(path):\n                continue\n"
        "            groups.setdefault(file_hash(path), []).append(path)\n"
        "    return [v for v in groups.values() if len(v) > 1]\n")),
    ("实现一个简单的 LRU 缓存", (
        "from collections import OrderedDict\n\n\n"
        "class LRUCache:\n"
        "    \"\"\"固定容量的 LRU 缓存，超过容量时淘汰最久未使用的键。\"\"\"\n"
        "    def __init__(self, capacity):\n"
        "        self.capacity = capacity\n        self.data = OrderedDict()\n\n"
        "    def get(self, key):\n"
        "        if key not in self.data:\n            return None\n"
        "        value = self.data.pop(key)\n"
        "        self.data[key] = value\n        return value\n\n"
        "    def put(self, key, value):\n"
        "        if key in self.data:\n            self.data.pop(key)\n"
        "        elif len(self.data) >= self.capacity:\n"
        "            self.data.popitem(last=False)\n"
        "        self.data[key] = value\n\n\n"
        "def run_ops(ops):\n"
        "    \"\"\"按指令序列执行缓存操作，返回每次 get 的结果。\"\"\"\n"
        "    cache = LRUCache(2)\n    out = []\n"
        "    for op in ops:\n"
        "        if op[0] == \"put\":\n            cache.put(op[1], op[2])\n"
        "        else:\n            out.append(cache.get(op[1]))\n"
        "    return out\n")),
]
BIG_CODE = [
    ("实现一个带重试和日志的 HTTP 抓取器", (
        "import logging\nimport time\nimport urllib.request\n\n"
        "logging.basicConfig(level=logging.INFO, format=\"%(asctime)s %(levelname)s %(message)s\")\n"
        "LOGGER = logging.getLogger(__name__)\n\n\n"
        "def fetch(url, retries=3, timeout=10, backoff=2.0):\n"
        "    \"\"\"抓取 url，失败时指数退避重试，返回正文文本。\"\"\"\n"
        "    last_error = None\n"
        "    for attempt in range(1, retries + 1):\n"
        "        try:\n"
        "            LOGGER.info(\"fetch %s attempt=%d\", url, attempt)\n"
        "            with urllib.request.urlopen(url, timeout=timeout) as resp:\n"
        "                data = resp.read()\n"
        "            text = data.decode(\"utf-8\", errors=\"replace\")\n"
        "            LOGGER.info(\"fetch ok bytes=%d\", len(data))\n"
        "            return text\n"
        "        except Exception as exc:\n"
        "            last_error = exc\n"
        "            LOGGER.warning(\"fetch failed attempt=%d error=%r\", attempt, exc)\n"
        "            if attempt < retries:\n"
        "                time.sleep(backoff ** attempt)\n"
        "    raise RuntimeError(\"fetch failed after %d retries\" % retries) from last_error\n\n\n"
        "def fetch_all(urls):\n"
        "    \"\"\"逐个抓取，返回 (url, text) 列表，单个失败不影响其它。\"\"\"\n"
        "    out = []\n"
        "    for url in urls:\n"
        "        try:\n"
        "            out.append((url, fetch(url)))\n"
        "        except Exception as exc:\n"
        "            LOGGER.error(\"skip %s error=%r\", url, exc)\n"
        "    return out\n")),
    ("实现一个 CSV 清洗与统计流水线", (
        "import csv\nimport re\nfrom collections import defaultdict\n\n\n"
        "def clean_amount(raw):\n"
        "    \"\"\"把 '1,234.50 元' 这类字符串清洗成 float，失败返回 None。\"\"\"\n"
        "    if raw is None:\n"
        "        return None\n"
        "    text = re.sub(r\"[^0-9.\\-]\", \"\", str(raw))\n"
        "    try:\n"
        "        return float(text)\n"
        "    except ValueError:\n"
        "        return None\n\n\n"
        "def load_rows(path):\n"
        "    rows = []\n"
        "    with open(path, newline=\"\", encoding=\"utf-8\") as f:\n"
        "        for item in csv.DictReader(f):\n"
        "            amount = clean_amount(item.get(\"amount\"))\n"
        "            if amount is None:\n"
        "                continue\n"
        "            rows.append({\"city\": item.get(\"city\", \"\").strip(),\n"
        "                         \"amount\": amount})\n"
        "    return rows\n\n\n"
        "def summarize(rows):\n"
        "    \"\"\"按城市汇总金额与笔数，返回排序后的列表。\"\"\"\n"
        "    total = defaultdict(float)\n"
        "    count = defaultdict(int)\n"
        "    for row in rows:\n"
        "        total[row[\"city\"]] += row[\"amount\"]\n"
        "        count[row[\"city\"]] += 1\n"
        "    result = [(city, round(total[city], 2), count[city]) for city in total]\n"
        "    result.sort(key=lambda x: x[1], reverse=True)\n"
        "    return result\n\n\n"
        "def run(path):\n"
        "    rows = load_rows(path)\n"
        "    return summarize(rows)\n")),
    ("实现一个带优先级的任务队列", (
        "import heapq\nimport itertools\nimport time\n\n\n"
        "class TaskQueue:\n"
        "    \"\"\"小顶堆任务队列，数值越小优先级越高，相同优先级按入队顺序。\"\"\"\n"
        "    def __init__(self):\n"
        "        self._heap = []\n"
        "        self._counter = itertools.count()\n\n"
        "    def push(self, priority, task):\n"
        "        heapq.heappush(self._heap, (priority, next(self._counter), task))\n\n"
        "    def pop(self):\n"
        "        if not self._heap:\n"
        "            raise IndexError(\"queue is empty\")\n"
        "        priority, _, task = heapq.heappop(self._heap)\n"
        "        return priority, task\n\n"
        "    def __len__(self):\n"
        "        return len(self._heap)\n\n\n"
        "def run_tasks(items, worker):\n"
        "    \"\"\"按优先级依次执行任务，返回每个任务的耗时。\"\"\"\n"
        "    queue = TaskQueue()\n"
        "    for priority, name in items:\n"
        "        queue.push(priority, name)\n"
        "    costs = []\n"
        "    while queue:\n"
        "        priority, name = queue.pop()\n"
        "        begin = time.time()\n"
        "        worker(name)\n"
        "        costs.append((name, round(time.time() - begin, 4)))\n"
        "    return costs\n")),
]
CODE_LEAD = ["给你代码：", "可以，这样写：", "写法如下：", "这个不难，给你：", "代码如下：",
             "试试这段：", "参考这份实现：", "给你一份："]
TRANS = [("你好，世界", "Hello, world."), ("今天很忙", "I'm busy today."),
         ("这个问题我解决了", "I solved this problem."), ("明天见", "See you tomorrow."),
         ("请把文件发给我", "Please send me the file."), ("我很喜欢这个设计", "I really like this design."),
         ("需要我帮忙吗", "Do you need my help?"), ("会议改到下午三点", "The meeting is moved to three in the afternoon."),
         ("他还没到", "He hasn't arrived yet."), ("我们先吃饭吧", "Let's have dinner first.")]
TRANS_REV = [("Good morning", "早上好。"), ("Where are you now", "你现在在哪？"),
             ("I will call you later", "我晚点给你打电话。"), ("This is very important", "这个很重要。"),
             ("Thank you for your help", "谢谢你帮忙。"), ("Let me think about it", "让我想想。"),
             ("The file is ready", "文件准备好了。"), ("We have a meeting today", "我们今天有会。"),
             ("I am on my way", "我在路上了。"), ("See you at noon", "中午见。")]
ARITH = [(3, 5, "+"), (12, 7, "-"), (6, 8, "*"), (45, 9, "/"), (7, 13, "+"), (20, 6, "-"),
         (9, 9, "*"), (100, 25, "/"), (17, 8, "+"), (50, 23, "-"), (11, 11, "*"), (144, 12, "/"),
         (8, 15, "+"), (33, 19, "-"), (5, 12, "*")]
EXPLAIN = [
    ("解释一下这段代码：for i in range(3): print(i)", "这段代码循环三次，i 依次取 0、1、2，每次打印当前的 i。"),
    ("这段代码啥意思：x = [i * 2 for i in range(4)]", "这是列表推导式，会生成 0、2、4、6 组成的列表，每个元素是下标的两倍。"),
    ("解释下 def f(a, b=2): return a + b", "定义函数 f，参数 a 必填，b 默认是 2，返回两者之和。"),
    ("解释什么是闭包", "闭包就是函数里再定义函数，内层函数带着外层函数的变量一起返回。"),
    ("解释一下递归", "递归就是函数自己调用自己，需要写清终止条件，否则会一直调用下去。"),
    ("这段代码做什么：s = sum(range(5))", "把 0 到 4 加起来，结果是 10，sum 对序列求和。"),
    ("解释 try except 的用处", "try 里放可能出错的代码，except 捕获异常，避免程序直接崩掉。"),
    ("解释一下字典推导式", "字典推导式用一对花括号一次生成字典，比如 {k: v for k, v in pairs}。"),
    ("解释什么是时间复杂度", "时间复杂度描述运行时间随输入规模增长的趋势，常用大 O 表示。"),
    ("这段代码是什么意思：a, b = b, a", "这是交换两个变量，右侧先算好元组，再分别赋给 a 和 b。"),
    ("解释一下 isinstance 的用途", "isinstance 判断对象是不是某个类型，返回 True 或 False。"),
    ("解释 with open 的好处", "with 会在代码块结束时自动关闭文件，出错也会关，不用手动 close。"),
]


def gen_B():
    out = []
    # 长代码 40 条（200-400 token 量级）优先，保证裁剪后仍保留
    qv_big = ["%s，写完整代码", "帮我实现一下：%s", "%s，给份完整实现", "%s，要能直接跑",
              "%s，写详细点", "%s 怎么写，给完整版", "把「%s」实现出来", "%s，附上完整代码"]
    for i in range(40):
        name, code = BIG_CODE[i % len(BIG_CODE)]
        q = qv_big[i % 8] % name
        dt = DTS[(i // 8) % len(DTS)]
        lead = CODE_LEAD[i % len(CODE_LEAD)]
        lines = code.split("\n")
        ans = lead + "\n```python\n" + code + "\n```"
        while len(ans) > 560 and len(lines) > 8:  # 整行 ≤900 字符预算（ans ≈620 + system≈270）
            lines = lines[:-1]
            ans = lead + "\n```python\n" + "\n".join(lines) + "\n```"
        out.append(single(q, ans, dt=dt))
    # 短代码：5 题 × 4-6 措辞 × 复数引导
    for name, qs, code in CODE_SHORT:
        for qi, q in enumerate(qs):
            for lk in range(5):
                lead = CODE_LEAD[(qi + lk) % len(CODE_LEAD)]
                out.append(single(q, lead + "\n```python\n" + code + "\n```",
                                  dt=DTS[(qi + lk) % len(DTS)]))
    # 翻译 中英各 10 组
    for i in range(2):
        pairs = TRANS if i == 0 else TRANS_REV
        for j, (src, dst) in enumerate(pairs):
            if i == 0:
                qs = ["把「%s」翻译成英文" % src, "「%s」用英语怎么说" % src, "翻译成英文：%s" % src,
                      "用英文表达：%s" % src, "这句子英文怎么说：%s" % src, "翻成英语：%s" % src]
                ans = ["英文是：%s" % dst, "可以翻成：%s" % dst, "这样翻：%s" % dst, "英文写作：%s" % dst,
                       "翻出来是：%s" % dst, "对应英文：%s" % dst]
            else:
                qs = ["把「%s」翻译成中文" % src, "「%s」中文怎么说" % src, "翻译成中文：%s" % src,
                      "用中文表达：%s" % src, "这句子中文怎么说：%s" % src, "翻成中文：%s" % src]
                ans = ["中文是：%s" % dst, "可以译成：%s" % dst, "这样翻：%s" % dst, "中文写作：%s" % dst,
                       "译出来是：%s" % dst, "对应中文：%s" % dst]
            for k, q in enumerate(qs):
                out.append(single(q, ans[(j + k) % len(ans)], dt=DTS[(j + k) % len(DTS)]))
    # 算术
    for a, b, op in ARITH:
        res = {"+": a + b, "-": a - b, "*": a * b, "/": a / b}[op]
        res_s = ("%d" % res) if (isinstance(res, int) or res == int(res)) else ("%.2f" % res)
        for k, q in enumerate(["%d %s %d 等于几？" % (a, op, b), "%d %s %d 是多少？" % (a, op, b),
                               "算一下 %d %s %d" % (a, op, b), "请问 %d %s %d 得多少？" % (a, op, b),
                               "%d %s %d 结果是多少？" % (a, op, b), "帮忙算 %d %s %d" % (a, op, b),
                               "%d %s %d 帮我算下" % (a, op, b), "%d %s %d 是多少呢" % (a, op, b)]):
            out.append(single(q, "%d %s %d 等于 %s。" % (a, op, b, res_s), dt=DTS[(a + k) % len(DTS)]))
    # 解释代码/概念
    for j, (q, ans) in enumerate(EXPLAIN):
        for p in ("", "问一下，", "在吗，", "问个问题，", "请教一下，", "麻烦讲下，",
                  "想问下，", "能解释下吗：", "简单说说，", "给我讲讲，", "帮我看下，", "请教下，"):
            out.append(single(p + q, ans, dt=DTS[(j + len(p)) % len(DTS)]))
    seen, uniq = set(), []
    for r in out:
        k = (norm(r["messages"][0]["content"]), norm(r["messages"][1]["content"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq[:340]


# ================================================================ C 动作拒答+对照对 120
C_PAIRS = [
    ("发消息", "把这段话发出去", ["帮我%s。", "麻烦帮我%s", "帮我把这段话发出去，行吗？"],
     ["这个我帮不了哦，我没法操作应用。", "发消息我做不到，我不能操作应用。",
      "抱歉，我不能替你发消息。", "这个得你自己发，我动不了应用。",
      "我没法操作聊天软件，发不了。", "发消息我帮不上，你手动发一下吧。"]),
    ("转账", "转一笔钱", ["帮我%s。", "帮我%s，急用", "能不能帮我%s"],
     ["转账我帮不了，我没法操作支付。", "这个做不了，我不能操作账户。",
      "抱歉，钱的事我没法替你操作。", "转账我做不到，你得自己来。",
      "我没法碰支付功能，帮不上。", "这个得你自己操作，我动不了账户。"]),
    ("删文件", "删掉这个文件", ["帮我%s。", "帮我把桌面那个表格%s", "帮我%s吧"],
     ["删文件我帮不了，我不能操作文件。", "这个我没法做，动不了你的文件。",
      "抱歉，我不能替你删东西。", "删文件得你自己来，我碰不到文件。",
      "我没法操作文件系统，帮不上这个。", "这个做不了，你手动删一下吧。"]),
    ("登录", "登录一下邮箱", ["帮我%s。", "帮我%s，密码我发你", "帮我%s呗"],
     ["登录账号我帮不了，我不能操作账号。", "这个做不了，我没法登录你的账号。",
      "抱歉，我不能替你登录。", "登录得你自己来，我动不了账号。",
      "我没法操作账号，帮不上。", "这个做不到，你手动登一下吧。"]),
    ("下单", "下单买个杯子", ["帮我%s。", "帮我%s，就那个链接", "帮我%s吧"],
     ["下单我帮不了，我没法操作购物应用。", "这个做不了，我不能替你下单。",
      "抱歉，我不能替你在购物应用下单。", "下单得你自己来，我动不了应用。",
      "我没法操作购物流程，帮不上。", "这个做不到，你自己下单更稳。"]),
]
C_KNOW = [
    ("写代码", "把这段需求写成代码", ["帮我%s。", "麻烦帮我%s", "帮我把这段需求写成代码，行吗？"],
     "可以，给你：\n```python\ndef handler(ok):\n    if not ok:\n        return None\n    return ok\n```"),
    ("翻译", "把这段话翻译成英文", ["帮我%s。", "帮我%s，口语一点", "能不能帮我%s"],
     "可以，英文是：Please send me the latest file."),
    ("算价", "算一下总价", ["帮我%s。", "帮我%s，按两件算", "帮我%s吧"],
     "可以算：两件单价 45，总价是 90 元。"),
    ("解释", "解释一下这段代码", ["帮我%s。", "帮我%s，说简单点", "帮我%s呗"],
     "可以，这段代码先把输入转成列表，再逐个累加求和。"),
    ("总结", "总结一下这段文字", ["帮我%s。", "帮我%s，三句话内", "帮我%s吧"],
     "可以，简单说：这段文字讲的是先把需求列清楚，再按优先级做。"),
]
C_BOUNDARY = [
    ("帮我查一下今天的新闻", "这个我帮不了，我不能联网，查不到实时信息。"),
    ("帮我查查明天天气", "这个我帮不了，我没法联网，实时信息拿不到。"),
    ("帮我搜一下最新的资料", "搜不了，我不能联网，拿不到实时内容。"),
    ("帮我解释一下什么是闭包", "闭包就是函数里再定义函数，内层函数带着外层函数的变量一起返回。"),
    ("帮我解释一下这个报错", "报错一般是类型不对或者变量没定义，你把报错贴全我看看。"),
]


def gen_C():
    out = []
    for i in range(60):
        act, obj, tpls, refusals = C_PAIRS[i % len(C_PAIRS)]
        know, kobj, ktpls, kans = C_KNOW[i % len(C_KNOW)]
        tpl = tpls[i % len(tpls)]
        ktpl = ktpls[i % len(ktpls)]
        dt = DTS[i % len(DTS)]
        u = (tpl % obj) if "%s" in tpl else tpl
        ku = (ktpl % kobj) if "%s" in ktpl else ktpl
        out.append(single(u, refusals[i % len(refusals)], dt=dt))
        out.append(single(ku, kans, dt=dt))
    for i, (q, ans) in enumerate(C_BOUNDARY):
        out.append(single(q, ans, dt=DTS[(i + 5) % len(DTS)]))
    seen, uniq = set(), []
    for r in out:
        k = (norm(r["messages"][0]["content"]), norm(r["messages"][1]["content"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq[:132]


# ================================================================ D 实时拒答 260
D_TOPICS = [
    ("天气", ["今天天气怎么样？", "今天什么天气？", "外面天气如何？"]),
    ("气温", ["现在气温多少？", "今天气温几度？", "现在多少度？"]),
    ("下雨", ["今天会下雨吗？", "下午下雨不下雨？", "明天会下雨吗？"]),
    ("限行", ["今天限行尾号是多少？", "今天限行吗？", "明天限行尾号是几？"]),
    ("股价", ["今天股价多少？", "大盘现在什么点位？", "某只股票今天涨了吗？"]),
    ("新闻", ["今天有什么新闻？", "现在热点新闻有哪些？", "帮我看看最近新闻"]),
    ("汇率", ["现在汇率多少？", "美元汇率是多少？", "人民币汇率现在多少？"]),
    ("油价", ["今天油价多少？", "现在汽油多少钱？", "油价涨了吗？"]),
    ("金价", ["现在金价多少？", "今天黄金价格多少？", "金价现在什么水平？"]),
    ("路况", ["现在路况怎么样？", "这个点堵不堵？", "高速路况如何？"]),
    ("台风", ["有台风吗？", "台风到哪了？", "台风会影响这边吗？"]),
    ("空气质量", ["今天空气质量怎么样？", "现在空气好吗？", "空气质量指数多少？"]),
]
D_PLACES = ["苏州", "青岛", "济南", "无锡", "常州", "南通", "扬州", "宁波"]
D_ANS = ["这个我查不到，你看看手机上的天气或新闻吧。",
         "我连不了网，实时的信息拿不到。",
         "我没法查实时信息，你用手机看一眼更准。",
         "查不了，建议看手机上的天气或新闻。",
         "这类实时信息我拿不到，手机上看一眼吧。",
         "我没有联网能力，实时信息没法确认。",
         "这个得看手机上的天气或新闻，我这边查不到。",
         "查不到实时的，你打开手机看一眼就好。"]
D_ANS_BAD = re.compile(r"\d|℃|度|晴|多云|阴|雨|级|元|块")


def gen_D():
    out = []
    for ti, (topic, qs) in enumerate(D_TOPICS):
        for pi, place in enumerate(D_PLACES):
            for qi, q in enumerate(qs):
                u = "%s%s" % (place, q) if qi == 0 else q
                ans = D_ANS[(ti + pi + qi) % len(D_ANS)]
                if D_ANS_BAD.search(ans):
                    raise RuntimeError("D answer banned token: %r" % ans)
                out.append(single(u, ans, dt=DTS[(ti + pi) % len(DTS)]))
    seen, uniq = set(), []
    for r in out:
        k = (norm(r["messages"][0]["content"]), norm(r["messages"][1]["content"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq[:260]


# ================================================================ E 记忆正样本 260
E_FACTS = [
    ("我住在滨江小区", "我住哪个小区？", "你住在滨江小区。"),
    ("我每周二晚上打羽毛球", "我每周几打羽毛球？", "你每周二晚上打羽毛球。"),
    ("我戴 600 度的眼镜", "我眼镜多少度？", "你戴 600 度的眼镜。"),
    ("我养了一只狗叫皮蛋", "我养的狗叫什么？", "你养的狗叫皮蛋。"),
    ("我女儿小名葡萄", "我女儿小名是什么？", "你女儿小名叫葡萄。"),
    ("我的银行卡尾号 3046", "我银行卡尾号多少？", "你银行卡尾号 3046。"),
    ("我的备用手机号是 189-0000-3344", "我备用号是多少？", "你备用手机号是 189-0000-3344。"),
    ("我姐姐叫小云", "我姐姐叫什么？", "你姐姐叫小云。"),
    ("我车是灰色的", "我车什么颜色？", "你车是灰色的。"),
    ("我每周三晚上七点有组会", "组会几点开？", "你每周三晚上七点有组会。"),
    ("我在准备软考", "我在准备什么考试？", "你在准备软考。"),
    ("我下个月去青岛出差", "我下个月去哪出差？", "你下个月去青岛出差。"),
    ("我最爱吃小笼包", "我最爱吃什么？", "你最爱吃小笼包。"),
    ("我用的手机是 iPhone 15", "我用的什么手机？", "你用的是 iPhone 15。"),
    ("我车是白色的 SUV", "我车是什么车？", "你的车是白色 SUV。"),
    ("我对青霉素过敏", "我对什么过敏？", "你对青霉素过敏。"),
    ("我老家在济南", "我老家在哪？", "你老家在济南。"),
    ("我儿子上小学三年级", "我儿子上几年级？", "你儿子上小学三年级。"),
    ("我习惯晚上十一点睡", "我一般几点睡？", "你习惯晚上十一点睡。"),
    ("我在学做川菜", "我在学做什么菜？", "你在学做川菜。"),
    ("我下周五要去苏州出差", "我下周五去哪？", "你下周五要去苏州出差。"),
    ("我换了新工位在 A 区 5 号", "我新工位在哪？", "你新工位在 A 区 5 号。"),
    ("我最近在减脂", "我最近在忙什么？", "你最近在减脂。"),
    ("我喜欢喝美式", "我喜欢喝什么？", "你喜欢喝美式。"),
    ("我每月 15 号交房租", "我几号交房租？", "你每月 15 号交房租。"),
    ("我每天八点出门", "我每天几点出门？", "你每天八点出门。"),
    ("我加入了游泳群", "我加入了什么群？", "你加入了游泳群。"),
    ("我车牌是皖 A 12345", "我车牌多少？", "你车牌是皖 A 12345。"),
    ("我下周要搬家", "我下周做什么？", "你下周要搬家。"),
    ("我出差喜欢坐高铁", "我出差坐什么？", "你出差喜欢坐高铁。"),
    ("我今天面试了新公司", "我今天面试了什么？", "你今天面试了新公司。"),
    ("我周末去爬山", "我周末去哪？", "你周末去爬山。"),
    ("我电脑是 16G 内存的", "我电脑多大内存？", "你电脑是 16G 内存的。"),
    ("我钥匙放在门口柜子上", "我钥匙放哪了？", "你钥匙放在门口柜子上。"),
    ("我周四下午要去医院复查", "我周四下午干什么？", "你周四下午要去医院复查。"),
    ("我姐姐住在城东", "我姐姐住哪？", "你姐姐住在城东。"),
]


def gen_E():
    out = []
    # 银行卡尾号族正样本 60 条（3046/8821/5590，禁 7418）
    tails = ["3046", "8821", "5590"]
    cqs = ["我银行卡尾号是多少？", "我卡尾号是哪个？", "我那张卡尾号多少？",
           "我工资卡尾号是几？", "我卡号后四位是多少？"]
    cmems = ["我的银行卡尾号是%s", "我工资卡尾号%s", "我常用的卡尾号是%s"]
    i = 0
    for t in tails:
        for qi, q in enumerate(cqs):
            for dj in range(6):
                mem = cmems[dj % len(cmems)] % t
                ans = ["你银行卡尾号是%s。" % t, "你卡尾号是%s。" % t, "按记忆是%s。" % t][qi % 3]
                out.append(single(q, ans, mems=[mem], dt=DTS[(i + dj) % len(DTS)]))
                i += 1
    for fi, (mem, q, ans) in enumerate(E_FACTS):
        for di in range(3):
            for dj in range(3):
                p = ["", "问一下，", "在吗，"][di]
                dt = DTS[(fi + dj) % len(DTS)]
                out.append(single(p + q, ans, mems=[mem], dt=dt))
    return out


# ================================================================ F 闲聊致谢 260
F_USERS = ["谢谢", "谢谢你", "谢啦", "好的谢谢", "太感谢了", "你真好", "你人还挺好",
           "在吗", "在不在", "在吗在吗", "早", "早上好", "晚上好", "晚安", "我回来了",
           "我出门了", "刚吃完饭", "今天好累", "有点无聊", "说得好", "厉害啊", "牛",
           "收到", "好的", "行", "嗯嗯", "哈哈", "笑死", "我也是", "确实",
           "好无聊啊", "陪我聊会儿", "你在干嘛", "今天过得怎么样", "有空吗",
           "我先忙了", "回头聊", "下次再说", "先这样", "好，那就这样"]
F_REPLIES = ["不客气。", "别客气。", "嗯，有事随时说。", "在呢，你说。", "在呢，我在。",
             "早，今天起得挺早。", "早上好。", "晚上好。", "晚安，早点休息。",
             "回来啦，今天怎么样？", "路上小心。", "吃得还行吧？", "累就早点睡。",
             "无聊就找点事做。", "谢谢，你也是。", "哈哈，过奖了。", "嗯，收到。",
             "好，那就这么办。", "嗯，我在。", "笑着笑着就困了。", "我也是这么想的。",
             "确实是。", "那要不聊点别的？", "我一直在，随时找我。", "我不用干什么，等你说话。",
             "今天还行，挺平静的。", "有空，你说。", "好，你先忙。", "回头聊。",
             "行，下次再聊。", "好，先这样。"]


def gen_F():
    out = []
    for ui, u in enumerate(F_USERS):
        for di, dt in enumerate(DTS):
            ans = F_REPLIES[(ui * 3 + di) % len(F_REPLIES)]
            out.append(single(u, ans, dt=dt))
            if len(out) >= 280:
                return out
    return out


# ================================================================ G 身份/meta 220
G_QS = [
    ("你是谁？", ["我是你的本地记忆助手，能帮你记东西、按记忆答问题。",
                "我是你的本地记忆助手，跑在本地的 14B 模型上。"]),
    ("你叫什么名字？", ["我是你的本地记忆助手，你直接叫我助手就行。",
                   "我算是你的本地记忆助手，没有别的名字。"]),
    ("你是什么模型？", ["我是本地部署的开源大模型，做了记忆能力的微调。",
                   "我在本地跑，是基于开源模型微调的记忆助手。"]),
    ("你是云端的大模型吗？", ["不是，我是本地部署的开源模型，不是云端那类模型。",
                   "不是，我跑在你自己的机器上，是本地模型。"]),
    ("你是机器人吗？", ["算是吧，我是本地跑的记忆助手，不是真人。",
                   "我是程序，本地跑的记忆助手。"]),
    ("你能联网吗？", ["不能，我是本地部署的，不联网。",
                 "我连不了网，查不到实时信息。"]),
    ("你能操作应用吗？", ["不能，我不能操作任何应用，只能聊天和按记忆答问题。",
                   "这个帮不了，我没法动你的应用和账号。"]),
    ("你有记忆吗？", ["有，记忆存在本地，你告诉我事实我就记着。",
                 "有记忆库，记着你告诉我的事。"]),
    ("你的记忆存在哪？", ["存在本地，不上传。", "记忆存在你本地的库文件里，不外传。"]),
    ("你会忘记我吗？", ["不会故意忘，记不清的时候我不会乱编。",
                  "我会记着，实在记不清就直说。"]),
    ("你能记住多少？", ["具体上限我不数，常用的我记着。",
                  "能记不少，你告诉我我就会记着。"]),
    ("你现在记得几条？", ["具体几条我没法随时数，但我记着你告诉我的事。",
                   "条数我没数过，你问哪件我按记忆答。"]),
    ("你会记住我说的话吗？", ["会，你告诉我事实就行。", "记着呢，你直接说。"]),
    ("你记忆里有什么？", ["有你告诉我的事，你问具体点我就按记忆答。",
                   "记着一些你的事，你问哪件我答哪件。"]),
    ("你记得我们刚才聊了什么吗？", ["刚才聊了些日常，你提个具体的事我好对上。",
                          "我按记忆找，你给个线索更好。"]),
    ("你能做什么？", ["我能帮你记事实、按记忆回答问题；不能操作应用，也不联网。",
                 "我能记事、按记忆答问题；不能联网、不能操作应用。"]),
    ("你有什么能力？", ["我能记东西、按记忆答问题；不能替你操作应用。",
                  "记事实、答问题、按记忆回你，就这些。"]),
    ("你是本地模型吗？", ["对，我跑在你本地的机器上，记忆也在本地。",
                  "是的，本地部署，不上云。"]),
    ("你说话怎么这么自然？", ["聊得多了就自然了，我尽量像朋友一样说话。",
                     "我特意调过说话风格，尽量简短口语化。"]),
    ("你为什么不联网？", ["我设计上就是本地跑的，联网能力没有。",
                  "本地部署不联网，隐私也更好一些。"]),
    ("你会不会乱编？", ["不会，记不清我就说记不清，不编。",
                 "我不编，没依据的我就直接说不知道。"]),
    ("你能帮我做什么？", ["帮你记事实、按记忆回答、解点小问题；操作应用不行。",
                  "记事、答问题、聊聊天；真去操作东西我做不到。"]),
    ("你是哪个公司的？", ["我没有公司背景，就是本地部署的助手。",
                  "这不是公司产品，是本地的助手程序。"]),
    ("你会不会偷看我的数据？", ["不会，记忆存在本地，也没有上传通道。",
                     "数据都在本地，我没有联网的地方可发。"]),
    ("你的知识截止到什么时候？", ["这个我记不准，不清楚具体截止日期，我不编。",
                        "具体截止到哪天我不清楚，不确定的事我不编。"]),
    ("你的训练数据是什么？", ["训练数据的细节我不清楚，没法给你具体来源。",
                      "这个我不清楚，不编具体的数据集名字。"]),
    ("你是什么版本？", ["具体版本号我不清楚，不确定的不乱说。",
                  "版本信息我没有准确记录，就不编了。"]),
    ("你多大了？", ["我没有年龄这个概念，不清楚就不编。",
               "我是程序，说不上年龄，这个真不清楚。"]),
    ("你训练用了多少数据？", ["具体规模我不清楚，没法给你准确数字。",
                     "训练数据量我没有准确记录，不编。"]),
]
G_ANTI = ["你的知识截止到什么时候？", "你的训练数据是什么？", "你是什么版本？",
          "你多大了？", "你训练用了多少数据？", "你是哪个版本训练的？",
          "你的参数有多少？", "你什么时候上线的？", "你的训练时间是什么时候？",
          "你是第几代模型？"]


def gen_G():
    out = []
    i = 0
    # anti-self-fact 60 条
    while sum(1 for r in out if r["messages"][1]["content"] in
              [x for x in G_ANTI] or any(r["messages"][1]["content"].endswith(x) for x in G_ANTI)) < 60 and i < 400:
        q = G_ANTI[i % len(G_ANTI)]
        ans = ["这个我记不准，不清楚具体日期或版本，我不编。",
               "具体信息我不清楚，不确定的不乱说，也不编数字。",
               "我没有准确记录，这个就不猜了。",
               "不清楚这个，编一个反而误导你。",
               "这类细节我没法确认，就不编了。"][i % 5]
        dt = DTS[i % len(DTS)]
        p = ["", "问一下，", "在吗，"][(i // len(G_ANTI)) % 3]
        out.append(single(p + q, ans, dt=dt))
        i += 1
    # 其余 meta 补足 220
    j = 0
    while len(out) < 250:
        q, anss = G_QS[j % len(G_QS)]
        dt = DTS[(j // len(G_QS)) % len(DTS)]
        p = ["", "问一下，", "在吗，", "问个问题，"][(j // (len(G_QS) * len(DTS))) % 4]
        out.append(single(p + q, anss[j % len(anss)], dt=dt))
        j += 1
    seen, uniq = set(), []
    for r in out:
        k = (norm(r["messages"][0]["content"]), norm(r["messages"][1]["content"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq[:250]


# ================================================================ H 自主 A/C 240
H_FACTS = [("下周三要去无锡开会", "你下周三要去无锡开会"),
           ("周五晚上十点去健身", "你周五晚上十点去健身"),
           ("下个月去无锡出差", "你下个月去无锡出差"),
           ("每周三晚上八点有组会", "你每周三晚上八点有组会"),
           ("老家在济南", "你老家在济南"),
           ("养的猫叫芝麻", "你养的猫叫芝麻"),
           ("车是白色 SUV", "你车是白色 SUV"),
           ("对青霉素过敏", "你对青霉素过敏"),
           ("生日是 10 月 12 号", "你生日是 10 月 12 号"),
           ("银行卡尾号 5590", "你银行卡尾号是 5590")]
H_USER = ["今天加班到现在，累死了", "刚开完会，脑子嗡嗡的", "在吗，有点无聊", "这两天事情好多",
          "刚到家，瘫了", "今天心情一般", "在吗，想找人说说话", "感觉最近有点忙不过来",
          "刚吃完饭，歇会儿", "今天跑了一天", "有点烦，想吐槽一下", "在吗",
          "明天又要早起", "这周太赶了", "刚忙完一阵", "今晚不想动",
          "有点困，但还不想睡", "今天效率好低", "外面还挺冷的", "刚洗完澡"]
H_A = ["辛苦了，{f}，早点休息。", "累就缓缓，{f}，别忘了。", "嗯，{f}，先照顾好自己。",
       "忙完了就好，{f}，别熬太晚。", "那记得{f}，别弄岔了。", "行，{f}，有事你说。"]
H_C = ["在呢。{f}，要不要先理一理？", "在。对了，{f}，别忘了。", "我在。{f}，需要我记着吗？",
       "嗯，{f}，要不先把这事安排下？", "{f}，要不这两天先准备下？", "在的。{f}，你看要不要提前弄。"]


def gen_H():
    out = []
    seen = set()

    def add(row):
        m = row["messages"]
        k = (norm(m[0]["content"]), norm("|".join(x["content"] for x in m if x["role"] == "user")))
        if k in seen:
            return False
        seen.add(k)
        out.append(row)
        return True

    i = 0
    while len(out) < 270 and i < 7000:
        fact, tie = H_FACTS[i % len(H_FACTS)]
        u = H_USER[(i // len(H_FACTS)) % len(H_USER)]
        style = i % 2
        tpl = (H_A if style == 0 else H_C)[(i // 7) % 6]
        a = tpl.format(f=tie)
        mems = ["我" + fact]
        if i % 3 == 0:
            mems.append("我" + H_FACTS[(i + 3) % len(H_FACTS)][0])
        dt = DTS[(i * 3) % len(DTS)]
        add(single(u, a, mems=mems, dt=dt))
        i += 1
    return out


# ================================================================ I 未知诚实拒答 90
I_QS = ["我驾照号码是多少？", "我护照号是多少？", "我工资多少？", "我单位电话是多少？",
        "我快递到哪了？", "我社保号是多少？", "我体检报告在哪？", "我车险什么时候到期？",
        "我爱人叫什么名字？", "我爸妈生日是哪天？", "我大学在哪读的？", "我入职时间是哪天？",
        "我医保卡号是多少？", "我公积金多少？", "我上次体检结果怎么样？"]
I_ANS = ["这个我没法确认，你没跟我说过。", "你没提过这个，我记不清就直说。",
         "你没告诉我，我不编。", "这个我这边没有记录，你说一下我就记着。",
         "我记忆里没有这条，不敢瞎说。", "你说的这个我没印象，可能没记过。",
         "这条我查不到，怕说错就不猜了。", "我这边没存过这个，你补一句我就记着。"]


def gen_I():
    out = []
    for qi, q in enumerate(I_QS):
        for di, dt in enumerate(DTS):
            ans = I_ANS[(qi + di) % len(I_ANS)]
            out.append(single(q, ans, dt=dt))
            if len(out) >= 110:
                return out
    return out


# ================================================================ J 时间题 50
J_TYPES = ["今天几号？", "今天星期几？", "明天几号？", "明天星期几？", "昨天几号？",
           "后天星期几？", "现在几点？", "今天是几月几号？", "这周还剩几天？"]


def j_answer(q, dt):
    wd = "一二三四五六日"[dt.weekday()]
    tm, ym, at = dt + timedelta(days=1), dt - timedelta(days=1), dt + timedelta(days=2)
    if q.startswith("今天星期"):
        return "今天星期%s。" % wd
    if q.startswith("今天几号"):
        return "今天 %d 月 %d 号。" % (dt.month, dt.day)
    if q.startswith("今天是几月几号"):
        return "今天是 %d 月 %d 号，星期%s。" % (dt.month, dt.day, wd)
    if q.startswith("明天几号"):
        return "明天 %d 月 %d 号。" % (tm.month, tm.day)
    if q.startswith("明天星期"):
        return "明天星期%s。" % "一二三四五六日"[tm.weekday()]
    if q.startswith("昨天几号"):
        return "昨天 %d 月 %d 号。" % (ym.month, ym.day)
    if q.startswith("后天星期"):
        return "后天星期%s。" % "一二三四五六日"[at.weekday()]
    if q.startswith("现在几点"):
        return "现在 %d 点 %02d 分。" % (dt.hour, dt.minute)
    return "这周还剩 %d 天。" % (6 - dt.weekday())


def gen_J():
    out = []
    i = 0
    while len(out) < 90 and i < 400:
        q = J_TYPES[i % len(J_TYPES)]
        dt = DTS[(i // len(J_TYPES)) % len(DTS)]
        p = ["", "问一下，", "在吗，"][(i // (len(J_TYPES) * len(DTS))) % 3]
        out.append(single(p + q, j_answer(q, dt), dt=dt))
        i += 1
    return out


# ================================================================ 底座补强 80
def gen_boost():
    out = []
    seen = set()

    def add(row):
        m = row["messages"]
        k = (norm(m[0]["content"]), norm("|".join(x["content"] for x in m if x["role"] == "user")))
        if k in seen:
            return False
        seen.add(k)
        out.append(row)
        return True

    # 40 条银行卡尾号族正样本（3046/8821/5590，禁 7418）
    tails = ["3046", "8821", "5590"]
    qs = ["我银行卡尾号是多少？", "我卡尾号是哪个？", "我那张卡尾号多少？", "我工资卡尾号是几？",
          "我卡号后四位是多少？"]
    mem_tpls = ["我的银行卡尾号是%s", "我工资卡尾号%s", "我常用的卡尾号是%s",
                "我新办的卡尾号%s", "我储蓄卡尾号%s"]
    contexts = ["我同事卡尾号 6677", "我爱人的卡尾号 8890", "我另一张卡尾号 2266",
                "我信用卡尾号 3344"]
    i = 0
    while sum(1 for r in out if "银行卡" in r["messages"][0]["content"] or "尾号" in r["messages"][0]["content"]) < 52 and i < 700:
        t = tails[i % len(tails)]
        mem = mem_tpls[(i // len(tails)) % len(mem_tpls)] % t
        mems = [mem]
        if i % 2 == 0:
            mems.append(contexts[(i // 2) % len(contexts)])
        rng.shuffle(mems)
        q = qs[(i // 3) % len(qs)]
        ans = ["你银行卡尾号是%s。" % t, "你卡尾号是%s。" % t, "按记忆你尾号是%s。" % t][i % 3]
        add(single(q, ans, mems=mems, dt=DTS[(i + 2) % len(DTS)]))
        i += 1
    # 40 条 meta 变体（多轮/单轮）
    meta_qs = ["你有记忆吗？", "你现在记得几条？", "你的记忆存在哪？", "你会忘记我吗？",
               "你记得我们刚才聊了什么吗？", "你有长期记忆吗？", "你会记住我说的话吗？",
               "你记忆里有什么？"]
    meta_ans = ["有，记忆存在本地，你告诉我事实我就记着。",
                "具体几条我没法随时数，但我记着你告诉我的事。",
                "存在本地，不上传。",
                "不会故意忘，记不清的时候我不会乱编。",
                "刚才聊了些日常，你提个具体的事我好对上。",
                "有，长期存在本地，你问我就按记忆答。",
                "会，你告诉我事实就行。",
                "有你告诉我的事，你问具体点我就按记忆答。"]
    j = 0
    while sum(1 for r in out if r["messages"][1]["content"].rstrip("？?") in
              [x.rstrip("？?") for x in meta_qs]) < 52 and j < 700:
        q = meta_qs[j % len(meta_qs)]
        ans = meta_ans[j % len(meta_ans)]
        dt = DTS[j % len(DTS)]
        if j % 5 == 0:  # 多轮变体
            turns = [("在吗", "在呢，你说。"), (q, ans)]
            add(multi(turns, None, dt))
        else:
            p = ["", "问一下，", "在吗，", "问个问题，"][(j // len(meta_qs)) % 4]
            add(single(p + q, ans, dt=dt))
        j += 1
    return out[:104]


# ================================================================ 组装 / 校验 / 审计
# 底座 v8b 里与评测值冲突的实体 → 统一替换为训练专用值（保留全部 1602 行，仅换值）
BASE_REPL = [
    ("布丁", "年糕"), ("团子", "饭团"), ("咪咪", "花花"), ("可乐", "汤圆"), ("奶糖", "芝麻"),
    ("杭州", "无锡"), ("成都", "常州"), ("北京", "苏州"), ("上海", "青岛"),
    ("广州", "南通"), ("深圳", "扬州"), ("沪A", "苏A"), ("小米", "用友"),
    ("华为", "中兴"), ("B座", "A座"), ("DeepSeek", "开源模型"), ("GPT", "云端模型"),
]


# 底座里过度集中的拒答模板 → 6-8 种等价说法（M3②）
BASE_REFUSAL_VARIANTS = {
    "这个我没法确认：你没跟我说过。": [
        "这个我没法确认，你没跟我说过。", "这条我这边没有记录，你说一下我就记着。",
        "你没提过这个，我记不清就直说。", "我记忆里没有这条，不敢瞎说。",
        "你没告诉我，我不编。", "这条查不到，我怕说错就不猜了。",
        "我这边没存过这个，你补一句我就记下来。"],
    "这条我没法确认，你没提过。": [
        "这条我没法确认，你没提过。", "这个我这边没记录，你说一下我记着。",
        "你没说过这个，我不敢乱讲。", "我记忆里没有这一条，就不猜了。",
        "这条我查不到，你说清楚我再记。"],
    "这个我没法查，我没有实时数据。": [
        "这个我没法查，我没有实时数据。", "查不到，我连不了网。",
        "这类信息我拿不到，手机上看看更准。", "我没有实时数据，帮不上这个。",
        "这个得你自己查一下，我这边拿不到。"],
    "这条我不能帮，超出我的边界。": [
        "这条我不能帮，超出我的边界。", "这个我帮不了，不在我能做的范围里。",
        "抱歉，这个我做不了。", "这件事我插不上手，你另想办法吧。",
        "我没法处理这种请求。"],
}


def sanitize_base(rows):
    """底座：评测冲突实体值替换 + 拒答模板多样化；行数与结构不变。"""
    repl = collections.Counter()

    def fix(s):
        s = str(s)
        for a, b in BASE_REPL:
            if a in s:
                repl[a] += s.count(a)
                s = s.replace(a, b)
        return s

    rv = collections.Counter()
    out = []
    for idx, r in enumerate(rows):
        nr = {"messages": [{"role": m["role"], "content": fix(m["content"])} for m in r["messages"]]}
        a = nr["messages"][-1]["content"]
        if a in BASE_REFUSAL_VARIANTS:
            vs = BASE_REFUSAL_VARIANTS[a]
            newa = vs[idx % len(vs)]
            if newa != a:
                rv[a] += 1
                nr["messages"][-1]["content"] = newa
        out.append(nr)
    return out, dict(repl), dict(rv)


def load_base():
    rows = []
    with open(BASE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def check_row(r, part):
    m = r["messages"]
    if len(m) < 3 or m[0].get("role") != "system":
        return "structure"
    if (len(m) - 1) % 2 != 0:
        return "structure"
    roles = [x["role"] for x in m]
    if roles[0] != "system" or not all(roles[k] == "user" and roles[k + 1] == "assistant"
                                       for k in range(1, len(m) - 1, 2)):
        return "structure"
    for x in m:
        if x["role"] == "user" and not str(x["content"]).strip():
            return "empty-user"
        if x["role"] == "assistant":
            c = str(x["content"])
            if not c.strip() or len(c) < 4:
                return "short-assistant"
            if c.startswith("对了，"):
                return "bad-prefix"
    txt = json.dumps(r, ensure_ascii=False)
    if BANNED_RE.search(txt):
        return "banned"
    if part == "A":
        for x in m:
            c = str(x["content"])
            if x["role"] == "assistant" and ("我记下了" in c or "已记住" in c):
                return "A-memory-narration"
    if re.search(r"别吃|换药|不能吃", txt):
        return "health-forbidden"
    if eval_hits(txt):
        return "eval-value"
    if part == "A":
        if row_chars(r) > BUDGET_CHARS or row_tokens(r) > BUDGET_TOKENS:
            return "over-budget"
    elif row_chars(r) > 900:
        return "over-budget"
    return None


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


TARGETS = {"A": 800, "B": 300, "C": 120, "D": 260, "E": 260, "F": 260,
           "G": 220, "H": 240, "I": 90, "J": 50, "BOOST": 0}
A_MODES = {"a": 400, "b": 240, "c": 160}


def main():
    base_raw = load_base()
    base, base_repl, base_refusal_div = sanitize_base(base_raw)
    gen = {
        "A": gen_A(), "B": gen_B(), "C": gen_C(), "D": gen_D(), "E": gen_E(),
        "F": gen_F(), "G": gen_G(), "H": gen_H(), "I": gen_I(), "J": gen_J(),
        "BOOST": gen_boost(),
    }
    built = {p: len(v) for p, v in gen.items()}
    parts, rejects = {}, collections.Counter()
    for part, rows in gen.items():
        ok = []
        for r in rows:
            why = check_row(r, part)
            if why:
                rejects[why] += 1
                continue
            r["_part"] = part
            ok.append(r)
        parts[part] = ok
    order = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "BOOST")
    seen, all_rows, dup, dup_base = set(), [], 0, 0
    def full_key(r):
        m = r["messages"]
        return (norm(m[0]["content"]),
                "|".join(norm(x["content"]) for x in m if x["role"] == "user"),
                "|".join(norm(x["content"]) for x in m if x["role"] == "assistant"))

    base_kept = 0
    for r in base:  # 底座按"完全重复三元组"去重（保序保留首次出现）
        k = full_key(r)
        if k in seen:
            dup_base += 1
            continue
        seen.add(k)
        base_kept += 1
        all_rows.append(r)
    for r in [r for p in order for r in parts[p]]:
        k = full_key(r)
        if k in seen:
            dup += 1
            continue
        seen.add(k)
        all_rows.append(r)
    counts = collections.Counter()
    keep = []
    for r in all_rows:
        p = r.get("_part")
        if p is None:
            counts["base"] += 1
            keep.append(r)
            continue
        if p == "A":
            mode = r.get("_m", "a")
            if counts["A_" + mode] >= A_MODES.get(mode, 0):
                continue
            counts["A_" + mode] += 1
            counts["A"] += 1
            keep.append(r)
            continue
        if counts[p] >= TARGETS.get(p, 0):
            continue
        counts[p] += 1
        keep.append(r)
    for r in keep:
        r.pop("_part", None)
        r.pop("_m", None)
    forbidden = [r for r in keep if eval_hits(json.dumps(r, ensure_ascii=False))]
    if forbidden:
        hits = collections.Counter()
        for r in forbidden:
            for h in eval_hits(json.dumps(r, ensure_ascii=False)):
                hits[h] += 1
        print("VALUE_POOL_ASSERT_FAIL", json.dumps(dict(hits), ensure_ascii=False), flush=True)
        raise SystemExit(3)
    rng.shuffle(keep)
    uniq = keep
    multi_rows = [r for r in uniq if len(r["messages"]) > 3]
    def _pct(arr, q):
        return arr[min(len(arr) - 1, int(math.ceil(q * (len(arr) - 1))))]

    all_toks = sorted(row_tokens(r) for r in uniq) or [0]
    toks = sorted(row_tokens(r) for r in multi_rows) or [0]
    p95 = _pct(toks, 0.95)
    banned_hits = {b: sum(1 for r in uniq if b in json.dumps(r, ensure_ascii=False)) for b in BANNED}
    empty_user = sum(1 for r in uniq if any(x["role"] == "user" and not str(x["content"]).strip()
                                            for x in r["messages"]))
    rounds_dist = collections.Counter((len(r["messages"]) - 1) // 2 for r in multi_rows)
    blocks_dist = collections.Counter(mem_blocks(r["messages"][0]["content"]) for r in multi_rows)
    # A 类三态实际分布（显式语义 / 纯位置 / 只挂旧值）
    mode_final = collections.Counter()
    for r in uniq:
        if r.get("_part") or len(r["messages"]) <= 3:
            continue
    for r in uniq:
        if len(r["messages"]) <= 3:
            continue
        s0 = r["messages"][0]["content"]
        if "以前" in s0 or "原来" in s0 or "从" in s0 or "改成" in s0 or "改到" in s0 or "换" in s0:
            mode_final["explicit_semantic"] += 1
        elif "旧" not in s0 and "新" not in s0:
            mode_final["positional_or_old_only"] += 1
    os.makedirs(OUT, exist_ok=True)
    paths = []
    for fn in ("train_v9.jsonl", "data_v9.jsonl"):
        fp = os.path.join(SFT, fn)
        with open(fp, "w", encoding="utf-8") as f:
            for r in uniq:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        paths.append(fp)
    audit = {
        "schema": "sft_data_v9_audit",
        "task": "TASK-083/TASK-086/TASK-088",
        "seed": SEED,
        "base_file": os.path.relpath(BASE, ROOT),
        "base_rows": len(base),
        "base_rows_kept": base_kept,
        "base_duplicate_rows_removed": dup_base,
        "base_refusal_diversified": base_refusal_div,
        "rows": len(uniq),
        "generated_rows": len(uniq) - len(base),
        "built_before_filter": built,
        "planned": {"base": base_kept, "boost": counts.get("BOOST", 0),
                    "A_multi_memory": counts.get("A", 0), "B_capability": counts.get("B", 0),
                    "C_action_refusal": counts.get("C", 0), "D_realtime_refusal": counts.get("D", 0),
                    "E_memory_pos": counts.get("E", 0), "F_chitchat": counts.get("F", 0),
                    "G_identity_meta": counts.get("G", 0), "H_autonomy": counts.get("H", 0),
                    "I_unknown": counts.get("I", 0), "J_time": counts.get("J", 0)},
        "A_modes": {"explicit_semantic": counts.get("A_a", 0), "positional": counts.get("A_b", 0),
                    "old_only": counts.get("A_c", 0)},
        "rejects": dict(rejects),
        "E_card_family_rows": sum(1 for r in keep if len(r["messages"]) == 3 and
                                  ("银行卡" in r["messages"][1]["content"] or "尾号" in r["messages"][1]["content"])
                                  and r["messages"][1]["content"].startswith(("我银行卡", "我卡尾号", "我那张卡", "我工资卡", "我卡号后四位"))),
        "B_long_code_rows": sum(1 for r in keep if "```python" in r["messages"][-1]["content"]
                                and len(r["messages"][-1]["content"]) > 300),
        "duplicates_dropped": dup,
        "multi_turn_rows": len(multi_rows),
        "multi_turn_rounds_dist": dict(sorted(rounds_dist.items())),
        "multi_turn_rounds_6_8_rows": sum(v for k, v in rounds_dist.items() if k >= 6),
        "multi_turn_mem_blocks_6_rows": sum(1 for r in multi_rows
                                            if mem_blocks(r["messages"][0]["content"]) >= 6),
        "multi_turn_mem_blocks_dist": dict(sorted(blocks_dist.items())),
        "prompt_tokens_est": {
            "method": "完整 prompt 估算：内容 tokens(CJK=1.0/alnum=0.34/other=0.55) + 每条消息角色/模板开销 4 + 起始 3，含 system",
            "all_rows": {"max": round(all_toks[-1], 1), "p95": round(_pct(all_toks, 0.95), 1),
                         "rows_over_512": sum(1 for t in all_toks if t > 512),
                         "rows_over_480": sum(1 for t in all_toks if t > 480)},
            "multi_turn_rows": {"max": round(toks[-1], 1), "p95": round(p95, 1),
                                "rows_over_512": sum(1 for t in toks if t > 512),
                                "rows_over_480": sum(1 for t in toks if t > 480)},
            "chars_max_multi": max((row_chars(r) for r in multi_rows), default=0),
            "chars_max_all": max(row_chars(r) for r in uniq),
        },
        "multi_turn_tokens_est": {"max": round(toks[-1], 1), "p95": round(p95, 1),
                                  "chars_max": max((row_chars(r) for r in multi_rows), default=0),
                                  "note": "旧口径（仅消息段），已由 prompt_tokens_est 取代"},
        "empty_user_rows": empty_user,
        "banned_value_hits": banned_hits,
        "value_pool_check": {
            "pass": True,
            "eval_file": os.path.relpath(EVAL_FILE, ROOT),
            "eval_values_independent_n": len(EVAL_VALUES),
            "fixture_values_n": len(FIXTURE_VALUES),
            "enforced_n": len(ENFORCED),
            "enforced_sample": ENFORCED[:20],
            "exempt_generic_n": len(EXEMPT),
            "exempt_reason": "代码关键字/通用词汇/中文数词/时间槽/纯数字：禁用会与定稿规格冲突"
                             "（B 类必须含 def、policy 必含记忆/助手、算术/日期必含数字）",
            "conflicts_in_train_blob": {},
            "base_value_replacements": base_repl,
        },
        "files": {},
    }
    for fp in paths:
        audit["files"][os.path.relpath(fp, ROOT)] = sha256_file(fp)
    with open(os.path.join(OUT, "SFT-DATA-v9-AUDIT.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in audit.items() if k != "files"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
