# Kyiv, 2026-09-27 07:55 to 2026-10-04 07:55 UTC (dev week), 15-minute forecast

Forecasts every 5 minutes. A siren (all-clear) is caught when the forecast was at the threshold or above at
some point in the 15 minutes before it. A false alarm is a stretch of forecasts at the threshold or above with
nothing happening within 15 minutes of any of them. Sirens/all-clears are counted on a 5-minute grid, so two
within the same 5 minutes count once.

| model                |                        |   events |   caught at 50%+ |   false alarms at 50%+ |   caught at 30%+ |   false alarms at 30%+ |
|:---------------------|:-----------------------|---------:|-----------------:|-----------------------:|-----------------:|-----------------------:|
| old (alert channel)  | siren, Kyiv city       |       60 |               14 |                      5 |               40 |                     33 |
| old (alert channel)  | siren, Kyiv oblast     |       57 |               20 |                      5 |               41 |                     17 |
| old (alert channel)  | all-clear, Kyiv city   |       61 |                2 |                      6 |               46 |                     40 |
| old (alert channel)  | all-clear, Kyiv oblast |       57 |                1 |                      4 |               28 |                     49 |
| new (+ @nebo_raketa) | siren, Kyiv city       |       60 |                0 |                      0 |               43 |                     37 |
| new (+ @nebo_raketa) | siren, Kyiv oblast     |       57 |                0 |                      0 |               40 |                     12 |
| new (+ @nebo_raketa) | all-clear, Kyiv city   |       61 |                6 |                     12 |               50 |                     49 |
| new (+ @nebo_raketa) | all-clear, Kyiv oblast |       57 |                2 |                      5 |               26 |                     62 |

Brier (lower is better) and points (gain over climatology per 100 forecasts, confident right x3, confident
wrong x10; higher is better):

| model                |                        |   brier |   brier climatology |   points |
|:---------------------|:-----------------------|--------:|--------------------:|---------:|
| old (alert channel)  | siren, Kyiv city       |  0.1097 |              0.1547 | 144.186  |
| old (alert channel)  | siren, Kyiv oblast     |  0.1705 |              0.2649 | 179.472  |
| old (alert channel)  | all-clear, Kyiv city   |  0.1526 |              0.1699 |  -3.8861 |
| old (alert channel)  | all-clear, Kyiv oblast |  0.1017 |              0.1056 |   3.7118 |
| new (+ @nebo_raketa) | siren, Kyiv city       |  0.1101 |              0.1547 |  99.2823 |
| new (+ @nebo_raketa) | siren, Kyiv oblast     |  0.1744 |              0.2649 | 161.948  |
| new (+ @nebo_raketa) | all-clear, Kyiv city   |  0.1542 |              0.1699 |  -4.648  |
| new (+ @nebo_raketa) | all-clear, Kyiv oblast |  0.1022 |              0.1056 |   6.9318 |
