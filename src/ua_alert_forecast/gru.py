"""Sequence model over the city event stream (experiment): a GRU reads the last K events before a forecast.

The tabular models flatten the stream into counts and minutes; order and coincidence are what's lost. This
model reads each forecast row's last K city-relevant events — Kyiv city starts/ends, city-area threats by
weapon, radar-text town mentions (with their Kyiv distance, so the corridor rings are inside), carrier posts —
in order, with minutes-ago scaled. One GRU layer over event embeddings, linear read-out, plain BCE. No hand
features: the question is whether the stream ordering itself adds catch that the counts miss.

Everything here needs torch only when training; building sequences is numpy. Sequences are built from events
strictly before the forecast time, so there is no leakage across the label window.
"""

import numpy as np
import pandas as pd

K = 48  # events per forecast
PAD_ID = 0
CITY_CODES = {"start": 1, "end": 2}
THREAT_CODES = {"drone": 3, "high_speed": 4, "kab": 5, "shelling": 6, "impact": 6, "explosions": 6, "recon": 6, "aviation": 6}
C = 6e10  # ns per minute

import torch  ### all functions below assume torch is importable; guarded by the caller scripts


def event_stream(events: pd.DataFrame, corridor: pd.DataFrame | None, carrier: pd.DataFrame | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Merged city-relevant stream sorted by time: ids (see CITY/THREAT codes, 7 = corridor mention,
    8 = carrier), times (ns) and Kyiv distances (nan where the event has no place meaning)."""
    parts = []
    sel = events[events.oblast.isin(("kyiv", "kyivska"))]
    for kind, code in CITY_CODES.items():
        parts.append((sel[sel.kind == kind], code, np.nan))
    thr = sel[sel.kind == "threat"]
    for detail, code in THREAT_CODES.items():
        parts.append((thr[thr.detail == detail], code, np.nan))
    if corridor is not None and len(corridor):
        parts.append((pd.DataFrame({"ts": pd.to_datetime(corridor.ts, utc=True)}), 7, corridor.dist.to_numpy(float)))
    if carrier is not None and len(carrier):
        parts.append((pd.DataFrame({"ts": pd.to_datetime(carrier.ts, utc=True)}), 8, np.nan))
    ids = np.concatenate([np.full(len(s), code) for s, code, _ in parts if len(s)])
    ts = np.concatenate([s["ts"].to_numpy(dtype="datetime64[ns]").astype(np.int64) for s, *_ in parts if len(s)]).astype(np.int64)
    dist = np.concatenate([np.full(len(s), d) for s, _, d in parts if len(s)]).astype(float)
    order = np.argsort(ts, kind="stable")
    return ids[order], ts[order], dist[order]


def sequences(ids: np.ndarray, ts: np.ndarray, dist: np.ndarray, grid: np.ndarray, k: int = K):
    """(ids, minutes_ago, dist, valid) float grids of shape (rows, k): the last k events before each grid time."""
    idx = np.searchsorted(ts, grid, side="left") - 1  # last event strictly before t
    pos = idx[:, None] + np.arange(-k, 0)[None, :] + 1  # event positions, oldest first
    valid = pos >= 0
    safe = np.clip(pos, 0, len(ts) - 1)
    dt = (grid[:, None] - ts[safe]) / C
    return ids[safe], dt, dist[safe], valid


class Net(torch.nn.Module):
    """Embed(id) cat [log1p(dt), dist/140, has_dist] -> GRU -> linear logit."""

    def __init__(self, n_ids: int = 9, emb: int = 32, hidden: int = 48):
        super().__init__()
        self.embed = torch.nn.Embedding(n_ids, emb, padding_idx=PAD_ID)
        self.gru = torch.nn.GRU(emb + 2, hidden, batch_first=True)
        self.out = torch.nn.Linear(hidden, 1)

    def forward(self, ids, dt, dist, valid):
        e = self.embed(ids)
        has = torch.nan_to_num(dist, nan=0.0) > 0
        d = torch.where(torch.isnan(dist), torch.zeros_like(dist), dist) / 140.0
        x = torch.cat([e, torch.log1p(dt / 30.0)[..., None], d[..., None]], dim=-1)
        mask = valid[..., None].expand(-1, -1, e.shape[-1])  # zeros out padding events
        x = x * mask
        lengths = valid.sum(-1).clamp(min=1)
        packed = torch.nn.utils.rnn.pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, h = self.gru(packed)
        return self.out(h[-1]).squeeze(-1)
