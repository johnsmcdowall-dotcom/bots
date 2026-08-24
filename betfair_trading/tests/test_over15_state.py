from betfair_trading.football.over_1_5_scalp.config import DEFAULT_CONFIG, GoalExitMode, Over15ScalpConfig
from betfair_trading.football.over_1_5_scalp.hedge import BackEntry
from betfair_trading.football.over_1_5_scalp.scoring import AggregateScoreResult, PrematchScoreResult
from betfair_trading.football.over_1_5_scalp.state import (
    DataQuality,
    MarketQuality,
    MatchTradeState,
    RedCardImpact,
    TradeStatus,
    check_data_quality,
    check_market_quality,
    evaluate_first_entry,
    evaluate_no_goal_exit,
    evaluate_pressure_decay_exit,
    evaluate_red_card,
    evaluate_second_entry,
    on_goal_detected,
    qualify_prematch,
)

GOOD_MARKET = MarketQuality(is_open=True, is_suspended=False, liquidity=1000.0, spread_ticks=1)
STRONG_PREMATCH = PrematchScoreResult(score=85.0, component_scores={}, inputs_used=5, inputs_total=12, sample_size_adequate=True, competition_excluded=False)
WEAK_PREMATCH = PrematchScoreResult(score=40.0, component_scores={}, inputs_used=5, inputs_total=12, sample_size_adequate=True, competition_excluded=False)
STRONG_LIVE = AggregateScoreResult(score=80.0, component_scores={}, inputs_used=5, inputs_total=12)
WEAK_LIVE = AggregateScoreResult(score=30.0, component_scores={}, inputs_used=5, inputs_total=12)


# --- check_market_quality ---------------------------------------------------

def test_market_quality_passes_when_all_good():
    decision = check_market_quality(GOOD_MARKET, DEFAULT_CONFIG)
    assert decision.approved


def test_market_quality_rejects_closed_market():
    market = MarketQuality(is_open=False, is_suspended=False, liquidity=1000.0, spread_ticks=1)
    decision = check_market_quality(market, DEFAULT_CONFIG)
    assert not decision.approved
    assert decision.status is TradeStatus.NO_TRADE


def test_market_quality_rejects_var_pending():
    market = MarketQuality(is_open=True, is_suspended=False, liquidity=1000.0, spread_ticks=1, awaiting_var=True)
    decision = check_market_quality(market, DEFAULT_CONFIG)
    assert not decision.approved
    assert "VAR" in decision.reason


def test_market_quality_rejects_low_liquidity():
    market = MarketQuality(is_open=True, is_suspended=False, liquidity=10.0, spread_ticks=1)
    decision = check_market_quality(market, DEFAULT_CONFIG)
    assert not decision.approved
    assert "liquidity" in decision.reason


def test_market_quality_rejects_wide_spread():
    market = MarketQuality(is_open=True, is_suspended=False, liquidity=1000.0, spread_ticks=10)
    decision = check_market_quality(market, DEFAULT_CONFIG)
    assert not decision.approved


# --- check_data_quality -----------------------------------------------------

def test_data_quality_passes_when_clean():
    assert check_data_quality(DataQuality()).approved


def test_data_quality_rejects_stale():
    decision = check_data_quality(DataQuality(stale=True))
    assert not decision.approved
    assert decision.status is TradeStatus.NO_TRADE


def test_data_quality_rejects_conflicting_sources():
    decision = check_data_quality(DataQuality(conflicting_sources=True))
    assert not decision.approved


# --- evaluate_red_card -------------------------------------------------------

def test_red_card_decreasing_expected_goals_forces_exit():
    decision = evaluate_red_card(RedCardImpact.DECREASES_EXPECTED_GOALS, DEFAULT_CONFIG)
    assert not decision.approved
    assert decision.status is TradeStatus.EARLY_EXIT


