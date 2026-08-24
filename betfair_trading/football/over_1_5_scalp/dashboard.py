"""Data aggregation for the spec's "Over 1.5 Goal Trading" dashboard
section — DATA ONLY, no UI. `dashboard/` itself is still a Phase 10
scaffold (docs/PLAN.md); this module produces the structured data a real
dashboard would render once that exists, and is fully usable today from a
notebook/REPL/CLI in the meantime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from betfair_trading.football.over_1_5_scalp.hedge import calculate_hedge
from betfair_trading.football.over_1_5_scalp.state import MatchTradeState, TradeStatus
from betfair_trading.football.over_1_5_scalp.stats import CompletedTrade, max_drawdown_from_pnls


@dataclass(frozen=True)
class MatchDashboardRow:
    match_id: str
    league: str
    status: TradeStatus
    minute: float | None
    home_score: int | None
    away_score: int | None
    back_price: float | None
    lay_price: float | None
    prematch_score: float | None
    live_pressure_score: float | None
    estimated_edge: float | None
    current_pnl: float | None  # mark-to-market: net P&L if greened right now, None if no open position
    target_hedge: float | None  # the lay stake required to green right now
    last_log_reason: str | None


def build_match_dashboard_row(
    state: MatchTradeState,
    minute: float | None = None,
    home_score: int | None = None,
    away_score: int | None = None,
    back_price: float | None = None,
    lay_price: float | None = None,
    prematch_score: float | None = None,
    live_pressure_score: float | None = None,
    estimated_edge: float | None = None,
    commission_rate: float = 0.05,
) -> MatchDashboardRow:
    current_pnl = None
    target_hedge = None
    if state.entries and lay_price is not None:
        hedge = calculate_hedge(state.entries, lay_price, commission_rate)
        current_pnl = hedge.locked_profit_net
        target_hedge = hedge.required_lay_stake

    return MatchDashboardRow(
        match_id=state.match_id, league=state.league, status=state.status, minute=minute,
        home_score=home_score, away_score=away_score, back_price=back_price, lay_price=lay_price,
        prematch_score=prematch_score, live_pressure_score=live_pressure_score, estimated_edge=estimated_edge,
        current_pnl=current_pnl, target_hedge=target_hedge,
        last_log_reason=state.log[-1][1] if state.log else None,
    )


_MONITORED_STATUSES = (TradeStatus.QUALIFIED, TradeStatus.WAITING_FOR_30, TradeStatus.MONITORING)
_ACTIVE_TRADE_STATUSES = (
    TradeStatus.ENTRY_1, TradeStatus.SECOND_ENTRY_APPROVED, TradeStatus.GOAL_DETECTED, TradeStatus.GREENING,
)
_CLOSED_STATUSES = (TradeStatus.CLOSED_PROFIT, TradeStatus.EARLY_EXIT, TradeStatus.HARD_TIME_EXIT, TradeStatus.NO_TRADE)


def categorise_rows(rows: Sequence[MatchDashboardRow]) -> dict[str, list[MatchDashboardRow]]:
    return {
        "watching_or_qualified": [r for r in rows if r.status in (TradeStatus.WATCHING, TradeStatus.QUALIFIED)],
        "first_entry_candidates": [r for r in rows if r.status is TradeStatus.WAITING_FOR_30],
        "monitored": [r for r in rows if r.status in _MONITORED_STATUSES],
        "second_entry_candidates": [
            r for r in rows if r.status is TradeStatus.MONITORING and r.minute is not None and 47 <= r.minute <= 53
        ],
        "active_trades": [r for r in rows if r.status in _ACTIVE_TRADE_STATUSES],
        "closed_today": [r for r in rows if r.status in _CLOSED_STATUSES],
    }


@dataclass(frozen=True)
class PerformanceSummary:
    daily_pnl: float
    all_time_pnl: float
    roi: float | None
    max_drawdown: float | None
    total_trades: int


def compute_performance_summary(all_trades: Sequence[CompletedTrade], today: date) -> PerformanceSummary:
    daily_pnl = sum(t.net_profit_loss for t in all_trades if t.kickoff.date() == today)
    all_time_pnl = sum(t.net_profit_loss for t in all_trades)
    total_staked = sum(t.total_staked for t in all_trades)
    roi = (all_time_pnl / total_staked) if total_staked > 0 else None
    chronological_pnls = [t.net_profit_loss for t in sorted(all_trades, key=lambda t: t.kickoff)]

    return PerformanceSummary(
        daily_pnl=daily_pnl,
        all_time_pnl=all_time_pnl,
        roi=roi,
        max_drawdown=max_drawdown_from_pnls(chronological_pnls),
        total_trades=len(all_trades),
    )


@dataclass(frozen=True)
class DashboardData:
    rows_by_category: dict[str, list[MatchDashboardRow]]
    performance: PerformanceSummary


def build_dashboard_data(
    rows: Sequence[MatchDashboardRow], all_trades: Sequence[CompletedTrade], today: date
) -> DashboardData:
    return DashboardData(
        rows_by_category=categorise_rows(rows),
        performance=compute_performance_summary(all_trades, today),
    )
