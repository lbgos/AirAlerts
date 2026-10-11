"""Town-level radar tracks from the text channels: corridor rings around Kyiv and missile-carrier posts.

kpszsu / deraketaua / war_monitor write free-text tracks ("Реактивний БпЛА на Вінничині ... курс на Липовець"),
nebo_raketa names Kyiv districts and ring towns. From those posts two frames feed build_table:

- `corridor_events`: one row per post, the closest named place to Kyiv (city district or "Київ" = 0 km) and its
  weapon. The corridor-ring features the user asked for — minutes since a threat crossed 120/80/40 km toward
  the city — are recency features over mentions inside each ring.
- `carrier_events`: missile-carrier posts (MiG-31K take-offs, Tu-95/Tu-160 launches) with any expected arrival
  time the post states ("підліт ... 5:00", "ближче до 6.00").

Town names in these channels are capitalized ("реактивних БпЛА з Миколаївщини курсом на Вінничину"), so matching
is case-sensitive; that keeps the verb "хотів" (a thousand-plus lowercase hits) off the town "Хотів". Timestamps
follow nebo.py: a post edited more than a minute after publishing counts from its edit date, because the dump
stores only the final text, which existed from that moment.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .dataset import WINDOWS, count_before, min_before, minutes_since
from .kyiv import KYIV, PLACES, distance_km

CHANNELS = ["kpszsu", "deraketaua", "nebo_raketa", "war_monitor"]
EDIT_GRACE = pd.Timedelta(minutes=1)
NS_PER_MIN = 6e10
DIST_CAP = 400.0  # km; same "no threat near" sentinel as the kyiv features
ETA_NONE = 999.0  # minutes-to-arrival sentinel: no current stated arrival

# Approach-route towns the channels name and kyiv.PLACES does not have (names lowercased, apostrophes stripped).
EXTRA_TOWNS = {
    "ізяслав": (50.16, 26.81), "липовець": (49.23, 29.06), "жмеринка": (49.44, 28.11), "козятин": (49.73, 29.43),
    "бердичів": (49.89, 28.57), "хмільник": (49.56, 28.48), "старокостянтинів": (49.86, 27.35), "славута": (50.30, 26.87),
    "шепетівка": (50.18, 26.85), "дубно": (50.42, 25.74), "мізоч": (50.15, 26.37), "умань": (48.75, 30.22),
    "полтава": (49.59, 34.55), "лубни": (50.02, 32.30), "пирятин": (50.24, 32.49), "миргород": (49.97, 33.61),
    "гадяч": (49.87, 34.31), "кременчук": (49.07, 33.42), "ромни": (50.74, 33.48), "конотоп": (51.21, 33.06),
    "шостка": (51.87, 33.47), "ахтирка": (50.30, 34.90), "суми": (50.91, 34.80), "корюківка": (51.77, 32.25),
    "новгород-сіверський": (51.99, 33.26), "тараща": (49.56, 30.50), "сквира": (49.73, 29.67), "богуслав": (49.55, 30.88),
    "черкаси": (49.44, 32.06), "сміла": (49.23, 31.88), "канів": (49.75, 31.46), "золотоноша": (49.67, 32.04),
    "чернігів": (51.50, 31.29), "ніжин": (51.05, 31.89), "прилуки": (50.59, 32.39), "остер": (50.95, 30.88),
    "козелець": (50.91, 31.12), "ріпки": (51.81, 31.08), "сновськ": (51.82, 31.95), "бахмач": (51.18, 32.82),
    "семенівка": (52.18, 32.58),
}


def _norm(s: str) -> str:
    return s.lower().replace("ʼ", "'").replace("’", "'").replace("'", "")


def gazetteer() -> dict[str, tuple[float, float]]:
    """Lowercase name -> coordinates: kyiv.PLACES plus the extra route towns, plus "Київ" itself."""
    out = {name: c for name, c in EXTRA_TOWNS.items()}
    for (oblast, place), c in PLACES.items():
        out.setdefault(_norm(place), c)
    out["київ"] = KYIV
    return out


# Reuse nebo.py's Kyiv-city district vocabulary: any of these means a threat inside the city (distance 0).
CITY_RE = re.compile(r"київ|києв|киян|столиц|оболонь|поділ|троєщин|троя|дарниц|лівий берег|позняк|осокорк|"
                     r"виноградар|святошин|борщагівк|теремк|голосі|феофані|видубич|русанівк|березняк|дврз|"
                     r"харківський масив|південний міст|печерськ|солом.?ян|відрадн|нивк|біличі|пуща-водиц|берковец|"
                     r"лісовий|конча-засп|корчуват|жулян|чоколівк|сирец|лук.?янівк|куренівк|почайн|гідропарк|"
                     r"теличк|ретровіль|пріорк|рембаз|зазим")
DRONE_RE = re.compile(r"бпла|шахед|герань|дрон|жет")
MISSILE_RE = re.compile(r"ракет|баліст|кінджал|кинжал|іскандер|калібр|х-101|х-59|крилат|аеробалісти")
CLEAR_RE = re.compile(r"відбій|посадк|імітаци")  # all-clear / exercise notices that also name towns or carriers
CAR_RE = {"tu": re.compile(r"ту-95|ту-160|т-95|ту-22"), "mig": re.compile(r"міг-31|миг-31")}
# Arrival time parsed only where the wording announces a future approach ("Підліт до пускових рубежів 5:30",
# "ближче до 6.00", "очікуємо підліт ракет близько 11.30", the "Піліт" typo). A bare "близько 3.00 зафіксовано
# зліт" reports the past and must not set an arrival; the stated times are Kyiv local, rolled to the next morning.
ETA_TRIGGER_RE = re.compile(r"підліт|підльот|підтліт|піліт|подлет|ближче до|очікуємо|очікується|прибуття")
ETA_RE = re.compile(r"(\d{1,2})\s?[.,:h](\d{2})\b")


def load_posts(raw_dir: Path, channels: list[str] = CHANNELS) -> pd.DataFrame:
    """Channel posts as ts (UTC ns, edit-aware) and text, one row per non-empty post."""
    rows = []
    for ch in channels:
        path = raw_dir / f"{ch}.jsonl"
        if not path.exists():
            continue
        with path.open() as f:
            for line in f:
                p = json.loads(line)
                ts = pd.Timestamp(p["date"])
                ed = p.get("edit_date")
                if ed and pd.Timestamp(ed) - ts > EDIT_GRACE:
                    ts = pd.Timestamp(ed)
                text = p.get("text") or ""
                if text.strip():
                    rows.append((int(ts.value), text))
    return pd.DataFrame(rows, columns=["ts", "text"])


def corridor_events(posts: pd.DataFrame) -> pd.DataFrame:
    """Per post: ts, dist (closest named place to Kyiv; DIST_CAP if nothing named), towns (count), weapon."""
    towns = gazetteer()
    # Match places by a fixed stem (first 5 letters, invariant across Ukrainian suffixes: "Броварі",
    # "Броварському"); longer names first, so one stem can't shadow another.
    stems = sorted(towns.items(), key=lambda kv: len(kv[0]), reverse=True)
    entries = [(re.compile(rf"(?<![а-яїієґА-ЯЇІЄҐ]){re.escape(n[:5])}"), n, c) for n, c in stems]
    rows = []
    for ts, text in posts.itertuples(index=False):
        low = _norm(text)
        if CLEAR_RE.search(low):
            continue
        dists = [0.0] if CITY_RE.search(low) else []
        for pat, name, c in entries:
            if pat.search(low):
                dists.append(0.0 if c == KYIV else distance_km(c))
        if not dists:
            continue
        drone, missile = bool(DRONE_RE.search(low)), bool(MISSILE_RE.search(low))
        rows.append((ts, min(dists), len(dists), "drone" if drone and not missile else "missile" if missile else "other"))
    df = pd.DataFrame(rows, columns=["ts", "dist", "towns", "weapon"]).sort_values("ts", kind="stable")
    return df.reset_index(drop=True)


def carrier_events(posts: pd.DataFrame) -> pd.DataFrame:
    """Per carrier post: ts, kind (tu/mig), eta (UTC ns or nan — the arrival a post states, if any)."""
    rows = []
    for ts, text in posts.itertuples(index=False):
        low = _norm(text)
        if CLEAR_RE.search(low):
            continue
        kind = next((k for k, p in CAR_RE.items() if p.search(low)), None)
        if kind is None:
            continue
        eta = np.nan
        trigger = ETA_TRIGGER_RE.search(low)
        m = ETA_RE.search(low[trigger.start():]) if trigger else None
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            if hh < 24 and mm < 60:
                post = pd.Timestamp(ts, tz="UTC")
                local = post.tz_convert("Europe/Kyiv")
                eta = pd.Timestamp(local.year, local.month, local.day, hh, mm, tz="Europe/Kyiv").tz_convert("UTC").value
                if eta < post.value + 5 * NS_PER_MIN:  # an arrival stated around midnight belongs to the next morning
                    eta += 24 * 3600 * 10**9
                if eta < post.value:
                    eta = np.nan
        rows.append((ts, kind, eta))
    return pd.DataFrame(rows, columns=["ts", "kind", "eta"]).sort_values("ts", kind="stable").reset_index(drop=True)


# Regions the text-channel features apply to (the same Kyiv-city + oblast pair the nebo features cover).
REGIONS = ("kyiv", "kyivska")


def corridor_features(co: pd.DataFrame, t: np.ndarray) -> dict[str, np.ndarray]:
    """Group "corridor" (co_*): how recently the channels named anything at each distance ring around the city,
    and the minimum such distance over recent minutes. `t`: grid times, ns."""
    ts = co["ts"].to_numpy(np.int64)
    dist = co["dist"].to_numpy(float)
    drone, missile = co["weapon"].to_numpy() == "drone", co["weapon"].to_numpy() == "missile"
    f: dict[str, np.ndarray] = {}
    f["co_min_since"] = minutes_since(ts, t)
    f["co_posts_1h"] = count_before(ts, t, WINDOWS["1h"])
    for wname, w in {"15m": pd.Timedelta(minutes=15), "30m": WINDOWS["30m"], "1h": WINDOWS["1h"]}.items():
        f[f"co_min_dist_{wname}"] = min_before(ts, dist, t, w, DIST_CAP)
    f["co_min_dist_drone_30m"] = min_before(ts[drone], dist[drone], t, WINDOWS["30m"], DIST_CAP)
    f["co_min_dist_missile_30m"] = min_before(ts[missile], dist[missile], t, WINDOWS["30m"], DIST_CAP)
    for ring in (120, 80, 40):
        ring_ts = ts[dist <= ring]
        f[f"co_ring{ring}_min_since"] = minutes_since(ring_ts, t)
        f[f"co_ring{ring}_30m"] = count_before(ring_ts, t, WINDOWS["30m"])
    return f


def carrier_features(ca: pd.DataFrame, t: np.ndarray) -> dict[str, np.ndarray]:
    """Group "carrier" (ca_*): recency of carrier posts, and the arrival the most recent eta-bearing post still
    promises (minutes from t, clipped at 0 once the stated moment has come; ETA_NONE where there is none)."""
    ts = ca["ts"].to_numpy(np.int64)
    mig, tu = ts[ca["kind"].to_numpy() == "mig"], ts[ca["kind"].to_numpy() == "tu"]
    has_eta = np.isfinite(ca["eta"].to_numpy(float))
    eta_ts, eta_val = ts[has_eta], ca["eta"].to_numpy(float)[has_eta]
    f: dict[str, np.ndarray] = {
        "ca_min_since": minutes_since(ts, t),
        "ca_mig_min_since": minutes_since(mig, t),
        "ca_tu_min_since": minutes_since(tu, t),
        "ca_cnt_3h": count_before(ts, t, WINDOWS["3h"]),
        "ca_cnt_24h": count_before(ts, t, pd.Timedelta(hours=24)),
    }
    eta_min = np.full(len(t), ETA_NONE)
    if len(eta_ts):
        i = np.searchsorted(eta_ts, t, side="left") - 1  # most recent eta post strictly before t
        age = minutes_since(eta_ts, t, cap_minutes=12 * 60)  # cap 12 h: fine for the staleness check
        fresh = (i >= 0) & (age <= 12 * 60)
        overall = (eta_val[np.maximum(i, 0)] - t) / NS_PER_MIN
        eta_min = np.where(fresh, np.maximum(overall, 0.0), ETA_NONE)
    f["ca_eta_min"] = eta_min
    f["ca_eta_in_1h"] = (eta_min <= 60).astype(np.int64)  # ETA_NONE (999) never falls inside these windows
    f["ca_eta_in_3h"] = (eta_min <= 180).astype(np.int64)
    return f


def blank_features(features: dict[str, np.ndarray], t: np.ndarray) -> dict[str, np.ndarray]:
    """Same columns for regions outside Kyiv city/oblast: nothing recent, nothing near."""
    caps = {"min_since": 24 * 60.0, "min_dist": DIST_CAP, "eta_min": ETA_NONE}
    out = {}
    for k in features:
        cap = next((v for pat, v in caps.items() if pat in k), None)
        if cap is not None:
            out[k] = np.full(len(t), cap, dtype="float32")
        else:
            out[k] = np.zeros(len(t), dtype=np.int64)
    return out
