from datetime import date, datetime, timezone

from betfair_trading.football.over_1_5_scalp.dashboard import (
    build_dashboard_data,
    build_match_dashboard_row,
    categorise_rows,
    compute_performance_summary,
)
from betfair_trading.football.over_1_5_scalp.hedge import BackEntry
from betfair_trading.football.over_1_5_scalp.state import MatchTradeState, TradeStatus
from betfair_trading.football.over_1_5_scalp.stats import CompletedTrade


def _completed_trade(kickoff, net_profit_loss, total_staked=10.0):
    return CompletedTrade(
        match_id="m", league="EPL", kickoff=kickoff, prematch_score=80.0, first_entry_minute=30.0,
        first_entry_price=1.8, first_entry_stake=total_staked, second_entry_taken=False, second_entry_price=None,
        second_entry_stake=None, second_entry_edge=None, goal_minute=40.0, exit_status=TradeStatus.CLOSED_PROFIT,
        exit_reason="greened", exit_price=1.2, total_staked=total_staked, gross_profit_loss=net_profit_loss,
        commission_paid=0.0, net_profit_loss=net_profit_loss,
    )


def test_row_with_open_position_computes_mark_to_market_pnl():
    state = MatchTradeState(match_id="m1", league="EPL", status=TradeStatus.ENTRY_1)
    state.add_entry(BackEntry(10.0, 1.8))

    row = build_match_dashboard_row(state, minute=35, home_score=0, away_score=0, lay_price=1.5, commission_rate=0.05)

    assert row.current_pnl is not None
    assert row.target_hedge is not None
    assert row.current_pnl > 0  # price shortened from 1.8 to 1.5 -- a paper profit


def test_row_with_no_position_has_no_pnl():
    state = MatchTradeState(match_id="m1", league="EPL", status=TradeStatus.WATCHING)
    row = build_match_dashboard_row(state, lay_price=1.5)
    assert row.current_pnl is None
    assert row.target_hedge is None


def test_row_carries_last_log_reason():
    state = MatchTradeState(match_id="m1", league="EPL")
    state.log.append((TradeStatus.QUALIFIED, "prematch_goal_score=85 >= threshold 70"))
    row = build_match_dashboard_row(state)
    assert row.last_log_reason == "prematch_goal_score=85 >= threshold 70"


def test_categorise_rows_buckets_by_status():
    rows = [
        build_match_dashboard_row(MatchTradeState("m1", "EPL", status=TradeStatus.WAITING_FOR_30)),
        build_match_dashboard_row(MatchTradeState("m2", "EPL", status=TradeStatus.ENTRY_1)),
        build_match_dashboard_row(MatchTradeState("m3", "EPL", status=TradeStatus.MONITORING), minute=49),
        build_match_dashboard_row(MatchTradeState("m4", "EPL", status=TradeStatus.CLOSED_PROFIT)),
    ]
    categories = categorise_rows(rows)

    assert [r.match_id for r in categories["first_entry_candidates"]] == ["m1"]
    assert [r.match_id for r in categories["active_trades"]] == ["m2"]
    assert [r.match_id for r in categories["second_entry_candidates"]] == ["m3"]
    assert [r.match_id for r in categories["closed_today"]] == ["m4"]


def test_performance_summary_daily_vs_all_time():
    today = date(2026, 3, 5)
    trades = [
        _completed_trade(datetime(2026, 3, 5, tzinfo=timezone.utc), net_profit_loss=5.0),
        _completed_trade(datetime(2026, 3, 4, tzinfo=timezone.utc), net_profit_loss=-2.0),
    ]
    summary = compute_performance_summary(trades, today)

    assert summary.daily_pnl == 5.0
    assert summary.all_time_pnl == 3.0
    assert summary.total_trades == 2
    assert round(summary.roi, 6) == round(3.0 / 20.0, 6)


def test_performance_summary_empty_trades():
    summary = compute_performance_summary([], date(2026, 1, 1))
    assert summary.daily_pnl == 0.0
    assert summary.all_time_pnl == 0.0
    assert summary.roi is None
    assert summary.max_drawdown is None


def test_build_dashboard_data_combines_both():
    rows = [build_match_dashboard_row(MatchTradeState("m1", "EPL", status=TradeStatus.WAITING_FOR_30))]
    trades = [_completed_trade(datetime(2026, 3, 5, tzinfo=timezone.utc), net_profit_loss=5.0)]
    data = build_dashboard_data(rows, trades, today=date(2026, 3, 5))

    assert "first_entry_candidates" in data.rows_by_category
    assert data.performance.all_time_pnl == 5.0
