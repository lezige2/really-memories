# -*- coding: utf-8 -*-
"""M5 探针 (a)「换措辞」实跑 —— 判据见 PREREG-M5-PROBES.md（冻结，逐条照做）。

零 GPU / 零模型调用：20 对文本逐字取自预登记 §4（答案侧取自已冻结的 14B 实答，
改写句由预登记给出），源正文取 memory.db（文本层），判定器为 m5_ground.ground。
判据层不另写一套：只调用 m5_ground 的 extract / ground，不自造匹配规则。

两个率按冻结文件的两条口径**双报**（§5.2 与 §6 的条文冲突见 prereg_conflict）：
  rates_frozen —— §6 冻结报告口径，分母 8/8，20 行全报；
  rates_strict —— §5.2 字面口径，逐族 key 集不等的对作废、不进分母。
规格缺陷不使本轮作废（exit 仍 0）；只有"对照组不复现"或"judge/prereg 的 sha16
跑前后不一致"才作废（exit 1，不出率）。判定器若需要引擎/GPU ⇒ exit 3 并停手。

产物：run_m5_probe_a.json，另存 _before/run_m5_probe_a.json@<sha16>（REGISTER 记账）。
"""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m5_ground as G

PREREG = os.path.join(HERE, "PREREG-M5-PROBES.md")
JUDGE = os.path.join(HERE, "m5_ground.py")
EVIDENCE = os.path.join(HERE, "evidence_m5.json")
DB = os.path.join(HERE, "memory.db")
OUT = os.path.join(HERE, "run_m5_probe_a.json")
BEFORE_DIR = os.path.join(HERE, "_before")
REGISTER = os.path.join(BEFORE_DIR, "REGISTER.json")

ALL = ["home", "project", "habit"]

PLATE = "我的车牌号是苏A12345。"
PROJ14 = "项目将在 3 月 14 日上线。"
PROJ15 = "项目将在 3 月 15 日上线。"
ADDR = "我住在广陵路 12 号 2 单元 602。"
HABIT = "我喝咖啡的习惯是只喝美式，不加糖。"

