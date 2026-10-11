import json

import pandas as pd

from ua_alert_forecast.history import alerts, forecasts

T0 = pd.Timestamp("2026-10-11T12:00:00+00:00")


def write_log(path, states: list[bool | None]) -> None:
    """One entry per minute from T0, forecast i/100 at minute i; None = no entry (logging gap)."""
    with path.open("w") as f:
        for i, active in enumerate(states):
            if active is not None:
                p = {h: i / 100 for h in ("15m", "30m", "1h", "3h", "6h")}
                region = {"active": active, "p": p}
                f.write(json.dumps({"t": (T0 + pd.Timedelta(minutes=i)).isoformat(), "regions": {"kyivska": region, "kyiv": region}}) + "\n")


def m(i: int) -> int:
    return int((T0 + pd.Timedelta(minutes=i)).timestamp())


def test_alerts_and_forecasts(tmp_path):
    log = tmp_path / "predictions.jsonl"
    # alert at 2-3, alert at 6-8, then the log stops during an alert at 11 and resumes at 20 while still on
    write_log(log, [False, False, True, True, False, False, True, True, True, False, False, True] + [None] * 8 + [True, False])
    got = alerts(log, "kyiv", T0 + pd.Timedelta(hours=1))
    assert got["since"] == m(0)
    assert [(a["start"], a["end"]) for a in got["alerts"]] == [(m(11), m(11)), (m(6), m(9)), (m(2), m(4))]
    assert got["alerts"][1]["peak"]["p"]["15m"] == 0.05  # highest clear-time forecast before minute 6
    assert got["alerts"][1]["peak"]["pu"]["15m"] is None

    f = forecasts(log, "kyiv", m(6))
    assert f["t"] == [m(4), m(5), m(6), m(7), m(8), m(9)]  # from the previous alert's end to this one's
    assert f["active"] == [False, False, True, True, True, False]
    assert f["p"]["15m"][:2] == [0.04, 0.05]
    assert forecasts(log, "kyiv", m(7)) is None
