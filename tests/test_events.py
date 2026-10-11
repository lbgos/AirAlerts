"""Event-based metric checks on hand-built forecast sets."""

import numpy as np

from ua_alert_forecast.events import (NS_PER_MIN, bucket, caught_leads, event_report, state_stats, stretch_stats,
                                      unforecastable_mask)

STEP = 5 * NS_PER_MIN


def grid(n):
    return np.arange(n, dtype=np.int64) * STEP


def test_bucket_merges_same_slot():
    t0 = 1000 * NS_PER_MIN
    assert list(bucket(np.array([t0 + 1, t0 + 4 * NS_PER_MIN, t0 + 5 * NS_PER_MIN]))) == [t0, t0 + 5 * NS_PER_MIN]


def test_caught_leads_first_hot_forecast():
    tsv = grid(40)  # 200 minutes
    p = np.zeros(40)
    p[16:18] = 0.6  # hot 80-85 min, cool after
    sirens = np.array([20 * STEP, 33 * STEP])  # at 100 min: caught with lead 20; at 165 min: not caught
    leads = caught_leads(p, tsv, sirens, 30 * NS_PER_MIN, 0.5)
    assert list(leads) == [20.0]


def test_caught_leads_uses_earliest_hot_in_window():
    tsv = grid(40)
    p = np.zeros(40)
    p[14] = 0.7  # 70 min
    sirens = np.array([20 * STEP])  # 100 min: inside the horizon window, lead capped at the horizon
    assert caught_leads(p, tsv, sirens, 30 * NS_PER_MIN, 0.5)[0] == 30.0


def test_stretch_false_needs_siren_in_promise():
    tsv = grid(10)
    p = np.array([0, 0.9, 0.9, 0, 0.9, 0.9, 0.9, 0, 0, 0], dtype=float)
    sirens = np.array([2 * STEP])  # during the first stretch, none near the second
    st = stretch_stats(p, tsv, sirens, 30 * NS_PER_MIN, 0.5, STEP)
    assert st["n_stretches"] == 2 and st["false"] == 1 and st["precision"] == 0.5


def test_stretch_gap_under_alert_splits_runs():
    tsv = np.array([0, STEP, 10 * STEP, 11 * STEP])  # a 45-minute gap stands for forecasts stopping
    p = np.array([0.9, 0.9, 0.9, 0.9], dtype=float)
    st = stretch_stats(p, tsv, np.array([]), 15 * NS_PER_MIN, 0.5, STEP)
    assert st["n_stretches"] == 2


def test_unforecastable_mask():
    tsv = grid(20)
    sirens = np.array([5 * STEP, 25 * STEP])  # second has no forecast rows in its horizon
    assert list(unforecastable_mask(sirens, tsv, 15 * NS_PER_MIN)) == [False, True]


def test_state_stats_bands():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.02, 0.5, 0.8, 0.4])
    st = state_stats(y, p)
    assert st["share_no"] == 0.25 and st["hit_no"] == 0.0
    assert st["share_yes"] == 0.25 and st["hit_yes"] == 1.0
    assert st["hit_probably_yes"] == 0.5


def test_event_report_excludes_unforecastable_from_recall():
    tsv = grid(40)
    p = np.full(40, 0.9)
    sirens = np.array([5 * STEP, 45 * STEP])  # 45 min: no forecast row in its 15m window
    rep = event_report(p, tsv, np.zeros(40), sirens, 15 * NS_PER_MIN, (0.5,), STEP, days=1)
    assert rep.iloc[0]["of"] == 1 and rep.iloc[0]["recall"] == 1.0
