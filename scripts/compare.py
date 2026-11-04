"""Paired comparison of two backtests: same windows, same rows, so the only difference is the forecast.

    uv run python scripts/compare.py data/backtests/base_start.preds.parquet data/backtests/cand.preds.parquet

Brier differences are correlated across neighbouring rows, so the confidence interval comes from a
day-block bootstrap: whole days are resampled, all oblasts and horizons stay together. Negative delta
means the candidate is better.
"""

import sys

import numpy as np
import pandas as pd

KEYS = ["window", "horizon", "ts", "region"]


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def main() -> None:
    base = pd.read_parquet(sys.argv[1])
    cand = pd.read_parquet(sys.argv[2])
    df = base.merge(cand, on=KEYS, suffixes=("_base", "_cand"))
    if len(df) != len(cand):
        raise SystemExit(f"candidate rows missing from baseline: {len(cand) - len(df):,} of {len(cand):,}")
    if not (df["y_base"] == df["y_cand"]).all():
        raise SystemExit("labels differ between the two runs")
    df["day"] = df["ts"].dt.floor("D")
    df["d"] = (df["p_cand"] - df["y_base"]) ** 2 - (df["p_base"] - df["y_base"]) ** 2

    rng = np.random.default_rng(0)
    days = df["day"].unique()

    def boot(sub: pd.DataFrame) -> tuple[float, float]:
        per_day = sub.groupby("day")["d"].agg(["sum", "size"])
        idx = rng.integers(0, len(per_day), (2000, len(per_day)))
        sums, sizes = per_day["sum"].to_numpy()[idx].sum(1), per_day["size"].to_numpy()[idx].sum(1)
        deltas = sums / sizes
        return float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))

    print(f"{len(df):,} rows, {len(days)} days\n")
    rows = []
    for h, sub in df.groupby("horizon", sort=False):
        lo, hi = boot(sub)
        rows.append({"horizon": h, "n": len(sub), "brier_base": brier(sub["y_base"], sub["p_base"]),
                     "brier_cand": brier(sub["y_base"], sub["p_cand"]), "delta": brier(sub["y_base"], sub["p_cand"]) - brier(sub["y_base"], sub["p_base"]),
                     "ci_lo": lo, "ci_hi": hi, "days_better": float((sub.groupby("day")["d"].mean() < 0).mean())})
    lo, hi = boot(df)
    rows.append({"horizon": "all", "n": len(df), "brier_base": brier(df["y_base"], df["p_base"]), "brier_cand": brier(df["y_base"], df["p_cand"]),
                 "delta": brier(df["y_base"], df["p_cand"]) - brier(df["y_base"], df["p_base"]), "ci_lo": lo, "ci_hi": hi,
                 "days_better": float((df.groupby("day")["d"].mean() < 0).mean())})
    print(pd.DataFrame(rows).round(5).to_string(index=False))
    print("\ndelta < 0 and ci_hi < 0: candidate better; days_better = share of days it improved on.")


if __name__ == "__main__":
    main()
