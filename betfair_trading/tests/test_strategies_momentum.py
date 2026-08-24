from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.betfair.ticks import shift_ticks
from betfair_trading.core.interfaces import Side, Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.pipeline import build_feature_table
from betfair_trading.strategies.momentum import (
    DEFAULT_DRIFTER_CONFIGS,
    DEFAULT_STEAMER_CONFIGS,
    DrifterStrategy,
    SteamerStrategy,
    _is_momentum_candidate,
)

MARKET_ID = "1.1"
SCHEDULED_START = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [self.probability] * len(X)


def _runner(selection_id, price, matched):
    return RunnerLadder(
        selection_id=selection_id, status=RunnerStatus.ACTIVE,
        back=(PriceLevel(price, 200.0),), lay=(PriceLevel(shift_ticks(price, 1), 200.0),),
        last_traded_price=price, total_matched=matched,
    )


def _build_race_snapshot_rows(tmp_path, n_snapshots=20, stride=0.5):
    """Runner '1' steadily shortens with growing volume (steamer candidate),
    runner '2' steadily drifts with growing volume (drifter candidate),
    runner '3' stays flat with zero volume growth (candidate for neither).
    Returns the last (richest-history) FeatureRow per runner.
    """
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1), ("2", "Horse B", 2), ("3", "Horse C", 3)],
    )
    p1, p2, p3 = 4.0, 3.0, 5.0
    m1, m2, m3 = 100.0, 100.0, 100.0
    for i in range(n_snapshots):
        ts = SCHEDULED_START - timedelta(seconds=(n_snapshots - i) * stride)
        if i > 0:
            p1 = shift_ticks(p1, -1)
            p2 = shift_ticks(p2, 1)
            m1 += 20.0
            m2 += 20.0
            # p3, m3 unchanged -> flat, no volume growth
        store.write_market_snapshot(
            Sport.HORSE_RACING,
            MarketSnapshot(
                market_id=MARKET_ID, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
                total_matched=m1 + m2 + m3,
                runners=(_runner("1", p1, m1), _runner("2", p2, m2), _runner("3", p3, m3)),
            ),
        )
    rows = build_feature_table(store, MARKET_ID)
    latest = {}
    for row in rows:
        latest[row.selection_id] = row  # last write wins == latest timestamp, since rows are chronological
    return store, latest


def test_is_momentum_candidate_detects_shortening_and_lengthening(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    assert _is_momentum_candidate(rows["1"], 10.0, direction=-1, min_tick_velocity=0.05, max_spread_ticks=1)
    assert not _is_momentum_candidate(rows["1"], 10.0, direction=1, min_tick_velocity=0.05, max_spread_ticks=1)
    assert _is_momentum_candidate(rows["2"], 10.0, direction=1, min_tick_velocity=0.05, max_spread_ticks=1)
    assert not _is_momentum_candidate(rows["3"], 10.0, direction=-1, min_tick_velocity=0.05, max_spread_ticks=1)
    assert not _is_momentum_candidate(rows["3"], 10.0, direction=1, min_tick_velocity=0.05, max_spread_ticks=1)


def test_steamer_generates_signals_only_for_shortening_runner(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    strategy = SteamerStrategy(FakeModel(0.9), model_confidence=0.8)

    signals = strategy.generate_signals(list(rows.values()))

    assert signals  # something was generated
    selection_ids = {s.selection_id for s in signals}
    assert selection_ids == {"1"}
    assert all(s.side is Side.BACK for s in signals)
    assert all(s.strategy == "steamer" for s in signals)
    assert len(signals) == len(DEFAULT_STEAMER_CONFIGS)


def test_drifter_generates_signals_only_for_lengthening_runner(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    strategy = DrifterStrategy(FakeModel(0.9), model_confidence=0.8)

    signals = strategy.generate_signals(list(rows.values()))

    selection_ids = {s.selection_id for s in signals}
    assert selection_ids == {"2"}
    assert all(s.side is Side.LAY for s in signals)
    assert all(s.strategy == "drifter" for s in signals)
    assert len(signals) == len(DEFAULT_DRIFTER_CONFIGS)


def test_no_candidates_produces_no_signals(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    strategy = SteamerStrategy(FakeModel(0.9), model_confidence=0.8)
    # Only the flat runner -> no candidates for steamer.
    signals = strategy.generate_signals([rows["3"]])
    assert signals == []


def test_steamer_and_drifter_configs_are_side_restricted():
    assert all(c.side is Side.BACK for c in DEFAULT_STEAMER_CONFIGS)
    assert all(c.side is Side.LAY for c in DEFAULT_DRIFTER_CONFIGS)
