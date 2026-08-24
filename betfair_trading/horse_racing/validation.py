"""Validates a recorded horse-racing market before any research is built on
top of it — Phase 2's explicit requirement to verify timestamp accuracy,
ladder integrity, and runner mapping rather than assuming the recorder
worked.

This is deliberately a post-hoc check over what's in SnapshotStore, not a
write-time assertion — a write-time check can't catch e.g. a gap caused by
a stream reconnect, which is exactly the kind of defect that matters here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from betfair_trading.betfair.models import MarketStatus
from betfair_trading.betfair.ticks import is_valid_price
from betfair_trading.database.storage import SnapshotStore

MAX_ISSUES_REPORTED = 20  # avoid an unbounded report for a badly broken recording


@dataclass(frozen=True)
class ValidationReport:
    market_id: str
    snapshot_count: int
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_recorded_market(
    store: SnapshotStore,
    market_id: str,
    min_snapshots: int = 1,
) -> ValidationReport:
    snapshots = store.read_market_snapshots(market_id)
    issues: list[str] = []

    if len(snapshots) < min_snapshots:
        issues.append(
            f"only {len(snapshots)} snapshot(s) recorded for {market_id}, expected at least {min_snapshots}"
        )
        return ValidationReport(market_id, len(snapshots), tuple(issues))

    timestamps = [s.timestamp for s in snapshots]
    if timestamps != sorted(timestamps):
        issues.append("recorded timestamps are not monotonically non-decreasing")

    runner_reference = store.read_runner_reference(market_id)
    reference_ids = {r["selection_id"] for r in runner_reference} if runner_reference else None
    if reference_ids is None:
        issues.append(f"no runner_reference registered for {market_id} — recorder likely skipped register_race")

    for snapshot in snapshots:
        if len(issues) >= MAX_ISSUES_REPORTED:
            issues.append("... further issues suppressed (MAX_ISSUES_REPORTED reached)")
            break

        if snapshot.status is MarketStatus.OPEN and not snapshot.runners:
            issues.append(f"snapshot at {snapshot.timestamp} is OPEN but has zero runners")

        if reference_ids is not None:
            recorded_ids = {r.selection_id for r in snapshot.runners}
            unknown_ids = recorded_ids - reference_ids
            if unknown_ids:
                issues.append(
                    f"snapshot at {snapshot.timestamp} has selection_id(s) not in runner_reference: {unknown_ids}"
                )

        for runner in snapshot.runners:
            for level in (*runner.back, *runner.lay):
                if not is_valid_price(level.price):
                    issues.append(
                        f"runner {runner.selection_id} at {snapshot.timestamp} has an off-ladder price {level.price}"
                    )

    # De-dup while preserving first-seen order (the same defect class often
    # repeats across many snapshots; the report should say so once, not N times).
    deduped = tuple(dict.fromkeys(issues))
    return ValidationReport(market_id, len(snapshots), deduped)