def test_red_card_uncertain_blocks_entry_without_forcing_exit():
    decision = evaluate_red_card(RedCardImpact.UNCERTAIN, DEFAULT_CONFIG)
    assert not decision.approved
    assert decision.status is TradeStatus.NO_TRADE  # blocks new entry, not EARLY_EXIT


def test_red_card_increasing_expected_goals_does_not_block():
    decision = evaluate_red_card(RedCardImpact.INCREASES_EXPECTED_GOALS, DEFAULT_CONFIG)
    assert decision.approved


def test_red_card_filter_can_be_disabled():
    config = Over15ScalpConfig(enable_red_card_filter=False)
    decision = evaluate_red_card(RedCardImpact.DECREASES_EXPECTED_GOALS, config)
    assert decision.approved


# --- qualify_prematch --------------------------------------------------------

def test_qualify_prematch_approves_strong_score():
    assert qualify_prematch(STRONG_PREMATCH, DEFAULT_CONFIG).approved


def test_qualify_prematch_rejects_weak_score():
    decision = qualify_prematch(WEAK_PREMATCH, DEFAULT_CONFIG)
    assert not decision.approved
    assert "prematch_goal_score" in decision.reason


def test_qualify_prematch_rejects_excluded_competition():
    excluded = PrematchScoreResult(score=95.0, component_scores={}, inputs_used=5, inputs_total=12, sample_size_adequate=True, competition_excluded=True)
    decision = qualify_prematch(excluded, DEFAULT_CONFIG)
    assert not decision.approved
    assert "competition" in decision.reason


def test_qualify_prematch_rejects_inadequate_sample():
    small_sample = PrematchScoreResult(score=95.0, component_scores={}, inputs_used=5, inputs_total=12, sample_size_adequate=False, competition_excluded=False)
    decision = qualify_prematch(small_sample, DEFAULT_CONFIG)
    assert not decision.approved
    assert "sample size" in decision.reason


# --- evaluate_first_entry ----------------------------------------------------

def test_first_entry_approved_when_everything_aligns():
    decision = evaluate_first_entry(30, 0, 0, STRONG_PREMATCH, STRONG_LIVE, GOOD_MARKET, DEFAULT_CONFIG)
    assert decision.approved
    assert decision.status is TradeStatus.ENTRY_1


def test_first_entry_rejects_outside_window():
    decision = evaluate_first_entry(15, 0, 0, STRONG_PREMATCH, STRONG_LIVE, GOOD_MARKET, DEFAULT_CONFIG)
    assert not decision.approved
    assert decision.status is TradeStatus.WAITING_FOR_30


def test_first_entry_rejects_nonzero_score():
    decision = evaluate_first_entry(30, 1, 0, STRONG_PREMATCH, STRONG_LIVE, GOOD_MARKET, DEFAULT_CONFIG)
    assert not decision.approved
    assert "0-0" in decision.reason


def test_first_entry_rejects_weak_live_pressure():
    decision = evaluate_first_entry(30, 0, 0, STRONG_PREMATCH, WEAK_LIVE, GOOD_MARKET, DEFAULT_CONFIG)
    assert not decision.approved
    assert "live_goal_pressure_score" in decision.reason


def test_first_entry_never_enters_without_market_quality():
    bad_market = MarketQuality(is_open=True, is_suspended=True, liquidity=1000.0, spread_ticks=1)
    decision = evaluate_first_entry(30, 0, 0, STRONG_PREMATCH, STRONG_LIVE, bad_market, DEFAULT_CONFIG)
    assert not decision.approved


# --- evaluate_second_entry ----------------------------------------------------

def test_second_entry_approved_with_sufficient_edge():
    decision = evaluate_second_entry(50, 0, 0, STRONG_LIVE, edge=0.06, market=GOOD_MARKET, config=DEFAULT_CONFIG)
    assert decision.approved
    assert decision.status is TradeStatus.SECOND_ENTRY_APPROVED


