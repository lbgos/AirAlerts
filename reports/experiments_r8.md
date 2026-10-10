# Experiments (dev window)

Dev test window: 14 days ending 2026-09-25 22:45 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.
rear = all regions except donetska, kharkivska, khersonska, luhanska, sumska, zaporizka.

## All regions, averaged over horizons

| predictor        |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:-----------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave     |  0.2775 |  0.1211 | 0.0265 | 0.8739 |     0.033  |    0.0448 |      0.938  |     0.9651 |     5252 |
| r2_small_platt7d |  0.276  |  0.1213 | 0.0294 | 0.8739 |     0.0329 |    0.0466 |      0.9365 |     0.9742 |     5263 |

## All regions, per horizon

| predictor        |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:-----------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r8_full_wave     |     0.2455 |      0.1808 |     0.3344 |     0.3494 |   0.0259 |    0.016  |   0.0284 |   0.0359 |
| r2_small_platt7d |     0.243  |      0.1758 |     0.3358 |     0.3492 |   0.0273 |    0.0184 |   0.0325 |   0.0394 |

## Rear regions, averaged over horizons

| predictor        |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:-----------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r8_full_wave     |  0.3036 |  0.1232 | 0.0399 | 0.8688 |     0.0399 |    0.0562 |      0.932  |     0.9521 |     3512 |
| r2_small_platt7d |  0.3013 |  0.1236 | 0.0432 | 0.8686 |     0.0396 |    0.0582 |      0.9329 |     0.9825 |     3528 |

## Rear regions, per horizon

| predictor        |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:-----------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r8_full_wave     |     0.2614 |      0.189  |     0.369  |     0.395  |   0.0331 |    0.0207 |   0.0448 |   0.061  |
| r2_small_platt7d |     0.2584 |      0.1836 |     0.3689 |     0.3941 |   0.0347 |    0.0226 |   0.0496 |   0.0658 |
