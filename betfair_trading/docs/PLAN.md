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

## Phase 2 — Horse Market Recorder (live capture) — DONE (this change)

Smallest useful milestone toward good research data: **discover today's
UK/IRE WIN markets that clear a liquidity/runner-count/time-to-off quality
bar, register their race/runner reference data, record their full ladder
via the streaming API, and validate what was recorded before trusting it.**

Delivered:
- `betfair/ticks.py` — Betfair's exact tick ladder (1.01–1000), used to
  validate every recorded price is a real Betfair tick (and later by
  execution/backtesting for all target/stop/slippage math).
- `horse_racing/market_discovery.py` — `RaceMarket`/`RunnerCatalogueEntry`
  dataclasses, `convert_market_catalogue` (betfairlightweight → ours),
  `MarketQualityFilter` + `select_win_markets` (liquidity, runner count,
  country, time-to-off window), `catalogue_filter` (Betfair Horse Racing
  event type + WIN market type + country + start-time window).
- `database/schema.py` / `storage.py` — `race_reference` /
  `runner_reference` tables (market → venue/event/scheduled start, and
  selection_id → horse name), so recorded ladder rows can be mapped back
  to a horse. Kept generic/primitive in `storage.py` (no `horse_racing`
  import) to preserve the sport-agnostic database layer.
- `horse_racing/recorder.py` — `HorseRacingRecorder`: discover → register
  reference data → record via `IngestionService`.
- `horse_racing/validation.py` — `validate_recorded_market`: timestamp
  monotonicity, ladder non-empty while OPEN, every recorded price is a
  valid Betfair tick, every recorded selection_id is in the registered
  runner reference.
- `horse_racing/__main__.py` — live CLI entrypoint (untested against the
  live API here — no credentials in this environment; every component it
  wires together is unit-tested independently against fakes).

Still open for a later pass through this phase, once live credentials
exist: run the recorder against real markets, confirm captured timestamps
line up with Betfair's own publish times under real network jitter, and
decide the retention/compaction policy for `var/trading.duckdb` as volume
grows. Historical (pre-recorded) Betfair data import is a separate,
still-open piece of this phase — needed before Phase 3+ can build features
from more than what this session records live.

## Phase 3 — Horse Research Features — DONE (this change)

`features/`: WOM, order-book imbalance, microprice, price velocity/
acceleration, volume velocity/acceleration, rolling windows (1s–5min),
cross-runner features (field-wide movement, book-% redistribution),
time-to-off regime tagging.

Delivered:
- `features/microstructure.py` — instantaneous per-runner features from a
  single snapshot: best_back/lay, mid_price, spread (ticks + %),
  microprice (opposite-side-size-weighted), back/lay depth (raw and
  distance-weighted), weight_of_money, order_book_imbalance, traded
  volume, runner market share, implied probability. Every feature returns
  `None` rather than a fabricated value when the ladder can't support it
  (e.g. a runner with no lay side quoted).
- `features/rolling.py` — the 1s/3s/5s/10s/30s/60s/2min/5min windows:
  volume change/velocity/acceleration, VWAP, price velocity/acceleration,
  tick velocity, recent high/low, distance from high/low in ticks. VWAP is
  explicitly documented as an *approximation* (weighted by consecutive
  snapshot deltas, not a true per-trade VWAP) — the platform doesn't yet
  capture Betfair's traded-volume-by-price ladder (`EX_TRADED_VOL` at the
  per-price level), only aggregate `total_matched`; flagged as a follow-up
  below. Acceleration uses an index-based (not time-based) window split so
  a 3-point window — the minimum it's ever called with — doesn't strand
  itself into a 2/1 split with too few points on one side.
