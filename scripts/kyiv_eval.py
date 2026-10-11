"""Kyiv city: how decisive and how right the siren forecast is, per horizon.

For each config, fit on everything before a test week (purged), calibrate on the 7 days before it, forecast Kyiv city
every 5 minutes during it (rows not under alert). `--window dev` pools the 3 weeks before the last one (used to pick
features); `--window test` is the last week, run once for the chosen configs.

Bands: below 30% ("won't happen"), 30-70% (unsure), 70% and above ("will happen"); for each, the share of forecasts in
it and how often a siren then came. Writes reports/kyiv_eval_<window>.md.
"""

import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ua_alert_forecast.dataset import HORIZONS
from ua_alert_forecast.experiments import BY_NAME
from ua_alert_forecast.model import Split, climatology, fit
from ua_alert_forecast.train import REPORT_DIR, load_table

BANDS = ((0.0, 0.3, "<30%"), (0.3, 0.7, "30-70%"), (0.7, 1.01, "70%+"))


def band_row(y: np.ndarray, p: np.ndarray, clim: np.ndarray) -> dict:
    out = {"rows": len(y), "siren rate": y.mean()}
    for lo, hi, name in BANDS:
        s = (p >= lo) & (p < hi)
        out[f"share {name}"] = s.mean()
        out[f"came true {name}"] = y[s].mean() if s.any() else np.nan
    out["brier"] = ((p - y) ** 2).mean()
    out["brier clim"] = ((clim - y) ** 2).mean()
    out["auc"] = roc_auc_score(y, p) if 0 < y.mean() < 1 else np.nan
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", choices=["dev", "test"], required=True)
    parser.add_argument("--configs", nargs="+", default=[n for n in BY_NAME if n.startswith("k1_")])
    parser.add_argument("--horizons", nargs="+", default=list(HORIZONS))
    args = parser.parse_args()

    table = load_table(with_radar=False, step=pd.Timedelta(minutes=5), with_nebo=any("nebo" in BY_NAME[c].groups for c in args.configs))
    end = table["ts"].max()
    week = pd.Timedelta(days=7)
    week_ends = [end - week - i * week for i in range(3)] if args.window == "dev" else [end]

    rows = []
    for name in args.configs:
        config = BY_NAME[name]
        for h in args.horizons:
            ys, ps, cs = [], [], []
            for we in week_ends:
                split = Split.ending(we, 7, config.calib_days)
                parts = split.periods(table, h, config.target)
                test = parts["test"][parts["test"]["region"] == "kyiv"]
                model = fit(table, h, split, config)
                ys.append(test[f"y_{h}"].to_numpy())
                ps.append(model.predict(test))
                cs.append(climatology(parts["train"], test, f"y_{h}"))
            r = band_row(np.concatenate(ys), np.concatenate(ps), np.concatenate(cs))
            rows.append({"config": name, "horizon": h, **r})
            print(f"{name:20s} {h:4s} 70%+ {r['share 70%+']:.3f} ({r['came true 70%+']:.2f})  <30% {r['share <30%']:.3f} "
                  f"({r['came true <30%']:.2f})  brier {r['brier']:.4f} clim {r['brier clim']:.4f} auc {r['auc']:.3f}", flush=True)

    df = pd.DataFrame(rows)
    span = f"{week_ends[-1] - week:%Y-%m-%d} to {week_ends[0]:%Y-%m-%d}"
    lines = [
        f"# Kyiv city siren forecast, {args.window} ({span} UTC)",
        "",
        "Forecasts every 5 minutes while Kyiv city is not under alert. share = fraction of forecasts in the band,",
        "came true = how often a siren started within the horizon after them. Brier: lower is better; brier clim is the",
        "same-hour training-period rate. auc: 0.5 = no skill, 1 = perfect ranking.",
        "",
    ]
    for h in args.horizons:
        lines += [f"## {h}", "", df[df.horizon == h].drop(columns="horizon").round(3).to_markdown(index=False), ""]
    (REPORT_DIR / f"kyiv_eval_{args.window}.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
