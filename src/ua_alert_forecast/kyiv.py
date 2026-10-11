"""Kyiv-specific geography for the Kyiv city forecast (feature group "kyiv", columns ky_*).

@UkraineAlarmSignal names the place of every event: sirens per raion ("Броварський район (Київська обл.)") and
threats per town ("🛸 Бровари"). The general features collapse these to the oblast. For Kyiv city the raions around it
and how close the named threat towns are carry the approach of a drone or missile, so they are kept here.

PLACES are rough coordinates (about 1-3 km) of the towns the channel names in Kyiv oblast and the neighbouring oblasts
on the approach routes, keyed by (oblast id, place as the channel writes it). Places not listed are ignored.
"""

import math

KYIV = (50.45, 30.52)

# The seven Kyiv-oblast raions, as the channel writes them -> short feature name.
RING_RAIONS = {
    "Вишгородський район": "vyshhorod",
    "Броварський район": "brovary",
    "Бориспільський район": "boryspil",
    "Обухівський район": "obukhiv",
    "Бучанський район": "bucha",
    "Фастівський район": "fastiv",
    "Білоцерківський район": "bilatserkva",
}

_KYIVSKA = {
    "Славутич": (51.52, 30.75), "Бровари": (50.51, 30.79), "Вишгород": (50.58, 30.49), "Васильків": (50.18, 30.32),
    "Бориспіль": (50.35, 30.95), "Обухів": (50.11, 30.62), "Вишневе": (50.39, 30.37), "Димер": (50.81, 30.31),
    "Гостомель": (50.57, 30.26), "Боярка": (50.32, 30.30), "Ірпінь": (50.52, 30.25), "Українка": (50.15, 30.74),
    "Біла Церква": (49.80, 30.12), "Переяслав": (50.07, 31.45), "Яготин": (50.24, 31.77), "Іванків": (50.93, 29.90),
    "Бородянка": (50.65, 29.92), "Буча": (50.55, 30.21), "Чабани": (50.34, 30.43), "Фастів": (50.08, 29.92),
    "Макарів": (50.46, 29.81), "Кагарлик": (49.87, 30.82), "Глеваха": (50.27, 30.30), "Згурівка": (50.50, 31.78),
    "Баришівка": (50.36, 31.32), "Ржищів": (49.97, 31.05), "Хотів": (50.33, 30.47), "Велика Димерка": (50.59, 30.91),
    "Богуслав": (49.55, 30.88), "Білогородка": (50.40, 30.22), "Миронівка": (49.66, 31.01), "Козин": (50.22, 30.65),
    "Гатне": (50.36, 30.43), "Ворзель": (50.54, 30.15), "Наливайківка": (50.51, 29.88), "Вишеньки": (50.30, 30.68),
    "Володарка": (49.52, 29.91), "Сквира": (49.73, 29.67), "Тараща": (49.56, 30.50), "Ставище": (49.39, 30.19),
    "Узин": (49.83, 30.43), "Рокитне": (49.69, 30.47), "Тетіїв": (49.37, 29.67), "Зазимʼя": (50.56, 30.66),
    "Березань": (50.31, 31.46), "Чорнобиль": (51.27, 30.22),
}
_CHERNIHIVSKA = {
    "Чернігів": (51.50, 31.29), "Городня": (51.89, 31.60), "Ніжин": (51.05, 31.89), "Сновськ": (51.82, 31.95),
    "Прилуки": (50.59, 32.39), "Ріпки": (51.81, 31.08), "Мена": (51.52, 32.21), "Семенівка": (52.18, 32.58),
    "Корюківка": (51.77, 32.25), "Короп": (51.57, 32.96), "Десна": (50.93, 30.75), "Новгород-Сіверський": (51.99, 33.26),
    "Бахмач": (51.18, 32.82), "Холми": (51.67, 32.67), "Сосниця": (51.52, 32.50), "Ічня": (50.86, 32.40),
    "Борзна": (51.25, 32.42), "Батурин": (51.34, 32.88), "Куликівка": (51.36, 31.65), "Гончарівське": (51.27, 31.33),
    "Козелець": (50.91, 31.12), "Бобровиця": (50.73, 31.38), "Любеч": (51.70, 30.66), "Носівка": (50.93, 31.58),
    "Остер": (50.95, 30.88),
}
_OTHER = {
    ("zhytomyrska", "Коростень"): (50.95, 28.64), ("zhytomyrska", "Овруч"): (51.32, 28.81),
    ("zhytomyrska", "Житомир"): (50.25, 28.66), ("zhytomyrska", "Малин"): (50.77, 29.24),
    ("zhytomyrska", "Радомишль"): (50.50, 29.23), ("cherkaska", "Черкаси"): (49.44, 32.06),
    ("cherkaska", "Сміла"): (49.23, 31.88), ("cherkaska", "Канів"): (49.75, 31.46),
    ("cherkaska", "Золотоноша"): (49.67, 32.04),
}
PLACES: dict[tuple[str, str], tuple[float, float]] = {
    **{("kyivska", p): c for p, c in _KYIVSKA.items()},
    **{("chernihivska", p): c for p, c in _CHERNIHIVSKA.items()},
    **_OTHER,
}


def distance_km(a: tuple[float, float], b: tuple[float, float] = KYIV) -> float:
    """Great-circle distance."""
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def distance_to_kyiv(oblast: str, place: str) -> float | None:
    """Distance of a threat place to Kyiv centre. Any place inside Kyiv city counts as 0; unknown places -> None."""
    if oblast == "kyiv":
        return 0.0
    c = PLACES.get((oblast, place))
    return distance_km(c) if c else None
