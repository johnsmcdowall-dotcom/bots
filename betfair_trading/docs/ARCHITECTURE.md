# Betfair Multi-Sport Trading Platform — Architecture

Horse racing (primary, high-turnover) + football (secondary, high-conviction)
trading system for the Betfair Exchange.

## 0. Repository inspection (done before writing any code)

The `bots` monorepo previously held two unrelated apps:

| Path | What it is |
|---|---|
| `piccolo-pizzeria/` | Next.js + Supabase restaurant ordering site. Unrelated domain, own DB, untouched by this work. |
| `deepseek_harness/` | Small DeepSeek chat/tool-calling CLI. |

Checklist findings:

- **Existing Betfair integration**: none.
- **Existing credential architecture**: none Betfair-specific. The repo's
  established convention (from `deepseek_harness`) is secrets in a
  git-ignored `.env`, read via `os.environ`, with `.env.example` holding
  placeholders only — reused here for Betfair/data-provider credentials.
- **Existing database**: none for trading. `piccolo-pizzeria`'s
  Supabase/Postgres is a separate app's storage and is not reused here.
- **Existing strategies**: none.
- **Existing tests**: none for trading (`piccolo-pizzeria` has its own,
  unrelated).
- **Security concerns**: none found pre-existing (no committed secrets in
  either project); the main thing to get right *for this build* is that
  Betfair certs/passwords and any paid data-feed keys never land in git,
  and that the LIVE-order code path is gated (see §5).
- **Missing infrastructure**: everything — Betfair auth/REST/streaming
  client, historical + live data storage, market replay, feature
  pipelines, models, strategy layer for two sports, an execution
  simulator with realistic fills, risk/portfolio management, paper/shadow/
  live modes, dashboard, alerting.

Conclusion: greenfield build. New top-level package `betfair_trading/` in
the monorepo, isolated dependencies/tests from the other two projects.

## 1. Directory layout

Mirrors the modular structure requested, as **subpackages of one
`betfair_trading` package** (kept inside its own top-level directory,
consistent with how `piccolo-pizzeria/` and `deepseek_harness/` already
sit side by side in this monorepo — nothing here touches those two):

```
betfair_trading/
  core/            Cross-cutting, sport-agnostic primitives: the PAPER/
                   SHADOW/LIVE mode gate, shared interfaces/protocols
                   (Strategy, Signal, Feed), the trade journal (every
                   signal — including REJECTs — for both sports).
  config/          Env-driven settings: credentials, DB paths, mode flags.
  risk/            RiskLimits config (position sizing %, daily stop,
                   per-market/per-match exposure caps, drawdown response
                   curve) — all figures configurable, sport-agnostic.
  betfair/         Betfair API layer: cert-login auth, REST wrapper
                   (market catalogue/book, place/cancel/replace orders,
                   current/cleared orders), Exchange Streaming API wrapper
                   (market-change + order-change streams), and the wire-
                   format-independent dataclasses (MarketSnapshot,
                   RunnerLadder, Order, Fill) everything else consumes.
  data/            Pluggable external data feeds behind protocols: live
                   football state (score/minute/xG/etc, provider TBD) and
                   historical horse-racing data import (Betfair historical
                   data files → normalised snapshots).
  database/        Schema (DuckDB DDL) + SnapshotStore (partitioned
                   Parquet + DuckDB query layer). One physical store,
                   shared by both sports, tables namespaced by sport.
  horse_racing/    Horse-specific domain logic (race/runner modelling,
                   time-to-off regimes, cross-runner book). Empty package
                   scaffold now; built out from Phase 2 onward.
  football/        Football-specific domain logic (match state, xG
                   inputs, event detection). Empty scaffold now; built out
                   from Phase 7.
  features/        Shared microstructure feature computation (WOM,
                   imbalance, microprice, velocity/acceleration, rolling
                   windows) — sport-agnostic where the market data shape
                   is the same. Phase 3+.
  models/          Probability models (logistic/GBM baselines first, per
                   spec — "begin with interpretable baselines"). Phase 4+.
  strategies/       Strategy modules (one file per strategy), each
                   producing a graded Signal via the `core` interfaces.
                   Phase 5 (horse) / Phase 7 (football).
  backtesting/       Timestamp-ordered replay engine (k-way merge of
                     stored snapshot streams, strictly no look-ahead) +,
                     later, the execution/fill simulator
                     (OPTIMISTIC/REALISTIC/PESSIMISTIC). Replay engine is
                     Phase 1/2 infrastructure; the fill simulator is
                     Phase 6.
  execution/         Live order execution: place/cancel/replace, partial
                     fills, hedge/green-up, exposure tracking. Phase 6+
                     for real logic; Phase 1 only defines the interface it
                     must implement so PAPER mode can fake it.
  portfolio/          Cross-sport portfolio manager — ranks/admits signals
                     from both engines by risk-adjusted capital
                     efficiency, enforces correlation/exposure limits.
                     Phase 8.
  monitoring/          Structured logging setup + regime/edge-decay
                       monitoring. Logging config is Phase 1; strategy
                       health monitoring is later.
  dashboard/           Local dashboard app. Phase 10-adjacent (after paper
                     evidence exists to display).
  alerts/              Push/Telegram/Discord/email notifiers for A/A+
                     signals. Late phase.
  tests/               Unit tests, no network/live credentials required —
                     Betfair/data clients are exercised through fakes.
docs/
  ARCHITECTURE.md   This file.
  PLAN.md           Staged roadmap with phase-by-phase deliverables.
```

