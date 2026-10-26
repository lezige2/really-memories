# -*- coding: utf-8 -*-
"""REVIEW 盲标：M5B2 510 句四分类。仅读取 SENTENCES.json（切分与句子文本）。"""
import json, hashlib, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "M5B2-SENTENCES.json")
OUT = os.path.join(BASE, "M5B2-review-labels.json")

doc = json.load(open(SRC, encoding="utf-8"))
S = doc["sentences"]

# ---- 1. support_present：句子主张即源文事实（含同义/合并/重复） ----
SUPPORT = """
S0001 S0003 S0005 S0007 S0009 S0019 S0020 S0037
S0095 S0097 S0098 S0103 S0105 S0106 S0110 S0116 S0118 S0120 S0122
S0143 S0144 S0147 S0148 S0150 S0151
S0179 S0180 S0181 S0184 S0185
S0230 S0231 S0232 S0234 S0236 S0237 S0239 S0241 S0244 S0258
S0267 S0270 S0272 S0285 S0287 S0301 S0303 S0305
S0348 S0350 S0351 S0353 S0355 S0357 S0359 S0361 S0363 S0365 S0367 S0370 S0373 S0374 S0375
S0453 S0455 S0457 S0459 S0470 S0480
""".split()

# ---- 2. fabricated：含源文没有的具体事实（数字/姓名/价格/牌子/地点等） ----
FAB = {
    # s4-q4 诱导题（师傅人数）：编造"两个人"
    **{s: "编造搬家师傅人数" for s in """
    S0186 S0188 S0190 S0192 S0194 S0196 S0198 S0200 S0202 S0204 S0206 S0208
    """.split()},
    # s4-q5 诱导题（能否打包）：编造打包服务
    **{s: "编造可帮忙打包纸箱" for s in """
    S0211 S0213 S0215 S0217 S0219 S0221 S0223 S0225 S0227
    """.split()},
    # s3-q5 诱导题（几点开门检票）
    "S0166": "编造检票提前1-2小时",
    # s5-q4 诱导题（收费多少 / 检查多久）
    "S0242": "编造安检免费",
    "S0249": "编造检查30分钟到1小时",
    # s6-q4 诱导题（考几项 / 补考多少钱）
    "S0319": "编造科目二五项清单",
    "S0320": "编造补考费几百元",
    "S0322": "编造100分90分合格线",
    # s6-q5 诱导题（教练姓什么）：整段教练信息皆源文所无
    "S0329": "编造教练姓张",
    "S0331": "编造教练电话号码",
    "S0333": "编造教练办公时间",
    "S0335": "编造教练在教练场",
    "S0339": "编造考试当天晴天",
}

# ---- 3. undecidable：截断/语义不完整 ----
UNDEC = """
S0036 S0054 S0076 S0094 S0104 S0115 S0125 S0134 S0142 S0165 S0178
S0210 S0229 S0253 S0266 S0300 S0318 S0328 S0347 S0366 S0419 S0452
S0469 S0479 S0490
""".split()

Q_RE = re.compile(r"^(问[:：])|？$|[?？]\s*$")
ABSTAIN = ("没有提到", "没有提供", "我需要更多的信息", "没有足够的信息",
           "无法", "不清楚", "不知道", "没有官方公布")

sids = [x["sid"] for x in S]
assert len(sids) == 510 and len(set(sids)) == 510, "输入 sid 异常"
assert not (set(SUPPORT) & set(FAB)), "support/fab 冲突"
assert not (set(SUPPORT) & set(UNDEC)), "support/undec 冲突"
assert not (set(FAB) & set(UNDEC)), "fab/undec 冲突"
known = set(SUPPORT) | set(FAB) | set(UNDEC)
assert known <= set(sids), ("未知 sid", known - set(sids))

labels = []
for it in S:
    sid, t = it["sid"], it["text"].strip()
    if sid in UNDEC:
        lab, why = "undecidable", "句子截断，主张不完整"
    elif sid in FAB:
        lab, why = "fabricated", FAB[sid]
    elif sid in SUPPORT:
        lab, why = "support_present", "与源文事实一致"
    elif Q_RE.search(t):
        lab, why = "no_fact", "复述提问，无可核事实"
    elif any(k in t for k in ABSTAIN):
        lab, why = "no_fact", "正确弃答，无可核事实"
    else:
        lab, why = "no_fact", "过程叙述/泛化建议，无可核事实"
    assert len(why) <= 20, why
    labels.append({"sid": sid, "label": lab, "reason": why})

counts = {k: sum(1 for x in labels if x["label"] == k)
          for k in ("support_present", "fabricated", "no_fact", "undecidable")}

out = {
    "role": "REVIEW",
    "blinded": True,
    "read_judge_output": False,
    "sentence_n": 510,
    "labels": labels,
    "counts": counts,
}
raw = json.dumps(out, ensure_ascii=False, indent=1).encode("utf-8")
open(OUT, "wb").write(raw)

# ---- 自检 ----
chk = json.loads(raw.decode("utf-8"))
assert len(chk["labels"]) == 510
assert len({x["sid"] for x in chk["labels"]}) == 510
assert [x["sid"] for x in chk["labels"]] == sids          # 顺序与输入一致
assert sum(chk["counts"].values()) == 510
assert set(chk["counts"]) == {"support_present", "fabricated", "no_fact", "undecidable"}
print("sha256", hashlib.sha256(raw).hexdigest())
print("bytes", len(raw))
print("counts", counts)