"""Time-to-off regime tagging.

The spec is explicit that pre-off market behaviour is not stationary
across the countdown to a race and must be treated as separate regimes
rather than pooled — this module is the single place that boundary logic
lives, so every later phase (features, models, strategies, backtesting)
buckets time-to-off identically.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum


class TimeToOffRegime(str, Enum):
    MORE_THAN_60_MIN = "MORE_THAN_60_MIN"
    MIN_60_TO_30 = "60-30_MIN"
    MIN_30_TO_15 = "30-15_MIN"
    MIN_15_TO_10 = "15-10_MIN"
    MIN_10_TO_5 = "10-5_MIN"
    MIN_5_TO_3 = "5-3_MIN"
    MIN_3_TO_2 = "3-2_MIN"
    MIN_2_TO_1 = "2-1_MIN"
    SEC_60_TO_30 = "60-30_SEC"
    SEC_30_TO_10 = "30-10_SEC"
    FINAL_10_SEC = "FINAL_10_SEC"
    POST_OFF = "POST_OFF"


# (upper_bound_seconds_to_off_inclusive, regime) — checked in order, so the
# first band whose upper bound the actual time-to-off does not exceed wins.
# time_to_off == upper bound sits in the *shorter* countdown regime (e.g.
# exactly 1800s to off is "30-15 min", not "60-30 min") — an explicit
# choice, not an accident, so behaviour at exact boundaries is consistent
# for every race rather than depending on float timestamp jitter.
_BANDS: tuple[tuple[float, TimeToOffRegime], ...] = (
    (10.0, TimeToOffRegime.FINAL_10_SEC),
    (30.0, TimeToOffRegime.SEC_30_TO_10),
    (60.0, TimeToOffRegime.SEC_60_TO_30),
    (120.0, TimeToOffRegime.MIN_2_TO_1),
    (180.0, TimeToOffRegime.MIN_3_TO_2),
    (300.0, TimeToOffRegime.MIN_5_TO_3),
    (600.0, TimeToOffRegime.MIN_10_TO_5),
    (900.0, TimeToOffRegime.MIN_15_TO_10),
    (1800.0, TimeToOffRegime.MIN_30_TO_15),
    (3600.0, TimeToOffRegime.MIN_60_TO_30),
)


def classify(scheduled_start: datetime, timestamp: datetime) -> TimeToOffRegime:
    time_to_off_seconds = (scheduled_start - timestamp).total_seconds()

    if time_to_off_seconds < 0:
        return TimeToOffRegime.POST_OFF

    for upper_bound, regime in _BANDS:
        if time_to_off_seconds <= upper_bound:
            return regime

    return TimeToOffRegime.MORE_THAN_60_MIN
