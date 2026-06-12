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

# Fusion tuning: pseudo-claims that pull a tiny evidence sample back toward neutral (0.5).
SHRINK_PRIOR = 0.5
# The ML model is article-trained; ignore its vote on inputs shorter than this (words).
ML_MIN_WORDS = 50


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
    text = state.get("article_text", "") or ""
    result = ml_predict(text)

    # The TF-IDF model is trained on full news *articles*. On a bare one-sentence
    # claim (very different from its training distribution) it tends to cry "fake",
    # which would wrongly drag down true short claims. So only let it vote when the
    # input is article-length; for short claims the evidence check decides alone.
    applicable = result["available"] and len(text.split()) >= ML_MIN_WORDS
    if result["available"] and not applicable:
        note = f"ML first-pass skipped (input too short for the article-trained model)."
    elif applicable:
        note = f"ML first-pass: {result['label']} (P_fake={result['score']:.2f})."
    else:
        note = "ML first-pass: model not trained."

    return {
        "ml_score": result["score"],
        "ml_label": result["label"],
        "ml_available": applicable,
        "log": [note],
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
    claims: list[str] = []
    via_llm = False
    if _has_groq():
        try:
            llm = get_llm("extractor")
            messages = [
                # NB: use replace, not .format — the system prompt contains literal JSON
                # braces ({"claims": ...}) that str.format would misread as fields.
                ("system", CLAIM_EXTRACTION_SYSTEM.replace("{max_claims}", str(settings.max_claims))),
                ("user", CLAIM_EXTRACTION_USER.format(text=text[:6000])),
            ]
            data = extract_json(llm.invoke(messages).content)
            claims = [c.strip() for c in data.get("claims", []) if c.strip()][: settings.max_claims]
            via_llm = True
        except Exception as exc:  # noqa: BLE001 - fall back to heuristic below
            logger.warning("claim_extraction_failed", extra={"error": str(exc)})

    # Fallback when the LLM is unavailable, errored, or found nothing: keep substantial
    # sentences — and if the input is itself a short single claim, use it whole, so a
    # one-liner like "the World Cup happens every 5 years" always gets fact-checked
    # instead of vanishing into a 0-claim "uncertain".
    if not claims:
        sentences = [s.strip() for s in _SENTENCE_RE.split(text) if len(s.strip()) > 40]
        claims = sentences[: settings.max_claims] or ([text] if len(text) <= 300 else [])
        via_llm = False

    suffix = "." if via_llm else " (fallback)."
    return {"claims": claims, "log": [f"Extracted {len(claims)} claim(s){suffix}"]}


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

    # ---- Evidence signal ----
    # Weight each checked claim by the model's OWN confidence, so a tentative
    # "refuted (0.5)" counts for far less than a sure "refuted (0.95)". Then shrink
    # toward neutral by a small prior so a single claim can't peg the score at 0 or 1.
    checked = [a for a in assessments if a["verdict"] in ("supported", "refuted")]
    n = len(checked)
    if n:
        contributions = []
        for a in checked:
            conf = min(max(float(a.get("confidence", 0.5)), 0.0), 1.0)
            # confident refuted -> ~1 ; confident supported -> ~0 ; unsure -> ~0.5
            contributions.append(0.5 + 0.5 * conf if a["verdict"] == "refuted" else 0.5 - 0.5 * conf)
        llm_fake = (sum(contributions) + 0.5 * SHRINK_PRIOR) / (n + SHRINK_PRIOR)
    else:
        llm_fake = None

    # ML signal: only trust it if a model was actually trained.
    ml_score = state.get("ml_score") if state.get("ml_available") else None

    fake_prob, basis = _blend(ml_score, llm_fake, settings.ml_weight)

    if fake_prob is None:
        final_label, confidence = "uncertain", 0.0
    else:
        if fake_prob >= settings.fake_threshold:
            final_label = "fake"
        elif fake_prob <= settings.real_threshold:
            final_label = "real"
        else:
            final_label = "uncertain"

        # Confidence reflects BOTH how far the score is from neutral (margin) AND how
        # much evidence backs it (volume). The ceiling means thin evidence can never
        # read as near-certain — the fix for confident false positives off one claim.
        margin = abs(fake_prob - 0.5) * 2
        signals = n + (1 if ml_score is not None else 0)
        ceiling = 1.0 - 0.4 / max(signals, 1)  # 1 signal -> 0.60, 2 -> 0.80, 3 -> 0.87
        confidence = min(1.0 - margin if final_label == "uncertain" else margin, ceiling)

    # Dedupe sources across all claims.
    sources = _dedupe_sources(assessments)
    rationale = _build_rationale(final_label, fake_prob, ml_score, checked, basis, confidence)

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


def _build_rationale(label, fake_prob, ml_score, checked, basis, confidence) -> str:
    if fake_prob is None:
        return (
            "Not enough signal to judge: the ML model isn't trained and no claims "
            "could be verified against evidence. Treat as unverified."
        )
    parts = [f"Overall fake-probability {fake_prob:.0%} (based on {basis}), confidence {confidence:.0%}."]
    if ml_score is not None:
        parts.append(f"ML first-pass put P(fake) at {ml_score:.0%}.")
    if checked:
        refuted = sum(1 for a in checked if a["verdict"] == "refuted")
        parts.append(f"Evidence check refuted {refuted}/{len(checked)} verifiable claims.")
        if len(checked) == 1 and ml_score is None:
            parts.append("Only one claim could be checked, so confidence is held low.")
    return " ".join(parts)
