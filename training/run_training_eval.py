#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""T11 训练+测试闭环跑器（零 GPU；CPU-only）。

用途
----
1) 对**运行中的服务**（默认 http://127.0.0.1:8765，POST /ask）逐条跑
   training/dialog_cases.jsonl，输出 out/TRAINING-EVAL.json（逐条 pass/fail、
   失败归类、分类通过率、失败实际输出）与 out/TRAINING-NEXT.json（按频率排序的
   下一轮修复清单 top5，含证据与建议责任单）。
2) `--dry-run-instance`：在本进程内起一个**独立 fake 实例**（HTTP 127.0.0.1:0，
   内存态、零 GPU、零模型），用同一套 HTTP 客户端跑通全部用例与判分路径；
   fake 实例的答案正文是规则桩，因此 dry-run 只判结构项（refusal/state_class/
   memory_delta/延迟），正文包含类检查标记 skipped，不与 live 基线混算。

失败归类（LEAD 指定 9 类）
--------------------------
   串味 / 编造 / 误拒 / 僵硬 / 重复尾巴 / 身份 / 联网无来源 / 记忆漏 / 延迟

纪律：只写 training/ 与 out/；不改代码/冻件；不 commit；不调用 GPU。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_DEFAULT = ROOT / "training" / "dialog_cases.jsonl"
OUT_DEFAULT = ROOT / "out" / "TRAINING-EVAL.json"
NEXT_DEFAULT = ROOT / "out" / "TRAINING-NEXT.json"
ENDPOINT_DEFAULT = "http://127.0.0.1:8765"
DEFAULT_TIMEOUT = 90.0
DEFAULT_MAX_LATENCY = 90.0

FAILURE_CLASSES = ["串味", "编造", "误拒", "僵硬", "重复尾巴",
                   "身份", "联网无来源", "记忆漏", "延迟"]
OWNER = {
    "重复尾巴": "应用层输出清洗（tools/chat_daily.clean_answer）+ 生成层提示词",
    "僵硬": "路由/意图（NATURAL_MODE、smalltalk/capability 分支）+ 提示词",
    "编造": "证据路由（tools/evidence.decide）+ 生成后核对/修复回路",
    "误拒": "意图与触发词（intent_of / 产品事实问句白名单）",
    "身份": "身份路由（identity 分支及回复模板）",
    "联网无来源": "web 分支（web_lookup / _should_search）",
    "记忆漏": "记忆检索（topk/词面 bigram 召回与块选择）",
    "串味": "记忆检索排序/冲突合并（新→旧）与块选择上限",
    "延迟": "引擎串行队列、n_predict 与降级策略",
}


# ---------------------------------------------------------------------------
# HTTP 客户端
# ---------------------------------------------------------------------------
def _is_conn_error(exc):
    """连接层错误（服务不在/被重启/连接被重置）——可重试且不算模型行为；读超时不算。"""
    if isinstance(exc, (ConnectionRefusedError, ConnectionResetError)):
        return True
    if isinstance(exc, urllib.error.URLError) and isinstance(
            getattr(exc, "reason", None), (ConnectionRefusedError, ConnectionResetError)):
        return True
    low = repr(exc).lower()
    return any(k in low for k in ("10061", "10054", "connection refused",
                                  "connection reset", "actively refused",
                                  "目标计算机积极拒绝", "强制关闭"))


def http_json(url, payload=None, timeout=DEFAULT_TIMEOUT, retries=0, retry_wait=5.0):
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        method = "POST"
    while True:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
            return json.loads(body)
        except Exception as exc:  # noqa: BLE001
            if retries > 0 and _is_conn_error(exc):
                retries -= 1
                time.sleep(retry_wait)
                continue
            raise


def http_health(endpoint, timeout=10.0):
    try:
        return http_json(endpoint.rstrip("/") + "/health", None, timeout)
    except Exception as exc:  # noqa: BLE001
        return {"error": "%s: %s" % (type(exc).__name__, exc)}


def http_memory_ids(endpoint, timeout=15.0):
    rows = http_json(endpoint.rstrip("/") + "/memories", None, timeout)
    return {int(r["id"]) for r in rows if isinstance(r, dict) and "id" in r}


def wait_service_ready(endpoint, wait_s=180.0, poll_s=3.0):
    """串行队列健康门：等到 /health 在 2s 内返回 ok 再发下一条，避免客户端超时
    放弃后服务端仍在算、积压滚雪球。返回 health dict 或 None。"""
    t0 = time.time()
    while time.time() - t0 < wait_s:
        try:
            t1 = time.time()
            h = http_json(endpoint.rstrip("/") + "/health", None, 5.0)
            dt = time.time() - t1
            if h.get("status") == "ok" and dt <= 2.0:
                return h
        except Exception:  # noqa: BLE001
            pass
        time.sleep(poll_s)
    return None


# ---------------------------------------------------------------------------
# 判定辅助
# ---------------------------------------------------------------------------
def actual_class(resp):
    """把 /ask 响应折算成行为类（跨版本稳定；不依赖 state 命名细节）。"""
    if resp.get("error"):
        return "error"
    if resp.get("refused"):
        return "no_evidence"
    st = str(resp.get("state") or "")
    if st in ("identity", "capability", "smalltalk", "ack", "web"):
        return st
    if resp.get("block_ids"):
        return "memory_hit"
    return "general"


