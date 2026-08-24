"""Stake sizing for OVER_1_5_GOALS_SCALP — wired to the platform's
existing risk/limits.py rather than inventing a parallel risk system.

THE BANKROLL RULE, stated precisely because getting this wrong is exactly
the kind of bug that quietly turns a controlled strategy into an
uncontrolled one: "50% stake" means 50% of THIS MATCH's predetermined
maximum exposure, never 50% of the total bankroll. Bankroll is read
exactly ONCE, in `max_match_exposure`, to compute the match's ceiling;
every stake below that point is a fraction of that ceiling, never of
bankroll directly.

Never increased after a loss — nothing in this module reads a match's own
trade history or the bankroll's recent trajectory to decide sizing, so
there is no code path by which a loss could inflate the next stake. No
Martingale, no loss chasing, by construction rather than by convention.
"""

from __future__ import annotations

from dataclasses import dataclass

from betfair_trading.football.over_1_5_scalp.config import Over15ScalpConfig
from betfair_trading.risk.limits import RiskLimits


def max_match_exposure(bankroll: float, config: Over15ScalpConfig, risk_limits: RiskLimits) -> float:
    """The ONLY function in this module that reads bankroll. Takes the
    stricter of this strategy's own configured risk fraction
    (`config.max_bankroll_risk`) and the platform-wide correlated-
    exposure-per-football-match cap (risk/limits.py) — a strategy config
    can tighten the platform limit, never loosen it.
    """
    if bankroll <= 0:
        raise ValueError("bankroll must be positive")
    strategy_cap = bankroll * config.max_bankroll_risk
    platform_cap = bankroll * (risk_limits.max_correlated_exposure_per_football_match_pct / 100.0)
    return min(strategy_cap, platform_cap)


@dataclass(frozen=True)
class StakeCalculation:
    max_match_exposure: float
    first_entry_stake: float
    second_entry_max_stake: float


def compute_stake_plan(bankroll: float, config: Over15ScalpConfig, risk_limits: RiskLimits) -> StakeCalculation:
    """The full picture for a qualifying match: what the match's ceiling
    is, and what each entry stage's stake would be at full approval —
    computed up front so a dashboard/log can show the plan before either
    entry actually happens.
    """
    exposure = max_match_exposure(bankroll, config, risk_limits)
    return StakeCalculation(
        max_match_exposure=exposure,
        first_entry_stake=exposure * config.first_entry_fraction,
        second_entry_max_stake=exposure * config.second_entry_max_fraction,
    )


def compute_first_entry_stake(bankroll: float, config: Over15ScalpConfig, risk_limits: RiskLimits) -> float:
    return max_match_exposure(bankroll, config, risk_limits) * config.first_entry_fraction


def compute_second_entry_stake(
    bankroll: float,
    second_entry_fraction: float,
    config: Over15ScalpConfig,
    risk_limits: RiskLimits,
) -> float:
    """`second_entry_fraction` comes from scoring.second_entry_fraction()
    (0.0 / half / full of `second_entry_max_fraction`) — this function
    only converts that fraction of the match allocation into an actual
    stake; it never recomputes or overrides the fraction decision itself.
    """
    if second_entry_fraction > config.second_entry_max_fraction + 1e-9:
        raise ValueError(
            f"second_entry_fraction {second_entry_fraction} exceeds configured "
            f"max {config.second_entry_max_fraction}"
        )
    return max_match_exposure(bankroll, config, risk_limits) * second_entry_fraction
