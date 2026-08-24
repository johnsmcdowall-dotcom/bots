"""Extracts race outcomes (which runner actually won) from recorded market
data, for research that needs real settlement — HORSE STRATEGY 7/12's
favourite/longshot calibration (strategies/favourite_longshot.py) most
directly, but useful anywhere a strategy needs ground truth rather than a
price-derived proxy.

Only trustworthy when a market was recorded through to actual settlement.
Returns `None` rather than guessing whenever the last recorded snapshot
isn't CLOSED or carries no resolved runner statuses — never infer a
winner from price alone (e.g. "shortest price = winner"), which would
silently fabricate ground truth instead of reporting that none was
captured.
"""

from __future__ import annotations

from betfair_trading.betfair.models import MarketStatus, RunnerStatus
from betfair_trading.database.storage import SnapshotStore


def extract_win_outcomes(store: SnapshotStore, market_id: str) -> dict[str, bool] | None:
    """selection_id -> True (won) / False (lost) for runners resolved in
    the market's final recorded snapshot. `None` if the market was never
    recorded through to CLOSED, or no runner statuses were resolved.
    """
    snapshots = store.read_market_snapshots(market_id)
    if not snapshots:
        return None

    last = snapshots[-1]
    if last.status is not MarketStatus.CLOSED:
        return None

    outcomes: dict[str, bool] = {}
    for runner in last.runners:
        if runner.status is RunnerStatus.WINNER:
            outcomes[runner.selection_id] = True
        elif runner.status is RunnerStatus.LOSER:
            outcomes[runner.selection_id] = False

    return outcomes or None
