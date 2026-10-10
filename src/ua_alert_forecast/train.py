"""`forecast train`: fit one config on all data before the final test window, evaluate on it, save models + report."""

import pickle

import pandas as pd

from .config import HISTORY_START, RAW_DIR, ROOT
from .dataset import build_table, load_events
from .radar import label_history
from .model import Config, evaluate

MODELS_PATH = ROOT / "data" / "models.pkl"
REPORT_DIR = ROOT / "reports"
LABEL_CHANNEL = "UkraineAlarmSignal"
RADAR_CHANNELS_USED = ["kpszsu", "deraketaua"]
RADAR_LABELS = ROOT / "labels" / "radar_v2"
# The radar student only learns from teacher labels before the dev window (which starts 28 days before the data ends).
STUDENT_DAYS_BEFORE_END = 28


def load_table() -> pd.DataFrame:
    events = load_events(RAW_DIR / f"{LABEL_CHANNEL}.jsonl")
    end = events["ts"].max()
    radar = label_history(RAW_DIR, RADAR_LABELS, RADAR_CHANNELS_USED, end - pd.Timedelta(days=STUDENT_DAYS_BEFORE_END))
    # Features need up to 24h of history, so the first forecast time is a day after the data starts.
    start = max(events["ts"].min(), pd.Timestamp(HISTORY_START)) + pd.Timedelta(hours=24)
    return build_table(events, start, end, radar=radar)


def train(config: Config) -> None:
    table = load_table()
    test_end = table["ts"].max()
    models, metrics, rel = evaluate(table, test_end, config)
    MODELS_PATH.write_bytes(pickle.dumps({"config": config, "models": models}))
    REPORT_DIR.mkdir(exist_ok=True)
    lines = [
        f"# Final test: {config.name}",
        "",
        f"Data until {test_end:%Y-%m-%d %H:%M} UTC, {len(table):,} rows. Test window: last 14 days, "
        f"calibration: {config.calib_days} days before it ({config.calibration}), training: everything earlier.",
        "",
        "Lower is better for brier, log_loss, ece; higher for auc.",
        "",
        metrics.round(4).to_markdown(index=False),
    ]
    for h, r in rel.items():
        lines += ["", f"## Reliability, {h}", "", r.round(3).to_markdown()]
    (REPORT_DIR / "metrics.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
