"""`forecast train`: fit one config on all data before the final test window, evaluate on it, save models + report."""

import pickle

import pandas as pd

from .config import HISTORY_START, RAW_DIR, ROOT
from .dataset import HORIZONS, STEP, build_table, load_events
from .radar import label_history
from .model import Config, Split, evaluate, fit

MODELS_PATH = ROOT / "data" / "models.pkl"
LIVE_MODEL_PATH = ROOT / "data" / "live_model.pkl"
REPORT_DIR = ROOT / "reports"
LABEL_CHANNEL = "UkraineAlarmSignal"
RADAR_CHANNELS_USED = ["kpszsu", "deraketaua"]
RADAR_LABELS = ROOT / "labels" / "radar_v2"
# The radar student only learns from teacher labels before the dev window (which starts 28 days before the data ends).
STUDENT_DAYS_BEFORE_END = 28


def load_table(with_radar: bool = True, step: pd.Timedelta = STEP) -> pd.DataFrame:
    events = load_events(RAW_DIR / f"{LABEL_CHANNEL}.jsonl")
    end = events["ts"].max()
    radar = None
    if with_radar:
        radar = label_history(RAW_DIR, RADAR_LABELS, RADAR_CHANNELS_USED, end - pd.Timedelta(days=STUDENT_DAYS_BEFORE_END))
    # Features need up to 24h of history, so the first forecast time is a day after the data starts.
    start = max(events["ts"].min(), pd.Timestamp(HISTORY_START)) + pd.Timedelta(hours=24)
    # Rows under alert are kept (all-clear models); start models filter them out in Split.periods.
    return build_table(events, start, end, radar=radar, keep_active=True, step=step)


def train(config: Config) -> None:
    table = load_table(step=pd.Timedelta(minutes=config.step_minutes))
    test_end = table["ts"].max()
    models, metrics, rel = evaluate(table, test_end, config)
    suffix = "" if config.target == "start" else "_clear"
    MODELS_PATH.with_stem(MODELS_PATH.stem + suffix).write_bytes(pickle.dumps({"config": config, "models": models}))
    REPORT_DIR.mkdir(exist_ok=True)
    lines = [
        f"# Final test: {config.name}",
        "",
        f"Target: {'siren starts (rows not under alert)' if config.target == 'start' else 'all-clear (rows under alert)'}. "
        f"Data until {test_end:%Y-%m-%d %H:%M} UTC, {len(table):,} rows, forecast every {config.step_minutes} min. Test window: last 14 days, "
        f"calibration: {config.calib_days} days before it ({config.calibration}), training: everything earlier.",
        "",
        "Lower is better for brier, log_loss, ece; higher for auc.",
        "",
        metrics.round(4).to_markdown(index=False),
    ]
    for h, r in rel.items():
        lines += ["", f"## Reliability, {h}", "", r.round(3).to_markdown()]
    (REPORT_DIR / f"metrics{suffix}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def fit_live(config: Config, clear_config: Config) -> None:
    """Refit the start and all-clear configs on all data for live use: train on everything but the last calib_days,
    calibrate on those. The final-test models leave out the latest 14 days; tactics drift, so live uses them too.
    """
    if any(g in c.groups for c in (config, clear_config) for g in ("radar", "clear_radar")):
        raise SystemExit("live mode reads only the alert channel; pick configs without radar groups")
    table = load_table(with_radar=False, step=pd.Timedelta(minutes=min(config.step_minutes, clear_config.step_minutes)))
    end = table["ts"].max()

    def fit_all(c: Config) -> dict:
        split = Split.ending(end, test_days=0, calib_days=c.calib_days)
        return {h: fit(table, h, split, c) for h in HORIZONS}

    bundle = {"config": config, "models": fit_all(config), "clear_config": clear_config, "clear_models": fit_all(clear_config), "data_end": end}
    LIVE_MODEL_PATH.write_bytes(pickle.dumps(bundle))
    print(f"{config.name} + {clear_config.name}: fitted on data until {end:%Y-%m-%d %H:%M} UTC -> {LIVE_MODEL_PATH}")
