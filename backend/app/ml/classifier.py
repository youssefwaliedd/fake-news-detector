"""TF-IDF + LogisticRegression first-pass credibility classifier.

This is the *fast* signal in the hybrid pipeline: it returns an instant P(fake)
for a piece of text with no network call and no GPU. The trained artifacts
(vectorizer + model) are produced by ``app.ml.train`` and loaded lazily here.

Graceful degradation: if the artifacts are missing (e.g. before you've trained),
``predict`` returns a neutral score of 0.5 / label "unknown" so the whole app
still boots and runs end-to-end.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import joblib

from app.core.config import get_settings

logger = logging.getLogger("ml.classifier")


class MLResult(TypedDict):
    score: float          # P(fake), 0..1
    label: str            # "real" | "fake" | "unknown"
    available: bool       # False when no trained model was found


@lru_cache(maxsize=1)
def _load():
    """Load (vectorizer, model) once. Returns (None, None) if artifacts are absent."""
    settings = get_settings()
    vec_path = Path(settings.vectorizer_path)
    model_path = Path(settings.model_path)
    if not vec_path.exists() or not model_path.exists():
        logger.warning(
            "ml_artifacts_missing",
            extra={"vectorizer": str(vec_path), "model": str(model_path)},
        )
        return None, None
    return joblib.load(vec_path), joblib.load(model_path)


def predict(text: str) -> MLResult:
    """Return P(fake) for ``text`` using the trained TF-IDF + LogReg model."""
    vectorizer, model = _load()
    if vectorizer is None or model is None or not (text or "").strip():
        return MLResult(score=0.5, label="unknown", available=False)

    features = vectorizer.transform([text])
    # Convention (see train.py): class 1 == "fake".
    proba = float(model.predict_proba(features)[0][1])
    label = "fake" if proba >= 0.5 else "real"
    return MLResult(score=round(proba, 4), label=label, available=True)
