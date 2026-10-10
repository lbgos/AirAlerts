"""Leakage and geography checks for the training table."""

import json

import pandas as pd

from ua_alert_forecast.dataset import build_table, feature_columns, load_events
from ua_alert_forecast.geo import NEIGHBORS, REGIONS

POSTS = [
    ("2026-10-01T00:10:00+00:00", "🛸 Ромни (Сумська обл.)\nЗагроза застосування БПЛА."),
    ("2026-10-01T00:20:00+00:00", "🟡 Роменський район (Сумська обл.)\nЖовтий рівень тривоги."),
    ("2026-10-01T00:50:00+00:00", "🛸 Лубни (Полтавська обл.)\nЗагроза застосування БПЛА."),
    ("2026-10-01T01:05:00+00:00", "🔴 Лубенський район (Полтавська обл.)\nЧервоний рівень тривоги."),
    ("2026-10-01T01:40:00+00:00", "🟢 Відбій тривоги\n• Роменський район (Сумська обл.)"),
    ("2026-10-01T02:30:00+00:00", "🟢 Лубенський район (Полтавська обл.)\nВідбій тривоги."),
    ("2026-10-01T03:10:00+00:00", "🟡 Київ\nЖовтий рівень тривоги."),
    ("2026-10-01T09:00:00+00:00", "🟢 Київ\nВідбій тривоги."),
]


def events_from(posts, tmp_path):
    path = tmp_path / "ch.jsonl"
    path.write_text("".join(json.dumps({"date": d, "text": t}, ensure_ascii=False) + "\n" for d, t in posts))
    return load_events(path)


def test_features_ignore_the_future(tmp_path):
    start, end = pd.Timestamp("2026-10-01T00:00Z"), pd.Timestamp("2026-10-01T04:00Z")
    full = build_table(events_from(POSTS, tmp_path), start, end)
    for cutoff in ["2026-10-01T00:45Z", "2026-10-01T01:30Z", "2026-10-01T03:00Z"]:
        cutoff = pd.Timestamp(cutoff)
        past = [p for p in POSTS if pd.Timestamp(p[0]) < cutoff]
        cut = build_table(events_from(past, tmp_path), start, end)
        cols = feature_columns(full)
        a = full[full.ts <= cutoff][cols].reset_index(drop=True)
        b = cut[cut.ts <= cutoff][cols].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b)


def test_labels_and_active_rows(tmp_path):
    table = build_table(events_from(POSTS, tmp_path), pd.Timestamp("2026-10-01T00:00Z"), pd.Timestamp("2026-10-01T03:00Z"))
    poltava = table[table.region == "poltavska"].set_index("ts")
    # Siren starts in Poltava at 01:05: in the 30m window from 00:45, not from 00:30.
    assert poltava.loc["2026-10-01T00:45Z", "y_30m"] == 1
    assert poltava.loc["2026-10-01T00:30Z", "y_30m"] == 0
    assert poltava.loc["2026-10-01T00:45Z", "nb_starts_30m"] == 1  # Sumy started at 00:20
    # Under alert 01:05-02:30: those rows are dropped.
    assert pd.Timestamp("2026-10-01T01:15Z") not in poltava.index
    assert pd.Timestamp("2026-10-01T02:30Z") not in poltava.index  # end at exactly 02:30 is not yet known
    assert pd.Timestamp("2026-10-01T02:45Z") in poltava.index


def test_neighbors_symmetric_and_complete():
    assert set(NEIGHBORS) == set(REGIONS)
    for a, bs in NEIGHBORS.items():
        assert bs, a
        for b in bs:
            assert a in NEIGHBORS[b], (a, b)
