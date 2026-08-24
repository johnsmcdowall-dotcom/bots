"""The OVER_1_5_GOALS_SCALP trade lifecycle: the spec's exact status
vocabulary (WATCHING...NO_TRADE) plus the pure decision functions that
drive transitions between them.

Every decision function returns a `Decision` (approved/rejected, the
resulting status, and a human-readable reason) rather than raising or
silently doing nothing — per the spec's explicit logging requirement,
every rejection must say why (e.g. "NO_TRADE: live_pressure=51 below
threshold 65"), and every acceptance is just as informative. Decision
functions are pure (state in, decision out); `MatchTradeState.apply()` is
the one place that actually mutates a match's tracked state, so the
decision logic itself stays trivially unit-testable without needing a
live match running through it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from betfair_trading.football.over_1_5_scalp.config import GoalExitMode, Over15ScalpConfig
from betfair_trading.football.over_1_5_scalp.hedge import BackEntry, HedgeCalculation
from betfair_trading.football.over_1_5_scalp.scoring import AggregateScoreResult, PrematchScoreResult


class TradeStatus(str, Enum):
    WATCHING = "WATCHING"
    QUALIFIED = "QUALIFIED"
    WAITING_FOR_30 = "WAITING_FOR_30"
    ENTRY_1 = "ENTRY_1"
    MONITORING = "MONITORING"
    SECOND_ENTRY_APPROVED = "SECOND_ENTRY_APPROVED"
    SECOND_ENTRY_REJECTED = "SECOND_ENTRY_REJECTED"
    GOAL_DETECTED = "GOAL_DETECTED"
    GREENING = "GREENING"
    CLOSED_PROFIT = "CLOSED_PROFIT"
    EARLY_EXIT = "EARLY_EXIT"
    HARD_TIME_EXIT = "70_MIN_EXIT"  # Python identifiers can't start with a digit; the *value* matches the spec exactly
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class Decision:
    approved: bool
    status: TradeStatus
    reason: str


@dataclass(frozen=True)
class MarketQuality:
    is_open: bool
    is_suspended: bool
    liquidity: float
    spread_ticks: int | None
    awaiting_var: bool = False
    data_latency_ok: bool = True


@dataclass(frozen=True)
class DataQuality:
    stale: bool = False
    conflicting_sources: bool = False
    unreliable: bool = False


class RedCardImpact(str, Enum):
    INCREASES_EXPECTED_GOALS = "INCREASES_EXPECTED_GOALS"
    DECREASES_EXPECTED_GOALS = "DECREASES_EXPECTED_GOALS"
    UNCERTAIN = "UNCERTAIN"


# --- gates ---------------------------------------------------------------


def check_market_quality(market: MarketQuality, config: Over15ScalpConfig) -> Decision:
    if not market.is_open or market.is_suspended:
        return Decision(False, TradeStatus.NO_TRADE, "market not open/tradeable")
    if market.awaiting_var:
        return Decision(False, TradeStatus.NO_TRADE, "recent goal awaiting VAR confirmation")
    if not market.data_latency_ok:
        return Decision(False, TradeStatus.NO_TRADE, "dangerous latency discrepancy between score feed and market")
    if market.liquidity < config.min_market_liquidity:
        return Decision(
            False, TradeStatus.NO_TRADE,
            f"liquidity {market.liquidity} below minimum {config.min_market_liquidity}",
        )
    if market.spread_ticks is None or market.spread_ticks > config.max_spread_ticks:
        return Decision(
            False, TradeStatus.NO_TRADE,
            f"spread {market.spread_ticks} exceeds maximum {config.max_spread_ticks}",
        )
    return Decision(True, TradeStatus.WAITING_FOR_30, "market quality OK")


def check_data_quality(data: DataQuality) -> Decision:
    if data.stale or data.conflicting_sources or data.unreliable:
        reason = "stale" if data.stale else ("conflicting data sources" if data.conflicting_sources else "unreliable data")
        return Decision(False, TradeStatus.NO_TRADE, f"data quality failure ({reason}) -- no new position opened")
    return Decision(True, TradeStatus.MONITORING, "data quality OK")


def evaluate_red_card(impact: RedCardImpact, config: Over15ScalpConfig) -> Decision:
    """Conservative default per the spec: DECREASES is an exit signal for
    an existing position; UNCERTAIN blocks new entry ("if uncertain, do
    not enter") without necessarily forcing an exit of one already open —
    the caller decides based on which phase the trade is in. All red-card
    situations should be logged separately for later research regardless
    of the decision (the spec is explicit about this); this function's
    `reason` string is written to support that.
    """
    if not config.enable_red_card_filter:
        return Decision(True, TradeStatus.MONITORING, "red-card filter disabled by config")
    if impact is RedCardImpact.DECREASES_EXPECTED_GOALS:
        return Decision(False, TradeStatus.EARLY_EXIT, "red card materially reduces expected goals")
    if impact is RedCardImpact.UNCERTAIN:
        return Decision(False, TradeStatus.NO_TRADE, "red card impact uncertain -- do not enter")
    return Decision(True, TradeStatus.MONITORING, "red card assessed as increasing expected goals")


# --- qualification / entries ----------------------------------------------


def qualify_prematch(prematch: PrematchScoreResult, config: Over15ScalpConfig) -> Decision:
    if prematch.competition_excluded:
        return Decision(False, TradeStatus.NO_TRADE, "competition excluded as statistically unreliable")
    if not prematch.sample_size_adequate:
        return Decision(False, TradeStatus.NO_TRADE, "insufficient sample size for reliable pre-match stats")
    if prematch.score < config.min_prematch_score:
        return Decision(
            False, TradeStatus.NO_TRADE,
            f"prematch_goal_score={prematch.score} below threshold {config.min_prematch_score}",
        )
    return Decision(
        True, TradeStatus.QUALIFIED,
        f"prematch_goal_score={prematch.score} >= threshold {config.min_prematch_score}",
    )


def evaluate_first_entry(
    minute: float,
    home_score: int,
    away_score: int,
    prematch: PrematchScoreResult,
    live: AggregateScoreResult,
    market: MarketQuality,
    config: Over15ScalpConfig,
) -> Decision:
    if not (config.first_entry_window[0] <= minute <= config.first_entry_window[1]):
        return Decision(
            False, TradeStatus.WAITING_FOR_30,
            f"minute={minute} outside first-entry window {config.first_entry_window}",
        )
    if config.require_score_0_0 and (home_score, away_score) != (0, 0):
        return Decision(False, TradeStatus.NO_TRADE, f"score {home_score}-{away_score} is not 0-0")

    market_decision = check_market_quality(market, config)
    if not market_decision.approved:
        return Decision(False, TradeStatus.NO_TRADE, market_decision.reason)

    if prematch.score < config.min_prematch_score:
        return Decision(
            False, TradeStatus.NO_TRADE,
            f"prematch_goal_score={prematch.score} below threshold {config.min_prematch_score}",
        )
    if live.score < config.min_live_pressure_score:
        return Decision(
            False, TradeStatus.NO_TRADE,
            f"live_goal_pressure_score={live.score} below threshold {config.min_live_pressure_score}",
        )
    return Decision(
        True, TradeStatus.ENTRY_1,
        f"prematch={prematch.score}, live_pressure={live.score} both clear threshold",
    )


def evaluate_second_entry(
    minute: float,
    home_score: int,
    away_score: int,
    live: AggregateScoreResult,
    edge: float,
    market: MarketQuality,
    config: Over15ScalpConfig,
) -> Decision:
    if not (config.second_entry_window[0] <= minute <= config.second_entry_window[1]):
        return Decision(
            False, TradeStatus.MONITORING,
            f"minute={minute} outside second-entry window {config.second_entry_window}",
        )
    if config.require_score_0_0 and (home_score, away_score) != (0, 0):
        return Decision(
            False, TradeStatus.MONITORING, f"score {home_score}-{away_score} is not 0-0 -- a goal already occurred"
        )

    market_decision = check_market_quality(market, config)
    if not market_decision.approved:
        return Decision(False, TradeStatus.SECOND_ENTRY_REJECTED, market_decision.reason)

    if edge < config.min_second_entry_edge:
        return Decision(
            False, TradeStatus.SECOND_ENTRY_REJECTED,
            f"model edge {edge:.1%} below required {config.min_second_entry_edge:.1%}",
        )
    return Decision(
        True, TradeStatus.SECOND_ENTRY_APPROVED,
        f"edge {edge:.1%} clears required {config.min_second_entry_edge:.1%}, live_pressure={live.score}",
    )


# --- exits -----------------------------------------------------------------


def on_goal_detected(config: Over15ScalpConfig) -> Decision:
    if config.goal_exit_mode is GoalExitMode.IMMEDIATE_GREEN:
        return Decision(True, TradeStatus.GOAL_DETECTED, "goal confirmed -- proceeding directly to green-up")
    return Decision(True, TradeStatus.GOAL_DETECTED, "goal confirmed -- dynamic-green evaluation window opened")


def evaluate_no_goal_exit(minute: float, home_score: int, away_score: int, config: Over15ScalpConfig) -> Decision:
    if (home_score, away_score) != (0, 0):
        return Decision(False, TradeStatus.MONITORING, "not applicable -- a goal has already occurred")
    if minute >= config.hard_exit_minute:
        return Decision(
            True, TradeStatus.HARD_TIME_EXIT,
            f"no goal by minute {minute} (hard exit at {config.hard_exit_minute})",
        )
    return Decision(False, TradeStatus.MONITORING, f"minute={minute} before hard exit {config.hard_exit_minute}")


def evaluate_pressure_decay_exit(current_live_score: float, decay_threshold: float, config: Over15ScalpConfig) -> Decision:
    if not config.enable_pressure_decay_exit:
        return Decision(False, TradeStatus.MONITORING, "pressure-decay exit disabled by config")
    if current_live_score < decay_threshold:
        return Decision(
            True, TradeStatus.EARLY_EXIT,
            f"live pressure decayed to {current_live_score} (threshold {decay_threshold})",
        )
    return Decision(
        False, TradeStatus.MONITORING,
        f"live pressure {current_live_score} still above decay threshold {decay_threshold}",
    )


# --- per-match state --------------------------------------------------------


@dataclass
class MatchTradeState:
    """Mutable per-match record — everything else in this module is pure
    functions of inputs; this is the one place a match's status/entries/
    log actually accumulate over the life of a trade.
    """

    match_id: str
    league: str
    status: TradeStatus = TradeStatus.WATCHING
    entries: list[BackEntry] = field(default_factory=list)
    goal_minute: float | None = None
    hedge: HedgeCalculation | None = None
    exit_reason: str | None = None
    log: list[tuple[TradeStatus, str]] = field(default_factory=list)

    def apply(self, decision: Decision) -> None:
        self.status = decision.status
        self.log.append((decision.status, decision.reason))

    def add_entry(self, entry: BackEntry) -> None:
        self.entries.append(entry)

    @property
    def total_matched_stake(self) -> float:
        return sum(e.stake for e in self.entries)

    @property
    def is_closed(self) -> bool:
        return self.status in (
            TradeStatus.CLOSED_PROFIT, TradeStatus.EARLY_EXIT, TradeStatus.HARD_TIME_EXIT, TradeStatus.NO_TRADE,
        )
