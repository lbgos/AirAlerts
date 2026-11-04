"""Walk-forward backtest of one model config over several test windows on one cached feature table.

A single 14-day test window is noisy: neighbouring forecasts are nearly identical, so a few
attacks decide the score. This runs the same config on several windows spaced two weeks apart
and reports the mean. Each window trains on everything before it, calibrates on the days before
the test and scores only the test window, exactly like `forecast train`, so no label crosses a
window boundary.

    uv run python scripts/backtest.py --config f1s_recent_cons --horizons 15m,1h,6h \
        --windows 2026-09-07,2026-09-21,2026-10-05,2026-10-19 --jobs 4 --json data/backtests/base.json

--extra points at a module with `add_features(table, events) -> table`; its columns land in the
"extra" feature group, so `--groups "...",extra` switches them on. That keeps research features
out of `dataset.py` until they earn their place.
"""

import argparse
import dataclasses
import importlib.util
import json
import multiprocessing as mp
from pathlib import Path

import pandas as pd

from ua_alert_forecast.config import HISTORY_START, RAW_DIR, ROOT
from ua_alert_forecast.dataset import build_table, load_events
from ua_alert_forecast.experiments import BY_NAME
from ua_alert_forecast.model import Config, Split, climatology, fit, label, scores

DATA = ROOT / "data"
LABEL_CHANNEL = "UkraineAlarmSignal"


def load_table(step_minutes: int, extra: str | None) -> pd.DataFrame:
    """Cached feature table. The base table is built once per grid step; a plugin's columns are cached next to it."""
    cache = DATA / f"table_{step_minutes}m.parquet"
    if not cache.exists():
        events = load_events(RAW_DIR / f"{LABEL_CHANNEL}.jsonl")
        start = max(events["ts"].min(), pd.Timestamp(HISTORY_START)) + pd.Timedelta(hours=24)
        table = build_table(events, start, events["ts"].max(), keep_active=True, step=pd.Timedelta(minutes=step_minutes))
        table.to_parquet(cache, index=False)
    table = pd.read_parquet(cache)
    if extra:
        name = Path(extra).stem
        cache = DATA / f"table_{step_minutes}m_{name}.parquet"
        if cache.exists():
            return pd.read_parquet(cache)
        spec = importlib.util.spec_from_file_location(name, extra)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        table = module.add_features(table, load_events(RAW_DIR / f"{LABEL_CHANNEL}.jsonl"))
        table.to_parquet(cache, index=False)
    return table


def run_one(job: tuple[str, str, str]) -> tuple[dict, pd.DataFrame]:
    """One (window end, horizon) fit and score. Runs in a worker process."""
    window, horizon, config = job
    table, cfg = _TABLE, _CONFIGS[config]
    split = Split.ending(pd.Timestamp(window, tz="UTC"), _TEST_DAYS, cfg.calib_days)
    model = fit(table, horizon, split, cfg)
    parts = split.periods(table, horizon, cfg.target)
    col = label(cfg.target, horizon)
    test = parts["test"]
    y = test[col].to_numpy()
    p = model.predict(test)
    clim = climatology(parts["train"], test, col)
    row = {"config": cfg.name, "window": window, "horizon": horizon, "n": len(test), "positive_rate": float(y.mean()),
           **scores(y, p, clim)}
    row["clim_brier"] = scores(y, clim)["brier"]
    row["skill_vs_clim"] = 1 - row["brier"] / row["clim_brier"]
    row["preds"] = pd.DataFrame({"window": window, "horizon": horizon, "ts": test["ts"].to_numpy(),
                                 "region": test["region"].astype(str).to_numpy(), "y": y, "p": p})
    return row, row.pop("preds")


_TABLE: pd.DataFrame | None = None
_CONFIGS: dict[str, Config] = {}
_TEST_DAYS = 14


