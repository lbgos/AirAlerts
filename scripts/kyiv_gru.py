"""Train the event-stream GRU on the dev window and score it with the same event metrics as the LGBM configs.

Sequences: for every Kyiv-city forecast row (5-minute grid, city not under alert), the last 48 city-relevant
events (starts, ends, threats by weapon, corridor town mentions with distance, carrier posts) in order. The GRU
never sees the tabular features — this tests the order signal alone. Per dev week: train on everything before
week-14d, calibrate Platt on week-14d..week-7d, forecast the week; pooled + reported like scripts/kyiv_events.py.
Writes reports/kyiv_gru_dev.md and preds npz under the kyiv_events cache for reuse.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from ua_alert_forecast.dataset import HORIZONS, alert_intervals, is_active, load_events
from ua_alert_forecast.events import event_report, bucket, state_stats
from ua_alert_forecast.gru import C, K, Net, event_stream, sequences
from ua_alert_forecast.radar_text import CHANNELS, carrier_events, corridor_events, load_posts
from ua_alert_forecast.config import RAW_DIR

CACHE = Path("/tmp/glm_review/cache")
WEEK = pd.Timedelta(days=7)
EPOCHS = 4
BATCH = 1024


def _logit(r):
    r = np.clip(r, 1e-6, 1 - 1e-6)
    return np.log(r / (1 - r)).reshape(-1, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", choices=["dev", "test"], default="dev")
    parser.add_argument("--horizons", nargs="+", default=["15m", "30m"])
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--channels", nargs="+", default=None, help="corridor text channels; default all")
    parser.add_argument("--k", type=int, default=K)
    args = parser.parse_args()

    torch = __import__("torch")  # late import: this script only runs when we decide to train
    torch.set_num_threads(4)
    events = load_events(RAW_DIR / "UkraineAlarmSignal.jsonl")
    channels = args.channels or CHANNELS
    corridor = corridor_events(load_posts(RAW_DIR, channels))
    car = carrier_events(load_posts(RAW_DIR, CHANNELS))
    ids, ts, dist = event_stream(events, corridor, car)
    city_starts = np.sort(events.loc[(events.oblast == "kyiv") & (events.kind == "start"), "ts"]
                          .to_numpy(dtype="datetime64[ns]").astype(np.int64))
    k_int = alert_intervals(events[events.oblast == "kyiv"])["kyiv"]

    end = pd.Timestamp(int(events.ts.max().value))
    week_ends = sorted([end - WEEK - i * WEEK for i in range(3)]) if args.window == "dev" else [end]
    sirens = bucket(city_starts)

    rows, states = [], []
    for h in args.horizons:
        h_ns = int(HORIZONS[h].value)
        ys, ps, tss, cs = [], [], [], []
        for we in week_ends:
            grid = np.arange((we - WEEK).value + 15 * 6e10, we.value, 5 * 6e10)
            grid = grid[~is_active(k_int, grid)]
            label_ok = grid + h_ns <= int(events.ts.max().value)
            grid = grid[label_ok]
            y = (np.searchsorted(bucket(city_starts), grid + h_ns, side="right")
                 - np.searchsorted(bucket(city_starts), grid, side="right")) > 0  # siren in (t, t+h]
            ids_g, dt_g, dist_g, valid_g = sequences(ids, ts, dist, grid, args.k)
            train_end = (we - 2 * WEEK).value
            in_train, in_calib = grid < train_end, (grid >= train_end) & (grid + h_ns <= (we - WEEK).value)
            train_rows = in_train & (grid + h_ns <= train_end)  # label window purged, matching the tabular splits
            print(f"{h} {we:%m-%d}: rows {len(grid)} train {train_rows.sum()} cal {in_calib.sum()} pos {y.mean():.3f}", flush=True)
            net = Net(n_ids=9)
            opt = torch.optim.Adam(net.parameters(), lr=2e-3)
            x_ids = torch.tensor(ids_g[train_rows], dtype=torch.long)
            x_dt = torch.tensor(dt_g[train_rows], dtype=torch.float32)
            x_d = torch.tensor(np.nan_to_num(dist_g[train_rows], nan=0.0), dtype=torch.float32)
            x_vs = torch.tensor(valid_g[train_rows])
            # dist for non-corridor events is nan; pass 0 and let the dist nons carry the ring information
            x_d = torch.where(torch.isnan(x_d), torch.zeros_like(x_d), x_d)
            yv = torch.tensor(y[train_rows], dtype=torch.float32)
            pos_w = torch.tensor((1 - yv.mean()) / max(yv.mean(), 1e-6), dtype=torch.float32)
            lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pos_w)
            w = 0.5 ** ((train_end - grid[train_rows]) / (60 * 86400 * 6e10))  # same half-life as the tabular configs
            w = torch.tensor(w, dtype=torch.float32)
            n = len(x_ids)
            for epoch in range(args.epochs):
                perm = torch.randperm(n)
                tot = 0.0
                for i in range(0, n, BATCH):
                    b = perm[i:i + BATCH]
                    opt.zero_grad()
                    loss = (lossf(net(x_ids[b], x_dt[b], x_d[b], x_vs[b]).squeeze(-1), yv[b], reduction="none") * w[b]).mean()
                    loss.backward()
                    opt.step()
                    tot += float(loss)
            with torch.no_grad():
                cal_ids = torch.tensor(ids_g[in_calib], dtype=torch.long)
                raw_cal = torch.sigmoid(net(torch.tensor(ids_g[in_calib]), torch.tensor(dt_g[in_calib]),
                                            torch.tensor(np.nan_to_num(dist_g[in_calib], nan=0.0)), torch.tensor(valid_g[in_calib]))).squeeze_().numpy()
            pl = LogisticRegression(max_iter=1000).fit(_logit(raw_cal), y[in_calib])
            with torch.no_grad():
                raw = torch.sigmoid(net(torch.tensor(ids_g), torch.tensor(dt_g),
                                        torch.tensor(np.nan_to_num(dist_g, nan=0.0)), torch.tensor(valid_g))).squeeze_().numpy()
            ps.append(pl.predict_proba(_logit(raw))[:, 1])
            ys.append(y.astype(float))
            tss.append(grid)
            cs.append(np.full(len(grid), y[in_calib].mean()))
            print(f"{h} {we:%m-%d} done, last loss {tot:.4f}", flush=True)
        y, p = np.concatenate(ys), np.concatenate(ps)
        tsv = np.concatenate(tss)
        order = np.argsort(tsv, kind="stable")
        y, p, tsv = y[order], p[order], tsv[order]
        np.savez(CACHE / f"preds_{args.window}_gru_{h}.npz", y=y, p=p, tsv=tsv, cs=np.concatenate(cs)[order])
        siren_set = sirens[(sirens >= tsv[0]) & (sirens < tsv[-1] + h_ns)]
        sw = event_report(p, tsv, y, siren_set, h_ns, (0.2, 0.3, 0.5), 5 * 6e10, 7 * len(week_ends))
        # compare against the k1_kyiv cached preds for the same window
        ref = np.load(CACHE / f"preds_{args.window}_k1_kyiv_{h}.npz")
        ref_sw = event_report(ref["p"], ref["tsv"].astype(np.int64), ref["y"], sirens[(sirens >= ref['tsv'][0]) & (sirens < ref['tsv'][-1] + h_ns)], h_ns, (0.2, 0.3, 0.5), 5*6e10, 7*len(week_ends))
        rows.append(pd.DataFrame({"model": f"gru_{h}", **sw}))
        rows.append(pd.DataFrame({"model": f"k1_kyiv_{h}", **ref_sw}))
    text = ["# Kyiv GRU over the event stream (dev)", "", pd.concat(rows).round(3).to_markdown(index=False)]
    (Path("reports") / f"kyiv_gru_{args.window}.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    main()
