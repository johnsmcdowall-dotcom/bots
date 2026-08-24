"""Finds today's UK/IRE WIN markets worth recording, and converts Betfair's
market-catalogue response into this platform's own dataclasses.

This is deliberately conservative: the quality filter exists to keep the
market recorder (and everything built on its output later) away from
illiquid/low-quality races rather than to maximise how much gets recorded.
Per docs/ARCHITECTURE.md, "prefer liquid markets" applies to data
collection too — a market recorded with 3 total matched is not useful
research data no matter how much of it there is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

# Betfair's event type ID for Horse Racing (stable, published in their API docs).
HORSE_RACING_EVENT_TYPE_ID = "7"
WIN_MARKET_TYPE_CODE = "WIN"


@dataclass(frozen=True)
class RunnerCatalogueEntry:
    selection_id: str
    runner_name: str
    sort_priority: int | None = None


@dataclass(frozen=True)
class RaceMarket:
    """A discovered WIN market, before any price data has been recorded."""

    market_id: str
    market_name: str
    event_id: str
    event_name: str
    venue: str | None
    country_code: str | None
    scheduled_start: datetime
    total_matched: float
    runners: tuple[RunnerCatalogueEntry, ...] = field(default_factory=tuple)

    @property
    def runner_count(self) -> int:
        return len(self.runners)

    def minutes_to_off(self, now: datetime) -> float:
        return (self.scheduled_start - now).total_seconds() / 60.0


def convert_market_catalogue(raw: Any) -> RaceMarket:
    """Convert one betfairlightweight MarketCatalogue (or a fake with the
    same attribute shape) into a RaceMarket.
    """
    event = raw.event
    runners = tuple(
        RunnerCatalogueEntry(
            selection_id=str(r.selection_id),
            runner_name=r.runner_name,
            sort_priority=getattr(r, "sort_priority", None),
        )
        for r in (raw.runners or [])
    )
    return RaceMarket(
        market_id=raw.market_id,
        market_name=raw.market_name,
        event_id=str(event.id),
        event_name=event.name,
        venue=getattr(event, "venue", None),
        country_code=getattr(event, "country_code", None),
        scheduled_start=raw.market_start_time,
        total_matched=getattr(raw, "total_matched", None) or 0.0,
        runners=runners,
    )


def catalogue_filter(
    country_codes: Iterable[str],
    start_from: datetime,
    start_to: datetime,
) -> dict[str, Any]:
    """Build the filter dict for BetfairClient.list_market_catalogue,
    restricted to horse racing WIN markets starting in the given window.
    """
    return {
        "event_type_ids": [HORSE_RACING_EVENT_TYPE_ID],
        "market_type_codes": [WIN_MARKET_TYPE_CODE],
        "market_countries": list(country_codes),
        "market_start_time": {
            "from": start_from.isoformat(),
            "to": start_to.isoformat(),
        },
    }


@dataclass(frozen=True)
class MarketQualityFilter:
    """The bar a discovered market must clear before it's worth recording."""

    min_total_matched: float = 200.0
    min_runners: int = 3
    max_runners: int = 40
    allowed_country_codes: tuple[str, ...] = ("GB", "IE")
    min_minutes_to_off: float = 0.0
    max_minutes_to_off: float = 120.0


def passes_quality_filter(race: RaceMarket, quality_filter: MarketQualityFilter, now: datetime) -> bool:
    if race.country_code is not None and race.country_code not in quality_filter.allowed_country_codes:
        return False
    if not (quality_filter.min_runners <= race.runner_count <= quality_filter.max_runners):
        return False
    if race.total_matched < quality_filter.min_total_matched:
        return False
    minutes_to_off = race.minutes_to_off(now)
    if not (quality_filter.min_minutes_to_off <= minutes_to_off <= quality_filter.max_minutes_to_off):
        return False
    return True


def select_win_markets(
    races: Iterable[RaceMarket],
    quality_filter: MarketQualityFilter,
    now: datetime | None = None,
) -> list[RaceMarket]:
    now = now or datetime.now(timezone.utc)
    return [race for race in races if passes_quality_filter(race, quality_filter, now)]


def discovery_window(now: datetime, minutes_ahead: float) -> tuple[datetime, datetime]:
    return now, now + timedelta(minutes=minutes_ahead)
