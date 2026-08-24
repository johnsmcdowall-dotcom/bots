"""Shared strategy infrastructure — everything a Phase 5 strategy needs
that isn't specific to one entry-filter idea (steamer vs drifter vs mean
reversion vs scalping).

This is deliberately thin. Real execution-cost realism (queue position,
partial fills, an actual slippage distribution) is Phase 6's job; what's
here is a documented, simple placeholder so strategies have *something* to
compute net EV against today — not a claim that it's realistic yet. Every
Signal produced via this module carries that caveat forward in
`context["placeholder_fill_model"] = True`.
"""

from __future__ import annotations

from dataclasses import dataclass

from betfair_trading.core.interfaces import TradeGrade


@dataclass(frozen=True)
class CommissionModel:
    """Flat-rate commission on net winning profit — Betfair's actual
    structure (charged on a market's net profit, not per bet). Applied
    per-trade here since strategies evaluate one opportunity at a time; a
    true market-level "net winnings across everything in this market"
    calculation belongs to the portfolio/execution layer (Phase 6/8).
    """

    rate: float = 0.05  # Betfair UK/IRE standard rate at time of writing; override per jurisdiction/account

    def commission_on_profit(self, profit: float) -> float:
        return self.rate * profit if profit > 0 else 0.0


DEFAULT_COMMISSION = CommissionModel()


def estimate_fill_probability(spread_ticks: int | None, back_depth: float, lay_depth: float) -> float:
    """A documented PLACEHOLDER, not Phase 6's realistic queue/fill
    simulator (which will model available volume ahead of an order, time
    resting, and actual partial-fill behaviour). Narrower spread and
    deeper liquidity on both sides score higher; the exact curve is
    arbitrary and unvalidated against real execution data — it exists so
    strategies can reject the obviously-illiquid case (e.g. a wide spread
    with thin depth) without waiting for Phase 6.
    """
    if spread_ticks is None or spread_ticks < 0:
        return 0.0
    thinner_side_depth = min(back_depth, lay_depth)
    spread_component = 1.0 / (1.0 + spread_ticks)
    depth_component = min(thinner_side_depth / 100.0, 1.0)
    return round(min(1.0, 0.3 + 0.7 * spread_component * depth_component), 4)


@dataclass(frozen=True)
class GradeThresholds:
    """Net-EV-after-costs / confidence thresholds for each trade grade,
    per docs/ARCHITECTURE.md's A+/A/B/C/REJECT rubric. Configurable
    starting points, not validated truth — revisit once real evidence
    exists (docs/PLAN.md Phase 5 caveat).
    """

    a_plus_min_net_ev: float = 0.02
    a_min_net_ev: float = 0.01
    b_min_net_ev: float = 0.003
    a_plus_min_confidence: float = 0.75
    a_min_confidence: float = 0.6
    min_fill_probability: float = 0.5


DEFAULT_GRADE_THRESHOLDS = GradeThresholds()


def grade_signal(
    net_expected_value: float,
    confidence: float,
    fill_probability: float,
    thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
) -> TradeGrade:
    """Reject aggressively: insufficient fill probability or non-positive
    net EV is always REJECT, regardless of how good anything else looks —
    per the spec, a trade doesn't exist just because a technical condition
    fired.
    """
    if fill_probability < thresholds.min_fill_probability:
        return TradeGrade.REJECT
    if net_expected_value <= 0:
        return TradeGrade.REJECT
    if net_expected_value >= thresholds.a_plus_min_net_ev and confidence >= thresholds.a_plus_min_confidence:
        return TradeGrade.A_PLUS
    if net_expected_value >= thresholds.a_min_net_ev and confidence >= thresholds.a_min_confidence:
        return TradeGrade.A
    if net_expected_value >= thresholds.b_min_net_ev:
        return TradeGrade.B
    return TradeGrade.REJECT
