from datetime import datetime, timezone

from betfair_trading.betfair.models import MarketSnapshot, MarketStatus
from betfair_trading.core.interfaces import Sport
from betfair_trading.data.football_feed import NullFeed
from betfair_trading.data.ingestion import IngestionService
from betfair_trading.database.storage import SnapshotStore


class FakeStreamClient:
    def __init__(self, snapshots):
        self._snapshots = snapshots

    def stream(self, market_ids, on_snapshot):
        for snapshot in self._snapshots:
            on_snapshot(snapshot)


def _snapshot(market_id: str) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=MarketStatus.OPEN,
        in_play=False,
        total_matched=0.0,
        runners=(),
    )


def test_record_market_stream_writes_every_snapshot(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    service = IngestionService(store)
    fake_stream = FakeStreamClient([_snapshot("1.1"), _snapshot("1.1")])

    written = []
    original_write = store.write_market_snapshot

    def spy_write(sport, snapshot):
        written.append((sport, snapshot.market_id))
        original_write(sport, snapshot)

    store.write_market_snapshot = spy_write  # type: ignore[assignment]

    service.record_market_stream(fake_stream, ["1.1"], Sport.HORSE_RACING)

    assert written == [(Sport.HORSE_RACING, "1.1"), (Sport.HORSE_RACING, "1.1")]
    store.close()


def test_poll_football_once_writes_state_with_timestamp(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    service = IngestionService(store)

    written = service.poll_football_once(NullFeed(), ["match-1", "match-2"])

    assert written == 2
    assert store.football_state_count("match-1") == 1
    assert store.football_state_count("match-2") == 1
    store.close()


def test_poll_football_once_skips_states_without_a_timestamp(tmp_path):
    class NoTimestampFeed:
        def poll(self, match_id):
            return {"match_id": match_id}

    store = SnapshotStore(tmp_path / "trading.duckdb")
    service = IngestionService(store)

    written = service.poll_football_once(NoTimestampFeed(), ["match-1"])

    assert written == 0
    assert store.football_state_count("match-1") == 0
    store.close()


def test_poll_football_once_continues_after_one_feed_failure(tmp_path):
    class FlakyFeed:
        def poll(self, match_id):
            if match_id == "bad":
                raise RuntimeError("provider timeout")
            return {"match_id": match_id, "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}

    store = SnapshotStore(tmp_path / "trading.duckdb")
    service = IngestionService(store)

    written = service.poll_football_once(FlakyFeed(), ["bad", "good"])

    assert written == 1
    assert store.football_state_count("good") == 1
    store.close()


def test_poll_football_forever_stops_when_should_continue_is_false(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    service = IngestionService(store)

    calls = {"n": 0}

    def should_continue():
        calls["n"] += 1
        return calls["n"] <= 3

    slept = []
    service.poll_football_forever(
        NullFeed(), ["match-1"], interval_seconds=0, sleep=slept.append, should_continue=should_continue
    )

    assert len(slept) == 3
    store.close()
