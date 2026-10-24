"""遗忘曲线：低权重记忆随时间衰减，长期不用则归档；程序记忆豁免。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .config import Settings
from .store import Store
from .textutil import iso, now, parse_iso


@dataclass
class DecayReport:
    considered: int = 0
    decayed: int = 0
    archived: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return f"遗忘：检查 {self.considered}，衰减 {self.decayed}，归档 {self.archived}"


class ForgettingCurve:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.s = settings

    def half_life_days(self, *, salience: float, emotion: float, access: int,
                       kind: str) -> float:
        base = self.s.forgetting_half_life_days
        factor = (0.55 + salience * 0.7 + emotion * 0.6 + min(access, 8) * 0.12)
        if kind == "semantic":
            factor *= 1.5          # 语义事实比情景细节更稳
        elif kind == "relational":
            factor *= 1.8          # 关系变化最稳
        return max(1.0, base * factor)

    def tick(self, *, now_dt: datetime | None = None,
             dry_run: bool = False) -> DecayReport:
        now_dt = now_dt or now()
        report = DecayReport()
        for card in self.store.active_cards():
            if card.kind == "procedural":
                continue
            report.considered += 1
            last = parse_iso(card.strength_updated_at) or parse_iso(card.created_at) or now_dt
            days = max(0.0, (now_dt - last).total_seconds() / 86400.0)
            if days < 0.02:
                continue
            half = self.half_life_days(salience=card.salience, emotion=card.emotion_weight,
                                       access=card.access_count, kind=card.kind)
            strength = card.strength * (0.5 ** (days / half))
            created = parse_iso(card.created_at) or now_dt
            age = max(0.0, (now_dt - created).total_seconds() / 86400.0)
            if not dry_run:
                self.store.update_card(card.id, strength=round(strength, 4),
                                       strength_updated_at=iso(now_dt))
            report.decayed += 1
            if (strength < self.s.archive_strength and age >= self.s.archive_grace_days
                    and card.status == "active"):
                if not dry_run:
                    self.store.archive(card.id, reason=f"strength={strength:.3f}, age={age:.0f}d")
                report.archived += 1
        return report

    def preview(self, limit: int = 10) -> list[tuple[int, float, str]]:
        """不落库地预览哪些记忆最接近被遗忘。"""
        now_dt = now()
        out = []
        for card in self.store.active_cards(limit=2000):
            last = parse_iso(card.strength_updated_at) or now_dt
            days = max(0.0, (now_dt - last).total_seconds() / 86400.0)
            half = self.half_life_days(salience=card.salience, emotion=card.emotion_weight,
                                       access=card.access_count, kind=card.kind)
            s = card.strength * (0.5 ** (days / half))
            out.append((card.id, round(s, 3), card.summary or card.text[:40]))
        out.sort(key=lambda x: x[1])
        return out[:limit]