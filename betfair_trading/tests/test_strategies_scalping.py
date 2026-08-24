from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.core.interfaces import Side, Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.pipeline import build_feature_table
from betfair_trading.strategies.scalping import (
    DEFAULT_SCALP_TARGET_STOP_PAIRS,
    ScalpingStrategy,
    passes_liquidity_gate,
)

MARKET_ID = "1.1"
SCHEDULED_START = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [self.probability] * len(X)


def _snapshot(ts, back_size, lay_size, spread_price=4.02):
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(4.0, back_size),), lay=(PriceLevel(spread_price, lay_size),),
        last_traded_price=4.0, total_matched=100.0,
    )
    return MarketSnapshot(
        market_id=MARKET_ID, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
        total_matched=100.0, runners=(runner,),
    )


def _build_row(tmp_path, back_size, lay_size, spread_price=4.02, n_snapshots=5):
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1)],
    )
    for i in range(n_snapshots):
        ts = SCHEDULED_START - timedelta(seconds=(n_snapshots - i) * 0.5)
        store.write_market_snapshot(Sport.HORSE_RACING, _snapshot(ts, back_size, lay_size, spread_price))
    rows = build_feature_table(store, MARKET_ID)
    return store, rows[-1]


def test_passes_liquidity_gate_requires_tight_spread_and_depth(tmp_path):
    _, deep_tight = _build_row(tmp_path, back_size=200.0, lay_size=200.0, spread_price=4.02)
    assert passes_liquidity_gate(deep_tight, max_spread_ticks=1, min_depth=100.0)


def test_liquidity_gate_rejects_thin_depth(tmp_path):
    _, thin = _build_row(tmp_path, back_size=10.0, lay_size=10.0, spread_price=4.02)
    assert not passes_liquidity_gate(thin, max_spread_ticks=1, min_depth=100.0)


def test_liquidity_gate_rejects_wide_spread(tmp_path):
    _, wide = _build_row(tmp_path, back_size=200.0, lay_size=200.0, spread_price=4.2)  # several ticks wide
    assert not passes_liquidity_gate(wide, max_spread_ticks=1, min_depth=100.0)


def test_scalping_strategy_evaluates_both_sides_when_liquid(tmp_path):
    _, row = _build_row(tmp_path, back_size=200.0, lay_size=200.0, spread_price=4.02)
    strategy = ScalpingStrategy(FakeModel(0.9), model_confidence=0.8)

    signals = strategy.generate_signals([row])

    sides = {s.side for s in signals}
    assert sides == {Side.BACK, Side.LAY}
    assert len(signals) == 2 * len(DEFAULT_SCALP_TARGET_STOP_PAIRS)
    assert all(s.strategy == "scalping" for s in signals)


def test_scalping_strategy_skips_illiquid_rows(tmp_path):
    _, row = _build_row(tmp_path, back_size=5.0, lay_size=5.0, spread_price=4.02)
    strategy = ScalpingStrategy(FakeModel(0.9), model_confidence=0.8)
    assert strategy.generate_signals([row]) == []