def test_second_entry_rejected_insufficient_edge():
    decision = evaluate_second_entry(50, 0, 0, STRONG_LIVE, edge=0.01, market=GOOD_MARKET, config=DEFAULT_CONFIG)
    assert not decision.approved
    assert decision.status is TradeStatus.SECOND_ENTRY_REJECTED
    assert "edge" in decision.reason


def test_second_entry_rejected_if_goal_already_happened():
    decision = evaluate_second_entry(50, 1, 0, STRONG_LIVE, edge=0.10, market=GOOD_MARKET, config=DEFAULT_CONFIG)
    assert not decision.approved


def test_second_entry_never_auto_enters_just_because_clock_reached_50():
    # The spec's explicit rule: reaching minute 50 alone must NEVER be
    # sufficient -- only a real edge is.
    borderline_live = AggregateScoreResult(score=66.0, component_scores={}, inputs_used=5, inputs_total=12)
    decision = evaluate_second_entry(50, 0, 0, borderline_live, edge=0.0, market=GOOD_MARKET, config=DEFAULT_CONFIG)
    assert not decision.approved


# --- goal / no-goal exits -----------------------------------------------------

def test_on_goal_detected_immediate_mode():
    decision = on_goal_detected(DEFAULT_CONFIG)
    assert decision.approved
    assert decision.status is TradeStatus.GOAL_DETECTED
    assert "directly" in decision.reason


def test_on_goal_detected_dynamic_mode():
    config = Over15ScalpConfig(goal_exit_mode=GoalExitMode.DYNAMIC_GREEN)
    decision = on_goal_detected(config)
    assert "dynamic" in decision.reason.lower()


def test_no_goal_exit_triggers_at_hard_exit_minute():
    decision = evaluate_no_goal_exit(70, 0, 0, DEFAULT_CONFIG)
    assert decision.approved
    assert decision.status is TradeStatus.HARD_TIME_EXIT


def test_no_goal_exit_does_not_trigger_before_hard_exit_minute():
    decision = evaluate_no_goal_exit(65, 0, 0, DEFAULT_CONFIG)
    assert not decision.approved


def test_no_goal_exit_not_applicable_once_a_goal_exists():
    decision = evaluate_no_goal_exit(75, 1, 0, DEFAULT_CONFIG)
    assert not decision.approved
    assert "already occurred" in decision.reason


def test_pressure_decay_exit_triggers_below_threshold():
    decision = evaluate_pressure_decay_exit(current_live_score=20.0, decay_threshold=40.0, config=DEFAULT_CONFIG)
    assert decision.approved
    assert decision.status is TradeStatus.EARLY_EXIT


def test_pressure_decay_exit_disabled_by_config():
    config = Over15ScalpConfig(enable_pressure_decay_exit=False)
    decision = evaluate_pressure_decay_exit(current_live_score=1.0, decay_threshold=40.0, config=config)
    assert not decision.approved


# --- MatchTradeState ----------------------------------------------------------

def test_match_trade_state_apply_and_log():
    state = MatchTradeState(match_id="m1", league="Premier League")
    decision = qualify_prematch(STRONG_PREMATCH, DEFAULT_CONFIG)
    state.apply(decision)

    assert state.status is TradeStatus.QUALIFIED
    assert len(state.log) == 1
    assert state.log[0] == (TradeStatus.QUALIFIED, decision.reason)


def test_match_trade_state_tracks_entries_and_total_stake():
    state = MatchTradeState(match_id="m1", league="Premier League")
    state.add_entry(BackEntry(10.0, 1.8))
    state.add_entry(BackEntry(10.0, 1.3))
    assert state.total_matched_stake == 20.0


def test_match_trade_state_is_closed_property():
    state = MatchTradeState(match_id="m1", league="Premier League")
    assert not state.is_closed
    state.apply(evaluate_no_goal_exit(70, 0, 0, DEFAULT_CONFIG))
    assert state.is_closed
