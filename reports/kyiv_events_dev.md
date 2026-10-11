# Kyiv city event metrics, dev (2026-09-13 07:55 to 2026-10-04 07:55 UTC)

Forecasts every 5 minutes while the city is not under alert, pooled over the window. A siren is caught when
a forecast reached the threshold in the horizon before it; lead = minutes from the first such forecast.
An alarm stretch is a run of consecutive >= threshold forecasts; false when no siren starts in (first,
last + horizon]. fa/night = false stretches per night. Sirens with no forecast slot before them (city
already under alert the whole horizon) are excluded from recall and reported per config below.

## 15m threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k2_base  | 15m       |         0.1 |      143 |  156 |    0.917 |                15 |           276 |     133 |       0.518 |          6.333 |
| k2_base  | 15m       |         0.2 |      110 |  156 |    0.705 |                15 |           261 |     149 |       0.429 |          7.095 |
| k2_base  | 15m       |         0.3 |       88 |  156 |    0.564 |                10 |           204 |     113 |       0.446 |          5.381 |
| k2_base  | 15m       |         0.5 |        0 |  156 |    0     |               nan |            10 |      10 |       0     |          0.476 |
| k2_base  | 15m       |         0.7 |        0 |  156 |    0     |               nan |             0 |       0 |     nan     |          0     |
| k2_kyiv  | 15m       |         0.1 |      140 |  156 |    0.897 |                15 |           296 |     156 |       0.473 |          7.429 |
| k2_kyiv  | 15m       |         0.2 |      107 |  156 |    0.686 |                10 |           265 |     157 |       0.408 |          7.476 |
| k2_kyiv  | 15m       |         0.3 |       68 |  156 |    0.436 |                10 |           181 |     111 |       0.387 |          5.286 |
| k2_kyiv  | 15m       |         0.5 |        5 |  156 |    0.032 |                 5 |            45 |      40 |       0.111 |          1.905 |
| k2_kyiv  | 15m       |         0.7 |        0 |  156 |    0     |               nan |             1 |       1 |       0     |          0.048 |

## 30m threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k2_base  | 30m       |         0.1 |      154 |  155 |    0.994 |                30 |           245 |      88 |       0.641 |          4.19  |
| k2_base  | 30m       |         0.2 |      146 |  155 |    0.942 |                25 |           276 |     125 |       0.547 |          5.952 |
| k2_base  | 30m       |         0.3 |      134 |  155 |    0.865 |                20 |           274 |     133 |       0.515 |          6.333 |
| k2_base  | 30m       |         0.5 |       69 |  155 |    0.445 |                10 |           161 |      83 |       0.484 |          3.952 |
| k2_base  | 30m       |         0.7 |        2 |  155 |    0.013 |                20 |             3 |       1 |       0.667 |          0.048 |
| k2_kyiv  | 30m       |         0.1 |      150 |  155 |    0.968 |                30 |           296 |     141 |       0.524 |          6.714 |
| k2_kyiv  | 30m       |         0.2 |      145 |  155 |    0.935 |                25 |           279 |     128 |       0.541 |          6.095 |
| k2_kyiv  | 30m       |         0.3 |      126 |  155 |    0.813 |                20 |           278 |     136 |       0.511 |          6.476 |
| k2_kyiv  | 30m       |         0.5 |       31 |  155 |    0.2   |                10 |            96 |      64 |       0.333 |          3.048 |
| k2_kyiv  | 30m       |         0.7 |        0 |  155 |    0     |               nan |             1 |       1 |       0     |          0.048 |

## 1h threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k2_base  | 1h        |         0.1 |      157 |  157 |    1     |              60   |           181 |      26 |       0.856 |          1.238 |
| k2_base  | 1h        |         0.2 |      157 |  157 |    1     |              60   |           216 |      56 |       0.741 |          2.667 |
| k2_base  | 1h        |         0.3 |      157 |  157 |    1     |              60   |           254 |      73 |       0.713 |          3.476 |
| k2_base  | 1h        |         0.5 |      138 |  157 |    0.879 |              40   |           245 |      79 |       0.678 |          3.762 |
| k2_base  | 1h        |         0.7 |       42 |  157 |    0.268 |              20   |            77 |      24 |       0.688 |          1.143 |
| k2_kyiv  | 1h        |         0.1 |      157 |  157 |    1     |              60   |           210 |      52 |       0.752 |          2.476 |
| k2_kyiv  | 1h        |         0.2 |      157 |  157 |    1     |              60   |           271 |      86 |       0.683 |          4.095 |
| k2_kyiv  | 1h        |         0.3 |      152 |  157 |    0.968 |              55   |           287 |     100 |       0.652 |          4.762 |
| k2_kyiv  | 1h        |         0.5 |      122 |  157 |    0.777 |              35   |           237 |      78 |       0.671 |          3.714 |
| k2_kyiv  | 1h        |         0.7 |       12 |  157 |    0.076 |              42.5 |            12 |       4 |       0.667 |          0.19  |

## Four-state view (website bands)

| config   | horizon   |   rows |   siren_rate |   share_no |   hit_no |   share_probably_no |   hit_probably_no |   share_probably_yes |   hit_probably_yes |   share_yes |   hit_yes |
|:---------|:----------|-------:|-------------:|-----------:|---------:|--------------------:|------------------:|---------------------:|-------------------:|------------:|----------:|
| k2_base  | 15m       |   3996 |        0.116 |      0.434 |    0.017 |               0.425 |             0.131 |                0.14  |              0.375 |       0     |   nan     |
| k2_base  | 30m       |   3994 |        0.221 |      0.131 |    0.004 |               0.526 |             0.154 |                0.342 |              0.406 |       0.001 |     1     |
| k2_base  | 1h        |   3993 |        0.387 |      0.027 |    0     |               0.32  |             0.2   |                0.617 |              0.484 |       0.036 |     0.685 |
| k2_kyiv  | 15m       |   3996 |        0.116 |      0.48  |    0.018 |               0.428 |             0.158 |                0.091 |              0.43  |       0     |     1     |
| k2_kyiv  | 30m       |   3994 |        0.221 |      0.17  |    0.015 |               0.552 |             0.181 |                0.278 |              0.426 |       0     |     1     |
| k2_kyiv  | 1h        |   3993 |        0.387 |      0.025 |    0     |               0.454 |             0.249 |                0.516 |              0.524 |       0.005 |     0.737 |

