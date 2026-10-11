# Kyiv city event metrics, dev (2026-09-13 07:55 to 2026-10-04 07:55 UTC)

Forecasts every 5 minutes while the city is not under alert, pooled over the window. A siren is caught when
a forecast reached the threshold in the horizon before it; lead = minutes from the first such forecast.
An alarm stretch is a run of consecutive >= threshold forecasts; false when no siren starts in (first,
last + horizon]. fa/night = false stretches per night. Sirens with no forecast slot before them (city
already under alert the whole horizon) are excluded from recall and reported per config below.

## 15m threshold sweep

| config       | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:-------------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k5_text_both | 15m       |         0.1 |      137 |  156 |    0.878 |              15   |           307 |     168 |       0.453 |          8     |
| k5_text_both | 15m       |         0.2 |      109 |  156 |    0.699 |              15   |           251 |     141 |       0.438 |          6.714 |
| k5_text_both | 15m       |         0.3 |       84 |  156 |    0.538 |              10   |           211 |     125 |       0.408 |          5.952 |
| k5_text_both | 15m       |         0.5 |       25 |  156 |    0.16  |              10   |            78 |      52 |       0.333 |          2.476 |
| k5_text_both | 15m       |         0.7 |        2 |  156 |    0.013 |               5   |             8 |       6 |       0.25  |          0.286 |
| k8_seq       | 15m       |         0.1 |      139 |  156 |    0.891 |              15   |           275 |     136 |       0.505 |          6.476 |
| k8_seq       | 15m       |         0.2 |      116 |  156 |    0.744 |              12.5 |           276 |     156 |       0.435 |          7.429 |
| k8_seq       | 15m       |         0.3 |       79 |  156 |    0.506 |              10   |           203 |     121 |       0.404 |          5.762 |
| k8_seq       | 15m       |         0.5 |       10 |  156 |    0.064 |               7.5 |            57 |      47 |       0.175 |          2.238 |
| k8_seq       | 15m       |         0.7 |        1 |  156 |    0.006 |               5   |             3 |       2 |       0.333 |          0.095 |

## 30m threshold sweep

| config       | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:-------------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k5_text_both | 30m       |         0.1 |      150 |  155 |    0.968 |              25   |           309 |     150 |       0.515 |          7.143 |
| k5_text_both | 30m       |         0.2 |      143 |  155 |    0.923 |              20   |           289 |     136 |       0.529 |          6.476 |
| k5_text_both | 30m       |         0.3 |      121 |  155 |    0.781 |              20   |           256 |     126 |       0.508 |          6     |
| k5_text_both | 30m       |         0.5 |       53 |  155 |    0.342 |              15   |           117 |      57 |       0.513 |          2.714 |
| k5_text_both | 30m       |         0.7 |        1 |  155 |    0.006 |              15   |             5 |       4 |       0.2   |          0.19  |
| k8_seq       | 30m       |         0.1 |      148 |  155 |    0.955 |              30   |           289 |     133 |       0.54  |          6.333 |
| k8_seq       | 30m       |         0.2 |      142 |  155 |    0.916 |              25   |           269 |     124 |       0.539 |          5.905 |
| k8_seq       | 30m       |         0.3 |      132 |  155 |    0.852 |              20   |           277 |     132 |       0.523 |          6.286 |
| k8_seq       | 30m       |         0.5 |       73 |  155 |    0.471 |              15   |           157 |      78 |       0.503 |          3.714 |
| k8_seq       | 30m       |         0.7 |        8 |  155 |    0.052 |              12.5 |            27 |      18 |       0.333 |          0.857 |

## 1h threshold sweep

| config       | horizon   |   threshold |   caught |   of |   recall |   median_lead_min |   n_stretches |   false |   precision |   fa_per_night |
|:-------------|:----------|------------:|---------:|-----:|---------:|------------------:|--------------:|--------:|------------:|---------------:|
| k5_text_both | 1h        |         0.1 |      157 |  157 |    1     |              60   |           253 |      80 |       0.684 |          3.81  |
| k5_text_both | 1h        |         0.2 |      154 |  157 |    0.981 |              55   |           273 |      92 |       0.663 |          4.381 |
| k5_text_both | 1h        |         0.3 |      152 |  157 |    0.968 |              52.5 |           285 |      97 |       0.66  |          4.619 |
| k5_text_both | 1h        |         0.5 |      117 |  157 |    0.745 |              35   |           222 |      77 |       0.653 |          3.667 |
| k5_text_both | 1h        |         0.7 |       28 |  157 |    0.178 |              20   |            44 |      14 |       0.682 |          0.667 |
| k8_seq       | 1h        |         0.1 |      157 |  157 |    1     |              60   |           228 |      63 |       0.724 |          3     |
| k8_seq       | 1h        |         0.2 |      154 |  157 |    0.981 |              60   |           275 |      84 |       0.695 |          4     |
| k8_seq       | 1h        |         0.3 |      151 |  157 |    0.962 |              45   |           286 |     100 |       0.65  |          4.762 |
| k8_seq       | 1h        |         0.5 |      119 |  157 |    0.758 |              40   |           227 |      81 |       0.643 |          3.857 |
| k8_seq       | 1h        |         0.7 |       35 |  157 |    0.223 |              40   |            59 |      25 |       0.576 |          1.19  |

## Four-state view (website bands)

| config       | horizon   |   rows |   siren_rate |   share_no |   hit_no |   share_probably_no |   hit_probably_no |   share_probably_yes |   hit_probably_yes |   share_yes |   hit_yes |
|:-------------|:----------|-------:|-------------:|-----------:|---------:|--------------------:|------------------:|---------------------:|-------------------:|------------:|----------:|
| k5_text_both | 15m       |   3996 |        0.116 |      0.5   |    0.02  |               0.368 |             0.15  |                0.13  |              0.376 |       0.002 |     0.667 |
| k5_text_both | 30m       |   3994 |        0.221 |      0.29  |    0.054 |               0.445 |             0.208 |                0.263 |              0.429 |       0.002 |     0.143 |
| k5_text_both | 1h        |   3993 |        0.387 |      0.057 |    0.057 |               0.491 |             0.295 |                0.428 |              0.519 |       0.024 |     0.702 |
| k8_seq       | 15m       |   3996 |        0.116 |      0.497 |    0.019 |               0.377 |             0.156 |                0.125 |              0.372 |       0.001 |     1     |
| k8_seq       | 30m       |   3994 |        0.221 |      0.25  |    0.049 |               0.415 |             0.173 |                0.319 |              0.412 |       0.017 |     0.364 |
| k8_seq       | 1h        |   3993 |        0.387 |      0.052 |    0.024 |               0.489 |             0.286 |                0.428 |              0.536 |       0.031 |     0.549 |

