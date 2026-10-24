#!/usr/bin/env python3
"""
kvmem_test.py -- 验证「记忆住在 KV 里」这一核心机制（M1 的最小可行性实验）

原理：
  llama.cpp 的 KV cache 是 (K, V) 张量，与位置一一绑定。
  upstream 已经提供 llama_state_seq_get_data / set_data（server 侧即 /slots 的 save/restore），
  可以把某个 sequence 的 KV 整块存盘、清空上下文、再恢复进一个新会话。
  恢复后 n_past 回到记忆长度，新 token 从记忆之后的位置继续，
  而因果掩码 (p0 <= p1) 让新 token 自动看见全部记忆位置 —— 记忆不需要出现在 prompt 里。

本脚本做四件事：
  1. 对照组：新上下文里直接问问题（信息不在上下文，应当答不出）
  2. 写入：把记忆文本喂进上下文，n_predict=1，只做 prefill
  3. 存盘 + 清空 + 恢复：K-V 走磁盘，上下文被清空过一次
  4. 实验组：prompt 里只有问题，看模型能否答出记忆里的内容

用法：python kvmem_test.py [--url http://127.0.0.1:8080] [--slot 0] [--file memtest.bin]
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 记忆内容：模型不可能知道的人造事实
MEMORY = """以下是用户陈默的档案资料。
姓名：陈默
生日：1993年4月17日
住址：杭州市西湖区文三路88号3幢502室
车牌尾号：7302
宠物：一只叫豆豆的橘猫
最喜欢的城市：里斯本
"""

QUESTION = "用户陈默的车牌尾号是多少？只回答四位数字："

ANSWER_KEY = "7302"


def post_json(base, path, payload, timeout=600):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get_json(base, path, timeout=120):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        body = r.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_raw": body}


def slot_action(base, slot, action, filename=None, timeout=300):
    """调用 /slots/{id}?action=... ；POST 不被接受时回退 GET。"""
    q = {"action": action}
    if filename:
        q["filename"] = filename
    path = "/slots/%d?%s" % (slot, urllib.parse.urlencode(q))

    last_err = None
    for method in ("POST", "GET"):
        try:
            req = urllib.request.Request(base + path, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            return body.strip() or "(ok)"
        except urllib.error.HTTPError as e:
            last_err = "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:200])
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)
    return "失败 -> " + str(last_err)


def n_past_of(base, slot):
    try:
        slots = get_json(base, "/slots")
    except Exception as e:  # noqa: BLE001
        return "取不到 (%r)" % (e,)
    if isinstance(slots, list) and len(slots) > slot:
        s = slots[slot]
        return s.get("n_past", s.get("n_ctx", "?"))
    return "?"


def ask(base, prompt, n_predict):
    r = post_json(base, "/completion", {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.0,
        "top_k": 1,
        "cache_prompt": False,
        "stream": False,
    })
    return (r.get("content") or "").strip(), r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--slot", type=int, default=0)
    ap.add_argument("--file", default="memtest.bin")
    args = ap.parse_args()
    base = args.url.rstrip("/")

    print("=" * 66)
    print("KV 记忆实验   服务端:", base, " slot:", args.slot)
    print("=" * 66)

    # ---------- 1. 对照组：上下文里没有记忆 ----------
    print("\n[1] 对照组：全新上下文，直接问（信息不在 prompt 里）")
    print("    prompt =", repr(QUESTION))
    a1, _ = ask(base, QUESTION, 24)
    print("    回答 =", repr(a1))
    ok1 = ANSWER_KEY in a1
    print("    命中期望答案 %s ? %s" % (ANSWER_KEY, ok1))

    # ---------- 2. 写入记忆：只做 prefill ----------
    print("\n[2] 写入记忆：把档案喂进上下文（n_predict=1，只要 KV）")
    slot_action(base, args.slot, "erase")
    _, r2 = ask(base, MEMORY, 1)
    print("    处理 token 数 =", r2.get("tokens_evaluated", "?"))
    print("    当前 n_past =", n_past_of(base, args.slot))

    # ---------- 3. 存盘 -> 清空 -> 恢复 ----------
    print("\n[3] KV 落盘 -> 清空上下文 -> 从磁盘恢复")
    print("    save :", slot_action(base, args.slot, "save", args.file))
    print("    erase:", slot_action(base, args.slot, "erase"))
    print("    清空后 n_past =", n_past_of(base, args.slot))
    print("    restore:", slot_action(base, args.slot, "restore", args.file))
    restored = n_past_of(base, args.slot)
    print("    恢复后 n_past =", restored)

    # ---------- 4. 实验组：prompt 只有问题 ----------
    print("\n[4] 实验组：prompt 里【只有问题】，没有任何记忆文本")
    print("    prompt =", repr(QUESTION))
    a2, r4 = ask(base, QUESTION, 24)
    print("    回答 =", repr(a2))
    ok2 = ANSWER_KEY in a2

    print("\n" + "=" * 66)
    print("结论")
    print("  对照组答出 %s : %s" % (ANSWER_KEY, "是 (实验无效!)" if ok1 else "否 (符合预期)"))
    print("  实验组答出 %s : %s" % (ANSWER_KEY, "是" if ok2 else "否"))
    if ok2 and not ok1:
        print("  => 通过：答案只能来自 KV 中的记忆，prompt 里没有该信息。")
        rc = 0
    elif ok1:
        print("  => 无效：对照组也答对了，问题本身可能泄露了答案。")
        rc = 2
    else:
        print("  => 未通过：记忆没有生效，需要检查 restore / 位置 / 掩码。")
        rc = 1
    print("=" * 66)
    return rc


if __name__ == "__main__":
    sys.exit(main())