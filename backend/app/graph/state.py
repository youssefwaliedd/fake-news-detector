"""The shared LangGraph state — the contract every node reads from and writes to.

Each node is a ``node(state) -> dict`` that returns ONLY the keys it updates;
LangGraph merges those into the running state. The pipeline is linear:

    ingest -> ml_classify -> extract_claims -> retrieve_evidence -> assess_claims -> fuse
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages

MLLabel = Literal["real", "fake", "unknown"]
ClaimVerdict = Literal["supported", "refuted", "unverified"]
FinalLabel = Literal["real", "fake", "uncertain"]


class Source(TypedDict):
    title: str
    url: str


class Evidence(TypedDict):
    """Search results gathered for a single claim."""

    claim: str
    results: list[dict]            # SearchResult items from tools.search


class ClaimAssessment(TypedDict):
    claim: str
    verdict: ClaimVerdict
    confidence: float
    rationale: str
    sources: list[Source]


class GraphState(TypedDict, total=False):
    # ---- input ----
    raw_input: str                 # pasted text or a URL
    # ---- ingest ----
    article_title: str
    article_text: str
    source: str                    # URL or "text"
    # ---- ml first-pass ----
    ml_score: float                # P(fake) 0..1
    ml_label: MLLabel
    ml_available: bool
    # ---- llm + evidence ----
    claims: list[str]
    evidence: list[Evidence]
    assessments: list[ClaimAssessment]
    # ---- fusion / output ----
    final_label: Optional[FinalLabel]
    final_confidence: float        # 0..1 confidence in the final label
    fake_probability: float        # fused P(fake) 0..1
    sources: list[Source]
    rationale: str                 # one-paragraph human-readable explanation
    # ---- trace ----
    log: Annotated[list, add_messages]
