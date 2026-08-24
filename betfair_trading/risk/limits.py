"""Configurable risk limits. Config only — no enforcement engine here yet
(that's the Phase 8 portfolio manager + Phase 6/11 execution layer's job).
This module exists in Phase 1 so every later phase reads limits from one
place instead of scattering magic numbers, and so the numbers in the spec
are visible/reviewable/changeable without touching strategy code.

All defaults below are research starting points from the spec, not
recommendations — see docs/PLAN.md Phase 9 (Monte Carlo) for how these
should eventually be chosen on risk-adjusted grounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from betfair_trading.core.interfaces import TradeGrade


@dataclass(frozen=True)
class GradeRiskBand:
    """Bankroll-risk-% range for a given trade grade."""

    minimum_pct: float
    maximum_pct: float


@dataclass(frozen=True)
class DrawdownResponseLevel:
    """At `drawdown_pct` peak-to-current drawdown, cut sizing by `risk_reduction_pct`."""

    drawdown_pct: float
    risk_reduction_pct: float
    description: str


@dataclass(frozen=True)
class RiskLimits:
    # Per-trade bankroll risk, by grade. Live trading is initially A+/A only
    # (enforced by whoever filters signals for execution, not here).
    grade_risk_bands: dict[TradeGrade, GradeRiskBand] = field(
        default_factory=lambda: {
            TradeGrade.A_PLUS: GradeRiskBand(1.0, 1.5),
            TradeGrade.A: GradeRiskBand(0.6, 1.0),
            TradeGrade.B: GradeRiskBand(0.25, 0.5),
        }
    )

    max_single_trade_risk_pct: float = 1.5
    normal_trade_risk_pct: float = 1.0

    max_exposure_per_horse_market_pct: float = 2.0
    max_correlated_exposure_per_football_match_pct: float = 2.5

    soft_daily_stop_pct: float = -3.0
    hard_daily_stop_pct: float = -5.0
    soft_stop_risk_reduction_pct: float = 50.0

    drawdown_response: tuple[DrawdownResponseLevel, ...] = field(
        default_factory=lambda: (
            DrawdownResponseLevel(10.0, 20.0, "reduce sizing ~20%"),
            DrawdownResponseLevel(15.0, 40.0, "reduce sizing ~40%"),
            DrawdownResponseLevel(20.0, 100.0, "conservative mode (block new signals below A+)"),
            DrawdownResponseLevel(25.0, 100.0, "disable live execution pending review"),
        )
    )

    def risk_reduction_for_drawdown(self, drawdown_pct: float) -> float:
        """Highest applicable risk_reduction_pct for the given drawdown, else 0."""
        applicable = [
            level.risk_reduction_pct
            for level in self.drawdown_response
            if drawdown_pct >= level.drawdown_pct
        ]
        return max(applicable, default=0.0)

    def band_for_grade(self, grade: TradeGrade) -> GradeRiskBand | None:
        return self.grade_risk_bands.get(grade)
