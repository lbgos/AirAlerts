# Experiments (dev window)

Dev test window: 14 days ending 2026-09-26 16:00 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
penalty: log loss with confident wrong forecasts (<= 20% and it happened, >= 80% and it did not) counted 10x.
conf_wrong: share of confident forecasts that were wrong; conf_promised: share they promised to be wrong.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   penalty |   conf_wrong |   conf_promised |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|----------:|-------------:|----------------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave          |  0.2694 |  0.1019 | 0.0246 | 0.8857 |    1.2499 |       0.0629 |          0.0557 |     0.0286 |    0.0389 |      0.937  |     0.9817 |     4936 |
| p1_start_conservative |  0.2583 |  0.1036 | 0.0342 | 0.8848 |    0.9054 |       0.0471 |          0.0675 |     0.0368 |    0.0274 |      0.9261 |     0.9799 |     2725 |
| c1_clear_full         |  0.1092 |  0.1401 | 0.0292 | 0.8123 |    1.4864 |       0.0904 |          0.0894 |     0.061  |    0.0507 |      0.9413 |     0.9575 |     8671 |
| p1_clear_conservative |  0.0859 |  0.1441 | 0.0544 | 0.8112 |    0.9399 |       0.0603 |          0.1075 |     0.0604 |    0.0186 |      0.9513 |     0.9446 |     4653 |

## All regions, per horizon

| predictor             |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   penalty_15m |   penalty_1h |   penalty_30m |   penalty_3h |   penalty_6h |   conf_wrong_15m |   conf_wrong_1h |   conf_wrong_30m |   conf_wrong_3h |   conf_wrong_6h |
|:----------------------|------------:|-----------:|------------:|-----------:|-----------:|--------------:|-------------:|--------------:|-------------:|-------------:|-----------------:|----------------:|-----------------:|----------------:|----------------:|
| r8_full_wave          |      0.1281 |     0.2673 |      0.1934 |     0.3665 |     0.3916 |        1.0733 |       1.1255 |        1.0642 |       1.4806 |       1.5058 |           0.0463 |          0.0521 |           0.0474 |          0.0826 |          0.086  |
| p1_start_conservative |      0.1247 |     0.2471 |      0.1816 |     0.3528 |     0.3852 |        0.8367 |       0.8789 |        0.6752 |       1.1283 |       1.0079 |           0.0402 |          0.04   |           0.0259 |          0.0688 |          0.0604 |
| c1_clear_full         |      0.0695 |     0.1183 |      0.0876 |     0.1417 |     0.129  |        1.6875 |       1.045  |        1.4654 |       1.1929 |       2.0415 |           0.0826 |          0.0884 |           0.0955 |          0.0839 |          0.1012 |
| p1_clear_conservative |      0.0506 |     0.074  |      0.0757 |     0.1053 |     0.1238 |        1.116  |       0.6954 |        0.8302 |       0.8586 |       1.199  |           0.0636 |          0.043  |           0.0562 |          0.0609 |          0.0781 |

## Rear regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   penalty |   conf_wrong |   conf_promised |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|----------:|-------------:|----------------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave          |  0.2792 |  0.1049 | 0.0281 | 0.8745 |    1.3341 |       0.0683 |          0.06   |     0.0341 |    0.0475 |      0.9264 |     0.9823 |     3425 |
| p1_start_conservative |  0.2706 |  0.1064 | 0.0346 | 0.8737 |    0.9712 |       0.0527 |          0.0731 |     0.0437 |    0.0362 |      0.9222 |     0.9859 |     1641 |
| c1_clear_full         |  0.1384 |  0.1418 | 0.035  | 0.8097 |    1.5354 |       0.0871 |          0.0871 |     0.0578 |    0.0554 |      0.9516 |     0.9288 |     7728 |
| p1_clear_conservative |  0.1195 |  0.1454 | 0.0537 | 0.8086 |    0.9768 |       0.0563 |          0.1038 |     0.0563 |    0.0135 |      0.9501 |     0.9374 |     4120 |

## Rear regions, per horizon

| predictor             |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   penalty_15m |   penalty_1h |   penalty_30m |   penalty_3h |   penalty_6h |   conf_wrong_15m |   conf_wrong_1h |   conf_wrong_30m |   conf_wrong_3h |   conf_wrong_6h |
|:----------------------|------------:|-----------:|------------:|-----------:|-----------:|--------------:|-------------:|--------------:|-------------:|-------------:|-----------------:|----------------:|-----------------:|----------------:|----------------:|
| r8_full_wave          |      0.1312 |     0.2792 |      0.1999 |     0.3826 |     0.4029 |        1.0675 |       1.2236 |        1.1055 |       1.6342 |       1.6396 |           0.0451 |          0.0567 |           0.0474 |          0.0933 |          0.0991 |
| p1_start_conservative |      0.128  |     0.2612 |      0.1974 |     0.3697 |     0.3968 |        0.8312 |       0.9616 |        0.7192 |       1.2546 |       1.0895 |           0.0393 |          0.0445 |           0.028  |          0.0809 |          0.071  |
| c1_clear_full         |      0.0861 |     0.1493 |      0.1084 |     0.192  |     0.1561 |        1.6317 |       0.7735 |        1.1461 |       1.4668 |       2.6588 |           0.0915 |          0.0607 |           0.088  |          0.0893 |          0.1061 |
| p1_clear_conservative |      0.0676 |     0.0976 |      0.0916 |     0.1698 |     0.171  |        1.0165 |       0.6383 |        0.6898 |       0.9301 |       1.6096 |           0.0655 |          0.0252 |           0.0424 |          0.0617 |          0.0868 |
