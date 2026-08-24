"""HORSE STRATEGY 7/12 — favourite/longshot calibration. This is a
RESEARCH REPORT, not a live Strategy: it does not implement
core.interfaces.Strategy and produces no Signals. Per the spec: "Research
actual modern Betfair behaviour... Do NOT hard-code historic favourite-
longshot assumptions" — this module measures calibration from real
recorded outcomes (horse_racing/outcomes.py), it does not assert that any
bias exists. Whether a genuinely exploitable, out-of-sample bias is found
is an empirical question this can only answer once run against real
settled markets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from betfair_trading.betfair.models import MarketSnapshot, MarketStatus
from betfair_trading.database.storage import SnapshotStore
from betfair_trading.horse_racing.outcomes import extract_win_outcomes
from betfair_trading.strategies.base import DEFAULT_COMMISSION, CommissionModel


@dataclass(frozen=True)
class OddsBucket:
    label: str
    min_price: float
    max_price: float  # exclusive, except the final open-ended bucket


DEFAULT_ODDS_BUCKETS: tuple[OddsBucket, ...] = (
    OddsBucket("1.01-1.25", 1.01, 1.25),
    OddsBucket("1.25-1.50", 1.25, 1.50),
    OddsBucket("1.50-2.00", 1.50, 2.00),
    OddsBucket("2.00-3.00", 2.00, 3.00),
    OddsBucket("3.00-5.00", 3.00, 5.00),
    OddsBucket("5.00-8.00", 5.00, 8.00),
    OddsBucket("8.00-15.00", 8.00, 15.00),
    OddsBucket("15.00+", 15.00, float("inf")),
)


@dataclass(frozen=True)
class RunnerOutcomeObservation:
    market_id: str
    selection_id: str
    price: float  # last recorded pre-off price -- a documented proxy, see collect_outcome_observations
    won: bool


def _last_pre_off_snapshot(snapshots: Sequence[MarketSnapshot]) -> MarketSnapshot | None:
    """The last snapshot while the market was still OPEN and not in-play —
    deliberately excludes CLOSED snapshots even though those also have
    `in_play=False`, since a settled market's ladder is typically emptied
    out and carries no usable price data.
    """
    for snapshot in reversed(snapshots):
        if snapshot.status is MarketStatus.OPEN and not snapshot.in_play:
            return snapshot
    return None


def collect_outcome_observations(store: SnapshotStore, market_ids: Sequence[str]) -> list[RunnerOutcomeObservation]:
    """One observation per runner with BOTH a known outcome (settlement
    captured — horse_racing/outcomes.py) AND a recorded pre-off price.
    Markets missing either are silently skipped, not estimated.

    The price used is the last recorded PRE-OFF snapshot's best_back — a
    proxy for the market's final pre-off assessment, not necessarily
    identical to actual BSP (same caveat as models/labels.py's
    closing_price_label; this platform doesn't capture real BSP yet).
    """
    observations: list[RunnerOutcomeObservation] = []
    for market_id in market_ids:
        outcomes = extract_win_outcomes(store, market_id)
        if not outcomes:
            continue
        snapshots = store.read_market_snapshots(market_id)
        reference_snapshot = _last_pre_off_snapshot(snapshots)
        if reference_snapshot is None:
            continue
        for runner in reference_snapshot.runners:
            if runner.selection_id not in outcomes or runner.best_back is None:
                continue
            observations.append(
                RunnerOutcomeObservation(
                    market_id=market_id,
                    selection_id=runner.selection_id,
                    price=runner.best_back.price,
                    won=outcomes[runner.selection_id],
                )
            )
    return observations


@dataclass(frozen=True)
class OddsBucketCalibration:
    bucket: OddsBucket
    sample_size: int
    mean_implied_probability: float | None
    actual_win_frequency: float | None
    back_roi: float | None  # commission-adjusted, per unit stake
    lay_roi: float | None  # commission-adjusted, per unit liability

    @property
    def calibration_error(self) -> float | None:
        """Positive = the market overrates this bucket's runners (implied
        probability exceeds how often they actually win); negative =
        underrates them. Zero sample size or missing data -> None, never 0.0."""
        if self.mean_implied_probability is None or self.actual_win_frequency is None:
            return None
        return self.mean_implied_probability - self.actual_win_frequency


def measure_favourite_longshot_calibration(
    observations: Sequence[RunnerOutcomeObservation],
    buckets: Sequence[OddsBucket] = DEFAULT_ODDS_BUCKETS,
    commission: CommissionModel = DEFAULT_COMMISSION,
) -> tuple[OddsBucketCalibration, ...]:
    results = []
    for bucket in buckets:
        in_bucket = [o for o in observations if bucket.min_price <= o.price < bucket.max_price]
        if not in_bucket:
            results.append(OddsBucketCalibration(bucket, 0, None, None, None, None))
            continue

        mean_implied = sum(1.0 / o.price for o in in_bucket) / len(in_bucket)
        win_frequency = sum(1 for o in in_bucket if o.won) / len(in_bucket)

        back_net_profits = []
        for o in in_bucket:
            gross = (o.price - 1.0) if o.won else -1.0
            back_net_profits.append(gross - commission.commission_on_profit(gross))
        back_roi = sum(back_net_profits) / len(in_bucket)

        lay_net_profits = []
        lay_liabilities = []
        for o in in_bucket:
            liability = o.price - 1.0
            gross = -liability if o.won else 1.0
            lay_net_profits.append(gross - commission.commission_on_profit(gross))
            lay_liabilities.append(liability)
        total_liability = sum(lay_liabilities)
        lay_roi = sum(lay_net_profits) / total_liability if total_liability > 0 else None

        results.append(
            OddsBucketCalibration(bucket, len(in_bucket), mean_implied, win_frequency, back_roi, lay_roi)
        )
    return tuple(results)
