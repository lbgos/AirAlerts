# Kyiv rethink: event-based evaluation, two-stage wave, text-channel features (branch glm-rethink)

What changed and why, per idea, with the dev numbers that decided each. Full tables:
`kyiv_events_dev.md`, `kyiv_events_test.md`, `kyiv_eval_dev.md` (pre-event baseline), `kyiv_guard_dev.md`.
Dev = 3 weeks ending 2026-10-04 07:55 UTC (the last 7 days never used while choosing); the final test week
2026-10-04 → 2026-10-11 was run once per chosen config at the end.

## New scoring (scripts/kyiv_events.py, src/ua_alert_forecast/events.py)

Per-row Brier/AUC replaced by event metrics: per threshold — caught sirens (a forecast ≥ threshold in the
horizon before it), median lead alarm-stretch precision and false alarms per night; plus the website's
four-state view (No <5% / Probably no 5-30% / Probably yes 30-70% / Yes 70%+ with per-band hit rates).
Metrics in `events.py` unit-tested (`tests/test_events.py`); the script reloads per-config pooled forecasts
so re-renders don't refit.

Dev baseline (pooled, at threshold 0.3): k1_kyiv 15m recall 0.564, 5.6 FA/night, precision 0.435, 70%+ band
basically never fires (0.1% of forecasts). So: over half of city sirens are missed at the 30% threshold and
every confident "yes" is unsupported — the gap the experiments below attacked.

## Idea 1-2: two-stage wave model — KEEP (winner at 30m and 1h)

`model.py`: `stage="wave2"` — gate P(city siren within 3h) fit on the usual features, times the intra-wave
hazard P(siren in h | coming wave) fit only on rows where the gate label is 1 (exact decomposition because a
siren within h is a siren within 3h). Gate/hazard splits purge by the 3h label window.

Dev, threshold 0.3 (recall / FA per night / precision):

|        | k1_base      | k2_base (wave2) | k1_kyiv | k2_kyiv |
|--------|--------------|-----------------|---------|---------|
| 30m    | .845 / 5.9   | **.865 / 6.3**  | .813    | .813    |
| 1h     | .968 / 4.0   | **1.000 / 3.5** | .968    | .968    |
| 15m    | .583 / 5.8   | .564 / 5.4      | .564    | .436 (worse — hazard stage too flat) |

Final test week (once):

|   | 15m @0.3 | 30m @0.2 | 1h @0.2 | 1h @0.1 |
|---|----------|----------|---------|---------|
| k1_kyiv | .543, 6.3 FA/n | .891, 9.6 | .978, 4.9 | .978, 2.0 |
| k2_base | .391, 6.7 | **.913, 7.3** | **.978, 3.3 (prec .66)** | **1.000, 0.7 FA/n (prec .90)** |

Verdict: keep k2_base for 30m and 1h, k1_kyiv for 15m. On the last week the two-stage model caught **every**
city siren at the 10% threshold with 0.7 false-alarm stretches per night over a week (vs 2.0 for the old
model). k2_base uses only alert-channel features — deployable with the live collector as-is.
Four-state (test week, k2_base): 1h — 72% of forecasts in "Probably yes" (hit rate .40), 1.2% in "Yes"
(hit .625); 15m — the "Yes" band is empty, so the website should reserve 70%+ for 1h only.

## Idea 3: corridor rings from radar text — DROP (as features; code kept, null result)

`radar_text.py` parses kpszsu/deraketaua/war_monitor/nebo_raketa text against a ~150-town gazetteer
(kyiv.py PLACES + extra route towns; nebo city-district vocabulary = distance 0; case-sensitive matching to
avoid the verb "хотів"; edits >1 min count from edit_date like nebo.py — leak-safe without needing the
text-diff answer, since no double snapshot exists to diff). Features co_* = minutes-since a mention crossed
120/80/40 km, counts, per-weapon minimum distances (13 columns, `build_table(..., corridor=...)`).
Sanity check on raw states: a ≤10m-old ring80 mention raises P15 0.113 → 0.179.
Config k3_corridor dev: 15m recall .558 (.564 base), 30m .703 vs .813 base, 1h .949 vs .968 — no gain, real
harm at 30m. Also kpszsu/deraketaua/war_monitor stopped 2026-10-10 00:36 UTC and are not collected live.
Verdict: drop; the alert channel's per-raion features already carry the corridor.