- `features/cross_runner.py` — `RaceBook`/`RunnerBookPosition` (normalised
  probability summing to 1 across priced runners, market rank,
  favourite/second-favourite) and `probability_shifts()` between two
  snapshots (field-relative delta — HORSE MODEL 7's "has this runner moved
  too much or too little relative to the field").
- `features/time_to_off.py` — `TimeToOffRegime`, the spec's 10 explicit
  bands plus `MORE_THAN_60_MIN`/`POST_OFF`, with boundary semantics fixed
  (exact boundary belongs to the shorter-countdown regime) so every race
  buckets identically regardless of timestamp jitter.
- `features/pipeline.py` — `build_feature_table()`: drives all of the
  above off `backtesting.replay.ReplayEngine` (not an ad-hoc storage
  query) to build one row per (runner, snapshot). Verified with a
  black-box no-look-ahead test: the same market recorded to two stores
  (one truncated partway through, one complete) produces byte-for-byte
  identical `FeatureRow`s for every timestamp both stores share — proving
  a row's rolling/cross-runner features can never be affected by
  snapshots recorded after it. `FeatureRow.to_flat_dict()` flattens
  everything into one prefixed dict per row for Phase 4 to consume as a
  training dataframe.

Deliberately not done here (belongs to Phase 4, once baseline models
exist): permutation importance / ablation validation of which features
actually add out-of-sample value. This phase built and unit-tested the
computation; Phase 4 is what gets to decide which of it is useless
complexity worth deleting.

Flagged follow-up: capture Betfair's per-price traded-volume ladder
(`EX_TRADED_VOL`) in `betfair/models.py`/`storage.py` so `rolling.py`'s
VWAP can be exact rather than an approximation — small, isolated change,
deferred rather than bundled into this phase's scope.

## Phase 4 — Horse Baseline Models — DONE (this change, machinery only — see caveat)

Interpretable baselines first (logistic regression) predicting tick
direction and target-before-stop outcomes as calibrated probabilities,
never buy/sell labels. Calibration measured (Brier score, log loss,
reliability tables) — a model that classifies well but is badly calibrated
must not be allowed to size a trade.

Delivered:
- `models/labels.py` — forward-looking label construction, kept
  structurally separate from `features/` (nothing in `features/` imports
  `models/`) so a label can never leak backwards into a live feature:
  - `short_horizon_label` (HORSE MODEL 2): the spec's 7-bucket signed tick
    movement (`<=-3, -2, -1, 0, +1, +2, >=+3`) at a given horizon.
  - `target_before_stop_label` (HORSE MODEL 1): walks forward from an
    entry to determine TARGET / STOP / TIMEOUT, BACK/LAY-aware.
    `CANONICAL_TARGET_STOP_CONFIGS` covers the spec's exact combinations
    (+1/-1 … +5/-3) for both sides — one model per config, not one
    hard-coded universal target/stop.
  - `closing_price_label` (HORSE MODEL 8): explicitly documented as a
    PROXY using the last recorded price, not real BSP — the platform
    hasn't captured Betfair's settlement/cleared-orders data (that's a
    separate, not-yet-built capture path), so this must not be read as a
    genuine BSP forecast until that exists.
- `models/calibration.py` — `brier_score`, `log_loss`,
  `multiclass_brier_score`, `reliability_table` — pure, independently
  tested against hand-computed values.
- `models/dataset.py` — `build_labelled_rows` (feature+label assembly),
  `chronological_market_split` (orders by `scheduled_start`, never
  shuffled, market-level not row-level so two rows from the same race
  can't land on opposite sides of a split), `to_model_matrix` (one-hot
  encodes `time_to_off_regime`, drops identifier columns, and — this
  surfaced two real bugs during testing — drops any row with a `None`
  among the selected feature columns rather than imputing a fabricated
  value).
- `models/baseline.py` — `ShortHorizonDirectionModel` (multinomial
  logistic regression, 7 classes), `TargetBeforeStopModel` (binary
  logistic regression, trained only on resolved TARGET/STOP rows —
  TIMEOUT is excluded per the spec's separate "neither occurs" estimate,
  not folded in as a third class), `BSPForecastModel` (ridge regression on
  the closing-price proxy, evaluated on mean absolute tick error, not
  calibration, since it's a regression target not a probability).
- `models/train.py` — `train_baseline_models()`: chronological split,
  fits every baseline on TRAIN, evaluates on VALIDATION. Configs/horizons
  with insufficient class diversity or data skip cleanly (`{"skipped":
  ...}`) rather than fitting a degenerate model or raising.

Two real bugs found by testing before they shipped: `to_model_matrix`
originally only added a column to the schema if it was numeric in *some*
scanned row, so a column that was `None` in every row of a small sample
(e.g. an acceleration feature with too little history) silently vanished
from the schema instead of correctly dropping those rows — fixed to
always include the column and let the None-check drop the rows. And the
first version of the end-to-end test used 5-second-spaced synthetic
snapshots, which structurally can never populate a 1s/3s rolling window
with enough points — not a code bug, but it demonstrated that
`to_model_matrix`'s no-fabrication policy will correctly starve a model of
every row if the recorded tick density doesn't support the requested
window sizes. Real Betfair streaming data is sub-second; this is a data-
density fact worth remembering once Phase 2's live recorder actually runs
against real markets.

**Caveat, stated plainly**: none of this has been run against real
historical horse-racing data. Phase 2 only built live-recording
infrastructure, and there are no live Betfair credentials in this
environment to have actually recorded a market; no bulk historical import
exists either. Every mechanic above (label correctness, chronological
split, model fitting, calibration scoring) is proven correct against
synthetic data in `tests/`. That is necessary but not sufficient — it
proves the machinery works, not that any of these baselines have a real
edge. Permutation-importance/ablation validation of which *features*
actually earn their place (deferred from Phase 3) still needs real data to
mean anything, and so does any claim about calibration or profitability.
Do not read "182 tests passing" as "this finds a real edge" — it doesn't
yet, because it hasn't been given real data to find one in.

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
