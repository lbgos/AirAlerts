# Accuracy on the final-test window (last 14 days)

accuracy = share of forecasts on the right side of 50% (>= 50% and it happened, or < 50% and it did not).
baseline = always give the more common answer (e.g. "no siren"), which is why plain accuracy looks high.
confident = forecasts below 20% or above 80%: share of all forecasts, and how often those were right.

## Siren starts (oblast not under alert)

|             | 15m                                                 | 30m                                                 | 1h                                                  | 3h                                                  | 6h                                                   |
|:------------|:----------------------------------------------------|:----------------------------------------------------|:----------------------------------------------------|:----------------------------------------------------|:-----------------------------------------------------|
| all oblasts | 92% (base 92%) · confident 86%, right 96% · n=22381 | 87% (base 86%) · confident 71%, right 95% · n=22368 | 81% (base 77%) · confident 61%, right 93% · n=22342 | 81% (base 58%) · confident 65%, right 90% · n=22201 | 84% (base 53%) · confident 71%, right 92% · n=22009  |
| Kyiv city   | 88% (base 88%) · confident 79%, right 93% · n=887   | 77% (base 77%) · confident 55%, right 87% · n=887   | 64% (base 60%) · confident 20%, right 78% · n=887   | 71% (base 73%) · confident 40%, right 85% · n=883   | 83% (base 87%) · confident 64%, right 93% · n=874    |
| Kyiv oblast | 75% (base 74%) · confident 52%, right 83% · n=458   | 65% (base 53%) · confident 19%, right 78% · n=458   | 70% (base 69%) · confident 14%, right 84% · n=458   | 95% (base 95%) · confident 68%, right 94% · n=455   | 100% (base 100%) · confident 96%, right 100% · n=455 |

## All-clear (oblast under alert)

|             | 15m                                                 | 30m                                                 | 1h                                                  | 3h                                                    | 6h                                                    |
|:------------|:----------------------------------------------------|:----------------------------------------------------|:----------------------------------------------------|:------------------------------------------------------|:------------------------------------------------------|
| all oblasts | 84% (base 83%) · confident 68%, right 90% · n=11293 | 72% (base 69%) · confident 34%, right 87% · n=11284 | 67% (base 51%) · confident 15%, right 89% · n=11259 | 88% (base 88%) · confident 74%, right 94% · n=11161   | 98% (base 98%) · confident 100%, right 98% · n=11054  |
| Kyiv city   | 81% (base 79%) · confident 23%, right 88% · n=464   | 62% (base 63%) · confident 7%, right 97% · n=463    | 61% (base 60%) · confident 15%, right 99% · n=461   | 100% (base 100%) · confident 100%, right 100% · n=457 | 100% (base 100%) · confident 100%, right 100% · n=449 |
| Kyiv oblast | 88% (base 87%) · confident 73%, right 92% · n=891   | 79% (base 76%) · confident 19%, right 92% · n=890   | 66% (base 57%) · confident 7%, right 95% · n=888    | 87% (base 87%) · confident 95%, right 89% · n=882     | 99% (base 99%) · confident 100%, right 99% · n=873    |
