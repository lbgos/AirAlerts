# AirAlerts

Forecasts the probability that an air raid siren **starts** in a Ukrainian oblast within the next 30 min / 1 h / 3 h / 6 h.
Calibrated: a forecast of 70% should come true about 70% of the time.

Work in progress: model and evaluation are done; live mode and the web page are next.

## Data

All from public Telegram channels, scraped with Telethon (`forecast login`, `forecast scrape`), 2025-12-01 to 2026-10-09.

- `@UkraineAlarmSignal`: alert starts/ends and threat notes (drones, KABs, missiles) per place, each tagged with its oblast.
  Parsed by `alerts.py`. This is both the label source and the main feature source.
- `@kpszsu`, `@deraketaua` (radar channels): free text about drones and missiles in flight. Converted to structured events
  by a small local classifier (`radar.py`, TF-IDF + logistic regression), trained on 3,000 posts labeled once by an LLM.
  No LLM runs at forecast time.

Older datasets (2022–2024) were not used: tactics changed, and recent data matches what the model sees live.

## Method

- One row per (oblast, time T) on a 15-minute grid, only when the oblast is not already under alert.
- Features use only events before T: time of day, the oblast's recent alerts and threats, neighbor oblasts, national counts.
- Label: did a siren start in (T, T + horizon].
- LightGBM per horizon, recent days weighted more (60-day half-life), Platt calibration on the 7 days before the test window.
- Time split train | calibrate | test, purged so no label window crosses a boundary. Model selection used a separate
  14-day dev window; the final test window (last 14 days) was run once.

## Results (final test, 2026-09-25 to 2026-10-09)

Brier score (lower is better) vs climatology (siren-start rate per oblast and hour of day):

| horizon | model | climatology | AUC | calibration error (ECE) |
|:--|--:|--:|--:|--:|
| 30m | 0.092 | 0.111 | 0.86 | 0.011 |
| 1h | 0.123 | 0.159 | 0.86 | 0.023 |
| 3h | 0.133 | 0.199 | 0.89 | 0.034 |
| 6h | 0.114 | 0.187 | 0.92 | 0.031 |

Full tables, including reliability per probability bin: `reports/metrics.md`. Feature and model comparisons: `reports/experiments.md`.

## Run

```
uv sync
cp .env.example .env        # Telegram api_id / api_hash from my.telegram.org
uv run forecast login       # QR login
uv run forecast scrape
uv run forecast train --config r2_small_platt7d
uv run pytest
```
