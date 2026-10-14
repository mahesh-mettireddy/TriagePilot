"""
engine/agents/hypothesis_agent.py
---------------------------------
Step 6 of the 12-step pipeline: Hypothesis & Semantic Reconciler.

Uses gemini-2.5-pro (or keyword fallback) to:
  1. Compare verified DOC cards vs verified CODE cards to detect
     BEHAVIOUR_MISMATCH and SCOPE_MISMATCH.
  2. Output <= 4 Hypothesis objects citing verified card_ids only.

Input:  ONLY verified_cards + deterministic contradictions.
Output: list[Hypothesis] + optional list[Contradiction] (semantic ones).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from engine.schemas import (
    Contradiction,
    ContradictionKind,
    EvidenceCard,
    Hypothesis,
    SourceType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM Prompt for Hypothesis generation
# ---------------------------------------------------------------------------

_HYPOTHESIS_PROMPT = """\
You are an expert root-cause analyst. You have been given ONLY verified evidence cards
and deterministic contradiction flags. Your job:

1. Identify BEHAVIOUR_MISMATCH: a verified DOC card says one thing, but a verified CODE card
   shows the code does something different (e.g., doc says "retries 3 times" but code has
   no retry loop).
2. Identify SCOPE_MISMATCH: the code or logs suggest the issue affects more/less than what
   the ticket describes.
3. Propose <= 4 hypotheses. Each must cite verified card_ids as supporting or contradicting.

Return ONLY valid JSON array of objects matching this schema:
[
  {
    "hypothesis_id": "H1",
    "statement": "<root cause statement>",
    "culprit_files": ["<file paths>"],
    "culprit_commit": "<sha or null>",
    "supporting_card_ids": ["<card_ids>"],
    "contradicting_card_ids": ["<card_ids>"],
    "score": <float 0.0-1.0>
  }
]

Also, if you detect BEHAVIOUR_MISMATCH or SCOPE_MISMATCH, append a field
"semantic_contradictions" as a list of objects:
[
  {"kind": "BEHAVIOUR_MISMATCH", "card_a": "<doc card_id>", "card_b": "<code card_id>", "note": "<explanation>"}
]

