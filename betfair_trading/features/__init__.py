"""Shared market-microstructure feature computation — Phase 3.

- microstructure.py: instantaneous per-runner order-book features
- rolling.py: time-windowed features (1s-5min) from a runner's price/volume history
- cross_runner.py: race-level (all-runners-at-once) book/probability features
- time_to_off.py: TIME_TO_OFF_REGIME tagging
- pipeline.py: build_feature_table() — assembles all of the above into one
  per-runner, per-snapshot feature table for a recorded market

Every feature added here must be shown (permutation importance/ablation)
to add genuine out-of-sample value before it feeds a model — that check
happens in Phase 4, once baseline models exist to ablate against; this
phase only builds and unit-tests the computation itself.
"""

from betfair_trading.features.pipeline import FeatureRow, build_feature_table, extract_price_points, rows_to_dicts

__all__ = ["FeatureRow", "build_feature_table", "extract_price_points", "rows_to_dicts"]
