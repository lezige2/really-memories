"""端到端测试：不依赖真实模型，用 MockClient 验证记忆回路。

运行：python -m unittest discover -s tests -v
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from biomem.agent import Agent
from biomem.config import Settings
from biomem.llm import MockClient
from biomem.textutil import now


_AGENTS: list[Agent] = []


def make_agent() -> Agent:
    data = Path(tempfile.mkdtemp(prefix="biomem-test-"))
    settings = Settings.load(data_dir=data)
    settings.mock = True
    settings.consolidate_every_turns = 100  # 测试里手动触发，避免干扰
    agent = Agent(settings, llm=MockClient())
    _AGENTS.append(agent)
    return agent


def tearDownModule() -> None:
    for agent in _AGENTS:
        agent.close()
    _AGENTS.clear()


class TestMemoryLoop(unittest.TestCase):
    def test_fact_written_and_recalled(self) -> None:
        a = make_agent()
        r1 = a.turn("我叫林澈，养了只猫叫团子，它特别爱拆家")
        self.assertTrue(r1.gate.write)
        self.assertGreaterEqual(len(r1.written), 2)
        self.assertEqual(a.persona.get("user_name"), "林澈")

        # 换一个会话，模拟过几天再来
        a.new_session()
        r2 = a.turn("你还记得我家那只猫叫什么吗？")
        self.assertTrue(r2.decision.needs_recall)
        summaries = [c.card.summary or c.card.text for c in r2.cards]
        self.assertTrue(any("团子" in s for s in summaries), summaries)
        self.assertIn("团子", r2.reply)

    def test_metamemory_smalltalk_no_recall(self) -> None:
        a = make_agent()
        a.turn("我叫林澈")
        a.new_session()
        r = a.turn("你好")
        self.assertFalse(r.decision.needs_recall)
        self.assertEqual(r.cards, [])

    def test_clause_split(self) -> None:
        a = make_agent()
        a.turn("我叫林澈，养了只猫叫团子")
        texts = [c.text for c in a.store.list_cards(limit=10)]
        self.assertIn("用户的名字是林澈", texts)
        self.assertTrue(any("猫" in t for t in texts))
        self.assertNotIn("我叫林澈，养了只猫叫团子", texts)


class TestConflict(unittest.TestCase):
    def test_correction_supersedes(self) -> None:
        a = make_agent()
        a.turn("我住在北京")
        a.turn("其实我住在上海，之前说错了")
        actives = [c for c in a.store.list_cards(status="active", limit=20)
                   if c.meta.get("predicate") == "居住地"]
        self.assertEqual(len(actives), 1)
        self.assertEqual(actives[0].meta.get("object"), "上海")
        old = [c for c in a.store.list_cards(status="superseded", limit=20)
               if c.meta.get("predicate") == "居住地"]
        self.assertTrue(old)


class TestForgetting(unittest.TestCase):
    def test_low_weight_card_archived(self) -> None:
        a = make_agent()
        cid = a.remember("随口提过一句的琐事")
        past = (now() - timedelta(days=60)).isoformat(timespec="seconds")
        a.store.update_card(cid, strength=0.5, strength_updated_at=past,
                            created_at=past, salience=0.2, emotion_weight=0.0)
        report = a.decay()
        self.assertGreaterEqual(report.archived, 1)
        self.assertEqual(a.store.get_card(cid).status, "archived")

    def test_semantic_survives_longer(self) -> None:
        a = make_agent()
        cid = a.store.add_card(text="用户的名字是林澈", kind="semantic",
                               source="user", confidence=0.9, salience=0.8)
        past = (now() - timedelta(days=60)).isoformat(timespec="seconds")
        a.store.update_card(cid, strength=0.9, strength_updated_at=past,
                            created_at=past)
        a.decay()
        self.assertEqual(a.store.get_card(cid).status, "active")


class TestPersona(unittest.TestCase):
    def test_snapshot_and_rollback(self) -> None:
        a = make_agent()
        original = a.persona.get("tone")
        sid = a.persona.snapshot("before")
        a.persona.set("tone", "冷淡")
        self.assertEqual(a.persona.get("tone"), "冷淡")
        self.assertTrue(a.persona.rollback(sid))
        self.assertEqual(a.persona.get("tone"), original)


class TestConsolidation(unittest.TestCase):
    def test_windows_become_cards(self) -> None:
        a = make_agent()
        for i in range(6):
            a.turn(f"今天加班到很晚，脑袋嗡嗡的，第{i}次了，真的累")
        rep = a.consolidate(use_llm=False)
        self.assertGreaterEqual(rep.created + rep.merged, 1)
        cards = a.store.list_cards(status="active", kind="episodic", limit=20)
        self.assertTrue(cards)

    def test_duplicate_windows_merge(self) -> None:
        a = make_agent()
        text = "今天去看了海，风很大，但心里特别安静"
        a.turn(text)
        first = a.consolidate(use_llm=False)
        self.assertGreaterEqual(first.created, 1)
        a.turn(text)
        second = a.consolidate(use_llm=False)
        self.assertGreaterEqual(second.merged, 1)
        # 不应产生两张几乎一样的卡片
        cards = [c for c in a.store.list_cards(status="active", limit=20)]
        same = [c for c in cards if "看海" in c.text or "看了海" in c.text]
        self.assertLessEqual(len(same), 1, [c.text for c in same])


if __name__ == "__main__":
    unittest.main()