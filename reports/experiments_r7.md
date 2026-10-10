# Experiments (dev window)

Dev test window: 14 days ending 2026-09-25 22:45 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r2_small_platt7d      |  0.276  |  0.1213 | 0.0294 | 0.8739 |     0.0329 |    0.0466 |      0.9365 |     0.9742 |     5263 |
| r7_full_radar         |  0.2734 |  0.1217 | 0.0322 | 0.8731 |     0.0324 |    0.0489 |      0.9346 |     0.9703 |     5395 |
| r7_time_history_radar |  0.2474 |  0.1262 | 0.043  | 0.865  |     0.0331 |    0.0564 |      0.9316 |     0.9728 |     5048 |

## All regions, per horizon

| predictor             |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:----------------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r2_small_platt7d      |     0.243  |      0.1758 |     0.3358 |     0.3492 |   0.0273 |    0.0184 |   0.0325 |   0.0394 |
| r7_full_radar         |     0.2416 |      0.175  |     0.3291 |     0.348  |   0.0297 |    0.0185 |   0.0376 |   0.0431 |
| r7_time_history_radar |     0.2157 |      0.1475 |     0.3058 |     0.3205 |   0.0393 |    0.0267 |   0.0491 |   0.0569 |

## Rear regions, averaged over horizons

| predictor             |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:----------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r2_small_platt7d      |  0.3013 |  0.1236 | 0.0432 | 0.8686 |     0.0396 |    0.0582 |      0.9329 |     0.9825 |     3528 |
| r7_full_radar         |  0.2974 |  0.1243 | 0.0465 | 0.8676 |     0.0385 |    0.0602 |      0.9313 |     0.9788 |     3643 |
| r7_time_history_radar |  0.268  |  0.1296 | 0.0586 | 0.8587 |     0.0388 |    0.069  |      0.9423 |     0.9724 |     3390 |

## Rear regions, per horizon

| predictor             |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:----------------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r2_small_platt7d      |     0.2584 |      0.1836 |     0.3689 |     0.3941 |   0.0347 |    0.0226 |   0.0496 |   0.0658 |
| r7_full_radar         |     0.256  |      0.1815 |     0.3615 |     0.3906 |   0.0378 |    0.0226 |   0.0557 |   0.0698 |
| r7_time_history_radar |     0.2266 |      0.1501 |     0.3355 |     0.3598 |   0.0476 |    0.0313 |   0.0693 |   0.0862 |
