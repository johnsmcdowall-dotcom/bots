from datetime import datetime, timedelta, timezone

from betfair_trading.football.over_1_5_scalp.backtest import (
    VERSION_A,
    VERSION_C,
    VERSION_D,
    MatchMinuteSnapshot,
    MatchRecord,
    replay_single_match,
    run_backtest,
    walk_forward_split,
)
from betfair_trading.football.over_1_5_scalp.config import DEFAULT_CONFIG, Over15ScalpConfig
from betfair_trading.football.over_1_5_scalp.hedge import BackEntry, calculate_hedge
from betfair_trading.football.over_1_5_scalp.scoring import LiveInputs, PrematchScoreResult
from betfair_trading.football.over_1_5_scalp.state import MarketQuality, RedCardImpact, TradeStatus
from betfair_trading.risk.limits import RiskLimits

RISK_LIMITS = RiskLimits()
MARKET = MarketQuality(is_open=True, is_suspended=False, liquidity=1000.0, spread_ticks=1)
STRONG_PREMATCH = PrematchScoreResult(score=85.0, component_scores={}, inputs_used=5, inputs_total=12, sample_size_adequate=True, competition_excluded=False)
WEAK_PREMATCH = PrematchScoreResult(score=30.0, component_scores={}, inputs_used=5, inputs_total=12, sample_size_adequate=True, competition_excluded=False)
STRONG_LIVE = LiveInputs(minute=30, total_shots=10, shots_on_target=3, xg=0.9)
WEAK_LIVE = LiveInputs(minute=30, total_shots=2, shots_on_target=0, xg=0.2)


def _match(prematch, snapshots, kickoff=datetime(2026, 1, 1, tzinfo=timezone.utc), league="EPL", match_id="m1"):
    return MatchRecord(match_id, league, kickoff, prematch, tuple(snapshots))


# --- prematch gating differs by version -----------------------------------

def test_version_a_ignores_prematch_filter():
    snapshots = [MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET)]
    match = _match(WEAK_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_A, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.total_staked > 0  # entered despite weak prematch score


def test_version_d_rejects_weak_prematch_score():
    snapshots = [MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET)]
    match = _match(WEAK_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.exit_status is TradeStatus.NO_TRADE
    assert trade.total_staked == 0.0


def test_version_d_rejects_weak_live_pressure_at_first_entry():
    snapshots = [MatchMinuteSnapshot(30, 0, 0, WEAK_LIVE, 1.8, 1.78, MARKET)]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.total_staked == 0.0


# --- goal / hedge outcome ---------------------------------------------------

def test_goal_scored_greens_up_with_correct_hedge_math():
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(40, 1, 0, STRONG_LIVE, 1.15, 1.12, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)

    assert trade.exit_status is TradeStatus.CLOSED_PROFIT
    assert trade.goal_minute == 40
    expected = calculate_hedge([BackEntry(trade.first_entry_stake, trade.first_entry_price)], 1.12, DEFAULT_CONFIG.commission_rate)
    assert round(trade.net_profit_loss, 6) == round(expected.locked_profit_net, 6)


def test_no_entry_before_goal_produces_no_trade_not_a_loss():
    # Goal happens before minute 28 -- the strategy never had a chance to enter.
    snapshots = [MatchMinuteSnapshot(15, 1, 0, STRONG_LIVE, 1.8, 1.78, MARKET)]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.exit_status is TradeStatus.NO_TRADE
    assert trade.total_staked == 0.0


# --- no-goal hard exit ------------------------------------------------------

def test_no_goal_hard_exit_closes_position_at_market_price():
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(70, 0, 0, STRONG_LIVE, 3.5, 3.4, MARKET),  # price drifted against Over 1.5 -- controlled loss
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)

    assert trade.exit_status is TradeStatus.HARD_TIME_EXIT
    assert trade.exit_price == 3.4
    assert trade.net_profit_loss < 0  # a controlled loss, not zero and not catastrophic
    assert trade.net_profit_loss > -trade.total_staked  # never loses more than what was staked


# --- second entry: blind (C) vs EV-gated (D) --------------------------------

