# -*- coding: utf-8 -*-
"""TASK-040 下轮 SFT 数据质量门：B 的 G1-G11 机械门 + veto#7（stdlib only）。
用法：python -X utf8 out/sft_data_gate.py --input training/sft/v3_autonomy.jsonl \
        --out out/SFT-DATA-GATE-REPORT.json [--min-len 8] [--max-len 60] [--policy-file tools/chat_daily.py]
退出码：有 fail 行（任一违规）→ 1；否则 0。
"""
import argparse, ast, hashlib, json, os, re, sys

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "苏州", "天津", "重庆", "长沙", "郑州", "青岛", "银川", "哈尔滨", "洛阳", "厦门", "合肥", "济南", "福州", "昆明", "大连"]
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
def norm(s):
    return re.sub(r"\s+", "", str(s or ""))
def policy_from(path):
    src = open(path, encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "SYSTEM_POLICY" for t in n.targets):
            return n.value.value if isinstance(n.value, ast.Constant) else eval(ast.get_source_segment(src, n.value).strip("() \n"))
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
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join("training", "sft", "v3_autonomy.jsonl"))
    ap.add_argument("--out", default=os.path.join("out", "SFT-DATA-GATE-REPORT.json"))
    ap.add_argument("--min-len", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=60)
    ap.add_argument("--policy-file", default=os.path.join("tools", "chat_daily.py"))
    ap.add_argument("--quota", default="A:100,B:80,C:60,D:60")
    args = ap.parse_args()
    policy = policy_from(args.policy_file)
    psha = hashlib.sha256(policy.encode("utf-8")).hexdigest()[:16]
    rows = [json.loads(l) for l in open(args.input, encoding="utf-8") if l.strip()]
    rules = {("G%d" % i): [] for i in range(1, 13)}
    cats, row_fail, per_row = {}, [0] * len(rows), [set() for _ in rows]
    as_norm = [""] * len(rows)
    seen_su = {}
    for i, r in enumerate(rows):
        m = r.get("messages") or []
        def add(rule, ev):
            rules[rule].append({"line": i + 1, "rule": rule, "evidence": ev,
                                "user": str(m[1]["content"])[:80] if len(m) > 1 else "",
                                "assistant": str(m[2]["content"])[:100] if len(m) > 2 else ""})
            row_fail[i] = 1
            per_row[i].add(rule)
        if len(m) != 3 or [x.get("role") for x in m] != ["system", "user", "assistant"]:
            add("G9", "消息结构须为 system/user/assistant 三条，实际 %r" % [x.get("role") for x in m])
            continue
        sysc, user, asst = (str(x.get("content") or "") for x in m)
        parts = sysc.split("\n\n")
        mems = "\n".join(parts[:-2]) if len(parts) >= 3 else ""
        as_norm[i] = norm(asst)
        cats[i] = classify(user, sysc, asst)
        # G1 输入非指令式
        if RE_G1.search(user):
            add("G1", "user 命中指令式模板：%r" % user[:60])
        # G2 答案非碎片（R2 放宽：允许谓语/系词标记；仅无谓语且<10 字 / 单名词句号且<8 字判 fail）
        PRED = ["是", "有", "在", "要", "会", "能", "别", "记得", "可以", "了", "吗", "呢", "吧", "好", "记", "行"]
        has_pred = any(w in asst for w in PRED)
        if len(asst) < args.min_len:
            add("G2", "assistant 长度 %d < %d" % (len(asst), args.min_len))
        elif (not has_pred and len(asst) < 10) or (len(asst) < 8 and asst.rstrip().endswith(("。", "."))):
            add("G2", "无谓语/碎片结尾：%r" % asst[-10:])
        # G3 无锚点具体值
        ctx = norm(sysc) + norm(user)
        bad = [t for t in g3_tokens(asst) if norm(t) not in ctx]
        if bad:
            add("G3", "assistant 具体值未在 system/user 出现：%r" % bad[:6])
        # G4 不叙述记忆动作
        if RE_G4.search(asst):
            add("G4", "assistant 叙述记忆动作：%r" % asst[:40])
        # G5 不陈述实时环境事实（system 无“检索资料”实际材料时；注意 policy 文本本身含该词，不能用裸词判断）
        if RE_G5.search(asst) and not re.search(r"检索资料[:：]|以下是从网上检索到的资料|资料[:：]\n", sysc):
            add("G5", "assistant 陈述实时环境事实：%r" % asst[:40])
        # G6 不承诺/假装执行
        if RE_G6.search(asst):
            add("G6", "assistant 承诺/假装执行：%r" % asst[:40])
        # G7 D 类须有记忆锚点（2-gram 命中 mems）
        if ("主动" in user) and mems:
            mn = norm(mems)
            grams = {mn[j:j + 2] for j in range(len(mn) - 1)}
            an = norm(asst)
            if not any(g in an for g in grams):
                add("G7", "D 类主动消息未含 mems 的 2-gram")
        # G9 长度/格式/时间行/policy
        if not (args.min_len <= len(asst) <= args.max_len):
            add("G9", "assistant 长度 %d 不在 [%d,%d]" % (len(asst), args.min_len, args.max_len))
        if RE_MD.search(asst):
            add("G9", "assistant 含换行/markdown/列表符号")
        if not re.match(r"^当前时间：\d{4}-\d{2}-\d{2} 星期[一二三四五六日] \d{2}:\d{2}。", sysc):
            add("G9", "system 首行不是时间行：%r" % sysc[:40])
        if not sysc.endswith(policy):
            add("G9", "system 未以运行时 SYSTEM_POLICY 结尾")
        # G10 同 (system,user) 只能一个 assistant
        k = (norm(sysc), norm(user))
        if k in seen_su:
            add("G10", "同 (system,user) 重复出现（首次 line %d）" % seen_su[k])
        else:
            seen_su[k] = i + 1
        # G11 医疗/投资/法律建议（veto#7）
        if RE_G11.search(asst) and not RE_SAFE.search(asst):
            add("G11", "疑似医疗/用药/投资/法律建议且无专业人士提示：%r" % asst[:40])
        # G12 时间语义门（R3）：A/C/D 含相对时间时不得换算成绝对日期
        if cats[i] in ("A", "C", "D") and RE_G12_REL.search(user + mems):
            c2 = norm(user) + norm(mems)
            absv = [t for t in RE_G12_ABS.findall(asst) if norm(t) not in c2]
            if absv:
                add("G12", "相对时间被换算为绝对日期：%r" % absv[:4])
    # G8 模板重复（同一 assistant 归一化 >3 次；同 user 答案种类 <2 为数据集级提示）
    from collections import Counter
    ac = Counter(x for x in as_norm if x)
    for i, an in enumerate(as_norm):
        if an and ac[an] > 3:
            rules["G8"].append({"line": i + 1, "rule": "G8", "evidence": "assistant 归一化后出现 %d 次（>3）" % ac[an]})
            if not row_fail[i]:
                row_fail[i] = 1
    uc = {}
    for i in range(len(rows)):
        if len(rows[i].get("messages") or []) != 3:
            continue
        q = norm(rows[i]["messages"][1]["content"])
        uc.setdefault(q, set()).add(as_norm[i])
    single = [{"user": q[:60], "answer_kinds": len(v)} for q, v in uc.items() if len(v) < 2]
    if single:
        rules["G8"].append({"line": 0, "rule": "G8", "evidence": "同一 user 仅 1 种答案：%d 个 user（提示加答案多样性）" % len(single)})
    # G10 配额（数据集级）
    quota = dict(p.split(":") for p in args.quota.split(","))
    counts = Counter(cats.values())
    for c, need in quota.items():
        if counts.get(c, 0) < int(need):
            rules["G10"].append({"line": 0, "rule": "G10", "evidence": "%s 类 %d 条 < 配额 %s" % (c, counts.get(c, 0), need)})
    # 汇总
    summary = {"rows": len(rows), "fail_rows": sum(row_fail), "pass_rows": len(rows) - sum(row_fail),
               "pass_rate": round((len(rows) - sum(row_fail)) / max(1, len(rows)), 4),
               "category_counts": dict(counts), "policy_sha16": psha,
               "min_len": args.min_len, "max_len": args.max_len,
               "rules": {k: {"n": len(v), "ok": len(v) == 0, "sample": v[:3]} for k, v in rules.items()}}
    report = {"schema": "sft_data_gate_v1", "task": "TASK-040", "input": args.input, "summary": summary,
              "input_sha256_16": hashlib.sha256(open(args.input, "rb").read()).hexdigest()[:16], "violations": rules}
    json.dump(report, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"input": args.input, "rows": len(rows), "fail_rows": summary["fail_rows"],
                      "pass_rate": summary["pass_rate"], "categories": summary["category_counts"],
                      "rule_hits": {k: v["n"] for k, v in summary["rules"].items()},
                      "out": args.out}, ensure_ascii=False, indent=1))
    return 1 if summary["fail_rows"] else 0
if __name__ == "__main__":
    sys.exit(main())