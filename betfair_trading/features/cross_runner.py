"""Race-level (all-runners-at-once) features. Horse prices are not
independent — HORSE MODEL 7 in the spec calls this out explicitly: when
one runner shortens materially, probability must migrate elsewhere in the
book. This module builds a normalised "race book" from a single
MarketSnapshot and compares two of them (previous vs. current) to detect
whether one runner has moved too much or too little relative to the field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from betfair_trading.betfair.models import MarketSnapshot


@dataclass(frozen=True)
class RunnerBookPosition:
    selection_id: str
    best_back: float | None
    implied_probability: float | None  # 1 / best_back, un-normalised (sums to > 1 across the race: the overround)
    normalised_probability: float | None  # implied_probability / market overround — sums to 1 across active runners
    market_rank: int | None  # 1 = favourite (shortest price), None if not currently priced


@dataclass(frozen=True)
class RaceBook:
    market_id: str
    timestamp: datetime
    overround: float | None
    runners: tuple[RunnerBookPosition, ...]

    def runner(self, selection_id: str) -> RunnerBookPosition | None:
        for runner in self.runners:
            if runner.selection_id == selection_id:
                return runner
        return None

    @property
    def favourite(self) -> RunnerBookPosition | None:
        return self._by_rank(1)

    @property
    def second_favourite(self) -> RunnerBookPosition | None:
        return self._by_rank(2)

    def _by_rank(self, rank: int) -> RunnerBookPosition | None:
        for runner in self.runners:
            if runner.market_rank == rank:
                return runner
        return None


def build_race_book(snapshot: MarketSnapshot) -> RaceBook:
    """Rank runners by best_back (shortest price = rank 1) and normalise
    implied probabilities to sum to 1 across the currently-priced runners.
    Runners with no back price at all (empty ladder — can happen for a
    heavily-removed/inactive runner) get `None` everywhere and don't
    participate in ranking or normalisation.
    """
    implied: dict[str, float] = {}
    for runner in snapshot.runners:
        best_back = runner.best_back
        if best_back is not None and best_back.price > 0:
            implied[runner.selection_id] = 1.0 / best_back.price

    overround = sum(implied.values()) if implied else None
    ranked_ids = sorted(implied, key=lambda sid: -implied[sid])  # highest implied prob = shortest price = rank 1
    rank_by_id = {sid: i + 1 for i, sid in enumerate(ranked_ids)}

    positions = []
    for runner in snapshot.runners:
        best_back = runner.best_back
        implied_probability = implied.get(runner.selection_id)
        normalised_probability = (
            implied_probability / overround if implied_probability is not None and overround else None
        )
        positions.append(
            RunnerBookPosition(
                selection_id=runner.selection_id,
                best_back=best_back.price if best_back else None,
                implied_probability=implied_probability,
                normalised_probability=normalised_probability,
                market_rank=rank_by_id.get(runner.selection_id),
            )
        )

    return RaceBook(
        market_id=snapshot.market_id,
        timestamp=snapshot.timestamp,
        overround=overround,
        runners=tuple(positions),
    )


@dataclass(frozen=True)
class ProbabilityShift:
    selection_id: str
    delta_normalised_probability: float
    field_relative_delta: float  # this runner's delta minus the mean delta of every other runner


def probability_shifts(previous: RaceBook, current: RaceBook) -> tuple[ProbabilityShift, ...]:
    """Field-wide movement / book-% redistribution between two snapshots of
    the same race. Only runners priced (non-None normalised_probability) in
    both snapshots are included — a runner that just got its first price,
    or was suspended, has no well-defined delta.
    """
    shared_ids = [
        r.selection_id
        for r in current.runners
        if r.normalised_probability is not None
        and previous.runner(r.selection_id) is not None
        and previous.runner(r.selection_id).normalised_probability is not None
    ]
    if not shared_ids:
        return ()

    deltas = {
        sid: current.runner(sid).normalised_probability - previous.runner(sid).normalised_probability
        for sid in shared_ids
    }

    shifts = []
    for sid in shared_ids:
        others = [d for other_sid, d in deltas.items() if other_sid != sid]
        field_mean = sum(others) / len(others) if others else 0.0
        shifts.append(
            ProbabilityShift(
                selection_id=sid,
                delta_normalised_probability=deltas[sid],
                field_relative_delta=deltas[sid] - field_mean,
            )
        )
    return tuple(shifts)
