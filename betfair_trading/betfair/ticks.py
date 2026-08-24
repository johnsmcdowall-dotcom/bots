"""Betfair's exact odds ladder and tick sizes.

Every profit/stop/target/slippage calculation anywhere in the platform
(execution, backtesting, horse-racing target-before-stop models, scalping)
must go through this module rather than doing float arithmetic on prices
directly — Betfair's tick increment is not constant (0.01 near 1.01, 10
near 500), so "add 0.01" is only valid in the 1.01-2.0 band.

The full ladder (1.01 to 1000, ~350 price points) is precomputed once at
import time as a sorted tuple, and everything else is index arithmetic
against it — that makes "N ticks away" and "ticks between two prices"
exact, with no float-drift risk from repeated addition.
"""

from __future__ import annotations

import bisect

# (range_start, range_end_exclusive, increment) — Betfair's published tick ladder.
_LADDER_RANGES: tuple[tuple[float, float, float], ...] = (
    (1.01, 2.0, 0.01),
    (2.0, 3.0, 0.02),
    (3.0, 4.0, 0.05),
    (4.0, 6.0, 0.1),
    (6.0, 10.0, 0.2),
    (10.0, 20.0, 0.5),
    (20.0, 30.0, 1.0),
    (30.0, 50.0, 2.0),
    (50.0, 100.0, 5.0),
    (100.0, 1000.0, 10.0),
)

MIN_PRICE = 1.01
MAX_PRICE = 1000.0


def _generate_ladder() -> tuple[float, ...]:
    prices: list[float] = []
    for start, end, step in _LADDER_RANGES:
        price = start
        # Round at every step (not just at the end) so accumulated float
        # error never pushes a price across a range boundary.
        steps_in_range = round((end - start) / step)
        for i in range(steps_in_range):
            prices.append(round(start + i * step, 2))
    prices.append(MAX_PRICE)
    return tuple(prices)


PRICE_LADDER: tuple[float, ...] = _generate_ladder()
_PRICE_TO_INDEX: dict[float, int] = {price: i for i, price in enumerate(PRICE_LADDER)}


def is_valid_price(price: float) -> bool:
    return price in _PRICE_TO_INDEX


def tick_index(price: float) -> int:
    """Exact index for a price on the ladder. Raises ValueError if the price
    is not itself a valid Betfair tick (use `round_to_nearest_tick` first for
    arbitrary/noisy floats)."""
    try:
        return _PRICE_TO_INDEX[price]
    except KeyError:
        raise ValueError(f"{price!r} is not a valid Betfair tick price") from None


def price_at_index(index: int) -> float:
    if index < 0:
        index = 0
    if index >= len(PRICE_LADDER):
        index = len(PRICE_LADDER) - 1
    return PRICE_LADDER[index]


def round_to_nearest_tick(price: float) -> float:
    """Snap an arbitrary float (e.g. a model's fair-price estimate) to the
    nearest valid Betfair tick."""
    if price <= MIN_PRICE:
        return MIN_PRICE
    if price >= MAX_PRICE:
        return MAX_PRICE
    i = bisect.bisect_left(PRICE_LADDER, price)
    if i == 0:
        return PRICE_LADDER[0]
    before, after = PRICE_LADDER[i - 1], PRICE_LADDER[i]
    return before if (price - before) <= (after - price) else after


def shift_ticks(price: float, ticks: int) -> float:
    """Move `price` by `ticks` ladder steps. Positive = price increases
    (drift/lengthen); negative = price decreases (shorten). Clamps at the
    ladder's ends rather than raising, since a strategy computing "target -3
    ticks" near evens should get 1.01, not an exception.
    """
    index = tick_index(round_to_nearest_tick(price))
    return price_at_index(index + ticks)


def ticks_between(price_a: float, price_b: float) -> int:
    """Signed tick distance from price_a to price_b (positive if price_b is
    the longer/higher price)."""
    return tick_index(round_to_nearest_tick(price_b)) - tick_index(round_to_nearest_tick(price_a))
