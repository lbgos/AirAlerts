# AirAlerts

For each Ukrainian oblast, forecasts within the next 15 min / 30 min / 1 h / 3 h / 6 h:

- not under alert: the probability that an air raid siren **starts**;
- under alert: the probability that the **all-clear** comes.

Calibrated: a forecast of 70% should come true about 70% of the time.

Live: **https://alerts.lbgos.dev**

In short: the forecast is reliable about calm and about rising risk, and says so when it is unsure. On the final test
(last 14 days), 15-minute forecasts under 10% were followed by a siren 1% of the time, and forecasts of 30% or more came
true 42% of the time. The high AUC (0.88–0.92, all oblasts) comes mostly from telling calm hours from active ones. A
confident "siren in the next 15 minutes" is out of reach with public data: in Kyiv city, when nothing is happening
nearby, a siren follows about 1 time in 100, and in the most dangerous state found about 1 in 4
([Where it ends](#looking-for-more-signal-research-round)). Over 20 more public sources, from radar channels to Rassvet
satellite passes, were tested and did not change this.

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

### Kyiv and @nebo_raketa

`@nebo_raketa` follows drones over Kyiv city and oblast in short posts; `nebo.py` turns them into keyword groups
(new drone, Kyiv city named, diving, missile, clear) counted over the last 10/30 min for the two Kyiv regions. Posts
edited more than a minute after publishing count from the edit time (the scrape keeps only the final text).
Kyiv city, last week (`scripts/kyiv_week.py`, `reports/kyiv_week_test.md`; features fixed on the week before):

| 15-minute siren forecast | sirens | caught at 50%+ | false alarms at 50%+ | caught at 30%+ | false alarms at 30%+ | Brier (climatology 0.094) |
|:--|--:|--:|--:|--:|--:|--:|
| alert channel only (live) | 45 | 6 | 5 | 26 | 42 | 0.087 |
| + @nebo_raketa | 45 | 15 | 24 | 29 | 58 | 0.095 |

The channel adds little on top of the alert channel: when Kyiv oblast is already under alert, a city siren follows
within 15 min 26% of the time after a "new drone" post vs 18% without one. Live mode keeps the alert-channel model.

### Kyiv geography round (k1)

Goal: forecasts that are usually decisive, 70%+ and right or under 30% and nothing happens. The alert channel names
the raion of every siren and the town of every threat ("🛸 Бровари"), which the general features collapse to the
oblast. Group `kyiv` (`kyiv.py`) keeps them for Kyiv city: which of the seven Kyiv-oblast raions are under alert and
since when, how far from Kyiv the threats named in the last 10/30/60 min are (about 80 towns with coordinates), how
many within 30/60 km, and whether the nearest one comes closer. Group `regime` flags rows after the 2026-09-06 switch
to yellow/red levels. Kyiv city, 3 dev weeks pooled (`scripts/kyiv_eval.py`, `reports/kyiv_eval_dev.md`), Platt:

| 15-minute horizon | forecasts 70%+ (came true) | forecasts under 30% (came true) | Brier (climatology 0.111) | AUC |
|:--|--:|--:|--:|--:|
| alert channel (k1_base) | 0.1% (50%) | 87% (7%) | 0.0872 | 0.812 |
| + Kyiv geography | 0.1% (67%) | 86% (7%) | 0.0870 | 0.819 |
| + geography, Kyiv city rows only | 0.1% | 94% (9%) | 0.0864 | 0.822 |
| + geography + @nebo_raketa | 0.3% (60%) | 88% (8%) | 0.0868 | 0.816 |

The geography barely moves the 15-minute forecast and does not help at 1 h–6 h. Since June, a city siren follows
a Kyiv-oblast raion siren within 15 min only 22% of the time (within 1 h 41%), and 27% of city sirens come less than
5 min after the latest raion siren, so raions add little to "neighbors under alert". The
forecast is decisive one way: under 30% (most of the time) a siren follows 7–9% of the time. 70%+ forecasts appear
at 3 h (54%, came true 86%) and 6 h (76%, came true 91%), not at 15–60 min.

Those long horizons are mostly the base rate: a Kyiv siren comes within 6 h 86% of the time. A rule "how often was
there a siren at this hour on the last 7 days" is right 86% of the time when it says yes at 6 h (model: 91%), 74% at
3 h (model: 86%), and is no better than chance at 1 h (AUC 0.53, model 0.71). The model reads the current situation,
but the 6 h number tells a user little.

### Looking for more signal (research round)

After k1 the question was whether any public source can do better. Each idea was measured against Kyiv city sirens,
leakage-free, by agents working from the same data (scratch scripts outside the repo):

| idea | result |
|:--|:--|
| radar-channel positions as distance to Kyiv (kpszsu, deraketaua, nebo) | a drone named within 20 km while the oblast is alerted: city siren within 15 min 29% of the time; 44% of city sirens have under 10 min of any notice |
| early launch reports (war_monitor launch/take-off posts) | precede 18% of city sirens 30 min–6 h ahead; random times: 19% |
| bomber / MiG-31K take-off posts | real lead (median ~1 h) but 6–10% of city sirens at most; no model gain |
| Rassvet LEO satellite passes (all 31 active, CelesTrak elements, two planes launched 2026-03-23 and 07-19) | no effect: pass windows drift through all 24 h, so time of day can be separated; Kyiv and national siren starts, wave onsets and before/after-launch rates match the same-hour baseline (national: rate ratios 0.95–1.00, all CIs include 1; the few p < 0.05 hits among ~100 uncorrected tests point both ways); pass windows hold 4% of time and 4% of sirens; no forecast gain at equal alarm time |
| weather, moon, day of week, strike cadence | no usable effect (massive nights come about every 4–5 days, close to random) |
| two-stage model (wave, then siren within it), town-level radar tracks, event order features | no gain at equal alarm time (below) |
| GPS jamming maps, internet outages (IODA), Russian airport closures, NOTAMs | null or wrong direction (outages precede 4.7% of sirens, chance 5%) |
| 10 more public monitor channels (t.me/s previews, last 1–2 weeks) | each adds coverage only by adding alarm time (below) |

**Scoring trap.** Event scores ("sirens with a warning before them") reward a warning that is always on. Two results
looked like breakthroughs until the share of time the warning was on was checked: a two-stage model caught every
siren of the last week with an hour's notice, but at that threshold it was on 98% of the time; nebo_raketa plus six
more monitor channels "caught" 93% of sirens, with a post in the last hour 92% of the calm time (nebo alone: 70%
caught, 62% of the time on). With the warning on for the same 30% of the time, both models flag the same share of the forecasts that a siren
followed (15 min: 57% two-stage vs 59% k1; 1 h: 42% vs 43%). Any recall number needs the alarm time next to it.

**Where it ends.** About half the time nothing is happening near Kyiv, and then a siren within 15 min follows about
1 time in 100. In the most dangerous state found (Kyiv oblast alerted in the last 10 min), it is about 1 in 4. Drones
near Kyiv often turn away or are shot down, and ballistic missiles fly about 4 minutes, so public data cannot carry a
confident "siren in the next 15 minutes". What the forecast can say reliably is "calm" and "something is building".

The last week (2026-10-04 to 10-11) was used as the final test for several rounds, so it is no longer unseen data.
The two-stage experiments are on the unmerged branch `glm-rethink`.

### Training start and daily recalibration (round r1)

Three ideas on the final model (`f1s_recent_cons`), picked on the dev window (14 days before the final test). Daily
recalibration refits the calibrator before each test day on the 1, 3 or 7 days before it, so it never sees the test day
(alternating calibration and test days would leak: one night's attack spans both days).

| siren starts, dev window | 15m Brier | 15m ECE | 15m points | 1h Brier | 1h ECE | 1h points |
|:--|--:|--:|--:|--:|--:|--:|
| final model (calibrated once on 7 days) | 0.0577 | 0.010 | 70.7 | 0.1121 | 0.033 | 49.3 |
| train from 2026-01-01 (drop December) | 0.0577 | 0.010 | 67.8 | 0.1122 | 0.033 | 48.2 |
| average of the two models | 0.0577 | 0.010 | 69.0 | 0.1121 | 0.033 | 48.7 |
| daily Platt, previous 3 days | 0.0576 | 0.005 | 57.8 | 0.1090 | 0.010 | 44.8 |
| daily Platt, previous 7 days | 0.0576 | 0.006 | 59.5 | 0.1091 | 0.013 | 47.4 |
| daily conservative cap, previous 1 day | 0.0613 | 0.051 | 29.5 | 0.1157 | 0.052 | 39.5 |

Dropping December changes nothing (with a 60-day half-life it already weighs little), so averaging the two adds nothing. Training only from 2026-06-01 does not change it either: Brier within 1% of the final model at 15m–3h on both windows, 6h 3% better on dev and 1% worse on the final window.
Daily Platt makes percentages more honest (calibration error 2–3x lower, Brier 3% lower at 1 h, the same ranking) but
drops the conservative cap, so more confident forecasts are wrong: on the final window at 1 h, 5.8% of confident
forecasts were wrong against 4.6% promised. The cap needs more than one day of cases. The live model is unchanged.
Script: `scripts/recal_eval.py`.

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
`deploy/airalerts-refit.timer` refits the live model every day at 05:00 Kyiv time (train on all data but the last 7
days, calibrate on those); live mode picks up the new model without a restart. On the last 3 days of data, a model
calibrated on the 7 days right before them beat one 21 days older at 1 h (Brier 0.148 vs 0.152) and 3 h (0.133 vs
0.145), and was confidently wrong less often; at 15 min they were equal.
The page also has a model toggle: "untested" is fitted on all data up to the last post, with no calibration hold-out
(raw LightGBM probabilities) and no test; the page says so. The refit container peaks at about 5.3 GB.
