# Kyiv city event metrics, dev (2026-09-27 07:55 to 2026-09-20 07:55 UTC)

Forecasts every 5 minutes while the city is not under alert, pooled over the window. A siren is caught when
a forecast reached the threshold in the horizon before it; lead = minutes from the first such forecast.
An alarm stretch is a run of consecutive >= threshold forecasts; false when no siren starts in (first,
last + horizon]. fa/night = false stretches per night. Sirens with no forecast slot before them (city
already under alert the whole horizon) are excluded from recall and reported per config below.

## 15m threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k1_base  | 15m       |         0.1 |      144 |  156 |    0.923 |                15 |           267 |     123 |       0.539 |          5.857 |
| k1_base  | 15m       |         0.2 |      111 |  156 |    0.712 |                15 |           275 |     163 |       0.407 |          7.762 |
| k1_base  | 15m       |         0.3 |       91 |  156 |    0.583 |                10 |           220 |     122 |       0.445 |          5.81  |
| k1_base  | 15m       |         0.5 |        5 |  156 |    0.032 |                 5 |            36 |      31 |       0.139 |          1.476 |
| k1_base  | 15m       |         0.7 |        0 |  156 |    0     |               nan |             4 |       4 |       0     |          0.19  |
| k1_kyiv  | 15m       |         0.1 |      137 |  156 |    0.878 |                15 |           276 |     138 |       0.5   |          6.571 |
| k1_kyiv  | 15m       |         0.2 |      116 |  156 |    0.744 |                15 |           270 |     153 |       0.433 |          7.286 |
| k1_kyiv  | 15m       |         0.3 |       88 |  156 |    0.564 |                10 |           207 |     117 |       0.435 |          5.571 |
| k1_kyiv  | 15m       |         0.5 |       17 |  156 |    0.109 |                 5 |            77 |      60 |       0.221 |          2.857 |
| k1_kyiv  | 15m       |         0.7 |        0 |  156 |    0     |               nan |             3 |       3 |       0     |          0.143 |

## 30m threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k1_base  | 30m       |         0.1 |      151 |  155 |    0.974 |              30   |           257 |     101 |       0.607 |          4.81  |
| k1_base  | 30m       |         0.2 |      144 |  155 |    0.929 |              25   |           284 |     135 |       0.525 |          6.429 |
| k1_base  | 30m       |         0.3 |      131 |  155 |    0.845 |              20   |           263 |     124 |       0.529 |          5.905 |
| k1_base  | 30m       |         0.5 |       81 |  155 |    0.523 |              10   |           170 |      81 |       0.524 |          3.857 |
| k1_base  | 30m       |         0.7 |        4 |  155 |    0.026 |              12.5 |            16 |      12 |       0.25  |          0.571 |
| k1_kyiv  | 30m       |         0.1 |      149 |  155 |    0.961 |              30   |           285 |     133 |       0.533 |          6.333 |
| k1_kyiv  | 30m       |         0.2 |      141 |  155 |    0.91  |              25   |           291 |     145 |       0.502 |          6.905 |
| k1_kyiv  | 30m       |         0.3 |      126 |  155 |    0.813 |              20   |           266 |     126 |       0.526 |          6     |
| k1_kyiv  | 30m       |         0.5 |       60 |  155 |    0.387 |              10   |           125 |      57 |       0.544 |          2.714 |
| k1_kyiv  | 30m       |         0.7 |        2 |  155 |    0.013 |               5   |            16 |      14 |       0.125 |          0.667 |

## 1h threshold sweep

| config   | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:---------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k1_base  | 1h        |         0.1 |      157 |  157 |    1     |                60 |           191 |      36 |       0.812 |          1.714 |
| k1_base  | 1h        |         0.2 |      157 |  157 |    1     |                60 |           235 |      65 |       0.723 |          3.095 |
| k1_base  | 1h        |         0.3 |      152 |  157 |    0.968 |                60 |           266 |      85 |       0.68  |          4.048 |
| k1_base  | 1h        |         0.5 |      143 |  157 |    0.911 |                45 |           264 |      81 |       0.693 |          3.857 |
| k1_base  | 1h        |         0.7 |       53 |  157 |    0.338 |                20 |           106 |      40 |       0.623 |          1.905 |
| k1_kyiv  | 1h        |         0.1 |      157 |  157 |    1     |                60 |           218 |      55 |       0.748 |          2.619 |
| k1_kyiv  | 1h        |         0.2 |      154 |  157 |    0.981 |                60 |           272 |      89 |       0.673 |          4.238 |
| k1_kyiv  | 1h        |         0.3 |      152 |  157 |    0.968 |                50 |           278 |      92 |       0.669 |          4.381 |
| k1_kyiv  | 1h        |         0.5 |      115 |  157 |    0.732 |                35 |           233 |      81 |       0.652 |          3.857 |
| k1_kyiv  | 1h        |         0.7 |       20 |  157 |    0.127 |                45 |            34 |      12 |       0.647 |          0.571 |

## Four-state view (website bands)

| config   | horizon   |   rows |   siren_rate |   share_no |   hit_no |   share_probably_no |   hit_probably_no |   share_probably_yes |   hit_probably_yes |   share_yes |   hit_yes |
|:---------|:----------|-------:|-------------:|-----------:|---------:|--------------------:|------------------:|---------------------:|-------------------:|------------:|----------:|
| k1_base  | 15m       |   3996 |        0.116 |      0.437 |    0.021 |               0.428 |             0.128 |                0.133 |              0.383 |       0.001 |     0.75  |
| k1_base  | 30m       |   3994 |        0.221 |      0.143 |    0.007 |               0.5   |             0.157 |                0.352 |              0.392 |       0.005 |     0.65  |
| k1_base  | 1h        |   3993 |        0.387 |      0.024 |    0     |               0.348 |             0.22  |                0.578 |              0.483 |       0.05  |     0.622 |
| k1_kyiv  | 15m       |   3996 |        0.116 |      0.487 |    0.018 |               0.378 |             0.145 |                0.134 |              0.384 |       0.001 |     0.667 |
| k1_kyiv  | 30m       |   3994 |        0.221 |      0.242 |    0.037 |               0.483 |             0.185 |                0.27  |              0.445 |       0.005 |     0.526 |
| k1_kyiv  | 1h        |   3993 |        0.387 |      0.031 |    0.041 |               0.491 |             0.277 |                0.465 |              0.521 |       0.014 |     0.593 |

