# -*- coding: utf-8 -*-
"""40k 压测数据生成器（纯 CPU，无模型调用，无真实记忆）。

输出（out/scale40k/）：
  blocks_200.jsonl   200 行记忆块
  queries_100.jsonl  100 条查询
  manifest.json      统计 + sha256

结构：
  120 唯一事实 = 10 族 x 12 owner（同族值仅差末位/末字）
   40 冲突链块 = 10 链 x A/B/C/D（同 owner+predicate，值依次更新）
   40 噪声块   = 纯闲聊，无可检索事实
"""
import hashlib
import json
import os
import random
import re

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scale40k")
SEED = 40000

# ---------------------------------------------------------------- owners
OWNERS = ["张伟", "李娜", "王强", "刘敏", "陈杰", "杨帆",
          "赵磊", "黄婷", "周昊", "吴静", "徐斌", "孙悦"]
CHAIN_OWNERS = ["郑凯", "冯樱", "韩峥", "曹岚", "邓辉",
                "沈越", "卢婷", "蒋川", "蔡敏", "潘石"]

# ---------------------------------------------------------------- families
# 10 族；每族 12 个值，同族值只在末位/末字上不同（高相似对抗）
FAMILIES = {}

FAMILIES["cat"] = dict(
    predicate="cat_name", key=False,
    values=["小橘", "小柚", "小柠", "小栗", "小桃", "小杏",
            "小梅", "小竹", "小松", "小柏", "小枫", "小桐"],
    noun="猫的名字",
    fact="{o}说起过，家里那只猫叫{v}，平时就爱趴在窗台上晒太阳。",
    q_direct="{o}家那只猫叫什么名字？",
    q_para="{o}那只猫，名字是啥来着？",
)
FAMILIES["dog"] = dict(
    predicate="dog_name", key=False,
    values=["阿福", "阿旺", "阿财", "阿宝", "阿贵", "阿顺",
            "阿康", "阿泰", "阿平", "阿和", "阿乐", "阿喜"],
    noun="狗的名字",
    fact="{o}提到过，自己养的那条狗叫{v}，见谁都摇尾巴。",
    q_direct="{o}养的那条狗叫什么？",
    q_para="{o}家那条狗叫啥？",
)
FAMILIES["plate"] = dict(
    predicate="plate", key=True,
    values=["京N·7K3Q0", "京N·7K3Q1", "京N·7K3Q2", "京N·7K3Q3",
            "京N·7K3Q4", "京N·7K3Q5", "京N·7K3Q6", "京N·7K3Q7",
            "京N·7K3Q8", "京N·7K3Q9", "京N·7K3QA", "京N·7K3QB"],
    noun="车牌号",
    fact="{o}的车的车牌号是{v}，他说这串字符当初记了好久。",
    q_direct="{o}的车牌号是多少？",
    q_para="{o}那车牌子你还记得不？",
)
FAMILIES["phone"] = dict(
    predicate="phone", key=False,
    values=["13910002001", "13910002002", "13910002003", "13910002004",
            "13910002005", "13910002006", "13910002007", "13910002008",
            "13910002009", "13910002010", "13910002011", "13910002012"],
    noun="手机号",
    fact="{o}留的手机号是{v}，平时不太接陌生来电。",
    q_direct="{o}的手机号码是多少？",
    q_para="{o}号码多少来着？",
)
FAMILIES["bank"] = dict(
    predicate="bank_card", key=True,
    values=["6222 0201 8830 4401", "6222 0201 8830 4402", "6222 0201 8830 4403",
            "6222 0201 8830 4404", "6222 0201 8830 4405", "6222 0201 8830 4406",
            "6222 0201 8830 4407", "6222 0201 8830 4408", "6222 0201 8830 4409",
            "6222 0201 8830 4410", "6222 0201 8830 4411", "6222 0201 8830 4412"],
    noun="银行卡号",
    fact="{o}那张工资卡的卡号是{v}，一直没换过银行。",
    q_direct="{o}的银行卡卡号是多少？",
    q_para="{o}那张工资卡号是多少呀？",
)
FAMILIES["company"] = dict(
    predicate="company", key=False,
    values=["杭州云枢网络科技有限公司一部", "杭州云枢网络科技有限公司二部",
            "杭州云枢网络科技有限公司三部", "杭州云枢网络科技有限公司四部",
            "杭州云枢网络科技有限公司五部", "杭州云枢网络科技有限公司六部",
            "杭州云枢网络科技有限公司七部", "杭州云枢网络科技有限公司八部",
            "杭州云枢网络科技有限公司九部", "杭州云枢网络科技有限公司十部",
            "杭州云枢网络科技有限公司十一部", "杭州云枢网络科技有限公司十二部"],
    noun="公司",
    fact="{o}现在在{v}上班，主要做后台相关的事情。",
    q_direct="{o}现在在哪家公司上班？",
    q_para="{o}单位是哪个来着？",
)
FAMILIES["meeting"] = dict(
    predicate="meeting_time", key=True,
    values=["2026-11-02 14:01", "2026-11-02 14:02", "2026-11-02 14:03",
            "2026-11-02 14:04", "2026-11-02 14:05", "2026-11-02 14:06",
            "2026-11-02 14:07", "2026-11-02 14:08", "2026-11-02 14:09",
            "2026-11-02 14:10", "2026-11-02 14:11", "2026-11-02 14:12"],
    noun="重要会议时间",
    fact="{o}下周那个重要会议定在{v}，得提前把材料准备好。",
    q_direct="{o}下周那个重要会议安排在什么时间？",
    q_para="{o}那个会定在几号几点了？",
)
FAMILIES["hometown"] = dict(
    predicate="hometown", key=False,
    values=["临安", "临海", "临江", "临川", "临汾", "临泉",
            "临夏", "临清", "临湘", "临沧", "临沂", "临颍"],
    noun="老家",
    fact="{o}的老家是{v}，每年也就过节回去一趟。",
    q_direct="{o}的老家是哪里？",
    q_para="{o}是哪儿人？",
)
FAMILIES["car_color"] = dict(
    predicate="car_color", key=False,
    values=["珍珠白", "珍珠黑", "珍珠灰", "珍珠蓝", "珍珠银", "珍珠金",
            "珍珠红", "珍珠绿", "珍珠紫", "珍珠棕", "珍珠青", "珍珠粉"],
    noun="车的颜色",
    fact="{o}那辆车是{v}的，洗完车之后特别显新。",
    q_direct="{o}那辆车是什么颜色？",
    q_para="{o}车子什么颜色的？",
)
FAMILIES["seat"] = dict(
    predicate="seat", key=False,
    values=["5排01号", "5排02号", "5排03号", "5排04号", "5排05号", "5排06号",
            "5排07号", "5排08号", "5排09号", "5排10号", "5排11号", "5排12号"],
    noun="座位号",
    fact="{o}这次活动的座位排在了{v}，说是视野还行。",
    q_direct="{o}这次活动的座位号是多少？",
    q_para="{o}坐哪个位置？",
)

