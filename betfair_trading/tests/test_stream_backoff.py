from betfair_trading.betfair.stream import BackoffPolicy, _run_with_backoff


def test_retries_until_success_with_increasing_delay():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("disconnected")
        # third attempt "succeeds" (returns normally = clean shutdown)

    sleeps = []
    _run_with_backoff(
        flaky,
        policy=BackoffPolicy(initial_delay_seconds=1.0, max_delay_seconds=10.0, multiplier=2.0),
        sleep=sleeps.append,
    )

    assert attempts["n"] == 3
    assert sleeps == [1.0, 2.0]  # backs off after the two failures, none after success


def test_stops_after_max_attempts():
    attempts = {"n": 0}

    def always_fails():
        attempts["n"] += 1
        raise ConnectionError("nope")

    sleeps = []
    _run_with_backoff(
        always_fails,
        policy=BackoffPolicy(initial_delay_seconds=0.1, max_delay_seconds=1.0, multiplier=2.0, max_attempts=4),
        sleep=sleeps.append,
    )

    assert attempts["n"] == 4
    assert len(sleeps) == 4


def test_delay_caps_at_max_delay():
    attempts = {"n": 0}

    def always_fails():
        attempts["n"] += 1
        raise ConnectionError("nope")

    sleeps = []
    _run_with_backoff(
        always_fails,
        policy=BackoffPolicy(initial_delay_seconds=1.0, max_delay_seconds=3.0, multiplier=2.0, max_attempts=5),
        sleep=sleeps.append,
    )

    assert sleeps == [1.0, 2.0, 3.0, 3.0, 3.0]
