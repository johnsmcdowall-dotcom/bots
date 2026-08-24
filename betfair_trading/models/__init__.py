"""Probability models. Interpretable baselines first (logistic regression
-> tree/GBM), calibration-checked (Brier score, log loss, reliability)
before any model is allowed to size a trade. Deep nets only if they beat
simpler models genuinely out-of-sample.

Empty scaffold as of Phase 1. Built out from Phase 4 per docs/PLAN.md.
"""
