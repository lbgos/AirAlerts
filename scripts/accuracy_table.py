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


tables = {}
rows, detail = [], []
for kind, path, report in [("siren", MODELS_PATH, "metrics.md"), ("all-clear", MODELS_PATH.with_stem("models_clear"), "metrics_clear.md")]:
    bundle = pickle.loads(path.read_bytes())
    config, models = bundle["config"], bundle["models"]
    split = Split.ending(test_end(report), 14, config.calib_days)
    step = config.step_minutes
    table = tables.setdefault(step, load_table(with_radar=False, step=pd.Timedelta(minutes=step)))
    for name, regions in GROUPS.items():
        row = {"": f"{kind}, {name}"}
        for h in HORIZONS:
            test = split.periods(table, h, config.target)["test"]
            if regions:
                test = test[test["region"].isin(regions)]
            y = test[f"y_{h}" if config.target == "start" else f"yc_{h}"].to_numpy()
            p = models[h].predict(test)
            row[h] = f"{((p >= 0.5) == (y == 1)).mean():.0%}"
            if h == "15m":
                said = p >= 0.3
                detail.append({"": f"{kind}, {name}", "it happened": f"{y.mean():.0%}",
                               "said 30%+: came true": f"{y[said].mean():.0%}" if said.any() else "-",
                               "caught at 30%+": f"{said[y == 1].mean():.0%}",
                               "said under 10%: came true": f"{y[p < 0.1].mean():.0%}" if (p < 0.1).any() else "-"})
        rows.append(row)
out = ["# How often the forecast was right (final-test window, last 14 days)", "",
       "Right = said 50% or more and it happened, or under 50% and it did not.", "",
       pd.DataFrame(rows).to_markdown(index=False), "",
       "## 15 minutes in detail", "",
       "it happened: share of 15-minute windows with a siren (all-clear). caught: share of those that had a 30%+ forecast.", "",
       pd.DataFrame(detail).to_markdown(index=False), ""]
(REPORT_DIR / "accuracy.md").write_text("\n".join(out))
print("\n".join(out))
