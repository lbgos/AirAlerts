"""Kyiv city event-based evaluation: recall with lead time, alarm-stretch precision, false alarms per night.

This is the main score for Kyiv config choice (replaces per-row Brier/AUC). For each config and horizon, fit on
everything before a test week (purged), calibrate on the 7 days before it, forecast Kyiv city every 5 minutes while
it is not under alert. `--window dev` pools the 3 weeks ending 7 days before the data end (used to choose configs);
`--window test` is the last week, run once for the chosen configs. Writes reports/kyiv_events_<window>.md.

Per horizon two tables:
- threshold sweep: caught sirens (a forecast >= threshold in the horizon before the siren), median lead,
  alarm stretches and how many were false, false alarms per night.
- four-state view for the website: share of forecasts per band and how often a siren followed within the horizon.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ua_alert_forecast.config import RAW_DIR
from ua_alert_forecast.dataset import HORIZONS, load_events
from ua_alert_forecast.events import NS_PER_MIN, bucket, event_report, state_stats
from ua_alert_forecast.experiments import BY_NAME
from ua_alert_forecast.model import Split, climatology, fit
from ua_alert_forecast.nebo import load_events as load_nebo
from ua_alert_forecast.train import REPORT_DIR, load_table

CACHE = Path("/tmp/glm_review/cache")
WEEK = pd.Timedelta(days=7)
STEP_NS = 5 * NS_PER_MIN


def cached(name: str, build):
    """Parse inputs once, then reuse the pickle across runs."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}.pkl"
    if path.exists():
        return pd.read_pickle(path)
    df = build()
    df.to_pickle(path)
    return df


def get_events() -> pd.DataFrame:
    return cached("events", lambda: load_events(RAW_DIR / "UkraineAlarmSignal.jsonl"))


def get_table(nebo: bool, corridor: bool = False, carrier: bool = False) -> pd.DataFrame:
    """5-minute start-model table; float32 to fit the memory limit."""
    key = f"t5_nebo{int(nebo)}_co{int(corridor)}_ca{int(carrier)}"
    table = cached(key, lambda: load_table(with_radar=False, step=pd.Timedelta(minutes=5), with_nebo=nebo))
    cols = [c for c in table.columns if table[c].dtype == "float64"]
    table[cols] = table[cols].astype("float32")
    return table


def city_sirens(events: pd.DataFrame) -> np.ndarray:
    """Kyiv city siren starts, one per 5-minute grid slot."""
    st = events.loc[(events.oblast == "kyiv") & (events.kind == "start"), "ts"]
    return bucket(st.to_numpy(dtype="datetime64[ns]").astype(np.int64), STEP_NS)


def needs(configs: list[str]) -> dict[str, bool]:
    groups = [g for n in configs for g in BY_NAME[n].groups]
    return {"nebo": "nebo" in groups, "corridor": "corridor" in groups, "carrier": "carrier" in groups}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", choices=["dev", "test"], required=True)
    parser.add_argument("--configs", nargs="+", default=["k1_base", "k1_kyiv"])
    parser.add_argument("--horizons", nargs="+", default=["15m", "30m", "1h"])
    parser.add_argument("--thresholds", nargs="+", type=float, default=[0.1, 0.2, 0.3, 0.5, 0.7])
    args = parser.parse_args()

    events = get_events()
    want = needs(args.configs)
    table = get_table(**want)
    end = table["ts"].max()
    week_ends = [end - WEEK - i * WEEK for i in range(3)] if args.window == "dev" else [end]
    sirens = city_sirens(events)

    sweeps, states = [], []
    for name in args.configs:
        config = BY_NAME[name]
        for h in args.horizons:
            ys, ps, cs, tss = [], [], [], []
            for we in week_ends:
                split = Split.ending(we, 7, config.calib_days)
                parts = split.periods(table, h, config.target)
                test = parts["test"][parts["test"]["region"] == "kyiv"]
                model = fit(table, h, split, config)
                ys.append(test[f"y_{h}"].to_numpy())
                ps.append(model.predict(test))
                cs.append(climatology(parts["train"], test, f"y_{h}"))
                tss.append(test["ts"].astype("int64").to_numpy())
                print(f"{name} {h} {we:%m-%d} done", flush=True)
            p, y = np.concatenate(ps), np.concatenate(ys)
            tsv = np.concatenate(tss)
            h_ns = int(HORIZONS[h].value)
            n_days = 7 * len(week_ends)
            sw = event_report(p, tsv, y, sirens[(sirens >= tsv[0]) & (sirens < tsv[-1] + h_ns)], h_ns, tuple(args.thresholds), STEP_NS, n_days)
            sweeps.append(pd.DataFrame({"config": name, "horizon": h, **sw}))
            states.append({"config": name, "horizon": h, "rows": len(y), "siren_rate": y.mean(),
                           **state_stats(y, p)})
            print(f"{name:22s} {h:4s} brier {((p - y) ** 2).mean():.4f} clim {((np.concatenate(cs) - y) ** 2).mean():.4f}", flush=True)

    span = f"{week_ends[-1] - WEEK:%Y-%m-%d %H:%M} to {week_ends[0]:%Y-%m-%d %H:%M} UTC"
    lines = [
        f"# Kyiv city event metrics, {args.window} ({span})",
        "",
        "Forecasts every 5 minutes while the city is not under alert, pooled over the window. A siren is caught when",
        "a forecast reached the threshold in the horizon before it; lead = minutes from the first such forecast.",
        "An alarm stretch is a run of consecutive >= threshold forecasts; false when no siren starts in (first,",
        "last + horizon]. fa/night = false stretches per night. Sirens with no forecast slot before them (city",
        "already under alert the whole horizon) are excluded from recall and reported per config below.",
        "",
    ]
    for h in args.horizons:
        lines += [f"## {h} threshold sweep", "", pd.concat(s for s in sweeps if s.horizon == h).round(3).to_markdown(index=False), ""]
    lines += ["## Four-state view (website bands)", "",
              pd.DataFrame(states).round(3).to_markdown(index=False), ""]
    (REPORT_DIR / f"kyiv_events_{args.window}.md").write_text("\n".join(lines) + "\n")
    print(f"-> {REPORT_DIR / f'kyiv_events_{args.window}.md'}")


if __name__ == "__main__":
    main()
