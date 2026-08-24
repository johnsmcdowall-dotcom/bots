"""SnapshotStore: writes market/football snapshots into DuckDB (the durable
store) and can export any table to partitioned Parquet for portability /
bulk-loading into a server-backed store later (see docs/ARCHITECTURE.md §3
for why DuckDB+Parquet rather than a server DB at this stage).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)
from betfair_trading.core.interfaces import Sport
from betfair_trading.database.schema import (
    FOOTBALL_STATE_SNAPSHOTS_TABLE,
    MARKET_SNAPSHOTS_TABLE,
    MATCH_EVENTS_TABLE,
    SCHEMA_SQL,
)


class SnapshotStore:
    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(self._db_path)
        self._conn.execute(SCHEMA_SQL)

    # -- writes -----------------------------------------------------------

    def write_market_snapshot(self, sport: Sport, snapshot: MarketSnapshot) -> None:
        """One row per runner, per the spec's requirement to capture ladder
        depth, traded volume, status, and timestamp for every runner.
        """
        ingested_at = datetime.now(timezone.utc)
        rows = [
            (
                sport.value,
                snapshot.market_id,
                snapshot.timestamp,
                snapshot.status.value,
                snapshot.in_play,
                snapshot.total_matched,
                runner.selection_id,
                runner.status.value,
                [level.price for level in runner.back],
                [level.size for level in runner.back],
                [level.price for level in runner.lay],
                [level.size for level in runner.lay],
                runner.last_traded_price,
                runner.total_matched,
                ingested_at,
            )
            for runner in snapshot.runners
        ]
        if not rows:
            return
        self._conn.executemany(
            f"INSERT INTO {MARKET_SNAPSHOTS_TABLE} VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    def write_football_state(self, match_id: str, timestamp: datetime, state: dict[str, Any]) -> None:
        self._conn.execute(
            f"INSERT INTO {FOOTBALL_STATE_SNAPSHOTS_TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                match_id,
                timestamp,
                state.get("minute"),
                state.get("home_score"),
                state.get("away_score"),
                state.get("home_xg"),
                state.get("away_xg"),
                json.dumps(state, default=str),
                datetime.now(timezone.utc),
            ],
        )

    def write_match_event(
        self,
        match_id: str,
        timestamp: datetime,
        event_type: str,
        team: str | None = None,
        minute: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            f"INSERT INTO {MATCH_EVENTS_TABLE} VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                match_id,
                timestamp,
                event_type,
                team,
                minute,
                json.dumps(detail or {}, default=str),
                datetime.now(timezone.utc),
            ],
        )

    # -- reads --------------------------------------------------------------

    def market_snapshot_timestamps(self, market_id: str) -> list[datetime]:
        rows = self._conn.execute(
            f"SELECT DISTINCT timestamp FROM {MARKET_SNAPSHOTS_TABLE} "
            "WHERE market_id = ? ORDER BY timestamp",
            [market_id],
        ).fetchall()
        return [row[0] for row in rows]

    def market_snapshot_count(self, market_id: str | None = None) -> int:
        if market_id is None:
            return self._conn.execute(f"SELECT COUNT(*) FROM {MARKET_SNAPSHOTS_TABLE}").fetchone()[0]
        return self._conn.execute(
            f"SELECT COUNT(*) FROM {MARKET_SNAPSHOTS_TABLE} WHERE market_id = ?", [market_id]
        ).fetchone()[0]

    def football_state_count(self, match_id: str | None = None) -> int:
        if match_id is None:
            return self._conn.execute(f"SELECT COUNT(*) FROM {FOOTBALL_STATE_SNAPSHOTS_TABLE}").fetchone()[0]
        return self._conn.execute(
            f"SELECT COUNT(*) FROM {FOOTBALL_STATE_SNAPSHOTS_TABLE} WHERE match_id = ?", [match_id]
        ).fetchone()[0]

    def read_market_snapshots(self, market_id: str) -> list[MarketSnapshot]:
        """Reconstruct MarketSnapshot objects (one per timestamp, all runners
        regrouped) ordered by timestamp — the read side backtesting.replay
        feeds off of. Regrouping happens here rather than in the caller so
        replay code never has to know the storage layer stores one row per
        runner.
        """
        rows = self._conn.execute(
            f"""
            SELECT timestamp, market_status, in_play, market_total_matched,
                   selection_id, runner_status, back_prices, back_sizes,
                   lay_prices, lay_sizes, last_traded_price, runner_total_matched
            FROM {MARKET_SNAPSHOTS_TABLE}
            WHERE market_id = ?
            ORDER BY timestamp, selection_id
            """,
            [market_id],
        ).fetchall()

        snapshots_by_ts: dict[datetime, MarketSnapshot] = {}
        for (
            timestamp,
            market_status,
            in_play,
            market_total_matched,
            selection_id,
            runner_status,
            back_prices,
            back_sizes,
            lay_prices,
            lay_sizes,
            last_traded_price,
            runner_total_matched,
        ) in rows:
            runner = RunnerLadder(
                selection_id=selection_id,
                status=RunnerStatus(runner_status),
                back=tuple(PriceLevel(p, s) for p, s in zip(back_prices, back_sizes)),
                lay=tuple(PriceLevel(p, s) for p, s in zip(lay_prices, lay_sizes)),
                last_traded_price=last_traded_price,
                total_matched=runner_total_matched,
            )
            if timestamp not in snapshots_by_ts:
                snapshots_by_ts[timestamp] = MarketSnapshot(
                    market_id=market_id,
                    timestamp=timestamp,
                    status=MarketStatus(market_status),
                    in_play=in_play,
                    total_matched=market_total_matched,
                    runners=(),
                )
            existing = snapshots_by_ts[timestamp]
            snapshots_by_ts[timestamp] = MarketSnapshot(
                market_id=existing.market_id,
                timestamp=existing.timestamp,
                status=existing.status,
                in_play=existing.in_play,
                total_matched=existing.total_matched,
                runners=existing.runners + (runner,),
            )
        return [snapshots_by_ts[ts] for ts in sorted(snapshots_by_ts)]

    # -- portability ----------------------------------------------------------

    def export_to_parquet(self, out_dir: str | Path) -> None:
        """Export all tables to Parquet, partitioned by sport/market_id for
        market_snapshots and by match_id for the football tables — the
        durable, portable artifact referenced in docs/ARCHITECTURE.md §3.
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        self._conn.execute(
            f"COPY {MARKET_SNAPSHOTS_TABLE} TO '{out_dir / 'market_snapshots'}' "
            "(FORMAT PARQUET, PARTITION_BY (sport, market_id), OVERWRITE_OR_IGNORE)"
        )
        self._conn.execute(
            f"COPY {FOOTBALL_STATE_SNAPSHOTS_TABLE} TO '{out_dir / 'football_state_snapshots'}' "
            "(FORMAT PARQUET, PARTITION_BY (match_id), OVERWRITE_OR_IGNORE)"
        )
        self._conn.execute(
            f"COPY {MATCH_EVENTS_TABLE} TO '{out_dir / 'match_events'}' "
            "(FORMAT PARQUET, PARTITION_BY (match_id), OVERWRITE_OR_IGNORE)"
        )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SnapshotStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
