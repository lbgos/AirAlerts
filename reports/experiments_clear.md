# Experiments (dev window)

Dev test window: 14 days ending 2026-09-26 14:30 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor           |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:--------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| c1_clear_full_radar |  0.059  |  0.1309 | 0.0238 | 0.7274 |     0.0738 |    0.047  |      0.9586 |     0.9585 |    17197 |
| c1_clear_full       |  0.0578 |  0.1312 | 0.0255 | 0.7276 |     0.0746 |    0.0449 |      0.9567 |     0.9616 |    17342 |
| c1_clear_time       |  0.0291 |  0.1363 | 0.0206 | 0.7069 |     0.0774 |    0.0551 |      0.938  |     0.9819 |    16522 |

## All regions, per horizon

| predictor           |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_15m |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:--------------------|------------:|-----------:|------------:|-----------:|-----------:|----------:|---------:|----------:|---------:|---------:|
| c1_clear_full_radar |      0.1082 |     0.0953 |      0.1012 |     0.0014 |    -0.0109 |    0.0145 |   0.0383 |    0.0335 |   0.021  |   0.0117 |
| c1_clear_full       |      0.0997 |     0.0968 |      0.0964 |     0.005  |    -0.0088 |    0.0174 |   0.0407 |    0.0357 |   0.0224 |   0.0114 |
| c1_clear_time       |      0.0488 |     0.0564 |      0.0582 |    -0.0031 |    -0.0147 |    0.0121 |   0.0301 |    0.0234 |   0.0265 |   0.0107 |

## Rear regions, averaged over horizons

| predictor           |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:--------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| c1_clear_full_radar |  0.0621 |  0.1344 | 0.0175 | 0.6846 |     0.0793 |    0.0575 |      0.9568 |     0.9476 |    11995 |
| c1_clear_full       |  0.0568 |  0.135  | 0.0195 | 0.6851 |     0.08   |    0.0535 |      0.9552 |     0.9542 |    12119 |
| c1_clear_time       |  0.0274 |  0.1407 | 0.015  | 0.6575 |     0.0825 |    0.0464 |      0.95   |     0.971  |    11662 |

## Rear regions, per horizon

| predictor           |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_15m |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:--------------------|------------:|-----------:|------------:|-----------:|-----------:|----------:|---------:|----------:|---------:|---------:|
| c1_clear_full_radar |      0.1081 |     0.0885 |      0.099  |     0.0132 |     0.0016 |    0.0084 |   0.0263 |    0.0231 |   0.0223 |   0.0071 |
| c1_clear_full       |      0.0983 |     0.0871 |      0.0929 |     0.0148 |    -0.0089 |    0.0116 |   0.0304 |    0.0247 |   0.0218 |   0.0091 |
| c1_clear_time       |      0.0402 |     0.045  |      0.0528 |     0.0125 |    -0.0134 |    0.0105 |   0.019  |    0.0177 |   0.0177 |   0.0102 |