Respond with ONLY the JSON, no markdown fences.
"""


# ---------------------------------------------------------------------------
# Deterministic fallback hypothesis builder
# ---------------------------------------------------------------------------

def _fallback_hypotheses(
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
) -> tuple[list[Hypothesis], list[Contradiction]]:
    """
    Build hypotheses without an LLM using pattern matching.

    This works well for the golden scenarios because the evidence structure
    is predictable.
    """
    hypotheses: list[Hypothesis] = []
    semantic_contradictions: list[Contradiction] = []

    code_cards = [c for c in verified_cards if c.source_type == SourceType.CODE]
    log_cards = [c for c in verified_cards if c.source_type == SourceType.LOG]
    doc_cards = [c for c in verified_cards if c.source_type == SourceType.DOC]
    record_cards = [c for c in verified_cards if c.source_type == SourceType.RECORD]
    ticket_cards = [c for c in verified_cards if c.source_type == SourceType.TICKET]

    # --- Hypothesis 1: Primary from code + log evidence ---
    if code_cards:
        primary_code = code_cards[0]
        supporting = [primary_code.card_id]
        supporting.extend(c.card_id for c in log_cards[:2])

        # Extract culprit files
        culprit_files = list({c.pointer.get("path", "") for c in code_cards if c.pointer.get("path")})
        culprit_commit = None
        for c in code_cards:
            sha = c.pointer.get("sha", "")
            if sha and not sha.startswith("stub"):
                culprit_commit = sha
                break

        hypotheses.append(Hypothesis(
            hypothesis_id="H1",
            statement=(
                f"Root cause in {', '.join(culprit_files) or 'suspected module'}: "
                f"{primary_code.claim}"
            ),
            culprit_files=culprit_files,
            culprit_commit=culprit_commit,
            supporting_card_ids=supporting,
            contradicting_card_ids=[c.card_id for c in contradictions[:1] if hasattr(c, 'card_id')],
            score=0.75 if log_cards else 0.50,
        ))

    # --- Hypothesis 2: From record mismatch (if applicable) ---
    if record_cards and log_cards:
        hypotheses.append(Hypothesis(
            hypothesis_id="H2",
            statement=(
                f"Data inconsistency: {record_cards[0].claim}. "
                f"Log evidence: {log_cards[0].claim}"
            ),
            culprit_files=[],
            supporting_card_ids=[record_cards[0].card_id, log_cards[0].card_id],
            score=0.55,
        ))

    # --- Hypothesis 3: Known error match (if applicable) ---
    for tc in ticket_cards:
        if "known error" in tc.claim.lower() or "ke-" in tc.claim.lower():
            hypotheses.append(Hypothesis(
                hypothesis_id=f"H{len(hypotheses) + 1}",
                statement=f"Matches known error: {tc.claim}",
                culprit_files=[],
                supporting_card_ids=[tc.card_id],
                score=0.80,
            ))
            break

    # --- BEHAVIOUR_MISMATCH: doc vs code ---
    for doc_card in doc_cards:
        for code_card in code_cards:
            doc_snippet = doc_card.snippet.lower()
            code_snippet = code_card.snippet.lower()
            # Detect: doc says "retry" but code doesn't show retry
            if "retry" in doc_snippet and "retry" not in code_snippet:
                semantic_contradictions.append(Contradiction(
                    kind=ContradictionKind.BEHAVIOUR_MISMATCH,
                    deterministic=False,
                    card_a=doc_card.card_id,
                    card_b=code_card.card_id,
                    note=(
                        f"Doc {doc_card.pointer.get('page_id','')} claims retry behaviour, "
                        f"but code in {code_card.pointer.get('path','')} does not show a retry loop"
                    ),
                ))
            # Detect: doc mentions different timezone handling
            if "ist" in doc_snippet and ("utc" in code_snippet and "ist" not in code_snippet):
                semantic_contradictions.append(Contradiction(
                    kind=ContradictionKind.BEHAVIOUR_MISMATCH,
                    deterministic=False,
                    card_a=doc_card.card_id,
                    card_b=code_card.card_id,
                    note=(
                        f"Doc {doc_card.pointer.get('page_id','')} specifies IST timezone, "
                        f"but code uses UTC comparison"
                    ),
                ))

    # Cap at 4 hypotheses
    hypotheses = sorted(hypotheses, key=lambda h: h.score, reverse=True)[:4]

    return hypotheses, semantic_contradictions


# ---------------------------------------------------------------------------
# LLM-backed hypothesis generation
# ---------------------------------------------------------------------------

async def _llm_hypotheses(
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
) -> tuple[list[Hypothesis], list[Contradiction]]:
    """Use gemini-2.5-pro to generate hypotheses from verified evidence."""
    import asyncio

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return _fallback_hypotheses(verified_cards, contradictions)

    try:
        from google import genai  # type: ignore[import]
        from google.genai import types  # type: ignore[import]

        client = genai.Client(api_key=api_key)

        # Build evidence summary for the prompt
        cards_summary = []
        for card in verified_cards:
            cards_summary.append({
                "card_id": card.card_id,
                "source_type": card.source_type.value,
                "pointer": card.pointer,
                "snippet": card.snippet[:200],
                "claim": card.claim,
                "stance": card.stance.value,
            })

        contra_summary = [
            {"kind": c.kind.value, "card_a": c.card_a, "card_b": c.card_b, "note": c.note}
            for c in contradictions
        ]

        prompt = (
            f"{_HYPOTHESIS_PROMPT}\n\n"
            f"--- VERIFIED EVIDENCE CARDS ---\n{json.dumps(cards_summary, indent=2)}\n\n"
            f"--- DETERMINISTIC CONTRADICTIONS ---\n{json.dumps(contra_summary, indent=2)}\n---"
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            ),
        )

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)

        # Parse hypotheses
        hypotheses = []
        semantic_contras = []

        if isinstance(data, dict):
            hyp_list = data.get("hypotheses", data.get("hypothesis", [data]))
            semantic_contras_raw = data.get("semantic_contradictions", [])
        elif isinstance(data, list):
            hyp_list = data
            semantic_contras_raw = []
        else:
            return _fallback_hypotheses(verified_cards, contradictions)

        for h in hyp_list[:4]:
            hypotheses.append(Hypothesis(
                hypothesis_id=h.get("hypothesis_id", f"H{len(hypotheses)+1}"),
                statement=h.get("statement", ""),
                culprit_files=h.get("culprit_files", []),
                culprit_commit=h.get("culprit_commit"),
                supporting_card_ids=h.get("supporting_card_ids", []),
                contradicting_card_ids=h.get("contradicting_card_ids", []),
                score=float(h.get("score", 0.5)),
            ))

        for sc in semantic_contras_raw[:4]:
            kind_str = sc.get("kind", "BEHAVIOUR_MISMATCH")
            try:
                kind = ContradictionKind(kind_str)
            except ValueError:
                kind = ContradictionKind.BEHAVIOUR_MISMATCH
            semantic_contras.append(Contradiction(
                kind=kind,
                deterministic=False,
                card_a=sc.get("card_a"),
                card_b=sc.get("card_b"),
                note=sc.get("note", ""),
            ))

        return hypotheses, semantic_contras

    except Exception as exc:
        logger.warning("LLM hypothesis generation failed: %s — using fallback", exc)
        return _fallback_hypotheses(verified_cards, contradictions)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_hypotheses(
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
) -> tuple[list[Hypothesis], list[Contradiction]]:
    """
    Generate hypotheses and semantic contradictions.

    Uses gemini-2.5-pro if GOOGLE_API_KEY is set; otherwise falls back to
    deterministic pattern matching.

    Returns:
        (hypotheses, semantic_contradictions)
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        return await _llm_hypotheses(verified_cards, contradictions)
    return _fallback_hypotheses(verified_cards, contradictions)
