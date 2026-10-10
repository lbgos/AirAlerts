# @raketa_trevoga (user suggestion, 2026-10-10)

Radar-style channel, 481K subscribers. It deletes posts after about two days, so only 297 posts (2026-10-08 14:48 to
2026-10-10 14:47 UTC) could be scraped; there is no history to train on. Live mode now records it
(`COLLECT_CHANNELS` in `live.py`) so it can be tested as a feature once weeks of posts exist.

Labels: all 297 posts labeled by 3 Haiku 5.5 agents with `prompts/radar_labeling_v2.md` (`labels/raketa_v2/`).
Rule parser (`scripts/raketa_parse.py`: oblast headers, "N [реактивний] БпЛА [курсом] на X", oblast-centre targets)
vs those labels, oblasts per post: precision 0.993, recall 0.891.

## Lead time before siren episodes (`scripts/raketa_leadtime.py`)

Window 2026-10-08 15:48 to 2026-10-10 14:59 UTC, 369 siren episodes (region-level alert starts). Signal = anything in
the 60 minutes before the siren.

| signal in the 60 min before the siren | share of episodes | before first neighbor siren | only warning (no neighbor siren, no threat note) |
|:--|--:|--:|--:|
| neighbor siren | 0.959 | | |
| threat note in the alert channel | 0.312 | | |
| raketa_trevoga (Haiku labels) | 0.255 | 0.157 | 0.003 |
| kpszsu + deraketaua (local student) | 0.211 | 0.084 | 0.000 |

## All-clear

Rows under alert (15-minute grid): share of alerts ending within 30 minutes, by whether the channel named the oblast in
the previous 30 minutes.

| source | mentioned | rows | ends within 30 min |
|:--|:--|--:|--:|
| raketa_trevoga | no | 1076 | 0.332 |
| raketa_trevoga | yes | 874 | 0.318 |
| kpszsu + deraketaua | no | 1301 | 0.345 |
| kpszsu + deraketaua | yes | 649 | 0.287 |

Reading: raketa_trevoga warns earlier and more often than the other two radar channels (before the first neighbor siren
in 16% of episodes vs 8%), but a neighbor siren still precedes 96% of episodes. Two days is too little to train on;
worth retesting as a 15-30 minute feature after a few weeks of recording. For all-clear it carries almost no signal.
