"""The trade journal: every signal, executed or rejected, for both sports.

Populated from Phase 5 (horse strategies) / Phase 7 (football strategies)
onward. The schema exists from Phase 1 so nothing has to be retrofitted
once strategies exist — and so REJECTs, which the spec explicitly requires
to be journaled for later research, are never an afterthought.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from betfair_trading.core.interfaces import Side, Signal, Sport, TradeGrade

JOURNAL_TABLE = "trade_journal"

JOURNAL_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {JOURNAL_TABLE} (
    entry_id            VARCHAR PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL,
    sport                VARCHAR NOT NULL,
    league_or_race       VARCHAR,
    event_name           VARCHAR,
    market_id            VARCHAR NOT NULL,
    market_type          VARCHAR,
    selection_id          VARCHAR NOT NULL,
    selection_name        VARCHAR,
    side                  VARCHAR NOT NULL,
    strategy               VARCHAR NOT NULL,
    trade_grade            VARCHAR NOT NULL,

    -- football-specific context (NULL for horse racing)
    score                  VARCHAR,
    minute                 DOUBLE,
    xg                     DOUBLE,
    xg_momentum            DOUBLE,
    shots                  INTEGER,
    red_cards               INTEGER,

    -- horse-racing-specific context (NULL for football)
    time_to_off_seconds       DOUBLE,
    runner_count               INTEGER,

    market_odds                DOUBLE,
    fair_odds                   DOUBLE,
    model_probability            DOUBLE,
    market_probability           DOUBLE,
    edge                          DOUBLE,
    expected_value                 DOUBLE,
    liquidity                       DOUBLE,
    spread_ticks                     DOUBLE,
    order_book_imbalance              DOUBLE,
    momentum_indicators                 VARCHAR,  -- JSON-encoded, sport/strategy-specific

    recommended_risk_pct                  DOUBLE,
    actual_risk_pct                        DOUBLE,
    requested_price                         DOUBLE,
    matched_price                            DOUBLE,
    exit_price                                DOUBLE,
    holding_time_seconds                       DOUBLE,
    commission                                  DOUBLE,
    profit_loss                                  DOUBLE,
    return_on_liability                           DOUBLE,

    reason_for_entry                               VARCHAR,
    reason_for_rejection                            VARCHAR,
    reason_for_exit                                  VARCHAR
);
"""


@dataclass(frozen=True)
class TradeJournalEntry:
    """One row of the journal. Construct via `from_signal` for the common case."""

    entry_id: str
    timestamp: datetime
    sport: Sport
    market_id: str
    selection_id: str
    side: Side
    strategy: str
    trade_grade: TradeGrade

    league_or_race: str | None = None
    event_name: str | None = None
    market_type: str | None = None
    selection_name: str | None = None

    score: str | None = None
    minute: float | None = None
    xg: float | None = None
    xg_momentum: float | None = None
    shots: int | None = None
    red_cards: int | None = None

    time_to_off_seconds: float | None = None
    runner_count: int | None = None

    market_odds: float | None = None
    fair_odds: float | None = None
    model_probability: float | None = None
    market_probability: float | None = None
    edge: float | None = None
    expected_value: float | None = None
    liquidity: float | None = None
    spread_ticks: float | None = None
    order_book_imbalance: float | None = None
    momentum_indicators: str | None = None

    recommended_risk_pct: float | None = None
    actual_risk_pct: float | None = None
    requested_price: float | None = None
    matched_price: float | None = None
    exit_price: float | None = None
    holding_time_seconds: float | None = None
    commission: float | None = None
    profit_loss: float | None = None
    return_on_liability: float | None = None

    reason_for_entry: str | None = None
    reason_for_rejection: str | None = None
    reason_for_exit: str | None = None

    @classmethod
    def from_signal(cls, signal: Signal, entry_id: str, **overrides: Any) -> "TradeJournalEntry":
        base = cls(
            entry_id=entry_id,
            timestamp=signal.timestamp,
            sport=signal.sport,
            market_id=signal.market_id,
            selection_id=signal.selection_id,
            side=signal.side,
            strategy=signal.strategy,
            trade_grade=signal.grade,
            market_odds=signal.available_price,
            fair_odds=signal.fair_odds,
            model_probability=signal.model_probability,
            market_probability=signal.market_probability,
            edge=signal.gross_edge,
            expected_value=signal.net_expected_value,
            commission=signal.estimated_commission,
            reason_for_entry=signal.reason if signal.is_actionable else None,
            reason_for_rejection=signal.rejection_reason if not signal.is_actionable else None,
        )
        if overrides:
            base = replace_dataclass(base, **overrides)
        return base


def replace_dataclass(entry: TradeJournalEntry, **overrides: Any) -> TradeJournalEntry:
    data = asdict(entry)
    data.update(overrides)
    return TradeJournalEntry(**data)


class JournalStore:
    """Append-only journal, one row per signal (accepted or rejected)."""

    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(self._db_path)
        self._conn.execute(JOURNAL_SCHEMA_SQL)

    def append(self, entry: TradeJournalEntry) -> None:
        row = asdict(entry)
        row["sport"] = entry.sport.value
        row["side"] = entry.side.value
        row["trade_grade"] = entry.trade_grade.value
        columns = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        self._conn.execute(
            f"INSERT INTO {JOURNAL_TABLE} ({columns}) VALUES ({placeholders})",
            list(row.values()),
        )

    def count(self) -> int:
        return self._conn.execute(f"SELECT COUNT(*) FROM {JOURNAL_TABLE}").fetchone()[0]

    def all_entries(self) -> list[dict[str, Any]]:
        cursor = self._conn.execute(f"SELECT * FROM {JOURNAL_TABLE} ORDER BY timestamp")
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "JournalStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
