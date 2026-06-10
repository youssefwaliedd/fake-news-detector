"""The six pipeline nodes.

Every node is written to *work* when API keys are present and to *degrade
gracefully* when they are not, so the app boots and returns well-formed JSON
even before you've added a GROQ key or trained the ML model. Each node is the
real implementation behind a stable interface — later phases only refine prompts
and tuning, not the shape of the graph.
"""
from __future__ import annotations

import logging
import re

from app.core.config import get_settings
from app.core.llm import extract_json, get_llm
from app.core.logging import timed_node
from app.graph.state import (
    ClaimAssessment,
    Evidence,
    GraphState,
    Source,
)
from app.ingest.extract import extract
from app.ml.classifier import predict as ml_predict
from app.prompts import (
    CLAIM_ASSESSMENT_SYSTEM,
    CLAIM_ASSESSMENT_USER,
    CLAIM_EXTRACTION_SYSTEM,
    CLAIM_EXTRACTION_USER,
)
from app.tools.search import search

logger = logging.getLogger("graph.nodes")

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _has_groq() -> bool:
    return bool(get_settings().groq_api_key.strip())


# --------------------------------------------------------------------------- #
# 1. ingest                                                                    #
# --------------------------------------------------------------------------- #
@timed_node("ingest")
def ingest(state: GraphState) -> dict:
    article = extract(state.get("raw_input", ""))
    note = (
        f"Ingested {len(article['text'])} chars from {article['source']}."
        if article["text"]
        else f"Could not extract text from {article['source']}."
    )
    return {
        "article_title": article["title"],
        "article_text": article["text"],
        "source": article["source"],
        "log": [note],
    }


# --------------------------------------------------------------------------- #
# 2. ml_classify                                                               #
# --------------------------------------------------------------------------- #
@timed_node("ml_classify")
def ml_classify(state: GraphState) -> dict:
    result = ml_predict(state.get("article_text", ""))
    return {
        "ml_score": result["score"],
        "ml_label": result["label"],
        "ml_available": result["available"],
        "log": [
            f"ML first-pass: {result['label']} (P_fake={result['score']:.2f}"
            f"{'' if result['available'] else ', model not trained'})."
        ],
    }


# --------------------------------------------------------------------------- #
# 3. extract_claims                                                            #
# --------------------------------------------------------------------------- #
@timed_node("extract_claims")
def extract_claims(state: GraphState) -> dict:
    text = (state.get("article_text") or "").strip()
    if not text:
        return {"claims": [], "log": ["No text to extract claims from."]}

    settings = get_settings()
    if _has_groq():
        try:
            llm = get_llm("extractor")
            messages = [
                ("system", CLAIM_EXTRACTION_SYSTEM.format(max_claims=settings.max_claims)),
                ("user", CLAIM_EXTRACTION_USER.format(text=text[:6000])),
            ]
            data = extract_json(llm.invoke(messages).content)
            claims = [c.strip() for c in data.get("claims", []) if c.strip()][: settings.max_claims]
            return {"claims": claims, "log": [f"Extracted {len(claims)} check-worthy claims."]}
        except Exception as exc:  # noqa: BLE001 - fall back to heuristic
            logger.warning("claim_extraction_failed", extra={"error": str(exc)})

    # Heuristic fallback (no LLM key): take the first few substantial sentences.
    sentences = [s.strip() for s in _SENTENCE_RE.split(text) if len(s.strip()) > 40]
    claims = sentences[: settings.max_claims]
    return {"claims": claims, "log": [f"Extracted {len(claims)} claims (heuristic, no LLM key)."]}


# --------------------------------------------------------------------------- #
# 4. retrieve_evidence                                                         #
# --------------------------------------------------------------------------- #
@timed_node("retrieve_evidence")
def retrieve_evidence(state: GraphState) -> dict:
    claims = state.get("claims", [])
    evidence: list[Evidence] = []
    for claim in claims:
        results = search(claim)
        evidence.append(Evidence(claim=claim, results=results))  # type: ignore[arg-type]
    total = sum(len(e["results"]) for e in evidence)
    return {"evidence": evidence, "log": [f"Retrieved {total} evidence snippets for {len(claims)} claims."]}


