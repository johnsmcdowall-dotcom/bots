from datetime import datetime, timedelta, timezone

from betfair_trading.core.interfaces import Side
from betfair_trading.features.rolling import PricePoint
from betfair_trading.models.labels import (
    CANONICAL_TARGET_STOP_CONFIGS,
    TargetBeforeStopOutcome,
    TICK_BUCKET_LABELS,
    closing_price_label,
    short_horizon_label,
    target_before_stop_label,
    tick_movement_bucket,
)


def _t(seconds: float) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


# --- tick_movement_bucket -------------------------------------------------

def test_tick_movement_bucket_clamps_to_seven_classes():
    assert tick_movement_bucket(-10) == 0  # "<=-3"
    assert tick_movement_bucket(-3) == 0
    assert tick_movement_bucket(-2) == 1
    assert tick_movement_bucket(0) == 3
    assert tick_movement_bucket(2) == 5
    assert tick_movement_bucket(3) == 6
    assert tick_movement_bucket(10) == 6  # ">=+3"
    assert len(TICK_BUCKET_LABELS) == 7


# --- short_horizon_label ---------------------------------------------------

def test_short_horizon_label_basic():
    points = [PricePoint(_t(0), 2.0, 0.0), PricePoint(_t(10), 1.98, 0.0)]
    label = short_horizon_label(points, as_of=_t(0), horizon_seconds=10.0)

    assert label.entry_price == 2.0
    assert label.future_price == 1.98
    assert label.tick_delta == -2  # 2.0 -> 1.99 -> 1.98
    assert label.bucket == tick_movement_bucket(-2)


def test_short_horizon_label_none_when_no_entry_price():
    points = [PricePoint(_t(5), 2.0, 0.0)]
    label = short_horizon_label(points, as_of=_t(0), horizon_seconds=10.0)
    assert label.entry_price is None
    assert label.bucket is None


def test_short_horizon_label_none_when_no_future_observation_within_tolerance():
    points = [PricePoint(_t(0), 2.0, 0.0), PricePoint(_t(20), 1.9, 0.0)]
    label = short_horizon_label(points, as_of=_t(0), horizon_seconds=10.0, lookup_tolerance_seconds=2.0)
    assert label.entry_price == 2.0
    assert label.future_price is None
    assert label.bucket is None


def test_short_horizon_label_uses_nearest_within_tolerance():
    points = [PricePoint(_t(0), 2.0, 0.0), PricePoint(_t(11), 1.9, 0.0)]
    label = short_horizon_label(points, as_of=_t(0), horizon_seconds=10.0, lookup_tolerance_seconds=2.0)
    assert label.future_price == 1.9  # 11s point is within 2s tolerance of the 10s horizon


# --- target_before_stop_label ----------------------------------------------

def test_back_hits_target_before_stop():
    points = [
        PricePoint(_t(0), 4.0, 0.0),
        PricePoint(_t(5), 3.9, 0.0),
        PricePoint(_t(10), 3.5, 0.0),  # target: 2 ticks shorter than 4.0 is 3.9; already hit at t5
    ]
    label = target_before_stop_label(points, as_of=_t(0), side=Side.BACK, target_ticks=2, stop_ticks=2, timeout_seconds=30.0)
    assert label.outcome == TargetBeforeStopOutcome.TARGET
    assert label.time_to_outcome_seconds == 5.0


def test_back_hits_stop_before_target():
    points = [
        PricePoint(_t(0), 4.0, 0.0),
        PricePoint(_t(5), 4.2, 0.0),  # drifted 2 ticks -> stop for BACK
    ]
    label = target_before_stop_label(points, as_of=_t(0), side=Side.BACK, target_ticks=2, stop_ticks=2, timeout_seconds=30.0)
    assert label.outcome == TargetBeforeStopOutcome.STOP
    assert label.time_to_outcome_seconds == 5.0


def test_back_times_out_when_neither_hit():
    points = [PricePoint(_t(0), 4.0, 0.0), PricePoint(_t(5), 4.0, 0.0), PricePoint(_t(10), 4.0, 0.0)]
    label = target_before_stop_label(points, as_of=_t(0), side=Side.BACK, target_ticks=2, stop_ticks=2, timeout_seconds=10.0)
    assert label.outcome == TargetBeforeStopOutcome.TIMEOUT
    assert label.outcome_price is None
    assert label.time_to_outcome_seconds is None


def test_lay_is_mirror_image_of_back():
    # LAY profits when price DRIFTS (goes up)
    points = [PricePoint(_t(0), 4.0, 0.0), PricePoint(_t(5), 4.2, 0.0)]
    label = target_before_stop_label(points, as_of=_t(0), side=Side.LAY, target_ticks=2, stop_ticks=2, timeout_seconds=30.0)
    assert label.outcome == TargetBeforeStopOutcome.TARGET

    points_stop = [PricePoint(_t(0), 4.0, 0.0), PricePoint(_t(5), 3.8, 0.0)]
    label_stop = target_before_stop_label(points_stop, as_of=_t(0), side=Side.LAY, target_ticks=2, stop_ticks=2, timeout_seconds=30.0)
    assert label_stop.outcome == TargetBeforeStopOutcome.STOP


def test_none_when_no_entry_price():
    points = [PricePoint(_t(5), 4.0, 0.0)]
    label = target_before_stop_label(points, as_of=_t(0), side=Side.BACK, target_ticks=2, stop_ticks=2, timeout_seconds=30.0)
    assert label is None


def test_does_not_look_beyond_timeout():
    points = [PricePoint(_t(0), 4.0, 0.0), PricePoint(_t(40), 3.5, 0.0)]  # would hit target, but after timeout
    label = target_before_stop_label(points, as_of=_t(0), side=Side.BACK, target_ticks=2, stop_ticks=2, timeout_seconds=30.0)
    assert label.outcome == TargetBeforeStopOutcome.TIMEOUT


def test_canonical_configs_cover_spec_combinations_both_sides():
    pairs = {(c.target_ticks, c.stop_ticks) for c in CANONICAL_TARGET_STOP_CONFIGS}
    assert pairs == {(1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (5, 3)}
    sides = {c.side for c in CANONICAL_TARGET_STOP_CONFIGS}
    assert sides == {Side.BACK, Side.LAY}
    assert len(CANONICAL_TARGET_STOP_CONFIGS) == 12


# --- closing_price_label -----------------------------------------------------

def test_closing_price_label_uses_last_point_as_proxy():
    points = [PricePoint(_t(0), 4.0, 0.0), PricePoint(_t(5), 3.9, 0.0), PricePoint(_t(30), 3.5, 0.0)]
    label = closing_price_label(points, as_of=_t(0))
    assert label.entry_price == 4.0
    assert label.closing_price == 3.5
    assert label.tick_delta < 0


def test_closing_price_label_empty_points():
    assert closing_price_label([], as_of=_t(0)) == closing_price_label([], as_of=_t(0))
    label = closing_price_label([], as_of=_t(0))
    assert label.entry_price is None
    assert label.closing_price is None
