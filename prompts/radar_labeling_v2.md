# Radar post labeling v2 (teacher instructions)

v2 of prompts/radar_labeling.md. Change: v1 merged "where the object is now" and "where it is heading" into one list and
dropped counts; v2 keeps them apart, because "heading to X before X has a siren" is the signal the forecaster needs.
Used once to label a sample; the labels train and grade the local student classifier.

## Task

You get a chunk file: one JSON object per line with `channel`, `id`, `date`, `text`.
Lines with `"context_only": true` are the posts just before the chunk: read them for context, do not label them.
Label every other post by READING it. Do not write a keyword/regex classifier; a small script only to write JSON is fine.

Write one output line per labeled post, same order:

```json
{"channel": "kpszsu", "id": 12345, "kind": "threat", "weapon": "shahed", "now_in": ["poltavska"], "heading_to": ["cherkaska"], "count": 2}
```

## Fields

`kind`, exactly one of:
- `threat`: an aerial threat is reported: drones, missiles, KABs, aircraft/launch activity, with location, course or target.
- `shot_down`: something was destroyed/intercepted: "мінус", "збили", "збиття", "знищено", "📡❌".
- `impact`: explosions, hits, strikes reported ("вибухи", "влучання", "б'ють по ...").
- `all_clear`: the area is clear / threat over ("чисто", "відбій", "загроза минула", "не спостерігається").
- `other`: everything else: maps ("Карта ...", "Ситуація ... станом на зараз" with no places), statistics/tallies
  ("ЗБИТО/ПОДАВЛЕНО ..."), ads, donations, channel promo, news, jokes.

`weapon` (for threat / shot_down / impact; `null` for all_clear / other):
- `shahed` (🛵, "шахед", "БпЛА", "мопед", "дрон", "Бандероль" = loitering munition) — regular attack drone
- `jet_drone` (🏍, "реактивний БпЛА", "реактивний шахед", "реактив")
- `missile` (🚀, "ракета", "КР", "балістика", "крилата", "Калібр", "Іскандер", "високошвидкісна ціль")
- `kab` (💣, "КАБ", "керовані авіабомби")
- `aviation` (✈️ as aircraft activity, "тактична авіація", "МіГ", "Ту-", "активність авіації")
- `recon_drone` ("розвідувальний БпЛА")
- `unknown` if the post doesn't say. A follow-up with no weapon named inherits the weapon of the thread it continues
  when the context makes that clear.

`now_in`: oblasts where the object IS now (or where the shot-down / impact / all-clear happened).
`heading_to`: oblasts the object is moving toward but is NOT in yet: "курсом на X", "у напрямку X", "на X" (as a target),
  "з Полтавщини на Черкащину" -> now_in poltavska, heading_to cherkaska. A target town inside the oblast it is already in
  goes to now_in, not heading_to ("на Київщині, курс на Бровари" -> now_in kyivska, heading_to []).
  If only a target is given with no current position ("Реактивний БпЛА на Козятин"), put the target's oblast in heading_to.
  Origins ("з Сумщини") go to neither unless the post says the object is still there.
`count`: number of objects if the post states it ("2 шахеди", "3х", "група з 5"), else null. "група"/"кілька" with no number -> null.

For follow-ups ("Мінус", "Збили", bare town names), take places from the thread they continue (context / earlier posts);
if unclear use []. Map towns/raions to oblasts from your knowledge; many Ukrainian place names exist in several oblasts:
use the surrounding context (oblast named nearby, direction of travel), and if still ambiguous use [] rather than guessing.

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
