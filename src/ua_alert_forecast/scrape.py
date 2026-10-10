"""Download Telegram channel history into data/raw/<channel>.jsonl, one post per line.

Incremental: a re-run fetches only posts newer than the last saved id.
Credentials come from .env (see .env.example). Log in once with `forecast login` (QR code),
which stores a local *.session file reused by later runs.
"""

import getpass
import json
import os

import qrcode

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.custom import Message

from .config import ALERT_CHANNELS, HISTORY_START, RADAR_CHANNELS, RAW_DIR, ROOT


def last_saved_id(path) -> int:
    if not path.exists():
        return 0
    last = 0
    with path.open() as f:
        for line in f:
            last = json.loads(line)["id"]
    return last


def to_row(msg: Message) -> dict:
    """One saved post: the format of data/raw/<channel>.jsonl."""
    return {
        "id": msg.id,
        "date": msg.date.isoformat(),
        "edit_date": msg.edit_date.isoformat() if msg.edit_date else None,
        "text": msg.message or "",
        "reply_to": msg.reply_to.reply_to_msg_id if msg.reply_to else None,
        "has_media": msg.media is not None,
    }


async def scrape_channel(client: TelegramClient, channel: str) -> int:
    path = RAW_DIR / f"{channel}.jsonl"
    min_id = last_saved_id(path)
    # Oldest-first, so the file stays sorted and resuming works after an interrupt.
    kwargs = {"min_id": min_id} if min_id else {"offset_date": HISTORY_START}
    count = 0
    with path.open("a") as f:
        async for msg in client.iter_messages(channel, reverse=True, **kwargs):
            if msg.date < HISTORY_START:
                continue
            f.write(json.dumps(to_row(msg), ensure_ascii=False) + "\n")
            count += 1
            if count % 1000 == 0:
                f.flush()
                print(f"  {channel}: {count} posts, at {msg.date:%Y-%m-%d}")
    return count


def make_client() -> TelegramClient:
    load_dotenv(ROOT / ".env")
    return TelegramClient(
        str(ROOT / "ua_alert_forecast"),
        int(os.environ["TG_API_ID"]),
        os.environ["TG_API_HASH"],
        flood_sleep_threshold=300,  # sleep through Telegram rate limits instead of failing
    )


async def login() -> None:
    """QR login: scan from the phone via Settings -> Devices -> Link Desktop Device.

    Used instead of phone codes, which Telegram did not deliver for this API app.
    """
    client = make_client()
    await client.connect()
    try:
        if await client.is_user_authorized():
            print("already logged in")
            return
        qr = await client.qr_login()
        while True:
            code = qrcode.QRCode(border=1)
            code.add_data(qr.url)
            code.print_ascii(invert=True)
            print("Scan with Telegram: Settings -> Devices -> Link Desktop Device")
            try:
                await qr.wait(timeout=60)
                break
            except TimeoutError:
                await qr.recreate()  # token expired; show a fresh QR
            except SessionPasswordNeededError:
                await client.sign_in(password=getpass.getpass("2FA password: "))
                break
        me = await client.get_me()
        print(f"logged in as {me.first_name}")
    finally:
        await client.disconnect()


async def scrape(channels: list[str] | None = None) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = make_client()
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("not logged in: run `uv run forecast login` first")
    try:
        for channel in channels or RADAR_CHANNELS + ALERT_CHANNELS:
            print(f"{channel}: fetching")
            print(f"{channel}: +{await scrape_channel(client, channel)} posts")
    finally:
        await client.disconnect()
