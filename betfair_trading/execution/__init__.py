"""Live order execution: place/cancel/replace, partial fills, hedge/
green-up, exposure tracking. Every order-placement path in here must call
core.modes.assert_live_allowed before submitting a real order.

Only the interface this package must eventually implement exists as of
Phase 1 (so PAPER mode has something to fake against); real logic and the
OPTIMISTIC/REALISTIC/PESSIMISTIC fill simulator land in Phase 6, per
docs/PLAN.md.
"""
