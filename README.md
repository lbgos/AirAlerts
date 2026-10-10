# AirAlerts

Forecasts the probability that an air raid siren **starts** in a Ukrainian oblast within the next 30 min / 1 h / 3 h / 6 h.
Calibrated: a forecast of 70% should come true about 70% of the time.

Work in progress: model and evaluation are done; live mode and the web page are next.

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

## Results (final test, 2026-09-25 to 2026-10-09)

Model `r8_full_wave`. Brier score (lower is better) vs climatology (siren-start rate per oblast and hour of day):

| horizon | model | climatology | AUC | calibration error (ECE) |
|:--|--:|--:|--:|--:|
| 30m | 0.091 | 0.111 | 0.86 | 0.008 |
| 1h | 0.122 | 0.159 | 0.86 | 0.023 |
| 3h | 0.133 | 0.199 | 0.89 | 0.036 |
| 6h | 0.114 | 0.187 | 0.92 | 0.033 |

Forecasts under 10% came true 2–4% of the time. The 0.8–0.9 band at 1h is overconfident (predicted 0.85, observed 0.76).
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
```
