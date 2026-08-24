"""Orchestrates capturing Betfair market data + football feed state into
SnapshotStore. Pure orchestration — no strategy logic, no signal
generation. Both the stream client and the feed are injected so this is
fully testable with fakes (see tests/test_ingestion.py).
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Iterable, Protocol

from betfair_trading.betfair.models import MarketSnapshot
from betfair_trading.core.interfaces import FootballFeed, Sport
from betfair_trading.database.storage import SnapshotStore

logger = logging.getLogger(__name__)


class MarketStreamLike(Protocol):
    def stream(self, market_ids: Iterable[str], on_snapshot: Callable[[MarketSnapshot], None]) -> None: ...


class IngestionService:
    def __init__(self, store: SnapshotStore):
        self._store = store

    def record_market_stream(
        self,
        stream_client: MarketStreamLike,
        market_ids: Iterable[str],
        sport: Sport,
    ) -> None:
        """Blocks for the life of the stream (stream_client.stream blocks),
        writing every incoming snapshot. Reconnect/backoff is the stream
        client's responsibility (betfair.stream.MarketStreamClient).
        """

        def on_snapshot(snapshot: MarketSnapshot) -> None:
            self._store.write_market_snapshot(sport, snapshot)

        stream_client.stream(market_ids, on_snapshot)

    def poll_football_once(self, feed: FootballFeed, match_ids: Iterable[str]) -> int:
        """Poll every match_id once, persist the state, return how many
        were written successfully (a poll failure for one match does not
        stop the others).
        """
        written = 0
        for match_id in match_ids:
            try:
                state = feed.poll(match_id)
            except Exception:
                logger.exception("Football feed poll failed for match_id=%s", match_id)
                continue
            timestamp = state.get("timestamp")
            if timestamp is None:
                logger.warning("Dropping football state with no timestamp for match_id=%s", match_id)
                continue
            self._store.write_football_state(match_id, timestamp, state)
            written += 1
        return written

    def poll_football_forever(
        self,
        feed: FootballFeed,
        match_ids: Iterable[str],
        interval_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        should_continue: Callable[[], bool] = lambda: True,
    ) -> None:
        match_ids = list(match_ids)
        while should_continue():
            self.poll_football_once(feed, match_ids)
            sleep(interval_seconds)
