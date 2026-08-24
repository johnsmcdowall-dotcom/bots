from betfair_trading.horse_racing.__main__ import build_arg_parser


def test_defaults():
    args = build_arg_parser().parse_args([])
    assert args.minutes_ahead == 120.0
    assert args.countries == "GB,IE"
    assert args.min_total_matched == 200.0
    assert args.min_runners == 3
    assert args.max_runners == 40


def test_overrides():
    args = build_arg_parser().parse_args(
        ["--minutes-ahead", "60", "--countries", "GB", "--min-total-matched", "500", "--min-runners", "5", "--max-runners", "20"]
    )
    assert args.minutes_ahead == 60.0
    assert args.countries == "GB"
    assert args.min_total_matched == 500.0
    assert args.min_runners == 5
    assert args.max_runners == 20