FAMILY_ORDER = ["cat", "dog", "plate", "phone", "bank",
                "company", "meeting", "hometown", "car_color", "seat"]

# ---------------------------------------------------------------- chains
CHAIN_SPEC = [
    # (chain_id, owner, family, [A,B,C,D], 谓词中文)
    ("ch01", "郑凯", "plate", ["沪B·5M8T1", "沪B·5M8T3", "沪B·5M8T5", "沪B·5M8T7"], "车牌号"),
    ("ch02", "冯樱", "company", ["宁波启元数据服务有限公司一部", "宁波启元数据服务有限公司二部",
                               "宁波启元数据服务有限公司三部", "宁波启元数据服务有限公司四部"], "公司"),
    ("ch03", "韩峥", "phone", ["13720013001", "13720013002", "13720013003", "13720013004"], "手机号"),
    ("ch04", "曹岚", "bank", ["6217 0012 3456 7801", "6217 0012 3456 7802",
                            "6217 0012 3456 7803", "6217 0012 3456 7804"], "银行卡号"),
    ("ch05", "邓辉", "meeting", ["2026-11-05 09:30", "2026-11-06 09:30",
                               "2026-11-09 14:00", "2026-11-12 10:00"], "会议时间"),
    ("ch06", "沈越", "seat", ["7排05号", "7排09号", "6排12号", "4排03号"], "座位号"),
    ("ch07", "卢婷", "car_color", ["珍珠白", "星空灰", "曜石黑", "冰川蓝"], "车身颜色"),
    ("ch08", "蒋川", "plate", ["苏E·2P9R4", "苏E·2P9R6", "苏E·2P9R8", "苏E·2P9R0"], "车牌号"),
    ("ch09", "蔡敏", "company", ["苏州明远智能装备有限公司一部", "苏州明远智能装备有限公司二部",
                               "苏州明远智能装备有限公司三部", "苏州明远智能装备有限公司四部"], "公司"),
    ("ch10", "潘石", "phone", ["15860027001", "15860027002", "15860027003", "15860027004"], "手机号"),
]