# --------------------------------------------------------------------------- #
# 5. assess_claims                                                             #
# --------------------------------------------------------------------------- #
@timed_node("assess_claims")
def assess_claims(state: GraphState) -> dict:
    evidence = state.get("evidence", [])
    assessments: list[ClaimAssessment] = []
    use_llm = _has_groq()
    llm = get_llm("assessor") if use_llm else None

    for item in evidence:
        claim, results = item["claim"], item["results"]
        sources = [Source(title=r.get("title", ""), url=r.get("url", "")) for r in results if r.get("url")]

        if use_llm and results:
            try:
                snippets = "\n\n".join(
                    f"[{i + 1}] {r.get('title', '')}\n{r.get('content', '')}"
                    for i, r in enumerate(results)
                )
                messages = [
                    ("system", CLAIM_ASSESSMENT_SYSTEM),
                    ("user", CLAIM_ASSESSMENT_USER.format(claim=claim, evidence=snippets)),
                ]
                data = extract_json(llm.invoke(messages).content)  # type: ignore[union-attr]
                assessments.append(
                    ClaimAssessment(
                        claim=claim,
                        verdict=data.get("verdict", "unverified"),
                        confidence=float(data.get("confidence", 0.0)),
                        rationale=data.get("rationale", ""),
                        sources=sources,
                    )
                )
                continue
            except Exception as exc:  # noqa: BLE001 - fall through to unverified
                logger.warning("claim_assessment_failed", extra={"claim": claim, "error": str(exc)})

        # Fallback: no LLM key or no evidence -> can't verify.
        reason = "No evidence retrieved." if not results else "LLM unavailable — not assessed."
        assessments.append(
            ClaimAssessment(
                claim=claim, verdict="unverified", confidence=0.0, rationale=reason, sources=sources
            )
        )

    counts = {v: sum(1 for a in assessments if a["verdict"] == v) for v in ("supported", "refuted", "unverified")}
    return {
        "assessments": assessments,
        "log": [f"Assessed claims — {counts['supported']} supported, {counts['refuted']} refuted, {counts['unverified']} unverified."],
    }


# --------------------------------------------------------------------------- #
# 6. fuse                                                                      #
# --------------------------------------------------------------------------- #
@timed_node("fuse")
def fuse(state: GraphState) -> dict:
    settings = get_settings()
    assessments = state.get("assessments", [])

    # LLM signal: share of *checked* claims that were refuted.
    checked = [a for a in assessments if a["verdict"] in ("supported", "refuted")]
    llm_fake_share = (
        sum(1 for a in checked if a["verdict"] == "refuted") / len(checked) if checked else None
    )

    # ML signal: only trust it if a model was actually trained.
    ml_score = state.get("ml_score") if state.get("ml_available") else None

    fake_prob, basis = _blend(ml_score, llm_fake_share, settings.ml_weight)

    if fake_prob is None:
        final_label, confidence = "uncertain", 0.0
    elif fake_prob >= settings.fake_threshold:
        final_label, confidence = "fake", fake_prob
    elif fake_prob <= settings.real_threshold:
        final_label, confidence = "real", 1.0 - fake_prob
    else:
        final_label, confidence = "uncertain", 1.0 - abs(fake_prob - 0.5) * 2

    # Dedupe sources across all claims.
    sources = _dedupe_sources(assessments)
    rationale = _build_rationale(final_label, fake_prob, ml_score, llm_fake_share, checked, basis)

    return {
        "final_label": final_label,
        "final_confidence": round(confidence, 4),
        "fake_probability": round(fake_prob, 4) if fake_prob is not None else None,
        "sources": sources,
        "rationale": rationale,
        "log": [f"Final verdict: {final_label} (confidence {confidence:.2f})."],
    }


def _blend(ml_score, llm_fake_share, ml_weight):
    """Combine the two signals into a single P(fake); return (prob, basis-str)."""
    if ml_score is not None and llm_fake_share is not None:
        return ml_weight * ml_score + (1 - ml_weight) * llm_fake_share, "ml+evidence"
    if llm_fake_share is not None:
        return llm_fake_share, "evidence"
    if ml_score is not None:
        return ml_score, "ml"
    return None, "none"


def _dedupe_sources(assessments) -> list[Source]:
    seen: set[str] = set()
    out: list[Source] = []
    for a in assessments:
        for s in a.get("sources", []):
            url = s.get("url", "")
            if url and url not in seen:
                seen.add(url)
                out.append(s)
    return out


def _build_rationale(label, fake_prob, ml_score, llm_fake_share, checked, basis) -> str:
    if fake_prob is None:
        return (
            "Not enough signal to judge: the ML model isn't trained and no claims "
            "could be verified against evidence. Treat as unverified."
        )
    parts = [f"Overall fake-probability {fake_prob:.0%} (based on {basis})."]
    if ml_score is not None:
        parts.append(f"ML first-pass put P(fake) at {ml_score:.0%}.")
    if llm_fake_share is not None and checked:
        refuted = sum(1 for a in checked if a["verdict"] == "refuted")
        parts.append(f"Evidence check refuted {refuted}/{len(checked)} verifiable claims.")
    return " ".join(parts)
