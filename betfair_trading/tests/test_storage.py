from datetime import datetime, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.storage import SnapshotStore


def _snapshot(ts: datetime, best_back: float) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="1.111",
        timestamp=ts,
        status=MarketStatus.OPEN,
        in_play=False,
        total_matched=1000.0,
        runners=(
            RunnerLadder(
                selection_id="1",
                status=RunnerStatus.ACTIVE,
                back=(PriceLevel(best_back, 50.0), PriceLevel(best_back + 0.02, 100.0)),
                lay=(PriceLevel(best_back + 0.01, 40.0),),
                last_traded_price=best_back,
                total_matched=200.0,
            ),
            RunnerLadder(
                selection_id="2",
                status=RunnerStatus.ACTIVE,
                back=(PriceLevel(3.5, 20.0),),
                lay=(PriceLevel(3.55, 20.0),),
                last_traded_price=3.5,
                total_matched=150.0,
            ),
        ),
    )


def test_write_and_read_market_snapshots_round_trip(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    ts1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(ts1, 2.0))
    store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(ts2, 1.98))

    assert store.market_snapshot_count("1.111") == 4  # 2 runners x 2 snapshots

    snapshots = store.read_market_snapshots("1.111")
    assert [s.timestamp for s in snapshots] == [ts1, ts2]
    assert len(snapshots[0].runners) == 2
    runner_1 = snapshots[0].runner("1")
    assert runner_1.best_back == PriceLevel(2.0, 50.0)
    assert runner_1.best_lay == PriceLevel(2.01, 40.0)
    assert snapshots[1].runner("1").best_back.price == 1.98

    store.close()


def test_write_football_state_and_events(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    ts = datetime(2026, 1, 1, 15, 30, 0, tzinfo=timezone.utc)

    store.write_football_state(
        "match-1", ts, {"minute": 55.0, "home_score": 1, "away_score": 0, "home_xg": 1.2, "away_xg": 0.4}
    )
    store.write_match_event("match-1", ts, "GOAL", team="HOME", minute=55.0, detail={"scorer": "Player X"})

    assert store.football_state_count("match-1") == 1
    assert store.football_state_count() == 1

    store.close()


def test_market_snapshot_count_for_unknown_market_is_zero(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    assert store.market_snapshot_count("does-not-exist") == 0
    store.close()
