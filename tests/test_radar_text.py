"""Radar-text track parsing and feature building: corridor rings, carrier posts with stated arrivals."""

import numpy as np
import pandas as pd

from ua_alert_forecast.dataset import build_table
from ua_alert_forecast.events import NS_PER_MIN
from ua_alert_forecast.kyiv import KYIV
from ua_alert_forecast.radar_text import (DIST_CAP, ETA_NONE, carrier_events, carrier_features, corridor_events,
                                          corridor_features, load_posts)
from ua_alert_forecast.config import RAW_DIR


def T(s: str) -> int:
    return int(pd.Timestamp(s, tz="UTC").value)


def test_corridor_town_and_city_and_clear_excluded():
    posts = pd.DataFrame({
        "ts": [T("2026-02-16T23:06:00Z"), T("2026-02-16T23:10:00Z"), T("2026-02-16T23:12:00Z")],
        "text": ["🛵 БпЛА на Бровари", "🛸 книги на Оболоні, летить на Поділ", "💚 Відбій у Броварах"],
    })
    co = corridor_events(posts)
    assert len(co) == 2
    assert abs(co.dist.iloc[0] - 20.6) < 1.5 and co.weapon.iloc[0] == "drone"
    assert co.dist.iloc[1] == 0.0 and co.towns.iloc[1] >= 1


def test_corridor_feature_ring_recency():
    co = pd.DataFrame({"ts": [T("2026-02-16T23:00:00Z"), T("2026-02-16T22:00:00Z")],
                       "dist": [30.0, 100.0], "weapon": ["drone", "missile"]})
    grid = np.array([T("2026-02-16T23:20:00Z")])
    f = corridor_features(co, grid)
    assert f["co_ring40_min_since"][0] == 20.0  # inside the 40 km ring, 20 minutes ago
    assert f["co_ring40_30m"][0] == 1 and f["co_ring80_30m"][0] == 1 and f["co_ring80_min_since"][0] == 20.0
    assert f["co_min_dist_drone_30m"][0] == 30.0  # only the drone post falls into the last 30 min
    assert f["co_min_dist_15m"][0] == DIST_CAP  # nothing named in the last 15 minutes


def L(s: str, tz: str = "Europe/Kyiv") -> int:
    """A Kyiv local wall-clock time as UTC ns (what the channels' stated times mean)."""
    return int(pd.Timestamp(s).tz_localize(tz).tz_convert("UTC").value)


def test_carrier_eta_local_time_and_rollover():
    posts = pd.DataFrame({
        "ts": [T("2026-02-16T23:06:00Z"), T("2026-01-20T01:50:00Z"), T("2026-04-24T19:52:00Z")],
        "text": ["✈️3 Ту-95мс з аеродрому Оленья, курс на пускові рубежі. Підліт до пускових рубежів 4:30",
                 "✈ Виліт Ту-95МС з Оленьї! Можливі пуски крилатих ракет повітряного базування ближче до 6.00!",
                 "…Прибуття в потенційну зону пуску крилатих ракет Х-101: Вологодська зона 0:00"],
    })
    ca = carrier_events(posts)
    assert ca.kind.iloc[0] == "tu" and ca.eta.iloc[0] == L("2026-02-17 04:30")
    assert ca.eta.iloc[1] == L("2026-01-20 06:00")
    assert ca.eta.iloc[2] == L("2026-04-24 00:00") + 24 * 3600 * 10**9  # 00:00 already passed -> next morning


def test_carrier_past_report_is_not_eta():
    posts = pd.DataFrame({
        "ts": [T("2026-02-11T14:05:00Z"), T("2026-01-20T01:50:00Z")],
        "text": ["❗️Сьогодні, близько 14.40 ворог здійснив пуски аеробалістичних ракет Х-47М2 Кинджал з МіГ-31К",
                 "🚫 Ту-95:ILD відбій ракетної небезпеки"],
    })
    ca = carrier_events(posts)
    assert ca.kind.iloc[0] == "mig" and np.isnan(ca.eta.iloc[0])
    assert len(ca) == 1  # the відбій post is dropped


def test_carrier_features_eta_windows():
    post = T("2026-02-16T23:06:00Z")
    eta = post + 90 * NS_PER_MIN
    ca = pd.DataFrame({"ts": [post, post], "kind": ["tu", "tu"], "eta": [np.nan, eta]})
    grid = np.array([post + 30 * NS_PER_MIN, post + 95 * NS_PER_MIN, post + 300 * NS_PER_MIN])
    f = carrier_features(ca, grid)
    assert f["ca_eta_min"].tolist() == [60.0, 0.0, 0.0]  # clipped at 0 once the stated moment has come
    assert f["ca_eta_in_1h"].tolist() == [1, 1, 1] and f["ca_eta_in_3h"].tolist() == [1, 1, 1]
    assert f["ca_min_since"].tolist() == [30.0, 95.0, 300.0]


def test_carrier_no_eta_current():
    ca = pd.DataFrame({"ts": [T("2026-02-16T23:06:00Z")], "kind": ["mig"], "eta": [np.nan]})
    grid = np.array([T("2026-02-17T06:00:00Z")])
    f = carrier_features(ca, grid)
    assert f["ca_eta_min"][0] == ETA_NONE and f["ca_eta_in_3h"][0] == 0
    assert f["ca_mig_min_since"][0] == 6 * 60 + 54 and f["ca_tu_min_since"][0] == 24 * 60.0


def test_build_table_wires_corridor_only_for_kyiv_regions():
    events = pd.DataFrame({"ts": pd.to_datetime([], utc=True, unit="ns"), "kind": pd.Series([], dtype="object"),
                           "detail": pd.Series([], dtype="object"), "oblast": pd.Series([], dtype="object"),
                           "place": pd.Series([], dtype="object")})
    co = pd.DataFrame({"ts": [T("2026-02-16T23:00:00Z")], "dist": [30.0], "towns": [1], "weapon": ["drone"]})
    table = build_table(events, pd.Timestamp("2026-02-16T20:00Z"), pd.Timestamp("2026-02-17T02:00Z"),
                        corridor=co, keep_active=True)
    one = table[(table.region == "kyiv") & (table.ts == pd.Timestamp("2026-02-16T23:10:00Z", tz="UTC"))].iloc[0]
    other = table[(table.region == "vinnytska") & (table.ts == pd.Timestamp("2026-02-16T23:10:00Z", tz="UTC"))].iloc[0]
    assert one["co_min_dist_15m"] == 30.0 and other["co_min_dist_15m"] == DIST_CAP
    assert other["co_ring40_min_since"] == 24 * 60.0


def test_load_posts():
    posts = load_posts(RAW_DIR, ["nebo_raketa"])
    assert set(posts.columns) == {"ts", "text"} and len(posts) > 1000 and posts["ts"].notna().all()
