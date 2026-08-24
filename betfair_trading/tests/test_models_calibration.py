import math

import pytest

from betfair_trading.models.calibration import (
    brier_score,
    log_loss,
    multiclass_brier_score,
    reliability_table,
)


def test_brier_score_perfect_predictions_is_zero():
    assert brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == 0.0


def test_brier_score_always_wrong_is_one():
    assert brier_score([0.0, 1.0], [1, 0]) == 1.0


def test_brier_score_known_value():
    # (0.7-1)^2 + (0.3-0)^2 = 0.09+0.09 = 0.18, /2 = 0.09
    assert round(brier_score([0.7, 0.3], [1, 0]), 6) == 0.09


def test_brier_score_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        brier_score([0.5, 0.5], [1])


def test_brier_score_empty_raises():
    with pytest.raises(ValueError):
        brier_score([], [])


def test_log_loss_perfect_is_near_zero():
    assert log_loss([1.0, 0.0], [1, 0]) < 1e-10


def test_log_loss_confidently_wrong_is_large_but_finite():
    score = log_loss([0.0], [1])
    assert score > 30  # clipped at _EPS, not infinite
    assert math.isfinite(score)


def test_log_loss_known_value():
    # -log(0.7) for outcome 1, symmetric for a well-known case
    expected = -math.log(0.7)
    assert round(log_loss([0.7], [1]), 6) == round(expected, 6)


def test_multiclass_brier_score_perfect_is_zero():
    probs = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert multiclass_brier_score(probs, [0, 1], n_classes=3) == 0.0


def test_multiclass_brier_score_uniform_guess():
    # 3-class uniform guess (1/3 each) against true class 0:
    # (1/3-1)^2 + (1/3-0)^2 + (1/3-0)^2 = 4/9+1/9+1/9 = 6/9
    probs = [[1 / 3, 1 / 3, 1 / 3]]
    assert round(multiclass_brier_score(probs, [0], n_classes=3), 6) == round(6 / 9, 6)


def test_multiclass_brier_score_wrong_vector_length_raises():
    with pytest.raises(ValueError):
        multiclass_brier_score([[0.5, 0.5]], [0], n_classes=3)


def test_reliability_table_bins_and_calibration_error():
    # 10 predictions all at 0.9, 9 of which are correct (outcome=1) -> bin
    # containing 0.9 should show mean_predicted=0.9, actual_frequency=0.9.
    predicted = [0.9] * 10
    outcomes = [1] * 9 + [0]
    table = reliability_table(predicted, outcomes, n_bins=10)

    populated = [b for b in table if b.count > 0]
    assert len(populated) == 1
    bin_ = populated[0]
    assert bin_.count == 10
    assert round(bin_.mean_predicted_probability, 6) == 0.9
    assert round(bin_.actual_frequency, 6) == 0.9
    assert round(bin_.calibration_error, 6) == 0.0


def test_reliability_table_detects_overconfidence():
    # Model always predicts 0.9 but is only right half the time -> badly calibrated.
    predicted = [0.9] * 20
    outcomes = [1, 0] * 10
    table = reliability_table(predicted, outcomes, n_bins=10)
    bin_ = next(b for b in table if b.count > 0)
    assert bin_.calibration_error > 0.3  # predicted much higher than actual


def test_reliability_table_empty_bins_have_none_fields():
    table = reliability_table([0.05], [0], n_bins=10)
    empty_bins = [b for b in table if b.count == 0]
    assert len(empty_bins) == 9
    assert all(b.mean_predicted_probability is None for b in empty_bins)
    assert all(b.calibration_error is None for b in empty_bins)


def test_reliability_table_boundary_value_lands_in_last_bin():
    table = reliability_table([1.0], [1], n_bins=10)
    last_bin = table[-1]
    assert last_bin.count == 1
