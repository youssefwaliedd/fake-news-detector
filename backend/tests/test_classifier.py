"""Classifier degrades gracefully when no model artifacts are present."""
from app.ml.classifier import predict


def test_predict_without_model_is_neutral():
    result = predict("Some article text that has no trained model behind it.")
    # Shape is always well-formed regardless of whether a model exists.
    assert set(result.keys()) == {"score", "label", "available"}
    assert 0.0 <= result["score"] <= 1.0
    if not result["available"]:
        assert result["label"] == "unknown"
        assert result["score"] == 0.5


def test_predict_empty_text():
    result = predict("   ")
    assert result["label"] == "unknown"
    assert result["available"] is False
