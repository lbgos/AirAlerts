"""Kyiv over one week: how many sirens and all-clears, and how many the 15-minute forecast called with high certainty.

Compares the live models without and with @nebo_raketa features (f1 vs f2). Both are trained on everything before the
week (purged), calibrated on the 7 days before it, and forecast every 5 minutes during it.
`--window dev` is the week before last (used to check the features), `--window test` the last week (run once).
Writes reports/kyiv_week_<window>.md.
"""

import argparse

import numpy as np
import pandas as pd

from ua_alert_forecast.experiments import BY_NAME
from ua_alert_forecast.model import Split, climatology, fit, points
from ua_alert_forecast.train import REPORT_DIR, load_table

HORIZON = "15m"
WINDOW = pd.Timedelta(minutes=15)
THRESHOLDS = (0.5, 0.3)
REGIONS = {"kyiv": "Kyiv city", "kyivska": "Kyiv oblast"}
MODELS = {"old (alert channel)": ("f1s_recent_cons", "f1c_recent_cons"), "new (+ @nebo_raketa)": ("f2s_nebo", "f2c_nebo")}


def runs(mask: np.ndarray, ts: np.ndarray, step: np.int64) -> list[np.ndarray]:
    """Indices of consecutive forecast times (one grid step apart) where `mask` holds."""
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    breaks = np.flatnonzero(np.diff(ts[idx]) != step) + 1
    return np.split(idx, breaks)


def score_events(rows: pd.DataFrame, p: np.ndarray, y: np.ndarray, events: np.ndarray, step: np.int64) -> dict:
    """events: times of the sirens (or all-clears). Caught = a forecast >= threshold in the 15 min before it.
    False alarm = a run of forecasts >= threshold where nothing happened within 15 min of any of them."""
    ts = rows["ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64)
    out = {"events": len(events)}
    for thr in THRESHOLDS:
        hi = p >= thr
        caught = sum(bool(hi[(ts >= e - WINDOW.value) & (ts < e)].any()) for e in events)
        false = sum(1 for r in runs(hi, ts, step) if (y[r] == 0).all())
        out[f"caught at {thr:.0%}+"] = caught
        out[f"false alarms at {thr:.0%}+"] = false
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", choices=["dev", "test"], required=True)
    args = parser.parse_args()

    step = pd.Timedelta(minutes=5)
    table = load_table(with_radar=False, step=step, with_nebo=True)
    data_end = table["ts"].max()
    week_end = data_end - pd.Timedelta(days=7) if args.window == "dev" else data_end
    week_start = week_end - pd.Timedelta(days=7)

    events, metrics = [], []
    for model, (start_name, clear_name) in MODELS.items():
        for kind, name in (("siren", start_name), ("all-clear", clear_name)):
            config = BY_NAME[name]
            split = Split.ending(week_end, 7, config.calib_days)
            parts = split.periods(table, HORIZON, config.target)
            m = fit(table, HORIZON, split, config)
            ycol = f"y_{HORIZON}" if kind == "siren" else f"yc_{HORIZON}"
            for region, label in REGIONS.items():
                rows = parts["test"][parts["test"]["region"] == region].sort_values("ts")
                p, y = m.predict(rows), rows[ycol].to_numpy()
                # Event times: siren = first forecast time after which a start happens; read from the full table so
                # every start/end inside the week counts once (state flips from not active to active and back).
                reg = table[(table["region"] == region) & (table["ts"] >= week_start) & (table["ts"] < week_end)].sort_values("ts")
                act = reg["active"].to_numpy()
                t = reg["ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64)
                flips = np.flatnonzero(act[1:] != act[:-1]) + 1
                ev = t[flips[act[flips]]] if kind == "siren" else t[flips[~act[flips]]]
                clim = climatology(parts["train"], rows, ycol)
                events.append({"model": model, "": f"{kind}, {label}", **score_events(rows, p, y, ev, np.int64(step.value))})
                metrics.append({"model": model, "": f"{kind}, {label}", "brier": ((p - y) ** 2).mean(),
                                "brier climatology": ((clim - y) ** 2).mean(), "points": points(y, p, clim)})

    ev_df, met_df = pd.DataFrame(events), pd.DataFrame(metrics)
    lines = [
        f"# Kyiv, {week_start:%Y-%m-%d %H:%M} to {week_end:%Y-%m-%d %H:%M} UTC ({args.window} week), 15-minute forecast",
        "",
        "Forecasts every 5 minutes. A siren (all-clear) is caught when the forecast was at the threshold or above at",
        "some point in the 15 minutes before it. A false alarm is a stretch of forecasts at the threshold or above with",
        "nothing happening within 15 minutes of any of them. Sirens/all-clears are counted on a 5-minute grid, so two",
        "within the same 5 minutes count once.",
        "",
        ev_df.to_markdown(index=False),
        "",
        "Brier (lower is better) and points (gain over climatology per 100 forecasts, confident right x3, confident",
        "wrong x10; higher is better):",
        "",
        met_df.round(4).to_markdown(index=False),
        "",
    ]
    (REPORT_DIR / f"kyiv_week_{args.window}.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