def test_version_c_takes_second_entry_blindly_when_still_0_0():
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(50, 0, 0, STRONG_LIVE, 1.4, 1.38, MARKET),
        MatchMinuteSnapshot(60, 1, 0, STRONG_LIVE, 1.1, 1.08, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_C, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.second_entry_taken is True
    assert trade.second_entry_price == 1.4


def test_version_d_skips_second_entry_without_a_model_probability():
    # No model_probability_two_plus_goals supplied on the minute-50 snapshot
    # -> Version D cannot compute an edge, so it must not fabricate one.
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(50, 0, 0, STRONG_LIVE, 1.4, 1.38, MARKET, model_probability_two_plus_goals=None),
        MatchMinuteSnapshot(70, 0, 0, STRONG_LIVE, 1.35, 1.33, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.second_entry_taken is False


def test_version_d_takes_second_entry_when_edge_is_sufficient():
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(50, 0, 0, STRONG_LIVE, 1.5, 1.48, MARKET, model_probability_two_plus_goals=0.75),
        MatchMinuteSnapshot(55, 1, 0, STRONG_LIVE, 1.1, 1.08, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.second_entry_taken is True
    assert trade.second_entry_edge is not None and trade.second_entry_edge > 0


def test_version_d_rejects_second_entry_when_edge_insufficient():
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        # model barely disagrees with market -> edge below min_second_entry_edge
        MatchMinuteSnapshot(50, 0, 0, STRONG_LIVE, 1.5, 1.48, MARKET, model_probability_two_plus_goals=0.68),
        MatchMinuteSnapshot(70, 0, 0, STRONG_LIVE, 1.45, 1.43, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.second_entry_taken is False


# --- red card ----------------------------------------------------------------

def test_red_card_decreasing_goals_forces_early_exit_of_open_position():
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(35, 0, 0, STRONG_LIVE, 1.9, 1.88, MARKET, red_card_impact=RedCardImpact.DECREASES_EXPECTED_GOALS),
        MatchMinuteSnapshot(70, 0, 0, STRONG_LIVE, 2.5, 2.4, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.exit_status is TradeStatus.EARLY_EXIT
    assert trade.exit_price == 1.88  # closed at the red-card minute's price, not waiting until 70


def test_red_card_before_entry_blocks_new_position():
    snapshots = [
        MatchMinuteSnapshot(20, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET, red_card_impact=RedCardImpact.DECREASES_EXPECTED_GOALS),
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.9, 1.88, MARKET),
    ]
    match = _match(STRONG_PREMATCH, snapshots)
    trade = replay_single_match(match, VERSION_D, DEFAULT_CONFIG, 2000.0, RISK_LIMITS)
    assert trade.total_staked == 0.0


# --- run_backtest aggregation ------------------------------------------------

def _winning_match(kickoff, match_id):
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(40, 1, 0, STRONG_LIVE, 1.15, 1.12, MARKET),
    ]
    return _match(STRONG_PREMATCH, snapshots, kickoff=kickoff, match_id=match_id)


def _losing_match(kickoff, match_id):
    snapshots = [
        MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET),
        MatchMinuteSnapshot(70, 0, 0, STRONG_LIVE, 4.0, 3.9, MARKET),
    ]
    return _match(STRONG_PREMATCH, snapshots, kickoff=kickoff, match_id=match_id)


def _no_qualify_match(kickoff, match_id):
    snapshots = [MatchMinuteSnapshot(30, 0, 0, STRONG_LIVE, 1.8, 1.78, MARKET)]
    return _match(WEAK_PREMATCH, snapshots, kickoff=kickoff, match_id=match_id)


def test_run_backtest_aggregates_and_excludes_no_trade_matches():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    matches = [
        _winning_match(base, "w1"),
        _losing_match(base + timedelta(days=1), "l1"),
        _no_qualify_match(base + timedelta(days=2), "n1"),
    ]
    report = run_backtest(matches, VERSION_D, DEFAULT_CONFIG, starting_bankroll=2000.0, risk_limits=RISK_LIMITS)

    assert report.total_trades == 2  # the NO_TRADE match is excluded
    assert report.winning_trades == 1
    assert report.losing_trades == 1
    assert len(report.bankroll_curve) == 2
    # float accumulation order differs (sum of net_pnls vs. running bankroll
    # additions), so compare with tolerance rather than exact equality.
    assert round(report.net_profit, 9) == round(report.bankroll_curve[-1] - 2000.0, 9)


def test_run_backtest_compounds_bankroll_chronologically_not_by_input_order():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Deliberately out of chronological order in the input list.
    matches = [_losing_match(base + timedelta(days=1), "l1"), _winning_match(base, "w1")]
    report = run_backtest(matches, VERSION_D, DEFAULT_CONFIG, starting_bankroll=2000.0, risk_limits=RISK_LIMITS)

    # First processed chronologically must be the winning match (kickoff=base).
    assert report.completed_trades[0].match_id == "w1"
    assert report.completed_trades[1].match_id == "l1"


def test_run_backtest_monthly_returns_grouped_correctly():
    matches = [
        _winning_match(datetime(2026, 1, 15, tzinfo=timezone.utc), "w1"),
        _winning_match(datetime(2026, 2, 15, tzinfo=timezone.utc), "w2"),
    ]
    report = run_backtest(matches, VERSION_D, DEFAULT_CONFIG, starting_bankroll=2000.0, risk_limits=RISK_LIMITS)
    assert set(report.monthly_returns.keys()) == {"2026-01", "2026-02"}


def test_run_backtest_longest_losing_run():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    matches = [
        _losing_match(base, "l1"),
        _losing_match(base + timedelta(days=1), "l2"),
        _winning_match(base + timedelta(days=2), "w1"),
        _losing_match(base + timedelta(days=3), "l3"),
    ]
    report = run_backtest(matches, VERSION_D, DEFAULT_CONFIG, starting_bankroll=2000.0, risk_limits=RISK_LIMITS)
    assert report.longest_losing_run == 2


def test_run_backtest_empty_input():
    report = run_backtest([], VERSION_D, DEFAULT_CONFIG, starting_bankroll=2000.0, risk_limits=RISK_LIMITS)
    assert report.total_trades == 0
    assert report.strike_rate is None
    assert report.roi is None
    assert report.max_drawdown is None


# --- walk_forward_split -------------------------------------------------------

def test_walk_forward_split_is_chronological_never_shuffled():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    matches = [_winning_match(base + timedelta(days=i), f"m{i}") for i in range(10)]
    # feed in reverse order deliberately
    train, test = walk_forward_split(list(reversed(matches)), train_fraction=0.7)

    assert len(train) == 7
    assert len(test) == 3
    assert [m.match_id for m in train] == [f"m{i}" for i in range(7)]
    assert [m.match_id for m in test] == [f"m{i}" for i in range(7, 10)]
    assert max(m.kickoff for m in train) < min(m.kickoff for m in test)
