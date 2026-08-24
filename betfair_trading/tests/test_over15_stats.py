import math
from datetime import datetime, timedelta, timezone

from betfair_trading.football.over_1_5_scalp.state import TradeStatus
from betfair_trading.football.over_1_5_scalp.stats import (
    CompletedTrade,
    compute_league_stats,
    compute_time_band_stats,
    time_band_for_minute,
)

DAY0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _trade(
    league="EPL", kickoff=DAY0, first_entry_price=1.8, exit_price=1.2, goal_minute=32.0,
    total_staked=10.0, net_profit_loss=5.0,
) -> CompletedTrade:
    return CompletedTrade(
        match_id="m", league=league, kickoff=kickoff, prematch_score=80.0,
        first_entry_minute=30.0, first_entry_price=first_entry_price, first_entry_stake=total_staked,
        second_entry_taken=False, second_entry_price=None, second_entry_stake=None, second_entry_edge=None,
        goal_minute=goal_minute, exit_status=TradeStatus.CLOSED_PROFIT, exit_reason="greened",
        exit_price=exit_price, total_staked=total_staked, gross_profit_loss=net_profit_loss,
        commission_paid=0.0, net_profit_loss=net_profit_loss,
    )


def test_league_stats_hand_worked_example():
    trades = [
        _trade(kickoff=DAY0, first_entry_price=1.8, exit_price=1.2, goal_minute=32.0, total_staked=10.0, net_profit_loss=5.0),
        _trade(kickoff=DAY0 + timedelta(days=1), first_entry_price=1.7, exit_price=None, goal_minute=None, total_staked=10.0, net_profit_loss=-10.0),
        _trade(kickoff=DAY0 + timedelta(days=2), first_entry_price=1.9, exit_price=1.25, goal_minute=52.0, total_staked=15.0, net_profit_loss=8.0),
    ]

    stats = compute_league_stats(trades)["EPL"]

    assert stats.trades == 3
    assert stats.wins == 2
    assert stats.losses == 1
    assert round(stats.strike_rate, 6) == round(2 / 3, 6)
    assert round(stats.avg_entry_odds, 6) == 1.8
    assert round(stats.avg_exit_odds, 6) == round((1.2 + 1.25) / 2, 6)
    assert round(stats.roi, 6) == round(3.0 / 35.0, 6)
    assert round(stats.profit_factor, 6) == round(13.0 / 10.0, 6)
    assert round(stats.avg_pnl, 6) == 1.0
    assert round(stats.avg_goal_minute, 6) == 42.0
    assert round(stats.max_drawdown, 6) == -10.0
    expected_expectancy = (0.5 + (-1.0) + (8.0 / 15.0)) / 3
    assert round(stats.expectancy, 6) == round(expected_expectancy, 6)
    assert stats.sharpe_like is not None and stats.sharpe_like > 0


def test_small_sample_never_flagged_regardless_of_expectancy():
    trades = [_trade(net_profit_loss=-10.0) for _ in range(5)]  # all losses, but n=5 < min sample
    stats = compute_league_stats(trades, min_sample_size=20)["EPL"]
    assert stats.avg_pnl < 0
    assert stats.flagged_negative_expectancy is False


def test_large_negative_sample_is_flagged():
    trades = [_trade(kickoff=DAY0 + timedelta(days=i), net_profit_loss=-10.0) for i in range(25)]
    stats = compute_league_stats(trades, min_sample_size=20)["EPL"]
    assert stats.flagged_negative_expectancy is True


def test_large_positive_sample_is_not_flagged():
    trades = [_trade(kickoff=DAY0 + timedelta(days=i), net_profit_loss=10.0) for i in range(25)]
    stats = compute_league_stats(trades, min_sample_size=20)["EPL"]
    assert stats.flagged_negative_expectancy is False


def test_leagues_are_kept_separate():
    trades = [_trade(league="EPL", net_profit_loss=10.0), _trade(league="La Liga", net_profit_loss=-10.0)]
    stats = compute_league_stats(trades)
    assert set(stats.keys()) == {"EPL", "La Liga"}
    assert stats["EPL"].avg_pnl == 10.0
    assert stats["La Liga"].avg_pnl == -10.0


def test_profit_factor_none_when_no_losses():
    trades = [_trade(net_profit_loss=10.0), _trade(net_profit_loss=5.0)]
    stats = compute_league_stats(trades)["EPL"]
    assert stats.profit_factor is None


# --- time bands ----------------------------------------------------------

def test_time_band_boundaries():
    assert time_band_for_minute(30) == "30-35"
    assert time_band_for_minute(35) == "30-35"
    assert time_band_for_minute(36) == "36-40"
    assert time_band_for_minute(45) == "41-45+"
    assert time_band_for_minute(46) == "46-50"
    assert time_band_for_minute(70) == "66-70"
    assert time_band_for_minute(71) == "71+"
    assert time_band_for_minute(120) == "71+"


def test_time_band_below_30_is_none():
    assert time_band_for_minute(10) is None


def test_compute_time_band_stats_buckets_correctly():
    trades = [
        _trade(goal_minute=32.0, net_profit_loss=5.0),
        _trade(goal_minute=33.0, net_profit_loss=7.0),
        _trade(goal_minute=52.0, net_profit_loss=-2.0),
        _trade(goal_minute=None, net_profit_loss=-10.0),  # no goal -- excluded from every band
    ]
    bands = compute_time_band_stats(trades)
    band_30_35 = next(b for b in bands if b.band_label == "30-35")
    band_51_55 = next(b for b in bands if b.band_label == "51-55")
    band_66_70 = next(b for b in bands if b.band_label == "66-70")

    assert band_30_35.goal_count == 2
    assert round(band_30_35.avg_pnl, 6) == 6.0
    assert band_51_55.goal_count == 1
    assert band_51_55.avg_pnl == -2.0
    assert band_66_70.goal_count == 0
    assert band_66_70.avg_pnl is None
