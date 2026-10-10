# Experiments (dev window)

Dev test window: 14 days ending 2026-09-26 11:45 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor        |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:-----------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave     |  0.2507 |  0.1064 | 0.0191 | 0.8769 |     0.0301 |    0.0397 |      0.9375 |     0.9679 |     5668 |
| r2_small_platt7d |  0.2482 |  0.1066 | 0.0222 | 0.8764 |     0.0302 |    0.0402 |      0.9365 |     0.977  |     5596 |

## All regions, per horizon

| predictor        |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_15m |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:-----------------|------------:|-----------:|------------:|-----------:|-----------:|----------:|---------:|----------:|---------:|---------:|
| r8_full_wave     |      0.1271 |     0.2559 |      0.1856 |     0.3376 |     0.3473 |    0.0075 |   0.0217 |    0.0144 |   0.0229 |   0.029  |
| r2_small_platt7d |      0.1199 |     0.2517 |      0.1808 |     0.34   |     0.3488 |    0.0096 |   0.024  |    0.0173 |   0.0272 |   0.0328 |

## Rear regions, averaged over horizons

| predictor        |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:-----------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave     |  0.2725 |  0.1076 | 0.0283 | 0.8721 |     0.0349 |    0.0483 |      0.9338 |     0.9453 |     3886 |
| r2_small_platt7d |  0.2691 |  0.1079 | 0.0316 | 0.8714 |     0.0347 |    0.0484 |      0.9303 |     0.9822 |     3804 |

## Rear regions, per horizon

| predictor        |   skill_15m |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_15m |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:-----------------|------------:|-----------:|------------:|-----------:|-----------:|----------:|---------:|----------:|---------:|---------:|
| r8_full_wave     |      0.1316 |     0.2717 |      0.1937 |     0.3712 |     0.3944 |    0.009  |   0.0279 |    0.0178 |   0.0357 |   0.0511 |
| r2_small_platt7d |      0.1214 |     0.2678 |      0.1885 |     0.373  |     0.3948 |    0.0113 |   0.03   |    0.02   |   0.0411 |   0.0555 |
