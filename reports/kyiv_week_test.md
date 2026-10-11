# Kyiv, 2026-10-04 07:55 to 2026-10-11 07:55 UTC (test week), 15-minute forecast

Forecasts every 5 minutes. A siren (all-clear) is caught when the forecast was at the threshold or above at
some point in the 15 minutes before it. A false alarm is a stretch of forecasts at the threshold or above with
nothing happening within 15 minutes of any of them. Sirens/all-clears are counted on a 5-minute grid, so two
within the same 5 minutes count once.

| model                |                        |   events |   caught at 50%+ |   false alarms at 50%+ |   caught at 30%+ |   false alarms at 30%+ |
|:---------------------|:-----------------------|---------:|-----------------:|-----------------------:|-----------------:|-----------------------:|
| old (alert channel)  | siren, Kyiv city       |       45 |                6 |                      5 |               26 |                     42 |
| old (alert channel)  | siren, Kyiv oblast     |       54 |               21 |                      5 |               44 |                     16 |
| old (alert channel)  | all-clear, Kyiv city   |       45 |                3 |                      2 |               36 |                     24 |
| old (alert channel)  | all-clear, Kyiv oblast |       54 |                1 |                      2 |               22 |                     59 |
| new (+ @nebo_raketa) | siren, Kyiv city       |       45 |               15 |                     24 |               29 |                     58 |
| new (+ @nebo_raketa) | siren, Kyiv oblast     |       54 |               13 |                      2 |               34 |                     20 |
| new (+ @nebo_raketa) | all-clear, Kyiv city   |       45 |                3 |                      5 |               34 |                     41 |
| new (+ @nebo_raketa) | all-clear, Kyiv oblast |       54 |                2 |                      3 |               20 |                     65 |

Brier (lower is better) and points (gain over climatology per 100 forecasts, confident right x3, confident
wrong x10; higher is better):

| model                |                        |   brier |   brier climatology |   points |
|:---------------------|:-----------------------|--------:|--------------------:|---------:|
| old (alert channel)  | siren, Kyiv city       |  0.0872 |              0.0937 |  59.7914 |
| old (alert channel)  | siren, Kyiv oblast     |  0.1851 |              0.2999 | 150.052  |
| old (alert channel)  | all-clear, Kyiv city   |  0.166  |              0.1672 | -10.8375 |
| old (alert channel)  | all-clear, Kyiv oblast |  0.0974 |              0.0921 |  -6.4991 |
| new (+ @nebo_raketa) | siren, Kyiv city       |  0.0949 |              0.0937 |  46.0484 |
| new (+ @nebo_raketa) | siren, Kyiv oblast     |  0.1913 |              0.2999 | 166.025  |
| new (+ @nebo_raketa) | all-clear, Kyiv city   |  0.1666 |              0.1672 |  -3.2742 |
| new (+ @nebo_raketa) | all-clear, Kyiv oblast |  0.0989 |              0.0921 |  -9.2418 |
