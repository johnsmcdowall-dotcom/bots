from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from betfair_trading.betfair.models import MarketSnapshot, MarketStatus
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.horse_racing.market_discovery import MarketQualityFilter
from betfair_trading.horse_racing.recorder import HorseRacingRecorder

NOW = datetime(2026, 3, 1, 13, 0, 0, tzinfo=timezone.utc)


def _fake_catalogue_entry(market_id, minutes_ahead, total_matched=5000.0, n_runners=6, country="GB"):
    return SimpleNamespace(
        market_id=market_id,
        market_name="2m Hcap",
        market_start_time=NOW + timedelta(minutes=minutes_ahead),
        total_matched=total_matched,
        event=SimpleNamespace(id=30001, name="York 1st Mar", venue="York", country_code=country),
        runners=[
            SimpleNamespace(selection_id=i, runner_name=f"Horse {i}", sort_priority=i)
            for i in range(1, n_runners + 1)
        ],
    )


class FakeBetfairClient:
    def __init__(self, catalogue_entries):
        self._catalogue_entries = catalogue_entries
        self.last_filter = None

    def list_market_catalogue(self, filter_, max_results=100):
        self.last_filter = filter_
        return self._catalogue_entries


class FakeStreamClient:
    def __init__(self, snapshots_by_market):
        self._snapshots_by_market = snapshots_by_market
        self.subscribed_market_ids = None

    def stream(self, market_ids, on_snapshot):
        self.subscribed_market_ids = list(market_ids)
        for market_id in market_ids:
            for snapshot in self._snapshots_by_market.get(market_id, []):
                on_snapshot(snapshot)


def _snapshot(market_id: str, ts: datetime) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
        total_matched=100.0, runners=(),
    )


def test_discover_races_applies_quality_filter(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    client = FakeBetfairClient(
        [
            _fake_catalogue_entry("1.1", minutes_ahead=45, total_matched=5000.0),
            _fake_catalogue_entry("1.2", minutes_ahead=45, total_matched=10.0),  # illiquid
            _fake_catalogue_entry("1.3", minutes_ahead=45, country="FR"),  # wrong country
        ]
    )
    recorder = HorseRacingRecorder(client, store)

    races = recorder.discover_races(MarketQualityFilter(), now=NOW, minutes_ahead=120)

    assert [r.market_id for r in races] == ["1.1"]
    assert client.last_filter["market_countries"] == ["GB", "IE"]
    store.close()


def test_register_race_writes_reference_data(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    client = FakeBetfairClient([_fake_catalogue_entry("1.1", minutes_ahead=45)])
    recorder = HorseRacingRecorder(client, store)

    races = recorder.discover_races(MarketQualityFilter(), now=NOW)
    recorder.register_race(races[0])

    reference = store.read_race_reference("1.1")
    assert reference["venue"] == "York"
    assert reference["runner_count"] == 6
    store.close()


def test_record_registers_and_streams_all_selected_races(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    client = FakeBetfairClient(
        [
            _fake_catalogue_entry("1.1", minutes_ahead=45),
            _fake_catalogue_entry("1.2", minutes_ahead=60),
        ]
    )
    recorder = HorseRacingRecorder(client, store)
    races = recorder.discover_races(MarketQualityFilter(), now=NOW)

    stream_client = FakeStreamClient(
        {
            "1.1": [_snapshot("1.1", NOW), _snapshot("1.1", NOW + timedelta(seconds=5))],
            "1.2": [_snapshot("1.2", NOW)],
        }
    )

    recorder.record(stream_client, races)

    assert sorted(stream_client.subscribed_market_ids) == ["1.1", "1.2"]
    assert store.market_snapshot_count("1.1") == 0  # snapshots here have zero runners
    assert store.read_race_reference("1.1") is not None
    assert store.read_race_reference("1.2") is not None
    store.close()


def test_record_with_no_races_does_not_touch_stream_client(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    client = FakeBetfairClient([])
    recorder = HorseRacingRecorder(client, store)

    stream_client = FakeStreamClient({})
    recorder.record(stream_client, [])

    assert stream_client.subscribed_market_ids is None
    store.close()
