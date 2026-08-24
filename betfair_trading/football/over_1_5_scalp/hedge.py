"""Green-up / hedge calculation for OVER_1_5_GOALS_SCALP.

Betfair's Over/Under 1.5 Goals market is a single-selection binary market
(BACK "Over 1.5" / LAY "Over 1.5" — exactly like a horse's win market, not
a multi-runner book), so hedging is the same "trade the ladder" mechanic
as strategies/engine.py, generalised here to N back entries at different
prices (the strategy enters at both 30 and 50 minutes, usually at
different odds) rather than assuming a single entry price. Feeding one
`BackEntry` per MATCHED partial fill (not per order) means partial fills
and multiple entry prices are handled by the same formula automatically —
there is no special case for them. Unmatched size must never appear here:
only matched stake is a real position to hedge.

DERIVATION (so the formula isn't taken on faith): with back stakes B_i at
prices P_i, and a hedging LAY stake L at price P_lay, the two settlement
outcomes' combined P&L are:

    Over wins:  sum(B_i * (P_i - 1)) - L * (P_lay - 1)
    Over loses: -sum(B_i) + L

Setting these equal (a fully hedged position must pay out the same either
way) and solving for L:

    L = sum(B_i * P_i) / P_lay

...and the locked-in profit (either outcome) is:

    locked_profit = L - sum(B_i) = sum(B_i * (P_i - P_lay)) / P_lay

This exactly generalises the single-entry BACK-then-LAY formula in
strategies/engine.py (there, n=1: profit = B*(P0-P1)/P1) — verified with a
hand-worked numeric example in tests, not assumed from memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BackEntry:
    """One MATCHED fill on the BACK side (a partial fill and a full fill
    both belong here individually; unmatched size never does)."""

    stake: float
    price: float


@dataclass(frozen=True)
class HedgeCalculation:
    total_back_stake: float
    required_lay_stake: float
    lay_price: float
    locked_profit_gross: float
    commission_on_locked_profit: float
    locked_profit_net: float


def required_lay_stake(entries: Sequence[BackEntry], lay_price: float) -> float:
    if lay_price <= 1.0:
        raise ValueError(f"lay_price must be > 1.0 (got {lay_price})")
    return sum(e.stake * e.price for e in entries) / lay_price


def calculate_hedge(entries: Sequence[BackEntry], lay_price: float, commission_rate: float) -> HedgeCalculation:
    """Commission is charged on net winnings at settlement — since the
    position is fully hedged, the same net profit (or loss) realises
    regardless of which outcome actually happens, so it's applied here
    once rather than per-outcome.
    """
    if not entries:
        raise ValueError("cannot hedge an empty set of back entries")

    total_back_stake = sum(e.stake for e in entries)
    lay_stake = required_lay_stake(entries, lay_price)
    locked_profit_gross = lay_stake - total_back_stake
    commission = commission_rate * locked_profit_gross if locked_profit_gross > 0 else 0.0
    locked_profit_net = locked_profit_gross - commission

    return HedgeCalculation(
        total_back_stake=total_back_stake,
        required_lay_stake=lay_stake,
        lay_price=lay_price,
        locked_profit_gross=locked_profit_gross,
        commission_on_locked_profit=commission,
        locked_profit_net=locked_profit_net,
    )


def passes_hedge_execution_gate(best_lay_price_available: float, max_acceptable_lay_price: float | None) -> bool:
    """Guards against greening into a temporarily terrible price right
    after a goal (thin/volatile market on reopen) — the spec's "use
    controlled execution rather than blindly hitting an extreme price."
    `None` means no cap is configured (always proceed); this is a simple,
    documented placeholder pending a real execution simulator, same as
    strategies/base.py's estimate_fill_probability for horse racing.
    """
    if max_acceptable_lay_price is None:
        return True
    return best_lay_price_available <= max_acceptable_lay_price
