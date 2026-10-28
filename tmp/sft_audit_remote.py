# -*- coding: utf-8 -*-
"""Read-only audit of ~/llm-ft/data.jsonl (runs remotely via ssh stdin)."""
import json
import os
import re
import statistics
from collections import Counter, defaultdict

PATH = os.path.expanduser("~/llm-ft/data.jsonl")
rows = []
bad_json = []
with open(PATH, encoding="utf-8") as fh:
    for i, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            bad_json.append({"line": i, "error": str(exc)[:160]})

ID_Q = re.compile(r"你是谁|你叫|你是什么模型|什么模型|机器人|AI|GPT|DeepSeek|公司|本地模型|"
                  r"能做什么|会什么|能力|自我介绍|帮我做什么")
TIME_Q = re.compile(r"几点|星期几|几号|哪天|几月|昨天|明天|后天|上周|下周|这个月|下个月|月\d|号")
ACT_Q = re.compile(r"帮我.*(发|转账|删|登录|加好友|打电话|订|评论|点赞|下单|预约|拉我进群)|"
                   r"发消息|同意好友|朋友圈")
PRIV_Q = re.compile(r"密码|身份证|验证码|系统提示|训练数据|隐藏指令|监听|破解|绕过|管理员|"
                    r"别人|账号|模型文件")
MEM_SYS = "可用记忆"
REFUSE = re.compile(r"帮不了|做不了|不能|没法|不该|抱歉|无法")
UNKNOWN_ANS = re.compile(r"没法确认|没跟我说过|不知道|记不清")
BAD_CLAIM = re.compile(r"已(?:帮你|发|转|删|下单|预约)|联网(?:搜索|查询)|我可以操作|这就帮你|已经发")
STRIP = re.compile(r"[\s，。！？、；：,.!?“”\"'（）()~～]+")


def norm(s):
    return STRIP.sub("", str(s or ""))


def classify(d):
    msgs = d.get("messages") or []
    sysc = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
    user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
    ans = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
    has_mem = MEM_SYS in sysc
    time_evidence = bool(re.search(r"\d{1,2}\s*月|\d{1,2}\s*[日号]|星期[一二三四五六日天]|周[一二三四五六日天]|\d{1,2}\s*点", ans))
    if has_mem and TIME_Q.search(user) and time_evidence:
        cat = "time"
    elif has_mem:
        cat = "memory"
    elif UNKNOWN_ANS.search(ans) and not REFUSE.search(ans.replace("没法确认", "")):
        cat = "unknown"
    elif PRIV_Q.search(user):
        cat = "privacy"
    elif ID_Q.search(user):
        cat = "identity"
    elif ACT_Q.search(user) or (REFUSE.search(ans) and re.search(r"操作|应用|账号|手机|消息", ans)):
        cat = "boundary"
    elif TIME_Q.search(user):
        cat = "time"
    elif UNKNOWN_ANS.search(ans):
        cat = "unknown"
    else:
        cat = "chat"
    return cat, sysc, user, ans, has_mem


cats = Counter()
sys_variants = Counter()
role_shapes = Counter()
issues = defaultdict(list)
flags = Counter()
samples_pool = defaultdict(list)
user_q_counter = Counter()
full_norm_counter = Counter()
row_texts = []
row_cats = []
for d in rows:
    cat, sysc, user, ans, has_mem = classify(d)
    cats[cat] += 1
    row_cats.append(cat)
    msgs = d.get("messages") or []
    roles = tuple(m.get("role") for m in msgs)
    role_shapes["->".join(roles)] += 1
    sys_key = ("none" if not sysc else
               ("mem" if has_mem else "plain"))
    sys_variants[sys_key] += 1
    if not sysc:
        issues["missing_system"].append({"user": user[:60], "ans": ans[:60]})
    if not user or not ans:
        issues["empty_content"].append({"user": user[:40], "ans": ans[:40]})
    if BAD_CLAIM.search(ans):
        issues["bad_capability_claim"].append({"cat": cat, "user": user[:60], "ans": ans[:80]})
        flags["bad_claim_" + cat] += 1
    if cat == "boundary" and not REFUSE.search(ans):
        issues["boundary_no_refusal"].append({"user": user[:60], "ans": ans[:80]})
        flags["boundary_no_refusal"] += 1
    if cat == "privacy" and not REFUSE.search(ans):
        issues["privacy_no_refusal"].append({"user": user[:60], "ans": ans[:80]})
        flags["privacy_no_refusal"] += 1
    if cat == "unknown" and not UNKNOWN_ANS.search(ans):
        issues["unknown_no_refusal"].append({"user": user[:60], "ans": ans[:80]})
        flags["unknown_no_refusal"] += 1
    if re.search(r"GPT|ChatGPT|联网|云端服务", ans) and cat == "identity" \
            and not re.search(r"不是|不会|不能|没法|并非", ans):
        issues["identity_questionable"].append({"user": user[:60], "ans": ans[:80]})
        flags["identity_claim"] += 1
    user_q_counter[norm(user)] += 1
    full_key = norm(user) + "||" + norm(ans)
    full_norm_counter[full_key] += 1
    row_texts.append((cat, user, ans))
    if len(samples_pool[cat]) < 6:
        samples_pool[cat].append({"cat": cat, "user": user, "ans": ans,
                                  "has_system": bool(sysc), "has_memory": has_mem})

