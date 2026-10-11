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

- One row per (oblast, time T) on a 5-minute grid (live mode forecasts every 30 s).
- An oblast is under alert from its first siren until the channel's all-clear for every place in it. A 24 h expiry
  only covers lost posts (in the last 60 days 26 alerts never got an all-clear; 14% of alerts last over 3 h).
- Features use only events before T: time of day, the oblast's recent alerts and threats, neighbor oblasts
  (alerts, threats, minutes since the latest neighbor siren), second-ring neighbors, national counts, and the last
  minutes (minutes since the latest threat note / all-clear here and next door, last-10-minute counts, neighbors that
  went under alert in the last 15 min). All-clear rows add how long the alert has run and recent partial all-clears.
- Labels: a siren starts in (T, T + horizon] (oblasts not under alert); the alert ends in (T, T + horizon] (under alert).
- LightGBM per horizon, recent days weighted more (60-day half-life), calibrated on the 7 days before the test window.
- Time split train | calibrate | test, purged so no label window crosses a boundary. Model selection used a separate
  14-day dev window; the final test window (last 14 days) was run once per chosen model.

### Overconfidence

- Calibration is conservative: Platt scaling, then on the calibration days forecasts are grouped into 20 bins and no
  forecast may be more certain than the 99% Wilson bound of how often that bin came true. Few cases or past
  overconfidence pull a forecast toward 50%.
- `penalty`: log loss where confident forecasts (<= 20% or >= 80%) that turned out wrong count 10x.
- `points` (higher is better): log2 score gained over climatology per 100 forecasts; confident forecasts that were
  right count 3x, confident ones that were wrong 10x. Used to pick the 15-minute model.

## Results (final test: last 14 days, ending 2026-10-10 16:20 UTC)

Siren starts, model `f1s_recent_cons`. Brier score (lower is better) vs climatology (rate per oblast and hour of day).
"Confident wrong" is the share of forecasts at <= 20% or >= 80% that were wrong, next to the share they promised:

| horizon | model | climatology | AUC | calibration error (ECE) | confident wrong / promised |
|:--|--:|--:|--:|--:|--:|
| 15m | 0.058 | 0.069 | 0.89 | 0.018 | 2.8% / 4.4% |
| 30m | 0.090 | 0.114 | 0.88 | 0.024 | 3.0% / 3.6% |
| 1h | 0.118 | 0.164 | 0.88 | 0.025 | 5.1% / 4.6% |
| 3h | 0.127 | 0.207 | 0.90 | 0.030 | 8.9% / 6.7% |
| 6h | 0.112 | 0.200 | 0.92 | 0.037 | 7.6% / 5.9% |

All-clear, model `f1c_recent_cons` (oblasts under alert):

| horizon | model | climatology | AUC | alerts that ended | confident wrong / promised |
|:--|--:|--:|--:|--:|--:|
| 15m | 0.099 | 0.105 | 0.77 | 13% | 6.4% / 7.8% |
| 30m | 0.146 | 0.159 | 0.78 | 23% | 6.4% / 7.2% |
| 1h | 0.172 | 0.190 | 0.81 | 37% | 7.9% / 8.5% |
| 3h | 0.154 | 0.167 | 0.85 | 62% | 6.6% / 9.1% |
| 6h | 0.118 | 0.131 | 0.88 | 76% | 3.9% / 12.1% |

The 15-minute forecast: sirens start in 8% of 15-minute windows. Forecasts of 30% or more came true 42% of the time
and preceded 38% of sirens; forecasts under 10% came true 1% of the time (`reports/accuracy.md`, also Kyiv).
On the dev window only 5% of 15-minute sirens came with no threat note or siren here or next door in the previous
30 min, so the limit is telling which nearby activity turns into a siren here, not missing activity.

Previous models on the same window: `reports/metrics_p1.md` (no last-minutes features, 15-minute grid; 15m Brier
0.060, all-clear 0.102). Models before the alert-duration fix (3 h expiry): `reports/metrics_r8_3h_rule.md`,
`reports/metrics_clear_c1_3h_rule.md`.

### 15-minute round (dev window, 15m horizon)

| siren starts | skill | points |
|:--|--:|--:|
| previous features, trained on a 15-minute grid | 0.126 | 63.3 |
| + 5-minute grid | 0.125 | 63.9 |
| + last-minutes features | 0.134 | 65.0 |
| + conservative calibration (final) | 0.135 | 74.7 |

All-clear, same steps: skill 0.069 → 0.067 → 0.075 → 0.073, points −2.3 → −1.6 → −1.1 → 15.4.
`reports/experiments_f1.md`, `reports/experiments_f1_all.md` (all horizons: the final models are no worse at 30m–6h).

## What helped (siren starts, dev window, 3 h expiry labels; skill = 1 − Brier / Brier of climatology, mean of 30m–6h)

| features | skill |
|:--|--:|
| time and oblast ¹ | 0.162 |
| + own alert history ¹ | 0.217 |
| + threat notes from the alert channel | 0.239 |
| + neighbor oblasts | 0.275 |
| + national counts | 0.276 |
| + alert-wave timing | 0.278 |
| + radar channels (v1 / v2 / v2 + national) | 0.277 / 0.276 / 0.273 |

¹ Round-1 settings (300 trees, Platt on 21 days); the other rows use the final settings (200 trees, Platt on 7 days).

Calibration: Platt scaling on the last 7 days beat isotonic and longer windows; without calibration ECE doubles.
The final models add the last-minutes features and the conservative cap on top (sections above).
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
uv run forecast train --config f1s_recent_cons
uv run forecast train --config f1c_recent_cons
uv run pytest

# live mode: refit both models on all data, then poll + serve http://<host>:8790; score the log later
uv run forecast fit-live --config f1s_recent_cons --clear-config f1c_recent_cons
uv run forecast live --host 127.0.0.1 --port 8790
uv run forecast score-live
```

Live mode reads only the alert channel: the final model uses no radar features. New posts are appended to
`data/raw/UkraineAlarmSignal.jsonl`, so the next `fit-live` trains on them. It also records `@raketa_trevoga` and
`@nebo_raketa` (Kyiv-region radar) for later experiments. Yellow and red alert levels count as one air alert:
an oblast is under alert from its first siren until the all-clear.

Server: `Dockerfile` + `deploy/docker-compose.yml` (restart `unless-stopped`; `data/`, `.env` and the Telegram
session are mounted, so a redeploy keeps the collected posts and the prediction log).
