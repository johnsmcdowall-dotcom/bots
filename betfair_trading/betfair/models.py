"""Dataclasses everything else in the platform consumes for Betfair market
data — independent of the betfairlightweight wire format, so storage,
replay, and strategies are never coupled to a specific client library's
response shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MarketStatus(str, Enum):
    INACTIVE = "INACTIVE"
    OPEN = "OPEN"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class RunnerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    WINNER = "WINNER"
    LOSER = "LOSER"
    REMOVED = "REMOVED"
    HIDDEN = "HIDDEN"


@dataclass(frozen=True)
class PriceLevel:
    price: float
    size: float


@dataclass(frozen=True)
class RunnerLadder:
    """One runner's order book at one point in time."""

    selection_id: str
    status: RunnerStatus
    back: tuple[PriceLevel, ...] = field(default_factory=tuple)
    lay: tuple[PriceLevel, ...] = field(default_factory=tuple)
    last_traded_price: float | None = None
    total_matched: float = 0.0

    @property
    def best_back(self) -> PriceLevel | None:
        return self.back[0] if self.back else None

    @property
    def best_lay(self) -> PriceLevel | None:
        return self.lay[0] if self.lay else None


@dataclass(frozen=True)
class MarketSnapshot:
    """A market book at one point in time — the core unit stored/replayed."""

    market_id: str
    timestamp: datetime
    status: MarketStatus
    in_play: bool
    total_matched: float
    runners: tuple[RunnerLadder, ...] = field(default_factory=tuple)

    def runner(self, selection_id: str) -> RunnerLadder | None:
        for runner in self.runners:
            if runner.selection_id == selection_id:
                return runner
        return None


@dataclass(frozen=True)
class Order:
    market_id: str
    selection_id: str
    side: str  # "BACK" / "LAY" — kept as str here to avoid a core<->betfair import cycle
    price: float
    size: float
    order_id: str | None = None
    persistence_type: str = "LAPSE"


@dataclass(frozen=True)
class Fill:
    order_id: str
    matched_price: float
    matched_size: float
    timestamp: datetime
