from betfair_trading.core.interfaces import TradeGrade
from betfair_trading.strategies.base import (
    DEFAULT_GRADE_THRESHOLDS,
    CommissionModel,
    estimate_fill_probability,
    grade_signal,
)


def test_commission_only_charged_on_profit():
    commission = CommissionModel(rate=0.05)
    assert commission.commission_on_profit(10.0) == 0.5
    assert commission.commission_on_profit(-10.0) == 0.0
    assert commission.commission_on_profit(0.0) == 0.0


def test_fill_probability_none_spread_is_zero():
    assert estimate_fill_probability(None, 100.0, 100.0) == 0.0


def test_fill_probability_tighter_spread_scores_higher():
    tight = estimate_fill_probability(1, 100.0, 100.0)
    wide = estimate_fill_probability(5, 100.0, 100.0)
    assert tight > wide


def test_fill_probability_more_depth_scores_higher():
    thin = estimate_fill_probability(1, 5.0, 5.0)
    deep = estimate_fill_probability(1, 200.0, 200.0)
    assert deep > thin


def test_fill_probability_bounded_zero_to_one():
    for spread in (0, 1, 5, 20):
        for depth in (0.0, 10.0, 1000.0):
            p = estimate_fill_probability(spread, depth, depth)
            assert 0.0 <= p <= 1.0


def test_fill_probability_uses_thinner_side():
    thin_lay = estimate_fill_probability(1, 200.0, 1.0)
    balanced = estimate_fill_probability(1, 200.0, 200.0)
    assert thin_lay < balanced


def test_grade_signal_rejects_low_fill_probability_regardless_of_ev():
    grade = grade_signal(net_expected_value=0.05, confidence=0.9, fill_probability=0.1)
    assert grade == TradeGrade.REJECT


def test_grade_signal_rejects_non_positive_ev():
    assert grade_signal(0.0, confidence=0.9, fill_probability=0.9) == TradeGrade.REJECT
    assert grade_signal(-0.01, confidence=0.9, fill_probability=0.9) == TradeGrade.REJECT


def test_grade_signal_a_plus_requires_both_ev_and_confidence():
    t = DEFAULT_GRADE_THRESHOLDS
    grade = grade_signal(t.a_plus_min_net_ev, t.a_plus_min_confidence, fill_probability=0.9)
    assert grade == TradeGrade.A_PLUS

    # high EV but low confidence should not reach A+
    grade_low_conf = grade_signal(t.a_plus_min_net_ev, confidence=0.1, fill_probability=0.9)
    assert grade_low_conf != TradeGrade.A_PLUS


def test_grade_signal_b_only_needs_ev_threshold():
    t = DEFAULT_GRADE_THRESHOLDS
    grade = grade_signal(t.b_min_net_ev, confidence=0.0, fill_probability=0.9)
    assert grade == TradeGrade.B


def test_grade_signal_below_all_thresholds_is_reject():
    grade = grade_signal(0.0001, confidence=0.0, fill_probability=0.9)
    assert grade == TradeGrade.REJECT
