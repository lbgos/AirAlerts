"""Train, calibrate and evaluate siren-start models, one per horizon.

Time split, oldest to newest: train | calibrate | test. A row belongs to a period only if its whole
label window (T, T + horizon] fits inside it, so no label peeks into the next period.
The classifier gives raw scores; a calibrator fitted on the calibration period maps them to
probabilities that match observed frequencies (the "70% means 70%" property).

A `Config` describes one variant (feature groups, model family and settings, calibration);
`experiments.py` compares variants, `train.py` fits the chosen one.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .dataset import HORIZONS, Horizon, feature_groups
from .geo import FRONTLINE

HALF_LIFE_DAYS = 60  # recent tactics count more: a row 60 days old weighs half as much as today's
Calibration = Literal["none", "isotonic", "platt", "conservative"]
# Overconfidence punishment. A forecast is "confident" at <= 20% or >= 80%; a confident forecast that turns out wrong
# costs CONFIDENT_WRONG_WEIGHT times its log loss in `penalty`. The conservative calibrator caps every forecast at the
# Wilson bound (z = BOUND_Z, about 99%) of how often forecasts at that level came true on the calibration days.
CONFIDENT = 0.2
CONFIDENT_WRONG_WEIGHT = 10.0
# Reward side, used by `points`: a confident forecast that turned out right counts this many times its gain over
# climatology.
CONFIDENT_RIGHT_WEIGHT = 3.0
BOUND_Z = 2.576
CONSERVATIVE_BINS = 20
Target = Literal["start", "clear"]  # siren starts (rows not under alert) / all-clear comes (rows under alert)


@dataclass(frozen=True)
class Config:
    name: str
    groups: tuple[str, ...] = ("time", "history", "threats", "neighbors", "national")
    family: Literal["lgbm", "logreg"] = "lgbm"
    lgbm: dict = field(default_factory=lambda: {"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31})
    calibration: Calibration = "platt"
    calib_days: int = 21
    members: tuple["Config", ...] = ()  # non-empty: an ensemble averaging these configs' calibrated outputs
    target: Target = "start"
    bound_z: float = BOUND_Z  # conservative calibration only: width of the Wilson bound (bigger = more cautious)
    step_minutes: int = 15  # forecast grid of the table `forecast train` / `fit-live` build for this config
    train_grid_minutes: int | None = None  # keep only train/calib rows on this grid (e.g. 15 on a 5-minute table)
    train_since: str | None = None  # drop training rows before this date (a regime change, e.g. the 2026-09 alert reform)
    half_life_days: float = HALF_LIFE_DAYS  # sample weight halves every this many days back
    regions: tuple[str, ...] | None = None  # train and calibrate on these regions only (e.g. ("kyiv",))


def label(target: Target, horizon: Horizon) -> str:
    return f"y_{horizon}" if target == "start" else f"yc_{horizon}"


@dataclass(frozen=True)
class Split:
    train_end: pd.Timestamp
    calib_end: pd.Timestamp
    test_end: pd.Timestamp

    @classmethod
    def ending(cls, test_end: pd.Timestamp, test_days: int, calib_days: int) -> "Split":
        calib_end = test_end - pd.Timedelta(days=test_days)
        return cls(calib_end - pd.Timedelta(days=calib_days), calib_end, test_end)

    def periods(self, table: pd.DataFrame, horizon: Horizon, target: Target = "start") -> dict[str, pd.DataFrame]:
        y = label(target, horizon)
        if "active" in table.columns:  # tables built with keep_active hold both kinds of rows
            table = table[table["active"] == (target == "clear")]
        ts, label_end = table["ts"], table["ts"] + HORIZONS[horizon]
        known = table[y].notna()
        return {
            "train": table[known & (label_end <= self.train_end)],
            "calib": table[known & (ts >= self.train_end) & (label_end <= self.calib_end)],
            "test": table[known & (ts >= self.calib_end) & (label_end <= self.test_end)],
        }


class Calibrator(Protocol):
    def __call__(self, raw: np.ndarray) -> np.ndarray: ...


def _logit(r: np.ndarray) -> np.ndarray:
    r = np.clip(r, 1e-6, 1 - 1e-6)
    return np.log(r / (1 - r)).reshape(-1, 1)


@dataclass
class Identity:
    def __call__(self, raw: np.ndarray) -> np.ndarray:
        return raw


@dataclass
class Isotonic:
    iso: IsotonicRegression

    def __call__(self, raw: np.ndarray) -> np.ndarray:
        return self.iso.predict(raw)


@dataclass
class Platt:
    """Logistic regression on the raw score's logit. Smooth and monotone, so it can't jump to 0 or 1."""

    lr: LogisticRegression

    def __call__(self, raw: np.ndarray) -> np.ndarray:
        return self.lr.predict_proba(_logit(raw))[:, 1]


def wilson(k: np.ndarray, n: np.ndarray, z: float = BOUND_Z) -> tuple[np.ndarray, np.ndarray]:
    """Lower and upper Wilson score bounds for k successes out of n."""
    phat = k / n
    centre = (phat + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


@dataclass
class Conservative:
    """Platt, then no forecast may claim more certainty than the calibration days support.

    Calibration-day forecasts are split into CONSERVATIVE_BINS equal-size bins by Platt probability. In bins above 50%
    a forecast is capped at the lower Wilson bound of how often those forecasts came true; below 50% it is raised to the
    upper bound. Few cases or overconfidence -> wide bound -> the forecast is pulled toward 50%.
    """

    platt: Platt
    centres: np.ndarray  # mean Platt probability per bin
    cap: np.ndarray  # highest allowed forecast at that level
    floor: np.ndarray  # lowest allowed forecast at that level

    def __call__(self, raw: np.ndarray) -> np.ndarray:
        p = self.platt(raw)
        return np.clip(p, np.interp(p, self.centres, self.floor), np.interp(p, self.centres, self.cap))

    @classmethod
    def fit(cls, raw: np.ndarray, y: np.ndarray, z: float = BOUND_Z) -> "Conservative":
        platt = Platt(LogisticRegression().fit(_logit(raw), y))
        p = platt(raw)
        order = np.argsort(p)
        bins = np.array_split(order, CONSERVATIVE_BINS)
        centres = np.array([p[b].mean() for b in bins])
        lo, hi = wilson(np.array([y[b].sum() for b in bins], dtype=float), np.array([len(b) for b in bins], dtype=float), z)
        high = centres >= 0.5
        # Monotone and never looser than any bin's own bound: caps take the running minimum from the top,
        # floors the running maximum from the bottom. The other half of the range inherits the nearest value.
        cap = np.minimum.accumulate(np.where(high, lo, 1.0)[::-1])[::-1]
        cap = np.where(high, cap, cap[high][0] if high.any() else 1.0)
        floor = np.maximum.accumulate(np.where(~high, hi, 0.0))
        floor = np.where(~high, floor, floor[~high][-1] if (~high).any() else 0.0)
        return cls(platt, centres, cap, floor)


def fit_calibrator(kind: Calibration, raw: np.ndarray, y: np.ndarray, z: float = BOUND_Z) -> Calibrator:
    if kind == "none":
        return Identity()
    if kind == "isotonic":
        return Isotonic(IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(raw, y))
    if kind == "conservative":
        return Conservative.fit(raw, y, z)
    return Platt(LogisticRegression().fit(_logit(raw), y))


@dataclass
class HorizonModel:
    horizon: Horizon
    features: list[str]
    classifier: object  # LGBMClassifier or sklearn Pipeline; both expose predict_proba
    calibrator: Calibrator

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        return self.calibrator(self.classifier.predict_proba(rows[self.features])[:, 1])


@dataclass
class Ensemble:
    members: list[HorizonModel]

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        return np.mean([m.predict(rows) for m in self.members], axis=0)


def make_classifier(config: Config, features: list[str]):
    if config.family == "lgbm":
        params = {"min_child_samples": 50, "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "verbose": -1}
        return lgb.LGBMClassifier(**(params | config.lgbm))
    numeric = [f for f in features if f != "region"]
    columns = ColumnTransformer([("region", OneHotEncoder(handle_unknown="ignore"), ["region"]), ("num", StandardScaler(), numeric)])
    return make_pipeline(columns, LogisticRegression(max_iter=2000))


def fit(table: pd.DataFrame, horizon: Horizon, split: Split, config: Config) -> HorizonModel | Ensemble:
    if config.members:
        return Ensemble([fit(table, horizon, split, m) for m in config.members])
    parts = split.periods(table, horizon, config.target)
    train, calib, y = parts["train"], parts["calib"], label(config.target, horizon)
    if config.train_grid_minutes:
        on_grid = lambda df: df[df["ts"].dt.minute % config.train_grid_minutes == 0]  # noqa: E731
        train, calib = on_grid(train), on_grid(calib)
    if config.train_since:
        train = train[train["ts"] >= pd.Timestamp(config.train_since, tz="UTC")]
    if config.regions:
        train, calib = train[train["region"].isin(config.regions)], calib[calib["region"].isin(config.regions)]
    groups = feature_groups(table.columns)
    features = [c for g in config.groups for c in groups[g]]
    weights = 0.5 ** ((split.train_end - train["ts"]).dt.total_seconds() / 86400 / config.half_life_days)
    clf = make_classifier(config, features)
    step = "lgbmclassifier__" if config.family == "lgbm" else "logisticregression__"
    clf.fit(train[features], train[y], **({"sample_weight": weights} if config.family == "lgbm" else {f"{step}sample_weight": weights}))
    calibrator = fit_calibrator(config.calibration, clf.predict_proba(calib[features])[:, 1], calib[y].to_numpy(), config.bound_z)
    return HorizonModel(horizon, features, clf, calibrator)


def climatology(train: pd.DataFrame, rows: pd.DataFrame, y: str) -> np.ndarray:
    """Baseline: training-period event rate (column `y`) for the same region and hour of day."""
    key = lambda df: df["region"].astype(str) + "_" + df["hour"].astype(int).astype(str)  # noqa: E731
    rate = train.groupby(key(train))[y].mean()
    return key(rows).map(rate).fillna(train[y].mean()).to_numpy()


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error: |predicted - observed| per probability bin, weighted by bin size."""
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(bins) if (idx == b).any()))


