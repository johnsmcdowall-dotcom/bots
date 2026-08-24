from betfair_trading.core.interfaces import TradeGrade
from betfair_trading.risk.limits import RiskLimits


def test_default_grade_bands_match_spec():
    limits = RiskLimits()
    assert limits.band_for_grade(TradeGrade.A_PLUS).minimum_pct == 1.0
    assert limits.band_for_grade(TradeGrade.A_PLUS).maximum_pct == 1.5
    assert limits.band_for_grade(TradeGrade.A).minimum_pct == 0.6
    assert limits.band_for_grade(TradeGrade.B).maximum_pct == 0.5
    assert limits.band_for_grade(TradeGrade.C) is None
    assert limits.band_for_grade(TradeGrade.REJECT) is None


def test_drawdown_response_is_monotonic_and_thresholded():
    limits = RiskLimits()
    assert limits.risk_reduction_for_drawdown(0.0) == 0.0
    assert limits.risk_reduction_for_drawdown(9.9) == 0.0
    assert limits.risk_reduction_for_drawdown(10.0) == 20.0
    assert limits.risk_reduction_for_drawdown(14.9) == 20.0
    assert limits.risk_reduction_for_drawdown(15.0) == 40.0
    assert limits.risk_reduction_for_drawdown(20.0) == 100.0
    assert limits.risk_reduction_for_drawdown(30.0) == 100.0


def test_daily_stop_defaults():
    limits = RiskLimits()
    assert limits.soft_daily_stop_pct == -3.0
    assert limits.hard_daily_stop_pct == -5.0
