"""OVER_1_5_GOALS_SCALP configuration.

An independent, additive football strategy — nothing here touches
horse_racing/ or strategies/ (the existing horse-racing strategy modules).
Betfair Match Odds/Goals markets (Over/Under 1.5 Goals) are a single-
selection binary market (BACK "Over 1.5" / LAY "Over 1.5", exactly like a
horse's win market), so this module reuses betfair/ticks.py for the price
ladder and follows the same "editable config, not hard-coded numbers"
convention as risk/limits.py.

`Over15ScalpConfig.from_dict()` accepts exactly the flat dict shape given
in the spec (`OVER_1_5_CONFIG = {...}`) so that literal example can be
pasted in unchanged; the dataclass is the canonical, type-checked form
everything else in this package is written against.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GoalExitMode(str, Enum):
    IMMEDIATE_GREEN = "IMMEDIATE_GREEN"
    DYNAMIC_GREEN = "DYNAMIC_GREEN"


@dataclass(frozen=True)
class Over15ScalpConfig:
    enabled: bool = True

    first_entry_minute: int = 30
    first_entry_window: tuple[int, int] = (28, 35)
    first_entry_fraction: float = 0.50

    second_entry_minute: int = 50
    second_entry_window: tuple[int, int] = (47, 53)
    second_entry_max_fraction: float = 0.50

    hard_exit_minute: int = 70
    # spec: "allow optimisation testing from approximately 65-75 minutes"
    hard_exit_window: tuple[int, int] = (65, 75)

    min_prematch_score: float = 70.0
    min_live_pressure_score: float = 65.0
    min_second_entry_edge: float = 0.04  # 4 percentage points, spec's suggested test range is 3-7pp

    max_bankroll_risk: float = 0.01  # fraction of bankroll, NOT of the per-match allocation — see risk.py
    goal_exit_mode: GoalExitMode = GoalExitMode.IMMEDIATE_GREEN

    require_score_0_0: bool = True
    enable_pressure_decay_exit: bool = True
    enable_red_card_filter: bool = True

    # Market-quality gates (spec's "market open and tradeable... liquidity
    # above configurable minimum... spread below configurable maximum").
    min_market_liquidity: float = 200.0
    max_spread_ticks: int = 3

    # Dynamic-green mode's own strict time/risk limit (spec: "must have
    # strict time/risk limits... do not enable in production until
    # backtesting proves it improves risk-adjusted return" — default OFF
    # via goal_exit_mode=IMMEDIATE_GREEN regardless of this value).
    dynamic_green_max_wait_seconds: float = 45.0

    # Commission rate used by hedge.py's net-locked-profit calculation.
    commission_rate: float = 0.05

    # Below this live_goal_pressure_score, an open pre-goal position is a
    # pressure_decay_exit candidate (spec: "shots completely dry up... xG
    # stagnates... close early"). Only used when enable_pressure_decay_exit=True.
    pressure_decay_threshold: float = 30.0

    def __post_init__(self) -> None:
        if not (0.0 < self.first_entry_fraction <= 1.0):
            raise ValueError("first_entry_fraction must be in (0, 1]")
        if not (0.0 <= self.second_entry_max_fraction <= 1.0):
            raise ValueError("second_entry_max_fraction must be in [0, 1]")
        if self.first_entry_fraction + self.second_entry_max_fraction > 1.0 + 1e-9:
            raise ValueError("first_entry_fraction + second_entry_max_fraction must not exceed 1.0 of the match allocation")
        if self.first_entry_window[0] > self.first_entry_window[1]:
            raise ValueError("first_entry_window must be (low, high) with low <= high")
        if self.second_entry_window[0] > self.second_entry_window[1]:
            raise ValueError("second_entry_window must be (low, high) with low <= high")
        if not (0.0 <= self.min_prematch_score <= 100.0):
            raise ValueError("min_prematch_score must be in [0, 100]")
        if not (0.0 <= self.min_live_pressure_score <= 100.0):
            raise ValueError("min_live_pressure_score must be in [0, 100]")
        if self.max_bankroll_risk <= 0.0:
            raise ValueError("max_bankroll_risk must be positive")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Over15ScalpConfig":
        """Accepts the exact OVER_1_5_CONFIG dict shape from the spec
        (list-valued windows, string goal_exit_mode) and converts to the
        typed dataclass.
        """
        data = dict(raw)
        for window_key in ("first_entry_window", "second_entry_window", "hard_exit_window"):
            if window_key in data:
                data[window_key] = tuple(data[window_key])
        if "goal_exit_mode" in data and isinstance(data["goal_exit_mode"], str):
            data["goal_exit_mode"] = GoalExitMode(data["goal_exit_mode"])
        known_fields = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known_fields
        if unknown:
            raise ValueError(f"unknown Over15ScalpConfig field(s): {sorted(unknown)}")
        return cls(**data)


DEFAULT_CONFIG = Over15ScalpConfig()

# The spec's four backtest versions (docs/PLAN.md / backtest.py) as config
# presets layered on top of DEFAULT_CONFIG — see backtest.py for what each
# version actually gates (filtering vs. live-stat confirmation vs. EV-based
# second entry vs. pressure-decay exit are strategy-logic differences, not
# just config differences, so the presets here only capture the config-level
# knobs; backtest.py's VERSION_* constants are the authoritative definition).
