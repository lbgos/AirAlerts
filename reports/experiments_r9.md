# Round r9: walk-forward screening (calibration, spatial features)

The earlier rounds picked models on one 14-day dev window and confirmed on one 14-day final window. With
about 8% of 15-minute windows containing a siren and forecasts that are nearly identical across neighbouring
rows, a single window is a noisy judge. This round scores every candidate on four 14-day windows spaced two
weeks apart, then looks once at a fifth window that was never used for any choice.

Protocol (`scripts/backtest.py`): each window trains on everything before it, calibrates on the 7 days before
the test window, and scores only the test window, purged exactly like `forecast train`. Skill is
1 − Brier / Brier(climatology). `scripts/compare.py` reports paired Brier deltas and a day-block bootstrap
(2000 resamples of whole days), because rows within a day and across horizons are correlated.

Screening windows end 2026-09-21 and 2026-10-19 (two 14-day windows), horizons 15m and 6h unless noted.
Confirmation windows end 2026-09-07, 2026-09-21, 2026-10-05, 2026-10-19. Sealed window ends 2026-11-02
(two weeks of posts that no earlier round used). Baseline on all tables: `f1s_recent_cons` / `f1c_recent_cons`
(the live pair), refitted inside each window.

All screens ran on the 15-minute grid to keep the loop fast. The live configs train on a 5-minute grid,
where the f1 round found a small extra gain at 15m; the r9 effect is measured on 15 minutes and not
re-measured on 5.

## Calibration

The conservative cap was set at a 99% Wilson bound (`bound_z=2.576`). On the screening windows it was
leaving probability on the table at every horizon. Deltas are Brier(candidate) − Brier(baseline), negative
is better; CI is the 95% day-block interval. `conf_wrong/promised` is the share of confident forecasts that
were wrong next to the share they promised.

| siren starts | 15m delta [CI] | 6h delta [CI] | ECE 15m | conf_wrong/promised 15m | verdict |
|:--|--:|--:|--:|--:|:--|
| Platt, no cap | −0.00045 [−0.00074, −0.00014] | −0.00234 [−0.00355, −0.00109] | 0.011 | 4.9% / 4.0% | reject: now overconfident |
| conservative, z=1.645 | −0.00041 [−0.00052, −0.00029] | −0.00111 [−0.00152, −0.00068] | 0.011 | 3.9% / 4.4% | keep |
| conservative, z=1.0 | −0.00052 [−0.00070, −0.00034] | −0.00160 [−0.00223, −0.00097] | 0.006 | 4.1% / 4.0% | keep as the aggressive option |
| half-life 21 days, z=1.645 | −0.00004 | +0.00200 | — | — | reject: no 15m gain, worse at 6h |
| calib 14 days, z=1.645 | −0.00065 | +0.00109 | — | — | reject: helps 15m, costs 6h |

| all-clear | 15m delta [CI] | 6h delta [CI] | ECE 15m | conf_wrong/promised 15m | verdict |
|:--|--:|--:|--:|--:|:--|
| Platt, no cap | −0.00560 [−0.00645, −0.00466] | −0.00053 [−0.00364, 0.00277] | 0.013 | 7.0% / 7.5% | reject: 6h overconfident |
| conservative, z=1.645 | −0.00270 [−0.00301, −0.00237] | −0.00110 [−0.00199, −0.00019] | 0.051 | 4.7% / 8.0% | keep |
| conservative, z=1.0 | −0.00395 [−0.00445, −0.00341] | −0.00144 [−0.00288, 0.00004] | 0.039 | 4.9% / 7.3% | keep as the aggressive option |

z=1.645 is the default because on the screening windows it improved Brier at every horizon while staying
inside the confidence guardrail: on both targets no horizon claimed more certainty than it delivered there. On all four confirmation
windows the all-clear Brier delta was −0.00217 at 15m, −0.00196 at 1h and −0.00211 at 6h (ECEs 0.039, 0.041
and 0.045, all below the baseline). z=1.0 buys another
0.0001–0.0013 Brier but sits at (siren starts) or slightly past (all-clear 6h) the promised error rate.

