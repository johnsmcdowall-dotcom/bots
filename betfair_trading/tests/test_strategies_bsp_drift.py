from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.core.interfaces import Side, Sport, TradeGrade
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.pipeline import build_feature_table
from betfair_trading.strategies.bsp_drift import BspDriftStrategy, evaluate_bsp_forecast_opportunity

MARKET_ID = "1.1"
SCHEDULED_START = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


class FakeRegressionModel:
    def __init__(self, tick_delta: float):
        self.tick_delta = tick_delta

    def predict(self, X):
        return [self.tick_delta] * len(X)


def _runner(matched: float):
    # Volume must actually grow snapshot-to-snapshot, or VWAP (which needs
    # a traded-volume delta) stays None for every window and to_model_matrix
    # drops every row as missing data -- price staying flat is fine, a
    # static volume total is not.
    return RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(4.0, 200.0),), lay=(PriceLevel(4.1, 200.0),),
        last_traded_price=4.0, total_matched=matched,
    )


def _build_row(tmp_path, n_snapshots=20, stride=0.5):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1)],
    )
    matched = 100.0
    for i in range(n_snapshots):
        ts = SCHEDULED_START - timedelta(seconds=(n_snapshots - i) * stride)
        if i > 0:
            matched += 20.0
        store.write_market_snapshot(
            Sport.HORSE_RACING,
            MarketSnapshot(
                market_id=MARKET_ID, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
                total_matched=matched, runners=(_runner(matched),),
            ),
        )
    rows = build_feature_table(store, MARKET_ID)
    return store, rows[-1]


def test_predicted_shortening_produces_a_back_signal(tmp_path):
    _, row = _build_row(tmp_path)
    model = FakeRegressionModel(tick_delta=-5.0)

    signal = evaluate_bsp_forecast_opportunity("bsp_drift", row, model, model_confidence=0.8)

    assert signal.side is Side.BACK
    assert signal.available_price == row.microstructure.best_back
    assert "predicted closing move" in signal.reason


def test_predicted_lengthening_produces_a_lay_signal(tmp_path):
    _, row = _build_row(tmp_path)
    model = FakeRegressionModel(tick_delta=5.0)

    signal = evaluate_bsp_forecast_opportunity("bsp_drift", row, model, model_confidence=0.8)

    assert signal.side is Side.LAY
    assert signal.available_price == row.microstructure.best_lay


def test_small_predicted_move_is_rejected(tmp_path):
    _, row = _build_row(tmp_path)
    model = FakeRegressionModel(tick_delta=0.5)

    signal = evaluate_bsp_forecast_opportunity("bsp_drift", row, model, model_confidence=0.8, min_predicted_tick_move=2.0)

    assert signal.grade == TradeGrade.REJECT
    assert "too small to trade" in signal.rejection_reason


def test_high_confidence_large_move_is_gradeable(tmp_path):
    _, row = _build_row(tmp_path)
    model = FakeRegressionModel(tick_delta=-10.0)

    signal = evaluate_bsp_forecast_opportunity("bsp_drift", row, model, model_confidence=0.85)

    assert signal.net_expected_value > 0
    assert signal.grade != TradeGrade.REJECT


def test_strategy_evaluates_every_row_no_prefilter(tmp_path):
    _, row = _build_row(tmp_path)
    strategy = BspDriftStrategy(FakeRegressionModel(tick_delta=0.1), model_confidence=0.8)

    signals = strategy.generate_signals([row, row, row])

    assert len(signals) == 3
    assert all(s.grade == TradeGrade.REJECT for s in signals)  # forecast too small every time
