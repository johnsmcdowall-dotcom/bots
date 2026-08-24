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
from betfair_trading.strategies.base import CommissionModel
from betfair_trading.strategies.favourite_longshot import (
    OddsBucket,
    RunnerOutcomeObservation,
    collect_outcome_observations,
    measure_favourite_longshot_calibration,
)

NOW = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


def _runner(selection_id, status, price=None):
    back = (PriceLevel(price, 10.0),) if price is not None else ()
    return RunnerLadder(selection_id=selection_id, status=status, back=back, lay=())


def _write_settled_market(store, market_id, pre_off_prices, outcomes, in_play_final=False):
    """pre_off_prices: dict[selection_id, price]. outcomes: dict[selection_id, bool]."""
    pre_off_runners = tuple(
        _runner(sid, RunnerStatus.ACTIVE, price) for sid, price in pre_off_prices.items()
    )
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        MarketSnapshot(market_id=market_id, timestamp=NOW, status=MarketStatus.OPEN, in_play=False, total_matched=0.0, runners=pre_off_runners),
    )
    closed_runners = tuple(
        _runner(sid, RunnerStatus.WINNER if outcomes.get(sid) else RunnerStatus.LOSER)
        for sid in pre_off_prices
    )
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        MarketSnapshot(
            market_id=market_id, timestamp=NOW + timedelta(minutes=5), status=MarketStatus.CLOSED,
            in_play=in_play_final, total_matched=0.0, runners=closed_runners,
        ),
    )


def test_collect_outcome_observations_from_settled_market(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    _write_settled_market(store, "1.1", {"1": 2.0, "2": 5.0}, {"1": True, "2": False})

    observations = collect_outcome_observations(store, ["1.1"])

    assert len(observations) == 2
    obs_by_id = {o.selection_id: o for o in observations}
    assert obs_by_id["1"].price == 2.0 and obs_by_id["1"].won is True
    assert obs_by_id["2"].price == 5.0 and obs_by_id["2"].won is False
    store.close()


def test_collect_outcome_observations_skips_unsettled_markets(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_market_snapshot(
        Sport.HORSE_RACING,
        MarketSnapshot(market_id="1.2", timestamp=NOW, status=MarketStatus.OPEN, in_play=False, total_matched=0.0, runners=(_runner("1", RunnerStatus.ACTIVE, 3.0),)),
    )
    assert collect_outcome_observations(store, ["1.2"]) == []
    store.close()


def test_measure_calibration_hand_worked_example(tmp_path):
    observations = [
        RunnerOutcomeObservation(market_id="1.1", selection_id="1", price=2.0, won=True),
        RunnerOutcomeObservation(market_id="1.2", selection_id="1", price=2.5, won=False),
    ]
    buckets = (OddsBucket("2.00-3.00", 2.00, 3.00),)

    results = measure_favourite_longshot_calibration(observations, buckets, commission=CommissionModel(rate=0.05))

    assert len(results) == 1
    bucket_result = results[0]
    assert bucket_result.sample_size == 2
    assert round(bucket_result.mean_implied_probability, 6) == round((0.5 + 0.4) / 2, 6)
    assert bucket_result.actual_win_frequency == 0.5
    assert round(bucket_result.back_roi, 6) == round((0.95 - 1.0) / 2, 6)
    assert round(bucket_result.lay_roi, 6) == round((-1.0 + 0.95) / 2.5, 6)
    assert round(bucket_result.calibration_error, 6) == round(0.45 - 0.5, 6)


def test_empty_bucket_has_none_fields_not_zero(tmp_path):
    observations = [RunnerOutcomeObservation("1.1", "1", price=10.0, won=True)]
    buckets = (OddsBucket("2.00-3.00", 2.00, 3.00),)

    results = measure_favourite_longshot_calibration(observations, buckets)

    assert results[0].sample_size == 0
    assert results[0].mean_implied_probability is None
    assert results[0].actual_win_frequency is None
    assert results[0].back_roi is None
    assert results[0].lay_roi is None
    assert results[0].calibration_error is None


def test_bucket_boundaries_are_min_inclusive_max_exclusive():
    observations = [
        RunnerOutcomeObservation("1.1", "1", price=2.0, won=True),   # in [2.0, 3.0)
        RunnerOutcomeObservation("1.2", "1", price=3.0, won=True),   # NOT in [2.0, 3.0) -- belongs to next bucket
    ]
    buckets = (OddsBucket("2.00-3.00", 2.00, 3.00), OddsBucket("3.00-5.00", 3.00, 5.00))

    results = measure_favourite_longshot_calibration(observations, buckets)

    assert results[0].sample_size == 1
    assert results[1].sample_size == 1
