"""prematch_goal_score / live_goal_pressure_score: configurable, weighted
0-100 aggregate scores (per the spec's explicit instruction to build a
*scoring model*, not one hard-coded filter), plus the 50-minute EV/edge
calculation and its resulting second-entry stake fraction.

Every input is Optional — per the spec, "do NOT make every individual
statistic mandatory if data quality differs between providers." A missing
input simply drops out of the weighted average rather than forcing a
default value that would silently bias the score; `inputs_used` /
`inputs_total` on the result tells the caller how much data the score
actually rests on, so a score computed from 2 of 12 inputs can be treated
with appropriate suspicion by whoever consumes it.

All reference ranges below (the `low`/`high` bounds each raw stat is
scaled between) are documented, unvalidated starting points — exactly the
kind of thing the spec's backtesting phase should tune, not something
claimed to already be correct.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from betfair_trading.football.over_1_5_scalp.config import Over15ScalpConfig

MIN_SAMPLE_SIZE = 10  # spec: "adequate sample size" -- configurable


def _linear_subscore(value: float, low: float, high: float) -> float:
    """Maps `value` linearly onto [0, 100], clipped at both ends. Pass
    `low > high` for a "lower raw value is better" metric (e.g. a team's
    0-0 full-time rate) — the mapping direction inverts automatically.
    """
    if high == low:
        return 50.0
    fraction = (value - low) / (high - low)
    return max(0.0, min(100.0, fraction * 100.0))


@dataclass(frozen=True)
class AggregateScoreResult:
    score: float  # 0-100, weighted average of whichever component subscores were available
    component_scores: dict[str, float]
    inputs_used: int
    inputs_total: int


# --- Pre-match ----------------------------------------------------------


@dataclass(frozen=True)
class PrematchInputs:
    home_over_1_5_rate: float | None = None  # 0-1
    away_over_1_5_rate: float | None = None  # 0-1
    combined_avg_total_goals: float | None = None  # e.g. 2.8
    home_scoring_rate: float | None = None  # 0-1
    away_scoring_rate: float | None = None  # 0-1
    zero_zero_ft_rate: float | None = None  # 0-1, LOWER is better
    second_half_goal_share: float | None = None  # 0-1, share of season goals scored in the 2nd half
    recent_goal_trend: float | None = None  # roughly -1..+1, recent vs. season-average goal rate
    recent_5_form_score: float | None = None  # 0-1
    recent_10_form_score: float | None = None  # 0-1
    h2h_over_1_5_rate: float | None = None  # 0-1 -- deliberately low-weighted below, per spec
    sample_size_home: int | None = None
    sample_size_away: int | None = None
    competition_reliable: bool = True
    competition_liquidity_score: float | None = None  # 0-1


@dataclass(frozen=True)
class PrematchScoreWeights:
    home_over_1_5_rate: float = 15.0
    away_over_1_5_rate: float = 15.0
    combined_avg_total_goals: float = 15.0
    home_scoring_rate: float = 10.0
    away_scoring_rate: float = 10.0
    zero_zero_ft_rate: float = 10.0
    second_half_goal_share: float = 8.0
    recent_goal_trend: float = 7.0
    recent_5_form_score: float = 5.0
    recent_10_form_score: float = 5.0
    h2h_over_1_5_rate: float = 5.0  # spec: "avoid relying entirely on head-to-head" -> small weight, not zero
    competition_liquidity_score: float = 5.0


DEFAULT_PREMATCH_WEIGHTS = PrematchScoreWeights()


@dataclass(frozen=True)
class PrematchScoreResult(AggregateScoreResult):
    sample_size_adequate: bool = True
    competition_excluded: bool = False


def prematch_goal_score(
    inputs: PrematchInputs,
    weights: PrematchScoreWeights = DEFAULT_PREMATCH_WEIGHTS,
    min_sample_size: int = MIN_SAMPLE_SIZE,
) -> PrematchScoreResult:
    subscores: dict[str, float] = {}

    if inputs.home_over_1_5_rate is not None:
        subscores["home_over_1_5_rate"] = _linear_subscore(inputs.home_over_1_5_rate, 0.40, 0.85)
    if inputs.away_over_1_5_rate is not None:
        subscores["away_over_1_5_rate"] = _linear_subscore(inputs.away_over_1_5_rate, 0.40, 0.85)
    if inputs.combined_avg_total_goals is not None:
        subscores["combined_avg_total_goals"] = _linear_subscore(inputs.combined_avg_total_goals, 2.0, 3.5)
    if inputs.home_scoring_rate is not None:
        subscores["home_scoring_rate"] = _linear_subscore(inputs.home_scoring_rate, 0.40, 0.85)
    if inputs.away_scoring_rate is not None:
        subscores["away_scoring_rate"] = _linear_subscore(inputs.away_scoring_rate, 0.35, 0.75)
    if inputs.zero_zero_ft_rate is not None:
        subscores["zero_zero_ft_rate"] = _linear_subscore(inputs.zero_zero_ft_rate, 0.20, 0.02)
    if inputs.second_half_goal_share is not None:
        subscores["second_half_goal_share"] = _linear_subscore(inputs.second_half_goal_share, 0.45, 0.65)
    if inputs.recent_goal_trend is not None:
        subscores["recent_goal_trend"] = _linear_subscore(inputs.recent_goal_trend, -0.5, 0.5)
    if inputs.recent_5_form_score is not None:
        subscores["recent_5_form_score"] = _linear_subscore(inputs.recent_5_form_score, 0.3, 0.9)
    if inputs.recent_10_form_score is not None:
        subscores["recent_10_form_score"] = _linear_subscore(inputs.recent_10_form_score, 0.3, 0.9)
    if inputs.h2h_over_1_5_rate is not None:
        subscores["h2h_over_1_5_rate"] = _linear_subscore(inputs.h2h_over_1_5_rate, 0.4, 0.85)
    if inputs.competition_liquidity_score is not None:
        subscores["competition_liquidity_score"] = _linear_subscore(inputs.competition_liquidity_score, 0.2, 0.8)

    score = _weighted_average(subscores, weights)

    sample_size_adequate = (
        (inputs.sample_size_home is None or inputs.sample_size_home >= min_sample_size)
        and (inputs.sample_size_away is None or inputs.sample_size_away >= min_sample_size)
    )

    return PrematchScoreResult(
        score=score,
        component_scores=subscores,
        inputs_used=len(subscores),
        inputs_total=len(fields(PrematchScoreWeights)),
        sample_size_adequate=sample_size_adequate,
        competition_excluded=not inputs.competition_reliable,
    )


# --- Live (30-minute pressure + 50-minute reassessment) ---------------------


@dataclass(frozen=True)
class LiveInputs:
    minute: float
    total_shots: float | None = None
    shots_on_target: float | None = None
    xg: float | None = None
    dangerous_attacks: float | None = None
    attacks: float | None = None
    box_entries: float | None = None
    corners: float | None = None
    possession_attacking_third: float | None = None  # 0-1
    big_chances: float | None = None
    shot_frequency_last_10min: float | None = None  # shots in the last 10 minutes
    xthreat: float | None = None
    momentum_last_10min: float | None = None  # roughly -1..+1


@dataclass(frozen=True)
class LiveScoreWeights:
    total_shots: float = 15.0
    shots_on_target: float = 15.0
    xg: float = 20.0
    dangerous_attacks: float = 10.0
    attacks: float = 5.0
    box_entries: float = 5.0
    corners: float = 5.0
    possession_attacking_third: float = 5.0
    big_chances: float = 10.0
    shot_frequency_last_10min: float = 5.0
    xthreat: float = 3.0
    momentum_last_10min: float = 2.0


DEFAULT_LIVE_WEIGHTS = LiveScoreWeights()


def live_goal_pressure_score(inputs: LiveInputs, weights: LiveScoreWeights = DEFAULT_LIVE_WEIGHTS) -> AggregateScoreResult:
    subscores: dict[str, float] = {}

    if inputs.total_shots is not None:
        subscores["total_shots"] = _linear_subscore(inputs.total_shots, 3.0, 12.0)
    if inputs.shots_on_target is not None:
        subscores["shots_on_target"] = _linear_subscore(inputs.shots_on_target, 0.0, 4.0)
    if inputs.xg is not None:
        subscores["xg"] = _linear_subscore(inputs.xg, 0.3, 1.2)
    if inputs.dangerous_attacks is not None:
        subscores["dangerous_attacks"] = _linear_subscore(inputs.dangerous_attacks, 20.0, 60.0)
    if inputs.attacks is not None:
        subscores["attacks"] = _linear_subscore(inputs.attacks, 40.0, 100.0)
    if inputs.box_entries is not None:
        subscores["box_entries"] = _linear_subscore(inputs.box_entries, 5.0, 20.0)
    if inputs.corners is not None:
        subscores["corners"] = _linear_subscore(inputs.corners, 1.0, 6.0)
    if inputs.possession_attacking_third is not None:
        subscores["possession_attacking_third"] = _linear_subscore(inputs.possession_attacking_third, 0.15, 0.40)
    if inputs.big_chances is not None:
        subscores["big_chances"] = _linear_subscore(inputs.big_chances, 0.0, 3.0)
    if inputs.shot_frequency_last_10min is not None:
        subscores["shot_frequency_last_10min"] = _linear_subscore(inputs.shot_frequency_last_10min, 0.0, 4.0)
    if inputs.xthreat is not None:
        subscores["xthreat"] = _linear_subscore(inputs.xthreat, 0.0, 0.15)
    if inputs.momentum_last_10min is not None:
        subscores["momentum_last_10min"] = _linear_subscore(inputs.momentum_last_10min, -0.5, 0.5)

    return AggregateScoreResult(
        score=_weighted_average(subscores, weights),
        component_scores=subscores,
        inputs_used=len(subscores),
        inputs_total=len(fields(LiveScoreWeights)),
    )


def _weighted_average(subscores: dict[str, float], weights: object) -> float:
    if not subscores:
        return 0.0
    weight_map = {name: getattr(weights, name) for name in subscores}
    total_weight = sum(weight_map.values())
    if total_weight <= 0:
        return 0.0
    return round(sum(subscores[name] * weight_map[name] for name in subscores) / total_weight, 2)


# --- 50-minute EV / edge ------------------------------------------------


def second_entry_edge(model_probability_two_plus_goals: float, back_odds: float) -> float:
    """edge = model_probability - market_probability, per the spec exactly."""
    market_probability = 1.0 / back_odds
    return model_probability_two_plus_goals - market_probability


def second_entry_fraction(edge: float, live_pressure_score: float, config: Over15ScalpConfig) -> float:
    """The spec's worked example: strong setup -> full remaining
    allocation, medium -> half of it, weak (edge below the configured
    minimum) -> nothing. "Strong" requires both a comfortably-above-
    minimum edge AND a high live pressure score; edge alone isn't enough,
    since a model badly miscalibrated on a noisy few inputs could produce
    a large "edge" without real supporting evidence.
    """
    if edge < config.min_second_entry_edge:
        return 0.0
    strong_edge_threshold = config.min_second_entry_edge * 1.5
    if edge >= strong_edge_threshold and live_pressure_score >= config.min_live_pressure_score:
        return config.second_entry_max_fraction
    return config.second_entry_max_fraction * 0.5
