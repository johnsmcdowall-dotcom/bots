"""Assembles the full per-runner, per-snapshot feature table for one
recorded horse-racing market — the practical artifact Phase 4 (baseline
models) consumes.

Goes through `backtesting.replay.ReplayEngine` rather than reading
`SnapshotStore` with an ad-hoc filter, per docs/ARCHITECTURE.md's
no-look-ahead rule for research code. Rolling-window state
(`points_by_selection`) is built up strictly in replay order, and each
runner's own current-timestamp point is appended *before* that row's
rolling features are computed — so a window is always computed over
"everything known up to and including now", never anything after.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Sequence

from betfair_trading.backtesting.replay import ReplayEngine, market_snapshot_stream
from betfair_trading.betfair.models import MarketSnapshot
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.cross_runner import RaceBook, RunnerBookPosition, build_race_book, probability_shifts
from betfair_trading.features.microstructure import MicrostructureFeatures, compute_microstructure
from betfair_trading.features.rolling import (
    DEFAULT_WINDOW_SECONDS,
    PricePoint,
    RollingFeatures,
    compute_rolling_features,
)
from betfair_trading.features.rolling import price_proxy as compute_price_proxy
from betfair_trading.features.time_to_off import TimeToOffRegime, classify


def _window_label(seconds: float) -> str:
    if seconds < 120:
        return f"{int(seconds)}s"
    return f"{int(seconds // 60)}m"


@dataclass(frozen=True)
class FeatureRow:
    market_id: str
    selection_id: str
    timestamp: datetime
    time_to_off_regime: TimeToOffRegime
    microstructure: MicrostructureFeatures
    book_position: RunnerBookPosition
    probability_shift: Any  # features.cross_runner.ProbabilityShift | None
    rolling: dict[float, RollingFeatures]

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten into a single dict — one row of a training/research
        dataframe. Nested dataclass fields are prefixed (micro_, book_,
        roll_<window>_) so column names are unambiguous once everything
        lands in the same table.
        """
        row: dict[str, Any] = {
            "market_id": self.market_id,
            "selection_id": self.selection_id,
            "timestamp": self.timestamp,
            "time_to_off_regime": self.time_to_off_regime.value,
        }
        row.update(
            {f"micro_{k}": v for k, v in asdict(self.microstructure).items() if k != "selection_id"}
        )
        row.update(
            {f"book_{k}": v for k, v in asdict(self.book_position).items() if k != "selection_id"}
        )
        if self.probability_shift is not None:
            row["prob_shift_delta_normalised_probability"] = self.probability_shift.delta_normalised_probability
            row["prob_shift_field_relative_delta"] = self.probability_shift.field_relative_delta
        else:
            row["prob_shift_delta_normalised_probability"] = None
            row["prob_shift_field_relative_delta"] = None
        for window_seconds, rolling_features in self.rolling.items():
            suffix = _window_label(window_seconds)
            for k, v in asdict(rolling_features).items():
                if k == "window_seconds":
                    continue
                row[f"roll_{suffix}_{k}"] = v
        return row


def rows_to_dicts(rows: Sequence[FeatureRow]) -> list[dict[str, Any]]:
    return [row.to_flat_dict() for row in rows]


def _iter_snapshots(store: SnapshotStore, market_id: str):
    """Shared replay iteration for anything in this module or models/
    (label construction) that needs a market's snapshots strictly in
    timestamp order, via the no-look-ahead replay engine rather than an
    ad-hoc storage query.
    """
    engine = ReplayEngine({"market": market_snapshot_stream(store, market_id)})
    for event in engine:
        yield event.payload


def extract_price_points(store: SnapshotStore, market_id: str) -> dict[str, list[PricePoint]]:
    """The per-selection PricePoint series for a whole recorded market —
    the same series `build_feature_table` accumulates internally for its
    rolling features, exposed so models/labels.py can build forward-
    looking training labels from *exactly* the same price history a live
    feature computation would have seen, via the shared `price_proxy`
    definition (features/rolling.py) rather than a second, possibly
    diverging, notion of "the price".
    """
    points_by_selection: dict[str, list[PricePoint]] = defaultdict(list)
    for snapshot in _iter_snapshots(store, market_id):
        for runner in snapshot.runners:
            price = compute_price_proxy(runner)
            if price is None:
                continue
            points_by_selection[runner.selection_id].append(
                PricePoint(snapshot.timestamp, price, runner.total_matched)
            )
    return points_by_selection


def build_feature_table(
    store: SnapshotStore,
    market_id: str,
    windows: Sequence[float] = DEFAULT_WINDOW_SECONDS,
) -> list[FeatureRow]:
    race_reference = store.read_race_reference(market_id)
    if race_reference is None:
        raise ValueError(
            f"no race_reference registered for market_id={market_id!r} — cannot compute "
            "time-to-off regimes. Was this market recorded via HorseRacingRecorder "
            "(which registers reference data before recording)?"
        )
    scheduled_start = race_reference["scheduled_start"]

    points_by_selection: dict[str, list[PricePoint]] = defaultdict(list)
    previous_race_book: RaceBook | None = None
    rows: list[FeatureRow] = []

    for snapshot in _iter_snapshots(store, market_id):
        race_book = build_race_book(snapshot)

        shifts_by_id: dict[str, Any] = {}
        if previous_race_book is not None:
            shifts_by_id = {s.selection_id: s for s in probability_shifts(previous_race_book, race_book)}

        regime = classify(scheduled_start, snapshot.timestamp)

        for runner in snapshot.runners:
            micro = compute_microstructure(runner, snapshot)
            price = compute_price_proxy(runner)
            if price is None:
                continue  # nothing to build a price history point from — skip this runner this snapshot

            points = points_by_selection[runner.selection_id]
            points.append(PricePoint(snapshot.timestamp, price, runner.total_matched))

            rolling = {
                window: compute_rolling_features(points, snapshot.timestamp, window) for window in windows
            }
            book_position = race_book.runner(runner.selection_id)

            rows.append(
                FeatureRow(
                    market_id=market_id,
                    selection_id=runner.selection_id,
                    timestamp=snapshot.timestamp,
                    time_to_off_regime=regime,
                    microstructure=micro,
                    book_position=book_position,
                    probability_shift=shifts_by_id.get(runner.selection_id),
                    rolling=rolling,
                )
            )

        previous_race_book = race_book

    return rows
