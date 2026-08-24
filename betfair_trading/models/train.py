"""Baseline-model training orchestration: chronological TRAIN/VALIDATION
split (docs/PLAN.md's walk-forward discipline), fits every baseline model
(HORSE MODEL 1/2/8), evaluates calibration on VALIDATION data the model
never trained on.

IMPORTANT — not exercised against real historical horse-racing data in
this environment. Phase 2 only built live-recording infrastructure; there
are no live Betfair credentials here to have actually recorded a market,
and no bulk historical import exists yet either. Every mechanic here
(label construction, chronological split, model fitting, calibration
scoring) is proven correct against synthetic data in tests/. Running this
against real markets and reporting what it actually finds — including if
the honest answer is "no usable edge" — is future work, not something to
claim has already happened.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from betfair_trading.database.storage import SnapshotStore
from betfair_trading.models.baseline import BSPForecastModel, ShortHorizonDirectionModel, TargetBeforeStopModel
from betfair_trading.models.dataset import (
    DEFAULT_SHORT_HORIZONS,
    ChronologicalSplit,
    LabelledRow,
    build_labelled_rows,
    chronological_market_split,
    to_model_matrix,
)
from betfair_trading.models.labels import CANONICAL_TARGET_STOP_CONFIGS, TargetBeforeStopOutcome, TargetStopConfig

_SKIPPED_INSUFFICIENT_DATA = {"skipped": "insufficient labelled data or class diversity to fit/evaluate"}


@dataclass(frozen=True)
class TrainingReport:
    split: ChronologicalSplit
    short_horizon_evaluations: dict[float, dict]
    target_before_stop_evaluations: dict[TargetStopConfig, dict]
    bsp_forecast_evaluation: dict


def _labelled_rows_for_markets(
    store: SnapshotStore,
    market_ids: Sequence[str],
    short_horizons: Sequence[float],
    target_stop_configs: Sequence[TargetStopConfig],
) -> list[LabelledRow]:
    rows: list[LabelledRow] = []
    for market_id in market_ids:
        rows.extend(build_labelled_rows(store, market_id, short_horizons, target_stop_configs))
    return rows


def _short_horizon_xy(labelled_rows: Sequence[LabelledRow], horizon: float):
    usable = [lr for lr in labelled_rows if lr.short_horizon[horizon].bucket is not None]
    if not usable:
        return None
    feature_names, X, kept = to_model_matrix([lr.feature_row for lr in usable])
    y = [lr.short_horizon[horizon].bucket for lr, k in zip(usable, kept) if k]
    if not y:
        return None
    return feature_names, X, y


def _target_before_stop_xy(labelled_rows: Sequence[LabelledRow], config: TargetStopConfig):
    usable = [
        lr
        for lr in labelled_rows
        if lr.target_before_stop[config] is not None
        and lr.target_before_stop[config].outcome in (TargetBeforeStopOutcome.TARGET, TargetBeforeStopOutcome.STOP)
    ]
    if not usable:
        return None
    feature_names, X, kept = to_model_matrix([lr.feature_row for lr in usable])
    y = [
        1 if lr.target_before_stop[config].outcome is TargetBeforeStopOutcome.TARGET else 0
        for lr, k in zip(usable, kept)
        if k
    ]
    if not y:
        return None
    return feature_names, X, y


def _bsp_xy(labelled_rows: Sequence[LabelledRow]):
    usable = [lr for lr in labelled_rows if lr.closing_price.tick_delta is not None]
    if not usable:
        return None
    feature_names, X, kept = to_model_matrix([lr.feature_row for lr in usable])
    y = [lr.closing_price.tick_delta for lr, k in zip(usable, kept) if k]
    if not y:
        return None
    return feature_names, X, y


def train_baseline_models(
    store: SnapshotStore,
    market_ids: Sequence[str],
    short_horizons: Sequence[float] = DEFAULT_SHORT_HORIZONS,
    target_stop_configs: Sequence[TargetStopConfig] = CANONICAL_TARGET_STOP_CONFIGS,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> TrainingReport:
    split = chronological_market_split(store, market_ids, train_fraction, validation_fraction)

    train_rows = _labelled_rows_for_markets(store, split.train_market_ids, short_horizons, target_stop_configs)
    validation_rows = _labelled_rows_for_markets(
        store, split.validation_market_ids, short_horizons, target_stop_configs
    )

    short_horizon_evaluations: dict[float, dict] = {}
    for horizon in short_horizons:
        train_data = _short_horizon_xy(train_rows, horizon)
        validation_data = _short_horizon_xy(validation_rows, horizon)
        if train_data is None or validation_data is None or len(set(train_data[2])) < 2:
            short_horizon_evaluations[horizon] = _SKIPPED_INSUFFICIENT_DATA
            continue
        model = ShortHorizonDirectionModel(horizon_seconds=horizon)
        model.fit(train_data[0], train_data[1], train_data[2])
        short_horizon_evaluations[horizon] = model.evaluate(validation_data[1], validation_data[2])

    target_before_stop_evaluations: dict[TargetStopConfig, dict] = {}
    for config in target_stop_configs:
        train_data = _target_before_stop_xy(train_rows, config)
        validation_data = _target_before_stop_xy(validation_rows, config)
        if train_data is None or validation_data is None or len(set(train_data[2])) < 2:
            target_before_stop_evaluations[config] = _SKIPPED_INSUFFICIENT_DATA
            continue
        model = TargetBeforeStopModel()
        model.fit(train_data[0], train_data[1], train_data[2])
        target_before_stop_evaluations[config] = model.evaluate(validation_data[1], validation_data[2])

    bsp_train = _bsp_xy(train_rows)
    bsp_validation = _bsp_xy(validation_rows)
    if bsp_train is None or bsp_validation is None:
        bsp_evaluation = _SKIPPED_INSUFFICIENT_DATA
    else:
        bsp_model = BSPForecastModel()
        bsp_model.fit(bsp_train[0], bsp_train[1], bsp_train[2])
        bsp_evaluation = bsp_model.evaluate(bsp_validation[1], bsp_validation[2])

    return TrainingReport(
        split=split,
        short_horizon_evaluations=short_horizon_evaluations,
        target_before_stop_evaluations=target_before_stop_evaluations,
        bsp_forecast_evaluation=bsp_evaluation,
    )
