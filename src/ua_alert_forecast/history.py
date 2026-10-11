"""Past alerts of one region and what the live model forecast before each one, read from the prediction log.

Served by `forecast live` as /history.json (live.Handler):
  ?region=kyiv                    -> {since, alerts}: alerts of the last DAYS days whose start the log saw (the poll
                                     before it was clear), newest first; since = first logged time in that window
  ?region=kyiv&start=<epoch s>    -> that alert's forecasts: start chances up to LEAD before it, all-clear chances
                                     up to LEAD before its end; one point per minute, as logged at the time
Only forecasts the page actually showed are used, so nothing here is replayed with hindsight.
"""

import json
from pathlib import Path

import pandas as pd

DAYS = 7
LEAD = pd.Timedelta(hours=6)  # longest horizon: earlier forecasts never covered the event
MAX_GAP = pd.Timedelta(minutes=5)  # a clear -> alert switch across a longer logging gap has no known start


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


def alerts(log: Path, region: str, now: pd.Timestamp) -> dict:
    """{"since": epoch s, "alerts": [{start, end}]} in epoch seconds; end is None while the alert is still on."""
    key = f'"{region}": {{"active": '
    out, prev_t, prev_active = [], None, None
    lines = tail_lines(log, now - pd.Timedelta(days=DAYS))
    for line in lines:
        i = line.find(key)
        if i < 0:
            continue
        t, active = pd.Timestamp(line[7:32]), line[i + len(key)] == "t"
        gap = prev_t is not None and t - prev_t > MAX_GAP
        if gap and out and out[-1]["end"] is None:
            out[-1]["end"] = int(prev_t.timestamp())  # logging stopped during the alert: end unknown, cut it there
        if active and prev_active is False and not gap:
            out.append({"start": int(t.timestamp()), "end": None})
        elif not active and prev_active and out and out[-1]["end"] is None:
            out[-1]["end"] = int(t.timestamp())
        prev_t, prev_active = t, active
    return {"since": int(pd.Timestamp(lines[0][7:32]).timestamp()) if lines else None, "alerts": out[::-1]}


def forecasts(log: Path, region: str, start: int, end: int | None) -> dict:
    """The region's logged forecasts before `start` (siren start) and before `end` (all-clear), one per minute.

    Each part: {"t": [epoch s], "p": {h: [..]}, "pu": {h: [..]}}; pu (untested model) values are None before it was logged.
    """
    t0, t1 = pd.Timestamp(start, unit="s", tz="UTC"), pd.Timestamp(end or start, unit="s", tz="UTC")
    parts = {"before_start": [], "before_end": []}
    seen = set()
    for line in tail_lines(log, t0 - LEAD):
        t = pd.Timestamp(line[7:32])
        if t > t1 or t.floor("min") in seen:
            continue
        seen.add(t.floor("min"))
        r = json.loads(line)["regions"].get(region)
        if r is None:
            continue
        if t < t0:  # only since the region's previous alert ended
            parts["before_start"] = [] if r["active"] else parts["before_start"] + [(t, r)]
        elif end and t0 <= t < t1 and t >= t1 - LEAD and r["active"]:
            parts["before_end"].append((t, r))
    for name, rows in parts.items():
        horizons = list(rows[0][1]["p"]) if rows else []
        parts[name] = {
            "t": [int(t.timestamp()) for t, _ in rows],
            "p": {h: [r["p"][h] for _, r in rows] for h in horizons},
            "pu": {h: [r["pu"][h] if "pu" in r else None for _, r in rows] for h in horizons},
        }
    return {"start": start, "end": end, **parts}
