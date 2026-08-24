import pytest

from betfair_trading.core.modes import (
    LiveTradingNotConfirmed,
    TradingMode,
    assert_live_allowed,
    is_execution_enabled,
)


def test_default_mode_is_paper():
    assert TradingMode.from_env_value(None) is TradingMode.PAPER
    assert TradingMode.from_env_value("") is TradingMode.PAPER


def test_mode_parsing_is_case_insensitive():
    assert TradingMode.from_env_value("live") is TradingMode.LIVE
    assert TradingMode.from_env_value(" Shadow ") is TradingMode.SHADOW


def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        TradingMode.from_env_value("YOLO")


@pytest.mark.parametrize(
    "mode,confirmed",
    [
        (TradingMode.PAPER, "YES"),
        (TradingMode.SHADOW, "YES"),
        (TradingMode.LIVE, None),
        (TradingMode.LIVE, "yes"),  # must be exact-case YES
        (TradingMode.LIVE, "TRUE"),
    ],
)
def test_live_requires_both_gates(mode, confirmed):
    with pytest.raises(LiveTradingNotConfirmed):
        assert_live_allowed(mode, confirmed)


def test_live_allowed_when_both_gates_open():
    assert_live_allowed(TradingMode.LIVE, "YES")  # must not raise


def test_execution_enabled_only_for_paper_and_live():
    assert is_execution_enabled(TradingMode.PAPER)
    assert is_execution_enabled(TradingMode.LIVE)
    assert not is_execution_enabled(TradingMode.SHADOW)
