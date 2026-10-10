"""Radar-channel post classifier (the "student"): text -> kind, weapon, count, now_in, heading_to. No LLM at run time.

Trained on a sample labeled once by an LLM teacher (prompts/radar_labeling_v2.md, labels in labels/radar_v2/).
v1 (prompts/radar_labeling.md, labels/radar/) had one oblast list mixing "is there" and "is heading there".
Uses character n-grams, which cover Ukrainian word forms ("Вінниччині", "Вінничині", "Вінниця").
The previous post of the same channel is a separate input, so follow-ups like "Мінус" can borrow its place
names without those names counting as the current post's own.

The forecaster is trained on this student's output for all history, the same output it sees live.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import MultiLabelBinarizer

from .geo import REGIONS

PREV_WINDOW = pd.Timedelta(minutes=60)  # a post older than this is not treated as the one being followed up


def with_prev(posts: pd.DataFrame) -> pd.DataFrame:
    """Add `prev`: the previous post's text in the same channel if it came within PREV_WINDOW, else ""."""
    posts = posts.sort_values(["channel", "date"]).copy()
    prev_text = posts.groupby("channel")["text"].shift(1)
    recent = (posts["date"] - posts.groupby("channel")["date"].shift(1)) <= PREV_WINDOW
    posts["prev"] = prev_text.where(recent, "").fillna("")
    return posts


def _vectorizer() -> ColumnTransformer:
    def tfidf() -> TfidfVectorizer:
        return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=60000)

    return ColumnTransformer([("text", tfidf(), "text"), ("prev", tfidf(), "prev")])


ARMED = ["threat", "shot_down", "impact"]
ROLES = ("now_in", "heading_to")  # where the object is now / where it is going but not yet
# Stated object counts are bucketed; an event's weight in the features is its bucket's typical size.
COUNT_WEIGHT = {"none": 1.0, "1": 1.0, "2-3": 2.5, "4+": 6.0}


def count_bucket(count: float | None) -> str:
    if count is None or pd.isna(count):
        return "none"
    return "1" if count <= 1 else "2-3" if count <= 3 else "4+"


@dataclass
class Student:
    kind: Pipeline
    weapon: Pipeline
    count: Pipeline
    places: dict[str, Pipeline]  # "any", "now_in", "heading_to" -> multi-label oblast classifier over REGIONS columns

    @classmethod
    def fit(cls, labeled: pd.DataFrame) -> "Student":
        """`labeled`: columns text, prev, kind, weapon, count, now_in, heading_to (lists of oblast ids)."""
        # Settings chosen by 4-fold cross-validation grouped by chunk on the v1 training labels:
        # class balancing lifted oblast recall from 0.69 to 0.87 at precision 0.91.
        lr = dict(max_iter=3000, C=4.0, class_weight="balanced")
        x = labeled[["text", "prev"]]
        kind = make_pipeline(_vectorizer(), LogisticRegression(**lr)).fit(x, labeled["kind"])
        armed = labeled[labeled["kind"].isin(ARMED)]
        weapon = make_pipeline(_vectorizer(), LogisticRegression(**lr)).fit(armed[["text", "prev"]], armed["weapon"].fillna("unknown"))
        count = make_pipeline(_vectorizer(), LogisticRegression(**lr)).fit(armed[["text", "prev"]], armed["count"].map(count_bucket))
        targets = {"any": [sorted(set(a) | set(b)) for a, b in zip(labeled["now_in"], labeled["heading_to"])]} | {r: labeled[r] for r in ROLES}
        places = {}
        for name, lists in targets.items():
            y = MultiLabelBinarizer(classes=REGIONS).fit_transform(lists)
            seen = y.sum(axis=0) > 0  # oblasts never seen in the sample can't be learned
            clf = make_pipeline(_vectorizer(), OneVsRestClassifier(LogisticRegression(**(lr | {"C": 16.0})))).fit(x, y[:, seen])
            places[name] = (clf, seen)
        return cls(kind, weapon, count, places)

    def _place_proba(self, name: str, x: pd.DataFrame) -> np.ndarray:
        clf, seen = self.places[name]
        out = np.zeros((len(x), len(REGIONS)))
        out[:, seen] = clf.predict_proba(x)
        return out

    def predict(self, posts: pd.DataFrame) -> pd.DataFrame:
        """Columns kind, weapon (None unless armed), count (bucket), now_in, heading_to, aligned with `posts`.

        Which oblasts a post mentions is easy (heldout P .93 / R .87); whether each is "now" or "heading" is
        harder, so one head finds the oblasts and the two role heads only decide the role of each found oblast.
        """
        x = posts[["text", "prev"]]
        kind = self.kind.predict(x)
        armed = np.isin(kind, ARMED)
        found = self._place_proba("any", x) >= 0.5
        is_now = self._place_proba("now_in", x) >= self._place_proba("heading_to", x)
        regions = np.array(REGIONS)
        return pd.DataFrame({
            "kind": kind,
            "weapon": np.where(armed, self.weapon.predict(x), None),
            "count": np.where(armed, self.count.predict(x), "none"),
            "now_in": [list(regions[f & n]) for f, n in zip(found, is_now)],
            "heading_to": [list(regions[f & ~n]) for f, n in zip(found, is_now)],
        }, index=posts.index)


