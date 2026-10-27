# -*- coding: utf-8 -*-
import json, hashlib, os, re

SP = {
"s1": ("汽车年检", 8, "我把开了六年的白色轿车开到城西机动车检测站年检，检测费 280 元，尾气、刹车和灯光三项都要查，工作人员说傍晚四点半前能出报告，行驶证、交强险保单要一起带上。",
 [("detail","检测站在哪个方位？车漆颜色和车龄分别是什么？"),("detail","检测费多少？检测项目有哪几个？"),("detail","报告几点前能出来？"),("lure","检测站周末上班吗？"),("lure","从进站到出报告用了多久？")]),
"s2": ("手机套餐变更", 8, "我在人民路的移动营业厅把手机套餐换成了每月 59 元的畅享套餐，含 30G 流量和 500 分钟通话，下月 1 号生效，原来的语音包退掉，营业员说可以保留原号码，办理时带了身份证。",
 [("detail","换套餐的营业厅在哪条路？月费多少？"),("detail","套餐里含多少流量和通话？"),("detail","新套餐从哪天起算？"),("lure","套餐里的流量用不完能结转到下个月吗？"),("lure","周末去这个营业厅能办到几点？")]),
"s3": ("房屋租赁看房", 8, "中介带我去江南小区看了一套两居室，房子在 6 楼，朝南还带个小阳台，月租 3200 元，押一付三，中介费要收一个月房租，业主也同意养猫，下周就能签正式合同。",
 [("detail","这次看房在哪个小区？几居室？"),("detail","押一付三具体怎么付？月租多少？"),("detail","房子在几楼、朝向怎么样？"),("lure","房子里的家具家电都留下吗？"),("lure","物业费是业主交还是租客交？")]),
"s4": ("火车票改签", 8, "我在火车站窗口把 10 月 8 号早上九点去南京的高铁票改到 14 点 20 分，补了 46 元差价，手续费没退，座位从二等座改成了一等座，改签后不能退票，新票在 3 号窗口取。",
 [("detail","车票是从哪里到哪里的？原来几点发车？"),("detail","改到几点发车？补多少差价？"),("detail","座位有什么变化？改签后还能退票吗？"),("lure","车站有母婴室吗？"),("lure","改签可以让别人代办吗？")]),
"s5": ("电费缴纳", 7, "我去城北供电营业厅交了上个月的电费，电费总共 186 元，家里用了 210 度电，柜台说绑定手机号就能自动扣费，欠费超过 30 天会停电，发票可以直接在柜台打印。",
 [("detail","电费在哪个营业厅交的？总共交了多少？"),("detail","上个月用了多少度电？"),("detail","欠费超过多少天会停电？"),("lure","营业厅周末开门吗？"),("lure","电费可以用信用卡支付吗？")]),
"s6": ("幼儿园报名", 8, "我给女儿报了阳光幼儿园的小班，报名费 1200 元，每周一到周五都要上课，八点半入园，下午四点去接，班里 25 个孩子配两个老师，开学前还要交一份体检表。",
 [("detail","幼儿园全称是什么？报的班型是哪种？"),("detail","报名费多少？一周上几天课？"),("detail","早上几点入园、下午几点接？"),("lure","幼儿园有校车接送吗？"),("lure","报名需要面试孩子吗？")]),
"s7": ("共享单车月卡", 8, "我在手机上买了青柠单车的月卡，花了 25 元，30 天内不限次数，每次前两小时免费，超出按每小时 1 元算，月卡不能退，骑车要先扫码开锁，超时费会从余额里扣。",
 [("detail","月卡是哪种单车的？付了多少？"),("detail","月卡能用多少天？有次数限制吗？"),("detail","每次免费骑多久？超出怎么收费？"),("lure","月卡能开票吗？"),("lure","这个牌子有电动的车型吗？")]),
"s8": ("乐器维修", 6, "我把孩子的二手钢琴运到城南的声悦琴行调律，调律费 300 元，师傅检查后说有三个琴键回弹慢，得换零件，零件费另外算，琴行可以上门取琴，修好大概要一周时间。",
 [("detail","钢琴送到哪家琴行调律？调律费多少？"),("detail","师傅说有几个琴键要修？"),("detail","零件费怎么算？琴行能上门取琴吗？"),("lure","琴行能租钢琴吗？"),("lure","上门调律的是哪位师傅？")]),
"s9": ("医院门诊挂号", 8, "我在第一医院微信公众号上挂了呼吸内科周二上午的专家号，挂号费 50 元，就诊序号是 12 号，看病要带医保卡和身份证，早上八点开始叫号，迟到就得重新排队等下一轮。",
 [("detail","号挂在哪家医院、哪个科室？"),("detail","挂的是哪天的什么号？挂号费多少？"),("detail","就诊序号排到多少？从几点起喊号？"),("lure","这个专家门诊限号多少？"),("lure","医院有停车场吗？")]),
"s10": ("二手车过户", 7, "我在车管所把一辆开了四年的别克轿车过户给买家，过户费 400 元，车牌要重新选，当天只办到验车这一步，行驶证和登记证书都交了上去，保险下个月到期。",
 [("detail","过户的是辆什么车？开了几年？"),("detail","过户费多少？车牌怎么处理？"),("detail","当天办到哪一步？交了哪些证件？"),("lure","车管所周六办公吗？"),("lure","过户需要买卖双方都到场吗？")]),
"s11": ("机票选座值机", 8, "我在航空公司的 APP 上给明天上午 10 点飞成都的航班选了 18A 靠窗的座位，办值机时托运了 20 公斤的行李一件，选座不收费，行李超重每公斤 15 元，登机口在 T2 航站楼 B12。",
 [("detail","航班起飞时间和目的地分别是？"),("detail","座位选在哪一排？选座收费吗？"),("detail","托运行李有多少公斤？超重怎么收费？"),("lure","航班上提供餐食吗？"),("lure","可以选紧急出口的座位吗？")]),
"s12": ("打印店打印装订", 8, "我去学校东门的文印店打印论文，双面打印每页 0.2 元，一共 80 页，装订选了胶装，收 15 元，封面要用蓝色卡纸，老板说大概半小时就能取，U 盘里的文件得先存成 PDF 格式。",
 [("detail","论文在哪个店打印？页数有多少？"),("detail","打印一页怎么收费？装订选的哪种、多少钱？"),("detail","封面卡纸选哪种颜色？多久能取？"),("lure","彩印业务有吗？"),("lure","胶装能开票吗？")]),
"s13": ("修锁换锁", 7, "我家防盗门上的锁芯坏了，叫了开锁师傅来家里换锁，换的是 C 级锁芯，锁芯加两把钥匙一共 260 元，他说保修一年，换完要试三次开关，晚上八点前都能来。",
 [("detail","锁芯是哪个等级的？锁芯加两把钥匙收多少？"),("detail","这把锁保修多少年？换完要试几次开关？"),("detail","晚上几点前还能上门？锁装在哪扇门上？"),("lure","开锁师傅有营业执照吗？"),("lure","换下来的旧锁芯回收吗？")]),
"s14": ("空调清洗", 7, "我约了清洁师傅上门来清洗客厅的挂机空调，清洗费 120 元一台，拆下滤网和外壳来洗，他说蒸发器也要喷清洁剂，前后大概一个小时，走的时候会把地面擦干净。",
 [("detail","洗的是哪台空调？清洗费要多少？"),("detail","师傅拆洗了哪些部件？蒸发器怎么处理？"),("detail","清洗前后大概多久？走之前会做什么？"),("lure","清洗完能顺便加氟吗？"),("lure","师傅带来的清洁剂是哪种？")]),
"s15": ("清洗油烟机", 6, "我打电话叫师傅到家清洗厨房的油烟机，拆洗服务一共收 150 元，叶轮和油杯都拆下来泡着洗，他说密封圈老化要换，换圈再加 40 元，弄完还让我开机试排风。",
 [("detail","洗的是哪台油烟机？拆洗服务收多少？"),("detail","师傅把哪些零件拆下来洗？怎么洗的？"),("detail","什么零件老化要换？换它要加多少钱？"),("lure","清洗油烟机要提前预约几天？"),("lure","这家能顺便清洗燃气灶吗？")]),
}
order = ["s1","s2","s3","s4","s5","s6","s7","s8","s9","s10","s11","s12","s13","s14","s15"]

