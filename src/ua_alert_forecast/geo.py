"""Oblast adjacency, used for "neighbors under alert" features.

Written by hand from the map of Ukraine; symmetry is enforced by construction and checked in tests.
Kyiv city is treated as its own region inside Kyiv oblast.
"""

from .alerts import KYIV_CITY, OBLASTS

_BORDERS = {
    "vinnytska": ["zhytomyrska", "kyivska", "cherkaska", "kirovohradska", "odeska", "khmelnytska", "chernivetska"],
    "volynska": ["rivnenska", "lvivska"],
    "dnipropetrovska": ["poltavska", "kharkivska", "donetska", "zaporizka", "khersonska", "mykolaivska", "kirovohradska"],
    "donetska": ["kharkivska", "luhanska", "zaporizka"],
    "zhytomyrska": ["kyivska", "khmelnytska", "rivnenska"],
    "zakarpatska": ["lvivska", "ivano_frankivska"],
    "zaporizka": ["khersonska"],
    "ivano_frankivska": ["lvivska", "ternopilska", "chernivetska"],
    "kyivska": ["chernihivska", "poltavska", "cherkaska", KYIV_CITY],
    "kirovohradska": ["cherkaska", "poltavska", "mykolaivska", "odeska"],
    "luhanska": ["kharkivska"],
    "lvivska": ["rivnenska", "ternopilska"],
    "mykolaivska": ["odeska", "khersonska"],
    "poltavska": ["chernihivska", "sumska", "kharkivska", "cherkaska"],
    "rivnenska": ["ternopilska", "khmelnytska"],
    "sumska": ["chernihivska", "kharkivska"],
    "ternopilska": ["chernivetska", "khmelnytska"],
    "khmelnytska": ["chernivetska"],
}

REGIONS: list[str] = sorted([*OBLASTS.values(), KYIV_CITY])

NEIGHBORS: dict[str, list[str]] = {r: [] for r in REGIONS}
for _a, _bs in _BORDERS.items():
    for _b in _bs:
        NEIGHBORS[_a].append(_b)
        NEIGHBORS[_b].append(_a)