def main() -> None:
    global _TABLE, _CONFIGS, _TEST_DAYS
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="f1s_recent_cons", help="name from experiments.CONFIGS")
    p.add_argument("--override", default="{}", help="JSON of Config fields to replace, e.g. '{\"half_life_days\": 30}'")
    p.add_argument("--extra", default=None, help="module with add_features(table, events)")
    p.add_argument("--step", type=int, default=15, help="feature-table grid in minutes")
    p.add_argument("--horizons", default="15m,1h,3h,6h")
    p.add_argument("--windows", default="2026-09-07,2026-09-21,2026-10-05,2026-10-19", help="test-window end dates")
    p.add_argument("--test-days", type=int, default=14)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--seeds", type=int, default=0, help="average this many LightGBM seeds (0 = config as is)")
    p.add_argument("--json", default=None, help="write per-window metrics here")
    args = p.parse_args()

    base = BY_NAME[args.config]
    overrides = json.loads(args.override)
    if "groups" in overrides:
        overrides["groups"] = tuple(overrides["groups"])
    cfg = dataclasses.replace(base, **overrides)
    if cfg.name == base.name and overrides:
        cfg = dataclasses.replace(cfg, name=base.name + "_" + Path(args.extra or "x").stem)
    if args.seeds > 1:
        members = tuple(dataclasses.replace(cfg, name=f"{cfg.name}_s{i}", lgbm={**cfg.lgbm, "random_state": i})
                        for i in range(args.seeds))
        cfg = dataclasses.replace(cfg, name=f"{cfg.name}_bag{args.seeds}", members=members)

    _TABLE = load_table(args.step, args.extra)
    _CONFIGS = {cfg.name: cfg}
    _TEST_DAYS = args.test_days
    windows = args.windows.split(",")
    horizons = [h for h in args.horizons.split(",") if h]
    jobs = [(w, h, cfg.name) for w in windows for h in horizons]
    slug = Path(args.json).stem if args.json else f"{cfg.name}_{args.step}m"
    outdir = DATA / "backtests" / slug
    outdir.mkdir(parents=True, exist_ok=True)
    meta = outdir / "jobs.jsonl"
    signature = {"config": dataclasses.asdict(cfg), "step": args.step, "test_days": args.test_days}
    sig_path = outdir / "meta.json"
    if sig_path.exists() and json.loads(sig_path.read_text()) != json.loads(json.dumps(signature)):
        raise SystemExit(f"{outdir} holds a different config; pass a new --json name")
    sig_path.write_text(json.dumps(signature, indent=1))

    done = {f"{w}_{h}" for w, h, _ in jobs if (outdir / f"{w}_{h}.parquet").exists()}
    todo = [j for j in jobs if f"{j[0]}_{j[1]}" not in done]
    if done:
        print(f"resume: {len(done)} jobs cached, {len(todo)} to run", flush=True)

    def keep(row: dict, preds: pd.DataFrame) -> None:
        preds.to_parquet(outdir / f"{row['window']}_{row['horizon']}.parquet", index=False)
        with meta.open("a") as f:
            f.write(json.dumps(row) + "\n")

    if args.jobs > 1:
        with mp.get_context("fork").Pool(args.jobs) as pool:
            for row, preds in pool.imap_unordered(run_one, todo):
                keep(row, preds)
                print(f"  {row['window']} {row['horizon']:>3s} n={row['n']:<6d} brier={row['brier']:.4f} "
                      f"skill={row['skill_vs_clim']:.3f}", flush=True)
    else:
        for job in todo:
            row, preds = run_one(job)
            keep(row, preds)
            print(f"  {row['window']} {row['horizon']:>3s} n={row['n']:<6d} brier={row['brier']:.4f} "
                  f"skill={row['skill_vs_clim']:.3f}", flush=True)

    # Rows from every run of this slug, newest wins, in the order the jobs were requested.
    latest = {}
    for line in meta.read_text().splitlines():
        r = json.loads(line)
        latest[(r["window"], r["horizon"])] = r
    res = pd.DataFrame([latest[(w, h)] for w, h, _ in jobs])
    preds = pd.concat([pd.read_parquet(outdir / f"{w}_{h}.parquet") for w, h, _ in jobs], ignore_index=True)

    per_h = res.groupby("horizon", sort=False).agg(
        n=("n", "sum"), positive_rate=("positive_rate", "mean"), brier=("brier", "mean"),
        skill=("skill_vs_clim", "mean"), ece=("ece", "mean"), auc=("auc", "mean"),
        conf_wrong=("conf_wrong", "mean"), conf_promised=("conf_promised", "mean"), points=("points", "mean"),
    )
    print(f"\n{cfg.name}  step={args.step}m windows={args.windows}")
    print(per_h.round(4).to_string())
    print(f"\nmean skill {per_h['skill'].mean():.4f}   mean ece {per_h['ece'].mean():.4f}   "
          f"mean points {per_h['points'].mean():.2f}   mean conf_wrong {per_h['conf_wrong'].mean():.4f}")
    rows = res.to_dict("records")
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"config": dataclasses.asdict(cfg), "step": args.step, "windows": windows,
                                   "horizons": horizons, "summary": per_h.reset_index().to_dict("records"), "rows": rows}, indent=1))
    pred_path = Path(args.json).with_suffix(".preds.parquet") if args.json else DATA / f"backtests/preds_{cfg.name}_{args.step}m.parquet"
    pred_path.parent.mkdir(parents=True, exist_ok=True)
    preds.to_parquet(pred_path, index=False)
    print(f"preds -> {pred_path}")
    print(res[["window", "horizon", "n", "positive_rate", "brier", "clim_brier", "skill_vs_clim", "ece", "auc"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
