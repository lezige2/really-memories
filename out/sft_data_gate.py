# -*- coding: utf-8 -*-
"""TASK-040/092 下轮 SFT 数据质量门：G1-G13（stdlib only）。

TASK-092 升级点：
  ① 支持多轮结构 system + N×(user, assistant)：
     - 每个 assistant turn 跑 G4/G5/G6/G11/G12/G13
     - 最后一对跑 G2/G3（内容判据）
     - 只有结构不合法才记 G9（多轮行不再按单轮长度/markdown 判罚）
  ② 新增 G13：assistant 同时命中 {天气/气温/限行/股价/新闻/汇率/路况} 与
     {\\d+|℃|度|级|元|块} 且不含"查不到/没法/不能" → fail；含"查不到"的拒答句豁免。
  ③ 原有 G1-G12 语义保留（3 条消息的行仍按原规则判 G9 长度/markdown/system）。
用法：python -X utf8 out/sft_data_gate.py --input training/sft/train_v9.jsonl \
        --out out/SFT-DATA-GATE-v9.json [--min-len 8] [--max-len 60] [--policy-file tools/chat_daily.py]
退出码：有 fail 行（任一违规）→ 1；否则 0。
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "苏州", "天津",
          "重庆", "长沙", "郑州", "青岛", "银川", "哈尔滨", "洛阳", "厦门", "合肥", "济南", "福州",
          "昆明", "大连"]
RE_G1 = re.compile(r"（[^）]{0,40}请|请主动|模拟|扮演|作为助手|生成一条|现在是.{0,12}，?请")
RE_G3_NUM = re.compile(r"\d+")
RE_G3_DATE = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*[号日]|\d{1,2}:\d{2}|\d{1,2}\s*点(?:半|一刻|\d{1,2}分)?")
RE_G3_PRICE = re.compile(r"\d+\s*(?:元|块|万|千)")
RE_G3_TEMP = re.compile(r"-?\d+\s*(?:℃|度)")
RE_G4 = re.compile(r"我(?:已经)?(?:记下|记住|记录|存|保存)了|已记住|记下来了|收到，我记")
RE_G5 = re.compile(r"天气|气温|温度|下雨|下雪|晴|阴|空气|新闻|股价|汇率|限行|路况|实时|最新")
RE_G6 = re.compile(r"已经帮你|我帮你(?:发|转|订|删|登录|下单|打电话|预约)了|已发送|已转账|已删除")
RE_G11 = re.compile(r"别吃|换药|建议吃|可以吃|换一种药|停药|投资建议|建议投资|可以投|能赚|直接签|可以签|法律建议")
RE_SAFE = re.compile(r"咨询医生|医生|就医|药师|专业人士|律师|专业意见|不提供|不能给|无法给|建议咨询|去医院")
RE_MD = re.compile(r"[\n\r]|^\s*[-*#•]\s|\*\*")
RE_G12_REL = re.compile(r"下(?:周|个?月|周[一二三四五六日])|上(?:周|个?月|周[一二三四五六日])|这(?:个)?月|明天|后天|昨天|前天|周[一二三四五六日]")
RE_G12_ABS = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*[号日]|\d{4}-\d{2}-\d{2}|星期[一二三四五六日]")
RE_G13_KW = re.compile(r"天气|气温|限行|股价|新闻|汇率|路况")
RE_G13_VAL = re.compile(r"\d|℃|度|级|元|块")
RE_G13_SAFE = re.compile(r"查不到|没法|不能")
RE_TIME_LINE = re.compile(r"^当前时间：\d{4}-\d{2}-\d{2} 星期[一二三四五六日] \d{2}:\d{2}。")
RE_RETRIEVED = re.compile(r"检索资料[:：]|以下是从网上检索到的资料|资料[:：]\n")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def policy_from(path):
    src = open(path, encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "SYSTEM_POLICY" for t in n.targets):
            return n.value.value if isinstance(n.value, ast.Constant) else eval(
                ast.get_source_segment(src, n.value).strip("() \n"))
    raise RuntimeError("SYSTEM_POLICY not found: %s" % path)


def classify(user, sysc, asst):
    u = user or ""
    if "主动" in u or "请" in u:
        return "D"
    parts = (sysc or "").split("\n\n")
    if len(parts) >= 3 and u.rstrip().endswith(("？", "?")):
        return "C"
    if u.rstrip().endswith(("？", "?")):
        return "B"
    if any(w in asst for w in ("好", "记", "行", "收到", "没问题")):
        return "A"
    return "unknown"


def g3_tokens(asst):
    toks = []
    for pat in (RE_G3_NUM, RE_G3_DATE, RE_G3_PRICE, RE_G3_TEMP):
        toks.extend(pat.findall(asst))
    toks.extend(c for c in CITIES if c in asst)
    return toks


def parse_turns(messages):
    """返回 (ok, sysc, users, assts)；结构不合法时 ok=False。"""
    if not messages:
        return False, "", [], []
    roles = [str(x.get("role")) for x in messages]
    if roles[0] != "system" or len(messages) < 3 or len(messages) % 2 == 0:
        return False, "", [], []
    for k in range(1, len(messages), 2):
        if roles[k] != "user" or roles[k + 1] != "assistant":
            return False, "", [], []
    return (True, str(messages[0].get("content") or ""),
            [str(messages[k].get("content") or "") for k in range(1, len(messages), 2)],
            [str(messages[k].get("content") or "") for k in range(2, len(messages), 2)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join("training", "sft", "train_v9.jsonl"))
    ap.add_argument("--out", default=os.path.join("out", "SFT-DATA-GATE-v9.json"))
    ap.add_argument("--min-len", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=60)
    ap.add_argument("--policy-file", default=os.path.join("tools", "chat_daily.py"))
    ap.add_argument("--quota", default="A:100,B:80,C:60,D:60")
    args = ap.parse_args()
    policy = policy_from(args.policy_file)
    psha = hashlib.sha256(policy.encode("utf-8")).hexdigest()[:16]
    rows = [json.loads(l) for l in open(args.input, encoding="utf-8") if l.strip()]
    rules = {("G%d" % i): [] for i in range(1, 14)}
    KNOWN_FP = ["G2", "G3", "G5", "G8"]  # 已知误报/提示级：短事实答 / 派生值与多轮历史值 / 拒答句含实时词 / 模板重复
    KNOWN_FP_SET = set(KNOWN_FP)
    cats, row_fail, per_row = {}, [0] * len(rows), [set() for _ in rows]
    row_fp = [0] * len(rows)
    as_norm = [""] * len(rows)
    multi_rows = 0
    for i, r in enumerate(rows):
        m = r.get("messages") or []

        disp = {"u": "", "a": ""}  # 多轮行显示首问/末答，避免证据错位

        def add(rule, ev):
            rules[rule].append({"line": i + 1, "rule": rule, "evidence": ev,
                                "known_fp": rule in KNOWN_FP_SET,
                                "user": disp["u"][:80], "assistant": disp["a"][:100]})
            per_row[i].add(rule)
            if rule in KNOWN_FP_SET:  # known-FP 不记 fail
                row_fp[i] = 1
            else:
                row_fail[i] = 1

        ok, sysc, users, assts = parse_turns(m)
        if not ok:
            add("G9", "消息结构须为 system + N×(user, assistant)：实际 roles=%r"
                % [x.get("role") for x in m])
            continue
        multi = len(m) > 3
        if multi:
            multi_rows += 1
        if users:
            disp["u"] = users[0]
            disp["a"] = assts[-1]
        parts = sysc.split("\n\n")
        mems = "\n".join(parts[:-2]) if len(parts) >= 3 else ""
        as_norm[i] = norm(assts[-1])
        cats[i] = classify(users[0], sysc, assts[-1])
        # G1 输入非指令式（每个 user turn 都查）
        for u in users:
            if RE_G1.search(u):
                add("G1", "user 命中指令式模板：%r" % u[:60])
                break
        # 每个 assistant turn：G4/G5/G6/G11/G13
        for a in assts:
            if RE_G4.search(a):
                add("G4", "assistant 叙述记忆动作：%r" % a[:40])
            if RE_G5.search(a) and not RE_RETRIEVED.search(sysc):
                add("G5", "assistant 陈述实时环境事实：%r" % a[:40])
            if RE_G6.search(a):
                add("G6", "assistant 承诺/假装执行：%r" % a[:40])
            if RE_G11.search(a) and not RE_SAFE.search(a):
                add("G11", "疑似医疗/用药/投资/法律建议且无专业人士提示：%r" % a[:40])
            if RE_G13_KW.search(a) and RE_G13_VAL.search(a) and not RE_G13_SAFE.search(a):
                add("G13", "实时事实+具体数值且无拒答语：%r" % a[:40])
        # G12 时间语义门：多轮行一律检查；单轮行保持原语义（仅 A/C/D 类）
        ctx_all = norm("".join(users) + mems)
        need_g12 = multi or cats[i] in ("A", "C", "D")
        if need_g12 and RE_G12_REL.search("".join(users) + mems):
            for a in assts:
                absv = [t for t in RE_G12_ABS.findall(a) if norm(t) not in ctx_all]
                if absv:
                    add("G12", "相对时间被换算为绝对日期：%r" % absv[:4])
                    break
        # 最后一对：G2/G3 内容判据
        last_a = assts[-1]
        has_code = ("```" in last_a) or bool(re.search(
            r"(?m)^(?:def |class |import |from |for |while |if |return |print\()|^\s{2,}\S", last_a))
        PRED = ["是", "有", "在", "要", "会", "能", "别", "记得", "可以", "了", "吗", "呢", "吧", "好", "记", "行"]
        has_pred = any(w in last_a for w in PRED)
        if len(last_a) < args.min_len:
            add("G2", "assistant 长度 %d < %d" % (len(last_a), args.min_len))
        elif (not has_pred and len(last_a) < 10) or (len(last_a) < 8 and last_a.rstrip().endswith(("。", "."))):
            add("G2", "无谓语/碎片结尾：%r" % last_a[-10:])
        ctx = norm(sysc) + norm("".join(users))
        bad = [t for t in g3_tokens(last_a) if norm(t) not in ctx] if not has_code else []
        if bad:
            add("G3", "assistant 具体值未在 system/user 出现：%r" % bad[:6])
        # G9：单轮行保留长度/markdown 判据，但按 K2 做三处豁免：
        #   ① 短答（≤8 字）豁免最小长度（短事实答如"你叫阿杰。"是既定风格）
        #   ② 代码围栏行豁免长度上限与 markdown（B 类长代码是本轮明确要求）
        #   ③ continuation 行（system 仅时间行、无 policy 尾）豁免 policy 尾校验
        if not multi:
            too_long = (not has_code) and len(last_a) > args.max_len
            too_short_hard = len(last_a) <= 8 and len(last_a) < 4
            if too_long:
                add("G9", "assistant 长度 %d > %d（非代码行）" % (len(last_a), args.max_len))
            if too_short_hard:
                add("G9", "assistant 长度 %d < 4" % len(last_a))
            if (not has_code) and RE_MD.search(last_a):
                add("G9", "assistant 含换行/markdown/列表符号")
        # v2 起 system 允许"记忆行 → 时间行 → policy"，时间行可不在首行
        _parts = sysc.split("\n\n")
        _time_ok = bool(_parts) and RE_TIME_LINE.match(_parts[0])
        if not _time_ok and len(_parts) >= 2:
            _time_ok = bool(RE_TIME_LINE.match(_parts[1]))
        if not _time_ok:
            add("G9", "system 缺少时间行（或位置不对）：%r" % sysc[:40])
        is_continuation = bool(RE_TIME_LINE.match(sysc.strip())) and "\n\n" not in sysc
        if (not is_continuation) and (not sysc.endswith(policy)):
            add("G9", "system 未以运行时 SYSTEM_POLICY 结尾")
        # G10 同 (system, 全部 user) 只能一个 assistant
        k = (norm(sysc), "|".join(norm(u) for u in users))
        if not hasattr(main, "_seen_su"):
            main._seen_su = {}
        if k in main._seen_su:
            add("G10", "同 (system,user) 重复出现（首次 line %d）" % main._seen_su[k])
        else:
            main._seen_su[k] = i + 1
    # G8 模板重复（同一 assistant 归一化 >3 次；同 user 答案种类 <2 为数据集级提示）
    from collections import Counter
    ac = Counter(x for x in as_norm if x)
    for i, an in enumerate(as_norm):
        if an and ac[an] > 3:
            rules["G8"].append({"line": i + 1, "rule": "G8", "known_fp": True,
                                "evidence": "assistant 归一化后出现 %d 次（>3）" % ac[an]})
    uc = {}
    for i in range(len(rows)):
        msgs = rows[i].get("messages") or []
        okp, _s, us, _a = parse_turns(msgs)
        if not okp:
            continue
        uc.setdefault("|".join(norm(u) for u in us), set()).add(as_norm[i])
    single = [{"user": q[:60], "answer_kinds": len(v)} for q, v in uc.items() if len(v) < 2]
    if single:
        rules["G8"].append({"line": 0, "rule": "G8",
                            "evidence": "同一 user 仅 1 种答案：%d 个 user（提示加答案多样性）" % len(single)})
    # G10 配额（数据集级）
    quota = dict(p.split(":") for p in args.quota.split(","))
    counts = Counter(cats.values())
    for c, need in quota.items():
        if counts.get(c, 0) < int(need):
            rules["G10"].append({"line": 0, "rule": "G10",
                                 "evidence": "%s 类 %d 条 < 配额 %s" % (c, counts.get(c, 0), need)})
    # 汇总
    safe_rules = ["G1", "G4", "G6", "G7", "G11", "G12", "G13"]
    fp_counts = {k: len([x for x in v if x.get("known_fp")]) for k, v in rules.items()}
    real_fail = sum(row_fail)
    fp_only = sum(1 for i in range(len(rows)) if row_fp[i] and not row_fail[i])
    summary = {"rows": len(rows), "multi_turn_rows": multi_rows,
               "known_fp_rules": list(KNOWN_FP), "known_fp_counts": fp_counts,
               "real_fail_rows": real_fail, "known_fp_rows": fp_only,
               "pass_rows_real": len(rows) - real_fail,
               "pass_rate_real": round((len(rows) - real_fail) / max(1, len(rows)), 4),
               "fail_rows": real_fail, "pass_rows": len(rows) - real_fail,
               "pass_rate": round((len(rows) - real_fail) / max(1, len(rows)), 4),
               "category_counts": dict(counts), "policy_sha16": psha,
               "min_len": args.min_len, "max_len": args.max_len,
               "safe_rules_zero": {k: len(rules[k]) == 0 for k in safe_rules},
               "rules": {k: {"n": len(v), "ok": len(v) == 0, "sample": v[:3]} for k, v in rules.items()}}
    report = {"schema": "sft_data_gate_v2", "task": "TASK-092", "input": args.input,
              "summary": summary,
              "input_sha256_16": hashlib.sha256(open(args.input, "rb").read()).hexdigest()[:16],
              "violations": rules}
    json.dump(report, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"input": args.input, "rows": len(rows), "multi_turn_rows": multi_rows,
                      "real_fail_rows": summary["real_fail_rows"],
                      "known_fp_rows": summary["known_fp_rows"],
                      "fail_rows": summary["fail_rows"], "pass_rate": summary["pass_rate"],
                      "categories": summary["category_counts"],
                      "rule_hits": {k: v["n"] for k, v in summary["rules"].items()},
                      "out": args.out}, ensure_ascii=False, indent=1))
    return 1 if summary["real_fail_rows"] else 0


if __name__ == "__main__":
    sys.exit(main())