"""HORSE STRATEGY 8 — BSP/closing-price forecast trading: uses the fitted
BSPForecastModel (Phase 4) to predict a signed tick move to the closing-
price proxy, and — if the predicted move is large enough to bother with —
prices a BACK-now/LAY-later (predicted shortening) or LAY-now/BACK-later
(predicted lengthening) trade via strategies/engine.py's shared core.

This is NOT the same shape as the target-before-stop strategies: there is
no P(target before stop) here, because BSPForecastModel is a regression
(a point forecast), not a classifier. Converting a point forecast into an
EV needs *some* probability of it being right — rather than inventing one,
`model_confidence` is caller-supplied (e.g. from the model's validation-
set directional accuracy: how often the predicted sign actually matched
the realised sign), exactly like every other strategy in this package.
The "stop" is a configured maximum adverse move (the forecast doesn't
predict a stop distance, only a point target), used the same way a
target-before-stop config's stop_ticks is.
"""

from __future__ import annotations

from typing import Sequence

from betfair_trading.betfair.ticks import shift_ticks
from betfair_trading.core.interfaces import Side, Signal, Sport
from betfair_trading.features.pipeline import FeatureRow
from betfair_trading.models.baseline import BSPForecastModel
from betfair_trading.models.dataset import to_model_matrix
from betfair_trading.strategies.base import DEFAULT_COMMISSION, DEFAULT_GRADE_THRESHOLDS, CommissionModel, GradeThresholds
from betfair_trading.strategies.engine import entry_price_for_side, evaluate_priced_opportunity, reject_signal

DEFAULT_STOP_TICKS = 2
DEFAULT_MIN_PREDICTED_TICK_MOVE = 2.0  # don't bother trading a forecast smaller than this
DEFAULT_TIMEOUT_SECONDS = 300.0  # a BSP-drift trade is held toward the off, not scalped in seconds


def evaluate_bsp_forecast_opportunity(
    strategy_name: str,
    feature_row: FeatureRow,
    model: BSPForecastModel,
    model_confidence: float,
    stop_ticks: int = DEFAULT_STOP_TICKS,
    min_predicted_tick_move: float = DEFAULT_MIN_PREDICTED_TICK_MOVE,
    holding_time_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    commission: CommissionModel = DEFAULT_COMMISSION,
    thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
) -> Signal:
    _, X, kept = to_model_matrix([feature_row])
    if not kept or not kept[0]:
        return reject_signal(
            strategy_name, feature_row, Side.BACK, "feature row has missing values the model requires"
        )

    predicted_tick_delta = model.predict(X)[0]
    if abs(predicted_tick_delta) < min_predicted_tick_move:
        return reject_signal(
            strategy_name, feature_row, Side.BACK,
            f"predicted move ({predicted_tick_delta:+.1f} ticks) too small to trade "
            f"(minimum {min_predicted_tick_move})",
        )

    # Negative predicted delta = model expects the price to shorten -> BACK
    # now, LAY later. Positive = expects lengthening -> LAY now, BACK later.
    side = Side.BACK if predicted_tick_delta < 0 else Side.LAY
    entry_price = entry_price_for_side(feature_row, side)
    if entry_price is None:
        return reject_signal(strategy_name, feature_row, side, f"no {side.value} price currently available")

    predicted_ticks = round(predicted_tick_delta)
    target_price = shift_ticks(entry_price, predicted_ticks)
    stop_price = shift_ticks(entry_price, stop_ticks if side is Side.BACK else -stop_ticks)

    reason = (
        f"{strategy_name}: predicted closing move {predicted_tick_delta:+.1f} ticks "
        f"({side.value} @ {entry_price} targeting {target_price})"
    )

    return evaluate_priced_opportunity(
        strategy_name, feature_row, side, entry_price, target_price, stop_price,
        model_confidence, model_confidence, holding_time_seconds, reason,
        commission, thresholds,
        extra_context={"predicted_tick_delta": predicted_tick_delta, "stop_ticks": stop_ticks},
    )


class BspDriftStrategy:
    """Evaluates every row it's given — there's no separate entry filter
    (unlike momentum/reversion/scalping): the forecast-magnitude gate
    (`min_predicted_tick_move`) inside `evaluate_bsp_forecast_opportunity`
    already decides whether a row is worth trading.
    """

    name = "bsp_drift"
    sport = Sport.HORSE_RACING

    def __init__(
        self,
        model: BSPForecastModel,
        model_confidence: float,
        stop_ticks: int = DEFAULT_STOP_TICKS,
        min_predicted_tick_move: float = DEFAULT_MIN_PREDICTED_TICK_MOVE,
        holding_time_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        commission: CommissionModel = DEFAULT_COMMISSION,
        thresholds: GradeThresholds = DEFAULT_GRADE_THRESHOLDS,
    ):
        self._model = model
        self._model_confidence = model_confidence
        self._stop_ticks = stop_ticks
        self._min_predicted_tick_move = min_predicted_tick_move
        self._holding_time_seconds = holding_time_seconds
        self._commission = commission
        self._thresholds = thresholds

    def generate_signals(self, feature_rows: Sequence[FeatureRow]) -> list[Signal]:
        return [
            evaluate_bsp_forecast_opportunity(
                self.name, row, self._model, self._model_confidence, self._stop_ticks,
                self._min_predicted_tick_move, self._holding_time_seconds, self._commission, self._thresholds,
            )
            for row in feature_rows
        ]