def penalty(y: np.ndarray, p: np.ndarray) -> float:
    """Log loss where every confident forecast that turned out wrong counts CONFIDENT_WRONG_WEIGHT times."""
    p = np.clip(p, 1e-4, 1 - 1e-4)
    loss = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    wrong = ((p >= 1 - CONFIDENT) & (y == 0)) | ((p <= CONFIDENT) & (y == 1))
    return float(np.mean(loss * np.where(wrong, CONFIDENT_WRONG_WEIGHT, 1.0)))


def points(y: np.ndarray, p: np.ndarray, clim: np.ndarray) -> float:
    """Reward and punishment in one number, higher is better: per forecast, the log2 score gained over climatology
    (positive when the model put more probability on what happened). Confident forecasts that were right count
    CONFIDENT_RIGHT_WEIGHT times, confident ones that were wrong CONFIDENT_WRONG_WEIGHT times. Reported per 100 forecasts.
    """
    p, clim = np.clip(p, 1e-4, 1 - 1e-4), np.clip(clim, 1e-4, 1 - 1e-4)
    gain = np.where(y == 1, np.log2(p / clim), np.log2((1 - p) / (1 - clim)))
    confident = (p <= CONFIDENT) | (p >= 1 - CONFIDENT)
    right = (p >= 0.5) == (y == 1)
    weight = np.where(confident, np.where(right, CONFIDENT_RIGHT_WEIGHT, CONFIDENT_WRONG_WEIGHT), 1.0)
    return float(100 * np.mean(weight * gain))


