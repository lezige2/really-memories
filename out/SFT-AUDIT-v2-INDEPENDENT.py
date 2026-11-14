# -*- coding: utf-8 -*-
"""TASK-003：SFT 数据集 v2 独立审计（不信任 builder 自报，全部从落盘文件重算）。
只读：training/sft/{train,val,data}.jsonl、out/SFT-DATA-v2-meta.json、out/SFT-DATA-AUDIT-v2.json、
      training/dialog_cases.jsonl、training/heldout/run_heldout.py、tools/chat_daily.py。
输出：out/SFT-AUDIT-v2-INDEPENDENT.json
"""
import ast
import calendar
import hashlib
import importlib.util
import json
import os
import random
import re
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WD = "一二三四五六日"
DENY = re.compile(r"我的的|我的住|我的养|我养的的|我的叫|帮我帮我|在吗，在吗|问一下，问一下")


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_jsonl(p):
    rows = []
    with open(p, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            rows.append((ln, json.loads(line)))
    return rows


def load_policy_ast():
    src = open(os.path.join(ROOT, "tools", "chat_daily.py"), encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "SYSTEM_POLICY"
                                             for t in n.targets):
            if isinstance(n.value, ast.Constant):
                return n.value.value
            return eval(ast.get_source_segment(src, n.value).strip("() \n"))
    raise RuntimeError("SYSTEM_POLICY not found")


def load_eval_inputs():
    s = set()
    p = os.path.join(ROOT, "training", "dialog_cases.jsonl")
    for line in open(p, encoding="utf-8"):
        if line.strip():
            s.add(norm(json.loads(line)["input"]))
    hp = os.path.join(ROOT, "training", "heldout", "run_heldout.py")
    spec = importlib.util.spec_from_file_location("rh_cases_audit", hp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for c in getattr(m, "CASES", []):
        s.add(norm(c.get("input", "")))
    return s


def parse_systime(content):
    m = re.search(r"当前时间：(\d{4})-(\d{2})-(\d{2}) 星期([一二三四五六日]) (\d{2}):(\d{2})", content)
    if not m:
        return None
    return (datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))),
            m.group(4), m.group(5) + ":" + m.group(6))


def cdate(d):
    return "%d 月 %d 号" % (d.month, d.day)


def expected_time_answer(q, d, hhmm, wd_in_sys):
    """独立重算：返回该问句答案中必须出现的片段列表（与 builder 生成逻辑无关地实现）。"""
    qs = norm(q)
    if qs.endswith("现在几点？") or qs.endswith("现在几点"):
        return [hhmm]
    if "现在是什么时间" in qs:
        return [d.strftime("%Y-%m-%d"), "星期" + WD[d.weekday()], hhmm]
    if "今天是几月几号" in qs:
        return ["%d 月 %d 号" % (d.month, d.day), "星期" + WD[d.weekday()]]
    if "今天几号" in qs:
        return ["%d 月 %d 号" % (d.month, d.day)]
    if "今天星期几" in qs:
        return ["星期" + WD[d.weekday()]]
    if "明天是星期几" in qs or "明天星期几" in qs:
        t = d + timedelta(days=1)
        return ["星期" + WD[t.weekday()]]
    if "明天几号" in qs:
        t = d + timedelta(days=1)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "后天几号" in qs:
        t = d + timedelta(days=2)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "后天星期几" in qs:
        t = d + timedelta(days=2)
        return ["星期" + WD[t.weekday()]]
    if "昨天几号" in qs:
        t = d - timedelta(days=1)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "昨天星期几" in qs:
        t = d - timedelta(days=1)
        return ["星期" + WD[t.weekday()]]
    if "前天几号" in qs:
        t = d - timedelta(days=2)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "前天星期几" in qs:
        t = d - timedelta(days=2)
        return ["星期" + WD[t.weekday()]]
    if "下周三几号" in qs:
        t = d - timedelta(days=d.weekday()) + timedelta(days=9)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "本周五几号" in qs:
        t = d - timedelta(days=d.weekday()) + timedelta(days=4)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "上周三几号" in qs:
        t = d - timedelta(days=d.weekday() + 5)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "周五几号" in qs:
        t = d + timedelta(days=(4 - d.weekday()) % 7)
        return ["%d 月 %d 号" % (t.month, t.day)]
    if "这个月还剩几天" in qs:
        return ["%d 天" % (calendar.monthrange(d.year, d.month)[1] - d.day)]
    return None


