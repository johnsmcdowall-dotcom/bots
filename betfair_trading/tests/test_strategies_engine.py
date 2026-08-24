from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.betfair.ticks import shift_ticks
from betfair_trading.core.interfaces import Side, TradeGrade
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.pipeline import build_feature_table
from betfair_trading.models.labels import TargetStopConfig
from betfair_trading.strategies.base import CommissionModel
from betfair_trading.strategies.engine import (
    capital_required_per_unit_stake,
    evaluate_target_before_stop_opportunity,
    resolved_profit_per_stake,
)

MARKET_ID = "1.1"
SCHEDULED_START = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [self.probability] * len(X)


# --- resolved_profit_per_stake: verified against manually worked exposure examples ---

def test_back_then_lay_profit_matches_hand_worked_example():
    # Back £1 @ 4.0, lay £(4.0/3.5) @ 3.5 to hedge -> locked profit 0.142857...
    profit = resolved_profit_per_stake(entry_price=4.0, exit_price=3.5, side=Side.BACK)
    assert round(profit, 6) == round(0.5 / 3.5, 6)


def test_lay_then_back_profit_matches_hand_worked_example():
    # Lay £1 @ 3.5, back £(3.5/4.0) @ 4.0 to hedge -> locked profit 0.125
    profit = resolved_profit_per_stake(entry_price=3.5, exit_price=4.0, side=Side.LAY)
    assert round(profit, 6) == 0.125


def test_back_profits_when_price_shortens_loses_when_it_drifts():
    assert resolved_profit_per_stake(4.0, 3.5, Side.BACK) > 0
    assert resolved_profit_per_stake(4.0, 4.5, Side.BACK) < 0


def test_lay_profits_when_price_drifts_loses_when_it_shortens():
    assert resolved_profit_per_stake(4.0, 4.5, Side.LAY) > 0
    assert resolved_profit_per_stake(4.0, 3.5, Side.LAY) < 0


def test_no_movement_is_exactly_zero_profit():
    assert resolved_profit_per_stake(4.0, 4.0, Side.BACK) == 0.0
    assert resolved_profit_per_stake(4.0, 4.0, Side.LAY) == 0.0


# --- capital_required_per_unit_stake -----------------------------------------

def test_capital_required_back_is_one():
    assert capital_required_per_unit_stake(4.0, Side.BACK) == 1.0


def test_capital_required_lay_is_liability():
    assert capital_required_per_unit_stake(4.0, Side.LAY) == 3.0


# --- evaluate_target_before_stop_opportunity ----------------------------------

def _runner(selection_id: str, price: float, matched: float) -> RunnerLadder:
    # Deep enough depth (200/200, 1-tick spread) that estimate_fill_probability
    # clears the default 0.5 threshold -- otherwise these tests would be
    # (mis)gated by the placeholder fill model rather than testing EV logic.
    return RunnerLadder(
        selection_id=selection_id, status=RunnerStatus.ACTIVE,
        back=(PriceLevel(price, 200.0),), lay=(PriceLevel(shift_ticks(price, 1), 200.0),),
        last_traded_price=price, total_matched=matched,
    )


def _build_dense_feature_row(tmp_path, selection_id="1", n_snapshots=20, stride=0.5):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1), ("2", "Horse B", 2)],
    )
    price1, price2 = 4.0, 3.0
    matched1, matched2 = 100.0, 100.0
    for i in range(n_snapshots):
        ts = SCHEDULED_START - timedelta(seconds=(n_snapshots - i) * stride)
        if i > 0:
            price1 = shift_ticks(price1, -1)
            price2 = shift_ticks(price2, 1 if i % 2 == 0 else -1)
            matched1 += 20.0
            matched2 += 10.0
        store.write_market_snapshot(
            Sport.HORSE_RACING,
            MarketSnapshot(
                market_id=MARKET_ID, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
                total_matched=matched1 + matched2,
                runners=(_runner("1", price1, matched1), _runner("2", price2, matched2)),
            ),
        )
    rows = build_feature_table(store, MARKET_ID)
    target_rows = sorted((r for r in rows if r.selection_id == selection_id), key=lambda r: r.timestamp)
    return store, target_rows[-1]  # richest history


