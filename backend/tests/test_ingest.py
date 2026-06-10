"""Ingest: URL detection + text passthrough."""
from app.ingest.extract import extract, looks_like_url


def test_looks_like_url():
    assert looks_like_url("https://example.com/article")
    assert looks_like_url("http://news.site/path?a=1")
    assert not looks_like_url("The president said the economy grew.")
    assert not looks_like_url("not a url with spaces https://x.com")


def test_extract_plain_text_passthrough():
    text = "Scientists confirmed water on the moon in a 2020 study."
    article = extract(text)
    assert article["source"] == "text"
    assert article["text"] == text
    assert article["title"] == ""
