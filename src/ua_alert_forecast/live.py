"""`forecast live`: poll @UkraineAlarmSignal, forecast every region at the current time, serve the web page.

Only the alert channel is read: the chosen model uses no radar features (see README).
New posts are appended to data/raw/UkraineAlarmSignal.jsonl in the scraper's format, so live data can be trained on later.
The page (web/index.html) fetches /state.json, which is rewritten after every poll.
"""

import asyncio
import json
import pickle
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd
from telethon import TelegramClient

from .config import RAW_DIR, ROOT
from .dataset import HORIZONS, build_table, events_from_posts
from .scrape import last_saved_id, make_client, to_row
from .train import LABEL_CHANNEL, LIVE_MODEL_PATH

HISTORY = pd.Timedelta(hours=30)  # features look back 24h; alerts opened before that can still be running
POLL_SECONDS = 30
STATE_PATH = ROOT / "data" / "live" / "state.json"
INDEX_HTML = Path(__file__).parent / "web" / "index.html"


def recent_posts(path: Path, since: pd.Timestamp) -> list[dict]:
    with path.open() as f:
        return [p for p in map(json.loads, f) if pd.Timestamp(p["date"]) >= since]


async def fetch_new(client: TelegramClient, path: Path, after_id: int) -> list[dict]:
    """Posts newer than `after_id`, oldest first, also appended to the raw dump."""
    new = [to_row(m) async for m in client.iter_messages(LABEL_CHANNEL, min_id=after_id, reverse=True)]
    if new:
        with path.open("a") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new)
    return new


def forecast(bundle: dict, posts: list[dict], now: pd.Timestamp) -> dict:
    """Probabilities per region and horizon at `now`, plus which regions are under alert."""
    events = events_from_posts(posts)
    grid = pd.DatetimeIndex([now]).as_unit("ns")
    table = build_table(events, now, now, grid=grid, keep_active=True)
    probs = {h: bundle["models"][h].predict(table) for h in HORIZONS}
    regions = [
        {
            "id": row.region,
            "active": bool(row.active),
            "alert_minutes": round(row.min_since_start) if row.active else None,
            "p": {h: round(float(probs[h][i]), 4) for h in HORIZONS},
        }
        for i, row in enumerate(table.itertuples())
    ]
    return {
        "generated_at": now.isoformat(),
        "last_post_at": posts[-1]["date"] if posts else None,
        "model": bundle["config"].name,
        "trained_until": bundle["data_end"].isoformat(),
        "regions": regions,
    }


def write_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False))
    tmp.replace(STATE_PATH)  # atomic: the page never reads a half-written file


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            body, ctype = INDEX_HTML.read_bytes(), "text/html; charset=utf-8"
        elif path == "/state.json" and STATE_PATH.exists():
            body, ctype = STATE_PATH.read_bytes(), "application/json"
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
    bundle = pickle.loads(LIVE_MODEL_PATH.read_bytes())
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
    while True:
        try:
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
