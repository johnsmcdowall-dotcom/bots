"""Rolling (time-windowed) features for one runner's price/traded-volume
history, over the windows the spec calls out: 1s, 3s, 5s, 10s, 30s, 60s,
2min, 5min.

Every function here takes the runner's full observed point series plus an
`as_of` timestamp and a window length, and only ever looks at points with
`as_of - window_seconds <= timestamp <= as_of` — so feeding it the full
history of a market (not just "history so far") is safe and cannot leak
the future, as long as `as_of` itself never exceeds what was actually
known at that point in the replay (features/pipeline.py guarantees this by
construction: it calls in strictly ascending as_of order and only ever
appends the current row's own point before computing that row's features).

Every feature returns `None` when the window doesn't have enough data
points to compute it honestly (fewer than 2, or 3 for acceleration) —
never a fabricated 0.0.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from betfair_trading.betfair.models import RunnerLadder
from betfair_trading.betfair.ticks import ticks_between

DEFAULT_WINDOW_SECONDS: tuple[float, ...] = (1.0, 3.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)


@dataclass(frozen=True)
class PricePoint:
    """One observation for a runner: `price` should be last_traded_price
    when a trade has occurred, `traded_volume` is the runner's cumulative
    total_matched at this timestamp (both straight off RunnerLadder).
    """

    timestamp: datetime
    price: float
    traded_volume: float


def price_proxy(runner: RunnerLadder) -> float | None:
    """The representative price used to build a runner's PricePoint series:
    prefer the actual last-traded price, fall back to mid-price, then to
    best back, else `None` if the runner isn't priced at all yet.

    Used identically by features/pipeline.py (building live rolling
    features) and models/labels.py (building forward-looking training
    labels from the same recorded data) — a single definition so both
    always agree on what "the price" was at a given snapshot; if this
    diverged between the two, a label could end up more optimistic/
    pessimistic than what a live feature computation actually saw.
    """
    if runner.last_traded_price is not None:
        return runner.last_traded_price
    best_back = runner.best_back
    best_lay = runner.best_lay
    if best_back is not None and best_lay is not None:
        return (best_back.price + best_lay.price) / 2.0
    if best_back is not None:
        return best_back.price
    return None


def _window_slice(points: Sequence[PricePoint], as_of: datetime, window_seconds: float) -> list[PricePoint]:
    """Precondition: `points` is sorted ascending by timestamp. Both bounds
    are inclusive: `as_of - window_seconds <= timestamp <= as_of`.
    """
    if not points:
        return []
    timestamps = [p.timestamp for p in points]
    lower_bound = as_of - timedelta(seconds=window_seconds)
    lo = bisect.bisect_left(timestamps, lower_bound)
    hi = bisect.bisect_right(timestamps, as_of)
    return list(points[lo:hi])


def _split_in_half(window: list[PricePoint]) -> tuple[list[PricePoint], list[PricePoint]]:
    """Split by point count, not by elapsed time, with the two halves
    overlapping at the middle point. A time-based midpoint split can strand
    an odd point count into a 2/1 split (the trailing half then has too few
    points for a rate), which is exactly the degenerate case acceleration
    most needs to handle — e.g. a 3-point window, the minimum this function
    is ever called with.
    """
    midpoint_index = len(window) // 2
    first_half = window[: midpoint_index + 1]
    second_half = window[midpoint_index:]
    return first_half, second_half


def _rate(window: list[PricePoint], value_of) -> float | None:
    if len(window) < 2:
        return None
    dt = (window[-1].timestamp - window[0].timestamp).total_seconds()
    if dt <= 0:
        return None
    return (value_of(window[-1]) - value_of(window[0])) / dt


def _acceleration(window: list[PricePoint], value_of) -> float | None:
    """Second derivative via finite differences: velocity of the second
    half of the window minus velocity of the first half, over the time
    between their midpoints.
    """
    if len(window) < 3:
        return None
    first_half, second_half = _split_in_half(window)
    v1 = _rate(first_half, value_of)
    v2 = _rate(second_half, value_of)
    if v1 is None or v2 is None:
        return None
    dt = (second_half[-1].timestamp - first_half[0].timestamp).total_seconds()
    if dt <= 0:
        return None
    return (v2 - v1) / dt


def _vwap(window: list[PricePoint]) -> float | None:
    """Volume-weighted average traded price, approximated from consecutive
    snapshot deltas: for each pair of consecutive observations, the traded
    volume that arrived between them is weighted by the later observation's
    last-traded-price.

    This is an approximation, not a true per-trade VWAP: it assumes the
    volume that arrived between two snapshots traded at the later
    snapshot's last_traded_price, because the platform does not yet
    capture Betfair's traded-volume-by-price ladder (EX_TRADED_VOL) at the
    per-price level — only aggregate total_matched. Flagged in
    docs/PLAN.md as a follow-up; do not treat this as exact.
    """
    if len(window) < 2:
        return None
    total_weighted_price = 0.0
    total_volume = 0.0
    for previous, current in zip(window, window[1:]):
        delta_volume = current.traded_volume - previous.traded_volume
        if delta_volume <= 0:
            continue
        total_weighted_price += current.price * delta_volume
        total_volume += delta_volume
    if total_volume <= 0:
        return None
    return total_weighted_price / total_volume


@dataclass(frozen=True)
class RollingFeatures:
    window_seconds: float
    observation_count: int

    volume_change: float | None
    volume_velocity: float | None
    volume_acceleration: float | None
    vwap: float | None

    price_velocity: float | None
    price_acceleration: float | None
    tick_velocity: float | None

    recent_high: float | None
    recent_low: float | None
    distance_from_high_ticks: int | None
    distance_from_low_ticks: int | None


def compute_rolling_features(
    points: Sequence[PricePoint], as_of: datetime, window_seconds: float
) -> RollingFeatures:
    window = _window_slice(points, as_of, window_seconds)

    volume_change = (window[-1].traded_volume - window[0].traded_volume) if len(window) >= 2 else None
    volume_velocity = _rate(window, lambda p: p.traded_volume)
    volume_acceleration = _acceleration(window, lambda p: p.traded_volume)
    vwap = _vwap(window)

    price_velocity = _rate(window, lambda p: p.price)
    price_acceleration = _acceleration(window, lambda p: p.price)
    tick_velocity = None
    if len(window) >= 2:
        dt = (window[-1].timestamp - window[0].timestamp).total_seconds()
        if dt > 0:
            tick_velocity = ticks_between(window[0].price, window[-1].price) / dt

    recent_high = max((p.price for p in window), default=None)
    recent_low = min((p.price for p in window), default=None)
    distance_from_high_ticks = None
    distance_from_low_ticks = None
    if window:
        current_price = window[-1].price
        distance_from_high_ticks = ticks_between(current_price, recent_high)
        distance_from_low_ticks = ticks_between(current_price, recent_low)

    return RollingFeatures(
        window_seconds=window_seconds,
        observation_count=len(window),
        volume_change=volume_change,
        volume_velocity=volume_velocity,
        volume_acceleration=volume_acceleration,
        vwap=vwap,
        price_velocity=price_velocity,
        price_acceleration=price_acceleration,
        tick_velocity=tick_velocity,
        recent_high=recent_high,
        recent_low=recent_low,
        distance_from_high_ticks=distance_from_high_ticks,
        distance_from_low_ticks=distance_from_low_ticks,
    )
