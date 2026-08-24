from datetime import datetime, timezone
from types import SimpleNamespace

from betfair_trading.betfair.client import _convert_market_book
from betfair_trading.betfair.models import MarketStatus, RunnerStatus


def _fake_price_level(price, size):
    return SimpleNamespace(price=price, size=size)


def _fake_runner(selection_id, status, back, lay, ltp, total_matched):
    return SimpleNamespace(
        selection_id=selection_id,
        status=status,
        ex=SimpleNamespace(
            available_to_back=[_fake_price_level(p, s) for p, s in back],
            available_to_lay=[_fake_price_level(p, s) for p, s in lay],
        ),
        last_price_traded=ltp,
        total_matched=total_matched,
    )


def _fake_market_book(**overrides):
    defaults = dict(
        market_id="1.222",
        publish_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="OPEN",
        inplay=False,
        total_matched=500.0,
        runners=[
            _fake_runner(123, "ACTIVE", [(2.0, 50.0)], [(2.02, 60.0)], 2.0, 100.0),
        ],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_convert_market_book_basic_fields():
    snapshot = _convert_market_book(_fake_market_book())

    assert snapshot.market_id == "1.222"
    assert snapshot.status is MarketStatus.OPEN
    assert snapshot.in_play is False
    assert snapshot.total_matched == 500.0
    assert len(snapshot.runners) == 1

    runner = snapshot.runners[0]
    assert runner.selection_id == "123"
    assert runner.status is RunnerStatus.ACTIVE
    assert runner.best_back.price == 2.0
    assert runner.best_lay.price == 2.02
    assert runner.last_traded_price == 2.0


def test_convert_market_book_handles_empty_ladder():
    book = _fake_market_book(
        runners=[_fake_runner(456, "ACTIVE", [], [], None, 0.0)]
    )
    snapshot = _convert_market_book(book)
    runner = snapshot.runners[0]
    assert runner.best_back is None
    assert runner.best_lay is None


def test_convert_market_book_defaults_publish_time_when_missing():
    book = _fake_market_book()
    del book.publish_time
    snapshot = _convert_market_book(book)
    assert snapshot.timestamp is not None
