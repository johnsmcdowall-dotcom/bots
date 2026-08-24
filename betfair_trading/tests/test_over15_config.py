import pytest

from betfair_trading.football.over_1_5_scalp.config import DEFAULT_CONFIG, GoalExitMode, Over15ScalpConfig


def test_default_config_matches_spec_example():
    assert DEFAULT_CONFIG.enabled is True
    assert DEFAULT_CONFIG.first_entry_minute == 30
    assert DEFAULT_CONFIG.first_entry_window == (28, 35)
    assert DEFAULT_CONFIG.first_entry_fraction == 0.50
    assert DEFAULT_CONFIG.second_entry_minute == 50
    assert DEFAULT_CONFIG.second_entry_window == (47, 53)
    assert DEFAULT_CONFIG.second_entry_max_fraction == 0.50
    assert DEFAULT_CONFIG.hard_exit_minute == 70
    assert DEFAULT_CONFIG.min_prematch_score == 70
    assert DEFAULT_CONFIG.min_live_pressure_score == 65
    assert DEFAULT_CONFIG.min_second_entry_edge == 0.04
    assert DEFAULT_CONFIG.max_bankroll_risk == 0.01
    assert DEFAULT_CONFIG.goal_exit_mode is GoalExitMode.IMMEDIATE_GREEN
    assert DEFAULT_CONFIG.require_score_0_0 is True
    assert DEFAULT_CONFIG.enable_pressure_decay_exit is True
    assert DEFAULT_CONFIG.enable_red_card_filter is True


def test_from_dict_accepts_exact_spec_shape():
    raw = {
        "enabled": True,
        "first_entry_minute": 30,
        "first_entry_window": [28, 35],
        "first_entry_fraction": 0.50,
        "second_entry_minute": 50,
        "second_entry_window": [47, 53],
        "second_entry_max_fraction": 0.50,
        "hard_exit_minute": 70,
        "min_prematch_score": 70,
        "min_live_pressure_score": 65,
        "min_second_entry_edge": 0.04,
        "max_bankroll_risk": 0.01,
        "goal_exit_mode": "IMMEDIATE_GREEN",
        "require_score_0_0": True,
        "enable_pressure_decay_exit": True,
        "enable_red_card_filter": True,
    }
    config = Over15ScalpConfig.from_dict(raw)
    assert config.first_entry_window == (28, 35)
    assert config.goal_exit_mode is GoalExitMode.IMMEDIATE_GREEN


def test_from_dict_rejects_unknown_field():
    with pytest.raises(ValueError, match="unknown"):
        Over15ScalpConfig.from_dict({"not_a_real_field": 1})


def test_rejects_entry_fractions_exceeding_total_allocation():
    with pytest.raises(ValueError):
        Over15ScalpConfig(first_entry_fraction=0.7, second_entry_max_fraction=0.5)


def test_rejects_invalid_window_ordering():
    with pytest.raises(ValueError):
        Over15ScalpConfig(first_entry_window=(35, 28))


def test_rejects_out_of_range_scores():
    with pytest.raises(ValueError):
        Over15ScalpConfig(min_prematch_score=150.0)
    with pytest.raises(ValueError):
        Over15ScalpConfig(min_live_pressure_score=-1.0)


def test_config_is_frozen():
    with pytest.raises(Exception):
        DEFAULT_CONFIG.enabled = False
