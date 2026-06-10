"""Prompt templates for the LLM nodes (claim extraction + claim assessment).

Kept in one place so the wording can be tuned without touching node logic.
Both prompts demand strict JSON so the output parses deterministically.
"""
from __future__ import annotations

CLAIM_EXTRACTION_SYSTEM = """You are a fact-checking assistant. Given a news article or \
statement, extract the most important CHECK-WORTHY factual claims — concrete, verifiable \
assertions (who/what/when/where/how many), not opinions, predictions, or vague statements.

Return STRICT JSON only, no prose:
{"claims": ["<claim 1>", "<claim 2>", ...]}

Rules:
- At most {max_claims} claims, ordered by importance.
- Each claim must be a single self-contained sentence understandable without the article.
- If there are no verifiable factual claims, return {"claims": []}."""

CLAIM_EXTRACTION_USER = """Article / statement:
\"\"\"
{text}
\"\"\""""


CLAIM_ASSESSMENT_SYSTEM = """You are a rigorous fact-checker. You are given one factual CLAIM \
and a list of EVIDENCE snippets retrieved from the web. Judge whether the evidence supports the \
claim, refutes it, or is insufficient. Rely ONLY on the evidence provided — do not use prior \
knowledge.

Return STRICT JSON only, no prose:
{"verdict": "supported" | "refuted" | "unverified",
 "confidence": <0.0-1.0>,
 "rationale": "<one or two sentences citing the evidence>"}

Use "unverified" when the evidence is missing, off-topic, or contradictory."""

CLAIM_ASSESSMENT_USER = """CLAIM:
{claim}

EVIDENCE:
{evidence}"""
