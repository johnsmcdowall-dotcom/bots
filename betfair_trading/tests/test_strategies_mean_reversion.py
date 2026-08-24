from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.betfair.ticks import shift_ticks
from betfair_trading.core.interfaces import Side, Sport
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.features.pipeline import build_feature_table
from betfair_trading.strategies.mean_reversion import (
    DEFAULT_TARGET_STOP_PAIRS,
    MeanReversionStrategy,
    detect_unconfirmed_move_direction,
)

MARKET_ID = "1.1"
SCHEDULED_START = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


class FakeModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return [self.probability] * len(X)


def _runner(selection_id, price, matched):
    return RunnerLadder(
        selection_id=selection_id, status=RunnerStatus.ACTIVE,
        back=(PriceLevel(price, 200.0),), lay=(PriceLevel(shift_ticks(price, 1), 200.0),),
        last_traded_price=price, total_matched=matched,
    )


def _build_race_snapshot_rows(tmp_path, n_snapshots=20, stride=0.5):
    """Runner '1' shortens rapidly with NO volume growth (a reversion
    candidate: expect a bounce back up -> LAY). Runner '2' lengthens
    rapidly with NO volume growth (reversion candidate -> BACK). Runner
    '3' shortens rapidly WITH volume growth (momentum's territory, must
    NOT be picked up as a reversion candidate).
    """
    store = SnapshotStore(tmp_path / "trading.duckdb")
    store.write_race_reference(
        market_id=MARKET_ID, event_id="e", event_name="Race", market_name="2m Hcap",
        venue="York", country_code="GB", scheduled_start=SCHEDULED_START,
        runners=[("1", "Horse A", 1), ("2", "Horse B", 2), ("3", "Horse C", 3)],
    )
    p1, p2, p3 = 4.0, 3.0, 4.0
    m1, m2, m3 = 100.0, 100.0, 100.0
    for i in range(n_snapshots):
        ts = SCHEDULED_START - timedelta(seconds=(n_snapshots - i) * stride)
        if i > 0:
            p1 = shift_ticks(p1, -1)
            p2 = shift_ticks(p2, 1)
            p3 = shift_ticks(p3, -1)
            m3 += 20.0  # only runner 3 gets volume growth
        store.write_market_snapshot(
            Sport.HORSE_RACING,
            MarketSnapshot(
                market_id=MARKET_ID, timestamp=ts, status=MarketStatus.OPEN, in_play=False,
                total_matched=m1 + m2 + m3,
                runners=(_runner("1", p1, m1), _runner("2", p2, m2), _runner("3", p3, m3)),
            ),
        )
    rows = build_feature_table(store, MARKET_ID)
    latest = {}
    for row in rows:
        latest[row.selection_id] = row
    return store, latest


def test_detects_unconfirmed_shortening_and_lengthening(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    assert detect_unconfirmed_move_direction(rows["1"], 10.0, 0.1, 0.0) == -1
    assert detect_unconfirmed_move_direction(rows["2"], 10.0, 0.1, 0.0) == 1


def test_volume_confirmed_move_is_not_a_reversion_candidate(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    assert detect_unconfirmed_move_direction(rows["3"], 10.0, 0.1, 0.0) is None


def test_strategy_fades_shortening_with_lay_and_lengthening_with_back(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    strategy = MeanReversionStrategy(FakeModel(0.9), model_confidence=0.8)

    signals = strategy.generate_signals(list(rows.values()))

    by_selection = {}
    for s in signals:
        by_selection.setdefault(s.selection_id, []).append(s)

    assert "3" not in by_selection  # volume-confirmed move, momentum's territory
    assert all(s.side is Side.LAY for s in by_selection["1"])  # fade shortening -> bet on bounce up
    assert all(s.side is Side.BACK for s in by_selection["2"])  # fade lengthening -> bet on pullback down
    assert len(by_selection["1"]) == len(DEFAULT_TARGET_STOP_PAIRS)
    assert all(s.strategy == "mean_reversion" for s in signals)


def test_no_candidates_produces_no_signals(tmp_path):
    _, rows = _build_race_snapshot_rows(tmp_path)
    strategy = MeanReversionStrategy(FakeModel(0.9), model_confidence=0.8)
    assert strategy.generate_signals([rows["3"]]) == []