def test_high_probability_positive_ev_gets_a_grade(tmp_path):
    _, feature_row = _build_dense_feature_row(tmp_path)
    config = TargetStopConfig(side=Side.BACK, target_ticks=2, stop_ticks=1, timeout_seconds=30.0)
    model = FakeModel(probability=0.9)

    signal = evaluate_target_before_stop_opportunity(
        "test_strategy", feature_row, config, model, model_confidence=0.8,
    )

    assert signal.grade in (TradeGrade.A_PLUS, TradeGrade.A, TradeGrade.B)
    assert signal.net_expected_value > 0
    assert signal.side == Side.BACK
    assert signal.strategy == "test_strategy"
    assert signal.expected_holding_time_seconds == 30.0
    assert signal.rejection_reason is None


def test_low_probability_negative_ev_is_rejected(tmp_path):
    _, feature_row = _build_dense_feature_row(tmp_path)
    config = TargetStopConfig(side=Side.BACK, target_ticks=1, stop_ticks=5, timeout_seconds=30.0)
    model = FakeModel(probability=0.1)

    signal = evaluate_target_before_stop_opportunity(
        "test_strategy", feature_row, config, model, model_confidence=0.8,
    )

    assert signal.grade == TradeGrade.REJECT
    assert signal.net_expected_value <= 0
    assert signal.rejection_reason is not None


def test_commission_reduces_net_ev_below_gross_edge(tmp_path):
    _, feature_row = _build_dense_feature_row(tmp_path)
    config = TargetStopConfig(side=Side.BACK, target_ticks=2, stop_ticks=1, timeout_seconds=30.0)
    model = FakeModel(probability=0.9)

    signal = evaluate_target_before_stop_opportunity(
        "test_strategy", feature_row, config, model, model_confidence=0.8,
        commission=CommissionModel(rate=0.05),
    )
    zero_commission_signal = evaluate_target_before_stop_opportunity(
        "test_strategy", feature_row, config, model, model_confidence=0.8,
        commission=CommissionModel(rate=0.0),
    )

    assert signal.net_expected_value < zero_commission_signal.net_expected_value
    assert signal.gross_edge == zero_commission_signal.gross_edge  # gross is commission-independent


def test_lay_side_uses_best_lay_as_entry_price(tmp_path):
    _, feature_row = _build_dense_feature_row(tmp_path)
    config = TargetStopConfig(side=Side.LAY, target_ticks=2, stop_ticks=1, timeout_seconds=30.0)
    model = FakeModel(probability=0.5)

    signal = evaluate_target_before_stop_opportunity("test_strategy", feature_row, config, model, model_confidence=0.5)

    assert signal.available_price == feature_row.microstructure.best_lay
    assert signal.capital_required == capital_required_per_unit_stake(feature_row.microstructure.best_lay, Side.LAY)


def test_rejects_when_side_has_no_price(tmp_path):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1)],
    )
    # last_traded_price keeps the row from being skipped entirely by the
    # pipeline (price_proxy falls back to it), but no back-side price is
    # quoted -- exactly the case a BACK-side evaluation must reject on.
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(), lay=(PriceLevel(4.02, 200.0),), last_traded_price=4.0,
    )
    snapshot = MarketSnapshot(
        market_id=MARKET_ID, timestamp=SCHEDULED_START - timedelta(seconds=5), status=MarketStatus.OPEN,
        in_play=False, total_matched=0.0, runners=(runner,),
    )
    store.write_market_snapshot(Sport.HORSE_RACING, snapshot)
    rows = build_feature_table(store, MARKET_ID)
    assert len(rows) == 1

    config = TargetStopConfig(side=Side.BACK, target_ticks=2, stop_ticks=1, timeout_seconds=30.0)
    signal = evaluate_target_before_stop_opportunity("test_strategy", rows[0], config, FakeModel(0.9), model_confidence=0.8)

    assert signal.grade == TradeGrade.REJECT
    assert "no BACK price" in signal.rejection_reason
    store.close()


def test_rejects_when_features_have_missing_values(tmp_path):
    # A single, isolated snapshot -> rolling features for most windows are None.
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1)],
    )
    snapshot = MarketSnapshot(
        market_id=MARKET_ID, timestamp=SCHEDULED_START - timedelta(seconds=5), status=MarketStatus.OPEN,
        in_play=False, total_matched=100.0,
        runners=(_runner("1", 4.0, 100.0),),
    )
    store.write_market_snapshot(Sport.HORSE_RACING, snapshot)
    rows = build_feature_table(store, MARKET_ID)

    config = TargetStopConfig(side=Side.BACK, target_ticks=2, stop_ticks=1, timeout_seconds=30.0)
    signal = evaluate_target_before_stop_opportunity("test_strategy", rows[0], config, FakeModel(0.9), model_confidence=0.8)

    assert signal.grade == TradeGrade.REJECT
    assert "missing values" in signal.rejection_reason
    store.close()
