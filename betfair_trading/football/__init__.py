"""Football domain logic.

- over_1_5_scalp/: OVER_1_5_GOALS_SCALP — an independent, additive
  strategy trading the Betfair Over/Under 1.5 Goals market around a
  30/50-minute staged entry, greened up on a goal, hard-exited if none
  arrives. The first concrete football strategy built against this
  package; see over_1_5_scalp/__init__.py for its module map and
  docs/PLAN.md for status/limitations.

Match state, xG inputs, and general event detection shared across future
football strategies remain unbuilt scaffold — over_1_5_scalp/ currently
defines its own scoring/state types rather than depending on shared
football-wide primitives that don't exist yet.
"""
