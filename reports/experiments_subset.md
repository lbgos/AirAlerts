# Experiments (dev window)

Dev test window: 14 days ending 2026-09-25 22:45 UTC. Final test window not used here.

skill = 1 - brier / brier(climatology), higher is better. ece = calibration error, lower is better.
low_* / high_*: mean predicted vs observed among forecasts below 10% / at or above 90%.

## Averaged over horizons

| predictor               |   skill |   brier |    ece |    auc |   low_pred |   low_obs |   high_pred |   high_obs |   n_high |
|:------------------------|--------:|--------:|-------:|-------:|-----------:|----------:|------------:|-----------:|---------:|
| r2_small_platt7d        |  0.276  |  0.1213 | 0.0294 | 0.8739 |     0.0329 |    0.0466 |      0.9365 |     0.9742 |     5263 |
| r5_no_national          |  0.2748 |  0.1216 | 0.0297 | 0.8741 |     0.0328 |    0.0514 |      0.9371 |     0.9723 |     5404 |
| r5_no_neighbors         |  0.2561 |  0.1246 | 0.0368 | 0.8661 |     0.0348 |    0.0517 |      0.9353 |     0.9737 |     5064 |
| r4_time_history_threats |  0.2389 |  0.1276 | 0.0416 | 0.8606 |     0.0373 |    0.0599 |      0.9363 |     0.9736 |     5036 |

## Per horizon

| predictor               |   skill_1h |   skill_30m |   skill_3h |   skill_6h |   ece_1h |   ece_30m |   ece_3h |   ece_6h |
|:------------------------|-----------:|------------:|-----------:|-----------:|---------:|----------:|---------:|---------:|
| r2_small_platt7d        |     0.243  |      0.1758 |     0.3358 |     0.3492 |   0.0273 |    0.0184 |   0.0325 |   0.0394 |
| r5_no_national          |     0.2451 |      0.1771 |     0.3339 |     0.3433 |   0.0279 |    0.0183 |   0.034  |   0.0384 |
| r5_no_neighbors         |     0.2252 |      0.1529 |     0.3159 |     0.3303 |   0.0365 |    0.0237 |   0.0413 |   0.0458 |
| r4_time_history_threats |     0.2087 |      0.1352 |     0.2985 |     0.3134 |   0.0408 |    0.0288 |   0.0472 |   0.0496 |
