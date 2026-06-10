"""Assemble the LangGraph state machine.

Linear pipeline:
    ingest -> ml_classify -> extract_claims -> retrieve_evidence -> assess_claims -> fuse
No loops — a credibility judgment is a single forward pass over the evidence.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    assess_claims,
    extract_claims,
    fuse,
    ingest,
    ml_classify,
    retrieve_evidence,
)
from app.graph.state import GraphState

# The ordered nodes — also used by the API/UI to render pipeline progress.
PIPELINE = [
    "ingest",
    "ml_classify",
    "extract_claims",
    "retrieve_evidence",
    "assess_claims",
    "fuse",
]


def build_graph(checkpointer: MemorySaver | None = None):
    """Build and compile the detector graph."""
    g = StateGraph(GraphState)

    g.add_node("ingest", ingest)
    g.add_node("ml_classify", ml_classify)
    g.add_node("extract_claims", extract_claims)
    g.add_node("retrieve_evidence", retrieve_evidence)
    g.add_node("assess_claims", assess_claims)
    g.add_node("fuse", fuse)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "ml_classify")
    g.add_edge("ml_classify", "extract_claims")
    g.add_edge("extract_claims", "retrieve_evidence")
    g.add_edge("retrieve_evidence", "assess_claims")
    g.add_edge("assess_claims", "fuse")
    g.add_edge("fuse", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


@lru_cache
def get_graph():
    """Cached compiled graph for the API layer."""
    return build_graph()
