"""OVER_1_5_GOALS_SCALP — an independent football strategy module.

Trades the Betfair Over/Under 1.5 Goals market: an early-goal-anticipation
BACK on Over 1.5, staged across a 30-minute and a 50-minute entry, greened
up (hedged) the moment a goal is confirmed, with a hard time-based exit if
no goal has occurred. Nothing here removes, weakens, or is imported by any
existing horse-racing strategy module (strategies/, horse_racing/) — this
package is purely additive.

- config.py: Over15ScalpConfig (editable, not hard-coded) + GoalExitMode.
- scoring.py: prematch_goal_score / live_goal_pressure_score (0-100,
  configurable weighted aggregates of whichever inputs are available —
  see its docstring for why no single stat is ever made mandatory) and
  second_entry_fraction (edge-graded sizing for the 50-minute decision).
- hedge.py: the green-up/lay-stake calculation, generalised from
  strategies/engine.py's single-entry formula to N back entries at
  different prices, derived from first principles and checked against
  hand-worked examples in tests.
- state.py: TradeStatus (the spec's WATCHING...NO_TRADE lifecycle) and the
  pure decision functions (qualify, first/second entry, red-card gate,
  data-quality gate, goal/no-goal exit) that drive it — every decision
  returns a logged reason, approved or rejected.
- risk.py: stake sizing wired to risk/limits.py, enforcing "50% of the
  match allocation, never 50% of the bankroll" and never Martingale.
- stats.py: per-league and goal-time-band performance tracking.
- backtest.py: the spec's Version A/B/C/D presets and a chronological,
  walk-forward replay runner. Exercised only against synthetic data in
  this environment — see docs/PLAN.md for why (no real historical
  football+odds data has been imported).
- dashboard.py: the structured data the spec's dashboard section needs —
  data only, no UI (dashboard/ itself is still a Phase 10 scaffold).
"""
