"""Version A/B/C/D backtesting per the spec, plus the replay runner and
metrics report.

IMPORTANT — exercised only against synthetic data in this environment.
There is no historical football match/odds dataset imported anywhere in
this platform, and no live football data provider is connected (see
data/football_feed.py). Every function here is proven correct against
hand-built `MatchRecord`s in tests/, which shows the *mechanics* are
right — it is not, and must not be read as, a real backtest result. See
docs/PLAN.md for what real historical data this needs before it can
answer the actual question ("is this strategy profitable after realistic
costs").

Version definitions (a `VersionBehaviour`, not just a config change — the
strategy LOGIC genuinely differs between them):

  A — original manual: blind 50/50 timing, no pre-match or live filters
      at either entry, green after goal, hard exit at 70.
  B — A + pre-match filtering gates the FIRST entry (second entry stays
      blind/manual, exactly the spec's "pre-match filtering + manual timing").
  C — B + live-stat confirmation gates BOTH entries (no EV/edge calc yet).
  D — full adaptive: EV-based second entry (requires a model probability
      per snapshot — see MatchMinuteSnapshot) and pressure-decay exit.

Chronological, walk-forward discipline: `run_backtest` processes matches
in kickoff order and compounds bankroll trade-by-trade (each match's stake
is sized off the bankroll *as it stood after every earlier match*, not the
starting bankroll) — never shuffled, matching the "never random-shuffle
financial/exchange time series" rule used everywhere else in this
platform. `walk_forward_split` below does the train/test split the spec
asks for ("do not optimise thresholds on the entire dataset").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from betfair_trading.football.over_1_5_scalp.config import Over15ScalpConfig
from betfair_trading.football.over_1_5_scalp.hedge import BackEntry, calculate_hedge
from betfair_trading.football.over_1_5_scalp.risk import compute_first_entry_stake, compute_second_entry_stake
from betfair_trading.football.over_1_5_scalp.scoring import (
    LiveInputs,
    PrematchScoreResult,
    live_goal_pressure_score,
    second_entry_edge,
    second_entry_fraction,
)
from betfair_trading.football.over_1_5_scalp.state import (
    MarketQuality,
    RedCardImpact,
    TradeStatus,
    check_market_quality,
    evaluate_no_goal_exit,
    evaluate_pressure_decay_exit,
    evaluate_red_card,
    evaluate_second_entry,
    qualify_prematch,
)
from betfair_trading.football.over_1_5_scalp.stats import CompletedTrade
from betfair_trading.risk.limits import RiskLimits


@dataclass(frozen=True)
class VersionBehaviour:
    name: str
    require_prematch_filter: bool
    require_live_pressure_filter: bool
    require_second_entry_edge: bool
    enable_pressure_decay_exit: bool


VERSION_A = VersionBehaviour("A_original_manual", False, False, False, False)
VERSION_B = VersionBehaviour("B_prematch_filter_manual_timing", True, False, False, False)
VERSION_C = VersionBehaviour("C_prematch_and_live_confirmation", True, True, False, False)
VERSION_D = VersionBehaviour("D_full_adaptive", True, True, True, True)
ALL_VERSIONS: tuple[VersionBehaviour, ...] = (VERSION_A, VERSION_B, VERSION_C, VERSION_D)


@dataclass(frozen=True)
class MatchMinuteSnapshot:
    minute: float
    home_score: int
    away_score: int
    live_inputs: LiveInputs
    back_odds: float
    lay_odds: float
    market: MarketQuality
    model_probability_two_plus_goals: float | None = None  # required for Version D's edge calc; None elsewhere is fine
    red_card_impact: RedCardImpact | None = None


@dataclass(frozen=True)
class MatchRecord:
    match_id: str
    league: str
    kickoff: datetime
    prematch: PrematchScoreResult
    minutes: tuple[MatchMinuteSnapshot, ...]  # sorted ascending by minute


def _empty_trade(match: MatchRecord, reason: str) -> CompletedTrade:
    return CompletedTrade(
        match_id=match.match_id, league=match.league, kickoff=match.kickoff,
        prematch_score=match.prematch.score, first_entry_minute=None, first_entry_price=None,
        first_entry_stake=None, second_entry_taken=False, second_entry_price=None, second_entry_stake=None,
        second_entry_edge=None, goal_minute=None, exit_status=TradeStatus.NO_TRADE, exit_reason=reason,
        exit_price=None, total_staked=0.0, gross_profit_loss=0.0, commission_paid=0.0, net_profit_loss=0.0,
    )


def _close_via_hedge(
    entries: list[BackEntry], lay_price: float, commission_rate: float, exit_status: TradeStatus, exit_reason: str,
    match: MatchRecord, first_entry_minute: float, first_entry_price: float, first_entry_stake: float,
    second_entry_taken: bool, second_entry_price: float | None, second_entry_stake: float | None,
    second_entry_edge_value: float | None, goal_minute: float | None,
) -> CompletedTrade:
    hedge = calculate_hedge(entries, lay_price, commission_rate)
    return CompletedTrade(
        match_id=match.match_id, league=match.league, kickoff=match.kickoff, prematch_score=match.prematch.score,
        first_entry_minute=first_entry_minute, first_entry_price=first_entry_price, first_entry_stake=first_entry_stake,
        second_entry_taken=second_entry_taken, second_entry_price=second_entry_price, second_entry_stake=second_entry_stake,
        second_entry_edge=second_entry_edge_value, goal_minute=goal_minute, exit_status=exit_status,
        exit_reason=exit_reason, exit_price=lay_price, total_staked=hedge.total_back_stake,
        gross_profit_loss=hedge.locked_profit_gross, commission_paid=hedge.commission_on_locked_profit,
        net_profit_loss=hedge.locked_profit_net,
    )


def _hard_exit_trade(
    entries: list[BackEntry], match: MatchRecord, exit_minute: float, exit_lay_price: float, commission_rate: float,
    first_entry_minute: float, first_entry_price: float, first_entry_stake: float,
    second_entry_taken: bool, second_entry_price: float | None, second_entry_stake: float | None,
    second_entry_edge_value: float | None, status: TradeStatus, reason: str,
) -> CompletedTrade:
    # A "controlled loss" hard exit is still executed as a hedge/close at
    # the current market price -- there is no code path that just abandons
    # a position and hopes, per the spec's "never allow the position to
    # run uncontrolled" instruction.
    return _close_via_hedge(
        entries, exit_lay_price, commission_rate, status, reason, match, first_entry_minute, first_entry_price,
        first_entry_stake, second_entry_taken, second_entry_price, second_entry_stake, second_entry_edge_value,
        goal_minute=None,
    )


def replay_single_match(
    match: MatchRecord,
    version: VersionBehaviour,
    config: Over15ScalpConfig,
    bankroll: float,
    risk_limits: RiskLimits,
) -> CompletedTrade:
    """Pure function: one match's full data in, one CompletedTrade out.
    Never mutates `match`; bankroll is a snapshot (the CURRENT bankroll at
    this match's kickoff, per run_backtest's compounding loop below).
    """
    if version.require_prematch_filter:
        prematch_decision = qualify_prematch(match.prematch, config)
        if not prematch_decision.approved:
            return _empty_trade(match, prematch_decision.reason)

    entries: list[BackEntry] = []
    first_entry_minute = first_entry_price = first_entry_stake = None
    second_entry_taken = False
    second_entry_price = second_entry_stake = second_entry_edge_value = None
    commission_rate = config.commission_rate

    for snapshot in match.minutes:
        score = (snapshot.home_score, snapshot.away_score)

        # Red card handling applies in every version -- a safety gate, not
        # a strategy-logic difference between manual and adaptive versions.
        if config.enable_red_card_filter and snapshot.red_card_impact is not None:
            red_card_decision = evaluate_red_card(snapshot.red_card_impact, config)
            if not red_card_decision.approved:
                if entries and red_card_decision.status is TradeStatus.EARLY_EXIT:
                    return _close_via_hedge(
                        entries, snapshot.lay_odds, commission_rate, TradeStatus.EARLY_EXIT,
                        red_card_decision.reason, match, first_entry_minute, first_entry_price, first_entry_stake,
                        second_entry_taken, second_entry_price, second_entry_stake, second_entry_edge_value,
                        goal_minute=None,
                    )
                if not entries:
                    return _empty_trade(match, red_card_decision.reason)

        # Goal detection -- as soon as score moves off 0-0 with an open
        # position, green up (IMMEDIATE_GREEN is the only mode this replay
        # implements; DYNAMIC_GREEN needs Phase 6's execution simulator to
        # model the wait realistically, so it is deliberately not attempted
        # here rather than faked).
        if score != (0, 0) and entries:
            return _close_via_hedge(
                entries, snapshot.lay_odds, commission_rate, TradeStatus.CLOSED_PROFIT, "goal scored -- greened up",
                match, first_entry_minute, first_entry_price, first_entry_stake, second_entry_taken,
                second_entry_price, second_entry_stake, second_entry_edge_value, goal_minute=snapshot.minute,
            )
        if score != (0, 0) and not entries:
            return _empty_trade(match, f"goal at minute {snapshot.minute} before any entry was taken")

        live_score = live_goal_pressure_score(snapshot.live_inputs).score

        # First entry.
        if not entries and config.first_entry_window[0] <= snapshot.minute <= config.first_entry_window[1]:
            market_decision = check_market_quality(snapshot.market, config)
            live_ok = (not version.require_live_pressure_filter) or (live_score >= config.min_live_pressure_score)
            if market_decision.approved and live_ok:
                stake = compute_first_entry_stake(bankroll, config, risk_limits)
                entries.append(BackEntry(stake, snapshot.back_odds))
                first_entry_minute, first_entry_price, first_entry_stake = snapshot.minute, snapshot.back_odds, stake

        # Second entry.
        elif (
            entries and not second_entry_taken
            and config.second_entry_window[0] <= snapshot.minute <= config.second_entry_window[1]
        ):
            if version.require_second_entry_edge:
                if snapshot.model_probability_two_plus_goals is not None:
                    edge = second_entry_edge(snapshot.model_probability_two_plus_goals, snapshot.back_odds)
                    decision = evaluate_second_entry(
                        snapshot.minute, snapshot.home_score, snapshot.away_score, live_goal_pressure_score(snapshot.live_inputs),
                        edge, snapshot.market, config,
                    )
                    if decision.approved:
                        fraction = second_entry_fraction(edge, live_score, config)
                        if fraction > 0:
                            stake = compute_second_entry_stake(bankroll, fraction, config, risk_limits)
                            entries.append(BackEntry(stake, snapshot.back_odds))
                            second_entry_taken = True
                            second_entry_price, second_entry_stake, second_entry_edge_value = snapshot.back_odds, stake, edge
            else:
                # Versions A/B/C: manual timing -- blind (or live-pressure-gated
                # for C) full second stake, never edge-gated. Still market-quality gated.
                live_ok = (not version.require_live_pressure_filter) or (live_score >= config.min_live_pressure_score)
                if check_market_quality(snapshot.market, config).approved and live_ok:
                    stake = compute_second_entry_stake(bankroll, config.second_entry_max_fraction, config, risk_limits)
                    entries.append(BackEntry(stake, snapshot.back_odds))
                    second_entry_taken = True
                    second_entry_price, second_entry_stake = snapshot.back_odds, stake

        # Pressure-decay early exit (Version D only).
        if entries and version.enable_pressure_decay_exit and config.enable_pressure_decay_exit:
            decay_decision = evaluate_pressure_decay_exit(live_score, config.pressure_decay_threshold, config)
            if decay_decision.approved:
                return _close_via_hedge(
                    entries, snapshot.lay_odds, commission_rate, TradeStatus.EARLY_EXIT, decay_decision.reason,
                    match, first_entry_minute, first_entry_price, first_entry_stake, second_entry_taken,
                    second_entry_price, second_entry_stake, second_entry_edge_value, goal_minute=None,
                )

        # Hard time exit.
        if entries:
            exit_decision = evaluate_no_goal_exit(snapshot.minute, snapshot.home_score, snapshot.away_score, config)
            if exit_decision.approved:
                return _hard_exit_trade(
                    entries, match, snapshot.minute, snapshot.lay_odds, commission_rate, first_entry_minute,
                    first_entry_price, first_entry_stake, second_entry_taken, second_entry_price,
                    second_entry_stake, second_entry_edge_value, TradeStatus.HARD_TIME_EXIT, exit_decision.reason,
                )

    if entries:
        # Match data ran out (full time reached) with a position still
        # open and no goal -- close at the last available price rather
        # than leave it unresolved.
        last = match.minutes[-1]
        return _hard_exit_trade(
            entries, match, last.minute, last.lay_odds, commission_rate, first_entry_minute, first_entry_price,
            first_entry_stake, second_entry_taken, second_entry_price, second_entry_stake, second_entry_edge_value,
            TradeStatus.HARD_TIME_EXIT, "match data ended with position still open -- closed at last available price",
        )
    return _empty_trade(match, "no qualifying entry window reached (0-0 requirement, market quality, or live pressure)")


@dataclass(frozen=True)
class BacktestReport:
    version_name: str
    total_trades: int  # trades with a non-zero stake taken (excludes NO_TRADE)
    winning_trades: int
    losing_trades: int
    strike_rate: float | None
    gross_profit: float
    net_profit: float
    commission: float
    roi: float | None
    profit_factor: float | None
    max_drawdown: float | None
    average_win: float | None
    average_loss: float | None
    expectancy_per_trade: float | None
    longest_losing_run: int
    monthly_returns: dict[str, float]  # "YYYY-MM" -> net profit
    bankroll_curve: list[float]  # bankroll after each traded match, chronological
    completed_trades: tuple[CompletedTrade, ...]


def _longest_losing_run(chronological_net_pnls: Sequence[float]) -> int:
    longest = current = 0
    for pnl in chronological_net_pnls:
        if pnl < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def run_backtest(
    matches: Sequence[MatchRecord],
    version: VersionBehaviour,
    config: Over15ScalpConfig,
    starting_bankroll: float,
    risk_limits: RiskLimits = RiskLimits(),
) -> BacktestReport:
    """Chronological, compounding: matches are processed in kickoff order
    (never shuffled) and each match's stake is sized off the bankroll AS
    IT STOOD after every earlier match, not the starting figure — so the
    reported bankroll_curve is a genuine compounding simulation, not a
    fixed-stake approximation of one.
    """
    ordered = sorted(matches, key=lambda m: m.kickoff)

    bankroll = starting_bankroll
    completed: list[CompletedTrade] = []
    bankroll_curve: list[float] = []

    for match in ordered:
        trade = replay_single_match(match, version, config, bankroll, risk_limits)
        if trade.total_staked > 0:
            bankroll += trade.net_profit_loss
            completed.append(trade)
            bankroll_curve.append(bankroll)

    net_pnls = [t.net_profit_loss for t in completed]
    winners = [p for p in net_pnls if p > 0]
    losers = [p for p in net_pnls if p < 0]
    total_staked = sum(t.total_staked for t in completed)

    monthly: dict[str, float] = {}
    for t in completed:
        key = f"{t.kickoff.year:04d}-{t.kickoff.month:02d}"
        monthly[key] = monthly.get(key, 0.0) + t.net_profit_loss

    peak = 0.0
    cumulative = 0.0
    worst_drawdown = 0.0
    for p in net_pnls:
        cumulative += p
        peak = max(peak, cumulative)
        worst_drawdown = min(worst_drawdown, cumulative - peak)

    return BacktestReport(
        version_name=version.name,
        total_trades=len(completed),
        winning_trades=len(winners),
        losing_trades=len(losers),
        strike_rate=(len(winners) / len(completed)) if completed else None,
        gross_profit=sum(t.gross_profit_loss for t in completed),
        net_profit=sum(net_pnls),
        commission=sum(t.commission_paid for t in completed),
        roi=(sum(net_pnls) / total_staked) if total_staked > 0 else None,
        profit_factor=(sum(winners) / abs(sum(losers))) if losers and sum(losers) != 0 else None,
        max_drawdown=worst_drawdown if completed else None,
        average_win=(sum(winners) / len(winners)) if winners else None,
        average_loss=(sum(losers) / len(losers)) if losers else None,
        expectancy_per_trade=(sum(net_pnls) / len(completed)) if completed else None,
        longest_losing_run=_longest_losing_run(net_pnls),
        monthly_returns=monthly,
        bankroll_curve=bankroll_curve,
        completed_trades=tuple(completed),
    )


def walk_forward_split(matches: Sequence[MatchRecord], train_fraction: float = 0.7) -> tuple[list[MatchRecord], list[MatchRecord]]:
    """Chronological train/test split — never shuffled, per the spec's
    "do not optimise thresholds on the entire dataset and then claim the
    resulting performance as genuine." Thresholds (min_prematch_score,
    min_live_pressure_score, min_second_entry_edge, entry/exit minutes,
    etc.) should be selected using only the train split; the test split's
    `run_backtest` result is the one that may be reported as
    out-of-sample.
    """
    if not (0.0 < train_fraction < 1.0):
        raise ValueError("train_fraction must be in (0, 1)")
    ordered = sorted(matches, key=lambda m: m.kickoff)
    cut = int(len(ordered) * train_fraction)
    return ordered[:cut], ordered[cut:]
