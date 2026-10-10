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

HALF_LIFE_DAYS = 60  # recent tactics count more: a row 60 days old weighs half as much as today's
Calibration = Literal["none", "isotonic", "platt"]


@dataclass(frozen=True)
class Config:
    name: str
    groups: tuple[str, ...] = ("time", "history", "threats", "neighbors", "national")
    family: Literal["lgbm", "logreg"] = "lgbm"
    lgbm: dict = field(default_factory=lambda: {"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31})
    calibration: Calibration = "platt"
    calib_days: int = 21
    members: tuple["Config", ...] = ()  # non-empty: an ensemble averaging these configs' calibrated outputs


@dataclass(frozen=True)
class Split:
    train_end: pd.Timestamp
    calib_end: pd.Timestamp
    test_end: pd.Timestamp

    @classmethod
    def ending(cls, test_end: pd.Timestamp, test_days: int, calib_days: int) -> "Split":
        calib_end = test_end - pd.Timedelta(days=test_days)
        return cls(calib_end - pd.Timedelta(days=calib_days), calib_end, test_end)

    def periods(self, table: pd.DataFrame, horizon: Horizon) -> dict[str, pd.DataFrame]:
        y = f"y_{horizon}"
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


def fit_calibrator(kind: Calibration, raw: np.ndarray, y: np.ndarray) -> Calibrator:
    if kind == "none":
        return Identity()
    if kind == "isotonic":
        return Isotonic(IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(raw, y))
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
    parts = split.periods(table, horizon)
    train, calib, y = parts["train"], parts["calib"], f"y_{horizon}"
    groups = feature_groups(table.columns)
    features = [c for g in config.groups for c in groups[g]]
    weights = 0.5 ** ((split.train_end - train["ts"]).dt.total_seconds() / 86400 / HALF_LIFE_DAYS)
    clf = make_classifier(config, features)
    step = "lgbmclassifier__" if config.family == "lgbm" else "logisticregression__"
    clf.fit(train[features], train[y], **({"sample_weight": weights} if config.family == "lgbm" else {f"{step}sample_weight": weights}))
    calibrator = fit_calibrator(config.calibration, clf.predict_proba(calib[features])[:, 1], calib[y].to_numpy())
    return HorizonModel(horizon, features, clf, calibrator)


def climatology(train: pd.DataFrame, rows: pd.DataFrame, horizon: Horizon) -> np.ndarray:
    """Baseline: training-period siren-start rate for the same region and hour of day."""
    y = f"y_{horizon}"
    key = lambda df: df["region"].astype(str) + "_" + df["hour"].astype(int).astype(str)  # noqa: E731
    rate = train.groupby(key(train))[y].mean()
    return key(rows).map(rate).fillna(train[y].mean()).to_numpy()


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error: |predicted - observed| per probability bin, weighted by bin size."""
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(bins) if (idx == b).any()))


def scores(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    low, high = p < 0.1, p >= 0.9
    return {
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


def evaluate(table: pd.DataFrame, test_end: pd.Timestamp, config: Config, test_days: int = 14):
    """Fit `config` for every horizon on the window ending at `test_end`.

    Returns models, a metrics table (config vs climatology and base-rate baselines) and per-horizon reliability tables.
    """
    split = Split.ending(test_end, test_days, config.calib_days)
    models, rows, rel = {}, [], {}
    for h in HORIZONS:
        model = fit(table, h, split, config)
        parts = split.periods(table, h)
        test, y = parts["test"], parts["test"][f"y_{h}"].to_numpy()
        p = model.predict(test)
        baselines = {"climatology": climatology(parts["train"], test, h), "base_rate": np.full(len(test), parts["train"][f"y_{h}"].mean())}
        for name, pred in {config.name: p, **baselines}.items():
            rows.append({"horizon": h, "predictor": name, "n_test": len(test), "positive_rate": y.mean(), **scores(y, pred)})
        models[h], rel[h] = model, reliability(y, p)
    return models, pd.DataFrame(rows), rel
