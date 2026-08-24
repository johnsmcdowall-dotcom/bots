"""Shared signal factory built on the fitted TargetBeforeStopModel
(HORSE MODEL 1, Phase 4): given one FeatureRow and one TargetStopConfig,
computes the conditional expected value of the trade and returns a graded
Signal — REJECT-graded if it doesn't clear costs, never `None`, so every
evaluated opportunity can be journaled. strategies/momentum.py,
mean_reversion.py, and scalping.py are all thin entry-filters wrapping
this one factory with different configs/conditions; strategies/bsp_drift.py
reuses `evaluate_priced_opportunity` (the low-level core, below) directly
since it prices a trade from a regression forecast rather than a fitted
classifier's P(target).

EV MODEL — stated precisely because it's a real, documented simplification:

The fitted model predicts P(TARGET | resolved) — the probability the
trade hits its target before its stop, CONDITIONAL on one of the two
happening before the timeout (models/labels.py excludes TIMEOUT rows from
training). `net_expected_value` here is therefore also conditional on
resolution — it does NOT yet weight in P(TIMEOUT) or model what a timed-
out position is worth (in practice, probably closed near breakeven at the
prevailing market price). That correction belongs to Phase 6's execution-
aware backtest, which can observe what actually happens to a real held
position past its timeout; inventing a P(TIMEOUT) estimate here without
evidence would be exactly the kind of unvalidated complexity the spec
warns against.

The per-stake profit/loss for a resolved outcome uses the standard
Betfair "trade the ladder" (green-up) formula, derived here from first
principles (setting win/lose exposure equal at entry vs. exit), not
assumed from memory — both directions divide by the EXIT price, which is
easy to get backwards:

    BACK then LAY: profit/stake = (entry_price - exit_price) / exit_price
    LAY then BACK:  profit/stake = (exit_price - entry_price) / exit_price

`model_probability`/`market_probability` on the resulting Signal are NOT
directly comparable win-probabilities the way they would be for a
fair-value strategy (spec's Strategy 1): `model_probability` is P(target
before stop) for this specific trade, while `market_probability` is the
market's current implied win probability for the runner, kept for
journaling context. `gross_edge`/`net_expected_value` come from the
target-before-stop EV math above, not from a (model - market) probability
gap.
"""

from __future__ import annotations

from typing import Any

from betfair_trading.betfair.ticks import shift_ticks
from betfair_trading.core.interfaces import Side, Signal, Sport, TradeGrade
from betfair_trading.features.pipeline import FeatureRow
from betfair_trading.models.baseline import TargetBeforeStopModel
from betfair_trading.models.dataset import to_model_matrix
from betfair_trading.models.labels import TargetStopConfig
from betfair_trading.strategies.base import (
    DEFAULT_COMMISSION,
    DEFAULT_GRADE_THRESHOLDS,
    CommissionModel,
    GradeThresholds,
    estimate_fill_probability,
    grade_signal,
)


def resolved_profit_per_stake(entry_price: float, exit_price: float, side: Side) -> float:
    """P&L per £1 of stake for a position opened at entry_price and closed
    ("greened up") at exit_price. See module docstring for the derivation.
    """
    if side is Side.BACK:
        return (entry_price - exit_price) / exit_price
    return (exit_price - entry_price) / exit_price


def entry_price_for_side(feature_row: FeatureRow, side: Side) -> float | None:
    return feature_row.microstructure.best_back if side is Side.BACK else feature_row.microstructure.best_lay


def capital_required_per_unit_stake(entry_price: float, side: Side) -> float:
    """Liability, not stake, for a LAY trade — per the spec's explicit
    instruction. £1 (the stake itself) for BACK.
    """
    return 1.0 if side is Side.BACK else max(entry_price - 1.0, 0.0)


def reject_signal(
    strategy_name: str,
    feature_row: FeatureRow,
    side: Side,
    reason: str,
    available_price: float = 0.0,
    context: dict[str, Any] | None = None,
) -> Signal:
    return Signal(
        timestamp=feature_row.timestamp,
        sport=Sport.HORSE_RACING,
        strategy=strategy_name,
        market_id=feature_row.market_id,
        selection_id=feature_row.selection_id,
        side=side,
        grade=TradeGrade.REJECT,
        market_probability=0.0,
        model_probability=0.0,
        fair_odds=0.0,
        available_price=available_price,
        gross_edge=0.0,
        estimated_commission=0.0,
        estimated_slippage=0.0,
        estimated_fill_probability=0.0,
        net_expected_value=0.0,
        confidence=0.0,
        expected_holding_time_seconds=0.0,
        capital_required=0.0,
        reason="not evaluated",
        rejection_reason=reason,
        context=context or {},
    )


