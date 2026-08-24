"""DuckDB schema + SnapshotStore: the one physical store shared by both
sports (horse_racing and football tables are namespaced by a `sport`
column rather than duplicated table sets — see docs/ARCHITECTURE.md §3).
"""

from betfair_trading.database.storage import SnapshotStore

__all__ = ["SnapshotStore"]
