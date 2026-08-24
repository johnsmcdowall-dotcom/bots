"""Wrapper over the Betfair Exchange Streaming API (market-change stream),
with reconnect/backoff.

Not exercised against the live API in this environment (no credentials) —
the reconnect/backoff loop (`_run_with_backoff`) is unit-tested in
isolation against a fake connect function that fails a configurable
number of times, so that logic has coverage independent of
betfairlightweight actually being reachable.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from betfair_trading.betfair.auth import BetfairSession
from betfair_trading.betfair.client import _convert_market_book
from betfair_trading.betfair.models import MarketSnapshot

logger = logging.getLogger(__name__)

OnSnapshot = Callable[[MarketSnapshot], None]


@dataclass(frozen=True)
class BackoffPolicy:
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    multiplier: float = 2.0
    max_attempts: int | None = None  # None = retry forever


def _run_with_backoff(
    connect_and_run: Callable[[], None],
    policy: BackoffPolicy = BackoffPolicy(),
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Call `connect_and_run` repeatedly, backing off after each failure,
    resetting the delay after any run that lasted long enough to be a real
    connection rather than an instant failure.

    `connect_and_run` is expected to block for the life of the stream and
    raise on disconnect; this function does not return until
    `policy.max_attempts` is exhausted (default: never, for a live
    long-running process) or `connect_and_run` returns normally (treated
    as a clean, intentional shutdown).
    """
    delay = policy.initial_delay_seconds
    attempt = 0
    while policy.max_attempts is None or attempt < policy.max_attempts:
        attempt += 1
        started_at = time.monotonic()
        try:
            connect_and_run()
            return  # clean shutdown
        except Exception:
            logger.exception("Betfair stream disconnected (attempt %d)", attempt)
        ran_for = time.monotonic() - started_at
        if ran_for >= policy.max_delay_seconds:
            delay = policy.initial_delay_seconds
        sleep(delay)
        delay = min(delay * policy.multiplier, policy.max_delay_seconds)


class MarketStreamClient:
    """Subscribes to market-change updates for a set of markets and calls
    `on_snapshot` with a converted MarketSnapshot for every update.
    """

    def __init__(self, session: BetfairSession, backoff: BackoffPolicy = BackoffPolicy()):
        self._session = session
        self._backoff = backoff

    def stream(self, market_ids: Iterable[str], on_snapshot: OnSnapshot) -> None:
        market_ids = list(market_ids)

        def connect_and_run() -> None:
            import betfairlightweight
            from betfairlightweight.filters import (
                streaming_market_data_filter,
                streaming_market_filter,
            )

            trading = self._session.login()
            listener = betfairlightweight.StreamListener(
                output_queue=None,
                max_latency=0.5,
            )
            stream = trading.streaming.create_stream(listener=listener)
            stream.subscribe_to_markets(
                market_filter=streaming_market_filter(market_ids=market_ids),
                market_data_filter=streaming_market_data_filter(
                    fields=[
                        "EX_BEST_OFFERS",
                        "EX_TRADED_VOL",
                        "EX_MARKET_DEF",
                    ],
                    ladder_levels=3,
                ),
            )

            def _forward(raw_books: Iterable[Any]) -> None:
                for raw_book in raw_books:
                    on_snapshot(_convert_market_book(raw_book))

            listener.on_data = _forward  # type: ignore[attr-defined]
            stream.start()

        _run_with_backoff(connect_and_run, policy=self._backoff)