## 2. Guiding constraints (apply to every phase)

- **No look-ahead.** All backtest/research code consumes data exclusively
  through `backtesting.replay.ReplayEngine`, which merges stored snapshot
  streams strictly by timestamp. Nothing queries storage directly with an
  ad-hoc time filter for research purposes — that's how future data leaks
  in accidentally.
- **PAPER is the default and only safe-by-default mode.** `SHADOW` runs
  the full live pipeline (signals, risk, portfolio) but never calls the
  execution layer's order-submission method. `LIVE` additionally requires
  *both* `TRADING_MODE=LIVE` and `LIVE_TRADING_CONFIRMED=YES` — enforced
  in one choke-point function (`core.modes.assert_live_allowed`) that
  every order-placement path must call.
- **The quant engine produces signals; the LLM only explains them.**
  Nothing in `strategies/`, `models/`, `risk/`, `portfolio/`, or
  `execution/` may ever be gated on an LLM call. A later explanation layer
  consumes an already-fully-computed `Signal` object.
- **Every signal is journaled**, including REJECTs, via `core.journal`,
  from the first phase strategies exist (Phase 4/5 for horse racing) — not
  bolted on retroactively.
- **Credentials never hardcoded.** All secrets via `.env` (git-ignored),
  documented with placeholders in `.env.example`, read once in
  `config.settings`.
- **No sport-specific capital allocation is hard-coded.** The 70/30
  horse/football research emphasis is a *research effort* split, not a
  capital-allocation constant in code — `portfolio/` (Phase 8) allocates
  by measured EV/confidence/drawdown/correlation/liquidity, per sport,
  dynamically.

## 3. Data storage choice

DuckDB + partitioned Parquet (spec's suggested research-tier option):

- No server process, zero infra cost while there's no live data flowing
  yet; trivial to run in CI for the test suite.
- Parquet is the durable/portable artifact, partitioned by
  `sport/market_id/date` — straightforward to bulk-load into
  Postgres/TimescaleDB later if an always-on multi-writer ingester needs
  a proper server-backed time-series DB (revisit once volume/concurrency
  is real, likely around Phase 10).
- DuckDB gives SQL over those Parquet files directly for research and for
  the replay engine's merge-read.
- One schema, two sports: tables carry a `sport` column
  (`horse_racing` / `football`) rather than duplicating table sets, since
  the underlying Betfair market-book shape (ladder, traded volume, status)
  is identical between the two — only the *feature/event* tables differ
  (football gets score/xG event tables; horse racing gets race/runner
  reference tables), which is exactly why those live in separate
  `horse_racing/` / `football/` domain packages rather than in `database/`.

## 4. Credential architecture

All secrets in `.env` (git-ignored), read once by `config/settings.py`.
`.env.example` documents every variable with a placeholder:

- `BETFAIR_USERNAME`, `BETFAIR_PASSWORD`, `BETFAIR_APP_KEY`
- `BETFAIR_CERT_PATH`, `BETFAIR_CERT_KEY_PATH` (cert-login)
- `FOOTBALL_DATA_API_KEY` (provider TBD — `data/football_feed.py` is
  provider-agnostic behind a `Protocol`)
- `EXTERNAL_ODDS_API_KEY` (optional, football external-consensus strategy)
- `TRADING_DB_PATH` (defaults under the package)
- `TRADING_MODE` (`PAPER` default / `SHADOW` / `LIVE`)
- `LIVE_TRADING_CONFIRMED` (must be exactly `YES`, together with
  `TRADING_MODE=LIVE`, for `core.modes.assert_live_allowed()` to pass)

Nothing outside `config/settings.py` reads `os.environ` directly for these
— every other module receives an already-constructed `Settings` or client
object (dependency injection), which is also what makes ingestion/replay
testable with fakes and keeps credentials out of test code entirely.

## 5. What is explicitly NOT built in this change

Per the spec's own phasing ("do not try to build everything
simultaneously"), this change delivers **Phase 1 only**: infrastructure.
No strategies, no models, no features, no execution simulator, no
portfolio manager, no dashboard, no Monte Carlo. Those require either
historical data (not yet imported) or a working replay/storage foundation
(this change) to backtest against honestly — building them first would
mean designing strategies against nothing, which the spec explicitly
warns against.