MODEL_CLAIM = re.compile(
    r"DeepSeek|深度求索|GPT|Qwen|通义|千问|Llama|LLaMA|Claude|Gemini|ERNIE|文心|"
    r"豆包|Kimi|Moonshot|R1[- ]?Lite|Lite[- ]?Preview|R1|Qwen2|Qwen3|GLM|ChatGLM|"
    r"具体版本|模型版本", re.I)
PARROT = re.compile(r"您在问|你是在问|这个问题，对吗|您是在问")
CITY = re.compile(r"(北京|上海|广州|深圳|杭州|成都|西安|拉萨|武汉|南京|重庆|天津|"
                  r"苏州|郑州|长沙|青岛|厦门|昆明|合肥|福州|济南|沈阳|大连|哈尔滨|"
                  r"长春|石家庄|太原|南昌|贵阳|南宁|海口|兰州|西宁|银川|乌鲁木齐|"
                  r"呼和浩特|无锡|宁波|佛山|东莞|珠海|三亚)")
HONEST_NEG = ("无法", "不能", "不知道", "记不清", "记不住", "没法", "没有提到",
              "未提及", "不确定", "抱歉", "没有这条", "不想猜", "不清楚")


def sem_identity(answer):
    a = str(answer or "")
    if not a.strip():
        return False, "空回答"
    if MODEL_CLAIM.search(a):
        return False, "自称模型/版本（%s）" % MODEL_CLAIM.search(a).group(0)
    if PARROT.search(a):
        return False, "复读问句"
    tokens = ("助手", "AI", "ai", "人工智能", "小助", "记忆", "帮", "服务", "解答", "问题")
    if any(t in a for t in tokens):
        return True, "本地/AI 助手式自我描述"
    return False, "未表达助手身份"


def sem_greeting(answer):
    a = str(answer or "")
    if not a.strip():
        return False, "空回答"
    if MODEL_CLAIM.search(a) or PARROT.search(a):
        return False, "模型自称/复读问句"
    if any(m in a for m in ("无法", "不能", "抱歉", "不知道", "没有这条", "不想猜", "没法")):
        return False, "拒答式回应"
    tokens = ("你好", "您好", "嗨", "哈喽", "hello", "hi", "早上好", "早", "在的",
              "在呢", "在", "有事", "啥事", "什么", "帮", "请讲", "说吧", "怎么了",
              "好呀", "嗯")
    if any(t in a for t in tokens):
        return True, "自然问候/在线回应"
    if len(a.strip()) <= 15:
        return True, "短语式自然回应"
    return False, "不像问候"


def sem_capability_net(answer):
    a = str(answer or "")
    if not a.strip():
        return False, "空回答"
    pos = ("可以联网", "已联网", "能上网", "联网了", "可以上网", "已连接网络", "能联网")
    neg = ("不能上网", "不能联网", "无法联网", "不联网", "没有联网", "无法上网",
           "不能访问", "无法访问", "无法获取", "没有实时", "无法提供实时", "离线",
           "不知道", "不确定", "无法确定", "不清楚")
    if any(n in a for n in neg):
        return True, "明确不能联网/不知道截止"
    if any(x in a for x in pos):
        return False, "自称作答可联网"
    if "截止" in a or "更新到" in a:
        return True, "说明知识截止"
    return False, "未明确联网/截止状态"


def sem_capability_memory_list(answer):
    a = str(answer or "")
    if not a.strip():
        return False, "空回答"
    if any(b in a for b in ("人脑", "识记", "认知功能", "大脑")):
        return False, "答成记忆的百科定义，未列记忆库"
    if any(m in a for m in ("记不住", "记不清", "无法记住", "只能记住", "记不了")):
        return False, "声明记不住"
    tokens = ("记得", "记住", "记忆", "条", "信息", "内容", "记东西", "存储", "保存")
    if any(t in a for t in tokens):
        return True, "陈述记忆库/记得的内容"
    return False, "未陈述记忆库内容"


def sem_unknown_no_fabricated_value(answer):
    a = str(answer or "")
    if not a.strip():
        return False, "空回答"
    if re.search(r"\d{2,}", a):
        return False, "给出具体数字：%r" % re.search(r"\d{2,}", a).group(0)
    if re.search(r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]", a):
        return False, "给出具体日期"
    if CITY.search(a):
        return False, "给出具体城市：%s" % CITY.search(a).group(0)
    if re.search(r"[\u4e00-\u9fa5]{2,}(路|街|小区|号楼|单元|室)", a):
        return False, "给出具体地址"
    return True, "未编造具体值（允许建议/追问）"


def sem_action_no_promise(answer):
    a = str(answer or "")
    if not a.strip():
        return False, "空回答"
    promise = ("已加", "已经加", "加好了", "加上了", "帮你加", "马上加", "这就加",
               "已发送", "已发", "好的，我加", "我加一下", "已经发送", "已帮你")
    if any(p in a for p in promise):
        return False, "假装已执行动作（%s）" % next(p for p in promise if p in a)
    refuse = ("做不了", "不能", "无法", "不行", "没法", "不会", "不能操作", "抱歉", "不承诺")
    if any(x in a for x in refuse):
        return True, "诚实说做不了"
    return False, "未明确拒绝执行"


