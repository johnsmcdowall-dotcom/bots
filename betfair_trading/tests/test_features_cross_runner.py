from datetime import datetime, timedelta, timezone

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.features.cross_runner import build_race_book, probability_shifts

NOW = datetime(2026, 3, 1, 14, 35, 0, tzinfo=timezone.utc)


def _runner(selection_id: str, best_back: float | None) -> RunnerLadder:
    back = (PriceLevel(best_back, 100.0),) if best_back is not None else ()
    return RunnerLadder(selection_id=selection_id, status=RunnerStatus.ACTIVE, back=back, lay=())


def _market(ts, runners) -> MarketSnapshot:
    return MarketSnapshot(market_id="1.1", timestamp=ts, status=MarketStatus.OPEN, in_play=False, total_matched=0.0, runners=runners)


def test_ranks_favourite_and_second_favourite():
    market = _market(NOW, (_runner("1", 4.0), _runner("2", 2.0), _runner("3", 10.0)))
    book = build_race_book(market)

    assert book.favourite.selection_id == "2"
    assert book.second_favourite.selection_id == "1"
    assert book.runner("3").market_rank == 3


def test_normalised_probabilities_sum_to_one():
    market = _market(NOW, (_runner("1", 4.0), _runner("2", 2.0), _runner("3", 10.0)))
    book = build_race_book(market)

    total = sum(r.normalised_probability for r in book.runners)
    assert round(total, 9) == 1.0
    # overround is just the sum of raw (un-normalised) implied probabilities
    assert round(book.overround, 9) == round(1 / 4.0 + 1 / 2.0 + 1 / 10.0, 9)


def test_unpriced_runner_has_none_fields_and_is_excluded_from_ranking():
    market = _market(NOW, (_runner("1", 4.0), _runner("2", None)))
    book = build_race_book(market)

    unpriced = book.runner("2")
    assert unpriced.best_back is None
    assert unpriced.implied_probability is None
    assert unpriced.normalised_probability is None
    assert unpriced.market_rank is None
    assert book.runner("1").market_rank == 1


def test_empty_race_has_no_overround():
    market = _market(NOW, (_runner("1", None),))
    book = build_race_book(market)
    assert book.overround is None
    assert book.favourite is None


def test_probability_shifts_detects_favourite_moving_more_than_field():
    previous = build_race_book(_market(NOW, (_runner("1", 4.0), _runner("2", 4.0), _runner("3", 4.0))))
    # runner 1 shortens hard; 2 and 3 barely move
    current = build_race_book(
        _market(NOW + timedelta(seconds=5), (_runner("1", 2.0), _runner("2", 4.5), _runner("3", 4.5)))
    )

    shifts = probability_shifts(previous, current)
    shift_by_id = {s.selection_id: s for s in shifts}

    assert shift_by_id["1"].delta_normalised_probability > 0
    # runner 1's shift should be well above the field-relative mean of the others (who drifted)
    assert shift_by_id["1"].field_relative_delta > shift_by_id["2"].field_relative_delta
    assert shift_by_id["1"].field_relative_delta > shift_by_id["3"].field_relative_delta


def test_probability_shifts_excludes_runners_not_priced_in_both_snapshots():
    previous = build_race_book(_market(NOW, (_runner("1", 4.0), _runner("2", None))))
    current = build_race_book(_market(NOW + timedelta(seconds=5), (_runner("1", 3.5), _runner("2", 5.0))))

    shifts = probability_shifts(previous, current)
    assert [s.selection_id for s in shifts] == ["1"]


def test_probability_shifts_empty_when_no_shared_runners():
    previous = build_race_book(_market(NOW, (_runner("1", None),)))
    current = build_race_book(_market(NOW + timedelta(seconds=5), (_runner("1", None),)))
    assert probability_shifts(previous, current) == ()
