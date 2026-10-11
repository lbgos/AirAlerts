"""Event-based scoring for one region's siren forecasts (Kyiv city is the user's case).

Per-row Brier/AUC say nothing about what the user cares about: are sirens caught, with how much lead time,
how many stretches of "loud" forecasts end in nothing. Here everything is measured on events:

- A siren is *caught* at threshold z when a forecast at or above z happens in the horizon before it
  (the lead is the time from the first such forecast to the siren).
- An *alarm stretch* is a maximal run of consecutive above-threshold forecast times (a run ends where a
  forecast drops below, or where the region goes under alert and forecasts stop). It counts as a *false alarm*
  when no siren starts between its first forecast and horizon minutes after its last one.
- The four-state view for the website bands forecasts into No / Probably no / Probably yes / Yes and reports,
  per band, the share of forecasts and how often a siren followed within the horizon.

Sirens are start events deduplicated onto the forecast grid (two starts in one grid slot are one siren).
Starts while the region is already under alert cannot be caught (no forecasts exist then); they are reported
separately as `unforecastable` and left out of the recall denominator.
"""

import numpy as np
import pandas as pd

NS_PER_MIN = 6e10  # ns; used as float for unit math, cast to int where it enters array ops
STATES = ((0.0, 0.05, "no"), (0.05, 0.3, "probably_no"), (0.3, 0.7, "probably_yes"), (0.7, 1.01, "yes"))
STATE_NAMES = [s[2] for s in STATES]
GRID_MINUTES = 5
STEP_NS = GRID_MINUTES * 60_000_000_000


def bucket(times: np.ndarray, step_ns: int = 5 * NS_PER_MIN) -> np.ndarray:
    """Event times floored to the forecast grid (ns), so sirens in one grid slot count once."""
    step_ns = int(step_ns)
    return np.unique(times // step_ns * step_ns)


def caught_leads(p: np.ndarray, tsv: np.ndarray, sirens: np.ndarray, horizon_ns: int, thr: float) -> np.ndarray:
    """Lead times (minutes) of the sirens caught by forecasts at or above `thr` in their horizon window."""
    hot = p >= thr
    leads = []
    for s in sirens:
        lo, hi = np.searchsorted(tsv, s - horizon_ns), np.searchsorted(tsv, s, side="left")
        w = np.flatnonzero(hot[lo:hi])
        if len(w):
            leads.append((s - tsv[lo + w[0]]) / NS_PER_MIN)
    return np.array(leads)


def stretches(p: np.ndarray, tsv: np.ndarray, thr: float, step_ns: int) -> tuple[np.ndarray, np.ndarray]:
    """First and last ns times of maximal runs of forecasts at or above `thr` on the grid."""
    hot = p >= thr
    first = np.flatnonzero(hot & ~np.concatenate(([False], hot[:-1] & (np.diff(tsv) == step_ns))))
    last = np.flatnonzero(hot & ~np.concatenate((hot[1:] & (np.diff(tsv) == step_ns), [False])))
    return tsv[first], tsv[last]


def stretch_stats(p: np.ndarray, tsv: np.ndarray, sirens: np.ndarray, horizon_ns: int, thr: float,
                  step_ns: int) -> dict:
    """Alarm stretches at `thr`: total, false (no siren in (first, last + horizon]), and their precision."""
    first, last = stretches(p, tsv, thr, step_ns)
    false = 0
    for a, b in zip(first, last):
        lo, hi = np.searchsorted(sirens, a, side="right"), np.searchsorted(sirens, b + horizon_ns, side="right")
        false += lo == hi  # no siren in the promised window
    return {"n_stretches": len(first), "false": false, "precision": (len(first) - false) / len(first) if len(first) else float("nan")}


def unforecastable_mask(sirens: np.ndarray, tsv: np.ndarray, horizon_ns: int) -> np.ndarray:
    """Mask over `sirens`: True where no forecast row exists in the horizon before the siren."""
    if not len(sirens):
        return np.zeros(0, dtype=bool)
    lo = np.searchsorted(tsv, sirens - horizon_ns, side="left")
    hi = np.searchsorted(tsv, sirens, side="left")
    return lo >= hi


def state_stats(y: np.ndarray, p: np.ndarray) -> dict:
    """Per band: share of forecasts and how often a siren followed (label `y` = siren within the horizon)."""
    out = {}
    for lo, hi, name in STATES:
        s = (p >= lo) & (p < hi)
        out[f"share_{name}"] = s.mean()
        out[f"hit_{name}"] = y[s].mean() if s.any() else float("nan")
    return out


def event_report(p: np.ndarray, tsv: np.ndarray, y: np.ndarray, sirens: np.ndarray, horizon_ns: int,
                 thresholds: tuple[float, ...] = (0.1, 0.2, 0.3, 0.5, 0.7), step_ns: int = 5 * NS_PER_MIN,
                 days: float | None = None) -> pd.DataFrame:
    """Threshold sweep (one row per threshold) plus the four-state block, for one pooled forecast set.

    `tsv` and `sirens` must be ascending (sort the pooled weeks); `days`: window length for false alarms per
    night (default: the span of the forecasts).
    """
    catchable = sirens[~unforecastable_mask(sirens, tsv, horizon_ns)]
    rows = []
    for thr in thresholds:
        leads = caught_leads(p, tsv, catchable, horizon_ns, thr)
        st = stretch_stats(p, tsv, sirens, horizon_ns, thr, step_ns)
        span = days * 86400e9 if days else max(tsv[-1] - tsv[0], 1)
        rows.append({"threshold": thr, "caught": len(leads), "of": len(catchable),
                     "recall": len(leads) / len(catchable) if len(catchable) else np.nan,
                     "median_lead_min": np.median(leads) if len(leads) else np.nan, **st,
                     "fa_per_night": st["false"] / span * 86400 * 1e9})
    return pd.DataFrame(rows)
