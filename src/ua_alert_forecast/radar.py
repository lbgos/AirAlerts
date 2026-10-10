"""Radar-channel post classifier (the "student"): text -> kind, weapon, oblasts. No LLM at run time.

Trained on a sample labeled once by an LLM teacher (prompts/radar_labeling.md, labels in data/radar_labels/).
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


@dataclass
class Student:
    kind: Pipeline
    weapon: Pipeline
    oblasts: Pipeline
    oblast_classes: list[str]

    @classmethod
    def fit(cls, labeled: pd.DataFrame) -> "Student":
        """`labeled`: columns text, prev, kind, weapon, oblasts (list[str])."""
        # Settings chosen by 4-fold cross-validation grouped by chunk on the training labels:
        # class balancing lifted oblast recall from 0.69 to 0.87 at precision 0.91.
        lr = dict(max_iter=3000, C=4.0, class_weight="balanced")
        kind = make_pipeline(_vectorizer(), LogisticRegression(**lr)).fit(labeled[["text", "prev"]], labeled["kind"])
        armed = labeled[labeled["kind"].isin(["threat", "shot_down", "impact"])]
        weapon = make_pipeline(_vectorizer(), LogisticRegression(**lr)).fit(armed[["text", "prev"]], armed["weapon"].fillna("unknown"))
        mlb = MultiLabelBinarizer(classes=REGIONS)
        y = mlb.fit_transform(labeled["oblasts"])
        seen = y.sum(axis=0) > 0  # oblasts never seen in the sample can't be learned
        oblasts = make_pipeline(_vectorizer(), OneVsRestClassifier(LogisticRegression(**(lr | {"C": 16.0})))).fit(labeled[["text", "prev"]], y[:, seen])
        return cls(kind, weapon, oblasts, [r for r, s in zip(REGIONS, seen) if s])

    def predict(self, posts: pd.DataFrame) -> pd.DataFrame:
        """Columns kind, weapon (None unless armed), oblasts (list[str]) aligned with `posts`."""
        x = posts[["text", "prev"]]
        kind = self.kind.predict(x)
        weapon = np.where(np.isin(kind, ["threat", "shot_down", "impact"]), self.weapon.predict(x), None)
        hits = self.oblasts.predict_proba(x) >= 0.5
        oblasts = [[c for c, h in zip(self.oblast_classes, row) if h] for row in hits]
        return pd.DataFrame({"kind": kind, "weapon": weapon, "oblasts": oblasts}, index=posts.index)


def normalize_teacher(labels: pd.DataFrame) -> pd.DataFrame:
    """Fix the two places where the 10 teacher agents disagreed with each other (found while reviewing their reports).

    - "Бандероль": the posts call it a loitering munition ("баражуючий боєприпас"); agents used shahed, missile or unknown.
    - "ЗБИТО/ПОДАВЛЕНО" daily tallies: the instructions say statistics are `other`; some agents used shot_down.
    """
    labels = labels.copy()
    armed = labels["kind"].isin(["threat", "shot_down", "impact"])
    banderol = labels["text"].str.contains("андерол", case=False)
    labels.loc[armed & banderol, "weapon"] = "shahed"
    tally = labels["text"].str.contains("ЗБИТО/ПОДАВЛЕНО", case=False)
    labels.loc[tally, "kind"] = "other"
    labels.loc[tally, "weapon"] = None
    labels.loc[tally, "oblasts"] = pd.Series([[] for _ in range(tally.sum())], index=labels.index[tally], dtype=object)
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
    """One row per (post, oblast) for posts with a place: ts, kind, weapon, oblast. Input for dataset.build_table."""
    df = pd.DataFrame({"ts": posts["date"], "kind": labels["kind"], "weapon": labels["weapon"], "oblast": labels["oblasts"]})
    df = df.explode("oblast").dropna(subset=["oblast"])
    return df.sort_values("ts", kind="stable").reset_index(drop=True)


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
