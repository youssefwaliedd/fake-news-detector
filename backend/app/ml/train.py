"""Train the TF-IDF + LogisticRegression fake-news classifier.

Dataset (free): Kaggle "Fake and Real News Dataset" — two CSVs, ``Fake.csv`` and
``True.csv`` (column ``text``). Drop them in ``backend/data/`` and run:

    cd backend
    python -m app.ml.train

Or point at a single labeled CSV with ``--csv path --text-col text --label-col label``
(label values: 1/fake/false == fake, 0/real/true == real).

Artifacts (``model.pkl`` + ``vectorizer.pkl``) are written to app/ml/artifacts/ and
loaded by classifier.py at request time.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import ARTIFACTS_DIR, DATA_DIR

_FAKE_TOKENS = {"1", "fake", "false", "fake_news"}


def _load_two_file(data_dir: Path):
    """Load the classic Fake.csv / True.csv layout into (texts, labels)."""
    import pandas as pd

    fake_csv, true_csv = data_dir / "Fake.csv", data_dir / "True.csv"
    if not fake_csv.exists() or not true_csv.exists():
        return None
    fake = pd.read_csv(fake_csv)
    true = pd.read_csv(true_csv)
    text_col = "text" if "text" in fake.columns else fake.columns[-1]
    texts = list(fake[text_col].astype(str)) + list(true[text_col].astype(str))
    labels = [1] * len(fake) + [0] * len(true)  # 1 == fake
    return texts, labels


def _load_single(csv: Path, text_col: str, label_col: str):
    import pandas as pd

    df = pd.read_csv(csv).dropna(subset=[text_col, label_col])
    texts = list(df[text_col].astype(str))
    labels = [1 if str(v).strip().lower() in _FAKE_TOKENS else 0 for v in df[label_col]]
    return texts, labels


def train(texts: list[str], labels: list[int]) -> None:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split
    import joblib

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    vectorizer = TfidfVectorizer(
        stop_words="english", max_features=20000, ngram_range=(1, 2), min_df=2
    )
    Xtr = vectorizer.fit_transform(X_train)
    Xte = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000, C=4.0)
    model.fit(Xtr, y_train)

    print(classification_report(y_test, model.predict(Xte), target_names=["real", "fake"]))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, ARTIFACTS_DIR / "vectorizer.pkl")
    joblib.dump(model, ARTIFACTS_DIR / "model.pkl")
    print(f"Saved artifacts to {ARTIFACTS_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the fake-news classifier.")
    parser.add_argument("--csv", help="Single labeled CSV (instead of Fake.csv/True.csv).")
    parser.add_argument("--text-col", default="text")
    parser.add_argument("--label-col", default="label")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()

    if args.csv:
        texts, labels = _load_single(Path(args.csv), args.text_col, args.label_col)
    else:
        loaded = _load_two_file(Path(args.data_dir))
        if loaded is None:
            print(
                f"No dataset found. Put Fake.csv and True.csv in {args.data_dir} "
                f"(Kaggle 'Fake and Real News Dataset'), or pass --csv. ",
                file=sys.stderr,
            )
            return 1
        texts, labels = loaded

    print(f"Training on {len(texts)} documents ({sum(labels)} fake / {len(labels) - sum(labels)} real)…")
    train(texts, labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
