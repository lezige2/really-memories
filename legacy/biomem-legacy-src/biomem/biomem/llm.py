"""推理后端：llama.cpp（OpenAI 兼容）/ 离线 Mock。

只依赖标准库 urllib；流式走 SSE。
DeepSeek-R1 蒸馏模型会输出  thinking...，这里做增量过滤，不把思考过程显示给用户。
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Iterable, Iterator

from .config import Settings


class LLMError(RuntimeError):
    pass


def strip_think(text: str) -> str:
    text = re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", text, flags=re.S | re.I)
    # reasoning-budget=0 时模板只留下一个孤立的结束标记
    text = re.sub(r"^\s*</think(?:ing)?>\s*", "", text, flags=re.I)
    text = re.sub(r"</think(?:ing)?>", "", text, flags=re.I)
    return text.strip()


class ThinkFilter:
    """把流式输出里的 think 段落过滤掉，同时容忍标记被切碎。"""

    def __init__(self, holdback: int = 16) -> None:
        self.buf = ""
        self.holdback = holdback
        self.in_think = False
        self.decided = False
        self.started = False

    def feed(self, chunk: str) -> str:
        self.buf += chunk
        out: list[str] = []
        while True:
            if not self.decided:
                probe = self.buf.lstrip()
                stripped = self.buf[: len(self.buf) - len(probe)]
                low = probe.lower()
                if low.startswith("<think>") or low.startswith("<thinking>"):
                    self.decided = True
                    self.in_think = True
                    end = probe.find(">")
                    if end < 0:
                        return ""
                    self.buf = stripped + probe[end + 1:]
                    continue
                if any(("<think".startswith(low[:n]) or "<thinking>".startswith(low[:n]))
                       for n in range(1, min(len(low), 10) + 1)) and len(low) < 10:
                    return "".join(out)  # 还看不出是不是 think，先等
                self.decided = True
                self.in_think = False
                continue
            if self.in_think:
                low = self.buf.lower()
                idx = low.find("")
                tag_len = len("")
                if idx < 0:
                    idx = low.find("</thinking>")
                    tag_len = len("</thinking>")
                if idx >= 0:
                    self.buf = self.buf[idx + tag_len:]
                    self.in_think = False
                    self.decided = True
                    continue
                # 保留结尾几个字符，防止标记被切断
                if len(self.buf) > self.holdback:
                    self.buf = self.buf[-self.holdback:]
                return "".join(out)
            piece = self.buf
            self.buf = ""
            if not self.started:
                piece = piece.lstrip()
                if piece:
                    self.started = True
            out.append(piece)
            return "".join(out)

    def flush(self) -> str:
        rest = "" if self.in_think else self.buf
        self.buf = ""
        if not self.started:
            rest = rest.lstrip()
        return rest


class BaseLLM:
    name = "base"

    def chat(self, messages: list[dict], *, temperature: float = 0.7,
             max_tokens: int = 512, stop: list[str] | None = None) -> str:
        raise NotImplementedError

    def stream(self, messages: list[dict], *, temperature: float = 0.7,
               max_tokens: int = 512, stop: list[str] | None = None) -> Iterator[str]:
        yield self.chat(messages, temperature=temperature, max_tokens=max_tokens, stop=stop)

    def health(self) -> tuple[bool, str]:
        return True, "ok"

    def summarize(self, text: str) -> str:
        """给巩固阶段用的短摘要；默认截断，子类可覆盖。"""
        first = re.split(r"[。！？!?\n]", text)[0]
        return first[:80]


class LlamaCppClient(BaseLLM):
    name = "llama.cpp"

    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.base = settings.base_url.rstrip("/")
        self.model = settings.model
        self.key = settings.api_key

    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    def health(self) -> tuple[bool, str]:
        url = f"{self.base}/models"
        try:
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            name = (data.get("data") or [{}])[0].get("id", "?")
            return True, f"已连接 {self.base}（{name}）"
        except Exception as e:  # noqa: BLE001
            return False, f"连不上 {self.base}：{e}"

    def _payload(self, messages: list[dict], temperature: float, max_tokens: int,
                 stream: bool, stop: list[str] | None = None) -> bytes:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if stop:
            body["stop"] = list(stop)
        return json.dumps(body, ensure_ascii=False).encode("utf-8")

    def _request(self, messages: list[dict], temperature: float, max_tokens: int,
                 stream: bool, stop: list[str] | None = None) -> dict:
        url = f"{self.base}/chat/completions"
        req = urllib.request.Request(
            url,
            data=self._payload(messages, temperature, max_tokens, stream, stop),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.s.request_timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise LLMError(f"推理服务返回 {e.code}：{detail}") from e
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"推理请求失败：{e}") from e

    def chat(self, messages: list[dict], *, temperature: float = 0.7,
             max_tokens: int = 512, stop: list[str] | None = None) -> str:
        data = self._request(messages, temperature, max_tokens, False, stop)
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"无法解析推理响应：{str(data)[:300]}") from e
        content = strip_think(msg.get("content") or "").strip()
        if not content and (msg.get("reasoning_content") or "").strip():
            # 思考把预算吃光了：加一倍预算再试一次（R1 蒸馏模型常见）
            data = self._request(messages, temperature, max_tokens * 2, False, stop)
            try:
                msg = data["choices"][0]["message"]
            except (KeyError, IndexError) as e:
                raise LLMError(f"无法解析推理响应：{str(data)[:300]}") from e
            content = strip_think(msg.get("content") or "").strip()
        return content

    def stream(self, messages: list[dict], *, temperature: float = 0.7,
               max_tokens: int = 512, stop: list[str] | None = None) -> Iterator[str]:
        url = f"{self.base}/chat/completions"
        req = urllib.request.Request(
            url,
            data=self._payload(messages, temperature, max_tokens, True, stop),
            headers=self._headers(),
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=self.s.request_timeout)
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"推理请求失败：{e}") from e
        filt = ThinkFilter()
        got_content = False
        with resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    got_content = True
                    visible = filt.feed(piece)
                    if visible:
                        yield visible
        tail = filt.flush()
        if tail:
            yield tail
        if not got_content:
            # 流式里全是思考、没有正文：退回非流式并加大预算
            reply = self.chat(messages, temperature=temperature, max_tokens=max_tokens * 2)
            if reply:
                yield reply

    def summarize(self, text: str) -> str:
        prompt = (
            "把下面这段对话压成一句中文记忆卡片，保留人物、事件、时间、情绪，"
            "不超过60字，不要解释：\n\n" + text[:4000]
        )
        try:
            out = self.chat([{"role": "user", "content": prompt}],
                            temperature=0.2, max_tokens=96)
            return out.strip().splitlines()[0][:120] or super().summarize(text)
        except LLMError:
            return super().summarize(text)


class MockClient(BaseLLM):
    """离线演示/测试用：不联网，根据上下文给出可预期的回复。"""

    name = "mock"

    def chat(self, messages: list[dict], *, temperature: float = 0.7,
             max_tokens: int = 512, stop: list[str] | None = None) -> str:
        user = ""
        memory: list[str] = []
        mode = "chat"
        for m in messages:
            content = m.get("content") or ""
            if m.get("role") == "user":
                user = content
            if "【回忆起" in content:
                memory = [ln.strip("- ").strip() for ln in content.splitlines()
                          if ln.strip().startswith("- ")]
            if "【模式：工作】" in content:
                mode = "work"
        # 挑与当前输入重合度最高的一条记忆，让离线演示也像“想起来了”
        best = None
        if memory:
            from .textutil import tokenize
            utoks = set(tokenize(user))
            best = max(memory, key=lambda line: len(utoks & set(tokenize(line))))
        if mode == "work":
            body = "（离线演示·工作模式）收到。" + (f"先前记忆：{best}。" if best else "")
            return body + "请补充目标与约束，我会按步骤给建议（结论待确认）。"
        if best:
            return (f"（离线演示）我还记得：{best}\n"
                    f"你刚说「{user[:40]}」，我接住了。")
        return f"（离线演示）嗯，我在听。你刚说「{user[:40]}」。"

    def summarize(self, text: str) -> str:
        return re.split(r"[。！？!?\n]", text)[0][:60]


def build_llm(settings: Settings) -> BaseLLM:
    if settings.mock:
        return MockClient()
    return LlamaCppClient(settings)