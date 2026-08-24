"""HORSE STRATEGY 11 — scalping: tight (1-3 tick) target/stop configs,
gated on stricter liquidity/spread requirements than the momentum/
reversion strategies. Per the spec: "Only trade where liquidity is
sufficient, spread is narrow... expected tick movement exceeds execution
cost." Tracked as its own strategy rather than folded into momentum, as
the spec requires.

Unlike momentum (needs a directional velocity trigger) or mean reversion
(needs an unconfirmed move), scalping has no directional entry filter of
its own: it evaluates both BACK and LAY tight configs whenever the
liquidity gate passes, and leaves the fitted model + strategies/engine.py's
EV math to decide whether either side clears costs. A scalp that exists
only because liquidity happened to be good, with no real edge behind it,
should — and will — get REJECTed by the engine, not manufactured here.
"""

from __future__ import annotations

from typing import Sequence

from betfair_trading.core.interfaces import Side, Signal, Sport
from betfair_trading.features.pipeline import FeatureRow
from betfair_trading.models.baseline import TargetBeforeStopModel
from betfair_trading.models.labels import TargetStopConfig
from betfair_trading.strategies.base import DEFAULT_COMMISSION, DEFAULT_GRADE_THRESHOLDS, CommissionModel, GradeThresholds
from betfair_trading.strategies.engine import evaluate_target_before_stop_opportunity

DEFAULT_SCALP_TARGET_STOP_PAIRS: tuple[tuple[int, int], ...] = ((1, 1), (2, 1), (2, 2), (3, 2))
DEFAULT_SCALP_TIMEOUT_SECONDS = 60.0  # spec: "seconds to 1-2 minutes"
DEFAULT_MAX_SPREAD_TICKS = 1
DEFAULT_MIN_DEPTH = 100.0

# A scalp needs BOTH its entry and exit to realistically fill, and
# strategies/base.py's placeholder fill model doesn't yet distinguish a
# one-sided fill from a round trip (that's Phase 6's job) -- this
# compensates with a stricter minimum fill probability than the platform
# default until the real queue/fill simulator exists.
DEFAULT_SCALPING_THRESHOLDS = GradeThresholds(
    a_plus_min_net_ev=DEFAULT_GRADE_THRESHOLDS.a_plus_min_net_ev,
    a_min_net_ev=DEFAULT_GRADE_THRESHOLDS.a_min_net_ev,
    b_min_net_ev=DEFAULT_GRADE_THRESHOLDS.b_min_net_ev,
    a_plus_min_confidence=DEFAULT_GRADE_THRESHOLDS.a_plus_min_confidence,
    a_min_confidence=DEFAULT_GRADE_THRESHOLDS.a_min_confidence,
    min_fill_probability=0.7,
)


def passes_liquidity_gate(feature_row: FeatureRow, max_spread_ticks: int, min_depth: float) -> bool:
    micro = feature_row.microstructure
    if micro.spread_ticks is None or micro.spread_ticks > max_spread_ticks:
        return False
    if micro.back_depth < min_depth or micro.lay_depth < min_depth:
        return False
    return True


class ScalpingStrategy:
    name = "scalping"
    sport = Sport.HORSE_RACING

    def __init__(
        self,
        model: TargetBeforeStopModel,
        model_confidence: float,
        target_stop_pairs: Sequence[tuple[int, int]] = DEFAULT_SCALP_TARGET_STOP_PAIRS,
        timeout_seconds: float = DEFAULT_SCALP_TIMEOUT_SECONDS,
        max_spread_ticks: int = DEFAULT_MAX_SPREAD_TICKS,
        min_depth: float = DEFAULT_MIN_DEPTH,
        commission: CommissionModel = DEFAULT_COMMISSION,
        thresholds: GradeThresholds = DEFAULT_SCALPING_THRESHOLDS,
    ):
        self._model = model
        self._model_confidence = model_confidence
        self._target_stop_pairs = tuple(target_stop_pairs)
        self._timeout_seconds = timeout_seconds
        self._max_spread_ticks = max_spread_ticks
        self._min_depth = min_depth
        self._commission = commission
        self._thresholds = thresholds

    def generate_signals(self, feature_rows: Sequence[FeatureRow]) -> list[Signal]:
        signals: list[Signal] = []
        for row in feature_rows:
            if not passes_liquidity_gate(row, self._max_spread_ticks, self._min_depth):
                continue
            for side in (Side.BACK, Side.LAY):
                for target_ticks, stop_ticks in self._target_stop_pairs:
                    config = TargetStopConfig(side, target_ticks, stop_ticks, self._timeout_seconds)
                    signals.append(
                        evaluate_target_before_stop_opportunity(
                            self.name, row, config, self._model, self._model_confidence,
                            self._commission, self._thresholds,
                        )
                    )
        return signals
