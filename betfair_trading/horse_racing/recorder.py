"""HorseRacingRecorder: the Phase-2 milestone. Discovers today's UK/IRE WIN
markets meeting the quality bar, registers their race/runner reference
data, and records their full ladder into SnapshotStore via the streaming
API.

Both the Betfair client and the stream client are injected, so discovery
and recording are independently testable with fakes (see
tests/test_horse_racing_recorder.py) without live Betfair credentials.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

from betfair_trading.betfair.client import BetfairClient
from betfair_trading.core.interfaces import Sport
from betfair_trading.data.ingestion import IngestionService, MarketStreamLike
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.horse_racing.market_discovery import (
    MarketQualityFilter,
    RaceMarket,
    catalogue_filter,
    convert_market_catalogue,
    discovery_window,
    select_win_markets,
)

logger = logging.getLogger(__name__)


class HorseRacingRecorder:
    def __init__(self, client: BetfairClient, store: SnapshotStore):
        self._client = client
        self._store = store
        self._ingestion = IngestionService(store)

    def discover_races(
        self,
        quality_filter: MarketQualityFilter,
        now: datetime | None = None,
        minutes_ahead: float = 120.0,
    ) -> list[RaceMarket]:
        now = now or datetime.now(timezone.utc)
        start, end = discovery_window(now, minutes_ahead)
        filter_ = catalogue_filter(quality_filter.allowed_country_codes, start, end)
        raw_catalogue = self._client.list_market_catalogue(filter_, max_results=200)
        races = [convert_market_catalogue(entry) for entry in raw_catalogue]
        return select_win_markets(races, quality_filter, now)

    def register_race(self, race: RaceMarket) -> None:
        """Persist race/runner reference data. Called automatically by
        `record`, but exposed separately so discovery and registration can
        run ahead of the (blocking) recording call.
        """
        self._store.write_race_reference(
            market_id=race.market_id,
            event_id=race.event_id,
            event_name=race.event_name,
            market_name=race.market_name,
            venue=race.venue,
            country_code=race.country_code,
            scheduled_start=race.scheduled_start,
            runners=[(r.selection_id, r.runner_name, r.sort_priority) for r in race.runners],
        )

    def record(self, stream_client: MarketStreamLike, races: Iterable[RaceMarket]) -> None:
        """Blocks for the life of the stream (reconnect/backoff is the
        stream client's responsibility — see betfair.stream.MarketStreamClient).
        """
        races = list(races)
        if not races:
            logger.warning("No races to record — nothing selected by the quality filter.")
            return
        for race in races:
            self.register_race(race)
        market_ids = [race.market_id for race in races]
        logger.info("Recording %d race(s): %s", len(races), [r.market_name for r in races])
        self._ingestion.record_market_stream(stream_client, market_ids, Sport.HORSE_RACING)