def evaluate_priced_opportunity(
    strategy_name: str,
    feature_row: FeatureRow,
    side: Side,
    entry_price: float,
    target_price: float,
    stop_price: float,
    probability_of_target: float,
    confidence: float,
    holding_time_seconds: float,
    reason: str,
    commission: CommissionModel = DEFAULT_COMMISSION,
    thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
    extra_context: dict[str, Any] | None = None,
) -> Signal:
    """The low-level core: given an already-priced target/stop and a
    probability of reaching the target (from wherever the caller got it —
    a fitted classifier's predict_proba, or a caller-supplied confidence
    alongside a regression forecast), compute EV/commission/grading and
    build the Signal. `evaluate_target_before_stop_opportunity` (below)
    and strategies/bsp_drift.py are both thin callers of this.
    """
    profit_if_target = resolved_profit_per_stake(entry_price, target_price, side)
    loss_if_stop = resolved_profit_per_stake(entry_price, stop_price, side)

    gross_edge = probability_of_target * profit_if_target + (1 - probability_of_target) * loss_if_stop

    commission_if_target = commission.commission_on_profit(profit_if_target)
    net_profit_if_target = profit_if_target - commission_if_target
    net_expected_value = probability_of_target * net_profit_if_target + (1 - probability_of_target) * loss_if_stop
    estimated_commission = probability_of_target * commission_if_target

    fill_probability = estimate_fill_probability(
        feature_row.microstructure.spread_ticks,
        feature_row.microstructure.back_depth,
        feature_row.microstructure.lay_depth,
    )

    grade = grade_signal(net_expected_value, confidence, fill_probability, thresholds)

    market_probability = feature_row.book_position.normalised_probability
    if market_probability is None:
        market_probability = 1.0 / entry_price

    context = {
        "target_price": target_price,
        "stop_price": stop_price,
        "placeholder_fill_model": True,
        "ev_conditional_on_resolution": True,
    }
    if extra_context:
        context.update(extra_context)

    return Signal(
        timestamp=feature_row.timestamp,
        sport=Sport.HORSE_RACING,
        strategy=strategy_name,
        market_id=feature_row.market_id,
        selection_id=feature_row.selection_id,
        side=side,
        grade=grade,
        market_probability=market_probability,
        model_probability=probability_of_target,
        fair_odds=(1.0 / probability_of_target) if probability_of_target > 0 else float("inf"),
        available_price=entry_price,
        gross_edge=gross_edge,
        estimated_commission=estimated_commission,
        estimated_slippage=0.0,
        estimated_fill_probability=fill_probability,
        net_expected_value=net_expected_value,
        confidence=confidence,
        expected_holding_time_seconds=holding_time_seconds,
        capital_required=capital_required_per_unit_stake(entry_price, side),
        reason=reason,
        rejection_reason=None if grade is not TradeGrade.REJECT else "net EV/confidence/fill probability below threshold",
        context=context,
    )


def evaluate_target_before_stop_opportunity(
    strategy_name: str,
    feature_row: FeatureRow,
    config: TargetStopConfig,
    model: TargetBeforeStopModel,
    model_confidence: float,
    commission: CommissionModel = DEFAULT_COMMISSION,
    thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
) -> Signal:
    """`model_confidence` is caller-supplied (e.g. derived from the
    model's validation-set calibration) rather than computed here — this
    module has no way to know how trustworthy `model` is out of sample,
    and guessing would hide that as a magic number.
    """
    side = config.side
    entry_price = entry_price_for_side(feature_row, side)
    if entry_price is None:
        return reject_signal(
            strategy_name, feature_row, side, f"no {side.value} price currently available",
            context={"config": config},
        )

    _, X, kept = to_model_matrix([feature_row])
    if not kept or not kept[0]:
        return reject_signal(
            strategy_name, feature_row, side, "feature row has missing values the model requires",
            available_price=entry_price, context={"config": config},
        )

    probability_target = model.predict_proba(X)[0]

    target_price = shift_ticks(entry_price, -config.target_ticks if side is Side.BACK else config.target_ticks)
    stop_price = shift_ticks(entry_price, config.stop_ticks if side is Side.BACK else -config.stop_ticks)

    reason = (
        f"{strategy_name}: P(target {config.target_ticks}t before stop {config.stop_ticks}t | resolved)"
        f"={probability_target:.1%} per unit stake"
    )

    return evaluate_priced_opportunity(
        strategy_name, feature_row, side, entry_price, target_price, stop_price,
        probability_target, model_confidence, config.timeout_seconds, reason,
        commission, thresholds, extra_context={"config": config},
    )
