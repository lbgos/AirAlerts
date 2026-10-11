"""`forecast live`: poll @UkraineAlarmSignal, forecast every region at the current time, serve the web page.

Only the alert channel is read: the chosen model uses no radar features (see README).
New posts are appended to data/raw/UkraineAlarmSignal.jsonl in the scraper's format, so live data can be trained on later.
The page (web/index.html) fetches /state.json, rewritten after every poll, /ukraine.json (map, scripts/make_map.py)
and /history.json (a region's past alerts and the forecasts logged before them, history.py).
"""

import asyncio
import json
import pickle
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd
from telethon import TelegramClient

from . import history
from .config import RAW_DIR, ROOT
from .dataset import HORIZONS, build_table, events_from_posts
from .scrape import last_saved_id, make_client, to_row
from .train import LABEL_CHANNEL, LIVE_MODEL_PATH

HISTORY = pd.Timedelta(hours=30)  # features look back 24h; alerts opened before that can still be running
POLL_SECONDS = 30
# Collected only (appended to data/raw/), not used by the models: radar channels with oblast/city-level detail
# (@raketa_trevoga deletes posts after ~2 days, so its history has to be recorded live before it can be tested).
COLLECT_CHANNELS = ["raketa_trevoga", "nebo_raketa"]
STATE_PATH = ROOT / "data" / "live" / "state.json"
# One line per poll: every region's forecasts at that moment, for scoring against what happened (`forecast score-live`).
PREDICTION_LOG = ROOT / "data" / "live" / "predictions.jsonl"
WEB_DIR = Path(__file__).parent / "web"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/ukraine.json": ("ukraine.json", "application/json")}


def recent_posts(path: Path, since: pd.Timestamp) -> list[dict]:
    with path.open() as f:
        return [p for p in map(json.loads, f) if pd.Timestamp(p["date"]) >= since]


async def fetch_new(client: TelegramClient, path: Path, after_id: int, channel: str = LABEL_CHANNEL) -> list[dict]:
    """Posts newer than `after_id`, oldest first, also appended to the raw dump."""
    new = [to_row(m) async for m in client.iter_messages(channel, min_id=after_id, reverse=True)]
    if new:
        with path.open("a") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new)
    return new


def forecast(bundle: dict, posts: list[dict], now: pd.Timestamp) -> dict:
    """Probabilities per region and horizon at `now`, plus which regions are under alert."""
    events = events_from_posts(posts)
    grid = pd.DatetimeIndex([now]).as_unit("ns")
    table = build_table(events, now, now, grid=grid, keep_active=True)
    start = {h: bundle["models"][h].predict(table) for h in HORIZONS}
    clear = {h: bundle["clear_models"][h].predict(table) for h in HORIZONS}
    untested = "untested_models" in bundle  # bundles fitted before the toggle existed have only the tested pair
    if untested:
        ustart = {h: bundle["untested_models"][h].predict(table) for h in HORIZONS}
        uclear = {h: bundle["untested_clear_models"][h].predict(table) for h in HORIZONS}
    regions = [
        {
            "id": row.region,
            "active": bool(row.active),
            "alert_minutes": round(row.clr_alert_minutes) if row.active else None,
            # p: siren starts within h (regions not under alert); pc: all-clear within h (regions under alert)
            "p": {h: round(float(start[h][i]), 4) for h in HORIZONS},
            "pc": {h: round(float(clear[h][i]), 4) for h in HORIZONS},
            # pu / pcu: the same from the untested models (page toggle)
            **({"pu": {h: round(float(ustart[h][i]), 4) for h in HORIZONS},
                "pcu": {h: round(float(uclear[h][i]), 4) for h in HORIZONS}} if untested else {}),
        }
        for i, row in enumerate(table.itertuples())
    ]
    return {
        "generated_at": now.isoformat(),
        "last_post_at": posts[-1]["date"] if posts else None,
        "model": bundle["config"].name,
        "clear_model": bundle["clear_config"].name,
        "trained_until": bundle["data_end"].isoformat(),
        "regions": regions,
    }


def write_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False))
    tmp.replace(STATE_PATH)  # atomic: the page never reads a half-written file
    # The forecast relevant to each region's state: start chances if clear, all-clear chances if under alert.
    log = {"t": state["generated_at"], "model": state["model"], "clear_model": state["clear_model"],
           "regions": {r["id"]: {"active": r["active"], "p": r["pc"] if r["active"] else r["p"],
                                 **({"pu": r["pcu"] if r["active"] else r["pu"]} if "pu" in r else {})} for r in state["regions"]}}
    with PREDICTION_LOG.open("a") as f:
        f.write(json.dumps(log) + "\n")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlsplit(self.path)
        path, query = url.path, {k: v[0] for k, v in parse_qs(url.query).items()}
        if path in STATIC:
            name, ctype = STATIC[path]
            body = (WEB_DIR / name).read_bytes()
        elif path == "/state.json" and STATE_PATH.exists():
            body, ctype = STATE_PATH.read_bytes(), "application/json"
        elif path == "/history.json" and PREDICTION_LOG.exists() and query.get("region", "").replace("_", "").isalpha():
            region = query["region"]
            if "start" in query:
                data = history.forecasts(PREDICTION_LOG, region, int(query["start"])) if query["start"].isdigit() else None
            else:
                data = history.alerts(PREDICTION_LOG, region, pd.Timestamp.now(tz="UTC"))
            if data is None:
                self.send_error(404)
                return
            body, ctype = json.dumps(data).encode(), "application/json"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


