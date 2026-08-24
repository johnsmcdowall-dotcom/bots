from datetime import datetime, timedelta, timezone

import pytest

from betfair_trading.features.time_to_off import TimeToOffRegime, classify

OFF = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


def _at(seconds_before_off: float) -> datetime:
    return OFF - timedelta(seconds=seconds_before_off)


@pytest.mark.parametrize(
    "seconds_before_off,expected",
    [
        (3601, TimeToOffRegime.MORE_THAN_60_MIN),
        (3600, TimeToOffRegime.MIN_60_TO_30),
        (1801, TimeToOffRegime.MIN_60_TO_30),
        (1800, TimeToOffRegime.MIN_30_TO_15),
        (901, TimeToOffRegime.MIN_30_TO_15),
        (900, TimeToOffRegime.MIN_15_TO_10),
        (601, TimeToOffRegime.MIN_15_TO_10),
        (600, TimeToOffRegime.MIN_10_TO_5),
        (301, TimeToOffRegime.MIN_10_TO_5),
        (300, TimeToOffRegime.MIN_5_TO_3),
        (181, TimeToOffRegime.MIN_5_TO_3),
        (180, TimeToOffRegime.MIN_3_TO_2),
        (121, TimeToOffRegime.MIN_3_TO_2),
        (120, TimeToOffRegime.MIN_2_TO_1),
        (61, TimeToOffRegime.MIN_2_TO_1),
        (60, TimeToOffRegime.SEC_60_TO_30),
        (31, TimeToOffRegime.SEC_60_TO_30),
        (30, TimeToOffRegime.SEC_30_TO_10),
        (11, TimeToOffRegime.SEC_30_TO_10),
        (10, TimeToOffRegime.FINAL_10_SEC),
        (1, TimeToOffRegime.FINAL_10_SEC),
        (0, TimeToOffRegime.FINAL_10_SEC),
    ],
)
def test_regime_boundaries(seconds_before_off, expected):
    assert classify(OFF, _at(seconds_before_off)) == expected


def test_post_off_is_negative_time_to_off():
    assert classify(OFF, OFF + timedelta(seconds=1)) == TimeToOffRegime.POST_OFF
    assert classify(OFF, OFF + timedelta(minutes=90)) == TimeToOffRegime.POST_OFF


def test_at_off_time_exactly_is_final_10_sec_not_post_off():
    assert classify(OFF, OFF) == TimeToOffRegime.FINAL_10_SEC
