"""Lead time of radar-channel mentions vs neighbor sirens before siren episodes, in the window raketa_trevoga covers."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from ua_alert_forecast.config import RAW_DIR
from ua_alert_forecast.dataset import alert_intervals, load_events, STEP
from ua_alert_forecast.geo import NEIGHBORS, REGIONS
from ua_alert_forecast.radar import label_history
from ua_alert_forecast.train import RADAR_LABELS, RADAR_CHANNELS_USED

W = pd.Timedelta(minutes=60)
ev = load_events(RAW_DIR / "UkraineAlarmSignal.jsonl")
end = ev.ts.max()
# raketa mentions from Haiku labels (now_in or heading_to)
lab = [json.loads(l) for f in sorted(Path(__file__).resolve().parents[1] / "labels" / "raketa_v2".glob("chunk_*.jsonl")) for l in open(f)]
dates = {json.loads(l)["id"]: json.loads(l)["date"] for l in open(RAW_DIR / "raketa_trevoga.jsonl")}
rk = pd.DataFrame([{"ts": pd.Timestamp(dates[l["id"]]), "oblast": o, "kind": l["kind"]}
                   for l in lab if l["kind"] == "threat" for o in set(l["now_in"]) | set(l["heading_to"])])
start = pd.Timestamp(min(dates.values())) + W
# kpszsu + deraketaua through the local student (trained on labels before end-28d, as in the experiments)
st = label_history(RAW_DIR, RADAR_LABELS, RADAR_CHANNELS_USED, end - pd.Timedelta(days=28))
st = st[(st.kind == "threat") & st.oblast.notna()]
sources = {"raketa_trevoga (Haiku labels)": rk, "kpszsu+deraketaua (student)": st}

iv = alert_intervals(ev)
starts = {r: np.sort(ev[(ev.kind == "start") & (ev.oblast == r)].ts.to_numpy(dtype="datetime64[ns]").astype(np.int64)) for r in REGIONS}
threat = {r: np.sort(ev[(ev.kind == "threat") & (ev.oblast == r)].ts.to_numpy(dtype="datetime64[ns]").astype(np.int64)) for r in REGIONS}
def first_in(times, s):
    sel = times[(times >= s - W.value) & (times < s)]
    return sel.min() if len(sel) else None

rows = []
for r in REGIONS:
    for s, e in iv[r]:
        if not (start.value <= s <= end.value):
            continue
        nb = [first_in(starts[n], s) for n in NEIGHBORS[r]]
        nb = min([x for x in nb if x is not None], default=None)
        row = {"region": r, "s": s, "neighbor": nb, "alert_threat": first_in(threat[r], s)}
        for name, df in sources.items():
            t = np.sort(df[df.oblast == r].ts.to_numpy(dtype="datetime64[ns]").astype(np.int64))
            row[name] = first_in(t, s)
        rows.append(row)
d = pd.DataFrame(rows)
print(f"window {start:%m-%d %H:%M} .. {end:%m-%d %H:%M} UTC, siren episodes: {len(d)}\n")
out = []
for src in ["neighbor", "alert_threat", *sources]:
    has = d[src].notna()
    o = {"signal in the 60 min before the siren": src, "share of episodes": has.mean()}
    if src in sources:
        o["before first neighbor siren"] = (has & (d.neighbor.isna() | (d[src] < d.neighbor))).mean()
        o["only warning (no neighbor siren, no threat note)"] = (has & d.neighbor.isna() & d.alert_threat.isna()).mean()
        lead = (d.s - d[src]) / 6e10
        o["median lead, min"] = lead[has].median()
    out.append(o)
print(pd.DataFrame(out).round(3).to_markdown(index=False))

# All-clear side: rows under alert on the 15-min grid; does a raketa mention of the region in the last 30 min change
# the chance that the alert ends within 30 min?
grid = pd.date_range(start.ceil(STEP), end - pd.Timedelta(minutes=30), freq=STEP, tz="UTC", unit="ns").asi8
res = []
for name, df in sources.items():
    for r in REGIONS:
        t = np.sort(df[df.oblast == r].ts.to_numpy(dtype="datetime64[ns]").astype(np.int64))
        for s, e in iv[r]:
            g = grid[(grid > s) & (grid <= e)]
            for x in g:
                recent = ((t >= x - pd.Timedelta(minutes=30).value) & (t < x)).any()
                res.append({"source": name, "mention_30m": recent, "ends_30m": e <= x + pd.Timedelta(minutes=30).value})
a = pd.DataFrame(res).groupby(["source", "mention_30m"]).agg(rows=("ends_30m", "size"), ends_within_30m=("ends_30m", "mean"))
print("\nAll-clear within 30 min, by whether the channel mentioned the oblast in the last 30 min (rows under alert)\n")
print(a.round(3).to_markdown())
