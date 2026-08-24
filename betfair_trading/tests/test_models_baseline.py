import random

import pytest

from betfair_trading.models.baseline import (
    BSPForecastModel,
    NotFittedError,
    ShortHorizonDirectionModel,
    TargetBeforeStopModel,
)
from betfair_trading.models.labels import TICK_BUCKET_LABELS


def _separable_binary_dataset(n=200, seed=0):
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        signal = rng.uniform(-1, 1)
        noise = rng.uniform(-0.2, 0.2)
        label = 1 if signal > 0 else 0
        X.append([signal + noise, rng.uniform(-1, 1)])  # second column is pure noise
        y.append(label)
    return ("signal", "noise"), X, y


# --- TargetBeforeStopModel ---------------------------------------------------

def test_target_before_stop_model_predict_before_fit_raises():
    model = TargetBeforeStopModel()
    with pytest.raises(NotFittedError):
        model.predict_proba([[0.0, 0.0]])


def test_target_before_stop_model_rejects_single_class_training_data():
    model = TargetBeforeStopModel()
    with pytest.raises(ValueError):
        model.fit(("a",), [[0.0], [1.0]], [1, 1])


def test_target_before_stop_model_learns_a_clearly_separable_pattern():
    names, X, y = _separable_binary_dataset()
    train_X, train_y = X[:150], y[:150]
    test_X, test_y = X[150:], y[150:]

    model = TargetBeforeStopModel()
    model.fit(names, train_X, train_y)
    probs = model.predict_proba(test_X)

    assert len(probs) == len(test_X)
    assert all(0.0 <= p <= 1.0 for p in probs)

    evaluation = model.evaluate(test_X, test_y)
    assert evaluation["n_samples"] == len(test_y)
    # A model that actually learned the separable signal should heavily
    # beat a naive always-0.5 forecaster (Brier score 0.25 against a
    # roughly balanced label set).
    assert evaluation["brier_score"] < 0.15


def test_target_before_stop_model_handles_positive_class_absent_at_predict_time():
    # Fit on data containing only class 0 alongside a dummy class-1 row so
    # fit() succeeds, then predict on data where the model still assigns
    # some probability mass to class 1 -- exercise the "1 in classes" branch.
    model = TargetBeforeStopModel()
    model.fit(("x",), [[0.0], [10.0]], [0, 1])
    probs = model.predict_proba([[5.0]])
    assert 0.0 <= probs[0] <= 1.0


# --- ShortHorizonDirectionModel -----------------------------------------------

def _separable_multiclass_dataset(n=300, seed=1):
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        signal = rng.uniform(-5, 5)
        noise = rng.uniform(-0.3, 0.3)
        if signal < -2:
            label = 0
        elif signal < 0:
            label = 3
        elif signal < 2:
            label = 3
        else:
            label = 6
        X.append([signal + noise])
        y.append(label)
    return ("signal",), X, y


def test_short_horizon_model_predict_before_fit_raises():
    model = ShortHorizonDirectionModel(horizon_seconds=5.0)
    with pytest.raises(NotFittedError):
        model.predict_proba([[0.0]])


def test_short_horizon_model_output_shape_covers_all_seven_buckets():
    names, X, y = _separable_multiclass_dataset()
    model = ShortHorizonDirectionModel(horizon_seconds=10.0)
    model.fit(names, X, y)

    probs = model.predict_proba(X[:5])
    assert len(probs) == 5
    for row in probs:
        assert len(row) == len(TICK_BUCKET_LABELS) == 7
        assert round(sum(row), 6) == 1.0  # never-seen buckets get 0, not omitted


def test_short_horizon_model_evaluate_uses_multiclass_brier():
    names, X, y = _separable_multiclass_dataset()
    train_X, train_y = X[:200], y[:200]
    test_X, test_y = X[200:], y[200:]

    model = ShortHorizonDirectionModel(horizon_seconds=10.0)
    model.fit(names, train_X, train_y)
    evaluation = model.evaluate(test_X, test_y)

    assert evaluation["n_samples"] == len(test_y)
    assert evaluation["multiclass_brier_score"] < 1.0  # better than a maximally-wrong forecaster


# --- BSPForecastModel ----------------------------------------------------------

def test_bsp_forecast_model_predict_before_fit_raises():
    model = BSPForecastModel()
    with pytest.raises(NotFittedError):
        model.predict([[0.0]])


def test_bsp_forecast_model_fits_a_linear_relationship():
    rng = random.Random(2)
    X = [[rng.uniform(-10, 10)] for _ in range(100)]
    y = [2.0 * x[0] + rng.uniform(-0.1, 0.1) for x in X]

    model = BSPForecastModel()
    model.fit(("x",), X[:70], y[:70])
    evaluation = model.evaluate(X[70:], y[70:])

    assert evaluation["n_samples"] == 30
    assert evaluation["mean_absolute_tick_error"] < 1.0


def test_bsp_forecast_model_rejects_empty_training_data():
    model = BSPForecastModel()
    with pytest.raises(ValueError):
        model.fit(("x",), [], [])
