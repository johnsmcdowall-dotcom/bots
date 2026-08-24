"""Shared types every strategy (horse racing or football) must produce.

These are the contracts `strategies/`, `risk/`, `portfolio/`, and
`execution/` are all written against. Nothing here has sport-specific
fields — that's what `horse_racing/` and `football/` are for; a `Signal`
just carries a free-form `context` dict for sport-specific detail that the
journal/dashboard can render without the core types needing to know about
xG or time-to-off.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class Sport(str, Enum):
    HORSE_RACING = "horse_racing"
    FOOTBALL = "football"


class Side(str, Enum):
    BACK = "BACK"
    LAY = "LAY"


class TradeGrade(str, Enum):
    """Ordered worst-to-best is REJECT < C < B < A < A_PLUS.

    Live trading is initially restricted to A_PLUS/A only (see
    docs/PLAN.md Phase 11) — that restriction is enforced wherever signals
    are filtered for live execution, not baked into this enum.
    """

    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    REJECT = "REJECT"


_GRADE_RANK = {
    TradeGrade.REJECT: 0,
    TradeGrade.C: 1,
    TradeGrade.B: 2,
    TradeGrade.A: 3,
    TradeGrade.A_PLUS: 4,
}


def grade_at_least(grade: TradeGrade, minimum: TradeGrade) -> bool:
    return _GRADE_RANK[grade] >= _GRADE_RANK[minimum]


@dataclass(frozen=True)
class Signal:
    """One trading opportunity, accepted or rejected.

    A REJECT signal is a first-class citizen, not an absence of one — the
    spec requires every rejected signal to be journaled for later research,
    so `Signal` must be able to represent "we looked at this and said no"
    just as fully as an accepted trade.
    """

    timestamp: datetime
    sport: Sport
    strategy: str
    market_id: str
    selection_id: str
    side: Side
    grade: TradeGrade

    market_probability: float
    model_probability: float
    fair_odds: float
    available_price: float

    gross_edge: float
    estimated_commission: float
    estimated_slippage: float
    estimated_fill_probability: float
    net_expected_value: float
    confidence: float

    expected_holding_time_seconds: float
    capital_required: float

    reason: str
    rejection_reason: str | None = None

    context: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.grade is not TradeGrade.REJECT

    @property
    def capital_efficiency_score(self) -> float:
        """net_expected_value x confidence x fill_probability / lock_time.

        This is the spec's *example* formula, explicitly flagged there as
        unvalidated ("do not blindly use this formula without validating
        it") — kept here as the Phase-1 placeholder ranking function so
        `portfolio/` (Phase 8) has something to start from and compare
        alternatives against, not as a claim that this is the right one.
        """
        lock_time = max(self.expected_holding_time_seconds, 1.0)
        return (self.net_expected_value * self.confidence * self.estimated_fill_probability) / lock_time


class Strategy(Protocol):
    """What every strategy module (Phase 5 horse, Phase 7 football) implements."""

    name: str
    sport: Sport

    def generate_signals(self, snapshot: Any) -> list[Signal]:
        """Given the current known-so-far market/event state, return zero or more Signals."""
        ...


class FootballFeed(Protocol):
    """Pluggable live football state provider (score/minute/xG/etc).

    No concrete provider is wired in yet (Phase 1) — see
    data/football_feed.py for the NullFeed placeholder and the rationale.
    """

    def poll(self, match_id: str) -> dict[str, Any]:
        """Return the latest known state for a match. Must include a timestamp."""
        ...
