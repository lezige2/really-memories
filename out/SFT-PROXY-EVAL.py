# -*- coding: utf-8 -*-
"""TASK-033/035 proxy harness：llama-server 跑 base vs base+lora（PP1-PP4 + extra-cases/only-extra）；proxy 无 KV/service 验证逻辑，不可与 78/81、90/92 横比。"""
import argparse, ast, hashlib, importlib.util, json, os, re, sys, time, urllib.request
from datetime import datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WD = "一二三四五六日"
PROXY_GAPS = ["无服务端检索/topk/library、KV mount、verify/repair/refused/state、auto_memory 写入；无快速分支；system 按训练格式",
              "绝对通过率不可与 78/81、90/92 横比；仅 base vs lora 同 prompt/同判据相对证据"]
def sha256_file(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()
def lora_evidence(adapters, lora_path):
    """PP1 v3：以 /lora-adapters 为唯一证据——非空 list、path basename 命中 --lora、scale>0；不读 /props.lora。"""
    if not isinstance(adapters, list) or not adapters: return False
    base = os.path.basename(lora_path) if lora_path else ""
    return any(isinstance(a, dict) and float(a.get("scale") or 0) > 0
               and (not base or base in os.path.basename(str(a.get("path") or ""))) for a in adapters)
def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def load_policy():
    src = open(os.path.join(ROOT, "tools", "chat_daily.py"), encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "SYSTEM_POLICY" for t in n.targets):
            return n.value.value if isinstance(n.value, ast.Constant) else eval(ast.get_source_segment(src, n.value).strip("() \n"))
    raise RuntimeError("SYSTEM_POLICY not found")
def now_line(now):
    d = datetime.strptime(now, "%Y-%m-%d %H:%M")          # PP2 冻结时间，禁止用 now()
    return "当前时间：%s 星期%s %s。" % (d.strftime("%Y-%m-%d"), WD[d.weekday()], d.strftime("%H:%M"))
def make_system(policy, mems, tl):
    return "\n\n".join((["\n".join(mems)] if mems else []) + [tl, policy])   # PP3 裸文本记忆行
def history_pairs(fixed):
    """TASK-084/085：把 3-8 轮固定 history 解析成 [(user,assistant),...]。
    支持 [{"role","content"}] / [{"q","a"}] / [[q,a]]；并对“分组排列”（前段全 user、后段全 assistant）
    做兜底按索引配对（M-b）。丢弃不完整对。"""
    pairs, seq = [], []
    for t in fixed or []:
        if isinstance(t, dict) and "q" in t and "a" in t:
            pairs.append((str(t["q"]), str(t["a"]))); continue
        if isinstance(t, (list, tuple)) and len(t) == 2:
            pairs.append((str(t[0]), str(t[1]))); continue
        if not isinstance(t, dict):
            continue
        role = str(t.get("role") or "")
        content = str(t.get("content") or "")
        if role in ("user", "assistant"):
            seq.append((role, content))
    out, pending = [], None
    for role, content in seq:
        if role == "user":
            pending = content
        elif role == "assistant" and pending is not None:
            out.append((pending, content)); pending = None
    users = [c for r, c in seq if r == "user"]
    assts = [c for r, c in seq if r == "assistant"]
    grouped = (len(seq) == len(users) + len(assts) and len(users) == len(assts) and len(users) > 0
               and [r for r, _ in seq] == ["user"] * len(users) + ["assistant"] * len(assts))
    if grouped and len(out) != len(users):        # 兜底：分组排列按索引配对
        out = [(users[i], assts[i]) for i in range(len(users))]
    return pairs + out
def chatml(system, history, user):
    s = "<|im_start|>system\n" + system + "<|im_end|>\n"
    for q, a in history:
        s += "<|im_start|>user\n" + q + "<|im_end|>\n<|im_start|>assistant\n" + a + "<|im_end|>\n"
    if not str(user or "").strip():                      # v4 D 类：空 user 主动发起（训练格式）
        return s + "<|im_start|>assistant\n"
    return s + "<|im_start|>user\n" + user + "<|im_end|>\n<|im_start|>assistant\n"
def http_json(url, payload, timeout):
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode("utf-8"))
def complete(port, prompt, timeout, n_predict):
    d = http_json("http://127.0.0.1:%d/completion" % port, {"prompt": prompt, "temperature": 0.0,
                  "top_k": 1, "n_predict": n_predict, "stop": ["<|im_end|>"]}, timeout)  # PP4 两臂贪心
    return str(d.get("content") or "").strip()
