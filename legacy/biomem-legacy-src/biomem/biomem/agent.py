"""智能体主循环：感觉缓冲 → 工作记忆 → 元记忆 → 多路召回 → 装配 → 推理
→ 写入门控 → 巩固 → 遗忘。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .config import Settings
from .consolidator import Consolidator, ConsolidationReport
from .context import ContextAssembler
from .db import connect, init_db
from .entities import Extraction, extract
from .forgetting import DecayReport, ForgettingCurve
from .indexes import IndexRouter, Recalled, RecallTrace
from .llm import BaseLLM, LLMError, build_llm
from .metamemory import Decision, Metamemory
from .persona import Persona
from .store import Card, Store
from .textutil import iso, normalize, now
from .working_memory import WorkingMemory, WorkingState
from .writegate import Candidate, GateResult, WriteGate


@dataclass
class TurnResult:
    reply: str
    session_id: str
    turn_idx: int
    mode: str
    cards: list[Recalled] = field(default_factory=list)
    trace: RecallTrace | None = None
    gate: GateResult | None = None
    decision: Decision | None = None
    written: list[int] = field(default_factory=list)
    latency_ms: float = 0.0
    messages: list[dict] = field(default_factory=list)


class Agent:
    def __init__(self, settings: Settings, *, llm: BaseLLM | None = None,
                 session_id: str | None = None) -> None:
        self.s = settings
        self.conn = connect(settings.db_path)
        init_db(self.conn)
        self.store = Store(self.conn, settings)
        self.persona = Persona(self.conn)
        self.router = IndexRouter(self.store, settings)
        self.metamemory = Metamemory(settings.recall_threshold)
        self.gate = WriteGate(settings)
        self.llm = llm or build_llm(settings)
        self.consolidator = Consolidator(self.store, settings, self.persona, self.llm)
        self.forgetting = ForgettingCurve(self.store, settings)
        self.assembler = ContextAssembler(settings)
        self.wm = WorkingMemory(self.store, settings.recent_turns)

        self.session_id = session_id or self._new_session_id()
        self.mode = "chat"
        self.store.ensure_session(self.session_id, self.mode)
        self._turns_since_consolidate = 0
        self._decay_counter = 0
        self.last_trace: RecallTrace | None = None
        self.last_gate: GateResult | None = None
        self._last_activity = time.monotonic()
        self._idle_timer: threading.Timer | None = None
        self._bg_lock = threading.Lock()

    # ------------------------------------------------------------------
    @staticmethod
    def _new_session_id() -> str:
        return "s-" + now().strftime("%Y%m%d-%H%M%S")

    def new_session(self, mode: str | None = None) -> str:
        self.session_id = self._new_session_id()
        self.mode = mode or self.mode
        self.store.ensure_session(self.session_id, self.mode)
        self.wm.reset()
        self._turns_since_consolidate = 0
        return self.session_id

    def set_mode(self, mode: str) -> None:
        if mode not in ("chat", "work"):
            raise ValueError("mode 只能是 chat 或 work")
        self.mode = mode
        self.store.set_session_mode(self.session_id, mode)

    # ------------------------------------------------------------------
    def turn(self, text: str, *, stream_cb: Callable[[str], None] | None = None) -> TurnResult:
        started = time.perf_counter()
        self._last_activity = time.monotonic()
        text = normalize(text)
        if not text:
            raise ValueError("输入为空")

        turn_idx = self.store.next_turn(self.session_id)
        extraction = extract(text, known_people=self.persona.known_people())
        user_utt = self.store.add_utterance(
            self.session_id, turn_idx, "user", text, extraction.emotion)
        self.store.index_utterance(user_utt, extraction.mentions)

        has_history = self.store.count_utterances(self.session_id) > 1
        decision = self.metamemory.decide(text, has_history=has_history)

        cards: list[Recalled] = []
        trace = RecallTrace(query=text)
        if decision.needs_recall:
            cards, trace = self.router.recall(
                text,
                emotion=extraction.emotion,
                mentions=extraction.mentions,
                topics=extraction.topics,
                exclude=set(),
            )
            if cards:
                self.store.touch([c.card.id for c in cards])
                self.store.add_event("recall", None,
                                     f"{[c.card.id for c in cards]}")
        self.last_trace = trace

        state = self.wm.begin_turn(
            self.session_id, text, extraction, cards, self.persona.digest())
        messages = self.assembler.build(
            system_prompt=self.persona.system_prompt(self.mode),
            state=state,
            user_text=text,
        )

        temperature = (self.s.temperature_chat if self.mode == "chat"
                       else self.s.temperature_work)
        max_tokens = self.s.chat_max_tokens if self.mode == "chat" else self.s.max_tokens
        stop = list(self.s.chat_stop) if self.mode == "chat" else None
        if stream_cb is not None:
            parts: list[str] = []
            for chunk in self.llm.stream(messages, temperature=temperature,
                                         max_tokens=max_tokens, stop=stop):
                parts.append(chunk)
                stream_cb(chunk)
            reply = "".join(parts).strip()
        else:
            reply = self.llm.chat(messages, temperature=temperature,
                                  max_tokens=max_tokens, stop=stop).strip()
        if not reply:
            reply = "……"

        self.store.add_utterance(self.session_id, turn_idx, "assistant", reply,
                                 emotion=round(extraction.emotion * 0.5, 3))

        gate = self.gate.evaluate(text, extraction=extraction, utterance_id=user_utt)
        self.last_gate = gate
        written: list[int] = []
        if gate.write:
            written = self._write_candidates(gate.candidates, user_utt)

        self._turns_since_consolidate += 1
        if self._turns_since_consolidate >= self.s.consolidate_every_turns:
            self._turns_since_consolidate = 0
            try:
                self.consolidate(use_llm=False)
            except Exception:
                pass

        self._decay_counter += 1
        if self._decay_counter >= 10:
            self._decay_counter = 0
            try:
                self.forgetting.tick()
            except Exception:
                pass

        latency = (time.perf_counter() - started) * 1000
        return TurnResult(
            reply=reply,
            session_id=self.session_id,
            turn_idx=turn_idx,
            mode=self.mode,
            cards=cards,
            trace=trace,
            gate=gate,
            decision=decision,
            written=written,
            latency_ms=round(latency, 1),
            messages=messages,
        )

    # ------------------------------------------------------------------
    def _write_candidates(self, candidates: list[Candidate], user_utt: int) -> list[int]:
        ids: list[int] = []
        for cand in candidates:
            meta = dict(cand.meta)
            meta["correction"] = cand.correction

            # 同一事实反复提及：不重复建卡，改为强化 + 补来源
            same = self._same_fact(meta)
            if same is not None:
                self.store.conn.execute(
                    "INSERT OR IGNORE INTO card_provenance(card_id, utterance_id) VALUES(?,?)",
                    (same.id, user_utt),
                )
                self.store.touch([same.id], delta=0.06)
                self.store.add_event("reinforce", same.id, "重复提及")
                continue

            ex = extract(cand.text, known_people=self.persona.known_people())
            cid = self.store.add_card(
                text=cand.text,
                kind=cand.kind,
                source=cand.source,
                confidence=cand.confidence,
                emotion=cand.emotion,
                salience=cand.salience,
                summary=cand.meta.get("fact") or cand.text[:80],
                session_id=self.session_id,
                meta=meta,
                utterance_ids=[user_utt],
                mentions=ex.mentions,
            )
            self.store.add_event("write", cid, cand.rationale)
            ids.append(cid)

            if cand.correction:
                self._supersede_conflicting(cid, meta)

            if meta.get("predicate") == "名字" and meta.get("object"):
                self.persona.set("user_name", meta["object"])
                aliases = dict(self.persona.get("aliases") or {})
                aliases[meta["object"]] = meta["object"]
                self.persona.set("aliases", aliases)

        return ids

    def _same_fact(self, meta: dict):
        pred = meta.get("predicate")
        obj = meta.get("object")
        if not pred or not obj or meta.get("correction"):
            return None
        for card in self.store.list_cards(status="active", limit=200):
            if card.kind not in ("semantic", "relational"):
                continue
            m = card.meta
            if (m.get("predicate") == pred and m.get("object") == obj
                    and m.get("subject", "用户") == meta.get("subject", "用户")):
                return card
        return None

    def _supersede_conflicting(self, new_id: int, meta: dict) -> None:
        pred = meta.get("predicate")
        obj = meta.get("object")
        if not pred:
            return
        for card in self.store.list_cards(status="active", limit=200):
            if card.id == new_id or card.kind not in ("semantic", "relational"):
                continue
            m = card.meta
            if m.get("predicate") == pred and m.get("object") and m.get("object") != obj:
                self.store.update_card(card.id, status="superseded",
                                       supersedes_id=new_id, updated_at=iso(now()))
                self.store.add_event("conflict", card.id,
                                     f"用户纠正 {pred}: {m.get('object')} -> {obj}")

    # ------------------------------------------------------------------
    def consolidate(self, *, force: bool = True, use_llm: bool = False,
                    session_id: str | None = None) -> ConsolidationReport:
        return self.consolidator.run(session_id=session_id, force=force, use_llm=use_llm)

    def decay(self) -> DecayReport:
        return self.forgetting.tick()

    def remember(self, text: str, *, note: str = "") -> int:
        """手动写入一条长期记忆（绕过门控）。"""
        text = normalize(text)
        ex = extract(text, known_people=self.persona.known_people())
        recent = self.store.recent_utterances(self.session_id, 1)
        utt_ids = [recent[0]["id"]] if recent else []
        cid = self.store.add_card(
            text=text, kind="episodic", source="user", confidence=0.95,
            emotion=max(0.2, ex.emotion), salience=0.9,
            session_id=self.session_id,
            summary=note or text[:80],
            meta={"manual": True, "fact": note or text[:80]},
            utterance_ids=utt_ids,
            mentions=ex.mentions,
        )
        self.store.add_event("write", cid, "manual remember")
        return cid

    def forget(self, card_id: int) -> bool:
        card = self.store.get_card(card_id)
        if not card:
            return False
        self.store.archive(card_id, reason="user forget")
        return True

    def recall_debug(self, query: str) -> tuple[list[Recalled], RecallTrace]:
        ex = extract(query, known_people=self.persona.known_people())
        return self.router.recall(query, emotion=ex.emotion, mentions=ex.mentions,
                                  topics=ex.topics)

    # ------------------------------------------------------------------
    # 空闲巩固（睡眠）：用户停手一段时间后，在后台线程里用独立连接跑巩固
    # ------------------------------------------------------------------
    def schedule_idle_consolidation(self, delay: float | None = None) -> None:
        self.cancel_idle_consolidation()
        delay = self.s.idle_consolidate_seconds if delay is None else max(5.0, delay)
        timer = threading.Timer(delay, self._idle_consolidate, args=(delay,))
        timer.daemon = True
        self._idle_timer = timer
        timer.start()

    def cancel_idle_consolidation(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

    def _idle_consolidate(self, delay: float) -> None:
        if time.monotonic() - self._last_activity < delay * 0.9:
            return
        if not self._bg_lock.acquire(blocking=False):
            return
        try:
            conn = connect(self.s.db_path)
            try:
                store = Store(conn, self.s)
                persona = Persona(conn)
                Consolidator(store, self.s, persona, None).run(use_llm=False)
            finally:
                conn.close()
        except Exception:
            pass
        finally:
            self._bg_lock.release()

    # ------------------------------------------------------------------
    def stats(self) -> dict:
        healthy, health_msg = self.llm.health()
        data = self.store.stats()
        data.update({
            "session": self.session_id,
            "mode": self.mode,
            "llm": self.llm.name,
            "llm_healthy": healthy,
            "llm_status": health_msg,
            "db_path": str(self.s.db_path),
            "persona_name": self.persona.get("name"),
            "user_name": self.persona.get("user_name"),
        })
        return data

    def snapshot_persona(self, note: str = "") -> int:
        return self.persona.snapshot(note)

    def close(self) -> None:
        self.cancel_idle_consolidation()
        try:
            self.conn.close()
        except Exception:
            pass