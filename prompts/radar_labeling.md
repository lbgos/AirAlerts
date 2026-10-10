# Radar post labeling (teacher instructions)

Used once to label a sample of radar-channel posts (@kpszsu, @deraketaua). These labels train and
grade the local student classifier; the forecaster never sees them directly.

## Task

You get a chunk file: one JSON object per line with `channel`, `id`, `date`, `text`.
Lines with `"context_only": true` are the posts just before the chunk: read them for context, do not label them.
Label every other post by READING it. Do not write a keyword/regex classifier.

Write one output line per labeled post, same order:

```json
{"channel": "kpszsu", "id": 12345, "kind": "threat", "weapon": "shahed", "oblasts": ["poltavska"]}
```

## Fields

`kind`, exactly one of:
- `threat`: an aerial threat is reported: drones, missiles, KABs, aircraft/launch activity, with location, course or target.
- `shot_down`: something was destroyed/intercepted: "мінус", "збили", "збиття", "знищено", "📡❌".
- `impact`: explosions, hits, strikes reported ("вибухи", "влучання", "б'ють по ...").
- `all_clear`: the area is clear / threat over ("чисто", "відбій", "загроза минула").
- `other`: everything else: maps ("Карта ..."), summaries/statistics, ads, donations, channel promo, news, jokes.

`weapon` (for threat / shot_down / impact; `null` for all_clear / other):
- `shahed` (🛵, "шахед", "БпЛА", "мопед", "дрон") — regular attack drone
- `jet_drone` (🏍, "реактивний БпЛА", "реактивний шахед", "реактив")
- `missile` (🚀, "ракета", "КР", "балістика", "крилата", "Калібр", "Іскандер", "високошвидкісна ціль")
- `kab` (💣, "КАБ", "керовані авіабомби")
- `aviation` (✈️, "тактична авіація", "МіГ", "Ту-", "активність авіації")
- `recon_drone` ("розвідувальний БпЛА")
- `unknown` if the post doesn't say

`oblasts`: list of oblast ids where the object is now or is heading (course / target town). Map towns and raions
to their oblast from your knowledge ("курс на Липовець" -> vinnytska). Use `[]` if no place can be determined.
For a follow-up like "Мінус" or "Збили", take the place from the post it follows up on (earlier posts / context lines);
if that isn't clear, use `[]`.

Oblast ids: vinnytska volynska dnipropetrovska donetska zhytomyrska zakarpatska zaporizka ivano_frankivska kyivska
kirovohradska luhanska lvivska mykolaivska odeska poltavska rivnenska sumska ternopilska kharkivska khersonska
khmelnytska cherkaska chernivetska chernihivska, plus `kyiv` for Kyiv CITY (distinct from `kyivska`, Kyiv oblast).
Ignore places outside Ukrainian-controlled oblasts above (Crimea, Russia, Belarus, the sea) except as context.
Oblast name forms: "Київщина/на Київщині" kyivska, "Сумщина" sumska, "Харківщина" kharkivska, "Полтавщина" poltavska,
"Чернігівщина" chernihivska, "Дніпропетровщина/Дніпровщина" dnipropetrovska, "Запоріжжя/Запорізька" zaporizka,
"Херсонщина" khersonska, "Миколаївщина" mykolaivska, "Одещина" odeska, "Кіровоградщина/Кропивниччина" kirovohradska,
"Черкащина" cherkaska, "Вінниччина" vinnytska, "Житомирщина" zhytomyrska, "Рівненщина" rivnenska, "Волинь" volynska,
"Львівщина" lvivska, "Тернопільщина" ternopilska, "Хмельниччина" khmelnytska, "Прикарпаття/Франківщина" ivano_frankivska,
"Закарпаття" zakarpatska, "Буковина/Чернівеччина" chernivetska, "Донеччина" donetska.
