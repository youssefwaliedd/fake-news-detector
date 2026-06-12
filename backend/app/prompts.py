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
- Extract each claim EXACTLY as the text asserts it — preserve the author's assertion even if \
you believe it is false or poorly worded. Do NOT correct it, negate it, fact-check it, or rephrase \
it into what is actually true. Deciding truth is the verifier's job, not yours; your job is to \
capture what was claimed so it can be checked. (E.g. from "the World Cup happens every 5 years not \
4", extract "The World Cup happens every 5 years" — never "...every 4 years".)
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
