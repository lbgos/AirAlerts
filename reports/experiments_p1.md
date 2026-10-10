# Experiments (dev window)

Dev test window: 14 days ending 2026-09-26 15:45 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
penalty: log loss with confident wrong forecasts (<= 20% and it happened, >= 80% and it did not) counted 10x.
conf_wrong: share of confident forecasts that were wrong; conf_promised: share they promised to be wrong.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   penalty |   conf_wrong |   conf_promised |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|----------:|-------------:|----------------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave          |  0.2498 |  0.1063 | 0.0172 | 0.8769 |    1.2507 |       0.0649 |          0.0599 |     0.0303 |    0.0372 |      0.9379 |     0.9774 |     5684 |
| p1_start_conservative |  0.2366 |  0.1084 | 0.031  | 0.8766 |    0.9339 |       0.0505 |          0.0733 |     0.0362 |    0.0249 |      0.9197 |     0.9793 |     2663 |
| c1_clear_full         |  0.0575 |  0.1313 | 0.0266 | 0.7277 |    1.4526 |       0.0984 |          0.093  |     0.0761 |    0.0445 |      0.9545 |     0.9641 |    16994 |
| p1_clear_conservative |  0.0183 |  0.1363 | 0.0585 | 0.7268 |    0.8793 |       0.0682 |          0.1193 |     0.0814 |    0.0234 |      0.9379 |     0.9824 |    10039 |

## All regions, per horizon

| predictor             |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   penalty_15m |   penalty_1h |   penalty_30m |   penalty_3h |   penalty_6h |   conf_wrong_15m |   conf_wrong_1h |   conf_wrong_30m |   conf_wrong_3h |   conf_wrong_6h |
|:----------------------|------------:|-----------:|------------:|-----------:|-----------:|--------------:|-------------:|--------------:|-------------:|-------------:|-----------------:|----------------:|-----------------:|----------------:|----------------:|
| r8_full_wave          |      0.1261 |     0.2527 |      0.1852 |     0.3372 |     0.3478 |        1.1211 |       1.1212 |        1.0973 |       1.3548 |       1.5593 |           0.0483 |          0.0543 |           0.0495 |          0.0801 |          0.0922 |
| p1_start_conservative |      0.1214 |     0.2321 |      0.1704 |     0.3205 |     0.3385 |        0.9373 |       0.887  |        0.7409 |       1.0231 |       1.0813 |           0.0455 |          0.0428 |           0.0313 |          0.0649 |          0.0681 |
| c1_clear_full         |      0.0972 |     0.0939 |      0.0965 |     0.0026 |    -0.0028 |        2.0406 |       0.8902 |        1.637  |       1.6841 |       1.011  |           0.1126 |          0.1135 |           0.1538 |          0.0872 |          0.025  |
| p1_clear_conservative |      0.0689 |     0.0535 |      0.0837 |    -0.0724 |    -0.0424 |        1.1153 |       0.7189 |        0.8252 |       1.055  |       0.6822 |           0.0857 |          0.0667 |           0.0937 |          0.0697 |          0.025  |

## Rear regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   penalty |   conf_wrong |   conf_promised |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|----------:|-------------:|----------------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave          |  0.2729 |  0.1074 | 0.026  | 0.8721 |    1.3131 |       0.0684 |          0.0627 |     0.0355 |    0.0455 |      0.9322 |     0.9827 |     3888 |
| p1_start_conservative |  0.2636 |  0.1091 | 0.0316 | 0.8719 |    0.9802 |       0.0542 |          0.077  |     0.0426 |    0.0326 |      0.9181 |     0.9862 |     1889 |
| c1_clear_full         |  0.0562 |  0.135  | 0.0208 | 0.6836 |    1.3528 |       0.1023 |          0.0965 |     0.0811 |    0.0477 |      0.9532 |     0.9592 |    11834 |
| p1_clear_conservative |  0.008  |  0.1406 | 0.0599 | 0.6844 |    0.8282 |       0.0773 |          0.121  |     0.0821 |    0.0194 |      0.9379 |     0.9738 |     6981 |

## Rear regions, per horizon

| predictor             |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   penalty_15m |   penalty_1h |   penalty_30m |   penalty_3h |   penalty_6h |   conf_wrong_15m |   conf_wrong_1h |   conf_wrong_30m |   conf_wrong_3h |   conf_wrong_6h |
|:----------------------|------------:|-----------:|------------:|-----------:|-----------:|--------------:|-------------:|--------------:|-------------:|-------------:|-----------------:|----------------:|-----------------:|----------------:|----------------:|
| r8_full_wave          |      0.1311 |     0.2699 |      0.1943 |     0.3734 |     0.3959 |        1.1226 |       1.2309 |        1.1405 |       1.5064 |       1.5651 |           0.0481 |          0.0592 |           0.0499 |          0.0884 |          0.0963 |
| p1_start_conservative |      0.1289 |     0.2581 |      0.1904 |     0.3585 |     0.3823 |        0.9324 |       0.9727 |        0.7827 |       1.155  |       1.0583 |           0.0449 |          0.0472 |           0.0328 |          0.0762 |          0.0697 |
| c1_clear_full         |      0.0948 |     0.0841 |      0.0929 |     0.0139 |    -0.0048 |        1.912  |       0.7936 |        1.3426 |       1.8866 |       0.8292 |           0.121  |          0.117  |           0.1687 |          0.0878 |          0.0169 |
| p1_clear_conservative |      0.0649 |     0.0405 |      0.0729 |    -0.0572 |    -0.0811 |        0.9691 |       0.7215 |        0.7573 |       1.1588 |       0.5342 |           0.0892 |          0.0864 |           0.122  |          0.0723 |          0.0169 |
