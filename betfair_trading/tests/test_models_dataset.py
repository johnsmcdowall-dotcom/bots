from datetime import datetime, timedelta, timezone

import pytest

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.models.dataset import (
    build_labelled_rows,
    chronological_market_split,
    to_model_matrix,
)
from betfair_trading.models.labels import CANONICAL_TARGET_STOP_CONFIGS


def _runner(selection_id: str, price: float) -> RunnerLadder:
    return RunnerLadder(
        selection_id=selection_id, status=RunnerStatus.ACTIVE,
        back=(PriceLevel(price, 50.0),), lay=(PriceLevel(price + 0.02, 40.0),),
        last_traded_price=price, total_matched=100.0,
    )


def _snapshot(market_id, ts, r1, r2) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
        total_matched=200.0, runners=(_runner("1", r1), _runner("2", r2)),
    )


def _register_and_record(store, market_id, scheduled_start, prices):
    store.write_race_reference(
        market_id=market_id, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=scheduled_start,
        runners=[("1", "Horse A", 1), ("2", "Horse B", 2)],
    )
    for i, (r1, r2) in enumerate(prices):
        ts = scheduled_start - timedelta(seconds=(len(prices) - i) * 5)
        store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(market_id, ts, r1, r2))


# --- build_labelled_rows ----------------------------------------------------

def test_build_labelled_rows_produces_labels_for_every_feature_row(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    scheduled_start = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)
    _register_and_record(store, "1.1", scheduled_start, [(4.0, 4.0), (3.9, 4.05), (3.6, 4.1)])

    rows = build_labelled_rows(store, "1.1", short_horizons=(5.0,), target_stop_configs=CANONICAL_TARGET_STOP_CONFIGS[:2])

    assert len(rows) == 6  # 3 snapshots x 2 runners
    first = rows[0]
    assert 5.0 in first.short_horizon
    assert len(first.target_before_stop) == 2
    assert first.closing_price is not None
    store.close()


def test_last_row_has_no_future_data_for_short_horizon(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    scheduled_start = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)
    _register_and_record(store, "1.1", scheduled_start, [(4.0, 4.0), (3.9, 4.05), (3.6, 4.1)])

    rows = build_labelled_rows(store, "1.1", short_horizons=(60.0,))
    runner1_rows = sorted((r for r in rows if r.feature_row.selection_id == "1"), key=lambda r: r.feature_row.timestamp)
    assert runner1_rows[-1].short_horizon[60.0].bucket is None  # nothing 60s further into the future exists
    store.close()


# --- chronological_market_split ---------------------------------------------

def test_chronological_split_orders_by_scheduled_start_not_market_id(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    base = datetime(2026, 3, 1, 14, 0, 0, tzinfo=timezone.utc)
    # IDs deliberately out of scheduled order -- market_id order must not matter.
    _register_and_record(store, "1.9", base, [(4.0, 4.0)])
    _register_and_record(store, "1.1", base + timedelta(minutes=30), [(4.0, 4.0)])
    _register_and_record(store, "1.5", base + timedelta(minutes=60), [(4.0, 4.0)])
    _register_and_record(store, "1.7", base + timedelta(minutes=90), [(4.0, 4.0)])
    _register_and_record(store, "1.3", base + timedelta(minutes=120), [(4.0, 4.0)])

    split = chronological_market_split(store, ["1.1", "1.5", "1.9", "1.7", "1.3"])  # default 0.6/0.2 fractions

    assert split.train_market_ids == ("1.9", "1.1", "1.5")
    assert split.validation_market_ids == ("1.7",)
    assert split.test_market_ids == ("1.3",)
    store.close()


def test_chronological_split_missing_reference_raises(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    with pytest.raises(ValueError, match="no race_reference"):
        chronological_market_split(store, ["nope"])
    store.close()


def test_chronological_split_invalid_fractions_raise(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    with pytest.raises(ValueError):
        chronological_market_split(store, [], train_fraction=0.7, validation_fraction=0.4)
    store.close()


# --- to_model_matrix ---------------------------------------------------------

def test_to_model_matrix_empty_input():
    assert to_model_matrix([]) == ((), [], ())


def test_to_model_matrix_one_hot_encodes_regime_and_drops_identifiers(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    scheduled_start = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)
    _register_and_record(store, "1.1", scheduled_start, [(4.0, 4.0), (3.9, 4.05)])

    from betfair_trading.features.pipeline import build_feature_table
    rows = build_feature_table(store, "1.1")

    columns, X, kept = to_model_matrix(rows)

    assert "market_id" not in columns
    assert "selection_id" not in columns
    assert "timestamp" not in columns
    assert "time_to_off_regime" not in columns
    assert any(c.startswith("regime_") for c in columns)
    assert len(X) == sum(kept)
    for row_values in X:
        assert all(isinstance(v, float) for v in row_values)
    store.close()


def test_to_model_matrix_drops_rows_with_missing_features(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    scheduled_start = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)
    # First snapshot: rolling features for longer windows will be None
    # (only 1 observation so far) for at least the acceleration features.
    _register_and_record(store, "1.1", scheduled_start, [(4.0, 4.0)])

    from betfair_trading.features.pipeline import build_feature_table
    rows = build_feature_table(store, "1.1")

    _, _, kept = to_model_matrix(rows)
    assert not all(kept)  # the single-snapshot rows should have missing velocity/acceleration features
    store.close()
