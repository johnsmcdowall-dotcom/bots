"""The structured completed-trade record the spec's LEARNING LOOP section
asks for, plus per-league and goal-time-band performance aggregation from
a list of them — how the system tells whether the 30/50/70-minute timing
and any given league are genuinely working, per real (or, in this
environment, synthetic-for-now — see docs/PLAN.md) results.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from betfair_trading.football.over_1_5_scalp.state import TradeStatus

MIN_LEAGUE_SAMPLE_SIZE = 20  # spec: "require statistically meaningful evidence" before flagging a league


@dataclass(frozen=True)
class CompletedTrade:
    """One fully-resolved match's trade record — the unit both stats.py
    and backtest.py operate on."""

    match_id: str
    league: str
    kickoff: datetime
    prematch_score: float
    first_entry_minute: float | None
    first_entry_price: float | None
    first_entry_stake: float | None
    second_entry_taken: bool
    second_entry_price: float | None
    second_entry_stake: float | None
    second_entry_edge: float | None
    goal_minute: float | None
    exit_status: TradeStatus
    exit_reason: str
    exit_price: float | None  # the green-up lay price, or None if held to full settlement
    total_staked: float
    gross_profit_loss: float
    commission_paid: float
    net_profit_loss: float


# --- league stats --------------------------------------------------------


@dataclass(frozen=True)
class LeagueStats:
    league: str
    trades: int
    wins: int
    losses: int
    strike_rate: float | None
    avg_entry_odds: float | None
    avg_exit_odds: float | None
    roi: float | None  # net_profit_loss summed / total_staked summed
    profit_factor: float | None  # sum(winning net P&L) / abs(sum(losing net P&L))
    max_drawdown: float | None  # currency, off the chronological cumulative net P&L curve
    avg_goal_minute: float | None
    avg_pnl: float | None  # mean net P&L per trade (currency)
    expectancy: float | None  # mean of (per-trade net P&L / per-trade stake) -- unweighted per-trade return
    sharpe_like: float | None  # mean(net P&L) / stdev(net P&L)
    flagged_negative_expectancy: bool  # only ever True with >= min_sample_size trades


def max_drawdown_from_pnls(chronological_pnls: Sequence[float]) -> float | None:
    if not chronological_pnls:
        return None
    cumulative = 0.0
    peak = 0.0
    worst = 0.0
    for pnl in chronological_pnls:
        cumulative += pnl
        peak = max(peak, cumulative)
        worst = min(worst, cumulative - peak)
    return worst  # <= 0; report as a negative number (a drawdown)


def _single_league_stats(league: str, trades: Sequence[CompletedTrade], min_sample_size: int) -> LeagueStats:
    n = len(trades)
    wins = sum(1 for t in trades if t.net_profit_loss > 0)
    losses = n - wins

    entry_odds = [t.first_entry_price for t in trades if t.first_entry_price is not None]
    exit_odds = [t.exit_price for t in trades if t.exit_price is not None]
    goal_minutes = [t.goal_minute for t in trades if t.goal_minute is not None]

    net_pnls = [t.net_profit_loss for t in trades]
    total_staked = sum(t.total_staked for t in trades)
    winning_pnls = [p for p in net_pnls if p > 0]
    losing_pnls = [p for p in net_pnls if p < 0]

    roi = (sum(net_pnls) / total_staked) if total_staked > 0 else None
    profit_factor = (sum(winning_pnls) / abs(sum(losing_pnls))) if losing_pnls and sum(losing_pnls) != 0 else None
    avg_pnl = (sum(net_pnls) / n) if n else None

    per_trade_returns = [t.net_profit_loss / t.total_staked for t in trades if t.total_staked > 0]
    expectancy = (sum(per_trade_returns) / len(per_trade_returns)) if per_trade_returns else None

    sharpe_like = None
    if n >= 2:
        mean_pnl = sum(net_pnls) / n
        variance = sum((p - mean_pnl) ** 2 for p in net_pnls) / (n - 1)
        stdev = math.sqrt(variance)
        if stdev > 0:
            sharpe_like = mean_pnl / stdev

    chronological = [t.net_profit_loss for t in sorted(trades, key=lambda t: t.kickoff)]

    flagged = n >= min_sample_size and avg_pnl is not None and avg_pnl < 0

    return LeagueStats(
        league=league,
        trades=n,
        wins=wins,
        losses=losses,
        strike_rate=(wins / n) if n else None,
        avg_entry_odds=(sum(entry_odds) / len(entry_odds)) if entry_odds else None,
        avg_exit_odds=(sum(exit_odds) / len(exit_odds)) if exit_odds else None,
        roi=roi,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown_from_pnls(chronological),
        avg_goal_minute=(sum(goal_minutes) / len(goal_minutes)) if goal_minutes else None,
        avg_pnl=avg_pnl,
        expectancy=expectancy,
        sharpe_like=sharpe_like,
        flagged_negative_expectancy=flagged,
    )


def compute_league_stats(
    trades: Sequence[CompletedTrade], min_sample_size: int = MIN_LEAGUE_SAMPLE_SIZE
) -> dict[str, LeagueStats]:
    by_league: dict[str, list[CompletedTrade]] = defaultdict(list)
    for trade in trades:
        by_league[trade.league].append(trade)
    return {league: _single_league_stats(league, league_trades, min_sample_size) for league, league_trades in by_league.items()}


# --- time-band stats -------------------------------------------------------

TIME_BANDS: tuple[tuple[float, float, str], ...] = (
    (30, 35, "30-35"),
    (36, 40, "36-40"),
    (41, 45, "41-45+"),
    (46, 50, "46-50"),
    (51, 55, "51-55"),
    (56, 60, "56-60"),
    (61, 65, "61-65"),
    (66, 70, "66-70"),
    (71, math.inf, "71+"),
)


def time_band_for_minute(minute: float) -> str | None:
    for low, high, label in TIME_BANDS:
        if low <= minute <= high:
            return label
    return None


@dataclass(frozen=True)
class TimeBandStats:
    band_label: str
    goal_count: int
    avg_pnl: float | None


def compute_time_band_stats(trades: Sequence[CompletedTrade]) -> tuple[TimeBandStats, ...]:
    results = []
    for low, high, label in TIME_BANDS:
        in_band = [t for t in trades if t.goal_minute is not None and low <= t.goal_minute <= high]
        pnls = [t.net_profit_loss for t in in_band]
        results.append(TimeBandStats(label, len(in_band), (sum(pnls) / len(pnls)) if pnls else None))
    return tuple(results)
