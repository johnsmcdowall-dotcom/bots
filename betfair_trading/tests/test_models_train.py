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
from betfair_trading.models.labels import CANONICAL_TARGET_STOP_CONFIGS
from betfair_trading.models.train import train_baseline_models

N_MARKETS = 8
N_SNAPSHOTS = 20
SNAPSHOT_STRIDE_SECONDS = 0.5


def _build_synthetic_multi_market_store(tmp_path):
    """8 markets, chronologically spaced 15 minutes apart, each recorded at
    0.5s intervals (sub-second, like real Betfair streaming ticks — wide
    5s+ spacing would leave the smallest rolling windows, e.g. 1s/3s,
    structurally unable to ever hold enough points, and to_model_matrix's
    no-fabrication policy correctly drops every row as a result). Runner
    "1" moves deterministically: shortens steadily in even-indexed markets,
    drifts steadily in odd-indexed markets. Runner "2" alternates by a
    tick each snapshot (near-flat noise). This gives every baseline model
    a genuinely learnable, class-balanced signal without relying on chance
    (a randomly generated dataset could flakily fail to produce enough
    class diversity to fit).
    """
    store = SnapshotStore(tmp_path / "trading.duckdb")
    base_start = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    market_ids = []

    for m in range(N_MARKETS):
        market_id = f"1.{100 + m}"
        market_ids.append(market_id)
        scheduled_start = base_start + timedelta(minutes=15 * m)
        shortening = m % 2 == 0

        store.write_race_reference(
            market_id=market_id, event_id=f"e{m}", event_name="Race", market_name="2m Hcap",
            venue="York", country_code="GB", scheduled_start=scheduled_start,
            runners=[("1", "Horse A", 1), ("2", "Horse B", 2)],
        )

        r1_price, r2_price = 4.0, 3.0
        r1_matched, r2_matched = 100.0, 100.0
        for i in range(N_SNAPSHOTS):
            ts = scheduled_start - timedelta(seconds=(N_SNAPSHOTS - i) * SNAPSHOT_STRIDE_SECONDS)
            if i > 0:
                r1_price = shift_ticks(r1_price, -1 if shortening else 1)
                r2_price = shift_ticks(r2_price, 1 if i % 2 == 0 else -1)
                r1_matched += 50.0
                r2_matched += 20.0
            snapshot = MarketSnapshot(
                market_id=market_id, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
                total_matched=r1_matched + r2_matched,
                runners=(
                    RunnerLadder(
                        selection_id="1", status=RunnerStatus.ACTIVE,
                        back=(PriceLevel(r1_price, 50.0),), lay=(PriceLevel(shift_ticks(r1_price, 1), 40.0),),
                        last_traded_price=r1_price, total_matched=r1_matched,
                    ),
                    RunnerLadder(
                        selection_id="2", status=RunnerStatus.ACTIVE,
                        back=(PriceLevel(r2_price, 50.0),), lay=(PriceLevel(shift_ticks(r2_price, 1), 40.0),),
                        last_traded_price=r2_price, total_matched=r2_matched,
                    ),
                ),
            )
            store.write_market_snapshot(Sport.HORSE_RACING, snapshot)

    return store, market_ids


def test_train_baseline_models_end_to_end(tmp_path):
    store, market_ids = _build_synthetic_multi_market_store(tmp_path)

    report = train_baseline_models(
        store,
        market_ids,
        short_horizons=(5.0, 10.0),
        target_stop_configs=CANONICAL_TARGET_STOP_CONFIGS[:2],
        train_fraction=0.6,
        validation_fraction=0.2,
    )

    total = (
        len(report.split.train_market_ids)
        + len(report.split.validation_market_ids)
        + len(report.split.test_market_ids)
    )
    assert total == N_MARKETS

    # Walk-forward discipline: every validation market's scheduled_start is
    # strictly after every training market's.
    train_starts = [store.read_race_reference(m)["scheduled_start"] for m in report.split.train_market_ids]
    validation_starts = [store.read_race_reference(m)["scheduled_start"] for m in report.split.validation_market_ids]
    assert train_starts and validation_starts
    assert max(train_starts) < min(validation_starts)

    # The synthetic signal is deliberately clean and class-balanced, so the
    # pipeline should actually produce scores rather than skip everything —
    # a bug that made every config unusable would show up as an all-skip report.
    assert any("multiclass_brier_score" in ev for ev in report.short_horizon_evaluations.values())
    assert any("brier_score" in ev for ev in report.target_before_stop_evaluations.values())
    assert "mean_absolute_tick_error" in report.bsp_forecast_evaluation

    for evaluation in report.short_horizon_evaluations.values():
        assert "skipped" in evaluation or evaluation["multiclass_brier_score"] >= 0.0
    for evaluation in report.target_before_stop_evaluations.values():
        assert "skipped" in evaluation or 0.0 <= evaluation["brier_score"] <= 1.0

    store.close()


def test_train_baseline_models_with_too_few_markets_skips_gracefully(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    scheduled_start = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)
    store.write_race_reference(
        market_id="1.1", event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=scheduled_start,
        runners=[("1", "Horse A", 1)],
    )
    snapshot = MarketSnapshot(
        market_id="1.1", timestamp=scheduled_start - timedelta(seconds=5), status=MarketStatus.OPEN,
        in_play=False, total_matched=100.0,
        runners=(RunnerLadder(selection_id="1", status=RunnerStatus.ACTIVE, back=(PriceLevel(4.0, 50.0),), lay=()),),
    )
    store.write_market_snapshot(Sport.HORSE_RACING, snapshot)

    report = train_baseline_models(store, ["1.1"], short_horizons=(5.0,), target_stop_configs=CANONICAL_TARGET_STOP_CONFIGS[:1])

    # A single market with one snapshot has no meaningful train/validation
    # split -- everything should skip cleanly rather than raise or fabricate a model.
    assert all("skipped" in ev for ev in report.short_horizon_evaluations.values())
    assert all("skipped" in ev for ev in report.target_before_stop_evaluations.values())
    assert "skipped" in report.bsp_forecast_evaluation
    store.close()
