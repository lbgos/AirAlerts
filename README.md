# AirAlerts

For each Ukrainian oblast, forecasts within the next 15 min / 30 min / 1 h / 3 h / 6 h:

- not under alert: the probability that an air raid siren **starts**;
- under alert: the probability that the **all-clear** comes.

Calibrated: a forecast of 70% should come true about 70% of the time.

Live mode polls `@UkraineAlarmSignal` every 30 s, forecasts every oblast at the current time and serves a one-page UI
(Ukrainian/English, dark/light, horizon dropdown, map shaded red by siren-start probability and blue by all-clear
probability for oblasts under alert). Every poll's forecasts are logged to `data/live/predictions.jsonl`;
`forecast score-live` scores them against what happened (`reports/live_score.md`).
Map geometry: geoBoundaries UKR ADM1 (OpenStreetMap, ODbL), converted by `scripts/make_map.py`.

## Data

All from public Telegram channels, scraped with Telethon (`forecast login`, `forecast scrape`), 2025-12-01 to 2026-10-09.

- `@UkraineAlarmSignal`: alert starts/ends and threat notes (drones, KABs, missiles) per place, each tagged with its oblast.
  Parsed by `alerts.py`. This is both the label source and the main feature source.
- `@kpszsu`, `@deraketaua` (radar channels): free text about drones and missiles in flight. Converted to structured events
  (weapon, count, oblast where it is now, oblast it is heading to) by a small local classifier (`radar.py`, TF-IDF +
  logistic regression), trained on 3,000 posts labeled once by an LLM. No LLM runs at forecast time.
  Tested in three rounds and not used by the final model (see below).

Older datasets (2022–2024) were not used: tactics changed, and recent data matches what the model sees live.

## Method

- One row per (oblast, time T) on a 15-minute grid, only when the oblast is not already under alert.
- Features use only events before T: time of day, the oblast's recent alerts and threats, neighbor oblasts
  (alerts, threats, minutes since the latest neighbor siren), second-ring neighbors, national counts.
- Label: did a siren start in (T, T + horizon].
- LightGBM per horizon, recent days weighted more (60-day half-life), Platt calibration on the 7 days before the test window.
- Time split train | calibrate | test, purged so no label window crosses a boundary. Model selection used a separate
  14-day dev window; the final test window (last 14 days) was run once.

## Results (final test: last 14 days, ending 2026-10-10)

Siren starts, model `r8_full_wave`. Brier score (lower is better) vs climatology (rate per oblast and hour of day):

| horizon | model | climatology | AUC | calibration error (ECE) |
|:--|--:|--:|--:|--:|
| 15m | 0.061 | 0.070 | 0.87 | 0.006 |
| 30m | 0.093 | 0.114 | 0.86 | 0.013 |
| 1h | 0.126 | 0.165 | 0.86 | 0.025 |
| 3h | 0.135 | 0.206 | 0.89 | 0.041 |
| 6h | 0.115 | 0.194 | 0.92 | 0.041 |

Forecasts under 10% came true 2–4% of the time. The 0.8–0.9 band at 1h is overconfident (predicted 0.85, observed 0.73).
The 15m horizon was added after the other four; its labels were checked blind by an LLM on 40 cases (40/40 agree).
The rerun with 15m moved the test window half a day later than the first r8 run (live posts were appended).

All-clear, model `c1_clear_full` (rows under alert; label: the oblast's alert ends within the horizon):

| horizon | model | climatology | AUC | alerts that ended |
|:--|--:|--:|--:|--:|
| 15m | 0.126 | 0.139 | 0.72 | 17% |
| 30m | 0.185 | 0.205 | 0.72 | 31% |
| 1h | 0.207 | 0.228 | 0.74 | 51% |
| 3h | 0.095 | 0.095 | 0.78 | 88% |
| 6h | 0.022 | 0.022 | 0.85 | 98% |

All-clear is harder than siren starts: about 10% better than climatology up to 1 h, no gain at 3–6 h (almost every alert
ends within 3 h). 79–86% of alerts end with an explicit all-clear post; the rest end by the 3 h expiry rule.
Radar features gave +0.001 mean skill on the dev window (better at 15–30 min, worse at 3–6 h); not used, since live
mode would then need the radar channels and classifier.
Full tables, including reliability per probability bin and rear oblasts (all except the six front-line/border oblasts):
`reports/metrics.md`. The previous model without wave features: `reports/metrics_r2.md`.

## What helped (dev window, skill = 1 − Brier / Brier of climatology, mean of the four horizons)

| features | skill |
|:--|--:|
| time and oblast ¹ | 0.162 |
| + own alert history ¹ | 0.217 |
| + threat notes from the alert channel | 0.239 |
| + neighbor oblasts | 0.275 |
| + national counts | 0.276 |
| + alert-wave timing (final) | 0.278 |
| + radar channels (v1 / v2 / v2 + national) | 0.277 / 0.276 / 0.273 |

¹ Round-1 settings (300 trees, Platt on 21 days); the other rows use the final settings (200 trees, Platt on 7 days).

Calibration: Platt scaling on the last 7 days beat isotonic and longer windows; without calibration ECE doubles.
`reports/experiments*.md` has every round.

Radar channels carry real signal (alone they beat the alert channel's threat notes, 0.249 vs 0.239) but add nothing on top of
neighbor sirens: in the last 28 days a neighbor siren preceded 94% of siren episodes, radar posts 53%, and radar was the only
early warning in 0.6%. Separating "is there" from "is heading there" and adding counts (v2) did not change that.

## Run

```
uv sync
cp .env.example .env        # Telegram api_id / api_hash from my.telegram.org
uv run forecast login       # QR login
uv run forecast scrape
uv run forecast train --config r8_full_wave
uv run pytest

# live mode: refit both models on all data, then poll + serve http://<host>:8790; score the log later
uv run forecast fit-live --config r8_full_wave --clear-config c1_clear_full
uv run forecast live --host 127.0.0.1 --port 8790
uv run forecast score-live
```

Live mode reads only the alert channel: the final model uses no radar features. New posts are appended to
`data/raw/UkraineAlarmSignal.jsonl`, so the next `fit-live` trains on them.
