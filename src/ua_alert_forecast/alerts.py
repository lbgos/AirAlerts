"""Parse @UkraineAlarmSignal posts into per-oblast alert events.

Every place in a post carries an explicit oblast tag like "(Полтавська обл.)" or "(Київ)",
so oblast mapping is an exact lookup on the tag, never a substring search over place names.
The same parser runs on scraped history and on live posts.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# Oblast tag adjective -> id. Kyiv city is separate from Kyiv oblast.
OBLASTS = {
    "Вінницька": "vinnytska",
    "Волинська": "volynska",
    "Дніпропетровська": "dnipropetrovska",
    "Донецька": "donetska",
    "Житомирська": "zhytomyrska",
    "Закарпатська": "zakarpatska",
    "Запорізька": "zaporizka",
    "Івано-Франківська": "ivano_frankivska",
    "Київська": "kyivska",
    "Кіровоградська": "kirovohradska",
    "Луганська": "luhanska",
    "Львівська": "lvivska",
    "Миколаївська": "mykolaivska",
    "Одеська": "odeska",
    "Полтавська": "poltavska",
    "Рівненська": "rivnenska",
    "Сумська": "sumska",
    "Тернопільська": "ternopilska",
    "Харківська": "kharkivska",
    "Херсонська": "khersonska",
    "Хмельницька": "khmelnytska",
    "Черкаська": "cherkaska",
    "Чернівецька": "chernivetska",
    "Чернігівська": "chernihivska",
}
KYIV_CITY = "kyiv"

EventKind = Literal["start", "end", "threat"]

# Section emoji -> (kind, detail). Detail is the alert level for starts, the threat type for threats.
SECTION_KINDS: dict[str, tuple[EventKind, str]] = {
    "🔴": ("start", "red"),
    "🟡": ("start", "yellow"),
    "🚨": ("start", "air"),  # pre-reform format (before the 2026-09 yellow/red levels)
    "🟢": ("end", ""),
    "🛸": ("threat", "drone"),
    "💣": ("threat", "kab"),
    "🚀": ("threat", "high_speed"),
    "💥": ("threat", "shelling"),
    "⚠️": ("threat", "explosions"),
    "👁️": ("threat", "recon"),
    "✈️": ("threat", "aviation"),
}

OBLAST_TAG = re.compile(r"([А-ЯІЇЄҐ][а-яіїєґ'’ʼ]+(?:-[А-ЯІЇЄҐ][а-яіїєґ'’ʼ]+)?) обл\.")
PLACE = re.compile(r"^(?P<place>.*?)\s*\((?P<tag>[^)]*)\)\s*$")


@dataclass(frozen=True)
class AlertEvent:
    ts: datetime
    kind: EventKind
    detail: str
    oblast: str
    place: str


def oblast_of(tag: str) -> str | None:
    """Map a place's parenthesised tag (or a bare header like "Київ") to an oblast id."""
    if m := OBLAST_TAG.search(tag):
        return OBLASTS.get(m.group(1))
    return KYIV_CITY if tag.strip() == "Київ" else None


def parse_place(line: str) -> tuple[str, str] | None:
    """"Сумський район (Сумська обл.)" -> ("Сумський район", "sumska")."""
    line = line.lstrip("•-– ").strip()
    if m := PLACE.match(line):
        oblast = oblast_of(m.group("tag"))
        return (m.group("place"), oblast) if oblast else None
    # Untagged forms, whole line only: "Київ" or an oblast-wide "Харківська обл."
    if line == "Київ" or OBLAST_TAG.fullmatch(line):
        return line, oblast_of(line)
    return None


def parse_post(text: str, ts: datetime) -> list[AlertEvent]:
    """All alert events in one post. Summary posts and unknown formats yield nothing."""
    if text.startswith("Мапа тривог"):
        return []
    events = []
    for section in re.split(r"\n\s*\n", text.strip()):
        emoji = next((e for e in SECTION_KINDS if section.startswith(e)), None)
        if emoji is None:
            continue
        kind, detail = SECTION_KINDS[emoji]
        # "Відбій червоної тривоги, жовта тривога ще триває": a downgrade of an ongoing alert, not a new start.
        if kind == "start" and "Відбій червоної" in section:
            continue
        header, *rest = section.split("\n")
        header = header.removeprefix(emoji).strip()
        # List posts put one place per line, with "•" (current format) or without (pre-reform).
        # Message body lines ("Повітряна тривога. Прямуйте в укриття!") carry no tag and are skipped.
        for line in [header, *rest]:
            if parsed := parse_place(line):
                place, oblast = parsed
                events.append(AlertEvent(ts, kind, detail, oblast, place))
    return events