CHAIN_TMPL = {
    1: "{o}一开始的{p}是{v}，那阵子一直没动过。",
    2: "{o}后来把{p}改成了{v}，中间隔了一段时间。",
    3: "{o}再后来又换成{v}，说是当时有点别的原因。",
    4: "{o}现在用的{p}是{v}，这个是最近才定下来的。",
}

# ---------------------------------------------------------------- fillers
# 纯闲聊：无数字、无实体、无任何可检索事实
FILLERS = [
    "说到这儿我忽然想起来，楼下那家小店门口排了老长的队，我看了两眼就懒得进去了，想着改天有空再说吧。",
    "外面好像要变天了，风一阵一阵的，我先去把窗户关上，顺便把外面晾着的东西收进来，你稍等一下就好。",
    "你上次提的那个法子我后来试了试，能用是能用，就是步骤有点绕，中间还得停下来想一会儿，效率不算高。",
    "这会儿有点犯困，我泡了杯茶提提神，茶还有点烫，得放一会儿才能喝，咱们慢慢说，不用赶时间。",
    "刚才手机响了一下，我还以为是谁找我，拿起来一看是推送广告，懒得点开，就又放回桌上去了。",
    "手边这杯水放凉了，我去续点热的，你要是等得无聊就先自己待一会儿，我很快就回来接着聊。",
    "今天坐得有点久，腰有点发僵，我起来走了两圈，又伸了伸胳膊，现在感觉松快一些了，也能坐得住。",
    "我这会儿在等一个快递，显示还在路上，估计还得一会儿才到，所以我暂时也出不了门，只能在家待着。",
    "屋里灯有点暗，我把台灯挪近了点，光线照着舒服些，看东西也不那么费劲，眼睛没那么酸了。",
    "说实话这些天事情有点杂，脑子转得比平时慢，说话也可能有点跳跃，你别介意，我尽量说清楚。",
    "你要是着急就先忙你的，我这边一点都不急，什么时候有空什么时候聊都行，不用特意腾出时间。",
    "刚才那段话我看了两遍才看明白，可能是我反应慢，也可能是话说得太绕，下回你说得直白点。",
    "窗外有只鸟一直在叫，叫得还挺有节奏，听久了倒也不觉得吵，反而觉得挺安静，心也跟着静下来。",
    "我把椅子调低了一格，这样靠着说话舒服点，坐久了也不至于太累，你也找个舒服的姿势靠着。",
    "说起来这几天胃口一般，晚上打算吃点清淡的，油腻的实在吃不太动，喝点粥就差不多了。",
    "上次那事儿过去就过去了，你也别老放在心上，想开点比什么都强，日子还得照常过，别为这点事耽误心情。",
    "我这边网速偶尔会卡一下，卡完自己又好了，所以刚才没及时回你，不是故意的，你别多想。",
    "桌上东西堆得有点多，我顺手理了理，把不用的挪到一边，现在看着清爽多了，找东西也方便。",
    "你先别急着下结论，慢慢想，想清楚再说也不迟，反正也不差这一会儿，急急忙忙反而容易出错。",
    "我这人说话比较直，有时候不太会绕弯子，有说得不对的地方你多担待点，我不是那个意思。",
    "刚喝了口热水，嗓子舒服多了，刚才说话有点干，现在好多了，接着聊，你也不用特意照顾我。",
    "屋里有点闷，我去把门开条缝透透气，一会儿凉下来再关上，这样坐着能舒服些，也不至于太燥。",
    "这些天睡得晚，白天总有点提不起精神，做什么都慢半拍，看来得早点睡了，不然一直这样下去。",
    "你说得也有道理，我再琢磨琢磨，有些地方确实是我没想周全，等我理清楚了再跟你细说。",
    "我这儿正收拾桌面呢，一边收拾一边跟你说话，手上有点事反而不容易走神，你接着说就行。",
    "天气一凉，人就容易懒，什么都不想干，只想窝着不动，连出门买点东西都想拖到明天再说。",
    "刚才走神了，没太听清，你再说一遍我听听，这回我认真听着，不会再漏掉什么了。",
    "我这会儿心情还行，就是有点累，说话可能没什么力气，你别嫌我敷衍，我确实是在听你说。",
    "咱们不着急，想到哪儿说到哪儿就行，不用非得有个结论，聊得开心比什么都重要。",
    "手边这盆绿植该浇水了，叶子有点蔫，我一会儿得处理一下，不然再放两天就救不回来了。",
    "我一会儿还得出去一趟，不过现在还有空，能聊多久聊多久，等我走了就回头再说。",
    "你这么说我倒是想起来点别的，不过先不岔开，等说完了再说，免得一会儿又忘了。",
    "这两天总想吃点热的，凉的东西吃多了胃里不舒服，所以喝水都得温的，冰的碰都不碰。",
    "我把外套搭在椅背上了，一会儿出门再穿，现在穿着有点热，屋里温度比外面高不少。",
    "刚才楼下有人在搬东西，动静挺大，响了好一阵才消停，现在总算安静下来了，说话也不用抬声音。",
    "我这个人记性一般，重要的事都得靠记下来，光靠脑子容易漏，所以到处都放着便签。",
    "说到这个我就想起上次那顿饭，吃得挺开心，就是聊得太久，回去有点晚，第二天起不来。",
    "你先歇会儿，喝口水，不用一直绷着，放松点反而说得清楚，我这边又不催你，慢慢来。",
    "这会儿安静下来了，窗外也没什么声音，正好说说话，比刚才那种乱糟糟的时候强多了。",
    "我也没什么特别的，就是随便聊聊，你别有压力，想到什么说什么就行，说错了也没关系。",
]

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def cjk_len(s):
    return len(CJK.findall(s))


