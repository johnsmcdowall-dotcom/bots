"""HORSE STRATEGY 2 (steamer) and HORSE STRATEGY 3 (drifter): momentum-
continuation entry filters wrapping strategies/engine.py's shared
target-before-stop signal factory.

Steamer: price has been sustainedly shortening, with traded-volume
confirmation and a tight spread (per the spec's requirement to distinguish
"real persistent money" from "temporary noise" — a raw price move with no
volume behind it is exactly the kind of noise the spec warns against
following). BACK now, expecting further shortening (BACK → LAY).

Drifter: the mirror image — sustained lengthening, volume-confirmed, tight
spread. LAY now, expecting further drift (LAY → BACK).

Neither strategy invents its own probability estimate — both delegate
entirely to the fitted TargetBeforeStopModel (Phase 4); this module is
only the entry filter deciding *which* rows are even worth asking the
model about; and strategies/engine.py's EV/cost math decides whether
what the model says is worth trading, per the spec's Strategy 1 rule
("Do not trade unless the discrepancy remains profitable after all
costs.").
"""

from __future__ import annotations

from typing import Sequence

from betfair_trading.core.interfaces import Side, Signal, Sport
from betfair_trading.features.pipeline import FeatureRow
from betfair_trading.models.baseline import TargetBeforeStopModel
from betfair_trading.models.labels import CANONICAL_TARGET_STOP_CONFIGS, TargetStopConfig
from betfair_trading.strategies.base import DEFAULT_COMMISSION, DEFAULT_GRADE_THRESHOLDS, CommissionModel, GradeThresholds
from betfair_trading.strategies.engine import evaluate_target_before_stop_opportunity

DEFAULT_STEAMER_CONFIGS: tuple[TargetStopConfig, ...] = tuple(
    c for c in CANONICAL_TARGET_STOP_CONFIGS if c.side is Side.BACK
)
DEFAULT_DRIFTER_CONFIGS: tuple[TargetStopConfig, ...] = tuple(
    c for c in CANONICAL_TARGET_STOP_CONFIGS if c.side is Side.LAY
)

DEFAULT_MOMENTUM_WINDOW_SECONDS = 10.0
DEFAULT_MIN_TICK_VELOCITY = 0.05  # ticks/sec, i.e. roughly 1 tick per 20s sustained — an unvalidated starting point
DEFAULT_MAX_SPREAD_TICKS = 1


def _is_momentum_candidate(
    feature_row: FeatureRow,
    window_seconds: float,
    direction: int,
    min_tick_velocity: float,
    max_spread_ticks: int,
) -> bool:
    """`direction` is -1 for shortening (steamer) or +1 for lengthening
    (drifter). Requires: tick velocity in the right direction and past the
    threshold, traded-volume confirmation (per spec — a price move with no
    volume behind it is noise, not a signal), and a tight spread (the spec
    lists spread among a steamer's required supporting conditions).
    """
    rolling = feature_row.rolling.get(window_seconds)
    if rolling is None or rolling.tick_velocity is None:
        return False
    if rolling.volume_velocity is None or rolling.volume_velocity <= 0:
        return False
    if feature_row.microstructure.spread_ticks is None or feature_row.microstructure.spread_ticks > max_spread_ticks:
        return False
    if direction < 0:
        return rolling.tick_velocity <= -min_tick_velocity
    return rolling.tick_velocity >= min_tick_velocity


class _MomentumStrategy:
    """Shared implementation; SteamerStrategy/DrifterStrategy below just
    fix `_direction` and default configs.
    """

    sport = Sport.HORSE_RACING
    _direction: int

    def __init__(
        self,
        model: TargetBeforeStopModel,
        model_confidence: float,
        configs: Sequence[TargetStopConfig],
        window_seconds: float = DEFAULT_MOMENTUM_WINDOW_SECONDS,
        min_tick_velocity: float = DEFAULT_MIN_TICK_VELOCITY,
        max_spread_ticks: int = DEFAULT_MAX_SPREAD_TICKS,
        commission: CommissionModel = DEFAULT_COMMISSION,
        thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
    ):
        self._model = model
        self._model_confidence = model_confidence
        self._configs = tuple(configs)
        self._window_seconds = window_seconds
        self._min_tick_velocity = min_tick_velocity
        self._max_spread_ticks = max_spread_ticks
        self._commission = commission
        self._thresholds = thresholds

    def generate_signals(self, feature_rows: Sequence[FeatureRow]) -> list[Signal]:
        signals: list[Signal] = []
        for row in feature_rows:
            if not _is_momentum_candidate(
                row, self._window_seconds, self._direction, self._min_tick_velocity, self._max_spread_ticks
            ):
                continue
            for config in self._configs:
                signals.append(
                    evaluate_target_before_stop_opportunity(
                        self.name, row, config, self._model, self._model_confidence, self._commission, self._thresholds
                    )
                )
        return signals


class SteamerStrategy(_MomentumStrategy):
    name = "steamer"
    _direction = -1

    def __init__(self, model: TargetBeforeStopModel, model_confidence: float, **kwargs):
        kwargs.setdefault("configs", DEFAULT_STEAMER_CONFIGS)
        super().__init__(model, model_confidence, **kwargs)


class DrifterStrategy(_MomentumStrategy):
    name = "drifter"
    _direction = 1

    def __init__(self, model: TargetBeforeStopModel, model_confidence: float, **kwargs):
        kwargs.setdefault("configs", DEFAULT_DRIFTER_CONFIGS)
        super().__init__(model, model_confidence, **kwargs)
