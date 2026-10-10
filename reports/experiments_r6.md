# Experiments (dev window)

Dev test window: 14 days ending 2026-09-25 22:45 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor                     |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:------------------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r6_full_radar2                |  0.2764 |  0.1213 | 0.029  | 0.874  |     0.033  |    0.0475 |      0.9341 |     0.9731 |     5290 |
| r2_small_platt7d              |  0.276  |  0.1213 | 0.0294 | 0.8739 |     0.0329 |    0.0466 |      0.9365 |     0.9742 |     5263 |
| r4_time_history_threats_radar |  0.2548 |  0.1249 | 0.0359 | 0.8666 |     0.0344 |    0.0548 |      0.9342 |     0.9723 |     5172 |
| r6_time_history_radar2        |  0.2489 |  0.126  | 0.0361 | 0.8641 |     0.0347 |    0.0548 |      0.9328 |     0.9732 |     5141 |
| r4_time_history_threats       |  0.2389 |  0.1276 | 0.0416 | 0.8606 |     0.0373 |    0.0599 |      0.9363 |     0.9736 |     5036 |

## All regions, per horizon

| predictor                     |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:------------------------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r6_full_radar2                |     0.244  |      0.1792 |     0.3324 |     0.3501 |   0.028  |    0.018  |   0.0327 |   0.0375 |
| r2_small_platt7d              |     0.243  |      0.1758 |     0.3358 |     0.3492 |   0.0273 |    0.0184 |   0.0325 |   0.0394 |
| r4_time_history_threats_radar |     0.2244 |      0.1535 |     0.3156 |     0.3257 |   0.0357 |    0.0246 |   0.04   |   0.0432 |
| r6_time_history_radar2        |     0.218  |      0.1503 |     0.3066 |     0.3208 |   0.0351 |    0.0247 |   0.0399 |   0.0446 |
| r4_time_history_threats       |     0.2087 |      0.1352 |     0.2985 |     0.3134 |   0.0408 |    0.0288 |   0.0472 |   0.0496 |

## Rear regions, averaged over horizons

| predictor                     |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:------------------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r6_full_radar2                |  0.3019 |  0.1235 | 0.042  | 0.8687 |     0.0396 |    0.0591 |      0.9428 |     0.9714 |     3596 |
| r2_small_platt7d              |  0.3013 |  0.1236 | 0.0432 | 0.8686 |     0.0396 |    0.0582 |      0.9329 |     0.9825 |     3528 |
| r4_time_history_threats_radar |  0.2774 |  0.1278 | 0.0504 | 0.8597 |     0.041  |    0.0676 |      0.944  |     0.9725 |     3533 |
| r6_time_history_radar2        |  0.2722 |  0.1288 | 0.0512 | 0.8578 |     0.0413 |    0.0676 |      0.9437 |     0.9703 |     3481 |
| r4_time_history_threats       |  0.2613 |  0.1306 | 0.0589 | 0.8544 |     0.0444 |    0.0741 |      0.9468 |     0.9767 |     3324 |

## Rear regions, per horizon

| predictor                     |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:------------------------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r6_full_radar2                |     0.2588 |      0.1879 |     0.3648 |     0.3962 |   0.0349 |    0.0213 |   0.0486 |   0.0632 |
| r2_small_platt7d              |     0.2584 |      0.1836 |     0.3689 |     0.3941 |   0.0347 |    0.0226 |   0.0496 |   0.0658 |
| r4_time_history_threats_radar |     0.236  |      0.1563 |     0.3464 |     0.3708 |   0.0433 |    0.028  |   0.0594 |   0.0711 |
| r6_time_history_radar2        |     0.2309 |      0.1518 |     0.339  |     0.3671 |   0.0436 |    0.0287 |   0.0597 |   0.0728 |
| r4_time_history_threats       |     0.219  |      0.136  |     0.3312 |     0.3588 |   0.0506 |    0.034  |   0.0704 |   0.0807 |