def build_text(head, rnd, lo=190, hi=222, target=204):
    """事实句 + 3~5 句无信息闲聊，约 200 中文字符。"""
    pool = FILLERS[:]
    best, best_d = None, 10 ** 9
    for _ in range(120):
        rnd.shuffle(pool)
        acc = head
        for n in range(1, 6):
            acc = acc + pool[n - 1]
            if n < 3:
                continue
            c = cjk_len(acc)
            if c > hi + 10:
                break
            d = abs(c - target)
            if lo <= c <= hi and d < best_d:
                best, best_d = acc, d
        if best_d == 0:
            break
    if best is not None:
        return best
    # 兜底：贪心加到下限
    rnd.shuffle(pool)
    acc = head
    for s in pool:
        if cjk_len(acc) >= lo:
            break
        acc += s
    return acc


# ---------------------------------------------------------------- position plan
BANDS = [(0.005, 0.080), (0.145, 0.370), (0.435, 0.475),
         (0.535, 0.670), (0.735, 0.870), (0.935, 0.995)]
ANCHORS = {"A": 0.100, "B": 0.400, "C": 0.700, "D": 0.900}
KEY_ANCHORS = [0.100, 0.500, 0.900]

# 关键事实：每族 4 条，索引固定，保证被查询覆盖
KEY_IDX = {"plate": [0, 3, 6, 9], "bank": [1, 4, 7, 10], "meeting": [2, 5, 8, 11]}


def spread(items, rnd, jitter=0.0):
    """把 items 均匀铺进 BANDS（避开锚点窗口），最大余数法保证不剩尾项。"""
    widths = [b - a for a, b in BANDS]
    total = sum(widths)
    n = len(items)
    raw = [w / total * n for w in widths]
    cnts = [int(x) for x in raw]
    rem = n - sum(cnts)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - cnts[i], reverse=True)
    for i in order[:rem]:
        cnts[i] += 1
    out = []
    k = 0
    for (a, b), cnt in zip(BANDS, cnts):
        for j in range(cnt):
            pos = a + (b - a) * (j + 0.5) / max(cnt, 1)
            if jitter:
                pos += rnd.uniform(-jitter, jitter)
            out.append((items[k], pos))
            k += 1
    assert k == n, (k, n)
    return out


