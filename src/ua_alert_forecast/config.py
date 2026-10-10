"""Shared paths and channel lists."""

from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

# Training history starts here: covers last winter's tactics as well as the late-August 2026 shift.
HISTORY_START = datetime(2025, 12, 1, tzinfo=UTC)

# Threat-tracking channels: model inputs.
RADAR_CHANNELS = ["kpszsu", "deraketaua", "war_monitor"]
# Alert start/end channels: labels. @air_alert_ua (official) went silent 2026-09-07;
# @UkraineAlarmSignal (volunteer-run) is live and is cross-checked against it on the overlap.
ALERT_CHANNELS = ["air_alert_ua", "UkraineAlarmSignal"]