## Spatial wave features

Group `spatial` (`sw_*`, in `dataset.py`): every other oblast's activity weighted by exp(−distance/150 or
300 km), recent starts in the eastern and north-eastern half, distance to the nearest active oblast and
whether it is closing in over an hour, and the centre of the last hour's sirens with its direction and speed
relative to the oblast. The existing neighbour features only count adjacent oblasts.

Screening, added on top of the f1 feature set (same calibration for both arms):

| horizon | delta [CI] | days better |
|:--|--:|--:|
| 15m | −0.00080 [−0.00122, −0.00044] | 89% |
| 1h | +0.00003 [−0.00047, 0.00054] | 43% |
| 6h | +0.00091 [−0.00004, 0.00178] | 25% |

Combined with z=1.645 and confirmed on all four windows: 15m −0.00098 [−0.00122, −0.00075] (better on 93% of
days, skill 0.121 → 0.135), 1h −0.00082 [−0.00116, −0.00049], 6h −0.00211 [−0.00301, −0.00118]. The 6h row of
the two-window screen (+0.0009) did not replicate: on four windows the model with the group is 0.0003 better
at 6h than the same model without it.

Splitting the features by horizon (`r10s_recent_cons`, spatial only at 15m/30m) changed 1h by +0.00004
[−0.00028, 0.00036] and 6h by +0.00032 [−0.00044, 0.00110] against r9 on the same four windows, so it adds
nothing. Rejected; `Config.groups_by_horizon` stays for later rounds.

A second feature module (regional and national 6–24h intensity, trend ratios, current yellow/red level,
wave age) changed the 15m Brier by less than 0.0001 on the screening window and was dropped. It is not in
the repo.

## Sealed window

One run per config on the window ending 2026-11-02 (about 1,750 siren starts), never used above. Deltas are
Brier(candidate) − Brier(baseline), both refitted inside the window.

| target | horizon | delta [CI] | days better | ECE baseline → r9 | skill baseline → r9 |
|:--|:--|--:|--:|--:|--:|
| siren starts | 15m | −0.00165 [−0.00204, −0.00130] | 100% | 0.037 → 0.024 | 0.143 → 0.163 |
| siren starts | 1h | −0.00147 [−0.00215, −0.00083] | 93% | 0.047 → 0.033 | 0.309 → 0.316 |
| siren starts | 6h | +0.00169 [−0.00014, 0.00371] | 43% | 0.034 → 0.046 | 0.519 → 0.514 |
| all-clear | 15m | −0.00063 [−0.00111, −0.00006] | 50% | 0.032 → 0.017 | 0.073 → 0.078 |
| all-clear | 1h | −0.00217 [−0.00309, −0.00127] | 93% | 0.056 → 0.044 | 0.140 → 0.152 |
| all-clear | 6h | −0.00221 [−0.00387, −0.00023] | 79% | 0.071 → 0.053 | 0.190 → 0.204 |

The all-clear improvement survived everywhere. Siren starts improved at 15m and 1h and did not at 6h; the
6h interval includes zero, and both arms were overconfident there on this window (confident wrong 11.5%
against 7.4% promised for r9, 10.3% against 7.6% for the baseline). Two busy weeks are not enough to say
whether that is the looser cap or the window.

## Decision

`r9s_recent_cons` (spatial features, z=1.645) and `r9c_recent_cons` (z=1.645) are the pair to train next;
`r10s_recent_cons` (per-horizon features) lost to r9 and stays an experiment.
They beat the live pair on the 15-minute siren forecast (the product's main number) and on the all-clear at
every horizon, with calibration inside its own promises. The live service runs this pair from 2026-11-04.
