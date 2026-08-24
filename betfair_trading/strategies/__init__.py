"""Horse-racing strategy modules — Phase 5.

- base.py: shared commission/fill-probability/grading infrastructure
  (documented placeholders pending Phase 6's real execution simulator).
- engine.py: the shared EV/grading core (`evaluate_priced_opportunity`)
  and the target-before-stop signal factory built on it
  (`evaluate_target_before_stop_opportunity`, HORSE MODEL 1).
- momentum.py: SteamerStrategy / DrifterStrategy (HORSE STRATEGY 2/3).
- mean_reversion.py: MeanReversionStrategy (HORSE MODEL 5) — fades an
  unconfirmed rapid move, the mirror image of momentum's requirement that
  a move BE volume-confirmed.
- scalping.py: ScalpingStrategy (HORSE STRATEGY 11) — tight configs
  gated on stricter liquidity/spread requirements.
- bsp_drift.py: BspDriftStrategy (HORSE STRATEGY 8) — trades a
  BSPForecastModel point forecast via the same EV core, with a caller-
  supplied confidence in place of a classifier's predict_proba.
- favourite_longshot.py: a RESEARCH REPORT (HORSE STRATEGY 7/12), not a
  live Strategy — measures calibration by odds bucket from real recorded
  settlement outcomes (horse_racing/outcomes.py), asserting no bias
  either way.

Every strategy here implements core.interfaces.Strategy
(`generate_signals(feature_rows) -> list[Signal]`) except
favourite_longshot.py. None invents its own probability estimate — each
delegates to a Phase 4 fitted model and only decides *which* rows are
worth asking the model about (or, for bsp_drift/favourite_longshot,
whether the model's own output already answers that). See docs/PLAN.md
Phase 5 for what's deliberately NOT built here (volume-shock/liquidity-
withdrawal strategies, left research-only per the spec's own caution
against fragile unvalidated microstructure strategies) and the standing
caveat that none of this has been run against real historical data yet.
"""
