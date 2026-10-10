"""How often the forecast was right (>= 50% vs what happened) on the final-test window, all oblasts and Kyiv.

Uses the saved final-test models (data/models.pkl, data/models_clear.pkl) and the same 14-day test window as
reports/metrics.md and reports/metrics_clear.md. Writes reports/accuracy.md.
"""

import pickle
import re

import pandas as pd

from ua_alert_forecast.dataset import HORIZONS
from ua_alert_forecast.model import Split
from ua_alert_forecast.train import MODELS_PATH, REPORT_DIR, load_table

GROUPS = {"all oblasts": None, "Kyiv city": ["kyiv"], "Kyiv oblast": ["kyivska"]}


def test_end(report: str) -> pd.Timestamp:
    first = (REPORT_DIR / report).read_text()
    return pd.Timestamp(re.search(r"Data until (\S+ \S+) UTC", first).group(1), tz="UTC")


table = load_table(with_radar=False)
rows = []
for kind, path, report in [("siren", MODELS_PATH, "metrics.md"), ("all-clear", MODELS_PATH.with_stem("models_clear"), "metrics_clear.md")]:
    bundle = pickle.loads(path.read_bytes())
    config, models = bundle["config"], bundle["models"]
    split = Split.ending(test_end(report), 14, config.calib_days)
    for name, regions in GROUPS.items():
        row = {"": f"{kind}, {name}"}
        for h in HORIZONS:
            test = split.periods(table, h, config.target)["test"]
            if regions:
                test = test[test["region"].isin(regions)]
            y = test[f"y_{h}" if config.target == "start" else f"yc_{h}"].to_numpy()
            p = models[h].predict(test)
            row[h] = f"{((p >= 0.5) == (y == 1)).mean():.0%}"
        rows.append(row)
out = ["# How often the forecast was right (final-test window, last 14 days)", "",
       "Right = said 50% or more and it happened, or under 50% and it did not.", "",
       pd.DataFrame(rows).to_markdown(index=False), ""]
(REPORT_DIR / "accuracy.md").write_text("\n".join(out))
print("\n".join(out))
