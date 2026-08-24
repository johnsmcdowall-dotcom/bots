from datetime import datetime, timedelta, timezone

from betfair_trading.features.rolling import PricePoint, compute_rolling_features


def _t(seconds: float) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_insufficient_points_returns_none_fields():
    points = [PricePoint(_t(0), 3.5, 100.0)]
    features = compute_rolling_features(points, _t(0), window_seconds=10.0)

    assert features.observation_count == 1
    assert features.volume_change is None
    assert features.volume_velocity is None
    assert features.price_velocity is None
    assert features.tick_velocity is None
    assert features.recent_high == 3.5
    assert features.recent_low == 3.5
    assert features.distance_from_high_ticks == 0
    assert features.distance_from_low_ticks == 0


def test_window_only_includes_points_within_bound():
    points = [
        PricePoint(_t(-20), 4.0, 0.0),   # outside a 10s window
        PricePoint(_t(-5), 3.6, 100.0),
        PricePoint(_t(0), 3.5, 150.0),
    ]
    features = compute_rolling_features(points, as_of=_t(0), window_seconds=10.0)

    assert features.observation_count == 2  # the -20s point excluded
    assert features.volume_change == 50.0


def test_never_includes_points_after_as_of():
    points = [
        PricePoint(_t(0), 3.5, 100.0),
        PricePoint(_t(5), 3.4, 150.0),
        PricePoint(_t(10), 3.3, 200.0),  # "future" relative to as_of below
    ]
    features = compute_rolling_features(points, as_of=_t(5), window_seconds=60.0)

    assert features.observation_count == 2
    assert features.recent_low == 3.4  # not 3.3, which is after as_of


def test_price_and_volume_velocity():
    points = [PricePoint(_t(0), 3.5, 100.0), PricePoint(_t(10), 3.3, 300.0)]
    features = compute_rolling_features(points, as_of=_t(10), window_seconds=10.0)

    assert features.volume_velocity == 20.0  # (300-100)/10
    assert round(features.price_velocity, 4) == round((3.3 - 3.5) / 10, 4)


def test_tick_velocity_uses_ticks_between():
    points = [PricePoint(_t(0), 2.0, 100.0), PricePoint(_t(5), 1.98, 100.0)]
    features = compute_rolling_features(points, as_of=_t(5), window_seconds=10.0)
    # 2.0 -> 1.99 -> 1.98 is -2 ticks (the 2.0-3.0 band steps by 0.02, the
    # 1.01-2.0 band by 0.01 — 1.99 is the tick strictly between them) over 5 seconds.
    assert features.tick_velocity == -2 / 5


def test_acceleration_needs_at_least_three_points():
    two_points = [PricePoint(_t(0), 3.5, 100.0), PricePoint(_t(5), 3.4, 150.0)]
    features = compute_rolling_features(two_points, as_of=_t(5), window_seconds=10.0)
    assert features.price_acceleration is None
    assert features.volume_acceleration is None


def test_acceleration_detects_speeding_up_movement():
    # Price barely moves in the first half, moves a lot in the second half
    # -> positive acceleration in the direction of the move.
    points = [
        PricePoint(_t(0), 4.0, 0.0),
        PricePoint(_t(5), 3.99, 0.0),
        PricePoint(_t(10), 3.5, 0.0),
    ]
    features = compute_rolling_features(points, as_of=_t(10), window_seconds=10.0)
    assert features.price_acceleration is not None
    assert features.price_acceleration < 0  # accelerating shorter (price falling faster)


def test_vwap_weights_by_volume_delta():
    points = [
        PricePoint(_t(0), 3.5, 0.0),
        PricePoint(_t(1), 3.6, 100.0),   # 100 volume arrives at price 3.6
        PricePoint(_t(2), 3.4, 300.0),   # 200 volume arrives at price 3.4
    ]
    features = compute_rolling_features(points, as_of=_t(2), window_seconds=10.0)
    expected = (3.6 * 100.0 + 3.4 * 200.0) / 300.0
    assert round(features.vwap, 6) == round(expected, 6)


def test_vwap_is_none_when_no_volume_arrived_in_window():
    points = [PricePoint(_t(0), 3.5, 100.0), PricePoint(_t(5), 3.4, 100.0)]
    features = compute_rolling_features(points, as_of=_t(5), window_seconds=10.0)
    assert features.vwap is None


def test_recent_high_low_and_distance_in_ticks():
    points = [
        PricePoint(_t(0), 3.5, 0.0),
        PricePoint(_t(5), 3.3, 0.0),  # low
        PricePoint(_t(10), 3.7, 0.0),  # high
        PricePoint(_t(15), 3.5, 0.0),  # current
    ]
    features = compute_rolling_features(points, as_of=_t(15), window_seconds=60.0)

    assert features.recent_high == 3.7
    assert features.recent_low == 3.3
    # current 3.5 vs high 3.7: ticks_between(3.5, 3.7) is positive (high is "longer")
    from betfair_trading.betfair.ticks import ticks_between
    assert features.distance_from_high_ticks == ticks_between(3.5, 3.7)
    assert features.distance_from_low_ticks == ticks_between(3.5, 3.3)
