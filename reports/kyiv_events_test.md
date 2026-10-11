# Kyiv city event metrics, test (2026-10-04 07:55 to 2026-10-11 07:55 UTC)

Forecasts every 5 minutes while the city is not under alert, pooled over the window. A siren is caught when
a forecast reached the threshold in the horizon before it; lead = minutes from the first such forecast.
An alarm stretch is a run of consecutive >= threshold forecasts; false when no siren starts in (first,
last + horizon]. fa/night = false stretches per night. Sirens with no forecast slot before them (city
already under alert the whole horizon) are excluded from recall and reported per config below.

## 15m threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k2_base  | 15m       |         0.1 |       38 |   46 |    0.826 |              15   |            97 |      60 |       0.381 |          8.571 |
| k2_base  | 15m       |         0.2 |       24 |   46 |    0.522 |              10   |            89 |      65 |       0.27  |          9.286 |
| k2_base  | 15m       |         0.3 |       18 |   46 |    0.391 |              12.5 |            66 |      47 |       0.288 |          6.714 |
| k2_base  | 15m       |         0.5 |        4 |   46 |    0.087 |               5   |            11 |       7 |       0.364 |          1     |
| k2_base  | 15m       |         0.7 |        0 |   46 |    0     |             nan   |             0 |       0 |     nan     |          0     |
| k1_kyiv  | 15m       |         0.1 |       39 |   46 |    0.848 |              15   |           109 |      71 |       0.349 |         10.143 |
| k1_kyiv  | 15m       |         0.2 |       29 |   46 |    0.63  |              15   |           105 |      75 |       0.286 |         10.714 |
| k1_kyiv  | 15m       |         0.3 |       25 |   46 |    0.543 |              10   |            70 |      44 |       0.371 |          6.286 |
| k1_kyiv  | 15m       |         0.5 |        7 |   46 |    0.152 |               5   |            24 |      17 |       0.292 |          2.429 |
| k1_kyiv  | 15m       |         0.7 |        0 |   46 |    0     |             nan   |             1 |       1 |       0     |          0.143 |

## 30m threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k2_base  | 30m       |         0.1 |       44 |   46 |    0.957 |              30   |            79 |      35 |       0.557 |          5     |
| k2_base  | 30m       |         0.2 |       42 |   46 |    0.913 |              30   |            96 |      51 |       0.469 |          7.286 |
| k2_base  | 30m       |         0.3 |       34 |   46 |    0.739 |              25   |            97 |      59 |       0.392 |          8.429 |
| k2_base  | 30m       |         0.5 |       15 |   46 |    0.326 |              15   |            44 |      27 |       0.386 |          3.857 |
| k2_base  | 30m       |         0.7 |        0 |   46 |    0     |             nan   |             0 |       0 |     nan     |          0     |
| k1_kyiv  | 30m       |         0.1 |       43 |   46 |    0.935 |              30   |            84 |      40 |       0.524 |          5.714 |
| k1_kyiv  | 30m       |         0.2 |       41 |   46 |    0.891 |              30   |           116 |      67 |       0.422 |          9.571 |
| k1_kyiv  | 30m       |         0.3 |       32 |   46 |    0.696 |              17.5 |            96 |      61 |       0.365 |          8.714 |
| k1_kyiv  | 30m       |         0.5 |       12 |   46 |    0.261 |              12.5 |            40 |      26 |       0.35  |          3.714 |
| k1_kyiv  | 30m       |         0.7 |        0 |   46 |    0     |             nan   |             2 |       2 |       0     |          0.286 |

## 1h threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k2_base  | 1h        |         0.1 |       46 |   46 |    1     |              60   |            50 |       5 |       0.9   |          0.714 |
| k2_base  | 1h        |         0.2 |       45 |   46 |    0.978 |              60   |            68 |      23 |       0.662 |          3.286 |
| k2_base  | 1h        |         0.3 |       45 |   46 |    0.978 |              55   |            89 |      42 |       0.528 |          6     |
| k2_base  | 1h        |         0.5 |       34 |   46 |    0.739 |              35   |            75 |      33 |       0.56  |          4.714 |
| k2_base  | 1h        |         0.7 |        5 |   46 |    0.109 |              20   |            10 |       5 |       0.5   |          0.714 |
| k1_kyiv  | 1h        |         0.1 |       45 |   46 |    0.978 |              60   |            62 |      14 |       0.774 |          2     |
| k1_kyiv  | 1h        |         0.2 |       45 |   46 |    0.978 |              55   |            86 |      34 |       0.605 |          4.857 |
| k1_kyiv  | 1h        |         0.3 |       44 |   46 |    0.957 |              50   |           103 |      51 |       0.505 |          7.286 |
| k1_kyiv  | 1h        |         0.5 |       30 |   46 |    0.652 |              22.5 |            72 |      33 |       0.542 |          4.714 |
| k1_kyiv  | 1h        |         0.7 |        1 |   46 |    0.022 |              55   |             4 |       3 |       0.25  |          0.429 |

## Four-state view (website bands)

| config   | horizon   |   rows |   siren_rate |   share_no |   hit_no |   share_probably_no |   hit_probably_no |   share_probably_yes |   hit_probably_yes |   share_yes |   hit_yes |
|:---------|:----------|-------:|-------------:|-----------:|---------:|--------------------:|------------------:|---------------------:|-------------------:|------------:|----------:|
| k2_base  | 15m       |   1379 |        0.098 |      0.334 |    0.033 |               0.53  |             0.103 |                0.136 |              0.241 |       0     |   nan     |
| k2_base  | 30m       |   1376 |        0.193 |      0.065 |    0.101 |               0.605 |             0.15  |                0.33  |              0.289 |       0     |   nan     |
| k2_base  | 1h        |   1370 |        0.345 |      0.004 |    0.8   |               0.264 |             0.188 |                0.721 |              0.395 |       0.012 |     0.625 |
| k1_kyiv  | 15m       |   1379 |        0.098 |      0.347 |    0.033 |               0.519 |             0.089 |                0.133 |              0.299 |       0.001 |     0     |
| k1_kyiv  | 30m       |   1376 |        0.193 |      0.09  |    0.073 |               0.664 |             0.159 |                0.245 |              0.329 |       0.001 |     0     |
| k1_kyiv  | 1h        |   1370 |        0.345 |      0.003 |    0.75  |               0.469 |             0.237 |                0.525 |              0.437 |       0.004 |     0.6   |