def normalize_teacher(labels: pd.DataFrame) -> pd.DataFrame:
    """Fix the two places where the teacher agents disagreed with each other (found while reviewing their reports).

    - "Бандероль": the posts call it a loitering munition ("баражуючий боєприпас"); agents used shahed, missile or unknown.
    - "ЗБИТО/ПОДАВЛЕНО" daily tallies: the instructions say statistics are `other`; some agents used shot_down.
    """
    labels = labels.copy()
    armed = labels["kind"].isin(ARMED)
    banderol = labels["text"].str.contains("андерол", case=False)
    labels.loc[armed & banderol, "weapon"] = "shahed"
    tally = labels["text"].str.contains("ЗБИТО/ПОДАВЛЕНО", case=False)
    labels.loc[tally, ["kind", "weapon", "count"]] = ["other", None, None]
    for role in ROLES:
        labels.loc[tally, role] = pd.Series([[] for _ in range(tally.sum())], index=labels.index[tally], dtype=object)
    return labels


def load_labels(label_dir: Path, raw_dir: Path) -> pd.DataFrame:
    """Join teacher labels with the raw posts (text, date) and their previous-post context."""
    labels = pd.DataFrame([json.loads(line) for f in sorted(label_dir.glob("chunk_*.jsonl")) for line in f.open()])
    posts = []
    for ch in labels["channel"].unique():
        with (raw_dir / f"{ch}.jsonl").open() as f:
            posts += [{"channel": ch, **json.loads(line)} for line in f]
    posts = pd.DataFrame(posts)[["channel", "id", "date", "text"]]
    posts["date"] = pd.to_datetime(posts["date"], utc=True)
    posts = with_prev(posts[posts["text"].str.strip() != ""])
    return normalize_teacher(labels.merge(posts, on=["channel", "id"], how="inner"))


def to_events(posts: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Input for dataset.build_table: ts, post, kind, weapon, weight, role, oblast.

    One row per (post, role, oblast), plus one row with role "post" and no oblast for every post, so posts that
    name no oblast (launches, take-offs, general ballistic warnings) still count in the national features.
    """
    base = pd.DataFrame({"ts": posts["date"], "post": np.arange(len(posts)), "kind": labels["kind"].to_numpy(),
                         "weapon": labels["weapon"].to_numpy(), "weight": labels["count"].map(COUNT_WEIGHT).to_numpy()})
    parts = [base.assign(role=role, oblast=labels[role].to_numpy()).explode("oblast").dropna(subset=["oblast"]) for role in ROLES]
    parts.append(base.assign(role="post", oblast=None))
    return pd.concat(parts).sort_values("ts", kind="stable").reset_index(drop=True)


def label_history(raw_dir: Path, label_dir: Path, channels: list[str], train_before: pd.Timestamp) -> pd.DataFrame:
    """Train the student on teacher labels dated before `train_before`, then label every post of `channels`.

    The cutoff matters: the student is part of the forecaster, so it must not learn from posts written after
    the forecast times it is evaluated on (e.g. town names that first appear in the test window).
    """
    labeled = load_labels(label_dir, raw_dir)
    student = Student.fit(labeled[labeled["date"] < train_before])
    posts = []
    for ch in channels:
        with (raw_dir / f"{ch}.jsonl").open() as f:
            posts += [{"channel": ch, **json.loads(line)} for line in f]
    posts = pd.DataFrame(posts)[["channel", "id", "date", "text"]]
    posts["date"] = pd.to_datetime(posts["date"], utc=True)
    posts = with_prev(posts[posts["text"].str.strip() != ""])
    return to_events(posts, student.predict(posts))
