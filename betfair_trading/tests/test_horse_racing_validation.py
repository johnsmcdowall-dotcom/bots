from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.betfair.ticks import shift_ticks
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.horse_racing.validation import validate_recorded_market

NOW = datetime(2026, 3, 1, 13, 0, 0, tzinfo=timezone.utc)


def _runner(selection_id: str, price: float) -> RunnerLadder:
    return RunnerLadder(
        selection_id=selection_id,
        status=RunnerStatus.ACTIVE,
        back=(PriceLevel(price, 50.0),),
        lay=(PriceLevel(shift_ticks(price, 1), 50.0),),
        last_traded_price=price,
        total_matched=100.0,
    )


def _snapshot(ts: datetime, runners: tuple[RunnerLadder, ...], status=MarketStatus.OPEN) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="1.111", timestamp=ts, status=status, in_play=False, total_matched=1000.0, runners=runners
    )


def _store_with_reference(tmp_path, runners=(("1", "Horse A"), ("2", "Horse B"))):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id="1.111", event_id="e1", event_name="York", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=NOW + timedelta(minutes=30),
        runners=[(sid, name, i) for i, (sid, name) in enumerate(runners, start=1)],
    )
    return store


def test_valid_recording_passes(tmp_path):
    store = _store_with_reference(tmp_path)
    store.write_market_snapshot(
        Sport.HORSE_RACING, _snapshot(NOW, (_runner("1", 2.0), _runner("2", 3.5)))
    )
    store.write_market_snapshot(
        Sport.HORSE_RACING, _snapshot(NOW + timedelta(seconds=5), (_runner("1", 1.98), _runner("2", 3.55)))
    )

    report = validate_recorded_market(store, "1.111")

    assert report.is_valid, report.issues
    assert report.snapshot_count == 2
    store.close()


def test_too_few_snapshots_fails(tmp_path):
    store = _store_with_reference(tmp_path)
    store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(NOW, (_runner("1", 2.0),)))

    report = validate_recorded_market(store, "1.111", min_snapshots=5)

    assert not report.is_valid
    assert "only 1 snapshot" in report.issues[0]
    store.close()


def test_missing_runner_reference_is_flagged(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")  # no write_race_reference call
    store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(NOW, (_runner("1", 2.0),)))

    report = validate_recorded_market(store, "1.111")

    assert not report.is_valid
    assert any("no runner_reference registered" in issue for issue in report.issues)
    store.close()


def test_selection_id_not_in_reference_is_flagged(tmp_path):
    store = _store_with_reference(tmp_path, runners=(("1", "Horse A"),))
    store.write_market_snapshot(
        Sport.HORSE_RACING, _snapshot(NOW, (_runner("1", 2.0), _runner("99", 5.0)))
    )

    report = validate_recorded_market(store, "1.111")

    assert not report.is_valid
    assert any("not in runner_reference" in issue for issue in report.issues)
    store.close()


def test_off_ladder_price_is_flagged(tmp_path):
    store = _store_with_reference(tmp_path)
    bad_runner = RunnerLadder(
        selection_id="1",
        status=RunnerStatus.ACTIVE,
        back=(PriceLevel(2.015, 50.0),),  # not a valid Betfair tick
        lay=(),
        last_traded_price=2.015,
        total_matched=100.0,
    )
    store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(NOW, (bad_runner,)))

    report = validate_recorded_market(store, "1.111")

    assert not report.is_valid
    assert any("off-ladder price" in issue for issue in report.issues)
    store.close()
