"""Turn parsed alert events into a training table: one row per (region, forecast time T).

Leakage rule: every feature for time T uses only events with ts < T. Labels look at (T, T + horizon].
Rows where the region is already under alert at T are dropped: "will a siren start" is undefined then,
and the UI shows "alert active now" instead.
"""

import json
from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from .alerts import KYIV_CITY, parse_post
from .geo import NEIGHBORS, REGIONS, RING2
from .kyiv import RING_RAIONS, distance_to_kyiv
from .nebo import GROUPS as NEBO_GROUPS
from .nebo import KYIV_REGIONS as NEBO_REGIONS

Horizon = Literal["15m", "30m", "1h", "3h", "6h"]
HORIZONS: dict[Horizon, pd.Timedelta] = {
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "3h": pd.Timedelta(hours=3),
    "6h": pd.Timedelta(hours=6),
}
STEP = pd.Timedelta(minutes=15)
# A place stays under alert until the channel posts its all-clear. This is only a safety net for lost posts: in the
# last 60 days just 26 alerts never got an all-clear post, while 14% of real alerts lasted over 3 h and 5.5% over 6 h
# (the earlier 3 h rule cut those short and showed oblasts as clear during long alerts).
ALERT_EXPIRY = timedelta(hours=24)
THREAT_GROUPS = {"drone": ["drone"], "kab": ["kab"], "missile": ["high_speed"], "other": ["shelling", "explosions", "recon", "aviation"]}
WINDOWS = {"30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1), "3h": pd.Timedelta(hours=3)}
RECENT = pd.Timedelta(minutes=10)  # window of the last-minutes features (group "recent"), aimed at the 15m horizon


def events_from_posts(posts: Iterable[dict]) -> pd.DataFrame:
    """Parse raw posts ({"date", "text", ...} as saved by the scraper) into a sorted event table."""
    rows = [e.__dict__ for post in posts for e in parse_post(post["text"], pd.Timestamp(post["date"]).to_pydatetime())]
    df = pd.DataFrame(rows, columns=["ts", "kind", "detail", "oblast", "place"])
    # pandas 3 defaults to microseconds; everything here works in int64 nanoseconds (Timestamp.value).
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.as_unit("ns")
    return df.sort_values("ts", kind="stable").reset_index(drop=True)


def load_events(path: Path) -> pd.DataFrame:
    """Parse a raw channel dump (data/raw/<channel>.jsonl) into a sorted event table."""
    with path.open() as f:
        return events_from_posts(json.loads(line) for line in f)


def alert_intervals(events: pd.DataFrame, by_place: bool = False) -> dict:
    """Per region, disjoint sorted [start, end) intervals (int64 ns) when any place in it was under alert.
    With `by_place`, the same per (region, place) instead, for places that ever had a siren.

    Places open on a start event and close on an end event for the same place, or after ALERT_EXPIRY.
    """
    open_at: dict[tuple[str, str], pd.Timestamp] = {}
    spans: dict = {} if by_place else {r: [] for r in REGIONS}

    def close(key: tuple[str, str], end: pd.Timestamp) -> None:
        start = open_at.pop(key)
        spans.setdefault(key if by_place else key[0], []).append((start.value, min(end, start + ALERT_EXPIRY).value))

    for ev in events[events["kind"].isin(["start", "end"])].itertuples():
        key = (ev.oblast, ev.place)
        if key in open_at and ev.ts - open_at[key] > ALERT_EXPIRY:
            close(key, ev.ts)
        if ev.kind == "start":
            open_at.setdefault(key, ev.ts)
        elif key in open_at:
            close(key, ev.ts)
    for key in list(open_at):
        close(key, open_at[key] + ALERT_EXPIRY)

    merged = {}
    for region, ss in spans.items():
        out: list[list[int]] = []
        for s, e in sorted(ss):
            if out and s <= out[-1][1]:
                out[-1][1] = max(out[-1][1], e)
            else:
                out.append([s, e])
        merged[region] = np.array(out, dtype=np.int64).reshape(-1, 2)
    return merged


def is_active(intervals: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Vectorised "is t inside one of the disjoint sorted intervals"."""
    if len(intervals) == 0:
        return np.zeros(len(t), dtype=bool)
    i = np.searchsorted(intervals[:, 0], t, side="left") - 1  # only alerts that started strictly before t
    return (i >= 0) & (t <= intervals[np.maximum(i, 0), 1])  # an end at exactly t is not known yet


def count_before(times: np.ndarray, t: np.ndarray, window: pd.Timedelta) -> np.ndarray:
    """Number of event times in [t - window, t), for each t. `times` must be sorted int64 ns."""
    return np.searchsorted(times, t, side="left") - np.searchsorted(times, t - window.value, side="left")


def minutes_since(times: np.ndarray, t: np.ndarray, cap_minutes: float = 24 * 60.0) -> np.ndarray:
    if len(times) == 0:
        return np.full(len(t), cap_minutes)
    i = np.searchsorted(times, t, side="left") - 1
    last = np.where(i >= 0, times[np.maximum(i, 0)], np.iinfo(np.int64).min // 2)
    return np.minimum((t - last) / 6e10, cap_minutes)


def sum_before(times: np.ndarray, weights: np.ndarray, t: np.ndarray, window: pd.Timedelta) -> np.ndarray:
    """Sum of weights of events in [t - window, t). `times` sorted int64 ns, `weights` aligned with it."""
    cs = np.concatenate([[0.0], np.cumsum(weights)])
    return cs[np.searchsorted(times, t, side="left")] - cs[np.searchsorted(times, t - window.value, side="left")]


def min_before(times: np.ndarray, values: np.ndarray, t: np.ndarray, window: pd.Timedelta, empty: float, lag_minutes: int = 0) -> np.ndarray:
    """Smallest value among events in [t - lag - window, t - lag), `empty` where there are none. `times` sorted int64 ns."""
    end = t - pd.Timedelta(minutes=lag_minutes).value
    lo = np.searchsorted(times, end - window.value, side="left")
    hi = np.searchsorted(times, end, side="left")
    vals = np.append(values, empty)  # reduceat indices may equal len(values)
    out = np.minimum.reduceat(vals, np.ravel(np.column_stack([lo, hi])))[::2]
    return np.where(hi > lo, out, empty)


# 2026-09-06 the channel switched from one air alert to yellow/red levels (first 🔴 at 01:00 UTC); siren habits
# changed with it (Kyiv city starts per month jumped), so the "regime" group flags rows after it.
REFORM = pd.Timestamp("2026-09-06T00:00Z")
DIST_CAP = 400.0  # km; "no threat near Kyiv"


def kyiv_features(events: pd.DataFrame, t: np.ndarray) -> dict[str, np.ndarray]:
    """Group "kyiv" (ky_*), for the Kyiv city rows: sirens in the seven Kyiv-oblast raions, and how close to Kyiv the
    threats named in the last minutes are (towns in kyiv.PLACES; any place inside the city = 0 km) and whether they come closer.
    """
    raion_iv = alert_intervals(events[events["oblast"] == "kyivska"], by_place=True)
    f: dict[str, np.ndarray] = {}
    ring_starts = []
    for raion, name in RING_RAIONS.items():
        iv = raion_iv.get(("kyivska", raion), np.empty((0, 2), dtype=np.int64))
        st = np.sort(events.loc[(events["kind"] == "start") & (events["oblast"] == "kyivska") & (events["place"] == raion), "ts"]
                     .to_numpy(dtype="datetime64[ns]").astype(np.int64))
        ring_starts.append(st)
        f[f"ky_{name}_active"] = is_active(iv, t).astype(np.int64)
        f[f"ky_{name}_min_since_start"] = minutes_since(st, t)
    all_ring = np.sort(np.concatenate(ring_starts))
    f["ky_ring_active"] = np.sum([f[f"ky_{n}_active"] for n in RING_RAIONS.values()], axis=0)
    f["ky_ring_min_since_start"] = minutes_since(all_ring, t)
    for wname, w in {"10m": RECENT, "30m": WINDOWS["30m"]}.items():
        f[f"ky_ring_starts_{wname}"] = count_before(all_ring, t, w)

    thr = events[events["kind"] == "threat"]
    dist = np.array([d if (d := distance_to_kyiv(o, p)) is not None else np.nan for o, p in zip(thr["oblast"], thr["place"])], dtype=float)
    known = ~np.isnan(dist)
    ts = thr["ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64)[known]
    dist, detail = dist[known], thr["detail"].to_numpy()[known]
    order = np.argsort(ts, kind="stable")
    ts, dist, detail = ts[order], dist[order], detail[order]
    for wname, w in {"10m": RECENT, "30m": WINDOWS["30m"], "1h": WINDOWS["1h"]}.items():
        f[f"ky_dist_min_{wname}"] = min_before(ts, dist, t, w, DIST_CAP)
    for g, kinds in (("drone", ["drone"]), ("missile", ["high_speed"])):
        m = np.isin(detail, kinds)
        f[f"ky_dist_{g}_30m"] = min_before(ts[m], dist[m], t, WINDOWS["30m"], DIST_CAP)
    for km in (30, 60):
        near = ts[dist <= km]
        f[f"ky_near{km}_15m"] = count_before(near, t, pd.Timedelta(minutes=15))
        f[f"ky_near{km}_30m"] = count_before(near, t, WINDOWS["30m"])
    # Approach: nearest threat in the last 15 min minus nearest in the 45 min before (negative = coming closer).
    f["ky_dist_trend"] = min_before(ts, dist, t, pd.Timedelta(minutes=15), DIST_CAP) - min_before(
        ts, dist, t, pd.Timedelta(minutes=45), DIST_CAP, lag_minutes=15)
    return f


def kyiv_features_blank(f: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """The same columns for the other regions: nothing near, nothing active."""
    def blank(name: str, a: np.ndarray) -> np.ndarray:
        if "min_since" in name:
            return np.full(len(a), 24 * 60.0)
        if "_dist_" in name and not name.endswith("trend"):
            return np.full(len(a), DIST_CAP)
        return np.zeros(len(a), dtype=a.dtype)
    return {k: blank(k, v) for k, v in f.items()}


# Radar-channel events (student classifier output) grouped like the alert-channel threats.
RADAR_GROUPS = {"drone": ["shahed", "jet_drone", "recon_drone"], "missile": ["missile"], "kab": ["kab"], "aviation": ["aviation"]}
RADAR_WINDOWS = {"30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1)}
RADAR_NATIONAL_WINDOWS = {"1h": pd.Timedelta(hours=1), "3h": pd.Timedelta(hours=3)}


def build_table(
    events: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    radar: pd.DataFrame | None = None,
    grid: pd.DatetimeIndex | None = None,
    keep_active: bool = False,
    step: pd.Timedelta = STEP,
    nebo: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Feature + label table on a grid of `step` (default 15 minutes) in [start, end). Labels need data up to end + 6h.

    Live mode passes `grid` (the forecast times, e.g. just "now") and `keep_active=True` to get an `active`
    column instead of dropping regions already under alert.

    `nebo` (optional): output of `nebo.load_events`, counted for the Kyiv city and Kyiv oblast rows (zero elsewhere).

    `radar` (optional): output of `radar.to_events` (rows per post, role and oblast, with weights). Role "heading_to" is where an object is going but not yet: the direction signal that
    neighbor sirens don't carry.
    """
    if grid is None:
        grid = pd.date_range(start.ceil(step), end, freq=step, inclusive="left", tz="UTC", unit="ns")
    t = grid.asi8
    intervals = alert_intervals(events)
    active = {r: is_active(intervals[r], t) for r in REGIONS}

    def times(mask: pd.Series) -> np.ndarray:
        return np.sort(events.loc[mask, "ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64))

    starts = {r: times((events["kind"] == "start") & (events["oblast"] == r)) for r in REGIONS}
    threats = {
        (r, g): times((events["kind"] == "threat") & (events["oblast"] == r) & events["detail"].isin(kinds))
        for r in REGIONS
        for g, kinds in THREAT_GROUPS.items()
    }
    ends = {r: times((events["kind"] == "end") & (events["oblast"] == r)) for r in REGIONS}
    any_threats = {r: times((events["kind"] == "threat") & (events["oblast"] == r)) for r in REGIONS}
    all_threats = times(events["kind"] == "threat")
    active_15m_ago = {r: is_active(intervals[r], t - pd.Timedelta(minutes=15).value) for r in REGIONS}
    all_ends = times(events["kind"] == "end")
    all_starts = times(events["kind"] == "start")
    all_drones = times((events["kind"] == "threat") & (events["detail"] == "drone"))
    national_active = np.sum([active[r] for r in REGIONS], axis=0)
    data_end = events["ts"].max().value

    def radar_series(mask: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        sel = radar[mask].sort_values("ts", kind="stable")
        return sel["ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64), sel["weight"].to_numpy(dtype=float)

    roles = {"now": "now_in", "head": "heading_to"}
    if radar is not None:
        radar_threat = {
            (r, role, g): radar_series(
                (radar["kind"] == "threat") & (radar["oblast"] == r) & (radar["role"] == rname) & radar["weapon"].isin(ws)
            )
            for r in REGIONS
            for role, rname in roles.items()
            for g, ws in RADAR_GROUPS.items()
        }
        radar_down = {r: radar_series((radar["kind"] == "shot_down") & (radar["oblast"] == r))[0] for r in REGIONS}
        radar_clear = {r: radar_series((radar["kind"] == "all_clear") & (radar["oblast"] == r))[0] for r in REGIONS}
        radar_impact = {r: radar_series((radar["kind"] == "impact") & (radar["oblast"] == r))[0] for r in REGIONS}
        # Country-wide threat posts per weapon group, counted once per post whether or not it names an oblast.
        radar_national = {
            (g, wname): count_before(radar_series((radar["role"] == "post") & (radar["kind"] == "threat") & radar["weapon"].isin(ws))[0], t, w)
            for g, ws in RADAR_GROUPS.items()
            for wname, w in RADAR_NATIONAL_WINDOWS.items()
        }

    if nebo is not None:
        nebo_times = {g: np.sort(nebo.loc[nebo["group"] == g, "ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64)) for g in ("post", *NEBO_GROUPS)}

    ky = kyiv_features(events, t)
    ky_blank = kyiv_features_blank(ky)

    kyiv_time = grid.tz_convert("Europe/Kyiv")
    frames = []
    for r in REGIONS:
        nb = NEIGHBORS[r]
        f: dict[str, np.ndarray] = {
            "ts": t,
            "region": np.full(len(t), r),
            "active": active[r],
            "hour": kyiv_time.hour.to_numpy() + kyiv_time.minute.to_numpy() / 60,
            "weekday": kyiv_time.weekday.to_numpy(),
            "reform": (t >= REFORM.value).astype(np.int64),
            "min_since_start": minutes_since(starts[r], t),
            "starts_24h": count_before(starts[r], t, pd.Timedelta(hours=24)),
            "nb_active": np.sum([active[n] for n in nb], axis=0) if nb else np.zeros(len(t)),
            "national_active": national_active,
            "national_starts_1h": count_before(all_starts, t, pd.Timedelta(hours=1)),
            "national_drones_1h": count_before(all_drones, t, pd.Timedelta(hours=1)),
        }
        for g in THREAT_GROUPS:
            for wname, w in WINDOWS.items():
                f[f"{g}_{wname}"] = count_before(threats[(r, g)], t, w)
                f[f"nb_{g}_{wname}"] = np.sum([count_before(threats[(n, g)], t, w) for n in nb], axis=0) if nb else 0
        # Alert-wave timing: how recently the nearest siren started next door, and what the second ring is doing.
        ring2 = RING2[r]
        f["wave_nb_min_since_start"] = np.min([minutes_since(starts[n], t) for n in nb], axis=0) if nb else np.full(len(t), 24 * 60.0)
        f["wave_ring2_active"] = np.sum([active[n] for n in ring2], axis=0) if ring2 else np.zeros(len(t))
        for wname in ("1h", "3h"):
            f[f"wave_ring2_starts_{wname}"] = np.sum([count_before(starts[n], t, WINDOWS[wname]) for n in ring2], axis=0) if ring2 else 0
        for wname, w in WINDOWS.items():
            f[f"nb_starts_{wname}"] = np.sum([count_before(starts[n], t, w) for n in nb], axis=0) if nb else 0
        # Last minutes, for the 15m horizon: how fresh the latest threat note / all-clear is here and next door,
        # what happened in the last 10 minutes, and which neighbors went under alert in the last 15.
        def nb_min(series: dict[str, np.ndarray]) -> np.ndarray:
            return np.min([minutes_since(series[n], t) for n in nb], axis=0) if nb else np.full(len(t), 24 * 60.0)

        f["rc_min_since_threat"] = minutes_since(any_threats[r], t)
        f["rc_nb_min_since_threat"] = nb_min(any_threats)
        for g in ("drone", "kab", "missile"):
            f[f"rc_min_since_{g}"] = minutes_since(threats[(r, g)], t)
            f[f"rc_nb_min_since_{g}"] = nb_min({n: threats[(n, g)] for n in nb})
        f["rc_min_since_end"] = minutes_since(ends[r], t)
        f["rc_nb_min_since_end"] = nb_min(ends)
        f["rc_threats_10m"] = count_before(any_threats[r], t, RECENT)
        f["rc_nb_threats_10m"] = np.sum([count_before(any_threats[n], t, RECENT) for n in nb], axis=0) if nb else 0
        f["rc_nb_starts_10m"] = np.sum([count_before(starts[n], t, RECENT) for n in nb], axis=0) if nb else 0
        f["rc_ring2_starts_10m"] = np.sum([count_before(starts[n], t, RECENT) for n in ring2], axis=0) if ring2 else 0
        f["rc_national_starts_10m"] = count_before(all_starts, t, RECENT)
        f["rc_national_threats_10m"] = count_before(all_threats, t, RECENT)
        f["rc_national_ends_10m"] = count_before(all_ends, t, RECENT)
        f["rc_nb_newly_active_15m"] = np.sum([active[n] & ~active_15m_ago[n] for n in nb], axis=0) if nb else 0
        f["rc_national_active_change_15m"] = national_active - np.sum([active_15m_ago[n] for n in REGIONS], axis=0)
        f.update(ky if r == KYIV_CITY else ky_blank)
        if nebo is not None:
            kyiv = r in NEBO_REGIONS
            for g, ts_ in nebo_times.items():
                for wname, w in {"10m": RECENT, "30m": WINDOWS["30m"]}.items():
                    f[f"neb_{g}_{wname}"] = count_before(ts_, t, w) if kyiv else np.zeros(len(t), dtype=np.int64)
                f[f"neb_min_since_{g}"] = minutes_since(ts_, t) if kyiv else np.full(len(t), 24 * 60.0)
        if radar is not None:
            for role in roles:
                for g in RADAR_GROUPS:
                    for wname, w in RADAR_WINDOWS.items():
                        f[f"radar_{role}_{g}_{wname}"] = sum_before(*radar_threat[(r, role, g)], t, w)
                        f[f"nb_radar_{role}_{g}_{wname}"] = np.sum([sum_before(*radar_threat[(n, role, g)], t, w) for n in nb], axis=0)
            f["radar_down_1h"] = count_before(radar_down[r], t, pd.Timedelta(hours=1))
            for (g, wname), counts in radar_national.items():
                f[f"radar_national_{g}_{wname}"] = counts
        # All-clear side, meaningful on rows under alert: how long the current alert has run, how many starts joined
        # it, and partial clears here and next door.
        iv = intervals[r]
        i = np.searchsorted(iv[:, 0], t, side="left") - 1 if len(iv) else np.full(len(t), -1)
        cur_start = np.where(active[r], iv[np.maximum(i, 0), 0] if len(iv) else 0, t)
        cur_end = np.where(active[r], iv[np.maximum(i, 0), 1] if len(iv) else 0, 0)
        f["clr_alert_minutes"] = (t - cur_start) / 6e10
        f["clr_starts_in_alert"] = np.searchsorted(starts[r], t, side="left") - np.searchsorted(starts[r], cur_start, side="left")
        for wname in ("30m", "1h"):
            f[f"clr_ends_{wname}"] = count_before(ends[r], t, WINDOWS[wname])
            f[f"clr_nb_ends_{wname}"] = np.sum([count_before(ends[n], t, WINDOWS[wname]) for n in nb], axis=0) if nb else 0
        f["clr_national_ends_30m"] = count_before(all_ends, t, WINDOWS["30m"])
        if radar is not None:
            for wname in ("30m", "1h"):
                f[f"clr_radar_clear_{wname}"] = count_before(radar_clear[r], t, WINDOWS[wname])
                f[f"clr_radar_down_{wname}"] = count_before(radar_down[r], t, WINDOWS[wname])
                f[f"clr_radar_impact_{wname}"] = count_before(radar_impact[r], t, WINDOWS[wname])
        for h, d in HORIZONS.items():
            # All-clear label (rows under alert): the region's alert ends in (t, t + d]. Ends come from all-clear posts
            # or the ALERT_EXPIRY rule, the same rule live mode uses to show "alert now".
            ended = active[r] & (cur_end <= t + d.value) & (cur_end <= data_end)
            f[f"yc_{h}"] = np.where(active[r], np.where(ended, 1.0, np.where(t + d.value <= data_end, 0.0, np.nan)), np.nan)
        for h, d in HORIZONS.items():
            # Count of starts in (t, t + d]; label unknown (NaN) when the window runs past the data.
            n = np.searchsorted(starts[r], t + d.value, side="right") - np.searchsorted(starts[r], t, side="right")
            f[f"y_{h}"] = np.where(t + d.value <= data_end, (n > 0).astype(float), np.nan)
        frames.append(pd.DataFrame(f))

    table = pd.concat(frames, ignore_index=True)
    table["ts"] = pd.to_datetime(table["ts"], utc=True)
    table["region"] = table["region"].astype(pd.CategoricalDtype(REGIONS))
    if keep_active:
        return table
    return table[~table["active"]].drop(columns="active").reset_index(drop=True)


FEATURES_EXCLUDED = {"ts", "active", *(f"y_{h}" for h in HORIZONS), *(f"yc_{h}" for h in HORIZONS)}


def feature_columns(table: pd.DataFrame) -> list[str]:
    return [c for c in table.columns if c not in FEATURES_EXCLUDED]


def feature_groups(columns) -> dict[str, list[str]]:
    """Feature columns by source, so experiments can switch whole groups on and off."""
    cols = [c for c in columns if c not in FEATURES_EXCLUDED]
    return {
        "time": ["region", "hour", "weekday"],
        "history": ["min_since_start", "starts_24h"],
        "threats": [c for c in cols if c.split("_")[0] in THREAT_GROUPS],
        "neighbors": [c for c in cols if c.startswith("nb_") and not c.startswith("nb_radar_")],
        "national": [c for c in cols if c.startswith("national_")],
        "radar": [c for c in cols if c.startswith(("radar_", "nb_radar_"))],
        "wave": [c for c in cols if c.startswith("wave_")],
        "clear": [c for c in cols if c.startswith("clr_") and not c.startswith("clr_radar_")],
        "clear_radar": [c for c in cols if c.startswith("clr_radar_")],
        "recent": [c for c in cols if c.startswith("rc_")],
        "nebo": [c for c in cols if c.startswith("neb_")],
        "kyiv": [c for c in cols if c.startswith("ky_")],
        "regime": ["reform"],
    }
