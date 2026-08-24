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
from betfair_trading.features.pipeline import build_feature_table
from betfair_trading.features.time_to_off import TimeToOffRegime

MARKET_ID = "1.111"
SCHEDULED_START = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


def _runner(selection_id: str, back_price: float, lay_price: float, ltp: float, total_matched: float) -> RunnerLadder:
    return RunnerLadder(
        selection_id=selection_id,
        status=RunnerStatus.ACTIVE,
        back=(PriceLevel(back_price, 50.0), PriceLevel(back_price - 0.02, 30.0)),
        lay=(PriceLevel(lay_price, 40.0),),
        last_traded_price=ltp,
        total_matched=total_matched,
    )


def _snapshot(ts: datetime, r1_price: float, r2_price: float, r1_matched: float, r2_matched: float) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=MARKET_ID, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
        total_matched=r1_matched + r2_matched,
        runners=(
            _runner("1", r1_price, r1_price + 0.02, r1_price, r1_matched),
            _runner("2", r2_price, r2_price + 0.02, r2_price, r2_matched),
        ),
    )


def _seconds_before_off(n: int) -> datetime:
    return SCHEDULED_START - timedelta(seconds=n)


# A runner ("1") shortens steadily from 4.0 towards 3.5; runner "2" drifts
# slightly. 6 snapshots, 5 seconds apart, all inside the FINAL_10_SEC..60-30s
# regimes for a range of time-to-off values.
_SNAPSHOT_SPECS = [
    (120, 4.0, 4.0, 100.0, 100.0),
    (115, 3.95, 4.05, 150.0, 110.0),
    (110, 3.9, 4.1, 250.0, 120.0),
    (105, 3.8, 4.1, 400.0, 125.0),
    (100, 3.6, 4.2, 700.0, 130.0),
    (95, 3.5, 4.2, 1000.0, 135.0),
]


def _build_synthetic_market(tmp_path, n_snapshots: int) -> SnapshotStore:
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e1", event_name="York", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1), ("2", "Horse B", 2)],
    )
    for spec in _SNAPSHOT_SPECS[:n_snapshots]:
        seconds_before_off, r1_price, r2_price, r1_matched, r2_matched = spec
        snapshot = _snapshot(_seconds_before_off(seconds_before_off), r1_price, r2_price, r1_matched, r2_matched)
        store.write_market_snapshot(Sport.HORSE_RACING, snapshot)
    return store


def test_produces_one_row_per_runner_per_snapshot(tmp_path):
    store = _build_synthetic_market(tmp_path, n_snapshots=6)
    rows = build_feature_table(store, MARKET_ID)
    assert len(rows) == 6 * 2
    store.close()


def test_time_to_off_regime_is_tagged_correctly(tmp_path):
    store = _build_synthetic_market(tmp_path, n_snapshots=1)
    rows = build_feature_table(store, MARKET_ID)
    # snapshot at 120s before off -> MIN_2_TO_1 band (<=120)
    assert all(r.time_to_off_regime == TimeToOffRegime.MIN_2_TO_1 for r in rows)
    store.close()


def test_microstructure_and_book_position_are_populated(tmp_path):
    store = _build_synthetic_market(tmp_path, n_snapshots=1)
    rows = build_feature_table(store, MARKET_ID)
    row1 = next(r for r in rows if r.selection_id == "1")
    row2 = next(r for r in rows if r.selection_id == "2")

    assert row1.microstructure.best_back == 4.0
    assert row1.book_position.market_rank == 1  # tied price, but runner 1 comes first in insertion order
    assert row2.book_position.best_back == 4.0


def test_rolling_features_accumulate_observations_over_snapshots(tmp_path):
    store = _build_synthetic_market(tmp_path, n_snapshots=6)
    rows = build_feature_table(store, MARKET_ID)

    runner1_rows = sorted((r for r in rows if r.selection_id == "1"), key=lambda r: r.timestamp)
    # last row's 60s window should have seen all 6 snapshots (they span 25s)
    last_row = runner1_rows[-1]
    assert last_row.rolling[60.0].observation_count == 6
    # the first row can only have seen itself
    first_row = runner1_rows[0]
    assert first_row.rolling[60.0].observation_count == 1
    assert first_row.rolling[60.0].price_velocity is None


def test_probability_shift_is_none_on_first_snapshot_then_populated(tmp_path):
    store = _build_synthetic_market(tmp_path, n_snapshots=2)
    rows = build_feature_table(store, MARKET_ID)

    runner1_rows = sorted((r for r in rows if r.selection_id == "1"), key=lambda r: r.timestamp)
    assert runner1_rows[0].probability_shift is None
    assert runner1_rows[1].probability_shift is not None
    # runner 1 shortened from 4.0 -> 3.95 while runner 2 drifted -> its
    # normalised probability should have increased.
    assert runner1_rows[1].probability_shift.delta_normalised_probability > 0


def test_missing_race_reference_raises(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    with pytest.raises(ValueError, match="no race_reference"):
        build_feature_table(store, MARKET_ID)
    store.close()


def test_to_flat_dict_produces_prefixed_columns(tmp_path):
    store = _build_synthetic_market(tmp_path, n_snapshots=2)
    rows = build_feature_table(store, MARKET_ID)
    flat = rows[0].to_flat_dict()

    assert flat["market_id"] == MARKET_ID
    assert "micro_best_back" in flat
    assert "book_normalised_probability" in flat
    assert "roll_1s_price_velocity" in flat
    assert "roll_2m_volume_velocity" in flat
    store.close()


def test_no_lookahead_earlier_rows_unaffected_by_later_snapshots(tmp_path):
    """The real guarantee that matters: a feature row computed at time T
    must be bit-for-bit identical whether or not snapshots after T exist
    in storage — proving rolling windows and cross-runner probability
    shifts never see the future.
    """
    store_partial = _build_synthetic_market(tmp_path / "partial", n_snapshots=3)
    store_full = _build_synthetic_market(tmp_path / "full", n_snapshots=6)

    rows_partial = build_feature_table(store_partial, MARKET_ID)
    rows_full = build_feature_table(store_full, MARKET_ID)

    partial_by_key = {(r.selection_id, r.timestamp): r for r in rows_partial}
    full_by_key = {(r.selection_id, r.timestamp): r for r in rows_full}

    for key, partial_row in partial_by_key.items():
        full_row = full_by_key[key]
        assert partial_row.microstructure == full_row.microstructure
        assert partial_row.book_position == full_row.book_position
        assert partial_row.probability_shift == full_row.probability_shift
        assert partial_row.rolling == full_row.rolling

    store_partial.close()
    store_full.close()
