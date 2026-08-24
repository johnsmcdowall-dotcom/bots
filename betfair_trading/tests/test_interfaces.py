from datetime import datetime, timezone

from betfair_trading.core.interfaces import Side, Signal, Sport, TradeGrade, grade_at_least


def _signal(**overrides) -> Signal:
    defaults = dict(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sport=Sport.HORSE_RACING,
        strategy="steamer",
        market_id="1.23",
        selection_id="456",
        side=Side.BACK,
        grade=TradeGrade.A,
        market_probability=0.4,
        model_probability=0.45,
        fair_odds=2.2,
        available_price=2.5,
        gross_edge=0.05,
        estimated_commission=0.02,
        estimated_slippage=0.005,
        estimated_fill_probability=0.9,
        net_expected_value=0.02,
        confidence=0.8,
        expected_holding_time_seconds=30.0,
        capital_required=20.0,
        reason="steamer confirmed",
    )
    defaults.update(overrides)
    return Signal(**defaults)


def test_is_actionable():
    assert _signal(grade=TradeGrade.A).is_actionable
    assert not _signal(grade=TradeGrade.REJECT, rejection_reason="poor liquidity").is_actionable


def test_grade_ordering():
    assert grade_at_least(TradeGrade.A_PLUS, TradeGrade.A)
    assert grade_at_least(TradeGrade.A, TradeGrade.A)
    assert not grade_at_least(TradeGrade.B, TradeGrade.A)
    assert not grade_at_least(TradeGrade.REJECT, TradeGrade.C)


def test_capital_efficiency_score():
    signal = _signal(
        net_expected_value=0.06,
        confidence=0.5,
        estimated_fill_probability=0.8,
        expected_holding_time_seconds=24.0,
    )
    # 0.06 * 0.5 * 0.8 / 24 = 0.001
    assert round(signal.capital_efficiency_score, 6) == round(0.06 * 0.5 * 0.8 / 24.0, 6)


def test_capital_efficiency_score_floors_lock_time_to_avoid_div_by_zero():
    signal = _signal(expected_holding_time_seconds=0.0)
    assert signal.capital_efficiency_score == signal.net_expected_value * signal.confidence * signal.estimated_fill_probability
