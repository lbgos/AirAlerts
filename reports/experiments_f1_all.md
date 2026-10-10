# Experiments (dev window)

Dev test window: 14 days ending 2026-09-26 16:15 UTC, forecast every 5 min. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
penalty: log loss with confident wrong forecasts (<= 20% and it happened, >= 80% and it did not) counted 10x.
conf_wrong: share of confident forecasts that were wrong; conf_promised: share they promised to be wrong.
points: log2 score gained over climatology per 100 forecasts, confident right x3, confident wrong x10; higher is better.
conf_right: share of all forecasts that were confident and right.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   points |   conf_right |   penalty |   conf_wrong |   conf_promised |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|---------:|-------------:|----------:|-------------:|----------------:|-----------:|----------:|------------:|-----------:|---------:|
| f1s_recent_cons       |  0.2713 |  0.1019 | 0.0243 | 0.8877 |  57.6416 |       0.6315 |    1.0233 |       0.0531 |          0.0617 |     0.0302 |    0.029  |      0.9308 |     0.9759 |    12585 |
| p1_start_conservative |  0.2643 |  0.1028 | 0.0248 | 0.8856 |  56.4933 |       0.628  |    1.0106 |       0.0522 |          0.0617 |     0.0314 |    0.0298 |      0.9325 |     0.9778 |    11031 |
| f1c_recent_cons       |  0.1089 |  0.1403 | 0.0412 | 0.8163 |  10.5766 |       0.4449 |    1.0944 |       0.0695 |          0.096  |     0.0579 |    0.0261 |      0.9389 |     0.9533 |    21488 |
| p1_clear_conservative |  0.1002 |  0.1416 | 0.0421 | 0.8125 |   9.1928 |       0.4498 |    1.1472 |       0.0748 |          0.0978 |     0.0664 |    0.0458 |      0.9397 |     0.949  |    21156 |

## All regions, per horizon

| predictor             |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   points_15m |   points_1h |   points_30m |   points_3h |   points_6h |   penalty_15m |   penalty_1h |   penalty_30m |   penalty_3h |   penalty_6h |   conf_wrong_15m |   conf_wrong_1h |   conf_wrong_30m |   conf_wrong_3h |   conf_wrong_6h |
|:----------------------|------------:|-----------:|------------:|-----------:|-----------:|-------------:|------------:|-------------:|------------:|------------:|--------------:|-------------:|--------------:|-------------:|-------------:|-----------------:|----------------:|-----------------:|----------------:|----------------:|
| f1s_recent_cons       |      0.1369 |     0.2636 |      0.1967 |     0.3679 |     0.3916 |      72.2956 |     48.9881 |      46.241  |     64.0735 |     56.6098 |        0.9365 |       0.9472 |        0.8079 |       1.2464 |       1.1784 |           0.0443 |          0.0432 |           0.0339 |          0.0748 |          0.0694 |
| p1_start_conservative |      0.1279 |     0.2555 |      0.1848 |     0.3614 |     0.3918 |      74.9258 |     48.0302 |      44.08   |     59.228  |     56.2026 |        0.9804 |       0.9354 |        0.7967 |       1.1999 |       1.1407 |           0.0468 |          0.0426 |           0.0334 |          0.0713 |          0.0669 |
| f1c_recent_cons       |      0.0729 |     0.1008 |      0.0895 |     0.1352 |     0.1463 |      15.6455 |      4.6431 |       8.0718 |     10.8799 |     13.6425 |        1.3273 |       0.7263 |        1.0903 |       1.0589 |       1.2688 |           0.0716 |          0.0474 |           0.0749 |          0.0764 |          0.0774 |
| p1_clear_conservative |      0.0666 |     0.0987 |      0.0862 |     0.1267 |     0.1228 |      14.9721 |      4.8385 |       8.8519 |     12.0241 |      5.2777 |        1.3112 |       0.7627 |        1.1044 |       1.0629 |       1.4949 |           0.071  |          0.054  |           0.0761 |          0.0779 |          0.0949 |

## Rear regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   points |   conf_right |   penalty |   conf_wrong |   conf_promised |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|---------:|-------------:|----------:|-------------:|----------------:|-----------:|----------:|------------:|-----------:|---------:|
| f1s_recent_cons       |  0.2809 |  0.1051 | 0.0249 | 0.8757 |  65.9101 |       0.6248 |    1.0998 |       0.0592 |          0.0672 |     0.037  |    0.0373 |      0.9265 |     0.9809 |     8551 |
| p1_start_conservative |  0.2769 |  0.1056 | 0.026  | 0.8751 |  65.0157 |       0.6223 |    1.0799 |       0.0577 |          0.0673 |     0.0381 |    0.0382 |      0.9273 |     0.9841 |     7302 |
| f1c_recent_cons       |  0.1395 |  0.142  | 0.0438 | 0.8136 |  11.8619 |       0.4447 |    1.1354 |       0.0659 |          0.0948 |     0.0553 |    0.0228 |      0.9383 |     0.9468 |    18900 |
| p1_clear_conservative |  0.1315 |  0.1432 | 0.043  | 0.8095 |  11.0595 |       0.45   |    1.1877 |       0.0695 |          0.0963 |     0.0639 |    0.0582 |      0.9386 |     0.9425 |    18817 |

## Rear regions, per horizon

| predictor             |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   points_15m |   points_1h |   points_30m |   points_3h |   points_6h |   penalty_15m |   penalty_1h |   penalty_30m |   penalty_3h |   penalty_6h |   conf_wrong_15m |   conf_wrong_1h |   conf_wrong_30m |   conf_wrong_3h |   conf_wrong_6h |
|:----------------------|------------:|-----------:|------------:|-----------:|-----------:|-------------:|------------:|-------------:|------------:|------------:|--------------:|-------------:|--------------:|-------------:|-------------:|-----------------:|----------------:|-----------------:|----------------:|----------------:|
| f1s_recent_cons       |      0.1404 |     0.2738 |      0.207  |     0.3814 |     0.4019 |      78.9977 |     56.7094 |      52.393  |     74.8862 |     66.5641 |        0.9334 |       1.0385 |        0.8499 |       1.3938 |       1.2834 |           0.0435 |          0.048  |           0.035  |          0.0875 |          0.082  |
| p1_start_conservative |      0.1341 |     0.2699 |      0.1994 |     0.3774 |     0.4036 |      82.2821 |     55.6878 |      50.5168 |     69.4941 |     67.0976 |        0.9723 |       1.0285 |        0.839  |       1.3373 |       1.2222 |           0.0457 |          0.0476 |           0.0347 |          0.0836 |          0.0769 |
| f1c_recent_cons       |      0.0855 |     0.1267 |      0.108  |     0.1941 |     0.1834 |      12.0258 |      9.1427 |       6.3551 |     16.0023 |     15.7837 |        1.2639 |       0.638  |        0.8279 |       1.2599 |       1.6874 |           0.0778 |          0.0286 |           0.0581 |          0.082  |          0.0831 |
| p1_clear_conservative |      0.0796 |     0.1257 |      0.1032 |     0.1873 |     0.1615 |      10.9166 |      8.5745 |       6.8336 |     18.6259 |     10.3467 |        1.2362 |       0.6535 |        0.8538 |       1.2308 |       1.9641 |           0.0762 |          0.0314 |           0.0626 |          0.0798 |          0.0977 |
