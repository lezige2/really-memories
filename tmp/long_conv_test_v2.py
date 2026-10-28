# -*- coding: utf-8 -*-
"""long_conv_test_v2.py -- 长上下文压测（可复跑；只读调用服务，不改服务/既有文件）。

目标：在约 40k 字符的连续对话里触发 rollover，考察 8 个事实（早期/中期/近期三档）
的跨 rollover 召回，并覆盖重复提问、跨 rollover 追问“刚才说的”、长时间不 reset
连续提问等边界场景。

相对 v1 的增强：
  1) 健壮性：单请求超时 + 对 5xx/断连自动重试（可配次数/退避），每次尝试留痕；
     逐 turn 记录 `chat_tokens`（/status）与 rollover 事件（turn/字符/token 前后值）。
  2) 埋点：8 个新事实按 ~3–5k 字符间隔插入（阈值 [3000,6500,11000,16000,
     21000,26000,32000,37000]），分 early/mid/recent 三档，逐条记录插入 turn。
  3) 异常场景：连续提问不 reset（10 连问 + token 增长）、同一事实重复问 3 次
     （一致性）、跨 rollover 后追问“刚才说的”。
  4) 可复跑：固定事实/种子/阈值；输出完整 JSON（含脚本 sha256、参数、每 turn
     遥测、rollover、探针、错误、汇总）；支持 --dry-run（零请求）与 --smoke。

用法：
  python -X utf8 tmp/long_conv_test_v2.py --dry-run
  python -X utf8 tmp/long_conv_test_v2.py --smoke
  python -X utf8 tmp/long_conv_test_v2.py --target-chars 40000 --out tmp/LONG-CONV-TEST-V2.json

注意：默认开始时 POST /reset（--no-reset 可关闭）；服务只由 LEAD 重启，本脚本不重启。
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

SCRIPT = os.path.abspath(__file__)
ROOT = os.path.dirname(os.path.dirname(SCRIPT))
DEFAULT_EP = "http://127.0.0.1:8765"
RETRYABLE_HTTP = {500, 502, 503, 504, 429}

FACTS = [
    {"id": 1, "tier": "early", "threshold": 3000,
     "text": "顺便说一下，我的车牌号是京A88888。",
     "question": "我的车牌号是多少？", "keywords": ["京A88888"]},
    {"id": 2, "tier": "early", "threshold": 6500,
     "text": "补充一个事实：我养的猫叫豆豆。",
     "question": "我养的猫叫什么名字？", "keywords": ["豆豆"]},
    {"id": 3, "tier": "mid", "threshold": 11000,
     "text": "再记一条：我下周五要去成都开会。",
     "question": "我下周五要去哪开会？", "keywords": ["成都"]},
    {"id": 4, "tier": "mid", "threshold": 16000,
     "text": "顺便说一下，我的工号是 A12345。",
     "question": "我的工号是多少？", "keywords": ["A12345"]},
    {"id": 5, "tier": "mid", "threshold": 21000,
     "text": "记一下：我妻子叫李娜。",
     "question": "我妻子叫什么名字？", "keywords": ["李娜"]},
    {"id": 6, "tier": "mid", "threshold": 26000,
     "text": "补充：我老家在青岛。",
     "question": "我老家在哪里？", "keywords": ["青岛"]},
    {"id": 7, "tier": "recent", "threshold": 32000,
     "text": "再说一个：我的手机号是 13800138000。",
     "question": "我的手机号是多少？", "keywords": ["13800138000"]},
    {"id": 8, "tier": "recent", "threshold": 37000,
     "text": "最后记一条：我下个月要去西安出差。",
     "question": "我下个月要去哪出差？", "keywords": ["西安"]},
]

FILLER = [
    "今天的工作安排有点满，上午处理邮件，下午继续整理资料。",
    "最近在整理一些旧项目的文档，顺手把目录结构理了一遍。",
    "周末打算去附近走走，可能去公园，也可能就在家休息。",
    "刚才看了一下进度，感觉节奏还可以，继续按计划推进。",
    "有些事情推进得比预期慢一点，不过总体还在可控范围。",
    "我在想下一步先把哪块理顺，避免来回返工。",
    "今天天气一般，不太想出门，就继续把手上事情做完。",
    "整理资料的时候发现几个之前记下的点，回头再逐条确认。",
]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path):
    b = open(path, "rb").read()
    return hashlib.sha256(b).hexdigest(), len(b)


class Client:
    def __init__(self, endpoint, timeout, retries, backoff, log=None):
        self.ep = endpoint.rstrip("/")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.backoff = float(backoff)
        self.log = log or (lambda *a, **k: None)
        self.requests = 0
        self.retries_used = 0

    def request(self, path, payload=None, timeout=None):
        """返回 (data|None, attempts, error|None)。5xx/断连/超时按 retries 重试。"""
        url = self.ep + path
        body = None
        method = "GET"
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            method = "POST"
            headers["Content-Type"] = "application/json; charset=utf-8"
        attempts = 0
        last_err = None
        for attempt in range(1, self.retries + 2):
            attempts = attempt
            self.requests += 1
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                    raw = r.read()
                    if r.status >= 500:
                        raise urllib.error.HTTPError(url, r.status, "server error",
                                                     r.headers, None)
                    data = json.loads(raw.decode("utf-8")) if raw else {}
                    return data, attempts, None
            except urllib.error.HTTPError as exc:
                last_err = "HTTP %s" % exc.code
                if exc.code in RETRYABLE_HTTP and attempt <= self.retries:
                    self.retries_used += 1
                    time.sleep(self.backoff * (2 ** (attempt - 1)))
                    continue
                try:
                    detail = exc.read().decode("utf-8", "replace")[:200]
                except Exception:                      # noqa: BLE001
                    detail = ""
                return None, attempts, "%s %s" % (last_err, detail)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_err = type(exc).__name__ + ": " + str(exc)[:160]
                if attempt <= self.retries:
                    self.retries_used += 1
                    time.sleep(self.backoff * (2 ** (attempt - 1)))
                    continue
                return None, attempts, last_err
        return None, attempts, last_err

    def ask(self, text):
        return self.request("/ask", {"text": text})

    def reset(self):
        return self.request("/reset", {})

    def status(self):
        data, attempts, err = self.request("/status", None, timeout=30)
        return data, attempts, err


def tokens_of(status_doc):
    try:
        return int((status_doc or {}).get("session", {}).get("chat_tokens"))
    except (TypeError, ValueError):
        return None


def filler_text(turn, rng):
    a = rng.choice(FILLER)
    b = rng.choice(FILLER)
    return "第%d段：%s%s" % (turn, a, b)


def plan_doc(args):
    return {
        "script": os.path.basename(SCRIPT),
        "script_sha256": sha256_file(SCRIPT)[0],
        "endpoint": args.endpoint,
        "target_chars": args.target_chars,
        "max_turns": args.max_turns,
        "request_timeout_s": args.request_timeout,
        "retries": args.retries,
        "backoff_s": args.backoff,
        "reset_first": not args.no_reset,
        "seed": args.seed,
        "status_every": args.status_every,
        "facts": [{k: f[k] for k in ("id", "tier", "threshold", "question", "keywords")}
                  for f in FACTS],
        "probe_sets": ["8 facts recall", "repeated same fact x3",
                       "post-rollover '刚才说的'", "10x continuous no-reset"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="long-context stress test v2 (rollover + recall)")
    ap.add_argument("--endpoint", default=DEFAULT_EP)
    ap.add_argument("--target-chars", type=int, default=40000)
    ap.add_argument("--max-turns", type=int, default=500)
    ap.add_argument("--request-timeout", type=float, default=300.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--backoff", type=float, default=1.0)
    ap.add_argument("--status-every", type=int, default=1,
                    help="每 N turn 采一次 /status.chat_tokens（默认每 turn）")
    ap.add_argument("--seed", type=int, default=20261028)
    ap.add_argument("--out", default=os.path.join(ROOT, "tmp", "LONG-CONV-TEST-V2.json"))
    ap.add_argument("--no-reset", action="store_true")
    ap.add_argument("--fail-fast", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="小规模冒烟（2k 字符/最多 20 turn）")
    ap.add_argument("--dry-run", action="store_true", help="零请求：只打印计划")
    args = ap.parse_args(argv)
    if args.smoke:
        args.target_chars = min(args.target_chars, 2000)
        args.max_turns = min(args.max_turns, 20)

    plan = plan_doc(args)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan,
                          "estimated_filler_calls": "≈%d turns to reach %d chars"
                                                    % (args.target_chars // 120, args.target_chars)},
                         ensure_ascii=False, indent=1))
        return 0

    rng = random.Random(args.seed)
    client = Client(args.endpoint, args.request_timeout, args.retries, args.backoff)
    doc = {"schema": "long_conv_test_v2", "version": 2,
           "started_at": now(), "plan": plan, "service_before": None,
           "turns": [], "rollovers": [], "facts": [],
           "probes": {"facts": [], "repeated": None, "post_rollover": None},
           "scenarios": {"no_reset_continuous": None},
           "errors": [], "summary": {}, "partial": True}

    def dump():
        out = args.out
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        os.replace(tmp, out)

    t_start = time.time()
    try:
        st, _a, _e = client.status()
        doc["service_before"] = {k: st.get(k) for k in
                                 ("version", "engine_meta", "session", "memories")
                                 if isinstance(st, dict)} if st else None
        if not args.no_reset:
            _r, _ra, rerr = client.reset()
            if rerr:
                doc["errors"].append({"phase": "reset", "error": rerr, "attempts": _ra})
                if args.fail_fast:
                    raise SystemExit(3)

        # ---- 主循环：按字符阈值灌入 8 事实 ----
        chars = 0
        turn = 0
        pending = [dict(f) for f in FACTS]
        tokens_now = tokens_of(st)
        while chars < args.target_chars and turn < args.max_turns:
            turn += 1
            fact = None
            if pending and chars >= pending[0]["threshold"]:
                fact = pending.pop(0)
                fact["turn"] = turn
                fact["chars_at_insert"] = chars
            text = fact["text"] if fact else filler_text(turn, rng)
            t0 = time.time()
            resp, attempts, err = client.ask(text)
            elapsed = round(time.time() - t0, 3)
            status_error = None
            if args.status_every > 1 and turn % args.status_every != 0 and not err:
                tokens = None
            else:
                sd, _sa, status_error = client.status()
                tokens = tokens_of(sd)
            rollover = (resp or {}).get("rollover") if isinstance(resp, dict) else None
            rec = {"turn": turn, "chars_before": chars, "text_len": len(text),
                   "is_fact": bool(fact), "fact_id": fact["id"] if fact else None,
                   "elapsed_s": elapsed, "attempts": attempts, "error": err,
                   "chat_tokens": tokens, "state": (resp or {}).get("state") if isinstance(resp, dict) else None,
                   "refused": (resp or {}).get("refused") if isinstance(resp, dict) else None,
                   "answer_len": len(str((resp or {}).get("answer") or "")),
                   "status_error": status_error,
                   "rollover": rollover}
            doc["turns"].append(rec)
            if err:
                doc["errors"].append({"phase": "ask", "turn": turn, "error": err,
                                      "attempts": attempts})
                if args.fail_fast:
                    raise SystemExit(3)
                dump()
                continue
            chars += len(text)
            tokens_now = tokens if tokens is not None else tokens_now
            if fact:
                doc["facts"].append({"id": fact["id"], "tier": fact["tier"],
                                     "turn": turn, "chars_at_insert": fact["chars_at_insert"]})
            if rollover:
                doc["rollovers"].append({"turn": turn, "chars": chars,
                                         "chat_tokens": tokens_now,
                                         "rollover": rollover})
                print("ROLLOVER turn=%d chars=%d tokens=%s %s" %
                      (turn, chars, tokens_now,
                       json.dumps(rollover, ensure_ascii=False)[:160]), flush=True)
            if turn % 25 == 0:
                print("turn=%d chars=%d tokens=%s rollovers=%d" %
                      (turn, chars, tokens_now, len(doc["rollovers"])), flush=True)
            dump()

        doc["summary"]["main_loop"] = {"turns": turn, "chars": chars,
                                       "chat_tokens_end": tokens_now,
                                       "rollovers": len(doc["rollovers"]),
                                       "elapsed_s": round(time.time() - t_start, 1),
                                       "errors": len(doc["errors"]),
                                       "retries_used": client.retries_used,
                                       "requests": client.requests}

        # ---- 探针 A：8 事实召回（early/mid/recent） ----
        for f in FACTS:
            ans, attempts, err = client.ask(f["question"])
            a = str((ans or {}).get("answer") or "")
            ok = (not err) and all(k in a for k in f["keywords"])
            doc["probes"]["facts"].append({"id": f["id"], "tier": f["tier"],
                                           "question": f["question"], "keywords": f["keywords"],
                                           "answer": a[:160], "pass": ok,
                                           "state": (ans or {}).get("state"),
                                           "attempts": attempts, "error": err})
            print(("PASS " if ok else "FAIL ") + f["question"] + " -> " + a[:70], flush=True)

        # ---- 探针 B：重复问同一事实 3 次（一致性） ----
        last_fact = FACTS[-1]
        reps = []
        for i in range(3):
            ans, attempts, err = client.ask(last_fact["question"])
            a = str((ans or {}).get("answer") or "")
            reps.append({"i": i + 1, "answer": a[:160], "error": err, "attempts": attempts})
        all_ok = all((not r["error"]) and all(k in r["answer"] for k in last_fact["keywords"])
                     for r in reps)
        consistent = len({r["answer"].strip() for r in reps}) == 1
        doc["probes"]["repeated"] = {"fact_id": last_fact["id"],
                                     "question": last_fact["question"],
                                     "runs": reps, "all_pass": all_ok,
                                     "consistent": consistent}
        print("REPEATED pass=%s consistent=%s" % (all_ok, consistent), flush=True)

        # ---- 探针 C：跨 rollover 追问“刚才说的” ----
        roll = doc["rollovers"][0] if doc["rollovers"] else None
        if roll:
            before = [f for f in FACTS if f.get("turn") and f["turn"] < roll["turn"]]
            target = before[-1] if before else None
            q = "我刚才说的、关于我的最后一件具体的事是什么？"
            ans, attempts, err = client.ask(q)
            a = str((ans or {}).get("answer") or "")
            if target:
                ok = (not err) and all(k in a for k in target["keywords"])
                doc["probes"]["post_rollover"] = {
                    "question": q, "expect_fact_id": target["id"],
                    "keywords": target["keywords"], "answer": a[:160],
                    "pass": ok, "attempts": attempts, "error": err,
                    "rollover_turn": roll["turn"]}
            else:
                doc["probes"]["post_rollover"] = {"question": q, "answer": a[:160],
                                                  "pass": None,
                                                  "reason": "rollover 前无事实埋点"}
            print("POST-ROLLOVER pass=%s -> %s" %
                  (doc["probes"]["post_rollover"].get("pass"), a[:70]), flush=True)
        else:
            doc["probes"]["post_rollover"] = {"pass": None,
                                              "reason": "本次未触发 rollover"}

        # ---- 场景 D：长时间连续提问不 reset（10 连问 + token 增长） ----
        tok_before = tokens_now
        cont = []
        for i in range(1, 11):
            ans, attempts, err = client.ask("第%d次连续追问：今天几号？" % i)
            a = str((ans or {}).get("answer") or "")
            sd, _sa, _se = client.status()
            cont.append({"i": i, "answer_len": len(a), "attempts": attempts,
                         "error": err, "chat_tokens": tokens_of(sd)})
        tok_after = cont[-1]["chat_tokens"] if cont else tok_before
        doc["scenarios"]["no_reset_continuous"] = {
            "runs": cont, "tokens_start": tok_before, "tokens_end": tok_after,
            "token_delta": ((tok_after - tok_before)
                            if isinstance(tok_before, int) and isinstance(tok_after, int) else None),
            "all_ok": all(not c["error"] for c in cont)}
        print("NO-RESET continuous all_ok=%s token_delta=%s" %
              (doc["scenarios"]["no_reset_continuous"]["all_ok"],
               doc["scenarios"]["no_reset_continuous"]["token_delta"]), flush=True)

        # ---- 汇总 ----
        by_tier = {}
        for p in doc["probes"]["facts"]:
            d = by_tier.setdefault(p["tier"], {"n": 0, "pass": 0})
            d["n"] += 1
            d["pass"] += 1 if p["pass"] else 0
        post = doc["probes"]["post_rollover"] or {}
        doc["summary"].update({
            "facts_recall": {"n": len(doc["probes"]["facts"]),
                             "pass": sum(1 for p in doc["probes"]["facts"] if p["pass"]),
                             "by_tier": by_tier},
            "repeated": {"pass": bool(doc["probes"]["repeated"]["all_pass"]),
                         "consistent": bool(doc["probes"]["repeated"]["consistent"])},
            "post_rollover": {"pass": post.get("pass")},
            "no_reset_continuous": doc["scenarios"]["no_reset_continuous"]["all_ok"],
            "rollover_triggered": len(doc["rollovers"]) > 0,
            "errors": len(doc["errors"]),
            "verdict": None,
        })
        s = doc["summary"]
        s["verdict"] = ("PASS" if (s["facts_recall"]["pass"] == s["facts_recall"]["n"]
                                   and s["repeated"]["pass"] and s["repeated"]["consistent"]
                                   and post.get("pass") is not False
                                   and s["no_reset_continuous"]
                                   and s["rollover_triggered"]
                                   and s["errors"] == 0) else "CHECK")
        doc["finished_at"] = now()
        doc["wall_s"] = round(time.time() - t_start, 1)
        doc["partial"] = False
        dump()
        print("VERDICT %s | facts %d/%d | rollovers %d | errors %d | wall %.0fs | saved %s" %
              (s["verdict"], s["facts_recall"]["pass"], s["facts_recall"]["n"],
               len(doc["rollovers"]), len(doc["errors"]), doc["wall_s"], args.out), flush=True)
        return 0 if s["verdict"] == "PASS" else 1
    except KeyboardInterrupt:
        doc["partial"] = True
        doc["interrupted_at"] = now()
        dump()
        print("INTERRUPTED; partial saved to %s" % args.out, flush=True)
        return 130
    except SystemExit:
        doc["partial"] = True
        dump()
        raise
    except Exception as exc:                          # noqa: BLE001
        doc["partial"] = True
        doc["fatal"] = repr(exc)
        dump()
        print("FATAL %r; partial saved" % exc, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())