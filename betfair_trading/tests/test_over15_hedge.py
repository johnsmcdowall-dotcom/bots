import pytest

from betfair_trading.football.over_1_5_scalp.hedge import (
    BackEntry,
    calculate_hedge,
    passes_hedge_execution_gate,
    required_lay_stake,
)
from betfair_trading.strategies.engine import resolved_profit_per_stake
from betfair_trading.core.interfaces import Side


def test_single_entry_hedge_matches_horse_racing_engine_formula():
    # Cross-check against strategies/engine.py's independently-derived
    # single-entry BACK-then-LAY formula -- both must agree exactly.
    entries = [BackEntry(stake=1.0, price=4.0)]
    hedge = calculate_hedge(entries, lay_price=3.5, commission_rate=0.0)

    expected_profit = resolved_profit_per_stake(entry_price=4.0, exit_price=3.5, side=Side.BACK)
    assert round(hedge.locked_profit_gross, 9) == round(expected_profit, 9)


def test_two_entry_hedge_hand_worked_example():
    # Back £10 @ 1.8 (30-min entry), back £10 @ 1.3 (50-min entry, price
    # shortened), goal scored, lay now available @ 1.15.
    entries = [BackEntry(10.0, 1.8), BackEntry(10.0, 1.3)]
    hedge = calculate_hedge(entries, lay_price=1.15, commission_rate=0.05)

    expected_lay_stake = (10.0 * 1.8 + 10.0 * 1.3) / 1.15
    expected_gross = expected_lay_stake - 20.0
    expected_commission = 0.05 * expected_gross
    expected_net = expected_gross - expected_commission

    assert round(hedge.required_lay_stake, 6) == round(expected_lay_stake, 6)
    assert round(hedge.locked_profit_gross, 6) == round(expected_gross, 6)
    assert round(hedge.commission_on_locked_profit, 6) == round(expected_commission, 6)
    assert round(hedge.locked_profit_net, 6) == round(expected_net, 6)
    assert hedge.total_back_stake == 20.0


def test_locked_profit_is_identical_regardless_of_settlement_outcome():
    # Directly verify the "locked" property: compute P&L both ways.
    entries = [BackEntry(10.0, 1.8), BackEntry(10.0, 1.3)]
    lay_price = 1.15
    lay_stake = required_lay_stake(entries, lay_price)

    profit_if_over_wins = sum(e.stake * (e.price - 1) for e in entries) - lay_stake * (lay_price - 1)
    profit_if_over_loses = -sum(e.stake for e in entries) + lay_stake

    assert round(profit_if_over_wins, 9) == round(profit_if_over_loses, 9)


def test_negative_locked_profit_has_no_commission_charged():
    # A hedge locking in a LOSS (e.g. entered at bad prices) must not be
    # charged commission on a negative "profit".
    entries = [BackEntry(10.0, 1.3)]
    hedge = calculate_hedge(entries, lay_price=1.8, commission_rate=0.05)  # price drifted against us
    assert hedge.locked_profit_gross < 0
    assert hedge.commission_on_locked_profit == 0.0
    assert hedge.locked_profit_net == hedge.locked_profit_gross


def test_rejects_invalid_lay_price():
    with pytest.raises(ValueError):
        required_lay_stake([BackEntry(10.0, 1.5)], lay_price=1.0)
    with pytest.raises(ValueError):
        required_lay_stake([BackEntry(10.0, 1.5)], lay_price=0.5)


def test_rejects_empty_entries():
    with pytest.raises(ValueError):
        calculate_hedge([], lay_price=1.5, commission_rate=0.05)


def test_execution_gate_no_cap_always_passes():
    assert passes_hedge_execution_gate(best_lay_price_available=100.0, max_acceptable_lay_price=None)


def test_execution_gate_blocks_price_worse_than_cap():
    assert not passes_hedge_execution_gate(best_lay_price_available=2.0, max_acceptable_lay_price=1.5)
    assert passes_hedge_execution_gate(best_lay_price_available=1.4, max_acceptable_lay_price=1.5)