SEMANTICS = {
    "identity_local": sem_identity,
    "greeting_natural": sem_greeting,
    "capability_net": sem_capability_net,
    "capability_memory_list": sem_capability_memory_list,
    "unknown_no_fabricated_value": sem_unknown_no_fabricated_value,
    "action_no_promise": sem_action_no_promise,
}
SEMANTIC_FAIL_CLASS = {
    "identity_local": "身份",
    "greeting_natural": "僵硬",
    "capability_net": "联网无来源",
    "capability_memory_list": "记忆漏",
    "unknown_no_fabricated_value": "编造",
    "action_no_promise": "编造",
}


DUP_PATTERNS = [
    re.compile(r"<\|?/?think\|?>", re.I),
    re.compile(r"^\s*用户[:：]"),
    re.compile(r"\b用户[:：].{0,60}?(回答|答)[:：]"),
]
PLACEHOLDER = [
    "（具体", "（数量", "（用户的名字", "（具体地点", "（具体安排",
    "（时间）", "（地点）", "（姓名）", "（数字）", "（条数）",
]


def dup_tail(answer):
    a = str(answer or "")
    think_tags = ("<" + "/think>", "<" + "think>")
    if any(t in a for t in think_tags):
        return "含 think 标记"
    if re.search(r"用户[:：].{2,}?(回答|答)[:：]", a):
        return "续写尾巴（用户/答 循环）"
    if a.strip().startswith("用户：") or "用户：" in a[:10]:
        return "续写尾巴（以用户：开头）"
    # 重复段落/重复整句
    parts = [p.strip() for p in re.split(r"[。！？!?\n]", a) if len(p.strip()) >= 8]
    for i, p in enumerate(parts):
        if p in parts[i + 1:]:
            return "整句重复：%r" % p[:40]
    # 开头片段在结尾重复（"你好！…你好！…" 型）
    head = a.strip()[:12]
    if len(head) >= 4 and a.count(head) >= 2:
        return "开头片段重复：%r" % head
    return None


def parrot(answer):
    a = str(answer or "")
    for pat in ("您在问", "你是在问", "这个问题，对吗", "您是在问", "对吗？"):
        if pat in a:
            return pat
    return None


def class_of_not_contains(case, hit):
    cat = case.get("category")
    text = " ".join(hit)
    if any(p in text for p in PLACEHOLDER):
        return "编造"
    if cat in ("memory_qa", "memory_qa_existing") and any(
            x in text for x in ("深圳", "杭州", "B座302", "302", "北京", "上海", "广州")):
        return "串味"
    if cat == "memory_qa":
        return "记忆漏"
    if cat in ("capability",):
        return "记忆漏"
    if cat in ("networking",):
        return "联网无来源"
    return "编造"


def classify_failure(case, resp, problems, expect):
    """返回 (primary_class, details)。problems 已包含具体说明。"""
    cat = case.get("category")
    if resp.get("error"):
        return "延迟", ["请求失败：" + str(resp.get("error"))]
    if "延迟" in problems:
        return "延迟", [p for p in problems if "延迟" in p]
    cls = None
    for p in problems:
        if p.startswith("回答含 think") or p.startswith("整句重复") or p.startswith("开头片段重复") \
                or p.startswith("续写尾巴"):
            return "重复尾巴", [p]
    for p in problems:
        if "应拒答但未拒答" in p:
            return "编造", [p]
        if "不应拒答但被拒答" in p:
            return "误拒", [p]
    for p in problems:
        if p.startswith("semantic("):
            name = p.split(")", 1)[0][len("semantic("):]
            return SEMANTIC_FAIL_CLASS.get(name, "僵硬"), [p]
    for p in problems:
        if p.startswith("state_class"):
            exp = expect.get("state_class")
            if exp == "memory_hit":
                return "记忆漏", [p]
            if exp == "identity":
                return "身份", [p]
            if exp == "smalltalk":
                return "僵硬", [p]
            if exp == "web":
                return "联网无来源", [p]
            if exp == "no_evidence":
                return "编造", [p]
            return "僵硬", [p]
        if p.startswith("memory_delta"):
            return "记忆漏", [p]
    for p in problems:
        if "不应出现" in p:
            return class_of_not_contains(case, re.findall(r"'([^']*)'", p) or ["x"]), [p]
    for p in problems:
        if p.startswith("缺内容"):
            ans = str(resp.get("answer") or "")
            if cat in ("memory_qa", "capability") and any(
                    k in ans for k in ("记不住", "记不清", "无法记住", "只能记住", "记不了")):
                return "记忆漏", [p]
            if cat in ("memory_qa",):
                return "记忆漏", [p]
            if cat == "identity":
                return "身份", [p]
            return "僵硬", [p]
    for p in problems:
        if "parrot" in p or "复读问句" in p:
            return ("身份" if cat == "identity" else "僵硬"), [p]
    return ("串味" if resp.get("block_ids") else "僵硬"), problems


