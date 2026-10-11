"""Past alerts of one region and what the live model forecast before each one, read from the prediction log.

Served by `forecast live` as /history.json (live.Handler):
  ?region=kyiv                    -> {since, alerts}: alerts of the last DAYS days whose start the log saw (the entry
                                     before it was clear), newest first, each with `peak`: the highest siren-start
                                     forecast in the horizon before it, per model ("p" tested, "pu" untested) and horizon
  ?region=kyiv&start=<epoch s>    -> that alert's minute-by-minute forecasts from LEAD before it (or the previous
                                     alert's end) to its end: start chances while clear, all-clear chances during it
Only forecasts the page actually showed are used, so nothing here is replayed with hindsight.
"""

import json
from bisect import bisect_left
from pathlib import Path

import pandas as pd

from .dataset import HORIZONS

DAYS = 7
LEAD = max(HORIZONS.values())  # forecasts earlier than the longest horizon never covered the alert
MAX_GAP = pd.Timedelta(minutes=5)  # a clear -> alert switch across a longer logging gap has no known start
MODELS = ("p", "pu")


def tail_lines(path: Path, since: pd.Timestamp) -> list[str]:
    """Log lines with t >= since. Reads back from the end in growing chunks, so a long log is not read whole."""
    since_s = since.isoformat()
    with path.open("rb") as f:
        size = f.seek(0, 2)
        chunk = 1 << 20
        while True:
            start = max(0, size - chunk)
            f.seek(start)
            lines = f.read(size - start).decode().split("\n")
            if start:
                lines = lines[1:]  # first line is cut
            lines = [line for line in lines if line.startswith('{"t": "')]  # also drops a partial trailing line
            if start == 0 or (lines and lines[0][7:32] < since_s):
                return [line for line in lines if line[7:32] >= since_s]
            chunk *= 4


def region_log(log: Path, region: str, since: pd.Timestamp) -> list[tuple[pd.Timestamp, dict]]:
    """(t, {"active", "p", "pu"?}) for the region since `since`, the first entry of each minute.

    Decodes only the region's object in each line, so a week of a 25-region log stays fast.
    """
    key, decoder = f'"{region}": ', json.JSONDecoder()
    out, last = [], None
    for line in tail_lines(log, since):
        t = pd.Timestamp(line[7:32])
        i = line.find(key)
        if t.floor("min") == last or i < 0:
            continue
        out.append((t, decoder.raw_decode(line, i + len(key))[0]))
        last = t.floor("min")
    return out


def find_alerts(rows: list[tuple[pd.Timestamp, dict]]) -> list[dict]:
    """[{start, end}] (Timestamps, oldest first); end is None while the alert is on, or the last entry before a gap."""
    out, prev_t, prev_active = [], None, None
    for t, r in rows:
        gap = prev_t is not None and t - prev_t > MAX_GAP
        if gap and out and out[-1]["end"] is None:
            out[-1]["end"] = prev_t  # logging stopped during the alert: end unknown, cut it there
        if r["active"] and prev_active is False and not gap:
            out.append({"start": t, "end": None})
        elif not r["active"] and prev_active and out and out[-1]["end"] is None:
            out[-1]["end"] = t
        prev_t, prev_active = t, r["active"]
    return out


def alerts(log: Path, region: str, now: pd.Timestamp) -> dict:
    """{"since": epoch s, "alerts": [{start, end, peak}]}, newest first; times in epoch seconds."""
    window = now - pd.Timedelta(days=DAYS)
    rows = region_log(log, region, window - LEAD)
    times = [t for t, _ in rows]
    out = []
    for a in find_alerts(rows):
        if a["start"] < window:
            continue
        lo, hi = bisect_left(times, a["start"] - LEAD), bisect_left(times, a["start"])
        before = [(t, r) for t, r in rows[lo:hi] if not r["active"]]
        peak = {}
        for m in MODELS:
            vals = {h: [r[m][h] for t, r in before if m in r and t >= a["start"] - span] for h, span in HORIZONS.items()}
            peak[m] = {h: max(v) if v else None for h, v in vals.items()}
        out.append({"start": int(a["start"].timestamp()), "end": a["end"] and int(a["end"].timestamp()), "peak": peak})
    since = next((t for t in times if t >= window), None)
    return {"since": since and int(since.timestamp()), "alerts": out[::-1]}


def forecasts(log: Path, region: str, start: int) -> dict | None:
    """One alert's forecasts: {"start", "end", "t": [epoch s], "active": [..], "p": {h: [..]}, "pu": {h: [..]}}.

    "p"/"pu" hold siren-start chances while clear and all-clear chances while under alert; pu values are None before
    the untested model was logged. None if the log has no alert starting at `start`.
    """
    t0 = pd.Timestamp(start, unit="s", tz="UTC")
    rows = region_log(log, region, t0 - LEAD)
    alert = next((a for a in find_alerts(rows) if a["start"] == t0), None)
    if alert is None:
        return None
    end = alert["end"] or rows[-1][0]
    first = max((i + 1 for i, (t, r) in enumerate(rows) if t < t0 and r["active"]), default=0)  # after the previous alert
    rows = [(t, r) for t, r in rows[first:] if t <= end]
    return {
        "start": start,
        "end": alert["end"] and int(alert["end"].timestamp()),
        "t": [int(t.timestamp()) for t, _ in rows],
        "active": [r["active"] for _, r in rows],
        **{m: {h: [r[m][h] if m in r else None for _, r in rows] for h in HORIZONS} for m in MODELS},
    }