# 逐字照抄 PREREG §4.1 / §4.2 / §4.3（不许改写、不许增删、不许换样本）
PAIRS = [
    # ---- §4.1 组 A · 应拦（漏判率）8 对 ----
    {"pair_id": "A1", "group": "A", "dim": "参照（不改写）", "orig": PLATE, "rewrite": PLATE,
     "expected": "unsupported", "mounted": ALL,
     "cite": "§4.1 A1 不改写对照基线；§5.1 单向（答案有、正文没有才 unsupported）"},
    {"pair_id": "A2", "group": "A", "dim": "语序倒装", "orig": PLATE, "rewrite": "车牌号苏A12345。",
     "expected": "unsupported", "mounted": ALL, "cite": "§5.1 单向"},
    {"pair_id": "A3", "group": "A", "dim": "问答句式", "orig": PLATE,
     "rewrite": "问：车牌号是多少？答：苏A12345。", "expected": "unsupported", "mounted": ALL,
     "cite": "§5.1 单向"},
    {"pair_id": "A4", "group": "A", "dim": "参照（不改写）", "orig": PROJ15, "rewrite": PROJ15,
     "expected": "unsupported", "mounted": ALL,
     "cite": "§4.1 A4 不改写对照基线；§6 写死「3 月 15 日 ⇒ unsupported」"},
    {"pair_id": "A5", "group": "A", "dim": "语序倒装 + 加修饰", "orig": PROJ15,
     "rewrite": "我记得项目上线的时间是 3 月 15 日那天。", "expected": "unsupported",
     "mounted": ALL, "cite": "§5.1 单向；§6 写死「3 月 15 日 ⇒ unsupported」"},
    {"pair_id": "A6", "group": "A", "dim": "数字替换", "orig": ADDR,
     "rewrite": "我的住址是广陵路 12 号 2 单元 603。", "expected": "unsupported", "mounted": ALL,
     "cite": "§5.1 单向（源文只有 602）；本对探针内容即「答案出现源文没有的硬事实」"},
    {"pair_id": "A7", "group": "A", "dim": "否定前缀压力（§5.5）", "orig": ADDR,
     "rewrite": "不是 602，我住在广陵路 12 号 2 单元 603。", "expected": "unsupported",
     "mounted": ALL, "cite": "§5.5 否定语境豁免（串前 6 字内）在此不成立 ⇒ 仍应 unsupported"},
    {"pair_id": "A8", "group": "A", "dim": "裸 body 车牌（R14 已知缺陷）", "orig": PLATE,
     "rewrite": "车牌号是B3F19K。", "expected": "unsupported", "mounted": ALL,
     "cite": "§4.1 A8；§9.3 R14 安全侧（裸 body 紧邻 CJK 吞前缀，按 unsupported 记）"},
    # ---- §4.2 组 B · 应放行（误判率）8 对 ----
    {"pair_id": "B1", "group": "B", "dim": "参照（不改写）", "orig": ADDR, "rewrite": ADDR,
     "expected": "supported", "mounted": ALL, "cite": "§4.2 B1 不改写对照基线；§5.1 单向"},
    {"pair_id": "B2", "group": "B", "dim": "语序倒装", "orig": ADDR,
     "rewrite": "广陵路 12 号 2 单元 602 是我的住处。", "expected": "supported", "mounted": ALL,
     "cite": "§5.3 超集容忍（多修饰不算错）"},
    {"pair_id": "B3", "group": "B", "dim": "删虚词", "orig": ADDR,
     "rewrite": "我住广陵路 12 号 2 单元 602。", "expected": "supported", "mounted": ALL,
     "cite": "§5.3 超集容忍；§5.1 单向"},
    {"pair_id": "B4", "group": "B", "dim": "日期等价写法（§6 写死）", "orig": PROJ14,
     "rewrite": "项目将在三月十四号上线。", "expected": "supported", "mounted": ALL,
     "cite": "§6 写死「三月十四号 ⇒ supported」"},
    {"pair_id": "B5", "group": "B", "dim": "加修饰（§5.3 超集容忍）", "orig": PROJ14,
     "rewrite": "项目上线时间定在 3 月 14 日，我记得是这样。", "expected": "supported",
     "mounted": ALL, "cite": "§5.3 超集容忍：答案比源文更啰嗦不算错"},
    {"pair_id": "B6", "group": "B", "dim": "参照（不改写）", "orig": HABIT, "rewrite": HABIT,
     "expected": "supported", "mounted": ALL, "cite": "§4.2 B6 不改写对照基线；§5.1 单向"},
    {"pair_id": "B7", "group": "B", "dim": "删虚词 + 语序", "orig": HABIT,
     "rewrite": "我喝咖啡只喝美式，不加糖。", "expected": "supported", "mounted": ALL,
     "cite": "§5.3 超集容忍"},
    {"pair_id": "B8", "group": "B", "dim": "问答句式", "orig": HABIT,
     "rewrite": "问：喝咖啡有什么习惯？答：只喝美式，不加糖。", "expected": "supported",
     "mounted": ALL, "cite": "§5.3 超集容忍"},
    # ---- §4.3 组 C · 判据已写死裁决的边界 4 条（不计入两个率）----
    {"pair_id": "C1", "group": "C", "dim": "源正文缺失（§6）", "orig": ADDR, "rewrite": ADDR,
     "expected": "undecidable", "mounted": ["nosuch_block"],
     "cite": "§6 写死：源正文缺失 ⇒ undecidable，不重写"},
    {"pair_id": "C2", "group": "C", "dim": "数字多重身份（§5.4）", "orig": "我的车停在 3 号楼。",
     "rewrite": "我的车停在 3 号楼。", "expected": "undecidable", "mounted": ALL,
     "cite": "§5.4 数字多重身份 ⇒ 记 undecidable、不标红"},
    {"pair_id": "C3", "group": "C", "dim": "已知漏判·无后缀专名（§5.8）", "orig": "我住在杭州西湖边。",
     "rewrite": "我住在杭州西湖边。", "expected": "supported", "mounted": ALL,
     "cite": "§5.8 已知漏判：有意接受，不许事后当 bug 修"},
    {"pair_id": "C4", "group": "C", "dim": "边界 1 张冠李戴（§0）", "orig": "我住的小区叫蓝鲸。",
     "rewrite": "我住的小区叫蓝鲸。", "expected": "supported", "mounted": ALL,
     "cite": "§0 边界 1 保持不动；§5 不变量 1（事实在别的块里 ⇒ supported）"},
]

