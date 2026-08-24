"""Interpretable baseline models — logistic regression for classification,
ridge regression for the closing-price forecast.

Per the spec: "Begin with interpretable baselines... Only use deep neural
networks if they outperform simpler models genuinely out of sample." That
comparison needs real historical data this environment doesn't have (see
docs/PLAN.md Phase 4 status) — these are the baselines to compare against
once it exists, not a claim that anything more complex has been tried and
lost.

Every model outputs PROBABILITIES (`predict_proba`), never a buy/sell
label, and is scored via models/calibration.py — a model with sharp
classification but rotten calibration must not be allowed to size a
trade later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from sklearn.linear_model import LogisticRegression, Ridge

from betfair_trading.models.calibration import brier_score, log_loss, multiclass_brier_score
from betfair_trading.models.labels import TICK_BUCKET_LABELS


class NotFittedError(RuntimeError):
    pass


def _require_multiple_classes(y: Sequence[int]) -> None:
    if len(set(y)) < 2:
        raise ValueError(
            f"need at least 2 distinct classes to fit a classifier, got {len(set(y))} "
            "(this usually means the training sample is too small or too narrow — "
            "not a reason to fabricate a model that would just predict a constant)"
        )


@dataclass
class ShortHorizonDirectionModel:
    """HORSE MODEL 2: multinomial logistic regression over the 7
    tick-movement buckets (TICK_BUCKET_LABELS)."""

    horizon_seconds: float
    _model: LogisticRegression | None = field(default=None, repr=False)
    feature_names: tuple[str, ...] = ()

    def fit(self, feature_names: tuple[str, ...], X: Sequence[Sequence[float]], y: Sequence[int]) -> None:
        _require_multiple_classes(y)
        self._model = LogisticRegression(max_iter=1000)
        self._model.fit(X, y)
        self.feature_names = tuple(feature_names)

    def predict_proba(self, X: Sequence[Sequence[float]]) -> list[list[float]]:
        if self._model is None:
            raise NotFittedError("call fit() before predict_proba()")
        raw = self._model.predict_proba(X)
        classes = list(self._model.classes_)
        # LogisticRegression only learns classes actually present in the
        # training data; expand back out to the full 7-bucket space (0
        # probability for any bucket never seen in training) so callers
        # can always index by TICK_BUCKET_LABELS position regardless of
        # what the training sample happened to contain.
        full: list[list[float]] = []
        for row in raw:
            probs = [0.0] * len(TICK_BUCKET_LABELS)
            for cls, p in zip(classes, row):
                probs[cls] = p
            full.append(probs)
        return full

    def evaluate(self, X: Sequence[Sequence[float]], y: Sequence[int]) -> dict:
        probs = self.predict_proba(X)
        return {
            "n_samples": len(y),
            "multiclass_brier_score": multiclass_brier_score(probs, y, len(TICK_BUCKET_LABELS)),
        }


@dataclass
class TargetBeforeStopModel:
    """HORSE MODEL 1: binary logistic regression, P(target hit before stop)
    for one (side, target_ticks, stop_ticks, timeout) configuration.
    Trained only on rows that actually resolved (TARGET or STOP) — TIMEOUT
    rows are excluded (see models/train.py), matching the spec's separate
    "probability neither occurs before timeout" estimate rather than
    folding a third outcome into what should be a clean binary target.
    """

    _model: LogisticRegression | None = field(default=None, repr=False)
    feature_names: tuple[str, ...] = ()

    def fit(self, feature_names: tuple[str, ...], X: Sequence[Sequence[float]], y: Sequence[int]) -> None:
        _require_multiple_classes(y)
        self._model = LogisticRegression(max_iter=1000)
        self._model.fit(X, y)
        self.feature_names = tuple(feature_names)

    def predict_proba(self, X: Sequence[Sequence[float]]) -> list[float]:
        if self._model is None:
            raise NotFittedError("call fit() before predict_proba()")
        classes = list(self._model.classes_)
        raw = self._model.predict_proba(X)
        if 1 not in classes:
            return [0.0] * len(X)
        positive_index = classes.index(1)
        return [row[positive_index] for row in raw]

    def evaluate(self, X: Sequence[Sequence[float]], y: Sequence[int]) -> dict:
        probs = self.predict_proba(X)
        return {
            "n_samples": len(y),
            "brier_score": brier_score(probs, y),
            "log_loss": log_loss(probs, y),
        }


@dataclass
class BSPForecastModel:
    """HORSE MODEL 8: ridge regression forecasting the signed tick delta
    to the closing-price proxy (see models/labels.py::closing_price_label
    for why it's a proxy, not real BSP). Evaluated on mean absolute tick
    error — a regression target, not a probability, so calibration metrics
    don't apply here.
    """

    _model: Ridge | None = field(default=None, repr=False)
    feature_names: tuple[str, ...] = ()

    def fit(self, feature_names: tuple[str, ...], X: Sequence[Sequence[float]], y: Sequence[float]) -> None:
        if not y:
            raise ValueError("cannot fit on an empty training sample")
        self._model = Ridge()
        self._model.fit(X, y)
        self.feature_names = tuple(feature_names)

    def predict(self, X: Sequence[Sequence[float]]) -> list[float]:
        if self._model is None:
            raise NotFittedError("call fit() before predict()")
        return [float(v) for v in self._model.predict(X)]

    def evaluate(self, X: Sequence[Sequence[float]], y: Sequence[float]) -> dict:
        predictions = self.predict(X)
        errors = [abs(p - actual) for p, actual in zip(predictions, y)]
        return {
            "n_samples": len(y),
            "mean_absolute_tick_error": sum(errors) / len(errors) if errors else None,
        }
