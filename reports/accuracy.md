# How often the forecast was right (final-test window, last 14 days)

Right = said 50% or more and it happened, or under 50% and it did not.

|                        | 15m   | 30m   | 1h   | 3h   | 6h   |
|:-----------------------|:------|:------|:-----|:-----|:-----|
| siren, all oblasts     | 92%   | 87%   | 81%  | 82%  | 84%  |
| siren, Kyiv city       | 87%   | 76%   | 61%  | 74%  | 82%  |
| siren, Kyiv oblast     | 73%   | 61%   | 78%  | 98%  | 100% |
| all-clear, all oblasts | 87%   | 78%   | 74%  | 78%  | 85%  |
| all-clear, Kyiv city   | 82%   | 66%   | 54%  | 85%  | 96%  |
| all-clear, Kyiv oblast | 89%   | 80%   | 66%  | 67%  | 88%  |

## 15 minutes in detail

it happened: share of 15-minute windows with a siren (all-clear). caught: share of those that had a 30%+ forecast.

|                        | it happened   | said 30%+: came true   | caught at 30%+   | said under 10%: came true   |
|:-----------------------|:--------------|:-----------------------|:-----------------|:----------------------------|
| siren, all oblasts     | 8%            | 42%                    | 38%              | 1%                          |
| siren, Kyiv city       | 13%           | 39%                    | 49%              | 4%                          |
| siren, Kyiv oblast     | 30%           | 49%                    | 58%              | 3%                          |
| all-clear, all oblasts | 13%           | 31%                    | 46%              | 3%                          |
| all-clear, Kyiv city   | 18%           | 23%                    | 68%              | 9%                          |
| all-clear, Kyiv oblast | 10%           | 23%                    | 33%              | 4%                          |