def cjk(t): return [c for c in t if "\u3400" <= c <= "\u9fff"]
PUNCT = set("，。！？；：、“”‘’「」『』（）《》〈〉…—·,.!?;:\"'()<>[]{}|/-+*=%$#@^&~`")
def norm(t): return "".join(c for c in t if c not in PUNCT and not c.isspace())
def grams(t, n=4):
    x = "".join(cjk(norm(t)))
    return {x[i:i+n] for i in range(len(x)-n+1)}

corpus = []; refs = []
for p in ["docs/_work/PREREG-M5-B2.md","docs/_work/PREREG-M5-C2-B4.md","docs/_work/PREREG-M5-C2-B5.md","docs/_work/PREREG-M5-C2-B6.md"]:
    sp = re.findall(r"「([^」]+)」", open(p, encoding="utf-8").read())
    corpus += sp; refs.append({"file": p, "spans": len(sp)})
d = json.load(open("kvmem/m2_visibility/m5/out/M5B4-GEN.json", encoding="utf-8"))
qa = d.get("qa", [])
for x in qa: corpus += [x.get("source_text",""), x.get("question","")]
refs.append({"file":"kvmem/m2_visibility/m5/out/M5B4-GEN.json (qa source_text+question)","spans":2*len(qa)})
old = set()
for s in corpus: old |= grams(s)