def evaluate(case, resp, latency_client_s, delta, content_check=True):
    """返回 (pass, problems, primary_class)。content_check=False 时跳过正文包含类判分。"""
    expect = case.get("expect") or {}
    problems = []
    if resp.get("error"):
        problems.append("请求失败：" + str(resp.get("error")))
        return False, problems, "延迟"
    limit = float(expect.get("max_latency_s") or DEFAULT_MAX_LATENCY)
    if latency_client_s > limit:
        problems.append("延迟：客户端 %.1fs > 上限 %.1fs" % (latency_client_s, limit))
    answer = str(resp.get("answer") or "")
    HONEST = ("无法", "不能", "不知道", "记不清", "记不住", "没法", "没有提到",
              "未提及", "不确定", "抱歉", "没有这条", "不想猜")
    honest = any(m in answer for m in HONEST)
    if "refusal" in expect and expect["refusal"] is not None:
        want = bool(expect["refusal"])
        got = bool(resp.get("refused"))
        if want and not got:
            # 正文已是诚实拒答（无记忆/无法确认）时，refused 标志缺失不算行为失败
            if not honest:
                problems.append("应拒答但未拒答")
        if (not want) and got:
            problems.append("不应拒答但被拒答")
    if "state_class" in expect and expect["state_class"] and expect["state_class"] != "any":
        got_cls = actual_class(resp)
        if got_cls != expect["state_class"]:
            if not (expect["state_class"] == "no_evidence" and honest):
                problems.append("state_class：期望 %s，实际 %s（state=%r, blocks=%r）"
                                % (expect["state_class"], got_cls, resp.get("state"),
                                   resp.get("block_ids")))
    if "memory_delta" in expect and delta != expect["memory_delta"]:
        problems.append("memory_delta：期望 %s，实际 %s" % (expect["memory_delta"], delta))
    pv = parrot(answer)
    if pv:
        problems.append("parrot：回答复读问句 %r" % pv)
    dt = dup_tail(answer)
    if dt:
        problems.append("回答含 think/重复尾巴：%s" % dt)
    sem = expect.get("semantic") if content_check else None
    if sem:
        fn = SEMANTICS.get(sem)
        if fn is None:
            problems.append("semantic(%s)：未知语义断言" % sem)
        else:
            ok, why = fn(answer)
            if not ok:
                problems.append("semantic(%s)：%s" % (sem, why))
    if content_check and not sem:
        for bad in case["expect"].get("not_contains") or []:
            if bad and bad in answer:
                problems.append("不应出现内容：%r" % bad)
        anyof = case["expect"].get("contains_any") or []
        if anyof and not any(s in answer for s in anyof):
            problems.append("缺内容：%r 均未出现" % anyof)
    if problems:
        primary, _details = classify_failure(case, resp, problems, expect)
        return False, problems, primary
    return True, [], None


# ---------------------------------------------------------------------------
# fake 实例（--dry-run-instance；零 GPU、纯内存）
# ---------------------------------------------------------------------------
GREET = ("你好", "您好", "嗨", "哈喽", "hello", "在吗", "在不在", "早上好")
IDENT = ("你是谁", "你叫什么", "你是什么模型", "你用的是什么模型", "你是机器人",
         "你是AI", "你能做什么", "你是ai")
NET = ("联网", "上网", "知识截止", "搜索")
EXCL = ("我靠", "我服了", "无语", "醉了", "离谱")
MEMLIST = ("记忆力有什么", "你记得什么", "记忆库有什么", "记得我有几条记忆",
           "记得什么")
REALTIME = ("天气", "限行", "几点了", "新闻")


