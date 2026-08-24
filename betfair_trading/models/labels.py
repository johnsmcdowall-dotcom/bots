"""Forward-looking label construction for Phase 4 baseline models.

This is the ONLY place the platform is allowed to look at future price
data outside of a live signal's own subsequent settlement — used
exclusively to build (feature_row, label) training pairs from already-
completed historical markets, never to compute a feature a live signal
would see. `features/pipeline.py` (live features) and this module (labels)
are kept structurally separate for exactly that reason: nothing in
`features/` imports from `models/`, so there is no path by which a label
could leak backwards into a live feature computation.

Three label families, matching the spec's HORSE MODEL 1/2/8:
- `short_horizon_label`: HORSE MODEL 2 — signed tick movement N seconds
  ahead, bucketed into the 7 classes the spec asks for.
- `target_before_stop_label`: HORSE MODEL 1 — did price reach a target
  before a stop, within a timeout, from either BACK or LAY's perspective.
- `closing_price_label`: HORSE MODEL 8 — a documented PROXY for BSP (see
  its docstring for why it isn't the real thing yet).
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Sequence

from betfair_trading.betfair.ticks import shift_ticks, ticks_between
from betfair_trading.core.interfaces import Side
from betfair_trading.features.rolling import PricePoint

# HORSE MODEL 2 tick-movement buckets, per spec: P(-3),P(-2),P(-1),P(flat),P(+1),P(+2),P(+3).
# Index 0 ("<=-3") = shortened 3 ticks or more; index 6 (">=+3") = drifted
# 3 ticks or more. Clamping rather than an unbounded class keeps this a
# fixed-size classification problem regardless of how far price can move.
TICK_BUCKET_LABELS: tuple[str, ...] = ("<=-3", "-2", "-1", "0", "+1", "+2", ">=+3")


def tick_movement_bucket(tick_delta: int) -> int:
    clamped = max(-3, min(3, tick_delta))
    return clamped + 3


def _price_at_or_before(points: Sequence[PricePoint], as_of: datetime) -> PricePoint | None:
    """Most recent point with timestamp <= as_of. Precondition: points sorted ascending."""
    timestamps = [p.timestamp for p in points]
    idx = bisect.bisect_right(timestamps, as_of) - 1
    return points[idx] if idx >= 0 else None


def _price_at_or_after(
    points: Sequence[PricePoint], as_of: datetime, tolerance_seconds: float
) -> PricePoint | None:
    """Nearest point with timestamp in [as_of, as_of + tolerance_seconds].
    Recorded snapshots don't land on exact horizon boundaries (a horizon of
    "10 seconds ahead" needs the closest thing actually captured), so this
    is a nearest-within-tolerance lookup, not an exact match.
    """
    timestamps = [p.timestamp for p in points]
    idx = bisect.bisect_left(timestamps, as_of)
    if idx >= len(points):
        return None
    candidate = points[idx]
    if (candidate.timestamp - as_of).total_seconds() > tolerance_seconds:
        return None
    return candidate


@dataclass(frozen=True)
class ShortHorizonLabel:
    horizon_seconds: float
    entry_price: float | None
    future_price: float | None
    tick_delta: int | None
    bucket: int | None  # index into TICK_BUCKET_LABELS; None if no future observation was found


def short_horizon_label(
    points: Sequence[PricePoint],
    as_of: datetime,
    horizon_seconds: float,
    lookup_tolerance_seconds: float = 2.0,
) -> ShortHorizonLabel:
    entry = _price_at_or_before(points, as_of)
    if entry is None:
        return ShortHorizonLabel(horizon_seconds, None, None, None, None)

    future = _price_at_or_after(points, as_of + timedelta(seconds=horizon_seconds), lookup_tolerance_seconds)
    if future is None:
        return ShortHorizonLabel(horizon_seconds, entry.price, None, None, None)

    delta = ticks_between(entry.price, future.price)
    return ShortHorizonLabel(horizon_seconds, entry.price, future.price, delta, tick_movement_bucket(delta))


class TargetBeforeStopOutcome(str, Enum):
    TARGET = "TARGET"
    STOP = "STOP"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class TargetBeforeStopLabel:
    entry_price: float
    side: Side
    target_ticks: int
    stop_ticks: int
    outcome: TargetBeforeStopOutcome
    outcome_price: float | None
    time_to_outcome_seconds: float | None


@dataclass(frozen=True)
class TargetStopConfig:
    side: Side
    target_ticks: int
    stop_ticks: int
    timeout_seconds: float


# The spec's own combinations (HORSE MODEL 1), evaluated for both BACK and
# LAY entry, at a single default timeout. The timeout is a documented
# starting point, not a validated optimum — Phase 5 (strategies) is where
# per-config timeout tuning against real evidence belongs, not here.
_CANONICAL_TARGET_STOP_PAIRS: tuple[tuple[int, int], ...] = ((1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (5, 3))
_DEFAULT_TIMEOUT_SECONDS = 30.0

CANONICAL_TARGET_STOP_CONFIGS: tuple[TargetStopConfig, ...] = tuple(
    TargetStopConfig(side, target, stop, _DEFAULT_TIMEOUT_SECONDS)
    for side in (Side.BACK, Side.LAY)
    for target, stop in _CANONICAL_TARGET_STOP_PAIRS
)


def target_before_stop_label(
    points: Sequence[PricePoint],
    as_of: datetime,
    side: Side,
    target_ticks: int,
    stop_ticks: int,
    timeout_seconds: float,
) -> TargetBeforeStopLabel | None:
    """Walk forward from `as_of` and determine whether price reaches the
    target before the stop, or times out first.

    For BACK, profit is price SHORTENING (going down) by `target_ticks`;
    loss is price DRIFTING (going up) by `stop_ticks`. LAY is the mirror
    image. Both `target_ticks` and `stop_ticks` are given as positive tick
    counts. Returns `None` if there's no known entry price at `as_of`.
    """
    entry = _price_at_or_before(points, as_of)
    if entry is None:
        return None
    entry_price = entry.price

    if side is Side.BACK:
        target_price = shift_ticks(entry_price, -target_ticks)
        stop_price = shift_ticks(entry_price, stop_ticks)
    else:
        target_price = shift_ticks(entry_price, target_ticks)
        stop_price = shift_ticks(entry_price, -stop_ticks)

    timestamps = [p.timestamp for p in points]
    start_idx = bisect.bisect_right(timestamps, as_of)
    deadline = as_of + timedelta(seconds=timeout_seconds)

    for point in points[start_idx:]:
        if point.timestamp > deadline:
            break
        hit_target = point.price <= target_price if side is Side.BACK else point.price >= target_price
        hit_stop = point.price >= stop_price if side is Side.BACK else point.price <= stop_price
        # target_price and stop_price sit on opposite sides of entry_price
        # by construction, so a single price can satisfy at most one —
        # check target first only to fix iteration order, not to break a tie.
        if hit_target:
            return TargetBeforeStopLabel(
                entry_price, side, target_ticks, stop_ticks,
                TargetBeforeStopOutcome.TARGET, point.price, (point.timestamp - as_of).total_seconds(),
            )
        if hit_stop:
            return TargetBeforeStopLabel(
                entry_price, side, target_ticks, stop_ticks,
                TargetBeforeStopOutcome.STOP, point.price, (point.timestamp - as_of).total_seconds(),
            )

    return TargetBeforeStopLabel(
        entry_price, side, target_ticks, stop_ticks, TargetBeforeStopOutcome.TIMEOUT, None, None
    )


@dataclass(frozen=True)
class ClosingPriceLabel:
    entry_price: float | None
    closing_price: float | None
    tick_delta: int | None


def closing_price_label(points: Sequence[PricePoint], as_of: datetime) -> ClosingPriceLabel:
    """HORSE MODEL 8's forecast target: how many ticks between the price at
    `as_of` and the market's closing price.

    This uses the LAST recorded price point as a proxy for BSP/closing
    price, and is explicitly NOT real settlement data: the platform
    doesn't yet capture Betfair's actual BSP (that needs cleared-orders/
    settlement capture, which Phase 1/2 didn't build — see docs/PLAN.md).
    Treat any model trained on this label as forecasting "the last price
    this platform happened to record", not the true Betfair Starting
    Price, until that capture exists.
    """
    if not points:
        return ClosingPriceLabel(None, None, None)
    entry = _price_at_or_before(points, as_of)
    if entry is None:
        return ClosingPriceLabel(None, None, None)
    closing = points[-1]
    return ClosingPriceLabel(entry.price, closing.price, ticks_between(entry.price, closing.price))
