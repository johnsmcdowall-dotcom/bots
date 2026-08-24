"""Instantaneous, single-snapshot order-book features for one runner.

Everything here is a pure function of one RunnerLadder (plus, where a
feature needs it, the parent MarketSnapshot's total_matched) — no history,
no rolling windows (that's features/rolling.py) and no other runners
(that's features/cross_runner.py). Kept separate so each layer can be unit
tested and later ablated independently, per docs/PLAN.md Phase 3.

Every feature returns `None` rather than a fabricated number when the
ladder doesn't support it (e.g. no lay side quoted) — a missing value is
honest; a silently-substituted 0.0 would poison anything trained on it.
"""

from __future__ import annotations

from dataclasses import dataclass

from betfair_trading.betfair.models import MarketSnapshot, RunnerLadder
from betfair_trading.betfair.ticks import ticks_between

def weighted_depth(levels: tuple, max_levels: int | None = None) -> float:
    """Nearer ladder levels count for more than deeper ones. Harmonic decay
    (1/(i+1)) is a documented, deliberately simple modelling choice — not
    validated against outcomes yet. Phase 4's permutation-importance/
    ablation pass is what should decide whether this beats flat or
    geometric weighting, per the Phase 3 plan ("remove useless complexity",
    not invent unvalidated complexity in the first place).
    """
    levels = levels[:max_levels] if max_levels else levels
    return sum(level.size / (i + 1) for i, level in enumerate(levels))


def total_depth(levels: tuple) -> float:
    return sum(level.size for level in levels)


@dataclass(frozen=True)
class MicrostructureFeatures:
    selection_id: str

    best_back: float | None
    best_lay: float | None
    mid_price: float | None
    spread_ticks: int | None
    spread_percentage: float | None
    microprice: float | None

    back_depth: float
    lay_depth: float
    weighted_back_depth: float
    weighted_lay_depth: float
    weight_of_money: float | None  # proportion of visible depth on the back side, in [0, 1]
    order_book_imbalance: float | None  # (back_depth - lay_depth) / (back_depth + lay_depth), in [-1, 1]

    traded_volume: float
    runner_market_share: float | None  # this runner's total_matched / market total_matched
    implied_probability: float | None  # 1 / best_back — NOT normalised across the race (see cross_runner.py)


def compute_microstructure(runner: RunnerLadder, market: MarketSnapshot) -> MicrostructureFeatures:
    best_back = runner.best_back
    best_lay = runner.best_lay

    mid_price = None
    spread_ticks = None
    spread_percentage = None
    microprice = None
    if best_back is not None and best_lay is not None:
        mid_price = (best_back.price + best_lay.price) / 2.0
        spread_ticks = ticks_between(best_back.price, best_lay.price)
        spread_percentage = (best_lay.price - best_back.price) / mid_price if mid_price else None
        # Standard microprice: weight each side's price by the OPPOSITE
        # side's size. Heavier lay size (more sellers queued) pulls the
        # microprice toward the back price, and vice versa.
        total_size = best_back.size + best_lay.size
        if total_size > 0:
            microprice = (best_back.price * best_lay.size + best_lay.price * best_back.size) / total_size

    back_depth = total_depth(runner.back)
    lay_depth = total_depth(runner.lay)
    weighted_back_depth = weighted_depth(runner.back)
    weighted_lay_depth = weighted_depth(runner.lay)

    weight_of_money = None
    order_book_imbalance = None
    combined_depth = back_depth + lay_depth
    if combined_depth > 0:
        weight_of_money = back_depth / combined_depth
        order_book_imbalance = (back_depth - lay_depth) / combined_depth

    runner_market_share = runner.total_matched / market.total_matched if market.total_matched > 0 else None
    implied_probability = (1.0 / best_back.price) if best_back is not None else None

    return MicrostructureFeatures(
        selection_id=runner.selection_id,
        best_back=best_back.price if best_back else None,
        best_lay=best_lay.price if best_lay else None,
        mid_price=mid_price,
        spread_ticks=spread_ticks,
        spread_percentage=spread_percentage,
        microprice=microprice,
        back_depth=back_depth,
        lay_depth=lay_depth,
        weighted_back_depth=weighted_back_depth,
        weighted_lay_depth=weighted_lay_depth,
        weight_of_money=weight_of_money,
        order_book_imbalance=order_book_imbalance,
        traded_volume=runner.total_matched,
        runner_market_share=runner_market_share,
        implied_probability=implied_probability,
    )
