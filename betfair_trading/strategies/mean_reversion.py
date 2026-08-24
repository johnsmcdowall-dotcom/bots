"""HORSE MODEL 5 — mean reversion: fades a rapid price move that lacks
traded-volume confirmation (the spec's own signature of an overshoot
rather than informed money — see strategies/momentum.py's docstring for
the opposite case, where volume confirmation is required rather than
absent).

A shortening move with no volume behind it is faded by LAYing now (betting
on a bounce back up); a lengthening move with no volume is faded by
BACKing now (betting on a pullback down) — the mirror image of
steamer/drifter's directional mapping.
"""

from __future__ import annotations

from typing import Sequence

from betfair_trading.core.interfaces import Side, Signal, Sport
from betfair_trading.features.pipeline import FeatureRow
from betfair_trading.models.baseline import TargetBeforeStopModel
from betfair_trading.models.labels import TargetStopConfig
from betfair_trading.strategies.base import DEFAULT_COMMISSION, DEFAULT_GRADE_THRESHOLDS, CommissionModel, GradeThresholds
from betfair_trading.strategies.engine import evaluate_target_before_stop_opportunity

DEFAULT_REVERSION_WINDOW_SECONDS = 10.0
DEFAULT_MIN_TICK_VELOCITY_MAGNITUDE = 0.1  # ticks/sec -- a faster move than momentum's own threshold, deliberately: reversion is about a SHARP overshoot, not gentle drift
DEFAULT_MAX_VOLUME_VELOCITY = 0.0  # require essentially no new money behind the move
DEFAULT_TIMEOUT_SECONDS = 20.0  # a bounce, if it happens, should happen quickly
DEFAULT_TARGET_STOP_PAIRS: tuple[tuple[int, int], ...] = ((1, 1), (2, 1), (2, 2))


def detect_unconfirmed_move_direction(
    feature_row: FeatureRow,
    window_seconds: float,
    min_tick_velocity_magnitude: float,
    max_volume_velocity: float,
) -> int | None:
    """Returns -1 (shortened) or +1 (lengthened) if this row shows a rapid,
    volume-UNconfirmed move — a reversion candidate — else None. A move
    that DOES have volume behind it belongs to momentum's territory, not
    reversion's, so it's explicitly excluded here rather than double-
    counted by both strategy families.
    """
    rolling = feature_row.rolling.get(window_seconds)
    if rolling is None or rolling.tick_velocity is None:
        return None
    if rolling.tick_velocity <= -min_tick_velocity_magnitude:
        direction = -1
    elif rolling.tick_velocity >= min_tick_velocity_magnitude:
        direction = 1
    else:
        return None
    if rolling.volume_velocity is not None and rolling.volume_velocity > max_volume_velocity:
        return None
    return direction


class MeanReversionStrategy:
    name = "mean_reversion"
    sport = Sport.HORSE_RACING

    def __init__(
        self,
        model: TargetBeforeStopModel,
        model_confidence: float,
        target_stop_pairs: Sequence[tuple[int, int]] = DEFAULT_TARGET_STOP_PAIRS,
        window_seconds: float = DEFAULT_REVERSION_WINDOW_SECONDS,
        min_tick_velocity_magnitude: float = DEFAULT_MIN_TICK_VELOCITY_MAGNITUDE,
        max_volume_velocity: float = DEFAULT_MAX_VOLUME_VELOCITY,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        commission: CommissionModel = DEFAULT_COMMISSION,
        thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
    ):
        self._model = model
        self._model_confidence = model_confidence
        self._target_stop_pairs = tuple(target_stop_pairs)
        self._window_seconds = window_seconds
        self._min_tick_velocity_magnitude = min_tick_velocity_magnitude
        self._max_volume_velocity = max_volume_velocity
        self._timeout_seconds = timeout_seconds
        self._commission = commission
        self._thresholds = thresholds

    def generate_signals(self, feature_rows: Sequence[FeatureRow]) -> list[Signal]:
        signals: list[Signal] = []
        for row in feature_rows:
            direction = detect_unconfirmed_move_direction(
                row, self._window_seconds, self._min_tick_velocity_magnitude, self._max_volume_velocity
            )
            if direction is None:
                continue
            side = Side.LAY if direction == -1 else Side.BACK  # fade the move
            for target_ticks, stop_ticks in self._target_stop_pairs:
                config = TargetStopConfig(side, target_ticks, stop_ticks, self._timeout_seconds)
                signals.append(
                    evaluate_target_before_stop_opportunity(
                        self.name, row, config, self._model, self._model_confidence, self._commission, self._thresholds
                    )
                )
        return signals
