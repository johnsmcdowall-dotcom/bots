# Staged Implementation Roadmap

Each phase only starts once the previous one has working tests. No phase
skips ahead to live order placement.

## Phase 1 — Infrastructure (THIS CHANGE)

Smallest useful milestone: **a system that can authenticate to Betfair
(given real credentials), record a market to disk in the platform's own
schema, and replay it back in strict timestamp order with zero look-ahead
— fully testable today with zero live credentials via fakes.**

Deliverables:
- `config/` — env-driven `Settings`, `.env.example` updated.
- `core/modes.py` — PAPER/SHADOW/LIVE gate.
- `core/interfaces.py` — `Signal`, `Strategy`, `FootballFeed` protocols
  shared by both sports.
- `core/journal.py` — `TradeJournalEntry` (every field the spec lists) +
  append-only store. No writers yet (Phase 5+), but the schema exists so
  nothing has to be retrofitted.
- `betfair/` — `models.py` (MarketSnapshot/RunnerLadder/Order/Fill),
  `auth.py` (cert-login wrapper), `client.py` (REST wrapper: catalogue,
  market book, orders, account funds), `stream.py` (streaming wrapper with
  reconnect/backoff). Real network calls untested here (no live creds in
  this environment) but structured so integration tests can run wherever
  credentials exist.
- `database/` — DuckDB DDL (`schema.py`) + `SnapshotStore` (partitioned
  Parquet writer/reader).
- `data/` — `football_feed.py` (Protocol + `NullFeed`), `ingestion.py`
  (orchestrates injected Betfair stream + feed → `SnapshotStore`, no
  strategy logic).
- `backtesting/replay.py` — k-way merge replay engine, strictly ordered,
  tested against out-of-order synthetic input to prove no look-ahead.
- `risk/limits.py` — `RiskLimits` dataclass with the spec's configurable
  defaults (position sizing bands, daily stop, exposure caps, drawdown
  response curve). Config only — no enforcement engine yet.
- `monitoring/logging_config.py` — structured logging setup.
- Scaffold `__init__.py` + short docstring for `horse_racing/`,
  `football/`, `features/`, `models/`, `strategies/`, `execution/`,
  `portfolio/`, `dashboard/`, `alerts/` marking them as later-phase.
- `tests/` — cover everything above that doesn't need live network.

## Phase 2 — Horse Historical Replay

Import Betfair historical horse-racing data (win markets, UK/IRE first).
Normalise into the Phase 1 schema. Verify ladder/volume/timestamp/runner
mapping/start-time integrity against known races before trusting any
research built on top. Extend `horse_racing/` with race/runner reference
data and time-to-off windowing.

## Phase 3 — Horse Research Features

`features/`: WOM, order-book imbalance, microprice, price velocity/
acceleration, volume velocity/acceleration, rolling windows (1s–5min),
cross-runner features (field-wide movement, book-% redistribution),
time-to-off regime tagging. Validated feature-by-feature (permutation
importance / ablation) before any model consumes them — per spec, remove
useless complexity rather than accumulate it.

## Phase 4 — Horse Baseline Models

Interpretable baselines first (logistic regression → tree/GBM) predicting
1-tick/2-tick/5–30s direction as calibrated probabilities, never
buy/sell labels. Calibration measured (Brier score, log loss, reliability
plots) before any model is allowed to size a trade.

## Phase 5 — Horse Strategies

Momentum, steamer, drifter, mean-reversion, cross-runner, favourite
segmentation, favourite/longshot bias (re-measured on recent data, not
assumed from old literature), BSP prediction, volume-shock, liquidity-
withdrawal, scalping. Each strategy graded, journaled (incl. REJECTs),
walk-forward validated independently before portfolio inclusion.

## Phase 6 — Execution Simulator

Realistic queue/fill modelling (OPTIMISTIC/REALISTIC/PESSIMISTIC), correct
Betfair tick ladder, commission, slippage. Every Phase 5 strategy is
re-evaluated under REALISTIC assumptions; only those still profitable
under REALISTIC (ideally marginally so under PESSIMISTIC) proceed.

## Phase 7 — Football Engine

Model-value, post-goal repricing, xG divergence, red-card repricing,
microstructure, external-consensus strategies — same grading/journal/
walk-forward discipline as Phase 5.

## Phase 8 — Portfolio System

Cross-sport signal ranking by risk-adjusted capital efficiency, not raw
EV. Correlation-aware exposure limits (per-market, per-match). This is
where the horse/football capital split becomes a measured output, not a
hard-coded 70/30.

## Phase 9 — Monte Carlo / Bankroll Research

≥10,000 simulated paths per validated strategy/portfolio config. £1,000 →
£2k/£5k/£10k probability distributions over 3/6/12/18/24 months, using
only out-of-sample returns. Risk-level comparison (0.25%–1.5%, fractional
Kelly variants) chosen on risk-adjusted terms, not best historical outcome.

## Phase 10 — Paper Trading

Full pipeline on live Betfair + live football data, real signals, simulated
fills, zero real orders. Compare predicted vs. actual fill conditions.
Dashboard built out here, once there's real paper data to show.

## Phase 11 — Controlled Live

Only after sufficient paper evidence. Requires `TRADING_MODE=LIVE` +
`LIVE_TRADING_CONFIRMED=YES`. Starts at the smallest configured risk band.
