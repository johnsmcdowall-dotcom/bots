"""DuckDB DDL for everything captured during ingestion.

One row per (market, timestamp, selection) for market data — DuckDB's
native LIST columns hold the ladder levels directly rather than flattening
into N fixed price/size columns, so ladder depth can be widened later
without a migration. Football live-state is a separate table since its
shape (score/minute/xG) is nothing like a Betfair ladder; horse-racing
reference data (races/runners) lives with the `horse_racing/` package once
Phase 2 needs it, not here.
"""

from __future__ import annotations

MARKET_SNAPSHOTS_TABLE = "market_snapshots"
FOOTBALL_STATE_SNAPSHOTS_TABLE = "football_state_snapshots"
MATCH_EVENTS_TABLE = "match_events"
RACE_REFERENCE_TABLE = "race_reference"
RUNNER_REFERENCE_TABLE = "runner_reference"

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {MARKET_SNAPSHOTS_TABLE} (
    sport                  VARCHAR NOT NULL,
    market_id               VARCHAR NOT NULL,
    timestamp                TIMESTAMPTZ NOT NULL,
    market_status              VARCHAR NOT NULL,
    in_play                     BOOLEAN NOT NULL,
    market_total_matched          DOUBLE NOT NULL,
    selection_id                   VARCHAR NOT NULL,
    runner_status                   VARCHAR NOT NULL,
    back_prices                      DOUBLE[] NOT NULL,
    back_sizes                        DOUBLE[] NOT NULL,
    lay_prices                         DOUBLE[] NOT NULL,
    lay_sizes                           DOUBLE[] NOT NULL,
    last_traded_price                    DOUBLE,
    runner_total_matched                  DOUBLE NOT NULL,
    ingested_at                            TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_market_ts
    ON {MARKET_SNAPSHOTS_TABLE} (market_id, timestamp);

CREATE TABLE IF NOT EXISTS {FOOTBALL_STATE_SNAPSHOTS_TABLE} (
    match_id       VARCHAR NOT NULL,
    timestamp        TIMESTAMPTZ NOT NULL,
    minute             DOUBLE,
    home_score           INTEGER,
    away_score            INTEGER,
    home_xg                DOUBLE,
    away_xg                 DOUBLE,
    raw_state                VARCHAR,  -- full feed payload as JSON, for fields not yet modelled
    ingested_at               TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_football_state_match_ts
    ON {FOOTBALL_STATE_SNAPSHOTS_TABLE} (match_id, timestamp);

CREATE TABLE IF NOT EXISTS {MATCH_EVENTS_TABLE} (
    match_id       VARCHAR NOT NULL,
    timestamp        TIMESTAMPTZ NOT NULL,
    event_type         VARCHAR NOT NULL,  -- GOAL / RED_CARD / PENALTY / VAR_REVERSAL / ...
    team                 VARCHAR,
    minute                 DOUBLE,
    detail                  VARCHAR,      -- JSON-encoded event-specific detail
    ingested_at               TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_match_events_match_ts
    ON {MATCH_EVENTS_TABLE} (match_id, timestamp);

-- Horse-racing race/runner reference data, captured at market-discovery
-- time (before/alongside recording starts) so recorded ladder rows can be
-- mapped back to a horse name, venue and scheduled off time. Kept generic
-- (no horse_racing/ import here — see database/storage.py) so this module
-- stays sport-agnostic infrastructure; the domain meaning of these fields
-- lives in horse_racing/market_discovery.py.
CREATE TABLE IF NOT EXISTS {RACE_REFERENCE_TABLE} (
    market_id           VARCHAR PRIMARY KEY,
    event_id              VARCHAR,
    event_name              VARCHAR,
    market_name                VARCHAR,
    venue                        VARCHAR,
    country_code                   VARCHAR,
    scheduled_start                  TIMESTAMPTZ NOT NULL,
    runner_count                       INTEGER NOT NULL,
    recorded_at                          TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS {RUNNER_REFERENCE_TABLE} (
    market_id      VARCHAR NOT NULL,
    selection_id     VARCHAR NOT NULL,
    runner_name        VARCHAR NOT NULL,
    sort_priority         INTEGER,
    PRIMARY KEY (market_id, selection_id)
);
"""