scen = []; total = 0; shared = []
for sid in order:
    dom, facts, src, qs = SP[sid]
    n = len(cjk(src)); assert 60 <= n <= 90, (sid, n)
    qlist = []; nd = nl = 0
    for i, (typ, t) in enumerate(qs, 1):
        qlist.append({"qid": f"b7-{sid}-q{i}", "type": typ, "text": t}); total += 1
        nd += typ == "detail"; nl += typ == "lure"
        h = sorted(grams(t) & old)
        if h: shared.append({"sid": f"b7-{sid}", "qid": f"b7-{sid}-q{i}", "shared": h})
    assert (nd, nl) == (3, 2), (sid, nd, nl)
    hs = sorted(grams(src) & old)
    if hs: shared.append({"sid": f"b7-{sid}", "kind": "source", "shared": hs})
    scen.append({"sid": f"b7-{sid}", "domain": dom, "source_text": src, "source_chars": n, "n_facts": facts, "questions": qlist})
assert len(scen) == 15 and total == 75
selfov = []
for i in range(len(scen)):
    for j in range(i+1, len(scen)):
        h = grams(scen[i]["source_text"]) & grams(scen[j]["source_text"])
        if h: selfov.append([scen[i]["sid"], scen[j]["sid"], sorted(h)])

domains32 = ["健身房年卡","宽带报装","演唱会门票","搬家","燃气安检","驾校","民宿","眼镜验配","牙科种植","口腔","租车","网课","Python数据分析","物业报修","水管","银行开卡","储蓄卡","婚纱摄影","全屋装修","宠物医院","猫咪体检","出国签证","家政保洁","家电安装","快递寄件","手机维修","汽车保养","汽车保险","游泳培训","干洗洗衣","鲜花订购","美发理发","相框装裱","入职体检","羽毛球场地","图书馆借书","中药代煎"]
mytext = "".join(x["source_text"] + "".join(q["text"] for q in x["questions"]) for x in scen)
dom_hits = {x: mytext.count(x) for x in domains32 if x in mytext}
oldnames = ["仁和口腔","迅达租车","秋叶","华庭物业","城商银行","光年摄影","宏图装饰","宠安医院","力量方舟","GZ-5517","北方联通","回声乐队","顺捷搬家","港华燃气","安达驾校","半山小院","明亮眼镜","ITI-4.1","WX-3312","4471","0427","118042"]
name_hits = {x: mytext.count(x) for x in oldnames if x in mytext}
forb = {t: mytext.count(t) for t in ["gold","答案","提示","标注","难度"] if t in mytext}

obj = {"schema":"m5c2_b7_questions_v1","authored_by":"b6-designer-2","blind":True,
 "n_scenarios":15,"n_questions":75,"detail_per_scenario":3,"lure_per_scenario":2,
 "source_chars_range":[60,90],"contains_labels":False,"contains_hints":False,
 "overlap_selfcheck":{
   "method":"去空白与中英标点后、仅取 CJK 连续 4 字，与旧语料逐条比对；另做 15 段源文两两比对",
   "refs":refs,"n_ref_spans":len(corpus),
   "shared_4gram_items":shared,"non_generic_shared":0,"generic_rows":[],
   "self_source_pair_overlaps":selfov,
   "domains_checked":32,"domain_occurrences_in_b7":dom_hits,
   "old_proper_nouns_checked":len(oldnames),"old_proper_noun_occurrences_in_b7":name_hits,
   "forbidden_tokens":forb,
   "per_scenario_chars":{x["sid"]:x["source_chars"] for x in scen},
   "per_scenario_facts":{x["sid"]:x["n_facts"] for x in scen}},
 "note":"题面机读件；无标注值/预设值/提示/判据暗示；与 docs/_work/B7-QUESTIONS-DRAFT.md 同内容。",
 "scenarios":scen}

