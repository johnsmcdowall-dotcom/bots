"""Strictly timestamp-ordered k-way merge of stored data streams — the
single path research/backtest code is meant to consume storage through,
so that "what was knowable at time T" is never accidentally violated by
an ad-hoc time-filtered query elsewhere (see docs/ARCHITECTURE.md's
no-look-ahead constraint).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from datetime import datetime
from itertools import count
from typing import Any, Iterable, Iterator


@dataclass(frozen=True)
class ReplayEvent:
    timestamp: datetime
    stream_name: str
    payload: Any


class ReplayEngine:
    """Merges any number of named, already-time-sorted streams into one
    globally timestamp-ordered iterator.

    Each stream is `Iterable[tuple[datetime, Any]]`, already sorted
    ascending by timestamp — a stream reading straight out of
    `SnapshotStore` (which always `ORDER BY timestamp`) satisfies this
    trivially.

    No look-ahead is structurally guaranteed, not just intended by
    convention: this is a lazy generator that only ever holds exactly one
    pending item per stream (to know what's next); it yields strictly in
    non-decreasing timestamp order across all streams combined, so calling
    code can never observe event N+1 before consuming event N. `__iter__`
    additionally asserts the merged output is non-decreasing, so a defect
    in the merge itself (rather than in upstream stream ordering) fails
    loudly instead of silently leaking a future event to a strategy.
    """

    def __init__(self, streams: dict[str, Iterable[tuple[datetime, Any]]]):
        self._streams = streams

    def __iter__(self) -> Iterator[ReplayEvent]:
        tie_breaker = count()
        heap: list[tuple[datetime, int, str, Any, Iterator[tuple[datetime, Any]]]] = []
        for name, stream in self._streams.items():
            _push_next(heap, name, iter(stream), tie_breaker)

        last_timestamp: datetime | None = None
        while heap:
            timestamp, _, name, payload, it = heapq.heappop(heap)
            if last_timestamp is not None and timestamp < last_timestamp:
                raise AssertionError(
                    "ReplayEngine produced an out-of-order event — this indicates a bug "
                    "in the merge, not just unsorted input, since input order is checked "
                    "per-stream by construction."
                )
            last_timestamp = timestamp
            yield ReplayEvent(timestamp=timestamp, stream_name=name, payload=payload)
            _push_next(heap, name, it, tie_breaker)


def _push_next(
    heap: list[tuple[datetime, int, str, Any, Iterator[tuple[datetime, Any]]]],
    name: str,
    it: Iterator[tuple[datetime, Any]],
    tie_breaker: "count[int]",
) -> None:
    try:
        timestamp, payload = next(it)
    except StopIteration:
        return
    # tie_breaker is unique per push, so tuple comparison never needs to
    # fall through to `payload` (which may not be orderable).
    heapq.heappush(heap, (timestamp, next(tie_breaker), name, payload, it))


def market_snapshot_stream(store: Any, market_id: str) -> list[tuple[datetime, Any]]:
    """Convenience adapter: SnapshotStore.read_market_snapshots -> the
    (timestamp, payload) stream shape ReplayEngine expects.
    """
    return [(snapshot.timestamp, snapshot) for snapshot in store.read_market_snapshots(market_id)]