async def run(host: str, port: int) -> None:
    bundle, model_mtime = pickle.loads(LIVE_MODEL_PATH.read_bytes()), LIVE_MODEL_PATH.stat().st_mtime
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"serving http://{host}:{port}  model {bundle['config'].name}", flush=True)

    client = make_client()
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("not logged in: run `uv run forecast login` first")
    path = RAW_DIR / f"{LABEL_CHANNEL}.jsonl"
    last_id = last_saved_id(path)
    posts = recent_posts(path, pd.Timestamp.now(tz="UTC") - HISTORY)
    collect_ids = {ch: last_saved_id(RAW_DIR / f"{ch}.jsonl") for ch in COLLECT_CHANNELS}
    while True:
        try:
            if LIVE_MODEL_PATH.stat().st_mtime != model_mtime:  # `forecast fit-live` wrote a newer model (daily refit)
                bundle, model_mtime = pickle.loads(LIVE_MODEL_PATH.read_bytes()), LIVE_MODEL_PATH.stat().st_mtime
                print(f"reloaded model, data until {bundle['data_end']:%Y-%m-%d %H:%M} UTC", flush=True)
            for ch in COLLECT_CHANNELS:
                got = await fetch_new(client, RAW_DIR / f"{ch}.jsonl", collect_ids[ch], ch)
                collect_ids[ch] = got[-1]["id"] if got else collect_ids[ch]
            new = await fetch_new(client, path, last_id)
            if new:
                last_id = new[-1]["id"]
                posts += new
            now = pd.Timestamp.now(tz="UTC").floor("s")
            posts = [p for p in posts if pd.Timestamp(p["date"]) >= now - HISTORY]
            write_state(forecast(bundle, posts, now))
            print(f"{now:%H:%M:%S} +{len(new)} posts", flush=True)
        except Exception:
            traceback.print_exc()  # keep serving the last state; Telethon reconnects on its own
        await asyncio.sleep(POLL_SECONDS)


def score() -> None:
    """Score logged live forecasts against what the channel later showed. One forecast per region per 5 minutes.

    Outcomes come from the same parser and labels as training (build_table at the logged times), so a forecast is
    scored only once its whole horizon has passed. Writes reports/live_score.md.
    """
    from .dataset import load_events
    from .model import reliability, scores
    from .train import REPORT_DIR

    logs = [json.loads(line) for line in PREDICTION_LOG.open()]
    by_slot = {}
    for entry in logs:  # first log line in each 5-minute slot
        by_slot.setdefault(pd.Timestamp(entry["t"]).floor("5min"), entry)
    entries = list(by_slot.values())
    events = load_events(RAW_DIR / f"{LABEL_CHANNEL}.jsonl")
    grid = pd.DatetimeIndex([pd.Timestamp(e["t"]) for e in entries]).as_unit("ns")
    truth = build_table(events, grid[0], grid[-1], grid=grid, keep_active=True).set_index(["ts", "region"])

    rows = []
    for e in entries:
        t = pd.Timestamp(e["t"])
        for region, r in e["regions"].items():
            actual = truth.loc[(t, region)]
            if bool(actual["active"]) != r["active"]:
                continue  # live and replay disagree on the state (late post); skip rather than guess
            for h, p in r["p"].items():
                y = actual[f"yc_{h}" if r["active"] else f"y_{h}"]
                if not pd.isna(y):
                    rows.append({"kind": "all-clear" if r["active"] else "siren start", "horizon": h, "p": p, "y": y})
    df = pd.DataFrame(rows)
    if df.empty:
        print(f"{len(logs)} polls logged, none scorable yet: a forecast is scored once its horizon has passed")
        return
    lines = ["# Live forecasts vs outcome", "", f"Logged {len(logs)} polls from {logs[0]['t'][:16]} to {logs[-1]['t'][:16]} UTC; "
             f"scored one forecast per region per 5 minutes once its horizon had passed.",
             "correct = forecast >= 50% and it happened, or < 50% and it did not.", ""]
    summary = []
    for (kind, h), g in df.groupby(["kind", "horizon"], sort=False):
        y, p = g["y"].to_numpy(), g["p"].to_numpy()
        sc = scores(y, p)
        summary.append({"forecast": kind, "horizon": h, "n": len(g), "happened": y.mean(), "mean_forecast": p.mean(),
                        "correct": ((p >= 0.5) == (y == 1)).mean(), "brier": sc["brier"], "auc": sc["auc"], "ece": sc["ece"]})
    lines += [pd.DataFrame(summary).round(3).to_markdown(index=False)]
    for (kind, h), g in df.groupby(["kind", "horizon"], sort=False):
        lines += ["", f"## Reliability: {kind}, {h}", "", reliability(g["y"].to_numpy(), g["p"].to_numpy()).round(3).to_markdown()]
    (REPORT_DIR / "live_score.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:6 + len(summary) + 2]))