def scores(y: np.ndarray, p: np.ndarray, clim: np.ndarray | None = None) -> dict[str, float]:
    low, high = p < 0.1, p >= 0.9
    confident = (p <= CONFIDENT) | (p >= 1 - CONFIDENT)
    wrong = confident & ((p >= 0.5) != (y == 1))
    return {
        "points": points(y, p, clim) if clim is not None else float("nan"),
        "penalty": penalty(y, p),
        # Of the confident forecasts, the share that turned out wrong, and the share they promised at most
        # (a 90% forecast promises to be wrong 10% of the time).
        "conf_wrong": wrong.sum() / confident.sum() if confident.any() else float("nan"),
        "conf_promised": np.minimum(p, 1 - p)[confident].mean() if confident.any() else float("nan"),
        "n_conf": int(confident.sum()),
        # Share of all forecasts that were confident and right: what the reward side pays for.
        "conf_right": (confident & ~wrong).mean(),
        "brier": brier_score_loss(y, p),
        "log_loss": log_loss(y, np.clip(p, 1e-4, 1 - 1e-4), labels=[0, 1]),
        "auc": roc_auc_score(y, p) if 0 < y.mean() < 1 else float("nan"),
        "ece": ece(y, p),
        # The two ends users act on: "almost surely not" and "almost surely yes".
        "low_pred": p[low].mean() if low.any() else float("nan"),
        "low_obs": y[low].mean() if low.any() else float("nan"),
        "high_pred": p[high].mean() if high.any() else float("nan"),
        "high_obs": y[high].mean() if high.any() else float("nan"),
        "n_high": int(high.sum()),
    }


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Per probability bin: how many forecasts, mean predicted, observed frequency."""
    df = pd.DataFrame({"bin": np.minimum((p * bins).astype(int), bins - 1), "p": p, "y": y})
    out = df.groupby("bin").agg(n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean"))
    out.index = [f"{b / bins:.1f}-{(b + 1) / bins:.1f}" for b in out.index]
    return out


def evaluate(table: pd.DataFrame, test_end: pd.Timestamp, config: Config, test_days: int = 14, horizons=tuple(HORIZONS)):
    """Fit `config` for every horizon on the window ending at `test_end`.

    Returns models, a metrics table (config vs climatology and base-rate baselines, for all regions and for the
    rear subset) and per-horizon reliability tables (all regions).
    """
    split = Split.ending(test_end, test_days, config.calib_days)
    models, rows, rel = {}, [], {}
    for h in horizons:
        model = fit(table, h, split, config)
        parts = split.periods(table, h, config.target)
        col = label(config.target, h)
        test, y = parts["test"], parts["test"][col].to_numpy()
        p = model.predict(test)
        baselines = {"climatology": climatology(parts["train"], test, col), "base_rate": np.full(len(test), parts["train"][col].mean())}
        subsets = {"all": np.ones(len(test), dtype=bool), "rear": ~test["region"].isin(FRONTLINE).to_numpy()}
        for subset, m in subsets.items():
            for name, pred in {config.name: p, **baselines}.items():
                rows.append({"subset": subset, "horizon": h, "predictor": name, "n_test": int(m.sum()), "positive_rate": y[m].mean(),
                             **scores(y[m], pred[m], baselines["climatology"][m])})
        models[h], rel[h] = model, reliability(y, p)
    return models, pd.DataFrame(rows), rel