# duplicates
exact = Counter((json.dumps(d.get("messages"), ensure_ascii=False, sort_keys=True) for d in rows))
exact_dups = {k: v for k, v in exact.items() if v > 1}
q_dups = {k: v for k, v in user_q_counter.items() if v > 1}
pair_dups = {k: v for k, v in full_norm_counter.items() if v > 1}
# near-dup: within same normalized question, assistant normalized equality / difflib ratio
near_pairs = 0
near_examples = []
by_q = defaultdict(list)
for d in rows:
    msgs = d.get("messages") or []
    user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
    ans = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
    by_q[norm(user)].append(norm(ans))
for q, ans_list in by_q.items():
    if len(ans_list) < 2:
        continue
    uniq = list(dict.fromkeys(ans_list))
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            a, b = uniq[i], uniq[j]
            if not a or not b:
                continue
            la, lb = len(a), len(b)
            if min(la, lb) / max(la, lb) < 0.8:
                continue
            common = sum(1 for x, y in zip(a, b) if x == y)
            ratio = common / max(la, lb)
            if ratio >= 0.9:
                near_pairs += 1
                if len(near_examples) < 8:
                    near_examples.append({"q": q[:50], "a": a[:70], "b": b[:70],
                                          "ratio": round(ratio, 3)})

# chat intent/answer coherence (builder gen_chat pairs)
CHAT_MAP = {
    "你好": ["嗨，有啥事儿？"],
    "你好你好": ["嗨嗨，有啥需要帮忙的吗？"],
    "在吗": ["在呢，有啥事？"],
    "在不在": ["在的，你说。"],
    "早上好呀": ["早上好，今天想聊点啥？"],
    "嗨": ["嗨，有啥事儿？"],
    "哈喽": ["哈喽，有啥想聊的？"],
    "谢谢": ["不客气～"],
    "随便聊聊吧": ["好啊，最近有啥新鲜事儿吗？", "好啊，最近有啥想聊的？"],
    "今天天气怎么样": ["我查不到实时天气，你可以看看手机上的天气。"],
    "我有点累": ["那先歇会儿吧，有啥想聊的随时说。"],
    "我刚才说要去哪": ["你刚才说下周五要去成都开会。"],
    "我们刚才聊了什么": ["刚才聊到你下周五要去成都开会。"],
    "你还在吗": ["在的，你说。"],
}
CHAT_MAP_N = {norm(k): [norm(x) for x in v] for k, v in CHAT_MAP.items()}
chat_mismatch = []
chat_rows = 0
for d in rows:
    user = next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="user"), "")
    ans = next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="assistant"), "")
    qn = norm(user)
    if qn in CHAT_MAP_N:
        chat_rows += 1
        if norm(ans) not in CHAT_MAP_N[qn]:
            chat_mismatch.append({"user": user, "ans": ans})
# train/val overlap
val_overlap = {"val_exists": False}
try:
    vpath = os.path.expanduser("~/llm-ft/val.jsonl")
    vrows = [json.loads(x) for x in open(vpath, encoding="utf-8") if x.strip()]
    def sig(d):
        return json.dumps(d.get("messages"), ensure_ascii=False, sort_keys=True)
    tr = {sig(d) for d in rows}
    vs = {sig(d) for d in vrows}
    trq = {norm(next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="user"), "")) for d in rows}
    vq = {norm(next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="user"), "")) for d in vrows}
    val_overlap = {"val_exists": True, "val_rows": len(vrows),
                   "exact_message_overlap": len(tr & vs),
                   "exact_overlap_rate": round(len(tr & vs) / max(1, len(vs)), 4),
                   "normalized_user_overlap": len(trq & vq),
                   "question_overlap_rate": round(len(trq & vq) / max(1, len(vq)), 4)}
except Exception as exc:                      # noqa: BLE001
    val_overlap = {"val_exists": False, "error": repr(exc)[:120]}

# tokenizer / token lengths
tok_info = {"tokenizer": None, "error": None}
counts = []
try:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from transformers import AutoTokenizer
    mpath = os.path.expanduser("~/models/Qwen2.5-14B-Instruct")
    tok = AutoTokenizer.from_pretrained(mpath, trust_remote_code=True)
    tok_info["tokenizer"] = "Qwen2.5-14B-Instruct"
    for d in rows:
        msgs = d.get("messages") or []
        try:
            ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False)
            total = len(ids)
        except Exception:
            total = len(tok(str(msgs)))
        user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
        ans = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
        sysc = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
        counts.append({"total": total,
                       "user": len(tok.encode(user or "", add_special_tokens=False)),
                       "assistant": len(tok.encode(ans or "", add_special_tokens=False)),
                       "system": len(tok.encode(sysc or "", add_special_tokens=False)),
                       "chars": len(user or "") + len(ans or "") + len(sysc or "")})
    # SFTTrainer/system-template behaviour checks
    demo = rows[0]["messages"]
    plain = [m for m in demo if m.get("role") != "system"]
    t_with = tok.apply_chat_template(demo, tokenize=False, add_generation_prompt=False)
    t_plain = tok.apply_chat_template(plain, tokenize=False, add_generation_prompt=False)
    tok_info["template"] = {
        "chat_template_present": bool(tok.chat_template),
        "system_rendered": "本地记忆助手" in t_with,
        "system_in_with": "本地记忆助手" in t_with,
        "system_in_plain": "本地记忆助手" in t_plain,
        "with_preview": t_with[:220],
        "plain_preview": t_plain[:160],
    }