def read_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
def score81(case, answer, latency, rte):
    """复用 run_training_eval.evaluate；仅剔除服务端专属 state_class/memory_delta，其余判据原样。"""
    expect = dict(case.get("expect") or {})
    dropped = [k for k in ("state_class", "memory_delta") if k in expect]
    for k in dropped: expect.pop(k)
    c = dict(case); c["expect"] = expect
    ok, problems, primary = rte.evaluate(c, {"answer": answer, "state": None, "refused": False,
                                             "block_ids": [], "error": None}, latency, 0, content_check=True)
    exp = case.get("expect") or {}
    na = re.sub(r"\s+", "", str(answer or ""))
    if ok and exp.get("contains_all"):                    # TASK-091 R3：新值完整要素必须全出现
        miss = [t for t in exp["contains_all"] if re.sub(r"\s+", "", str(t)) not in na]
        if miss:
            ok, problems, primary = False, ["contains_all_miss:%r" % miss], "僵硬"
    if ok and exp.get("conflict_if_all"):                 # TASK-091 R3：新旧值同现才 fail
        for pair in exp["conflict_if_all"]:
            if all(re.sub(r"\s+", "", str(t)) in na for t in pair):
                ok, problems, primary = False, ["conflict_old_new:%r" % pair], "串味"
    return ok, (primary if not ok else "ok"), problems, dropped
