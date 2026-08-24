"""Dataset assembly: combines Phase 3 feature rows with Phase 4
forward-looking labels, and enforces the walk-forward discipline the spec
requires — "never random-shuffle financial/exchange time series".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.pipeline import FeatureRow, build_feature_table, extract_price_points
from betfair_trading.features.time_to_off import TimeToOffRegime
from betfair_trading.models.labels import (
    CANONICAL_TARGET_STOP_CONFIGS,
    ClosingPriceLabel,
    ShortHorizonLabel,
    TargetBeforeStopLabel,
    TargetStopConfig,
    closing_price_label,
    short_horizon_label,
    target_before_stop_label,
)

DEFAULT_SHORT_HORIZONS: tuple[float, ...] = (1.0, 3.0, 5.0, 10.0, 30.0, 60.0)


@dataclass(frozen=True)
class LabelledRow:
    feature_row: FeatureRow
    short_horizon: dict[float, ShortHorizonLabel]
    target_before_stop: dict[TargetStopConfig, TargetBeforeStopLabel | None]
    closing_price: ClosingPriceLabel


def build_labelled_rows(
    store: SnapshotStore,
    market_id: str,
    short_horizons: Sequence[float] = DEFAULT_SHORT_HORIZONS,
    target_stop_configs: Sequence[TargetStopConfig] = CANONICAL_TARGET_STOP_CONFIGS,
) -> list[LabelledRow]:
    feature_rows = build_feature_table(store, market_id)
    points_by_selection = extract_price_points(store, market_id)

    labelled: list[LabelledRow] = []
    for row in feature_rows:
        points = points_by_selection.get(row.selection_id, [])
        short = {horizon: short_horizon_label(points, row.timestamp, horizon) for horizon in short_horizons}
        target_before_stop = {
            config: target_before_stop_label(
                points, row.timestamp, config.side, config.target_ticks, config.stop_ticks, config.timeout_seconds
            )
            for config in target_stop_configs
        }
        closing = closing_price_label(points, row.timestamp)
        labelled.append(LabelledRow(row, short, target_before_stop, closing))

    return labelled


@dataclass(frozen=True)
class ChronologicalSplit:
    train_market_ids: tuple[str, ...]
    validation_market_ids: tuple[str, ...]
    test_market_ids: tuple[str, ...]


def chronological_market_split(
    store: SnapshotStore,
    market_ids: Sequence[str],
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> ChronologicalSplit:
    """Order markets by scheduled_start (never shuffled) and cut TRAIN /
    VALIDATION / TEST chronologically, so every validation market runs
    strictly after every training market, and every test market strictly
    after every validation market. This is market-level splitting, not
    row-level: two rows from the same race always land in the same split,
    since they're not independent observations.
    """
    if not (0 < train_fraction < 1) or not (0 < validation_fraction < 1) or train_fraction + validation_fraction >= 1:
        raise ValueError("train_fraction and validation_fraction must be in (0, 1) and sum to < 1")

    dated: list[tuple[Any, str]] = []
    for market_id in market_ids:
        reference = store.read_race_reference(market_id)
        if reference is None:
            raise ValueError(f"no race_reference registered for market_id={market_id!r}")
        dated.append((reference["scheduled_start"], market_id))
    dated.sort(key=lambda pair: pair[0])
    ordered_ids = [market_id for _, market_id in dated]

    n = len(ordered_ids)
    train_end = int(n * train_fraction)
    validation_end = train_end + int(n * validation_fraction)

    return ChronologicalSplit(
        train_market_ids=tuple(ordered_ids[:train_end]),
        validation_market_ids=tuple(ordered_ids[train_end:validation_end]),
        test_market_ids=tuple(ordered_ids[validation_end:]),
    )


def _one_hot_regime(regime_value: str) -> dict[str, int]:
    return {f"regime_{regime.value}": (1 if regime.value == regime_value else 0) for regime in TimeToOffRegime}


def to_model_matrix(feature_rows: Sequence[FeatureRow]) -> tuple[tuple[str, ...], list[list[float]], tuple[bool, ...]]:
    """Flatten FeatureRows into a numeric matrix a sklearn model can fit on.

    - `time_to_off_regime` is one-hot encoded (it's the spec's own point
      that regime is not a number to feed a linear-ish model raw).
    - Identifier/timestamp columns are dropped.
    - Only numeric (int/float/bool) columns are kept.
    - Any row with a `None` among the selected columns is DROPPED, not
      imputed — a silently-substituted 0.0 would poison training on a
      feature that legitimately couldn't be computed (e.g. no lay side
      quoted). `kept` tells the caller which input rows survived, in
      order, so labels can be filtered identically.
    """
    if not feature_rows:
        return (), [], ()

    flat_rows: list[dict[str, Any]] = []
    for row in feature_rows:
        flat = row.to_flat_dict()
        flat.update(_one_hot_regime(flat.pop("time_to_off_regime")))
        for identifier in ("market_id", "selection_id", "timestamp"):
            flat.pop(identifier, None)
        flat_rows.append(flat)

    # Column universe = every key that appears (first-seen order), minus any
    # key that ever holds a genuinely non-numeric, non-None value. Crucially
    # this must NOT require a column to be numeric *in the rows scanned* —
    # a column that happens to be None in every row of a small sample (e.g.
    # a rolling-acceleration feature with only 1-2 observations so far) is
    # still a real column whose rows should be dropped by the None-check
    # below, not a column that silently disappears from the schema.
    columns: list[str] = []
    seen: set[str] = set()
    non_numeric: set[str] = set()
    for flat in flat_rows:
        for key, value in flat.items():
            if key not in seen:
                seen.add(key)
                columns.append(key)
            if value is not None and not isinstance(value, (int, float, bool)):
                non_numeric.add(key)
    columns = [c for c in columns if c not in non_numeric]

    X: list[list[float]] = []
    kept: list[bool] = []
    for flat in flat_rows:
        values = [flat.get(col) for col in columns]
        if any(v is None for v in values):
            kept.append(False)
            continue
        kept.append(True)
        X.append([float(v) for v in values])

    return tuple(columns), X, tuple(kept)
