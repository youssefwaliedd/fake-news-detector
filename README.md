# Fake News Detector

**🔗 Live demo: https://fake-news-detector-xi-gold.vercel.app**
*(First load may take ~50s while the free-tier backend wakes up.)*

A **hybrid** credibility checker. Paste a claim/article or drop in an article URL, and it returns
a **Real / Fake / Uncertain** verdict with a confidence score, a claim-by-claim breakdown, and
cited web evidence.

Two signals are fused:

1. **ML first-pass** — a TF-IDF + Logistic Regression classifier (scikit-learn) gives an instant
   `P(fake)` with no GPU and a tiny model file.
2. **LLM + evidence retrieval** — a LangGraph pipeline extracts the check-worthy claims, retrieves
   web evidence, and judges each claim, producing an explainable verdict with sources.

The two are blended (`fuse` node). When they disagree strongly, the app reports **Uncertain** and
surfaces both — honest over confident.

> **100% free stack:** [Groq](https://console.groq.com) for the LLM (no credit card), Tavily free
> tier (or keyless DuckDuckGo via `ddgs`) for search, scikit-learn locally.

## Architecture

```
ingest → ml_classify → extract_claims → retrieve_evidence → assess_claims → fuse
```

- **Backend** — FastAPI + LangGraph + `langchain-groq`, in `backend/app/{api,core,graph,ingest,ml,tools}`.
- **Frontend** — Vite + React, with a Server-Sent-Events pipeline timeline.
- **Deploy** — Render (backend) + Vercel (frontend).

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # add your GROQ_API_KEY (+ TAVILY_API_KEY or SEARCH_PROVIDER=ddgs)
uvicorn app.main:app --reload --port 8000
```

The app boots and runs **before** you add keys or train the model — missing pieces degrade
gracefully (neutral ML score, heuristic claim extraction, `uncertain` verdict).

### 2. Train the ML classifier (optional but recommended)

Download the free Kaggle [Fake and Real News Dataset](https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset)
(`Fake.csv` + `True.csv`) into `backend/data/`, then:

```bash
cd backend && source .venv/bin/activate
python -m app.ml.train
```

This writes `model.pkl` + `vectorizer.pkl` to `app/ml/artifacts/` (both gitignored).
Or train on any labeled CSV: `python -m app.ml.train --csv mydata.csv --text-col text --label-col label`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analyze` | Run the full pipeline, return the verdict JSON. |
| `POST` | `/api/analyze/stream` | Same, as Server-Sent Events (node-by-node progress). |
| `GET`  | `/healthz` | Liveness probe. |

Request body: `{ "input": "<article text or URL>" }`.

## Configuration

All settings live in `backend/app/core/config.py` (overridable via env). Key knobs:

| Env | Default | Meaning |
|-----|---------|---------|
| `GROQ_API_KEY` | — | Free Groq key for claim extraction + assessment. |
| `TAVILY_API_KEY` | — | Evidence search (free tier). |
| `SEARCH_PROVIDER` | `tavily` | Set to `ddgs` for keyless/unlimited DuckDuckGo. |
| `ML_WEIGHT` | `0.4` | Weight of the ML signal vs evidence in the fused score. |
| `FAKE_THRESHOLD` / `REAL_THRESHOLD` | `0.60` / `0.40` | Verdict bands on the fused `P(fake)`. |

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

Smoke tests cover ingest, the classifier's graceful-degradation path, and an end-to-end graph run
that needs **no API keys and no trained model**.

---

> ⚠️ **Decision-support tool, not a verdict of truth.** Verdicts are probabilistic and depend on
> the evidence retrieved. Always check the cited sources yourself.
