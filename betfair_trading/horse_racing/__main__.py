"""CLI entrypoint for the live Phase 2 market recorder:

    python -m betfair_trading.horse_racing --minutes-ahead 120 --countries GB,IE

Discovers upcoming UK/IRE WIN markets meeting the quality bar and records
their full ladder via the streaming API into SnapshotStore, blocking for
the life of the recording session (Ctrl-C to stop).

Requires real Betfair credentials in .env — not exercised against the live
API in this environment (no credentials here). Every piece this wires
together (BetfairSession, BetfairClient, MarketStreamClient, SnapshotStore,
HorseRacingRecorder, MarketQualityFilter) is unit-tested independently
against fakes; this module is the thin, deliberately untested wiring on
top, structured so it can be integration-tested wherever credentials exist
without any calling code changing.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from betfair_trading.betfair.auth import BetfairSession
from betfair_trading.betfair.client import BetfairClient
from betfair_trading.betfair.stream import MarketStreamClient
from betfair_trading.config.settings import Settings
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.horse_racing.market_discovery import MarketQualityFilter
from betfair_trading.horse_racing.recorder import HorseRacingRecorder
from betfair_trading.monitoring.logging_config import configure_logging

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record live UK/IRE horse racing WIN markets")
    parser.add_argument("--minutes-ahead", type=float, default=120.0, help="discovery window, minutes from now")
    parser.add_argument("--countries", default="GB,IE", help="comma-separated Betfair country codes")
    parser.add_argument("--min-total-matched", type=float, default=200.0)
    parser.add_argument("--min-runners", type=int, default=3)
    parser.add_argument("--max-runners", type=int, default=40)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    configure_logging()
    settings = Settings.from_env()
    session = BetfairSession(settings.betfair)
    client = BetfairClient(session)
    stream_client = MarketStreamClient(session)
    store = SnapshotStore(settings.db_path)
    recorder = HorseRacingRecorder(client, store)

    quality_filter = MarketQualityFilter(
        allowed_country_codes=tuple(c.strip() for c in args.countries.split(",")),
        min_total_matched=args.min_total_matched,
        min_runners=args.min_runners,
        max_runners=args.max_runners,
    )

    races = recorder.discover_races(quality_filter, minutes_ahead=args.minutes_ahead)
    if not races:
        logger.warning("No races met the quality filter in the next %.0f minutes — nothing to record.", args.minutes_ahead)
        return

    now = datetime.now(timezone.utc)
    logger.info("Selected %d race(s) for recording:", len(races))
    for race in races:
        logger.info(
            "  %s (%s) — %s runners, off in %.1f min",
            race.market_name, race.venue, race.runner_count, race.minutes_to_off(now),
        )

    try:
        recorder.record(stream_client, races)  # blocks
    finally:
        store.close()
        session.logout()


if __name__ == "__main__":
    main()
