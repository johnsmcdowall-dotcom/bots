"""Probability-quality metrics.

Per the spec: "A model with high classification accuracy but poor
probability calibration must not control position sizing." So every
baseline model in this phase is scored on these, not on raw accuracy —
accuracy says nothing about whether a model's "72%" actually happens 72%
of the time, which is exactly what Kelly-adjacent position sizing
(risk/limits.py, later phases) needs to be true.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

_EPS = 1e-15


def _check_same_length_and_nonempty(predicted: Sequence, outcomes: Sequence) -> None:
    if len(predicted) != len(outcomes):
        raise ValueError(
            f"predicted and outcomes must be the same length, got {len(predicted)} and {len(outcomes)}"
        )
    if not predicted:
        raise ValueError("cannot score an empty sample")


def brier_score(predicted_probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    """Binary Brier score: mean squared error between predicted probability
    and the binary outcome (0 or 1). Lower is better; 0 is perfect, 0.25 is
    what a coin-flip forecaster with an always-0.5 prediction scores against
    a 50/50 base rate.
    """
    _check_same_length_and_nonempty(predicted_probabilities, outcomes)
    return sum((p - y) ** 2 for p, y in zip(predicted_probabilities, outcomes)) / len(outcomes)


def multiclass_brier_score(
    predicted_probability_vectors: Sequence[Sequence[float]], true_class_indices: Sequence[int], n_classes: int
) -> float:
    """Generalisation of the Brier score to a K-class distribution: mean
    squared error between the predicted probability vector and the
    one-hot encoding of the true class.
    """
    _check_same_length_and_nonempty(predicted_probability_vectors, true_class_indices)
    total = 0.0
    for probs, true_class in zip(predicted_probability_vectors, true_class_indices):
        if len(probs) != n_classes:
            raise ValueError(f"expected {n_classes} probabilities, got {len(probs)}")
        for k in range(n_classes):
            target = 1.0 if k == true_class else 0.0
            total += (probs[k] - target) ** 2
    return total / len(predicted_probability_vectors)


def log_loss(predicted_probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    """Binary log loss (cross-entropy). Lower is better. Probabilities are
    clipped away from exactly 0/1 so a single confidently-wrong prediction
    doesn't produce an infinite score.
    """
    _check_same_length_and_nonempty(predicted_probabilities, outcomes)
    total = 0.0
    for p, y in zip(predicted_probabilities, outcomes):
        clipped = min(max(p, _EPS), 1 - _EPS)
        total += -(y * math.log(clipped) + (1 - y) * math.log(1 - clipped))
    return total / len(outcomes)


@dataclass(frozen=True)
class CalibrationBin:
    bin_lower: float
    bin_upper: float
    count: int
    mean_predicted_probability: float | None
    actual_frequency: float | None

    @property
    def calibration_error(self) -> float | None:
        if self.mean_predicted_probability is None or self.actual_frequency is None:
            return None
        return self.mean_predicted_probability - self.actual_frequency


def reliability_table(
    predicted_probabilities: Sequence[float], outcomes: Sequence[int], n_bins: int = 10
) -> tuple[CalibrationBin, ...]:
    """Bucket predictions into `n_bins` equal-width probability bins and
    compare each bin's mean predicted probability against its actual
    outcome frequency — a well-calibrated model has these track closely
    across every bin, not just on average.
    """
    _check_same_length_and_nonempty(predicted_probabilities, outcomes)
    if n_bins < 1:
        raise ValueError("n_bins must be at least 1")

    edges = [i / n_bins for i in range(n_bins + 1)]
    bins = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        is_last_bin = i == n_bins - 1
        in_bin = [
            (p, y)
            for p, y in zip(predicted_probabilities, outcomes)
            if (lo <= p < hi) or (is_last_bin and p == hi)
        ]
        if in_bin:
            mean_p = sum(p for p, _ in in_bin) / len(in_bin)
            freq = sum(y for _, y in in_bin) / len(in_bin)
        else:
            mean_p = None
            freq = None
        bins.append(CalibrationBin(lo, hi, len(in_bin), mean_p, freq))
    return tuple(bins)
