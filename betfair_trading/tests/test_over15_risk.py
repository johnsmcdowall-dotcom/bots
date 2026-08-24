import pytest

from betfair_trading.football.over_1_5_scalp.config import DEFAULT_CONFIG, Over15ScalpConfig
from betfair_trading.football.over_1_5_scalp.risk import (
    compute_first_entry_stake,
    compute_second_entry_stake,
    compute_stake_plan,
    max_match_exposure,
)
from betfair_trading.risk.limits import RiskLimits

DEFAULT_RISK_LIMITS = RiskLimits()


def test_spec_worked_example_20_pound_match_exposure():
    # bankroll £2000, 1% max_bankroll_risk -> £20 match exposure, exactly
    # the spec's own worked example (30-min entry ~£10, 50-min up to ~£10).
    plan = compute_stake_plan(bankroll=2000.0, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)
    assert plan.max_match_exposure == 20.0
    assert plan.first_entry_stake == 10.0
    assert plan.second_entry_max_stake == 10.0


def test_50_percent_means_50_percent_of_match_allocation_not_bankroll():
    # bankroll £1000 -> match exposure is £10 (1%), first entry £5.
    # Must NEVER be anywhere near "50% of £1000" (£500).
    bankroll = 1000.0
    stake = compute_first_entry_stake(bankroll, DEFAULT_CONFIG, DEFAULT_RISK_LIMITS)
    assert stake == 5.0
    assert stake < bankroll * 0.01  # nowhere close to touching bankroll directly


def test_strategy_cap_is_capped_by_platform_wide_football_correlation_limit():
    # A misconfigured strategy risk fraction (10%) must not override the
    # platform's own max_correlated_exposure_per_football_match_pct (2.5%
    # by default) -- the stricter limit always wins.
    loose_config = Over15ScalpConfig(max_bankroll_risk=0.10)
    exposure = max_match_exposure(bankroll=1000.0, config=loose_config, risk_limits=DEFAULT_RISK_LIMITS)
    assert exposure == 1000.0 * (DEFAULT_RISK_LIMITS.max_correlated_exposure_per_football_match_pct / 100.0)
    assert exposure == 25.0


def test_strategy_cap_used_when_tighter_than_platform_limit():
    tight_config = Over15ScalpConfig(max_bankroll_risk=0.005)  # 0.5%, tighter than the 2.5% platform cap
    exposure = max_match_exposure(bankroll=1000.0, config=tight_config, risk_limits=DEFAULT_RISK_LIMITS)
    assert exposure == 5.0


def test_rejects_nonpositive_bankroll():
    with pytest.raises(ValueError):
        max_match_exposure(bankroll=0.0, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)
    with pytest.raises(ValueError):
        max_match_exposure(bankroll=-100.0, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)


def test_second_entry_stake_scales_with_fraction():
    full = compute_second_entry_stake(2000.0, second_entry_fraction=0.50, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)
    half = compute_second_entry_stake(2000.0, second_entry_fraction=0.25, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)
    none = compute_second_entry_stake(2000.0, second_entry_fraction=0.0, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)
    assert full == 10.0
    assert half == 5.0
    assert none == 0.0


def test_second_entry_stake_rejects_fraction_exceeding_configured_max():
    with pytest.raises(ValueError):
        compute_second_entry_stake(2000.0, second_entry_fraction=0.9, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)


def test_total_planned_exposure_never_exceeds_match_ceiling():
    plan = compute_stake_plan(bankroll=5000.0, config=DEFAULT_CONFIG, risk_limits=DEFAULT_RISK_LIMITS)
    assert plan.first_entry_stake + plan.second_entry_max_stake <= plan.max_match_exposure + 1e-9


def test_sizing_never_reads_prior_trade_outcomes():
    # No Martingale by construction: the function signature has no way to
    # accept "previous result" -- this test documents/locks that in, since
    # a future edit adding such a parameter would be exactly the mistake
    # to catch in review.
    import inspect

    for fn in (max_match_exposure, compute_first_entry_stake, compute_second_entry_stake, compute_stake_plan):
        params = set(inspect.signature(fn).parameters)
        assert not params & {"previous_loss", "losing_streak", "recent_result", "consecutive_losses"}