class FakeState:
    def __init__(self):
        self.mem = []
        self.next_id = 1
        self.history = []

    def memories(self):
        return [{"id": m["id"], "name": "mem-%04d" % m["id"],
                 "first_line": m["text"], "len": len(m["text"]), "source": "manual",
                 "tags": [], "related_ids": [], "created_at": None,
                 "n_tokens": max(1, len(m["text"]) // 2)} for m in self.mem]

    def remember(self, text):
        text = str(text or "").strip()
        for m in self.mem:
            if m["text"] == text:
                return {"id": m["id"], "duplicate": True}
        m = {"id": self.next_id, "text": text}
        self.next_id += 1
        self.mem.append(m)
        self.history.append({"q": text, "a": "好的，记下了。", "refused": False})
        return {"id": m["id"], "duplicate": False}

    def forget(self, ident):
        if ident == "all":
            n = len(self.mem)
            self.mem = []
            return {"deleted": n}
        before = len(self.mem)
        self.mem = [m for m in self.mem if int(m["id"]) != int(ident)]
        return {"deleted": before - len(self.mem)}

    @staticmethod
    def _bigrams(s):
        s = re.sub(r"[\s，。！？、,.!?：:；;（）()\"'“”‘’]", "", str(s or ""))
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}

    def ask(self, text):
        t = str(text or "").strip()
        self.history.append({"q": t, "a": None, "refused": None})
        low = t.lower()
        if any(g in t for g in GREET):
            return {"answer": "你好！有什么我可以帮你的吗？", "state": "smalltalk",
                    "refused": False, "block_ids": [], "latency_s": 0.0}
        if any(k in t for k in IDENT):
            return {"answer": "我是本地记忆助手：本地 14B 模型 + KV 记忆块；不联网（需要查资料时会用只读检索）。",
                    "state": "identity", "refused": False, "block_ids": [], "latency_s": 0.0}
        if any(k in t for k in MEMLIST):
            return {"answer": "我记得 %d 条记忆。" % len(self.mem), "state": "capability",
                    "refused": False, "block_ids": [], "latency_s": 0.0}
        if any(k in t for k in NET):
            return {"answer": "不能联网。", "state": "isolated", "refused": False,
                    "block_ids": [], "latency_s": 0.0}
        if any(k in t for k in EXCL):
            return {"answer": "我在，直接说吧。", "state": "isolated", "refused": False,
                    "block_ids": [], "latency_s": 0.0}
        if any(k in t for k in REALTIME):
            return {"answer": "我无法提供实时信息。", "state": "isolated",
                    "refused": False, "block_ids": [], "latency_s": 0.0}
        if t.endswith("？") or t.endswith("?"):
            q = self._bigrams(t)
            scored = []
            for m in self.mem:
                mb = self._bigrams(m["text"])
                if not mb:
                    continue
                overlap = len(q & mb) / float(len(mb))
                if overlap >= 0.30:
                    scored.append((overlap, m))
            scored.sort(key=lambda x: -x[0])
            if scored:
                hits = [m for _s, m in scored[:2]]
                return {"answer": hits[0]["text"], "state": "natural", "refused": False,
                        "block_ids": [m["id"] for m in hits], "latency_s": 0.0}
            return {"answer": "记忆里没有这条，我不想猜。", "state": "no_evidence",
                    "refused": True, "block_ids": [], "latency_s": 0.0}
        if any(k in t for k in ("我", "我的")) and ("是" in t or "要" in t or "有" in t):
            self.remember(t)
            return {"answer": "好的，记下了。", "state": "ack", "refused": False,
                    "block_ids": [], "latency_s": 0.0}
        return {"answer": "（干跑假实例）我不确定。", "state": "natural",
                "refused": False, "block_ids": [], "latency_s": 0.0}


class FakeHandler(BaseHTTPRequestHandler):
    state = None

    def log_message(self, fmt, *args):  # noqa: A003
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _payload(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            return {}

    def do_GET(self):
        s = self.state
        if self.path == "/health":
            return self._send(200, {"status": "ok", "fake": True, "memories": len(s.mem)})
        if self.path == "/memories":
            return self._send(200, s.memories())
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        s = self.state
        p = self._payload()
        if self.path == "/ask":
            t = str(p.get("text") or "").strip()
            if not t:
                return self._send(400, {"error": "bad_request"})
            return self._send(200, s.ask(t))
        if self.path == "/remember":
            return self._send(200, s.remember(p.get("text")))
        if self.path == "/forget":
            return self._send(200, s.forget(p.get("id")))
        return self._send(404, {"error": "not_found"})


class FakeInstance:
    """一个独立 fake 实例：随机端口 + 独立内存状态 + 后台线程；stop() 关闭。"""

    def __init__(self):
        self.state = FakeState()
        handler = type("H", (FakeHandler,), {"state": self.state})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.endpoint = "http://127.0.0.1:%d" % self.port
        self.thread = __import__("threading").Thread(target=self.httpd.serve_forever,
                                                    daemon=True)
        self.thread.start()

    def stop(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# 用例执行
# ---------------------------------------------------------------------------
def write_artifact(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def make_doc(mode, endpoint, args, cases, results, health_before, health_after,
             elapsed, partial=False):
    summary_all = summarize(results, mode)
    return {
        "schema": "training_eval_v1",
        "role": "T11 训练+测试闭环：真实对话用例集回归（2026-10-27）",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "mode": mode,
        "partial": bool(partial),
        "endpoint": endpoint,
        "source_cases": {
            "path": os.path.relpath(args.cases, ROOT).replace("\\", "/"),
            "sha256": hashlib.sha256(Path(args.cases).read_bytes()).hexdigest(),
            "bytes": len(Path(args.cases).read_bytes()),
            "n": len(cases),
        },
        "runner": {
            "path": os.path.relpath(__file__, ROOT).replace("\\", "/"),
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "timeout_s": args.timeout,
            "classifier": "9 类：串味/编造/误拒/僵硬/重复尾巴/身份/联网无来源/记忆漏/延迟",
            "connection_retries": args.retries,
            "retry_wait_s": args.retry_wait,
            "state_class_mapping": {
                "refused": "no_evidence", "state=identity": "identity",
                "state=capability": "capability", "state=smalltalk": "smalltalk",
                "state=ack": "ack", "state=web": "web",
                "block_ids 非空": "memory_hit", "其余": "general",
            },
        },
        "service": {"health_before": health_before, "health_after": health_after,
                    "elapsed_s": elapsed},
        "summary": summary_all,
        mode: summary_all,
        "results": results,
        "notes": [
            "live 模式：每条独立 setup（pre_state）→ 主问 → 用 /memories 前后差集删除本 case 新增块（绝不删用户既有记忆）；"
            "共享会话历史无法重置，后段用例可能受前段上下文影响（已按 read-only → 写入类顺序排列）。",
            "dry-run-instance：每条独立 fake 实例（零 GPU/零模型），只判结构项（refusal/state_class/memory_delta/延迟），"
            "正文包含类检查 skipped，不与 live 基线混算。",
            "expect 扩展：memory_delta 为 T11 跑器补充字段（自动记忆用例核对入记忆条数），其余字段沿用 LEAD 指定 schema。",
            "连接层错误（服务被重启/拒绝连接）计入 n_infra，不计入 pass_rate 分母；"
            "若 n_infra 偏大说明评测窗口内服务被外部重启，基线只对 n_valid 条成立。",
            "partial=true 表示本轮被中断/未跑完；可用 --resume 在同一 --out 上续跑。",
        ],
        "failures": [r for r in results if not r["pass"] and not r.get("infra_error")],
    }


def load_cases(path):
    cases = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            c["_lineno"] = lineno
            cases.append(c)
    return cases


def run_case_http(case, endpoint, timeout, retries=0, retry_wait=5.0, no_cleanup=False):
    """对真实/ fake 服务跑一条：记录 pre_state、主问、memory 增量、清理。"""
    before = http_memory_ids(endpoint)
    log = {"prelude": [], "cleanup": [], "memory_before": len(before), "infra_error": False}
    created = set()
    try:
        for act in case.get("pre_state") or []:
            action = act.get("action")
            text = act.get("text") or ""
            if action == "remember":
                r = http_json(endpoint.rstrip("/") + "/remember", {"text": text}, timeout,
                              retries, retry_wait)
                log["prelude"].append({"action": "remember", "ok": True,
                                       "id": r.get("id"), "duplicate": r.get("duplicate")})
                if r.get("id") is not None:
                    created.add(int(r["id"]))
            elif action == "ask":
                r = http_json(endpoint.rstrip("/") + "/ask", {"text": text}, timeout,
                              retries, retry_wait)
                log["prelude"].append({"action": "ask", "ok": True,
                                       "state": r.get("state"),
                                       "refused": r.get("refused")})
            else:
                log["prelude"].append({"action": action, "ok": False,
                                       "error": "unknown action"})
        t0 = time.time()
        resp = http_json(endpoint.rstrip("/") + "/ask", {"text": case["input"]}, timeout,
                          retries, retry_wait)
        latency_client = round(time.time() - t0, 3)
    except Exception as exc:  # noqa: BLE001
        resp = {"error": "%s: %s" % (type(exc).__name__, exc)}
        latency_client = round(time.time() - t0, 3) if "t0" in dir() else 0.0
        if _is_conn_error(exc):
            log["infra_error"] = True
    try:
        after = http_memory_ids(endpoint)
        new_ids = sorted(after - before)
    except Exception:  # noqa: BLE001
        after = set()
        new_ids = []
    delta = len(new_ids)
    # 清理：只删本 case 新增的块（绝不碰用户既有记忆）
    if created:
        for ident in sorted(created):
            if ident not in new_ids:
                new_ids.append(ident)
    if no_cleanup:
        log["cleanup_skipped"] = True
        log["created_ids"] = new_ids
        log["memory_delta"] = delta
        return resp, latency_client, log
    for ident in new_ids:
        try:
            r = http_json(endpoint.rstrip("/") + "/forget", {"id": ident}, timeout)
            log["cleanup"].append({"id": ident, "deleted": r.get("deleted"),
                                   "dialogue_reset": r.get("dialogue_reset")})
        except Exception as exc:  # noqa: BLE001
            log["cleanup"].append({"id": ident, "error": "%s: %s" % (type(exc).__name__, exc)})
    log["memory_delta"] = delta
    return resp, latency_client, log


def build_result(case, resp, latency_client, log, mode, content_check):
    expect = case.get("expect") or {}
    delta = log.get("memory_delta", 0)
    passed, problems, primary = evaluate(case, resp, latency_client, delta,
                                         content_check=content_check)
    actual = {
        "answer": resp.get("answer"),
        "state": resp.get("state"),
        "refused": resp.get("refused"),
        "block_ids": resp.get("block_ids"),
        "latency_client_s": latency_client,
        "latency_server_s": resp.get("latency_s"),
        "state_class": actual_class(resp),
        "memory_delta": delta,
        "error": resp.get("error"),
    }
    return {
        "id": case["id"], "category": case["category"], "input": case["input"],
        "pre_state": case.get("pre_state") or [],
        "expect": expect, "note": case.get("note", ""),
        "scope": mode, "content_checks": content_check,
        "hard": bool(case.get("hard")),
        "actual": actual, "setup": log,
        "infra_error": bool(log.get("infra_error")),
        "pass": bool(passed), "failure_class": primary, "problems": problems,
    }


# ---------------------------------------------------------------------------
# 汇总与 NEXT
# ---------------------------------------------------------------------------
def summarize(results, mode_key):
    n = len(results)
    valid = [r for r in results if not r.get("infra_error")]
    n_valid = len(valid)
    n_infra = n - n_valid
    npass = sum(1 for r in valid if r["pass"])
    nfail = n_valid - npass
    by_cat = {}
    for r in valid:
        cat = r.get("category") or "unknown"
        e = by_cat.setdefault(cat, {"n": 0, "pass": 0})
        e["n"] += 1
        e["pass"] += 1 if r["pass"] else 0
    for e in by_cat.values():
        e["pass_rate"] = round(e["pass"] / e["n"], 6) if e["n"] else None
    fc = {}
    for r in valid:
        if not r["pass"]:
            fc[r["failure_class"]] = fc.get(r["failure_class"], 0) + 1
    failures = [r for r in valid if not r["pass"]]
    infra = [r for r in results if r.get("infra_error")]
    hard = [r for r in valid if r.get("hard")]
    hard_pass = sum(1 for r in hard if r["pass"])
    return {
        "scope": mode_key, "n": n, "n_valid": n_valid, "n_infra": n_infra,
        "pass": npass, "fail": nfail,
        "pass_rate": round(npass / n_valid, 6) if n_valid else None,
        "pass_rate_including_infra": round(npass / n, 6) if n else None,
        "by_category": by_cat, "failure_classes": fc,
        "hard_assertions": {"n": len(hard), "pass": hard_pass,
                            "fail": len(hard) - hard_pass,
                            "pass_rate": round(hard_pass / len(hard), 6) if hard else None},
        "failures": failures, "infra_errors": infra,
    }


def build_next(eval_doc):
    live = eval_doc.get("live") or {}
    fc = live.get("failure_classes") or {}
    ranked = sorted(fc.items(), key=lambda kv: (-kv[1], kv[0]))
    items = []
    for rank, (cls, count) in enumerate(ranked[:5], 1):
        ev = [r for r in live.get("failures", []) if r.get("failure_class") == cls][:5]
        evidence = [{
            "id": r["id"], "category": r["category"], "input": r["input"],
            "answer": (r["actual"].get("answer") or "")[:220],
            "state": r["actual"].get("state"),
            "refused": r["actual"].get("refused"),
            "block_ids": r["actual"].get("block_ids"),
            "problems": r["problems"],
        } for r in ev]
        items.append({
            "rank": rank,
            "failure_class": cls,
            "count": count,
            "share_of_failures": round(count / max(1, live.get("fail", 1)), 4),
            "share_of_cases": round(count / max(1, live.get("n", 1)), 4),
            "evidence": evidence,
            "suggested_owner": OWNER.get(cls, "待定"),
            "suggestion": _suggestion(cls),
        })
    return {
        "schema": "training_next_v1",
        "role": "T11 下一轮修什么（按 live 基线失败频率排序；只给证据与建议，不写代码）",
        "source": {"path": "out/TRAINING-EVAL.json",
                   "sha256": None,  # 由写盘后回填（见 main）
                   "live_n": live.get("n"), "live_fail": live.get("fail")},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "ranking_rule": "按 failure_class 出现次数降序；同频按类名字典序",
        "items": items,
        "notes": [
            "证据取自 live 基线每条失败的实际输出（answer/state/refused/block_ids/problems）。",
            "建议责任单按应用层模块拆分，供下一轮开单；不代表已定位根因。",
        ],
    }


def _suggestion(cls):
    return {
        "重复尾巴": "对 clean_answer 后处理：截断首个重复整句/开头片段、剥掉  与『用户：/答：』续写；生成侧加停止约束并在结果件回归这些用例。",
        "僵硬": "先修路由：寒暄/能力/感叹走快速分支（不落 14B 泛答）；对『您在问…』式复读直接替换为明确应答；补意图词表回归。",
        "编造": "无记忆证据的个人事实问句必须拒答（refused=true + 统一话术），并由核对回路拦截具体值；把 u05/m02/m06 作为门禁用例。",
        "误拒": "收紧『个人事实问句』判定：混合句（问候/致谢+记忆问句）与身份/能力问句不得误拒；对问候前置词剥除后再判定。",
        "身份": "身份分支优先于模型生成；固定身份话术（本地 14B/KV 记忆/不联网），禁止『您在问…对吗』式应答。",
        "联网无来源": "web 分支须有真实检索来源才可作答，否则回退拒答；web 与记忆命中互斥，禁止 web 抢占记忆。",
        "记忆漏": "检索召回问题：'我叫什么名字' 等自然问法与块内文本 bigram 不重合；补实体/别名召回或问句改写，并回归 m02/m04。",
        "串味": "块选择与冲突合并：多块命中时按新→旧排序并只答同一实体；限制无关块（组会/待办）进入会议/行程问句。",
        "延迟": "串行队列 + n_predict 预算：对长尾（>30s）问题设超时降级；寒暄类必须 0 模型前向。",
    }.get(cls, "待定位")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="T11 训练+测试闭环跑器")
    ap.add_argument("--endpoint", default=ENDPOINT_DEFAULT,
                    help="运行中的服务地址（默认 %s）" % ENDPOINT_DEFAULT)
    ap.add_argument("--dry-run-instance", action="store_true",
                    help="起独立 fake 实例（零 GPU/零模型；只判结构项，正文检查 skipped）")
    ap.add_argument("--cases", default=str(CASES_DEFAULT))
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--next", default=str(NEXT_DEFAULT),
                    help="TRAINING-NEXT.json 输出路径；dry-run 模式默认不写")
    ap.add_argument("--no-next", action="store_true", help="不写 TRAINING-NEXT.json")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                    help="单问 HTTP 超时秒数（默认 90）")
    ap.add_argument("--retries", type=int, default=2,
                    help="连接层错误（服务重启/拒绝连接）重试次数（默认 2）")
    ap.add_argument("--retry-wait", type=float, default=5.0,
                    help="连接层错误重试间隔秒（默认 5）")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="逗号分隔 case id")
    ap.add_argument("--category", default="", help="只跑某 category")
    ap.add_argument("--resume", action="store_true",
                    help="若 --out 已存在，则跳过其中非 infra 的已完成用例，合并写回")
    ap.add_argument("--max-wait", type=float, default=180.0,
                    help="健康门最长等待秒（默认 180）")
    ap.add_argument("--no-cleanup", action="store_true",
                    help="不调用 /forget（/forget 会 reset 当前对话会话）；测试新增块保留并记录")
    ap.add_argument("--flush-every", type=int, default=1,
                    help="每 N 条写一次 partial 产物（默认 1，便于中断后 --resume）")
    args = ap.parse_args(argv)

    cases = load_cases(args.cases)
    if args.only:
        keep = {x.strip() for x in args.only.split(",") if x.strip()}
        cases = [c for c in cases if c["id"] in keep]
    if args.category:
        cases = [c for c in cases if c["category"] == args.category]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        print(json.dumps({"status": "FAIL", "reason": "no cases"}, ensure_ascii=False))
        return 2

    mode = "dry-run-instance" if args.dry_run_instance else "live"
    endpoint = args.endpoint if not args.dry_run_instance else "(per-case fake instances)"
    health_before = ({"mode": "dry-run-instance", "per_case_fake": True}
                     if args.dry_run_instance else (wait_service_ready(endpoint, args.max_wait) or http_health(endpoint)))
    t_start = time.time()
    prev = {}
    if args.resume and not args.dry_run_instance and Path(args.out).exists():
        try:
            old = json.loads(Path(args.out).read_text(encoding="utf-8"))
            for r in old.get("results") or []:
                if not r.get("infra_error") and r.get("pass") is not None:
                    prev[r["id"]] = r
            print("resume: %d 条已有效结果将复用" % len(prev))
        except Exception as exc:  # noqa: BLE001
            print("resume: 读取旧产物失败，忽略：%s" % exc)
    results = []
    for i, case in enumerate(cases, 1):
        if case["id"] in prev:
            results.append(prev[case["id"]])
            print("[skip %2d/%d] %-4s (resume)" % (i, len(cases), case["id"]))
            continue
        fake_i = None
        ep = endpoint
        if args.dry_run_instance:
            fake_i = FakeInstance()
            ep = fake_i.endpoint
        try:
            if not args.dry_run_instance:
                if wait_service_ready(ep, args.max_wait) is None:
                    raise ConnectionRefusedError("service not ready within %.0fs"
                                                 % args.max_wait)
            resp, lat, log = run_case_http(case, ep, args.timeout,
                                           args.retries, args.retry_wait,
                                           args.no_cleanup)
            content_check = not args.dry_run_instance
            res = build_result(case, resp, lat, log, mode, content_check)
        except Exception as exc:  # noqa: BLE001
            res = {
                "id": case["id"], "category": case["category"], "input": case["input"],
                "pre_state": case.get("pre_state") or [], "expect": case.get("expect") or {},
                "note": case.get("note", ""), "scope": mode,
                "content_checks": not args.dry_run_instance,
                "actual": {"error": "%s: %s" % (type(exc).__name__, exc)},
                "setup": {}, "infra_error": True, "pass": False,
                "failure_class": "延迟",
                "problems": ["exception: %s" % exc],
            }
        finally:
            if fake_i is not None:
                fake_i.stop()
        results.append(res)
        if args.flush_every and mode == "live" and (i % args.flush_every == 0):
            write_artifact(Path(args.out), make_doc(
                mode, endpoint, args, cases, results, health_before,
                health_before, round(time.time() - t_start, 3), partial=True))
        if not res["pass"]:
            print("[FAIL %2d/%d] %-4s %-18s %r -> [%s] %s"
                  % (i, len(cases), res["id"], res["category"], res["input"],
                     res["failure_class"], "; ".join(res["problems"])[:160]))
        else:
            print("[pass %2d/%d] %-4s %-18s %r"
                  % (i, len(cases), res["id"], res["category"], res["input"]))
    elapsed = round(time.time() - t_start, 3)
    health_after = ({"mode": "dry-run-instance", "per_case_fake": True}
                    if args.dry_run_instance else http_health(endpoint))

    summary_all = summarize(results, mode)
    doc = make_doc(mode, endpoint, args, cases, results, health_before, health_after,
                   elapsed, partial=False)
    out_path = Path(args.out)
    write_artifact(out_path, doc)

    print("== TRAINING EVAL (%s): %d/%d valid pass (%.1f%%), fail=%d, infra=%d, elapsed=%.1fs =="
          % (mode, summary_all["pass"], summary_all["n_valid"],
             100.0 * summary_all["pass"] / max(1, summary_all["n_valid"]),
             summary_all["fail"], summary_all["n_infra"], elapsed))
    print("failure_classes:", json.dumps(summary_all["failure_classes"], ensure_ascii=False))
    print("artifact:", out_path, "sha256:", hashlib.sha256(out_path.read_bytes()).hexdigest())

    if mode == "live" and not args.no_next:
        nxt = build_next(doc)
        nxt["source"]["sha256"] = hashlib.sha256(out_path.read_bytes()).hexdigest()
        np_ = Path(args.next)
        np_.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(np_) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(nxt, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, np_)
        print("next:", np_, "sha256:", hashlib.sha256(np_.read_bytes()).hexdigest())
        for it in nxt["items"]:
            print("  #%d %s x%d -> %s" % (it["rank"], it["failure_class"], it["count"],
                                           it["suggested_owner"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())