## Idea 4: carrier / missile-watch — DROP (as features; null result)

Same module: ca_* = minutes since Tu-95/Tu-160/MiG-31K posts per kind, counts, and the arrival time a post
states ("Підліт ... 5:30" — Kyiv-local clock, next-morning rollover; past reports excluded). 599 carrier
posts in the whole history; 35 with an ETA. Raw states on dev: fresh MiG-31K post → P15 0.000 (n=18) — a
veto-ish signal — but ETA windows are empty on dev. Config k4_carrier: 15m recall .532 (base .564), 30m
.735 (base .813) — no gain anywhere. Verdict: drop. (The ETA idea needs weeks where ETAs are posted; none
in the dev/test data.)

## Idea 5: order features (seq) — DROP; edit-question (guard) — DROP

k8_seq (sq_*: kind of the region's own last two alert posts, their gap, the pair code): 15m .506, 30m
.852, 1h .962 — ties or loses everywhere. The counts already capture order-sensitive mass.
scripts/kyiv_guard.py — a deterministic cap where "Kyiv oblast clear + no neighbor start in 2h + no corridor
mention ≤140 km in 60m": only trims ~10 false stretches at 1h@0.2 for −1.3% recall (report
kyiv_guard_dev.md). The wave2 model already does this better; drop.

## Bold item not finished: GRU over the raw event stream (PROPOSAL)

`src/ua_alert_forecast/gru.py` + `scripts/kyiv_gru.py` are in the tree (syntax-checked, not run): the last
48 city-relevant events (starts/ends/threats by weapon/corridor mentions with distance/carrier posts) in
order → event embeddings + minutes-ago → GRU → calibrated probability, per dev week. Not completed within
the resource budget (6-8 GB cap; theunion tables already forced float32 tables and ~2 min/fit). Concrete
plan: `uv pip install torch --index-url https://download.pytorch.org/whl/cpu`, run `scripts/kyiv_gru.py
--window dev` (~30-40 min: 3 weeks × 4 epochs at 1.4M tokens/epoch), score through the same `event_report`,
then either stack (mean of GRU + k2_base) or drop. Expected value: unknown; the tabular counts leave
mostly the coin-flip residual (55% of 15m misses have no distinguishing trail), which is where order/co-occurrence could still matter.

## Final test protocol

15m = k1_kyiv, 30m + 1h = k2_base (chosen on dev only; last week run once each). Live note: both configs
need only UkraineAlarmSignal — the text channels only run in the null-result arms, so the deployed model
keeps working with the existing live collector.

## Commits and tests

`git log --oneline main..glm-rethink`:

    HEAD (a31da05+): Summary report for the Kyiv rethink round
    ba6d875 Guard: none-arm fix; final-test and guard reports
    7f1da41 Dev batch results: two-stage wave wins 30m/1h; corridor/carrier/seq nulls
    15bb8ec Pin LightGBM to four threads
    c564ae5 Cache float32 table after first cast
    e74e438 Memory: float32 region frames in build_table; GRU sequence module; guard script
    00dadbe Fix radar-text tests: sorted rows, empty own-stream, grid step
    f4f462b Two-stage wave model, corridor/carrier text tracks, order features, event eval runs
    90abf9b Event-based Kyiv evaluation: recall/lead, alarm-stretch precision, four-state view

`uv run pytest -q`: 38 passed (parser, leakage, neighbors, labels + 8 new event tests + 8 radar-text tests
+ wave-gate test).
