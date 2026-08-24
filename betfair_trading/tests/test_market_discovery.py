from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from betfair_trading.horse_racing.market_discovery import (
    HORSE_RACING_EVENT_TYPE_ID,
    MarketQualityFilter,
    RaceMarket,
    RunnerCatalogueEntry,
    WIN_MARKET_TYPE_CODE,
    catalogue_filter,
    convert_market_catalogue,
    discovery_window,
    passes_quality_filter,
    select_win_markets,
)

NOW = datetime(2026, 3, 1, 13, 0, 0, tzinfo=timezone.utc)


def _race(**overrides) -> RaceMarket:
    defaults = dict(
        market_id="1.111",
        market_name="2m Hcap",
        event_id="30001",
        event_name="York 1st Mar",
        venue="York",
        country_code="GB",
        scheduled_start=NOW + timedelta(minutes=45),
        total_matched=5000.0,
        runners=tuple(RunnerCatalogueEntry(str(i), f"Horse {i}", i) for i in range(1, 9)),
    )
    defaults.update(overrides)
    return RaceMarket(**defaults)


def _fake_catalogue_entry(**overrides):
    defaults = dict(
        market_id="1.222",
        market_name="1m Nov Stks",
        market_start_time=NOW + timedelta(minutes=30),
        total_matched=1500.0,
        event=SimpleNamespace(id=40002, name="Newmarket 1st Mar", venue="Newmarket", country_code="GB"),
        runners=[
            SimpleNamespace(selection_id=111, runner_name="Horse One", sort_priority=1),
            SimpleNamespace(selection_id=222, runner_name="Horse Two", sort_priority=2),
        ],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_convert_market_catalogue_basic_fields():
    race = convert_market_catalogue(_fake_catalogue_entry())

    assert race.market_id == "1.222"
    assert race.event_id == "40002"
    assert race.venue == "Newmarket"
    assert race.country_code == "GB"
    assert race.runner_count == 2
    assert race.runners[0].selection_id == "111"
    assert race.runners[0].runner_name == "Horse One"


def test_convert_market_catalogue_defaults_total_matched_when_absent():
    entry = _fake_catalogue_entry()
    del entry.total_matched
    race = convert_market_catalogue(entry)
    assert race.total_matched == 0.0


def test_minutes_to_off():
    race = _race(scheduled_start=NOW + timedelta(minutes=45))
    assert race.minutes_to_off(NOW) == 45.0


def test_catalogue_filter_shape():
    start, end = discovery_window(NOW, minutes_ahead=120)
    filter_dict = catalogue_filter(["GB", "IE"], start, end)

    assert filter_dict["event_type_ids"] == [HORSE_RACING_EVENT_TYPE_ID]
    assert filter_dict["market_type_codes"] == [WIN_MARKET_TYPE_CODE]
    assert filter_dict["market_countries"] == ["GB", "IE"]
    assert end - start == timedelta(minutes=120)


def test_passes_quality_filter_accepts_good_race():
    race = _race()
    assert passes_quality_filter(race, MarketQualityFilter(), NOW)


def test_rejects_wrong_country():
    race = _race(country_code="FR")
    assert not passes_quality_filter(race, MarketQualityFilter(), NOW)


def test_rejects_too_few_runners():
    race = _race(runners=tuple(RunnerCatalogueEntry(str(i), f"H{i}", i) for i in range(1, 3)))
    assert not passes_quality_filter(race, MarketQualityFilter(min_runners=3), NOW)


def test_rejects_low_liquidity():
    race = _race(total_matched=50.0)
    assert not passes_quality_filter(race, MarketQualityFilter(min_total_matched=200.0), NOW)


def test_rejects_race_outside_time_window():
    too_soon = _race(scheduled_start=NOW - timedelta(minutes=1))
    too_far = _race(scheduled_start=NOW + timedelta(minutes=200))
    filter_ = MarketQualityFilter(min_minutes_to_off=0.0, max_minutes_to_off=120.0)
    assert not passes_quality_filter(too_soon, filter_, NOW)
    assert not passes_quality_filter(too_far, filter_, NOW)


def test_select_win_markets_filters_a_list():
    races = [
        _race(market_id="1.1", total_matched=5000.0),
        _race(market_id="1.2", total_matched=10.0),  # illiquid, rejected
        _race(market_id="1.3", country_code="US"),  # wrong country, rejected
    ]
    selected = select_win_markets(races, MarketQualityFilter(), NOW)
    assert [r.market_id for r in selected] == ["1.1"]
