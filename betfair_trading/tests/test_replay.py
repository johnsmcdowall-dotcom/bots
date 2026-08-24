from datetime import datetime, timedelta, timezone

from betfair_trading.backtesting.replay import ReplayEngine, market_snapshot_stream


def _t(seconds: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_merges_two_streams_in_strict_timestamp_order():
    market_stream = [(_t(0), "m0"), (_t(2), "m2"), (_t(5), "m5")]
    football_stream = [(_t(1), "f1"), (_t(3), "f3"), (_t(4), "f4")]

    engine = ReplayEngine({"market": market_stream, "football": football_stream})
    events = list(engine)

    assert [(e.timestamp, e.stream_name, e.payload) for e in events] == [
        (_t(0), "market", "m0"),
        (_t(1), "football", "f1"),
        (_t(2), "market", "m2"),
        (_t(3), "football", "f3"),
        (_t(4), "football", "f4"),
        (_t(5), "market", "m5"),
    ]


def test_never_yields_an_event_before_an_earlier_one_from_another_stream():
    # A naive "read stream A fully, then stream B" implementation would leak
    # stream B's earlier events after all of stream A's — this is exactly
    # the no-look-ahead bug the replay engine exists to prevent.
    early_but_second_stream = [(_t(10), "late")]
    later_but_first_stream = [(_t(0), "early"), (_t(1), "early2")]

    engine = ReplayEngine(
        {"a": later_but_first_stream, "b": early_but_second_stream}
    )
    timestamps = [e.timestamp for e in engine]
    assert timestamps == sorted(timestamps)
    assert timestamps == [_t(0), _t(1), _t(10)]


def test_single_stream_and_empty_streams():
    engine = ReplayEngine({"only": [(_t(0), "x")], "empty": []})
    events = list(engine)
    assert len(events) == 1
    assert events[0].payload == "x"


def test_no_streams_yields_nothing():
    assert list(ReplayEngine({})) == []


def test_is_lazy_pulls_one_item_ahead_per_stream_not_the_whole_stream():
    pulled = []

    def spying_stream():
        for i in range(5):
            pulled.append(i)
            yield (_t(i), i)

    engine = ReplayEngine({"spy": spying_stream()})
    iterator = iter(engine)
    first = next(iterator)
    # Only the first item (plus the lookahead pull that discovered it) should
    # have been consumed from the generator at this point.
    assert first.payload == 0
    assert len(pulled) <= 2


def test_market_snapshot_stream_adapter_uses_store():
    class FakeSnapshot:
        def __init__(self, timestamp):
            self.timestamp = timestamp

    class FakeStore:
        def read_market_snapshots(self, market_id):
            assert market_id == "1.1"
            return [FakeSnapshot(_t(0)), FakeSnapshot(_t(1))]

    stream = market_snapshot_stream(FakeStore(), "1.1")
    assert [ts for ts, _ in stream] == [_t(0), _t(1)]