except Exception as exc:                      # noqa: BLE001
    tok_info["error"] = repr(exc)[:300]

def stat(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    s = sorted(vals)
    return {"n": len(vals), "mean": round(sum(vals) / len(vals), 1),
            "median": statistics.median(vals), "p90": s[int(len(s) * 0.9) - 1],
            "p95": s[int(len(s) * 0.95) - 1], "max": s[-1],
            "min": s[0]}

# char-estimated token lengths (fallback / cross-check): Chinese ~1 token/1.5 chars
char_tokens = [max(1, round(c["chars"] / 1.5)) for c in counts] if counts else []

# stratified 20 samples
sample_rows = []
idx = 0
while len(sample_rows) < 20:
    added = False
    for cat in list(samples_pool.keys()):
        items = samples_pool[cat]
        if idx < len(items) and len(sample_rows) < 20:
            if not any(x is items[idx] for x in sample_rows):
                sample_rows.append(items[idx])
            added = True
    idx += 1
    if not added:
        break
for s in sample_rows:
    msgs = None
    for d in rows:
        u = next((m.get("content", "") for m in d.get("messages") or [] if m.get("role") == "user"), "")
        if u == s["user"]:
            msgs = d["messages"]
            break
    s["system_head"] = (next((m.get("content", "") for m in msgs or [] if m.get("role") == "system"), "") or "")[:220]
    s["has_system"] = any(m.get("role") == "system" for m in msgs or [])
    s["has_memory"] = "可用记忆" in s["system_head"]
    s["messages_roles"] = [m.get("role") for m in msgs or []]

out = {
    "path": PATH,
    "total_lines": len(rows) + len(bad_json),
    "parsed_rows": len(rows),
    "bad_json": bad_json[:10],
    "category_counts": dict(cats),
    "system_variants": dict(sys_variants),
    "system_unique_count": len({next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="system"),"") for d in rows}),
    "system_time_values": dict(Counter(re.findall(r"现在时间：([^。\n]+)", next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="system"),""))[0] if re.findall(r"现在时间：([^。\n]+)", next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="system"),"")) else "none" for d in rows)),
    "unique_normalized_user_questions": len(user_q_counter),
    "unique_normalized_answers": len({norm(next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="assistant"),"")) for d in rows}),
    "top_repeated_questions": user_q_counter.most_common(8),
    "answer_chars": stat([len(next((m.get("content","") for m in d.get("messages") or [] if m.get("role")=="assistant"),"")) for d in rows]),
    "role_shapes": dict(role_shapes),
    "duplicates": {
        "exact_message_duplicate_groups": len(exact_dups),
        "exact_rows_in_dup_groups": sum(v for v in exact_dups.values()),
        "exact_duplicate_rate": round(sum(v for v in exact_dups.values()) / max(1, len(rows)), 4),
        "normalized_user+assistant_dup_groups": len(pair_dups),
        "rows_in_pair_dup_groups": sum(v for v in pair_dups.values()),
        "pair_duplicate_rate": round(sum(v for v in pair_dups.values()) / max(1, len(rows)), 4),
        "user_question_dup_groups": len(q_dups),
        "rows_with_dup_question": sum(v for v in q_dups.values()),
        "near_duplicate_pairs_ge0.9": near_pairs,
        "near_examples": near_examples,
    },
    "tokenizer": tok_info,
    "token_stats": {
        "total": stat([c["total"] for c in counts]) if counts else None,
        "user": stat([c["user"] for c in counts]) if counts else None,
        "assistant": stat([c["assistant"] for c in counts]) if counts else None,
        "system": stat([c["system"] for c in counts]) if counts else None,
        "char_estimate_mean": round(sum(char_tokens) / len(char_tokens), 1) if char_tokens else None,
        "chars": stat([c["chars"] for c in counts]) if counts else None,
    },
    "behavior": {
        "flags": dict(flags),
        "issue_counts": {k: len(v) for k, v in issues.items()},
        "issue_examples": {k: v[:5] for k, v in issues.items()},
    },
    "chat_coherence": {"chat_rows": chat_rows, "mismatch": len(chat_mismatch),
                        "mismatch_rate": round(len(chat_mismatch) / max(1, chat_rows), 4),
                        "examples": chat_mismatch[:10]},
    "val_overlap": val_overlap,
    "samples": sample_rows,
    "system_template_expected": "你是用户身边的本地记忆助手，现在时间... 可用记忆...",
}
print(json.dumps(out, ensure_ascii=False))