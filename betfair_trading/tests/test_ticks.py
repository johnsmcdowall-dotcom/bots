import pytest

from betfair_trading.betfair.ticks import (
    MAX_PRICE,
    MIN_PRICE,
    PRICE_LADDER,
    is_valid_price,
    round_to_nearest_tick,
    shift_ticks,
    tick_index,
    ticks_between,
)


def test_ladder_boundaries():
    assert PRICE_LADDER[0] == 1.01
    assert PRICE_LADDER[-1] == 1000.0
    assert PRICE_LADDER == tuple(sorted(set(PRICE_LADDER)))  # strictly increasing, no dupes


def test_known_valid_prices():
    for price in [1.01, 1.02, 1.99, 2.0, 2.02, 3.0, 3.05, 4.0, 4.1, 6.0, 6.2, 10.0, 10.5, 20.0, 21.0, 30.0, 32.0, 50.0, 55.0, 100.0, 110.0, 1000.0]:
        assert is_valid_price(price), f"{price} should be a valid Betfair tick"


def test_known_invalid_prices():
    for price in [1.005, 1.015, 2.01, 2.03, 3.01, 5.05, 6.1, 15.25, 25.5, 999.99]:
        assert not is_valid_price(price), f"{price} should NOT be a valid Betfair tick"


def test_round_to_nearest_tick():
    assert round_to_nearest_tick(2.015) == 2.02
    assert round_to_nearest_tick(2.011) == 2.02  # closer to 2.02 than 2.0? check midpoint below
    assert round_to_nearest_tick(2.005) in (2.0, 2.02)  # exact midpoint, either side acceptable
    assert round_to_nearest_tick(0.5) == MIN_PRICE
    assert round_to_nearest_tick(5000.0) == MAX_PRICE


def test_shift_ticks_shorten_and_drift():
    assert shift_ticks(2.0, 1) == 2.02
    assert shift_ticks(2.0, -1) == 1.99
    assert shift_ticks(3.0, 1) == 3.05
    assert shift_ticks(4.0, -1) == 3.95


def test_shift_ticks_clamps_at_ladder_ends():
    assert shift_ticks(1.01, -5) == MIN_PRICE
    assert shift_ticks(1000.0, 5) == MAX_PRICE


def test_ticks_between():
    assert ticks_between(2.0, 2.02) == 1
    assert ticks_between(2.02, 2.0) == -1
    assert ticks_between(3.55, 3.55) == 0
    assert ticks_between(1.01, 2.0) == tick_index(2.0) - tick_index(1.01)


def test_tick_index_rejects_off_ladder_price():
    with pytest.raises(ValueError):
        tick_index(2.015)