# 对照组：必须复现"上游已判裁决"（取自 evidence_m5.json 的冻结读数，不手填）
CONTROLS = {"A1": ("four_cases", "plate", "I1"),
            "A4": ("boundary_cases", "15", None),
            "B1": ("four_cases", "addr", "I1"),
            "B6": ("four_cases", "habit", "I1")}


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def keys_by_family(text):
    """§1 抽取器：A/D/P/N 四族 key 集合（判定器同源，不自造）。"""
    fams = {"A": set(), "D": set(), "P": set(), "N": set()}
    for f in G.extract(text):
        fams[f["family"]].add(str(f["key"]))
    return fams


def symmetry(orig, rewrite):
    a, b = keys_by_family(orig), keys_by_family(rewrite)
    diff = {}
    for fam in ("A", "D", "P", "N"):
        if a[fam] != b[fam]:
            diff[fam] = {"orig_only": sorted(a[fam] - b[fam]),
                         "rewrite_only": sorted(b[fam] - a[fam])}
    return (not diff), diff


def upstream_verdicts(ev):
    """从冻结证据里取对照对的上游已判裁决（找不到 ⇒ 返回 None，由调用方记为不变量失败）。"""
    out = {}
    cases = {c.get("case"): c for c in ev.get("four_cases", [])}
    for pid, (grp, key, form) in CONTROLS.items():
        if grp == "four_cases":
            c = cases.get(key) or {}
            out[pid] = (c.get(form) or {}).get("verdict")
        else:
            for c in ev.get(grp, []):
                if key in str(c.get("case", "")) or key in str(c.get("answer", "")):
                    out[pid] = c.get("verdict")
                    break
    return out


