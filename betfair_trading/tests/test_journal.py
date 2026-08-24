from datetime import datetime, timezone

from betfair_trading.core.interfaces import Side, Signal, Sport, TradeGrade
from betfair_trading.core.journal import JournalStore, TradeJournalEntry


def _signal(grade: TradeGrade, rejection_reason: str | None = None) -> Signal:
    return Signal(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sport=Sport.FOOTBALL,
        strategy="post_goal_repricing",
        market_id="1.99",
        selection_id="88",
        side=Side.LAY,
        grade=grade,
        market_probability=0.55,
        model_probability=0.49,
        fair_odds=2.04,
        available_price=1.82,
        gross_edge=0.06,
        estimated_commission=0.02,
        estimated_slippage=0.01,
        estimated_fill_probability=0.85,
        net_expected_value=0.03,
        confidence=0.7,
        expected_holding_time_seconds=180.0,
        capital_required=15.0,
        reason="market overreacted to underdog goal" if grade != TradeGrade.REJECT else "n/a",
        rejection_reason=rejection_reason,
    )


def test_append_and_read_accepted_and_rejected_signals(tmp_path):
    db_path = tmp_path / "journal.duckdb"
    with JournalStore(db_path) as store:
        store.append(TradeJournalEntry.from_signal(_signal(TradeGrade.A), entry_id="1"))
        store.append(
            TradeJournalEntry.from_signal(
                _signal(TradeGrade.REJECT, rejection_reason="spread too wide"),
                entry_id="2",
            )
        )

        assert store.count() == 2
        entries = store.all_entries()

    assert entries[0]["trade_grade"] == "A"
    assert entries[0]["reason_for_entry"] == "market overreacted to underdog goal"
    assert entries[0]["reason_for_rejection"] is None

    assert entries[1]["trade_grade"] == "REJECT"
    assert entries[1]["reason_for_rejection"] == "spread too wide"
    assert entries[1]["reason_for_entry"] is None


def test_journal_persists_across_reopen(tmp_path):
    db_path = tmp_path / "journal.duckdb"
    with JournalStore(db_path) as store:
        store.append(TradeJournalEntry.from_signal(_signal(TradeGrade.A_PLUS), entry_id="1"))

    with JournalStore(db_path) as reopened:
        assert reopened.count() == 1
