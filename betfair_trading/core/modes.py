"""The PAPER / SHADOW / LIVE mode gate.

This is the single choke point every order-placement code path must call
before submitting a real order to Betfair. Nothing else in the codebase is
allowed to duplicate this check — execution/ imports and calls
`assert_live_allowed` rather than re-deriving the condition, so there is
exactly one place that can get this wrong.
"""

from __future__ import annotations

from enum import Enum


class TradingMode(str, Enum):
    """PAPER is the only mode that should ever be the default."""

    PAPER = "PAPER"
    SHADOW = "SHADOW"
    LIVE = "LIVE"

    @classmethod
    def from_env_value(cls, raw: str | None) -> "TradingMode":
        if raw is None or raw == "":
            return cls.PAPER
        try:
            return cls(raw.strip().upper())
        except ValueError as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Invalid TRADING_MODE={raw!r}; must be one of: {valid}"
            ) from exc


LIVE_CONFIRMATION_VALUE = "YES"


class LiveTradingNotConfirmed(RuntimeError):
    """Raised whenever code tries to place a real order without both gates open."""


def assert_live_allowed(mode: TradingMode, live_trading_confirmed_raw: str | None) -> None:
    """Raise unless BOTH TRADING_MODE=LIVE and LIVE_TRADING_CONFIRMED=YES.

    Call this immediately before submitting any real order. It intentionally
    takes primitives rather than a `Settings` object so it has no import-time
    dependency on `config/` and can't be bypassed by constructing a partial
    settings object.
    """
    if mode is not TradingMode.LIVE:
        raise LiveTradingNotConfirmed(
            f"Refusing to place a live order: TRADING_MODE is {mode.value}, not LIVE."
        )
    if live_trading_confirmed_raw != LIVE_CONFIRMATION_VALUE:
        raise LiveTradingNotConfirmed(
            "Refusing to place a live order: LIVE_TRADING_CONFIRMED must be "
            f"exactly {LIVE_CONFIRMATION_VALUE!r} (got {live_trading_confirmed_raw!r})."
        )


def is_execution_enabled(mode: TradingMode) -> bool:
    """Whether the execution layer should even simulate/submit orders at all.

    PAPER and LIVE both "trade" (one simulated, one real); SHADOW runs the
    full pipeline but must short-circuit before order submission regardless
    of this flag — this is just used to decide whether execution/ runs its
    simulated-fill path.
    """
    return mode in (TradingMode.PAPER, TradingMode.LIVE)