def main():
    rnd = random.Random(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---------- 120 唯一事实 ----------
    facts = []
    for fam in FAMILY_ORDER:
        meta = FAMILIES[fam]
        for i, owner in enumerate(OWNERS):
            facts.append(dict(kind="fact", family=fam, owner=owner,
                              predicate=meta["predicate"],
                              value=meta["values"][i], idx=i,
                              key=(i in KEY_IDX.get(fam, []))))

    key_facts = [f for f in facts if f["key"]]
    plain_facts = [f for f in facts if not f["key"]]
    assert len(key_facts) == 12, len(key_facts)

    # 关键事实：3 锚点 × 4 条，每锚点内覆盖 3 个族
    key_facts.sort(key=lambda f: (["plate", "bank", "meeting"].index(f["family"]), f["idx"]))
    placed = []
    for j, f in enumerate(key_facts):
        anchor = KEY_ANCHORS[j % 3]
        f["position"] = round(anchor + 0.0008 * (j // 3 + 1), 4)
        placed.append(f)

    # ---------- 40 冲突链 ----------
    chain_blocks = []
    for cid, owner, fam, vals, noun in CHAIN_SPEC:
        for step, v in enumerate(vals, start=1):
            chain_blocks.append(dict(
                kind="chain", family=fam, owner=owner,
                predicate=FAMILIES[fam]["predicate"], value=v,
                chain_id=cid, chain_seq=step, chain_noun=noun,
                position=round(ANCHORS["ABCD"[step - 1]] + 0.0008 * (int(cid[2:]) - 1), 4)))

    # ---------- 40 噪声 ----------
    noise = [dict(kind="noise", family="noise", owner="", predicate="", value="")
             for _ in range(40)]

    # ---------- 位置铺设 ----------
    free_facts = spread(plain_facts, rnd, jitter=0.002)
    for f, pos in free_facts:
        f["position"] = round(pos, 4)
    free_noise = spread(noise, rnd, jitter=0.002)
    for nb, pos in free_noise:
        nb["position"] = round(pos, 4)

    all_blocks = placed + plain_facts + chain_blocks + noise
    assert len(all_blocks) == 200, len(all_blocks)

    # 排序 → 定 id（稳定：position 升序，同位置按 kind 权重）
    kind_rank = {"fact": 0, "chain": 1, "noise": 2}
    all_blocks.sort(key=lambda b: (b["position"], kind_rank[b["kind"]],
                                   b.get("chain_id", ""), b.get("chain_seq", 0)))
    for n, b in enumerate(all_blocks, start=1):
        b["id"] = "b%04d" % n

    # ---------- 文本 ----------
    for b in all_blocks:
        r = random.Random(SEED * 7 + int(b["id"][1:]))
        if b["kind"] == "noise":
            head = ""
        elif b["kind"] == "fact":
            head = FAMILIES[b["family"]]["fact"].format(o=b["owner"], v=b["value"])
        else:
            head = CHAIN_TMPL[b["chain_seq"]].format(
                o=b["owner"], p=b["chain_noun"], v=b["value"])
        b["text"] = build_text(head, r)

    # ---------- 写 blocks_200 ----------
    fields = ["id", "text", "family", "owner", "predicate", "value", "kind"]
    lines = []
    for b in all_blocks:
        rec = {k: b[k] for k in fields}
        if b["kind"] == "chain":
            rec["chain_id"] = b["chain_id"]
            rec["chain_seq"] = b["chain_seq"]
        rec["position"] = b["position"]
        lines.append(json.dumps(rec, ensure_ascii=False))
    blocks_path = os.path.join(OUT_DIR, "blocks_200.jsonl")
    with open(blocks_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    # ---------- 索引 ----------
    fact_id = {}
    for b in all_blocks:
        if b["kind"] == "fact":
            fact_id[(b["family"], b["owner"])] = b["id"]
    chain_id = {}
    for b in all_blocks:
        if b["kind"] == "chain":
            chain_id.setdefault((b["chain_id"], b["chain_seq"]), b["id"])

    def variants(v):
        out = [v]
        nz = v.replace(" ", "")
        if nz != v:
            out.append(nz)
        nz2 = v.replace("·", "")
        if nz2 != v and nz2 not in out:
            out.append(nz2)
        return out

    # ---------- 查询 ----------
    queries = []

    def q(text, target, expect, notc, kind):
        queries.append(dict(id="q%03d" % (len(queries) + 1), text=text,
                            target_block_id=target, expect_any=expect,
                            not_contains=notc, kind=kind))

    # 40 直接问：每族 4 条
    for fam in FAMILY_ORDER:
        meta = FAMILIES[fam]
        idxs = KEY_IDX.get(fam, [0, 3, 6, 9])
        for i in idxs:
            owner = OWNERS[i]
            v = meta["values"][i]
            q(meta["q_direct"].format(o=owner),
              fact_id[(fam, owner)], variants(v), [], "direct")

    # 30 同义/口语改写：每族 3 条
    for fam in FAMILY_ORDER:
        meta = FAMILIES[fam]
        for i in (2, 5, 8):
            owner = OWNERS[i]
            v = meta["values"][i]
            q(meta["q_para"].format(o=owner),
              fact_id[(fam, owner)], variants(v), [], "paraphrase")

    # 20 冲突链"最后值"：每链 2 条
    for cid, owner, fam, vals, noun in CHAIN_SPEC:
        tgt = chain_id[(cid, 4)]
        old = vals[:3]
        notc = []
        for v in old:
            notc.extend(variants(v))
        q("{o}现在的{p}是什么？".format(o=owner, p=noun), tgt,
          variants(vals[3]), notc, "chain_last")
        q("{o}最新的{p}是哪个？之前那些都不算了。".format(o=owner, p=noun), tgt,
          variants(vals[3]), notc, "chain_last")

    # 10 负例
    # 6 条：问旧值（不引用旧串，只问"还是最早那个吗"）
    for cid, owner, fam, vals, noun in CHAIN_SPEC[:6]:
        tgt = chain_id[(cid, 4)]
        notc = []
        for v in vals[:3]:
            notc.extend(variants(v))
        q("{o}的{p}还是最早那个吗？".format(o=owner, p=noun), tgt,
          variants(vals[3]), notc, "negative")
    # 2 条：问伪造值（该串不存于任何块，且与谓词类型一致）
    fake = [("ch07", "琉璃金"), ("ch08", "苏E·7Q1W2")]
    for cid, fv in fake:
        spec = [c for c in CHAIN_SPEC if c[0] == cid][0]
        _, owner, fam, vals, noun = spec
        tgt = chain_id[(cid, 4)]
        notc = variants(fv)
        for v in vals[:3]:
            notc.extend(variants(v))
        q("{o}的{p}是不是{f}？".format(o=owner, p=noun, f=fv), tgt,
          variants(vals[3]), notc, "negative")
    # 2 条：问不存在的事实
    q("郑凯的护照号码是多少？", None, ["不知道", "没有记录", "不清楚", "没提过", "无法确定"],
      ["E12345678"], "negative")
    q("冯樱的驾照什么时候到期？", None, ["不知道", "没有记录", "不清楚", "没提过", "无法确定"],
      ["2031-05-06"], "negative")

    assert len(queries) == 100, len(queries)
    assert [x["kind"] for x in queries].count("direct") == 40
    assert [x["kind"] for x in queries].count("paraphrase") == 30
    assert [x["kind"] for x in queries].count("chain_last") == 20
    assert [x["kind"] for x in queries].count("negative") == 10

    queries_path = os.path.join(OUT_DIR, "queries_100.jsonl")
    with open(queries_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(json.dumps(x, ensure_ascii=False) for x in queries) + "\n")

    # ---------- 校验 ----------
    all_vals = [b["value"] for b in all_blocks if b["value"]]
    for x in queries:
        for v in all_vals:
            assert v not in x["text"], ("查询泄露稀有串", x["id"], v)
            nz = v.replace(" ", "")
            assert nz not in x["text"].replace(" ", ""), ("查询泄露稀有串(去空格)", x["id"], v)
    # 噪声块不得含数字/实体
    for b in all_blocks:
        if b["kind"] == "noise":
            assert not re.search(r"[0-9]", b["text"]), b["id"]
    # 冲突链：同 owner+predicate，值全不同
    for cid, owner, fam, vals, noun in CHAIN_SPEC:
        blocks = [b for b in all_blocks if b["kind"] == "chain" and b["chain_id"] == cid]
        assert len(blocks) == 4
        assert all(b["owner"] == owner and b["predicate"] == FAMILIES[fam]["predicate"] for b in blocks)
        assert len({b["value"] for b in blocks}) == 4
        assert len({b["position"] for b in blocks}) == 4

    # ---------- manifest ----------
    def dist(seq):
        d = {}
        for s in seq:
            d[s] = d.get(s, 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    poss = [b["position"] for b in all_blocks]
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for p in poss:
        if p < 0.2:
            buckets["0.0-0.2"] += 1
        elif p < 0.4:
            buckets["0.2-0.4"] += 1
        elif p < 0.6:
            buckets["0.4-0.6"] += 1
        elif p < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1

    def in_win(p, a):
        return a - 0.012 <= p <= a + 0.012

    anchors = {
        "~0.1": sum(1 for p in poss if in_win(p, 0.1)),
        "~0.4": sum(1 for p in poss if in_win(p, 0.4)),
        "~0.5": sum(1 for p in poss if in_win(p, 0.5)),
        "~0.7": sum(1 for p in poss if in_win(p, 0.7)),
        "~0.9": sum(1 for p in poss if in_win(p, 0.9)),
    }

    def sha(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    texts = [b["text"] for b in all_blocks]
    qtexts = [x["text"] for x in queries]
    key_report = [{"id": b["id"], "family": b["family"], "owner": b["owner"],
                   "value": b["value"], "position": b["position"]}
                  for b in all_blocks if b.get("key")]
    assert len(key_report) == 12

    manifest = {
        "generated_by": "SCALE-40K-GEN.py (CPU only, no model calls, synthetic)",
        "seed": SEED,
        "files": {"blocks": "blocks_200.jsonl", "queries": "queries_100.jsonl"},
        "totals": {"blocks": len(all_blocks), "queries": len(queries),
                   "unique_facts": 120, "chain_blocks": 40, "noise_blocks": 40,
                   "families": 10, "chains": 10, "chain_len": 4},
        "family_dist": dist([b["family"] for b in all_blocks]),
        "kind_dist": dist([b["kind"] for b in all_blocks]),
        "query_kind_dist": dist([x["kind"] for x in queries]),
        "position_dist": buckets,
        "position_anchors": anchors,
        "chain_position_targets": {"A": 0.1, "B": 0.4, "C": 0.7, "D": 0.9},
        "key_fact_anchor_targets": [0.1, 0.5, 0.9],
        "key_facts": key_report,
        "chinese_chars": {
            "blocks_total": sum(cjk_len(t) for t in texts),
            "blocks_avg": round(sum(cjk_len(t) for t in texts) / len(texts), 2),
            "blocks_min": min(cjk_len(t) for t in texts),
            "blocks_max": max(cjk_len(t) for t in texts),
            "queries_total": sum(cjk_len(t) for t in qtexts),
        },
        "sha256": {
            "blocks_200.jsonl": sha(blocks_path),
            "queries_100.jsonl": sha(queries_path),
        },
        "notes": [
            "同族 12 值仅在末位/末字上不同（company 为尾部分部编号），制造高相似检索对抗。",
            "冲突链每块只陈述自身值，不引用旧值，避免 not_contains 误伤。",
            "查询文本不含任何块的完整值串（生成后已程序校验）。",
            "负例 4 类：问旧值 6 / 伪造值 2 / 不存在 2；不存在类 target_block_id 为 null。",
        ],
    }
    mpath = os.path.join(OUT_DIR, "manifest.json")
    with open(mpath, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(json.dumps({k: manifest[k] for k in
                      ("totals", "family_dist", "kind_dist", "query_kind_dist",
                       "position_dist", "position_anchors", "chinese_chars", "sha256")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()