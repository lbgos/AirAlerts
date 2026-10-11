"""Kyiv: does a deterministic "quiet-state" guard on top of the model cut false alarms?

The event metrics put model precision at ~0.45 for the 15m/30m horizon at the 0.3 threshold — many alarm
stretches while the whole approach corridor is quiet, where the raw state hazards say P15 ~1-2%. Test a hard
rule applied to the pooled forecasts: where the state says quiet, cap the forecast. The state uses only
events before the forecast time, so the rule is deployable:

- arm "ko": Kyiv oblast fully clear.
- arm "quiet": ko clear AND no neighbor siren start in 2h AND no corridor mention within 140 km in 60m.

Usage: scripts/kyiv_guard.py --configs k1_base k1_kyiv [--window dev] [--cap 0.05]. Reloads the cached pooled
forecasts that scripts/kyiv_events.py wrote, rebuilds the state, and writes reports/kyiv_guard_<window>.md
with the event metrics before and after the cap.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ua_alert_forecast.config import RAW_DIR
from ua_alert_forecast.dataset import HORIZONS, alert_intervals, count_before, is_active, load_events, minutes_since
from ua_alert_forecast.events import event_report, state_stats
from ua_alert_forecast.geo import NEIGHBORS
from ua_alert_forecast.radar_text import CHANNELS, corridor_events, load_posts

CACHE = Path("/tmp/glm_review/cache")
CAP = 0.05
CORRIDOR_KM = 140.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", choices=["dev", "test"], default="dev")
    parser.add_argument("--configs", nargs="+", default=["k1_base", "k1_kyiv"])
    parser.add_argument("--horizons", nargs="+", default=["15m", "30m", "1h"])
    parser.add_argument("--thresholds", nargs="+", type=float, default=[0.2, 0.3, 0.5])
    parser.add_argument("--cap", type=float, default=CAP)
    args = parser.parse_args()

    events = load_events(RAW_DIR / "UkraineAlarmSignal.jsonl")
    posts = load_posts(RAW_DIR, CHANNELS)
    co = corridor_events(posts)
    ko_int = alert_intervals(events[events.oblast == "kyivska"])["kyivska"]
    nb = NEIGHBORS["kyiv"]
    sirens_raw = np.sort(events.loc[(events.oblast == "kyiv") & (events.kind == "start"), "ts"]
                         .to_numpy(dtype="datetime64[ns]").astype(np.int64))
    sirens = bucket(sirens_raw)

    rows = []
    for name in args.configs:
        for h in args.horizons:
            blob = np.load(CACHE / f"preds_{args.window}_{name}_{h}.npz")
            p, y, tsv = blob["p"], blob["y"], blob["tsv"].astype(np.int64)
            h_ns = int(HORIZONS[h].value)
            siren_set = np.sort(sirens[(sirens >= tsv[0]) & (sirens < tsv[-1] + h_ns)])
            ts = pd.DatetimeIndex(tsv)
            ko_clear = ~is_active(ko_int, tsv)
            nb_start_times = np.sort(events.loc[(events.kind == "start") & (events.oblast.isin(nb)), "ts"]
                                     .to_numpy(dtype="datetime64[ns]").astype(np.int64))
            quiet_nb = count_before(nb_start_times, tsv, pd.Timedelta(hours=2)) == 0
            near = co.ts.to_numpy(np.int64)[co.dist.to_numpy(float) <= CORRIDOR_KM]
            quiet_cor = count_before(near, tsv, pd.Timedelta(minutes=60)) == 0
            arms = {"none": np.ones(len(tsv), bool), "ko": ko_clear, "quiet": ko_clear & quiet_nb & quiet_cor}
            for arm, mask in arms.items():
                p2 = np.where(mask, np.minimum(p, args.cap), p)
                sw = event_report(p2, tsv, y, siren_set, h_ns, tuple(args.thresholds), 5 * 6e10, 7 * (3 if args.window == "dev" else 1))
                rows.append(pd.DataFrame({"config": name, "horizon": h, "guard": arm, **sw}))
            print(name, h, "guarded share:", float((arms["quiet"]).mean()), flush=True)
    text = [
        f"# Kyiv quiet-state guard, {args.window} window",
        "",
        f"Cap = {args.cap} where the guard state holds (applied at forecast time). Guard arms:",
        "none (model as-is), ko (Kyiv oblast fully clear), quiet (ko clear + no neighbor start in 2h + no corridor",
        "mention within 140 km in the last 60m). Sirens = city starts on the 5-minute grid.",
        "",
        pd.concat(rows).round(3).to_markdown(index=False),
    ]
    (Path("reports") / f"kyiv_guard_{args.window}.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    main()
