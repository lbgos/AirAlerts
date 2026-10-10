"""`forecast experiments`: compare model variants on a development window, before touching the final test.

The dev window is the 14 days before the final test window. Variants are ranked by mean Brier skill
over climatology across horizons (ties: lower calibration error); the rule was fixed before running.
Only the winner is then evaluated on the final test by `forecast train --config <name>`.
"""

import pandas as pd

from .geo import FRONTLINE
from .model import Config, evaluate
from .train import REPORT_DIR, load_table

FULL = ("time", "history", "threats", "neighbors", "national")
SMALL = {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 15}
DEFAULT = {"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31}
BIG = {"n_estimators": 600, "learning_rate": 0.03, "num_leaves": 63}

CONFIGS = [
    # Which inputs matter
    Config("feat_time", groups=("time",)),
    Config("feat_+history", groups=("time", "history")),
    Config("feat_+threats", groups=("time", "history", "threats")),
    Config("feat_full", groups=FULL),
    # Which calibration
    Config("cal_none", calibration="none"),
    Config("cal_isotonic_7d", calibration="isotonic", calib_days=7),
    Config("cal_isotonic_21d", calibration="isotonic", calib_days=21),
    Config("cal_platt_7d", calibration="platt", calib_days=7),
    # Model size and family (feat_full above is the default size with Platt 21d)
    Config("lgbm_small", lgbm=SMALL),
    Config("lgbm_big", lgbm=BIG),
    Config("logreg", family="logreg"),
    # Combinations: average of calibrated outputs
    Config("ens_lgbm_3sizes", members=(Config("s", lgbm=SMALL), Config("d"), Config("b", lgbm=BIG))),
    Config("ens_lgbm_logreg", members=(Config("d"), Config("l", family="logreg"))),
    # Round 2, added after round 1: combine the best calibration (Platt 7d) with the best size (small)
    Config("r2_small_platt7d", lgbm=SMALL, calib_days=7),
    Config("r2_ens3_platt7d", calib_days=7, members=(Config("s", lgbm=SMALL, calib_days=7), Config("d", calib_days=7), Config("b", lgbm=BIG, calib_days=7))),
    # Round 3: radar channels via the local student classifier, on top of the round-2 winner
    Config("r3_small_platt7d_radar", groups=FULL + ("radar",), lgbm=SMALL, calib_days=7),
    # Round 4 (user question: does radar carry signal on its own, or does it duplicate the alert channel?)
    Config("r4_time_radar", groups=("time", "radar"), lgbm=SMALL, calib_days=7),
    Config("r4_time_history_radar", groups=("time", "history", "radar"), lgbm=SMALL, calib_days=7),
    Config("r4_time_history_threats", groups=("time", "history", "threats"), lgbm=SMALL, calib_days=7),
    Config("r4_time_history_threats_radar", groups=("time", "history", "threats", "radar"), lgbm=SMALL, calib_days=7),
    # Round 5 (user question: do neighbors help on their own?)
    Config("r5_no_national", groups=("time", "history", "threats", "neighbors"), lgbm=SMALL, calib_days=7),
    Config("r5_no_neighbors", groups=("time", "history", "threats", "national"), lgbm=SMALL, calib_days=7),
    # Round 6: radar v2 (now_in vs heading_to, count-weighted). Rounds 3-4 above were run with v1 radar features;
    # the "radar" group now holds v2 features, so rerunning them measures v2.
    Config("r6_full_radar2", groups=FULL + ("radar",), lgbm=SMALL, calib_days=7),
    Config("r6_time_history_radar2", groups=("time", "history", "radar"), lgbm=SMALL, calib_days=7),
    # Round 7: student finds oblasts with one head and picks each one's role with two more; adds national radar
    # counts that include posts naming no oblast (launches, take-offs). Same groups as round 6.
    Config("r7_full_radar", groups=FULL + ("radar",), lgbm=SMALL, calib_days=7),
    Config("r7_time_history_radar", groups=("time", "history", "radar"), lgbm=SMALL, calib_days=7),
    # Round 8: alert-wave timing (minutes since the latest neighbor siren, second-ring neighbors) on the round-2 winner
    Config("r8_full_wave", groups=FULL + ("wave",), lgbm=SMALL, calib_days=7),
    # All-clear (rows under alert; label: the oblast's alert ends within the horizon). c1 = first round.
    Config("c1_clear_time", groups=("time", "clear"), lgbm=SMALL, calib_days=7, target="clear"),
    Config("c1_clear_full", groups=FULL + ("wave", "clear"), lgbm=SMALL, calib_days=7, target="clear"),
    Config("c1_clear_full_radar", groups=FULL + ("wave", "clear", "radar", "clear_radar"), lgbm=SMALL, calib_days=7, target="clear"),
]
BY_NAME = {c.name: c for c in CONFIGS}


def summarize(res: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per predictor: metrics averaged over horizons (ranked by the selection rule), and skill/ece per horizon."""
    summary = (
        res.groupby("predictor", sort=False)
        .agg(skill=("skill", "mean"), brier=("brier", "mean"), ece=("ece", "mean"), auc=("auc", "mean"),
             low_pred=("low_pred", "mean"), low_obs=("low_obs", "mean"), high_pred=("high_pred", "mean"),
             high_obs=("high_obs", "mean"), n_high=("n_high", "sum"))
        .sort_values(["skill", "ece"], ascending=[False, True])
    )
    per_h = res.pivot(index="predictor", columns="horizon", values=["skill", "ece"]).loc[summary.index]
    per_h.columns = [f"{m}_{h}" for m, h in per_h.columns]
    return summary, per_h


def run(only: list[str] | None = None, report: str = "experiments") -> None:
    table = load_table()
    dev_end = table["ts"].max() - pd.Timedelta(days=14)
    rows = []
    for config in [c for c in CONFIGS if not only or c.name in only]:
        _, metrics, _ = evaluate(table, dev_end, config)
        clim = metrics[metrics.predictor == "climatology"].set_index(["subset", "horizon"])["brier"]
        own = metrics[metrics.predictor == config.name].copy()
        own["skill"] = 1 - own["brier"] / pd.MultiIndex.from_frame(own[["subset", "horizon"]]).map(clim)
        rows.append(own)
        print(f"{config.name:18s} skill {own[own.subset == 'all']['skill'].mean():.3f}  rear {own[own.subset == 'rear']['skill'].mean():.3f}", flush=True)
    res = pd.concat(rows)
    text = (
        "# Experiments (dev window)\n\n"
        f"Dev test window: 14 days ending {dev_end:%Y-%m-%d %H:%M} UTC. Final test window not used here.\n\n"
        "skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.\n"
        "low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.\n"
        f"rear = all regions except {', '.join(sorted(FRONTLINE))}.\n"
    )
    for subset, title in [("all", "All regions"), ("rear", "Rear regions")]:
        summary, per_h = summarize(res[res.subset == subset])
        text += f"\n## {title}, averaged over horizons\n\n{summary.round(4).to_markdown()}\n\n## {title}, per horizon\n\n{per_h.round(4).to_markdown()}\n"
        print(f"\n{title}\n{summary.round(3).to_string()}")
    (REPORT_DIR / f"{report}.md").write_text(text)
