"""Round r1: (a) train from 2026-01-01, (b) daily walk-forward recalibration, (c) ensemble of (base, jan).
Classifier: f1s_recent_cons. Daily recalibration: for each test day d, the calibrator is refit on the k days before d
(rows whose label window ends before d), so calibration never sees the test day. Windows: dev (14 d ending 14 d before
the data end, used to pick) and final (last 14 d; already reused in earlier rounds, reported for reference only)."""

import dataclasses

import numpy as np
import pandas as pd

from ua_alert_forecast.experiments import BY_NAME
from ua_alert_forecast.model import (
    HORIZONS,
    Split,
    climatology,
    fit,
    fit_calibrator,
    label,
    scores,
)
from ua_alert_forecast.train import REPORT_DIR, load_table

base = BY_NAME["f1s_recent_cons"]
jan = dataclasses.replace(base, name="jan", train_since="2026-01-01")
table = load_table(with_radar=False, step=pd.Timedelta(minutes=5))
end = table["ts"].max()
rows = []
for wname, we in [("dev", end - pd.Timedelta(days=14)), ("final", end)]:
    split = Split.ending(we, 14, 7)
    test_start = split.calib_end
    for h in ["15m", "1h", "3h"]:
        y = label("start", h)
        parts = split.periods(table, h, "start")
        test = parts["test"]
        yt = test[y].to_numpy()
        clim = climatology(parts["train"], test, y)
        mb, mj = fit(table, h, split, base), fit(table, h, split, jan)
        preds = {"base": mb.predict(test), "jan": mj.predict(test)}
        preds["ensemble"] = (preds["base"] + preds["jan"]) / 2
        # walk-forward daily recalibration of the base classifier
        allr = table[
            (table["active"] == False)
            & table[y].notna()
            & (table["ts"] >= split.train_end - pd.Timedelta(days=7))
        ]
        raw_all = pd.Series(
            mb.classifier.predict_proba(allr[mb.features])[:, 1], index=allr.index
        )
        lab_end = allr["ts"] + HORIZONS[h]
        raw_test = raw_all.loc[test.index].to_numpy()
        for k in (1, 3, 7):
            for kind in ("conservative", "platt"):
                p = np.empty(len(test))
                day = (test["ts"] - test_start).dt.days.to_numpy()
                for d in np.unique(day):
                    d0 = test_start + pd.Timedelta(days=int(d))
                    m = (allr["ts"] >= d0 - pd.Timedelta(days=k)) & (lab_end <= d0)
                    cal = fit_calibrator(
                        kind,
                        raw_all[m].to_numpy(),
                        allr.loc[m, y].to_numpy(),
                        base.bound_z,
                    )
                    p[day == d] = cal(raw_test[day == d])
                preds[f"daily_{kind[:4]}_k{k}"] = p
        for name, p in preds.items():
            s = scores(yt, p, clim)
            rows.append({"window": wname, "horizon": h, "variant": name, **s})
            print(
                wname,
                h,
                f"{name:18s}",
                {k: round(v, 4) for k, v in s.items()},
                flush=True,
            )
pd.DataFrame(rows).to_csv(REPORT_DIR / "recal_eval.csv", index=False)
