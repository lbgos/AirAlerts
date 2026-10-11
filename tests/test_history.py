import json

import pandas as pd

from ua_alert_forecast.history import alerts, forecasts

T0 = pd.Timestamp("2026-10-11T12:00:00+00:00")


def write_log(path, states: list[bool | None]) -> None:
    """One poll per minute from T0; None = no poll (logging gap)."""
    with path.open("w") as f:
        for i, active in enumerate(states):
            if active is not None:
                p = {"15m": i / 100, "1h": i / 50}
                f.write(json.dumps({"t": (T0 + pd.Timedelta(minutes=i)).isoformat(), "regions": {"kyiv": {"active": active, "p": p}}}) + "\n")


def test_alerts_and_forecasts(tmp_path):
    log = tmp_path / "predictions.jsonl"
    # alert at 2-3, alert at 6-8, then the log stops during an alert at 11 and resumes at 20 while still on
    write_log(log, [False, False, True, True, False, False, True, True, True, False, False, True] + [None] * 8 + [True, False])
    got = alerts(log, "kyiv", T0 + pd.Timedelta(hours=1))
    m = lambda i: int((T0 + pd.Timedelta(minutes=i)).timestamp())
    assert got["since"] == m(0)
    assert got["alerts"] == [{"start": m(11), "end": m(11)}, {"start": m(6), "end": m(9)}, {"start": m(2), "end": m(4)}]

    f = forecasts(log, "kyiv", m(6), m(9))
    assert f["before_start"]["t"] == [m(4), m(5)]  # only since the previous alert ended
    assert f["before_end"]["t"] == [m(6), m(7), m(8)]
    assert f["before_start"]["p"]["15m"] == [0.04, 0.05]
    assert f["before_start"]["pu"]["15m"] == [None, None]
