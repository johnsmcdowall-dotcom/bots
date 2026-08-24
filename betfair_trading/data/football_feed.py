"""Live football state feed, kept behind a Protocol so a real provider
(Opta/StatsPerform/whoever is actually procured) can be plugged in later
without touching ingestion.py or any strategy code.

No real provider is wired in yet — FOOTBALL_DATA_API_KEY is declared in
config/settings.py for whenever one is chosen, but which provider, what
its poll cadence/rate limits are, and how xG is defined are all TBD and
out of scope for Phase 1 infrastructure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from betfair_trading.core.interfaces import FootballFeed


class NullFeed:
    """Placeholder FootballFeed used until a real provider is configured.

    Always returns an empty-but-well-formed state so ingestion.py can be
    wired up and tested end-to-end today without a live data contract.
    """

    def poll(self, match_id: str) -> dict[str, Any]:
        return {
            "match_id": match_id,
            "timestamp": datetime.now(timezone.utc),
            "minute": None,
            "home_score": None,
            "away_score": None,
            "home_xg": None,
            "away_xg": None,
        }


def _assert_is_football_feed(feed: FootballFeed) -> None:
    """Cheap runtime sanity check used by tests/callers wiring up a new
    provider — Protocol conformance isn't checked automatically at
    instantiation time in Python.
    """
    if not hasattr(feed, "poll"):
        raise TypeError(f"{feed!r} does not implement the FootballFeed protocol (missing .poll)")
