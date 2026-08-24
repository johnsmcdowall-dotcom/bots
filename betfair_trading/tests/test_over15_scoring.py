from betfair_trading.football.over_1_5_scalp.config import DEFAULT_CONFIG, Over15ScalpConfig
from betfair_trading.football.over_1_5_scalp.scoring import (
    LiveInputs,
    PrematchInputs,
    live_goal_pressure_score,
    prematch_goal_score,
    second_entry_edge,
    second_entry_fraction,
)


# --- prematch_goal_score -----------------------------------------------

def test_no_inputs_gives_zero_score_not_crash():
    result = prematch_goal_score(PrematchInputs())
    assert result.score == 0.0
    assert result.inputs_used == 0
    assert result.inputs_total == 12


def test_strong_inputs_score_highly():
    inputs = PrematchInputs(
        home_over_1_5_rate=0.85, away_over_1_5_rate=0.85, combined_avg_total_goals=3.5,
        home_scoring_rate=0.85, away_scoring_rate=0.75, zero_zero_ft_rate=0.02,
        second_half_goal_share=0.65, recent_goal_trend=0.5,
    )
    result = prematch_goal_score(inputs)
    assert result.score >= 90.0


def test_weak_inputs_score_lowly():
    inputs = PrematchInputs(
        home_over_1_5_rate=0.40, away_over_1_5_rate=0.40, combined_avg_total_goals=2.0,
        zero_zero_ft_rate=0.20,
    )
    result = prematch_goal_score(inputs)
    assert result.score <= 10.0


def test_missing_inputs_are_excluded_not_defaulted():
    partial = prematch_goal_score(PrematchInputs(home_over_1_5_rate=0.85))
    assert partial.inputs_used == 1
    assert set(partial.component_scores.keys()) == {"home_over_1_5_rate"}


def test_zero_zero_rate_is_inverted_lower_is_better():
    low_zero_zero = prematch_goal_score(PrematchInputs(zero_zero_ft_rate=0.02))
    high_zero_zero = prematch_goal_score(PrematchInputs(zero_zero_ft_rate=0.20))
    assert low_zero_zero.score > high_zero_zero.score


def test_sample_size_flagged_inadequate_when_below_minimum():
    result = prematch_goal_score(PrematchInputs(sample_size_home=3, sample_size_away=20), min_sample_size=10)
    assert result.sample_size_adequate is False


def test_sample_size_adequate_when_both_meet_minimum():
    result = prematch_goal_score(PrematchInputs(sample_size_home=15, sample_size_away=20), min_sample_size=10)
    assert result.sample_size_adequate is True


def test_unreliable_competition_flagged():
    result = prematch_goal_score(PrematchInputs(competition_reliable=False))
    assert result.competition_excluded is True


def test_score_bounded_0_to_100():
    extreme = prematch_goal_score(PrematchInputs(combined_avg_total_goals=10.0, home_over_1_5_rate=1.0))
    assert 0.0 <= extreme.score <= 100.0


# --- live_goal_pressure_score --------------------------------------------

def test_high_pressure_inputs_score_highly():
    inputs = LiveInputs(minute=30, total_shots=12, shots_on_target=4, xg=1.2, dangerous_attacks=60, big_chances=3)
    result = live_goal_pressure_score(inputs)
    assert result.score >= 90.0


def test_low_pressure_inputs_score_lowly():
    inputs = LiveInputs(minute=30, total_shots=3, shots_on_target=0, xg=0.3)
    result = live_goal_pressure_score(inputs)
    assert result.score <= 10.0


def test_live_score_missing_all_optional_inputs_is_zero():
    result = live_goal_pressure_score(LiveInputs(minute=30))
    assert result.score == 0.0
    assert result.inputs_used == 0


# --- second_entry_edge / second_entry_fraction ----------------------------

def test_edge_matches_spec_formula():
    edge = second_entry_edge(model_probability_two_plus_goals=0.75, back_odds=1.50)
    assert round(edge, 6) == round(0.75 - (1 / 1.50), 6)


def test_negative_edge_gets_no_second_entry():
    assert second_entry_fraction(edge=-0.02, live_pressure_score=90.0, config=DEFAULT_CONFIG) == 0.0


def test_edge_below_minimum_gets_no_second_entry():
    config = Over15ScalpConfig(min_second_entry_edge=0.04)
    assert second_entry_fraction(edge=0.02, live_pressure_score=90.0, config=config) == 0.0


def test_strong_edge_and_pressure_gets_full_remaining_allocation():
    config = Over15ScalpConfig(min_second_entry_edge=0.04, second_entry_max_fraction=0.5, min_live_pressure_score=65.0)
    fraction = second_entry_fraction(edge=0.10, live_pressure_score=80.0, config=config)
    assert fraction == config.second_entry_max_fraction


def test_medium_edge_gets_half_of_max_fraction():
    config = Over15ScalpConfig(min_second_entry_edge=0.04, second_entry_max_fraction=0.5, min_live_pressure_score=65.0)
    # clears the minimum but not the "strong" threshold (1.5x minimum)
    fraction = second_entry_fraction(edge=0.045, live_pressure_score=80.0, config=config)
    assert fraction == config.second_entry_max_fraction * 0.5


def test_strong_edge_but_weak_pressure_only_gets_medium_allocation():
    config = Over15ScalpConfig(min_second_entry_edge=0.04, second_entry_max_fraction=0.5, min_live_pressure_score=65.0)
    fraction = second_entry_fraction(edge=0.10, live_pressure_score=30.0, config=config)
    assert fraction == config.second_entry_max_fraction * 0.5
