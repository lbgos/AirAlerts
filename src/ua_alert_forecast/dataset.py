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

from .alerts import parse_post
from .geo import NEIGHBORS, REGIONS, RING2

Horizon = Literal["15m", "30m", "1h", "3h", "6h"]
HORIZONS: dict[Horizon, pd.Timedelta] = {
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "3h": pd.Timedelta(hours=3),
    "6h": pd.Timedelta(hours=6),
}
STEP = pd.Timedelta(minutes=15)
# A place with no matching end post is treated as cleared after this long (same rule as the Vadimkin processor).
ALERT_EXPIRY = timedelta(hours=3)
THREAT_GROUPS = {"drone": ["drone"], "kab": ["kab"], "missile": ["high_speed"], "other": ["shelling", "explosions", "recon", "aviation"]}
WINDOWS = {"30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1), "3h": pd.Timedelta(hours=3)}


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


def alert_intervals(events: pd.DataFrame) -> dict[str, np.ndarray]:
    """Per region, disjoint sorted [start, end) intervals (int64 ns) when any place in it was under alert.

    Places open on a start event and close on an end event for the same place, or after ALERT_EXPIRY.
    """
    open_at: dict[tuple[str, str], pd.Timestamp] = {}
    spans: dict[str, list[tuple[int, int]]] = {r: [] for r in REGIONS}

    def close(key: tuple[str, str], end: pd.Timestamp) -> None:
        start = open_at.pop(key)
        spans[key[0]].append((start.value, min(end, start + ALERT_EXPIRY).value))

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


def minutes_since(times: np.ndarray, t: np.ndarray, cap_minutes: float = 24 * 60) -> np.ndarray:
    if len(times) == 0:
        return np.full(len(t), cap_minutes)
    i = np.searchsorted(times, t, side="left") - 1
    last = np.where(i >= 0, times[np.maximum(i, 0)], np.iinfo(np.int64).min // 2)
    return np.minimum((t - last) / 6e10, cap_minutes)


def sum_before(times: np.ndarray, weights: np.ndarray, t: np.ndarray, window: pd.Timedelta) -> np.ndarray:
    """Sum of weights of events in [t - window, t). `times` sorted int64 ns, `weights` aligned with it."""
    cs = np.concatenate([[0.0], np.cumsum(weights)])
    return cs[np.searchsorted(times, t, side="left")] - cs[np.searchsorted(times, t - window.value, side="left")]


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
) -> pd.DataFrame:
    """Feature + label table on a 15-minute grid in [start, end). Labels need data up to end + 6h.

    Live mode passes `grid` (the forecast times, e.g. just "now") and `keep_active=True` to get an `active`
    column instead of dropping regions already under alert.

    `radar` (optional): output of `radar.to_events` (rows per post, role and oblast, with weights). Role "heading_to" is where an object is going but not yet: the direction signal that
    neighbor sirens don't carry.
    """
    if grid is None:
        grid = pd.date_range(start.ceil(STEP), end, freq=STEP, inclusive="left", tz="UTC", unit="ns")
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
    }