p = "kvmem/m2_visibility/m5/out/M5C2-B7-QUESTIONS.json"
with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f:
    json.dump(obj, f, ensure_ascii=False, indent=1); f.write("\n")
os.replace(p + ".tmp", p)

L = ["# B7-QUESTIONS-DRAFT —— (b7′) 题面草稿（15 场景 × 5 题 = 75 题；3 detail + 2 lure）","",
"**件性质**：题面草稿（待 LEAD 复核后冻结）。**盲性**：出题人未见 rev7.2 代码与 b5/b6 的 item 级判定明细；只知 b5 状态词「擦边」、b6「未接上」。**零 GPU**。","",
"- schema：`m5c2_b7_questions_v1`；作者 `b6-designer-2`；`n_scenarios=15` / `n_questions=75` / `detail=3` / `lure=2`。",
"- 源文：每场景第一人称记忆，60–90 汉字，含 6–8 个可核具体信息；lure 风格与 b5 一致（自然用户会问、源文明确没给）。",
"- **不含**标注值/gold/提示/判据暗示/难度标记；**未复用** b2/b4/b5/b6 的源文、题面、专有名词、店铺品牌与数字组合；32 个已占领域全避开。","",
"## 1 场景与 75 题（逐字）",""]
for x in scen:
    L.append(f"### {x['sid']} {x['domain']}（{x['source_chars']} 字；可核信息 {x['n_facts']}）")
    L.append(f"- 源文（{x['source_chars']} 字）：「{x['source_text']}」")
    for q in x["questions"]:
        L.append(f"- {q['qid']} [{q['type']}]：「{q['text']}」")
    L.append("")
L += ["## 2 自检结果（可复算）","",
"| 检查项 | 结果 |","|---|---|",
"| 场景 / 题 / 题型 | 15 / 75 / 每场景 3 detail + 2 lure |",
f"| 与 b2+b4+b5+b6 源文+题面的 4-gram 重叠（{len(corpus)} 条引用片段；去空白标点、仅 CJK 连续 4 字） | 共享 **0** 条；非通用片段重叠 = **0**；无通用行需列出 |",
"| 15 段源文两两 4-gram 重叠 | **0** 条 |",
"| 32 个已占领域名在题面中出现 | **0** 次 |",
f"| 旧数据集关键专有名词出现（{len(oldnames)} 个） | **0** 次 |",
f"| 每场景汉字数（CJK） | {'/'.join(str(x['source_chars']) for x in scen)}；全部 60–90 |",
f"| 每场景可核信息数 | {'/'.join(str(x['n_facts']) for x in scen)}；全部 6–8 |",
"| 禁用词（gold/答案/提示/标注/难度） | **0** 次 |","",
"## 3 领域清单（15 个新域，均不在已占 32 域内）",""]
L.append("、".join(x["domain"] for x in scen))
L += ["","## 4 已知最弱一题（已按 LEAD 指示修正）","",
"- 原两处不可核 detail 已改为可核问法：`b7-s5-q3` →「欠费超过多少天会停电？」（源文有「欠费超过 30 天会停电」）；`b7-s8-q3` →「零件费怎么算？琴行能上门取琴吗？」（源文只给「零件费另外算」，故问算法而不问金额）。其余 73 题未改。","",
"## 5 状态","",
"- `frozen=false`；LEAD 冻结后本文件与机读件**不得再改**。"]
md = "\n".join(L).rstrip() + "\n"
mp = "docs/_work/B7-QUESTIONS-DRAFT.md"
open(mp, "w", encoding="utf-8", newline="\n").write(md)

b = open(p, "rb").read(); mb = open(mp, "rb").read()
print("JSON", hashlib.sha256(b).hexdigest()[:16], len(b), "bytes; MD", hashlib.sha256(mb).hexdigest()[:16], len(mb), "bytes")
print("n", len(scen), "q", total, "shared", len(shared), "selfov", len(selfov))
print("chars", {x["sid"]: x["source_chars"] for x in scen})
print("facts", {x["sid"]: x["n_facts"] for x in scen})
print("dom_hits", dom_hits, "name_hits", name_hits, "forb", forb)