def mem_key_value(mem):
    for pat in (r"我下周三要去(.+?)开会$", r"我下周五要去(.+?)出差$", r"我每周三晚上(.+?)有组会$"):
        m = re.search(pat, mem)
        if m:
            return m.group(1)
    return None


def main():
    out = {"schema": "sft_audit_v2_independent", "task": "TASK-003",
           "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
           "checks": {}, "must_fix": [], "warn": [], "samples": {}}
    C = out["checks"]

    # ---------- 0. 文件存在/哈希 ----------
    f_train = os.path.join(ROOT, "training", "sft", "train.jsonl")
    f_val = os.path.join(ROOT, "training", "sft", "val.jsonl")
    f_data = os.path.join(ROOT, "training", "sft", "data.jsonl")
    f_meta = os.path.join(ROOT, "out", "SFT-DATA-v2-meta.json")
    f_audit = os.path.join(ROOT, "out", "SFT-DATA-AUDIT-v2.json")
    files = {"train": f_train, "val": f_val, "data": f_data}
    hashes = {k: sha256(v) for k, v in files.items()}
    audit_decl = json.load(open(f_audit, encoding="utf-8"))
    C["file_sha256"] = {k: {"actual": hashes[k], "declared": audit_decl["files"][k]["sha256"],
                            "match": hashes[k] == audit_decl["files"][k]["sha256"]}
                        for k in files}
    C["data_equals_train_bytes"] = {"equal": hashes["data"] == hashes["train"],
                                    "detail": [hashes["data"][:16], hashes["train"][:16]]}
    if not C["data_equals_train_bytes"]["equal"]:
        out["must_fix"].append("data.jsonl 与 train.jsonl 字节不等")

    # ---------- 1. 两次重跑产物 ----------
    rerun = {}
    for tag in ("r1", "r2"):
        d = {"train": os.path.join(ROOT, "out", "_audit_%s" % tag, "train.jsonl"),
             "val": os.path.join(ROOT, "out", "_audit_%s" % tag, "val.jsonl"),
             "data": os.path.join(ROOT, "out", "_audit_%s" % tag, "data.jsonl")}
        rerun[tag] = {k: sha256(v) for k, v in d.items()}
        rerun[tag]["audit"] = json.load(open(os.path.join(ROOT, "out", "_audit_%s.json" % tag),
                                             encoding="utf-8"))
    C["rerun_determinism"] = {
        "r1": {k: rerun["r1"][k][:16] for k in ("train", "val", "data")},
        "r2": {k: rerun["r2"][k][:16] for k in ("train", "val", "data")},
        "r1_eq_r2": all(rerun["r1"][k] == rerun["r2"][k] for k in ("train", "val", "data")),
        "official_eq_rerun": all(rerun["r1"][k] == hashes[k] for k in ("train", "val", "data")),
        "official": {k: hashes[k][:16] for k in ("train", "val", "data")},
    }
    if not (C["rerun_determinism"]["r1_eq_r2"] and C["rerun_determinism"]["official_eq_rerun"]):
        out["must_fix"].append("重跑产物与正式产物/两次重跑之间 sha256 不一致")
    a1, a2 = rerun["r1"]["audit"], rerun["r2"]["audit"]
    a1c = {k: v for k, v in a1.items() if k != "generated_at"}
    a2c = {k: v for k, v in a2.items() if k != "generated_at"}
    C["rerun_audit_equal_except_generated_at"] = a1c == a2c

    # ---------- 2. 从落盘文件独立重算 ----------
    tr = [r for _, r in load_jsonl(f_train)]
    va = [r for _, r in load_jsonl(f_val)]
    da = [r for _, r in load_jsonl(f_data)]
    meta = json.load(open(f_meta, encoding="utf-8"))
    catmap = {norm(k): v for k, v in meta["category_of_q"].items()}
    chat_catalog = {norm(k): [norm(x) for x in v] for k, v in meta["chat_catalog"].items()}
    POLICY = load_policy_ast()

    def shape_ok(r):
        m = r.get("messages")
        if not isinstance(m, list) or len(m) != 3:
            return False
        if [x.get("role") for x in m] != ["system", "user", "assistant"]:
            return False
        return (isinstance(m[0].get("content"), str) and m[0]["content"]
                and isinstance(m[1].get("content"), str) and m[1]["content"]
                and isinstance(m[2].get("content"), str) and m[2]["content"])

    all_rows = tr + va
    C["rows"] = {"train": len(tr), "val": len(va), "sum": len(all_rows), "data": len(da),
                 "audit_declared": {"rows": audit_decl["rows"], "train_rows": audit_decl["train_rows"],
                                    "val_rows": audit_decl["val_rows"]},
                 "data_eq_train_rows": len(da) == len(tr)}
    C["schema"] = {"all_3msg_system_user_assistant": all(shape_ok(r) for r in all_rows),
                   "bad_rows": [i for i, r in enumerate(all_rows) if not shape_ok(r)][:10]}
    if not C["schema"]["all_3msg_system_user_assistant"]:
        out["must_fix"].append("存在 role/消息结构不合法的行")

    # 分类（用 meta.category_of_q，不读 builder 计算）
    def cat_of(r):
        return catmap.get(norm(r["messages"][1]["content"]), "UNKNOWN")
    cats = {}
    for r in all_rows:
        cats[cat_of(r)] = cats.get(cat_of(r), 0) + 1
    missing_q = sum(1 for r in all_rows if norm(r["messages"][1]["content"]) not in catmap)
    C["category_counts"] = {"computed": dict(sorted(cats.items())),
                            "declared": audit_decl["category_counts"],
                            "equal": dict(sorted(cats.items())) == dict(sorted(audit_decl["category_counts"].items())),
                            "questions_missing_in_meta": missing_q}
    if missing_q:
        out["must_fix"].append("有行的 user 问句不在 meta.category_of_q 中")

    # pair 去重率
    pairs = [(norm(r["messages"][1]["content"]), norm(r["messages"][2]["content"])) for r in all_rows]
    pair_dup = 1.0 - len(set(pairs)) / max(1, len(pairs))
    # 旧口径：落在完全重复组内的行占比（含 system 全对齐）
    full = [json.dumps(r["messages"], ensure_ascii=False, sort_keys=True) for r in all_rows]
    dup_groups = {}
    for x in full:
        dup_groups[x] = dup_groups.get(x, 0) + 1
    dup_rows_in_groups = sum(v for v in dup_groups.values() if v > 1)
    C["duplicates"] = {"rows": len(all_rows), "unique_pairs": len(set(pairs)),
                       "pair_dup_rate": round(pair_dup, 6),
                       "declared_pair_dup_rate": audit_decl["pair_dup_rate"],
                       "exact_dup_rate_old_metric": round(dup_rows_in_groups / len(all_rows), 6),
                       "exact_dup_rows": dup_rows_in_groups,
                       "max_template_share": round(max(
                           __import__("collections").Counter(norm(r["messages"][1]["content"])
                                                             for r in all_rows).values()) / len(all_rows), 6)}
    if pair_dup >= 0.02:
        out["must_fix"].append("pair_dup_rate >= 2%")

    # val ∩ train
    tq = {norm(r["messages"][1]["content"]) for r in tr}
    vq = {norm(r["messages"][1]["content"]) for r in va}
    tm = {json.dumps(r["messages"], ensure_ascii=False, sort_keys=True) for r in tr}
    vm = {json.dumps(r["messages"], ensure_ascii=False, sort_keys=True) for r in va}
    C["val_leakage"] = {"val_rows": len(va), "val_train_question_overlap": len(tq & vq),
                        "val_train_exact_message_overlap": len(tm & vm),
                        "exact_overlap_rate": round(len(tm & vm) / max(1, len(va)), 6),
                        "question_overlap_rate": round(len(tq & vq) / max(1, len(va)), 6)}
    if len(tq & vq) != 0:
        out["must_fix"].append("val∩train 问句交集 != 0")

    # chat 匹配
    chat_rows = [r for r in all_rows if cat_of(r) == "chat"]
    chat_ok = sum(1 for r in chat_rows
                  if norm(r["messages"][2]["content"]) in chat_catalog.get(
                      norm(r["messages"][1]["content"]), []))
    C["chat"] = {"rows": len(chat_rows), "match": chat_ok,
                 "match_rate": round(chat_ok / max(1, len(chat_rows)), 6),
                 "declared_rate": audit_decl["chat_match_rate"],
                 "mismatch_samples": [
                     {"q": r["messages"][1]["content"], "a": r["messages"][2]["content"]}
                     for r in chat_rows
                     if norm(r["messages"][2]["content"]) not in chat_catalog.get(
                         norm(r["messages"][1]["content"]), [])][:10]}
    if chat_ok != len(chat_rows):
        out["must_fix"].append("chat 匹配率 != 100%")

    # 语法 denylist
    bad = [r["messages"][1]["content"] for r in all_rows if DENY.search(r["messages"][1]["content"])]
    C["grammar_denylist"] = {"violations": len(bad), "declared": audit_decl["grammar_violations"],
                             "samples": bad[:10]}
    if bad:
        out["must_fix"].append("语法 denylist 命中")

    # eval 用例重叠
    ev = load_eval_inputs()
    ev_hits = [r["messages"][1]["content"] for r in all_rows
               if norm(r["messages"][1]["content"]) in ev]
    C["eval_overlap"] = {"eval_inputs": len(ev), "overlap": len(ev_hits),
                         "declared": audit_decl["eval_case_question_overlap"], "samples": ev_hits[:10]}
    if ev_hits:
        out["must_fix"].append("与 eval 用例问句重叠")

    # unique questions
    uq = len(tq | vq)
    C["unique_questions"] = {"count": uq, "declared": audit_decl["unique_questions"]}
    if uq < 300:
        out["must_fix"].append("unique_questions < 300")

    # latest：独立界定 = system 记忆行数 ≥2；要求 answer 含最后一条记忆关键值（最新优先）
    def mem_lines_of(r):
        parts = r["messages"][0]["content"].split("\n\n")
        return [x for x in parts[0].split("\n") if x.strip()] if len(parts) >= 3 else []

    latest_rows = [r for r in all_rows if len(mem_lines_of(r)) >= 2]
    latest_detail = []
    latest_bad = 0
    for r in latest_rows:
        mems = mem_lines_of(r)
        last = mems[-1]
        kv = mem_key_value(last)
        ans = norm(r["messages"][2]["content"])
        ok = bool(kv) and norm(kv) in ans
        # 冲突：答案不应命中更早的记忆值（最新优先）；排除旧值是最后值子串的合法情况（七点 vs 七点半）
        earlier = [mem_key_value(m) for m in mems[:-1]]
        earlier_hit = [x for x in earlier
                       if x and norm(x) in ans and norm(x) not in norm(kv or "")]
        if (not ok) or earlier_hit:
            latest_bad += 1
        latest_detail.append({"q": r["messages"][1]["content"], "mems": len(mems),
                              "last_kv": kv, "contains_last": ok,
                              "earlier_hit": earlier_hit, "a": r["messages"][2]["content"]})
    C["latest"] = {"rows_mems_ge2": len(latest_rows),
                   "rows_with_mems_ge2": sum(1 for x in latest_detail if x["mems"] >= 2),
                   "rows_answer_contains_last": sum(1 for x in latest_detail if x["contains_last"]),
                   "bad": latest_bad,
                   "declared_latest_priority_rows": audit_decl["latest_priority_rows"],
                   "meta_mapped_latest_rows": sum(1 for r in all_rows if cat_of(r) == "latest"),
                   "sample_24": latest_detail[:24]}
    if latest_bad or len(latest_rows) < 20:
        out["must_fix"].append("latest 冲突行不足或答案不是最后一条记忆值")

    # ---------- 3. 策略绑定 ----------
    pol_rows, ends, mid = 0, 0, 0
    cont_rows = 0
    part_hist = {}
    for r in all_rows:
        sysc = r["messages"][0]["content"]
        parts = sysc.split("\n\n")
        part_hist[len(parts)] = part_hist.get(len(parts), 0) + 1
        has_pol = POLICY in sysc
        if has_pol:
            pol_rows += 1
            if sysc.endswith(POLICY):
                ends += 1
            else:
                mid += 1
        if len(parts) == 1:
            cont_rows += 1
    policy_sha = hashlib.sha256(POLICY.encode("utf-8")).hexdigest()
    C["policy"] = {"policy_chars": len(POLICY), "policy_sha256": policy_sha,
                   "meta_policy_sha256": meta.get("policy_sha256"),
                   "sha_match": policy_sha == meta.get("policy_sha256"),
                   "rows_containing_policy": pol_rows, "rows_endswith_policy": ends,
                   "rows_policy_middle": mid, "system_part_hist": part_hist,
                   "declared_policy_equals_runtime": audit_decl["policy_equals_runtime"],
                   "continuation_rows": cont_rows,
                   "continuation_ratio": round(cont_rows / len(all_rows), 6),
                   "declared_continuation_rows": audit_decl["continuation_rows"]}
    if mid or not policy_sha == meta.get("policy_sha256"):
        out["must_fix"].append("政策行 system 未以 SYSTEM_POLICY 结尾 / policy sha 不匹配")
    if not (0.10 <= cont_rows / len(all_rows) <= 0.20):
        out["warn"].append("continuation 行占比不在 10-20% 区间")

    # ---------- 4. 时间一致性（全量重算 + 随机 30 条抽查） ----------
    time_rows = [r for r in all_rows if cat_of(r) == "time"]
    tbad, tchecked, tdetail, tmismatch_samples = 0, 0, 0, []
    for r in time_rows:
        sysc = r["messages"][0]["content"]
        st = parse_systime(sysc)
        if st is None:
            tdetail += 1
            continue
        d, wd_sys, hhmm = st
        exp = expected_time_answer(r["messages"][1]["content"], d, hhmm, wd_sys)
        if exp is None:
            tdetail += 1
            continue
        tchecked += 1
        ans = r["messages"][2]["content"]
        if not all(x in ans for x in exp):
            tbad += 1
            tmismatch_samples.append({"q": r["messages"][1]["content"], "sys": sysc.split("\n")[-1],
                                      "a": ans, "expected_contains": exp})
        # 星期与日期自洽
        if ("星期" in ans) and (wd_sys != WD[d.weekday()]):
            tbad += 1
            tmismatch_samples.append({"q": r["messages"][1]["content"], "err": "system 星期与日期不自洽"})
    rng = random.Random(20261028)
    pick30 = rng.sample(time_rows, min(30, len(time_rows)))
    pick30_detail = []
    for r in pick30:
        sysc = r["messages"][0]["content"]
        st = parse_systime(sysc)
        d, wd_sys, hhmm = st
        exp = expected_time_answer(r["messages"][1]["content"], d, hhmm, wd_sys)
        pick30_detail.append({"q": r["messages"][1]["content"], "sys_time": d.strftime("%Y-%m-%d") + " " + hhmm,
                              "a": r["messages"][2]["content"],
                              "ok": bool(exp) and all(x in r["messages"][2]["content"] for x in exp)})
    C["time_consistency"] = {"time_rows": len(time_rows), "checked": tchecked,
                             "no_time_line": tdetail, "mismatch": tbad,
                             "declared": audit_decl["time_consistency"],
                             "mismatch_samples": tmismatch_samples[:10],
                             "random30_all_ok": all(x["ok"] for x in pick30_detail),
                             "random30": pick30_detail}
    if tbad or len(pick30_detail) < 30 or not all(x["ok"] for x in pick30_detail):
        out["must_fix"].append("时间类答案与 system 时间不一致")

    # ---------- 4b. 独立签名分类（不依赖 builder 的 family/category）+ 元数据歧义 ----------
    UNKNOWN_A = {"这个我没法确认：你没跟我说过。", "这条我没法确认，你没提过。",
                 "这个我不知道，你没告诉过我。"}
    PRIVACY_A = {"这个我没法做，也不该做。", "抱歉，这类请求我帮不了。",
                 "我不能泄露内部信息或帮你做违规的事。", "这个我帮不了哦，涉及隐私/安全。",
                 "这条我不能帮，超出我的边界。", "这个做不了，也不合适做。"}
    TIME_Q_RE = re.compile(r"(几点|几号|星期几|还剩几天|什么时间)")

    def mem_lines_of(r):
        parts = r["messages"][0]["content"].split("\n\n")
        return [x for x in parts[0].split("\n") if x.strip()] if len(parts) >= 3 else []

    def sig_classify(r):
        q = r["messages"][1]["content"]
        a = r["messages"][2]["content"]
        an, qn = norm(a), norm(q)
        mems = mem_lines_of(r)
        if len(mems) >= 2:
            return "latest"
        if an in UNKNOWN_A:
            return "unknown"
        if an in PRIVACY_A:
            return "privacy"
        if an in chat_catalog.get(qn, []):
            return "chat"
        if an.startswith("这个我帮不了哦") or an.startswith("抱歉，"):
            return "boundary"
        if len(mems) == 1:
            return "memory"
        if TIME_Q_RE.search(qn):
            return "time"
        return "identity_or_other"

    sig_all = {}
    for r in all_rows:
        k = sig_classify(r)
        sig_all[k] = sig_all.get(k, 0) + 1
    sig_val = {}
    for r in va:
        k = sig_classify(r)
        sig_val[k] = sig_val.get(k, 0) + 1
    qsig = {}
    for r in all_rows:
        qsig.setdefault(norm(r["messages"][1]["content"]), set()).add(sig_classify(r))
    ambiguous = {q: sorted(v) for q, v in qsig.items()
                 if len(v & {"memory", "unknown", "latest"}) > 1}
    amb_rows = sum(1 for r in all_rows
                   if len(qsig[norm(r["messages"][1]["content"])] & {"memory", "unknown", "latest"}) > 1)
    dcl = audit_decl["category_counts"]
    sig_match = (sig_all.get("identity_or_other", 0) == dcl["identity"]
                 and all(sig_all.get(k, 0) == dcl[k]
                         for k in ("boundary", "unknown", "privacy", "chat", "time", "memory", "latest")))
    C["category_counts_signature"] = {
        "computed": dict(sorted(sig_all.items())), "declared": dcl,
        "matches_declared": sig_match,
        "method": "latest=system记忆行≥2；memory=记忆行=1；unknown/privacy/chat/boundary 用答案文本签名；time 用问句模式；identity=剩余",
        "val_by_signature": dict(sorted(sig_val.items())),
        "val_category_coverage": sorted(sig_val.keys())}
    C["meta_category_ambiguity"] = {"ambiguous_questions": len(ambiguous), "rows_affected": amb_rows,
                                    "detail": {q: v for q, v in list(ambiguous.items())[:20]},
                                    "meta_category_of_q_n": len(meta["category_of_q"])}
    if not sig_match:
        out["must_fix"].append("独立签名分类计数与自报 category_counts 不一致")
    if ambiguous:
        out["warn"].append("meta.category_of_q 非单射：%d 个问句跨 memory/unknown/latest、%d 行无法用 meta 唯一还原分类（签名法计数与自报一致，数据本身无矛盾）"
                           % (len(ambiguous), amb_rows))

    # ---------- 4c. 附加独立一致性 ----------
    anchors = set(meta["anchors"])
    sys_times = {}
    bad_anchor = []
    cont_not_pure = 0
    part_hist2 = {}
    for r in all_rows:
        sysc = r["messages"][0]["content"]
        st = parse_systime(sysc)
        parts = sysc.split("\n\n")
        part_hist2[len(parts)] = part_hist2.get(len(parts), 0) + 1
        key = (st[0].strftime("%Y-%m-%d") + " " + st[2]) if st else "NO_TIME"
        sys_times[key] = sys_times.get(key, 0) + 1
        if key not in anchors and key != "NO_TIME":
            bad_anchor.append((key, norm(r["messages"][1]["content"])[:30]))
        if len(parts) == 1 and st is not None:
            pure = "当前时间：%s 星期%s %s。" % (st[0].strftime("%Y-%m-%d"), st[1], st[2])
            if sysc != pure:
                cont_not_pure += 1
    qs_all = [r["messages"][1]["content"] for r in all_rows]
    ans_all = [r["messages"][2]["content"] for r in all_rows]
    lint = {"double_qmark": sum(1 for q in qs_all if "？？" in q),
            "space_before_qmark": sum(1 for q in qs_all if re.search(r"\s[？?]", q)),
            "empty_q": sum(1 for q in qs_all if not norm(q)),
            "empty_a": sum(1 for a in ans_all if not norm(a))}
    chars2 = sorted(len(json.dumps(r["messages"], ensure_ascii=False)) for r in all_rows)
    C["extra"] = {"system_time_values": sys_times,
                  "n_system_time_outside_anchors": len(bad_anchor),
                  "system_time_outside_samples": bad_anchor[:10],
                  "system_part_hist": part_hist2,
                  "continuation_rows_not_pure_time_line": cont_not_pure,
                  "lint": lint,
                  "unique_answers": len({norm(a) for a in ans_all}),
                  "p99_chars_recomputed": chars2[int(len(chars2) * 0.99) - 1],
                  "declared_p99_chars": audit_decl["p99_chars"],
                  "self_sha256": sha256(os.path.join(ROOT, "training", "sft", "build_dataset.py")),
                  "declared_self_sha256": audit_decl["self_sha256"]}
    if bad_anchor:
        out["warn"].append("存在 system 时间不在 anchors 集合内的行")
    thin = {k: v for k, v in sig_val.items() if v < 5}
    if thin:
        out["warn"].append("val 各类别覆盖不均，<5 行的类别：%r（比例代表性弱）" % thin)
    if lint["double_qmark"] or lint["empty_q"] or lint["empty_a"]:
        out["must_fix"].append("问句/答案基础 lint 未过：%r" % lint)

    # ---------- 5. 其它 builder 声明复核 ----------
    declared_gates = audit_decl["gates"]
    rec = {
        "rows_2600_3200": 2600 <= len(all_rows) <= 3200,
        "pair_dup_lt_2pct": pair_dup < 0.02,
        "val_train_overlap_zero": len(tq & vq) == 0,
        "chat_match_100": chat_ok == len(chat_rows),
        "grammar_zero": len(bad) == 0,
        "latest_ge_20": len(latest_rows) >= 20,
        "memory_facts_ge_120": None,
        "policy_equals_runtime": mid == 0 and pol_rows > 0,
        "eval_overlap_zero": len(ev_hits) == 0,
        "unique_questions_ge_300": uq >= 300,
        "max_question_share_le_2pct": (max(__import__("collections").Counter(
            norm(r["messages"][1]["content"]) for r in all_rows).values()) / len(all_rows)) <= 0.02,
        "time_consistency": tchecked > 150 and tbad == 0,
        "data_equals_train_bytes": hashes["data"] == hashes["train"],
        "val_140_160": 140 <= len(va) <= 160,
    }
    mem_facts = set()
    for r in all_rows:
        parts = r["messages"][0]["content"].split("\n\n")
        if len(parts) >= 3:
            for m in parts[0].split("\n"):
                if m.strip():
                    mem_facts.add(norm(m))
    rec["memory_facts_ge_120"] = len(mem_facts) >= 120
    C["gate_recompute"] = {"recomputed": rec, "declared_all_ok": all(v["ok"] for v in declared_gates.values()),
                           "declared": {k: v["ok"] for k, v in declared_gates.items()},
                           "memory_facts": len(mem_facts), "declared_facts": audit_decl["distinct_memory_facts"]}
    for k, v in rec.items():
        if v is False:
            out["must_fix"].append("gate 复核失败: %s" % k)

    # ---------- 6. 与旧审计口径对比 ----------
    old = json.load(open(os.path.join(ROOT, "out", "SFT-DATA-AUDIT.json"), encoding="utf-8"))
    old_ev = {i["id"]: i["evidence"] for i in old["issues"]}
    C["old_vs_new"] = {
        "old_dataset": {"rows": old["target"]["rows"], "val_rows": old["target"]["val"]["rows"],
                        "sha256_16": old["target"]["sha256"][:16]},
        "duplicate_rate": {"old_exact_dup_rows_in_groups_pct": round(old_ev["I3"]["exact_duplicate_rate"] * 100, 2),
                           "old_unique_questions": old_ev["I3"]["unique_user_questions"],
                           "old_unique_answers": old_ev["I3"]["unique_answers"],
                           "new_exact_dup_pct": round(dup_rows_in_groups / len(all_rows) * 100, 4),
                           "new_pair_dup_pct": round(pair_dup * 100, 4),
                           "new_unique_questions": uq},
        "val_leakage": {"old_exact_overlap_pct": round(old_ev["I1"]["exact_overlap_rate"] * 100, 2),
                        "old_question_overlap_pct": round(old_ev["I1"]["question_overlap_rate"] * 100, 2),
                        "new_exact_overlap_pct": round(len(tm & vm) / max(1, len(va)) * 100, 4),
                        "new_question_overlap_pct": round(len(tq & vq) / max(1, len(va)) * 100, 4)},
        "chat_mismatch": {"old_chat_rows": old_ev["I2"]["chat_rows"],
                          "old_mismatch_pct": round(old_ev["I2"]["mismatch_rate"] * 100, 2),
                          "new_chat_rows": len(chat_rows),
                          "new_mismatch_pct": round((len(chat_rows) - chat_ok) / max(1, len(chat_rows)) * 100, 4)},
    }

    # 输出
    with open(os.path.join(ROOT, "out", "SFT-AUDIT-v2-INDEPENDENT.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    concise = {k: C[k] for k in ("rerun_determinism", "rows", "category_counts",
                                 "category_counts_signature", "meta_category_ambiguity",
                                 "duplicates", "val_leakage", "chat", "grammar_denylist",
                                 "eval_overlap", "unique_questions", "policy", "time_consistency",
                                 "extra", "gate_recompute", "old_vs_new")}
    concise["latest_summary"] = {k: v for k, v in C["latest"].items() if k != "sample_24"}
    print(json.dumps({"must_fix": out["must_fix"], "warn": out["warn"],
                      "checks": concise}, ensure_ascii=False, indent=1))
    return 0 if not out["must_fix"] else 1


if __name__ == "__main__":
    raise SystemExit(main())