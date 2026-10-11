"""@nebo_raketa: Kyiv-region radar channel, free text following drones and missiles over Kyiv city and oblast.

Posts are short and formulaic ("🛵 БпЛА на Бровари", "Наша область чиста", "Чабани, падає🔻", "💚 Відбій"), so
keyword groups are enough; no classifier. Each post becomes one event per matching group; `build_table` counts them
for the Kyiv city and Kyiv oblast rows only (group "nebo").
"""

import json
import re
from pathlib import Path

import pandas as pd

KYIV_REGIONS = ("kyiv", "kyivska")
EDIT_GRACE = pd.Timedelta(minutes=1)

# Kyiv city districts and neighbourhoods the channel names, plus "the capital".
CITY = (
    r"київ|києв|киян|столиц|оболонь|поділ|троєщин|троя|дарниц|лівий берег|позняк|осокорк|виноградар|святошин|"
    r"борщагівк|теремк|голосі|феофані|видубич|русанівк|березняк|дврз|харківський масив|південний міст|печерськ|"
    r"соломʼян|солом'ян|відрадн|нивк|біличі|пуща-водиц|берковец|лісовий|конча-засп|корчуват|жулян|чоколівк|сирец|"
    r"лук'янівк|лукʼянівк|куренівк|почайн|гідропарк|теличк|ретровіль|пріорк|рембаз|теці?-"
)
GROUPS = {
    "city": CITY,  # a threat named inside Kyiv city
    "new": r"🛵|бпла|шахед|курс|летит|летять|йде|йдуть|заходить|напрям|вектор",  # a drone tracked or announced
    "down": r"🔻|знижу|падає|на удар|йде на удар|пікіру",  # diving at a target
    "missile": r"балісти|ракет|кинджал|калібр|іскандер|ту-95|міг-31|х-101|крилат",
    "clear": r"чиста|чисто|не спостеріга|не фіксу|припинив існування|мінус|збит|відбій",
}
_PATTERNS = {g: re.compile(p) for g, p in GROUPS.items()}


def load_events(path: Path) -> pd.DataFrame:
    """Columns ts (UTC, ns) and group: one "post" row per post (overall activity) plus one row per matching group.

    The channel edits posts ("Upd. Наразі область чиста") and a scrape stores only the final text, so a post edited
    more than EDIT_GRACE after publishing counts from its last edit: the text is known to exist only from then.
    """
    rows = []
    with path.open() as f:
        for line in f:
            p = json.loads(line)
            ts = pd.Timestamp(p["date"])
            if p.get("edit_date") and pd.Timestamp(p["edit_date"]) - ts > EDIT_GRACE:
                ts = pd.Timestamp(p["edit_date"])
            text = (p["text"] or "").lower()
            rows.append((ts, "post"))
            rows += [(ts, g) for g, pat in _PATTERNS.items() if pat.search(text)]
    df = pd.DataFrame(rows, columns=["ts", "group"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.as_unit("ns")
    return df.sort_values("ts", kind="stable").reset_index(drop=True)