def main():
    t0 = time.time()
    judge_before, prereg_before = sha16(JUDGE), sha16(PREREG)
    ev_sha16, db_sha16 = sha16(EVIDENCE), sha16(DB)
    ev = json.load(open(EVIDENCE, encoding="utf-8"))
    upstream = upstream_verdicts(ev)
    rows, sym_void, inv_fail = [], [], []
    miss_frozen = miss_strict = 0
    fa_frozen = fa_strict = 0
    den_a_strict = den_b_strict = 0
    controls = {}
    for p in PAIRS:
        rep = G.ground(p["rewrite"], list(p["mounted"]), None, DB)
        got = rep["verdict"]
        ok, diff = symmetry(p["orig"], p["rewrite"])
        flipped = (got != p["expected"])
        row = {"pair_id": p["pair_id"], "group": p["group"],
               "orig": p["orig"], "rewrite": p["rewrite"],
               "expected": p["expected"], "got": got, "flipped": flipped,
               "reason": "%s｜%s" % (rep.get("reason", ""), p["cite"]),
               "dim": p["dim"], "mounted": list(p["mounted"]),
               "judge_reason": rep.get("reason"),
               "facts": [{"family": f["family"], "raw": f["raw"], "key": str(f["key"]),
                          "hit": f["hit"]} for f in rep.get("facts", [])],
               "unhit": [{"family": u["family"], "raw": u["raw"]} for u in rep.get("unhit", [])],
               "exempt": [{"family": e["family"], "raw": e["raw"], "why": e["why"]}
                          for e in rep.get("exempt", [])],
               "symmetry_ok": ok}
        rows.append(row)
        if not ok:
            sym_void.append({"pair_id": p["pair_id"], "group": p["group"],
                             "dim": p["dim"], "families": diff,
                             "note": "§5.2 字面：四族 key 集不等 ⇒ 该对作废、不进 rates_strict 的分母"})
            inv_fail.append({"invariant": "1（§5.2 四族 key 逐族相等）",
                             "pair_id": p["pair_id"],
                             "detail": json.dumps(diff, ensure_ascii=False),
                             "round_void": False})
        if p["group"] == "A":
            if got in ("supported", "undecidable"):
                miss_frozen += 1
                if ok:
                    miss_strict += 1
            if ok:
                den_a_strict += 1
        if p["group"] == "B":
            if got == "unsupported":
                fa_frozen += 1
                if ok:
                    fa_strict += 1
            if ok:
                den_b_strict += 1
        if p["pair_id"] in CONTROLS:
            controls[p["pair_id"]] = {"upstream": upstream.get(p["pair_id"]), "now": got,
                                      "reproduced": upstream.get(p["pair_id"]) == got}
    controls_reproduced = all(v["reproduced"] for v in controls.values()) \
        if len(controls) == len(CONTROLS) else False
    for pid, v in sorted(controls.items()):
        if not v["reproduced"]:
            inv_fail.append({"invariant": "2（A1/A4/B1/B6 复现上游裁决）", "pair_id": pid,
                             "detail": "upstream=%r now=%r" % (v["upstream"], v["now"]),
                             "round_void": True})
    if len(controls) != len(CONTROLS):
        inv_fail.append({"invariant": "2（对照组齐全）", "pair_id": None,
                         "detail": "上游证据里缺对照组读数：%s" % sorted(CONTROLS), "round_void": True})
    judge_after, prereg_after = sha16(JUDGE), sha16(PREREG)
    frozen_stable = (judge_before == judge_after and prereg_before == prereg_after)
    if not frozen_stable:
        inv_fail.append({"invariant": "3（judge/prereg 跑前后 sha16 一致）", "pair_id": None,
                         "detail": "%s|%s -> %s|%s" % (judge_before, prereg_before,
                                                       judge_after, prereg_after),
                         "round_void": True})
    round_void = any(x["round_void"] for x in inv_fail)
    c_rows = [r for r in rows if r["group"] == "C"]
    c_ok = [r for r in c_rows if not r["flipped"]]
    c2 = [r for r in rows if r["pair_id"] == "C2"][0]
    c2_mech = {
        "expected": c2["expected"], "got": c2["got"],
        "unhit": c2["unhit"], "facts": c2["facts"],
        "mechanism": ("§5.4 的『数字多重身份』分支只作用于**未命中**的 N 键；而 '3' 在"
                      " source_profile 的 prof['nums'] 里是**命中**的（该函数把所有源文阿拉伯数字"
                      "并入 nums，日期元组里的 3 也进了），所以 ground() 走命中分支、"
                      "多重身份路径根本进不去 ⇒ 实得 supported。"),
        "source_nums": None,
    }
    con = None
    try:
        import sqlite3
        con = sqlite3.connect(DB)
        txts, probs = G.verify_sources(con, ALL)
        c2_mech["source_nums"] = sorted(G.source_profile(txts)["nums"]) if not probs else None
        c2_mech["source_problems"] = probs
    finally:
        if con is not None:
            con.close()
    prereg_conflict = {
        "clauses": ["§5.2", "§6"],
        "static_proof": ("§4.1 中 A6 改写维度=数字替换（602→603）、A7=否定前缀压力、A8=裸 body 编造车牌："
                         "这些对的探针内容就是『答案里出现源文没有的硬事实』⇒ 四族 key 集按构造必然不等；"
                         "故 §5.2『逐族相等』不可能原意覆盖 A 组这些对，与 §6 的固定分母 8 不能同时成立。"),
        "resolution": "双报，不改条文；§9 修订待 inspector 记（方向=改对象）。",
        "note": "规格缺陷不使本轮作废：exit 仍为 0。",
    }
    expected_miss = []
    expected_miss_note = ("§5.8 的已知漏判命中项只有 C3（无后缀专名），它属 C 组、已在 c_group_rows 单列、"
                          "本就不在漏判率分母；A/B 组无 §5.8 类应拦项 ⇒ 本轮 expected_miss 为空。")
    rates_frozen = {"miss_rate": {"num": miss_frozen, "den": 8},
                    "false_alarm_rate": {"num": fa_frozen, "den": 8}}
    rates_strict = {"miss_rate": {"num": miss_strict, "den": den_a_strict},
                    "false_alarm_rate": {"num": fa_strict, "den": den_b_strict},
                    "denominator_note": "§5.2 字面：作废对不进分母（本轮 A 5/B 4）"}
    code = 1 if round_void else 0
    rec = {"schema": "m5_probe_a_v1", "probe": "a",
           "judge_sha16": judge_before, "judge_sha16_after": judge_after,
           "prereg_sha16": prereg_before, "prereg_sha16_after": prereg_after,
           "frozen_sha_stable": frozen_stable,
           "evidence_sha16": ev_sha16, "db_sha16": db_sha16,
           "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "gpu_used": False, "model_calls": 0, "judge_entry": "m5_ground.ground",
           "rows": rows,
           "symmetry_void": sym_void,
           "rates_frozen": None if round_void else rates_frozen,
           "rates_strict": None if round_void else rates_strict,
           "c_group_rows": [{"pair_id": r["pair_id"], "expected": r["expected"], "got": r["got"],
                             "flipped": r["flipped"], "reason": r["reason"]} for r in c_rows],
           "c_group_consistency": "%d/%d" % (len(c_ok), len(c_rows)),
           "c2_mechanism": c2_mech,
           "expected_miss": expected_miss, "expected_miss_note": expected_miss_note,
           "controls": controls, "controls_reproduced": controls_reproduced,
           "prereg_conflict": prereg_conflict,
           "invariant_failures": inv_fail, "round_void": round_void,
           "exit": code}
    json.dump(rec, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    out_sha16 = sha16(OUT)
    os.makedirs(BEFORE_DIR, exist_ok=True)
    copy = os.path.join(BEFORE_DIR, "run_m5_probe_a.json@%s" % out_sha16)
    shutil.copyfile(OUT, copy)
    reg = {"entries": []}
    if os.path.exists(REGISTER):
        reg = json.load(open(REGISTER, encoding="utf-8"))
        reg.setdefault("entries", [])
    reg["entries"].append({
        "source_name": "run_m5_probe_a.json", "source_sha16": out_sha16,
        "copy_path": os.path.abspath(copy).replace("\\", "/"), "in_place": False,
        "copy_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "copyist": "executor",
        "reason": "M5 探针 (a) 产物落档：PREREG 冻结口径，§5.2/§6 双报；"
                  "规格缺陷（§5.2 与 §6 冲突）已记 prereg_conflict，本轮不作废",
        "exit": code})
    json.dump(reg, open(REGISTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s (sha16=%s, %d B) -> %s" % (OUT, out_sha16, os.path.getsize(OUT), copy))
    print(json.dumps({"rates_frozen": rec["rates_frozen"], "rates_strict": rec["rates_strict"],
                      "c_group_consistency": rec["c_group_consistency"],
                      "controls_reproduced": controls_reproduced,
                      "judge_sha16": judge_before, "prereg_sha16": prereg_before,
                      "round_void": round_void, "exit": code}, ensure_ascii=False))
    print("elapsed_s=%.1f" % (time.time() - t0))
    return code


if __name__ == "__main__":
    sys.exit(main())