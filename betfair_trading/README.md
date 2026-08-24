# Betfair Multi-Sport Trading Platform

Horse racing (primary, high-turnover) + football (secondary,
high-conviction) trading system for the Betfair Exchange.

**Status: Phase 1 (infrastructure) only.** No strategies, no models, no
live trading. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the
full design and [`docs/PLAN.md`](docs/PLAN.md) for the staged roadmap.

## What exists right now

- `betfair/` — Betfair REST/streaming client wrapper and dataclasses
  (untested against the live API in this environment — no credentials
  here; the response-conversion logic is unit-tested against fakes).
- `database/` — DuckDB schema + `SnapshotStore` (partitioned-Parquet
  export supported).
- `data/` — ingestion orchestration + a pluggable, provider-agnostic
  football feed interface (currently only a `NullFeed` placeholder).
- `backtesting/replay.py` — timestamp-ordered, no-look-ahead replay
  engine.
- `core/` — PAPER/SHADOW/LIVE mode gate, shared `Signal`/`Strategy`
  interfaces, the trade journal.
- `risk/limits.py` — configurable risk-limit defaults from the spec.
- `horse_racing/`, `football/`, `features/`, `models/`, `strategies/`,
  `execution/`, `portfolio/`, `dashboard/`, `alerts/` — empty package
  scaffolds marking where later phases land; see `docs/PLAN.md`.

## Setup

```bash
cd betfair_trading
pip install -r requirements.txt
cp .env.example .env   # fill in real values only when you have them
```

No credentials are required to run the test suite — Betfair/football
clients are exercised through fakes.

## Tests

```bash
cd /home/user/bots
python -m pytest betfair_trading/tests -v
```

## Safety

`TRADING_MODE` defaults to `PAPER`. No real order can ever be placed
unless **both** `TRADING_MODE=LIVE` and `LIVE_TRADING_CONFIRMED=YES` are
set — enforced in `core.modes.assert_live_allowed`, the single choke point
every execution code path must call.
