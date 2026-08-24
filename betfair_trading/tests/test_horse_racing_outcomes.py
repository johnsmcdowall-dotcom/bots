from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.horse_racing.outcomes import extract_win_outcomes

MARKET_ID = "1.1"
NOW = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


def _snapshot(status, runners, ts=NOW):
    return MarketSnapshot(market_id=MARKET_ID, timestamp=ts, status=status, in_play=False, total_matched=0.0, runners=runners)


def _runner(selection_id, status, price=4.0):
    return RunnerLadder(selection_id=selection_id, status=status, back=(PriceLevel(price, 10.0),), lay=())


def test_extracts_winner_and_loser_from_closed_market(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        _snapshot(MarketStatus.OPEN, (_runner("1", RunnerStatus.ACTIVE), _runner("2", RunnerStatus.ACTIVE)), ts=NOW),
    )
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        _snapshot(
            MarketStatus.CLOSED,
            (_runner("1", RunnerStatus.WINNER), _runner("2", RunnerStatus.LOSER)),
            ts=NOW + timedelta(minutes=5),
        ),
    )

    outcomes = extract_win_outcomes(store, MARKET_ID)

    assert outcomes == {"1": True, "2": False}
    store.close()


def test_returns_none_when_market_never_closed(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        _snapshot(MarketStatus.OPEN, (_runner("1", RunnerStatus.ACTIVE),)),
    )
    assert extract_win_outcomes(store, MARKET_ID) is None
    store.close()


def test_returns_none_when_no_market_recorded(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    assert extract_win_outcomes(store, "does-not-exist") is None
    store.close()


def test_returns_none_when_closed_but_no_resolved_statuses(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        _snapshot(MarketStatus.CLOSED, (_runner("1", RunnerStatus.REMOVED),)),
    )
    assert extract_win_outcomes(store, MARKET_ID) is None
    store.close()


def test_excludes_removed_runners_but_keeps_resolved_ones(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        _snapshot(
            MarketStatus.CLOSED,
            (_runner("1", RunnerStatus.WINNER), _runner("2", RunnerStatus.REMOVED), _runner("3", RunnerStatus.LOSER)),
        ),
    )
    outcomes = extract_win_outcomes(store, MARKET_ID)
    assert outcomes == {"1": True, "3": False}
    store.close()
