"""FastAPI endpoints.

POST /api/analyze         : run the full pipeline, return the verdict as JSON.
POST /api/analyze/stream  : run the pipeline as Server-Sent Events, emitting
                            node-by-node progress so the UI can animate it:
  - node_start  : a node began            {"node": "ingest"}
  - node_output : a node produced output  {"node": "...", "summary": "..."}
  - final       : the run is complete      {"result": {...}}
  - error       : something failed         {"message": "..."}
GET  /healthz             : liveness probe.
"""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.graph.build_graph import PIPELINE, get_graph
from app.graph.state import GraphState

router = APIRouter()

# Human-friendly labels for the UI timeline.
NODE_LABELS = {
    "ingest": "Reading input",
    "ml_classify": "ML first-pass",
    "extract_claims": "Extracting claims",
    "retrieve_evidence": "Gathering evidence",
    "assess_claims": "Checking claims",
    "fuse": "Final verdict",
}


class AnalyzeRequest(BaseModel):
    input: str = Field(min_length=3, max_length=20000, description="Article text or a URL.")


def _initial_state(req: AnalyzeRequest) -> GraphState:
    return {
        "raw_input": req.input.strip(),
        "claims": [],
        "evidence": [],
        "assessments": [],
        "sources": [],
        "log": [],
    }


def _result_view(state: dict) -> dict:
    """Project the full graph state down to the public result payload."""
    return {
        "label": state.get("final_label"),
        "confidence": state.get("final_confidence", 0.0),
        "fake_probability": state.get("fake_probability"),
        "rationale": state.get("rationale", ""),
        "ml": {
            "label": state.get("ml_label", "unknown"),
            "score": state.get("ml_score", 0.5),
            "available": state.get("ml_available", False),
        },
        "article_title": state.get("article_title", ""),
        "source": state.get("source", ""),
        "claims": [
            {
                "claim": a.get("claim", ""),
                "verdict": a.get("verdict", "unverified"),
                "confidence": a.get("confidence", 0.0),
                "rationale": a.get("rationale", ""),
                "sources": a.get("sources", []),
            }
            for a in state.get("assessments", [])
        ],
        "sources": state.get("sources", []),
    }


def summarize_update(node: str, update: dict) -> dict:
    """Short, human-readable summary of what a node produced (for the SSE feed)."""
    log = update.get("log") or []
    summary = log[-1] if log else NODE_LABELS.get(node, "Working…")
    return {"node": node, "label": NODE_LABELS.get(node, node), "summary": summary}


@router.post("/api/analyze")
async def analyze(req: AnalyzeRequest) -> dict:
    graph = get_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    final_state = await graph.ainvoke(_initial_state(req), config=config)
    return _result_view(final_state)


async def _event_stream(req: AnalyzeRequest) -> AsyncIterator[dict]:
    graph = get_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    final_state: dict = {}

    try:
        async for event in graph.astream_events(_initial_state(req), config=config, version="v2"):
            kind, name = event.get("event"), event.get("name")
            if name not in PIPELINE:
                continue
            if kind == "on_chain_start":
                yield {"event": "node_start", "data": json.dumps({"node": name, "label": NODE_LABELS.get(name, name)})}
            elif kind == "on_chain_end":
                output = event.get("data", {}).get("output") or {}
                if isinstance(output, dict):
                    final_state = {**final_state, **output}
                    yield {"event": "node_output", "data": json.dumps(summarize_update(name, output))}

        yield {"event": "final", "data": json.dumps({"result": _result_view(final_state)})}
    except Exception as exc:  # noqa: BLE001 - surface failure to the client
        yield {"event": "error", "data": json.dumps({"message": str(exc)})}


@router.post("/api/analyze/stream")
async def analyze_stream(req: AnalyzeRequest) -> EventSourceResponse:
    # ping every 10s keeps the connection alive through free-tier backoffs.
    return EventSourceResponse(_event_stream(req), ping=10)


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
