"""程序记忆 / 人格核心：人设、语气、边界、梗规则，独立于情景记忆。

支持版本化快照与回滚；这部分不参与遗忘衰减。
"""
from __future__ import annotations

import json
from datetime import datetime

from .db import get_meta, set_meta
from .textutil import iso, now

DEFAULT_PROFILE: dict = {
    "name": "小忆",
    "role": "运行在本地的陪伴型记忆体",
    "tone": "温和、口语化、不端着；先接住情绪，再给建议；不刷鸡汤",
    "boundaries": [
        "不假装自己是人类",
        "不说教、不评判用户的情绪",
        "不打探用户没主动说的隐私",
        "不确定的记忆要软确认，不编造共同经历",
    ],
    "memes": [],
    "user_name": None,
    "aliases": {},
    "reply_style": "短句为主，一般 2-5 句；不主动列 1234；工作模式除外",
}

CHAT_MODE = """【模式：聊天】
- 允许模糊、重构和情绪化表达，像老朋友。
- 记忆只在自然相关时提起，不要逐条复述卡片。
- 不确定的旧事用「我记得……对吗？」这类软确认。
- 除非对方刚打招呼，不要每轮都以「你好」开头；直接接话。
- 用户只是分享近况或心情时，接住就好，不要给方案、清单或项目建议；只有对方明确问「怎么办」才展开。
- 聊天回复控制在 2-4 句，宁短勿长。"""

WORK_MODE = """【模式：工作】
- 更精确、更结构化、更克制；必要时用短列表。
- 结论若依赖记忆或推测，标注「待确认」，不要直接当成事实。
- 不把工作模式里的推断写成人格或长期事实。"""

MEMORY_RULES = """【记忆规则】
- 下面若给出「回忆起」的片段，它们来自长期记忆，可能模糊或有冲突；优先相信用户当前的话。
- 不要暴露数据库、索引、分数这些内部细节。
- 用户纠正你时，先接受，再自然改口。"""


class Persona:
    def __init__(self, conn) -> None:
        self.conn = conn
        self.profile: dict = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        rows = self.conn.execute("SELECT key, value FROM procedural_profile").fetchall()
        data = dict(DEFAULT_PROFILE)
        for r in rows:
            try:
                data[r["key"]] = json.loads(r["value"])
            except Exception:
                data[r["key"]] = r["value"]
        # 补齐新增的默认键
        for k, v in DEFAULT_PROFILE.items():
            data.setdefault(k, v)
        self.profile = data

    def get(self, key: str, default=None):
        return self.profile.get(key, default)

    def set(self, key: str, value) -> None:
        self.profile[key] = value
        row = self.conn.execute(
            "SELECT version FROM procedural_profile WHERE key=?", (key,)
        ).fetchone()
        version = int(row["version"]) + 1 if row else 1
        self.conn.execute(
            "INSERT INTO procedural_profile(key, value, version, updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, version=excluded.version, "
            "updated_at=excluded.updated_at",
            (key, json.dumps(value, ensure_ascii=False), version, iso(now())),
        )

    # ------------------------------------------------------------------
    def digest(self) -> str:
        name = self.profile.get("name") or "小忆"
        tone = self.profile.get("tone") or ""
        user_name = self.profile.get("user_name")
        memes = self.profile.get("memes") or []
        lines = [f"你叫{name}。{tone}"]
        if user_name:
            lines.append(f"用户希望被叫「{user_name}」。")
        if memes:
            lines.append("你们之间的梗/称呼：" + "、".join(map(str, memes[:8])) + "。")
        return "\n".join(lines)

    def system_prompt(self, mode: str = "chat") -> str:
        name = self.profile.get("name") or "小忆"
        role = self.profile.get("role") or ""
        boundaries = self.profile.get("boundaries") or []
        style = self.profile.get("reply_style") or ""
        parts = [
            f"你是{name}，{role}。你运行在用户自己的电脑上，数据不出本机。",
            f"语气：{self.profile.get('tone', '')}",
            "边界：\n" + "\n".join(f"- {b}" for b in boundaries),
        ]
        if style:
            parts.append(f"表达：{style}")
        user_name = self.profile.get("user_name")
        if user_name:
            parts.append(
                f"用户的名字是{user_name}。记住：你叫{name}，不要用{user_name}自称，"
                f"也不要把用户的名字当成你的名字。"
            )
        parts.append(CHAT_MODE if mode == "chat" else WORK_MODE)
        parts.append(MEMORY_RULES)
        parts.append(
            "【输出要求】只回 2-4 句口语，直接接话；不要列 1234、不要写小标题、"
            "不要给项目方案。只有用户明确问「怎么办/帮我分析」时才展开。"
        )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    def snapshot(self, note: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO persona_snapshot(profile_json, created_at, note) VALUES(?,?,?)",
            (json.dumps(self.profile, ensure_ascii=False), iso(now()), note),
        )
        self.conn.execute(
            "INSERT INTO memory_event(ts, kind, detail) VALUES(?,?,?)",
            (iso(now()), "persona", f"snapshot {cur.lastrowid}: {note}"),
        )
        return int(cur.lastrowid)

    def list_snapshots(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT snapshot_id, created_at, note FROM persona_snapshot "
            "ORDER BY snapshot_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def rollback(self, snapshot_id: int) -> bool:
        row = self.conn.execute(
            "SELECT profile_json FROM persona_snapshot WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if not row:
            return False
        data = json.loads(row["profile_json"])
        self.profile = dict(data)
        self.conn.execute("DELETE FROM procedural_profile")
        for k, v in data.items():
            self.conn.execute(
                "INSERT INTO procedural_profile(key, value, version, updated_at) VALUES(?,?,?,?)",
                (k, json.dumps(v, ensure_ascii=False), 1, iso(now())),
            )
        self.conn.execute(
            "INSERT INTO memory_event(ts, kind, detail) VALUES(?,?,?)",
            (iso(now()), "persona", f"rollback to {snapshot_id}"),
        )
        return True

    # ------------------------------------------------------------------
    def known_people(self) -> dict[str, str]:
        people = dict(self.profile.get("aliases") or {})
        user_name = self.profile.get("user_name")
        if user_name:
            people[user_name] = user_name
        return {str(k): str(v) for k, v in people.items()}

    def display_user(self) -> str:
        return self.profile.get("user_name") or "你"