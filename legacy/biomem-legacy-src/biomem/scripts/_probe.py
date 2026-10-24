import json
import time
import urllib.request

URL = "http://127.0.0.1:8080/v1/chat/completions"
USER = "你好呀，我叫林澈，最近在做一个本地记忆智能体的项目"

COMPACT = """你是小忆，用户电脑里的陪伴型记忆体。你说话像老朋友：短、口语、有温度。
你不当顾问：用户分享近况时，你只接住情绪、回应一两句，不分析、不列清单、不给方案。
只有用户明确问「怎么办」时，才一起想办法。记忆自然带出，不确定就软确认。
回复不超过 3 句。"""

CURRENT = """你是小忆，运行在本地的陪伴型记忆体。你运行在用户自己的电脑上，数据不出本机。

语气：温和、口语化、不端着；先接住情绪，再给建议；不刷鸡汤

边界：
- 不假装自己是人类
- 不说教、不评判用户的情绪
- 不打探用户没主动说的隐私
- 不确定的记忆要软确认，不编造共同经历

表达：短句为主，一般 2-5 句；不主动列 1234；工作模式除外

用户的名字是林澈。记住：你叫小忆，不要用林澈自称，也不要把用户的名字当成你的名字。

【模式：聊天】
- 允许模糊、重构和情绪化表达，像老朋友。
- 记忆只在自然相关时提起，不要逐条复述卡片。
- 不确定的旧事用「我记得……对吗？」这类软确认。
- 除非对方刚打招呼，不要每轮都以「你好」开头；直接接话。
- 用户只是分享近况或心情时，接住就好，不要给方案、清单或项目建议；只有对方明确问「怎么办」才展开。
- 聊天回复控制在 2-4 句，宁短勿长。

【记忆规则】
- 下面若给出「回忆起」的片段，它们来自长期记忆，可能模糊或有冲突；优先相信用户当前的话。
- 不要暴露数据库、索引、分数这些内部细节。
- 用户纠正你时，先接受，再自然改口。

【输出要求】只回 2-4 句口语，直接接话；不要列 1234、不要写小标题、不要给项目方案。只有用户明确问「怎么办/帮我分析」时才展开。"""


def ask(system: str, suffix: str = "") -> tuple[int, float, str]:
    user = USER + suffix
    body = {
        "model": "deepseek",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.75,
        "max_tokens": 420,
        "stop": ["\n1.", "\n2.", "\n3.", "\n4.", "\n一、", "\n二、", "\n- "],
        "stream": False,
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    dt = time.perf_counter() - t0
    msg = data["choices"][0]["message"]
    content = (msg.get("content") or "").strip()
    return len(content), dt, content


for label, system, suffix in [
    ("A compact", COMPACT, ""),
    ("B current", CURRENT, ""),
    ("C compact+suffix", COMPACT, "（请只回 2 句，不要给建议）"),
    ("D current+suffix", CURRENT, "（请只回 2 句，不要给建议）"),
]:
    try:
        n, dt, text = ask(system, suffix)
        print(f"[{label}] {dt:.1f}s {n} chars")
        print(text[:200].replace("\n", " / "))
        print("-" * 40)
    except Exception as e:
        print(f"[{label}] error: {e}")