"""Baseline probability models — Phase 4.

- labels.py: forward-looking label construction (HORSE MODEL 1/2/8) — the
  only place in the platform allowed to look at future price data.
- calibration.py: Brier score, log loss, reliability tables. Every model
  here is scored on these, not raw accuracy.
- dataset.py: feature+label assembly and the chronological (never
  shuffled) TRAIN/VALIDATION/TEST market split.
- baseline.py: the interpretable baseline models themselves (logistic/
  ridge regression), each outputting probabilities, never buy/sell labels.
- train.py: train_baseline_models() — orchestrates all of the above.

Not exercised against real historical horse-racing data in this
environment (see train.py's docstring) — this phase built and proved the
machinery correct on synthetic data. Running it against real markets and
reporting what it actually finds is future work.
"""

from betfair_trading.models.train import TrainingReport, train_baseline_models

__all__ = ["TrainingReport", "train_baseline_models"]
