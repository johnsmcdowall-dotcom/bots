from datetime import datetime, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.features.microstructure import compute_microstructure, total_depth, weighted_depth

NOW = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


def _market(runners, total_matched=1000.0) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="1.1", timestamp=NOW, status=MarketStatus.OPEN, in_play=False,
        total_matched=total_matched, runners=runners,
    )


def test_basic_spread_and_mid_price():
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(3.5, 50.0),), lay=(PriceLevel(3.55, 40.0),),
        last_traded_price=3.5, total_matched=200.0,
    )
    features = compute_microstructure(runner, _market((runner,)))

    assert features.best_back == 3.5
    assert features.best_lay == 3.55
    assert features.mid_price == 3.525
    assert features.spread_ticks == 1
    assert round(features.spread_percentage, 5) == round(0.05 / 3.525, 5)


def test_microprice_weights_toward_heavier_opposite_side():
    # Heavy lay size relative to back size should pull microprice toward
    # the back price (more sellers queued => downward pressure).
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(3.5, 10.0),), lay=(PriceLevel(3.55, 1000.0),),
        last_traded_price=3.5, total_matched=200.0,
    )
    features = compute_microstructure(runner, _market((runner,)))
    # microprice = (3.5*1000 + 3.55*10) / 1010 ≈ 3.5005
    assert 3.5 < features.microprice < 3.51


def test_missing_lay_side_yields_none_spread_and_microprice():
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(3.5, 50.0),), lay=(), last_traded_price=3.5, total_matched=0.0,
    )
    features = compute_microstructure(runner, _market((runner,)))

    assert features.best_back == 3.5
    assert features.best_lay is None
    assert features.mid_price is None
    assert features.spread_ticks is None
    assert features.microprice is None


def test_depth_and_weighted_depth():
    levels = (PriceLevel(3.5, 100.0), PriceLevel(3.55, 50.0), PriceLevel(3.6, 20.0))
    assert total_depth(levels) == 170.0
    assert weighted_depth(levels) == 100.0 / 1 + 50.0 / 2 + 20.0 / 3


def test_order_book_imbalance_and_weight_of_money():
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(3.5, 300.0),), lay=(PriceLevel(3.55, 100.0),),
        last_traded_price=3.5, total_matched=0.0,
    )
    features = compute_microstructure(runner, _market((runner,)))

    assert features.weight_of_money == 300.0 / 400.0
    assert features.order_book_imbalance == (300.0 - 100.0) / 400.0


def test_order_book_imbalance_none_when_no_depth_at_all():
    runner = RunnerLadder(selection_id="1", status=RunnerStatus.ACTIVE, back=(), lay=())
    features = compute_microstructure(runner, _market((runner,)))
    assert features.weight_of_money is None
    assert features.order_book_imbalance is None


def test_runner_market_share_and_implied_probability():
    runner = RunnerLadder(
        selection_id="1", status=RunnerStatus.ACTIVE,
        back=(PriceLevel(4.0, 10.0),), lay=(PriceLevel(4.1, 10.0),),
        last_traded_price=4.0, total_matched=250.0,
    )
    market = _market((runner,), total_matched=1000.0)
    features = compute_microstructure(runner, market)

    assert features.runner_market_share == 0.25
    assert features.implied_probability == 0.25


def test_market_share_none_when_market_total_matched_zero():
    runner = RunnerLadder(selection_id="1", status=RunnerStatus.ACTIVE, back=(PriceLevel(4.0, 10.0),), lay=())
    features = compute_microstructure(runner, _market((runner,), total_matched=0.0))
    assert features.runner_market_share is None