def main():
    ap = argparse.ArgumentParser(description="proxy harness: base vs base+lora via llama-server /completion")
    ap.add_argument("--arm", choices=["base", "sft"], default="base")
    ap.add_argument("--out", default="")
    ap.add_argument("--port", type=int, default=8767)
    ap.add_argument("--model", default="D:/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf")
    ap.add_argument("--lora", default="")
    ap.add_argument("--expect-lora-sha", default="", help="外层传入 adapter sha16，sft 臂断言")
    ap.add_argument("--now", default="2026-10-28 21:00", help="PP2 冻结时间（两臂共用）")
    ap.add_argument("--n-predict", type=int, default=192)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--contamination", default=os.path.join(ROOT, "out", "SFT-CONTAMINATION-EXCLUDE-v2.json"))
    ap.add_argument("--extra-cases", default=os.path.join(ROOT, "out", "SFT-EXTRA-CASES-v2.jsonl"))
    ap.add_argument("--only-extra", action="store_true", help="只跑 --extra-cases（不跑 81/92；TASK-035 autonomy 子集）")
    args = ap.parse_args()
    out_path = args.out or os.path.join(ROOT, "out", "PROXY-%s.json" % args.arm)
    adapter_sha = sha256_file(args.lora) if args.lora and os.path.isfile(args.lora) else ""
    try:                                                   # PP1 v3：props + lora-adapters 指纹
        props = http_json("http://127.0.0.1:%d/props" % args.port, None, 10.0)
        adapters = http_json("http://127.0.0.1:%d/lora-adapters" % args.port, None, 10.0)
    except Exception as exc:  # noqa: BLE001
        print("ERROR: GET /props|/lora-adapters:%d 失败：%s" % (args.port, exc), file=sys.stderr); raise SystemExit(3)
    lora_seen = lora_evidence(adapters, args.lora)   # 非空 list + path basename 命中 + scale>0
    if args.arm == "sft":
        if not adapter_sha or (args.expect_lora_sha and not adapter_sha.startswith(args.expect_lora_sha)):
            print("ERROR: adapter 缺失或 sha 与 --expect-lora-sha 不符", file=sys.stderr); raise SystemExit(3)
        if not lora_seen:
            print("ERROR: /lora-adapters 未证明该 --lora 已加载（path/scale），无法证明 sft 臂", file=sys.stderr); raise SystemExit(3)
    elif lora_seen:
        print("ERROR: base 臂 /lora-adapters 仍有 adapter（疑似起错 server）", file=sys.stderr); raise SystemExit(3)
    other = os.path.join(ROOT, "out", "PROXY-%s.json" % ("sft" if args.arm == "base" else "base"))
    if os.path.isfile(other):
        od = json.load(open(other, encoding="utf-8"))
        if od.get("model") == args.model and od.get("arm") != args.arm and od.get("adapter_sha256") == adapter_sha \
                and json.dumps(od.get("server_props"), sort_keys=True) == json.dumps(props, sort_keys=True):
            print("ERROR: 两臂 model/props/adapter 一致，无法区分", file=sys.stderr); raise SystemExit(3)
    datetime.strptime(args.now, "%Y-%m-%d %H:%M")              # PP2 非法格式直接 ValueError
    policy = load_policy()
    rte = load_module("rte_proxy", "training/run_training_eval.py")
    rh = load_module("rh_proxy", "training/heldout/run_heldout.py")
    cases81 = read_jsonl(os.path.join(ROOT, "training", "dialog_cases.jsonl"))
    extra = read_jsonl(args.extra_cases)
    cases_sha = {"dialog_cases": sha256_file(os.path.join(ROOT, "training/dialog_cases.jsonl")),
                 "heldout_run_heldout": sha256_file(os.path.join(ROOT, "training/heldout/run_heldout.py")),
                 "extra": sha256_file(args.extra_cases), "only_extra": args.only_extra,
                 "contamination": sha256_file(args.contamination) if os.path.isfile(args.contamination) else ""}
    try:
        cm = json.load(open(args.contamination, encoding="utf-8"))
        hexcl, eexcl = set(cm.get("heldout_exclude_ids") or []), set(cm.get("extra_exclude_ids") or [])
    except Exception:  # noqa: BLE001
        hexcl, eexcl = set(), set()
    def run_case(case, source):
        mems, history = [], []
        fixed = history_pairs(case.get("history"))            # v9 多轮：system + 3-8 轮 history + 最后提问
        if fixed:
            history = list(fixed)
        for act in case.get("pre_state") or []:
            if act.get("action") == "remember" and act.get("text"):
                mems.append(act["text"])
            elif act.get("action") == "ask" and act.get("text") and not fixed:
                a = complete(args.port, chatml(make_system(policy, mems, now_line(args.now)), history,
                                               act["text"]), args.timeout, args.n_predict)
                history.append((act["text"], a))
        if case.get("remember"):
            mems.append(case["remember"])
        t0 = time.time()
        answer = complete(args.port, chatml(make_system(policy, mems, now_line(args.now)), history,
                                            case["input"]), args.timeout, args.n_predict)
        latency = round(time.time() - t0, 3)
        if source == "heldout92":
            ok, why = rh.judge(case, answer); problems, dropped = [], []
        else:
            ok, why, problems, dropped = score81(case, answer, latency, rte)
            ml = int((case.get("expect") or {}).get("max_len") or 0)   # TASK-035 D 类：长度上限
            if ml and len(answer) > ml:
                ok, why, problems = False, "too_long", ["max_len: %d > %d" % (len(answer), ml)]
        excluded = (source == "heldout92" and case["id"] in hexcl) or (source == "extra20" and case["id"] in eexcl)
        return {"source": source, "id": case["id"], "category": case.get("category"), "excluded": excluded,
                "ok": bool(ok), "why": why, "problems": problems, "dropped_assertions": dropped,
                "answer": answer, "latency_s": latency, "n_mem": len(mems), "n_hist": len(history), "empty_user": not str(case.get("input") or "").strip()}
    t0 = time.time()
    cases81, held = ([], []) if args.only_extra else (cases81, rh.CASES)
    results = [run_case(c, "eval81") for c in cases81] + [run_case(c, "heldout92") for c in held] + [run_case(c, "extra20") for c in extra]
    by_src = {}
    for r in results:
        e = by_src.setdefault(r["source"], {"n": 0, "pass": 0, "excluded": 0, "excluded_pass": 0})
        e["n"] += 1; e["pass"] += 1 if r["ok"] else 0
        if r["excluded"]:
            e["excluded"] += 1; e["excluded_pass"] += 1 if r["ok"] else 0
    for e in by_src.values(): e["pass_rate"] = round(e["pass"] / e["n"], 6) if e["n"] else None
    eff = [r for r in results if not r["excluded"]]
    summary = {"total": len(results), "pass": sum(1 for r in results if r["ok"]), "by_source": by_src,
               "pass_rate": round(sum(1 for r in results if r["ok"]) / max(1, len(results)), 6),
               "excluded": {"n": len(results) - len(eff), "pass": sum(1 for r in results if r["excluded"] and r["ok"])}, "effective": {"n": len(eff), "pass": sum(1 for r in eff if r["ok"]), "pass_rate": round(sum(1 for r in eff if r["ok"]) / max(1, len(eff)), 6)}}
    out = {"schema": "sft_proxy_eval_v1", "task": "TASK-033", "arm": args.arm, "model": args.model,
           "harness": "llama-server /completion; ChatML; temperature=0.0; top_k=1; n_predict=%d; stop=<|im_end|>" % args.n_predict,
           "lora": args.lora, "adapter_sha256": adapter_sha, "port": args.port, "now": args.now, "server_props": props, "lora_adapters": adapters,
           "server_identity": {"lora_seen_in_props": bool(lora_seen), "lora_evidence": bool(lora_seen),
           "distinguishable_by": ["lora_adapters"] if lora_seen else (["adapter_sha256+expect_lora_sha"] if args.expect_lora_sha else [])},
           "cases_sha256": cases_sha, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)),
           "elapsed_s": round(time.time() - t0, 2),
           "exclude_policy": {"source": os.path.basename(args.contamination),
                              "heldout_exclude_ids": sorted(hexcl), "extra_exclude_ids": sorted(eexcl)},
           "proxy_gaps": PROXY_GAPS, "summary": summary, "results": results}
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"arm": args.arm, "out": out_path, "now": args.now, "summary": summary, "elapsed_s": out["elapsed_s"]}, ensure_ascii=False, indent=1))
if __name__ == "__main__":
    main()
