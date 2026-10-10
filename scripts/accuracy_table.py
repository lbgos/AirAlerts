"""Plain accuracy (forecast >= 50% vs what happened) on the final-test window, all oblasts and Kyiv.

Uses the saved final-test models (data/models.pkl, data/models_clear.pkl) and the same 14-day test window as
reports/metrics.md and reports/metrics_clear.md. Baseline = always give the more common answer.
Writes reports/accuracy.md.
"""

import pickle
import re

import numpy as np
import pandas as pd

from ua_alert_forecast.dataset import HORIZONS
from ua_alert_forecast.model import Split
from ua_alert_forecast.train import MODELS_PATH, REPORT_DIR, load_table

GROUPS = {"all oblasts": None, "Kyiv city": ["kyiv"], "Kyiv oblast": ["kyivska"]}


def test_end(report: str) -> pd.Timestamp:
    first = (REPORT_DIR / report).read_text()
    return pd.Timestamp(re.search(r"Data until (\S+ \S+) UTC", first).group(1), tz="UTC")


table = load_table(with_radar=False)
out = ["# Accuracy on the final-test window (last 14 days)", "",
       "accuracy = share of forecasts on the right side of 50% (>= 50% and it happened, or < 50% and it did not).",
       "baseline = always give the more common answer (e.g. \"no siren\"), which is why plain accuracy looks high.",
       "confident = forecasts below 20% or above 80%: share of all forecasts, and how often those were right.", ""]
for title, path, report in [("Siren starts (oblast not under alert)", MODELS_PATH, "metrics.md"),
                            ("All-clear (oblast under alert)", MODELS_PATH.with_stem("models_clear"), "metrics_clear.md")]:
    bundle = pickle.loads(path.read_bytes())
    config, models = bundle["config"], bundle["models"]
    split = Split.ending(test_end(report), 14, config.calib_days)
    rows = []
    for name, regions in GROUPS.items():
        row = {"": name}
        for h in HORIZONS:
            test = split.periods(table, h, config.target)["test"]
            if regions:
                test = test[test["region"].isin(regions)]
            y = test[f"y_{h}" if config.target == "start" else f"yc_{h}"].to_numpy()
            p = models[h].predict(test)
            conf = (p < 0.2) | (p > 0.8)
            row[h] = (f"{((p >= 0.5) == (y == 1)).mean():.0%} (base {max(y.mean(), 1 - y.mean()):.0%}) · "
                      f"confident {conf.mean():.0%}, right {((p[conf] >= 0.5) == (y[conf] == 1)).mean():.0%} · n={len(y)}")
        rows.append(row)
    out += [f"## {title}", "", pd.DataFrame(rows).to_markdown(index=False), ""]
(REPORT_DIR / "accuracy.md").write_text("\n".join(out))
print("\n".join(out))
