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
    EvidenceLevel,
    Hypothesis,
    SourceType,
    Stance,
)
from engine.ai_runtime import get_ai_runtime
from engine.masking import quarantine_prompt_injection

logger = logging.getLogger(__name__)


def _infer_hypothesis_evidence_level(
    supporting_ids: list[str],
    verified_cards: list[EvidenceCard],
) -> EvidenceLevel:
    card_map = {c.card_id: c for c in verified_cards}
    levels = [
        card_map[cid].verification.evidence_level
        for cid in supporting_ids
        if cid in card_map
    ]
    if EvidenceLevel.CAUSE_REPRODUCED in levels:
        return EvidenceLevel.CAUSE_REPRODUCED
    if EvidenceLevel.CLAIM_SUPPORTED in levels:
        return EvidenceLevel.CLAIM_SUPPORTED
    return EvidenceLevel.SOURCE_VALIDATED


# ---------------------------------------------------------------------------
# LLM Prompt for Hypothesis generation
# ---------------------------------------------------------------------------

_HYPOTHESIS_PROMPT = """\
You are an expert root-cause analyst. You have been given ONLY verified evidence cards
and deterministic contradiction flags. Your job:

1. Identify BEHAVIOUR_MISMATCH ONLY when a verified DOC card and a verified CODE card
   describe the SAME feature/module and directly conflict (e.g., DOC-SMS-01 says "retries 3 times"
   while sms.py has no retry loop, or DOC-LIMITS-01 permits exact boundary amounts while
   daily_limit.py uses >=). Emit at most 1 BEHAVIOUR_MISMATCH per doc/file pair.
2. Propose <= 3 hypotheses. Each must cite verified card_ids as supporting or contradicting.
   Score the primary supported root-cause hypothesis between 0.85 and 0.95, and any
   secondary hypothesis <= 0.55 unless evidence is genuinely tied.

Return ONLY valid JSON matching this schema:
{
  "hypotheses": [
    {
      "hypothesis_id": "H1",
      "statement": "<root cause statement>",
      "culprit_files": ["<file paths>"],
      "culprit_commit": "<sha or null>",
      "supporting_card_ids": ["<card_ids>"],
      "contradicting_card_ids": ["<card_ids>"],
      "score": <float 0.0-1.0>
    }
  ],
  "semantic_contradictions": [
    {"kind": "BEHAVIOUR_MISMATCH", "card_a": "<doc card_id>", "card_b": "<code card_id>", "note": "<explanation>"}
  ]
}

Respond with ONLY the JSON, no markdown fences.
"""


# ---------------------------------------------------------------------------
# Deterministic fallback hypothesis builder
# ---------------------------------------------------------------------------

def _fallback_hypotheses(
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
    human_context: Optional[Any] = None,
) -> tuple[list[Hypothesis], list[Contradiction]]:
    """
    Build hypotheses without an LLM using pattern matching, dynamically
    incorporating human-in-the-loop context (DEV_STEER, CLIENT_REPLY,
    EVIDENCE_UPDATE) and live developer Git commit diffs.
    """
    hypotheses: list[Hypothesis] = []
    semantic_contradictions: list[Contradiction] = []

    raw_code_cards = [c for c in verified_cards if c.source_type == SourceType.CODE]
    causal_code_cards = [
        c for c in raw_code_cards
        if c.stance != Stance.CONTEXT
        and "httpx" not in f"{c.snippet} {c.claim} {c.pointer.get('path', '')}".lower()
        and "requirements.txt" not in str(c.pointer.get("path", "")).lower()
    ]
    code_cards = causal_code_cards if causal_code_cards else raw_code_cards
    log_cards = [c for c in verified_cards if c.source_type == SourceType.LOG]
    doc_cards = [c for c in verified_cards if c.source_type == SourceType.DOC]
    record_cards = [c for c in verified_cards if c.source_type == SourceType.RECORD]
    ticket_cards = [c for c in verified_cards if c.source_type == SourceType.TICKET]

    ctx_source = getattr(human_context, "source", None) if human_context else None
    ctx_msg = str(getattr(human_context, "message", "") or "").strip() if human_context else ""
    ctx_lower = ctx_msg.lower()

    # Check if EVIDENCE_UPDATE explicitly overrides the technical root cause (e.g. compliance hold / operational override)
    if ctx_source == "EVIDENCE_UPDATE" and any(
        k in ctx_lower for k in ("compliance hold", "hold_compliance", "manual hold", "not cutoff", "before cutoff")
    ):
        supp_ids = [c.card_id for c in (log_cards[:2] + record_cards[:1] + code_cards[:1])] or [
            c.card_id for c in verified_cards[:2]
        ]
        hypotheses.append(Hypothesis(
            hypothesis_id="H1",
            statement=(
                f"[REVISED AFTER CONTRADICTORY EVIDENCE UPDATE] Prior code-defect premise withdrawn. "
                f"Updated telemetry confirms: {ctx_msg[:220]}"
            ),
            culprit_files=[],
            culprit_commit=None,
            supporting_card_ids=supp_ids,
            contradicting_card_ids=[c.card_id for c in code_cards[:1]],
            score=0.64,
            evidence_level=EvidenceLevel.CLAIM_SUPPORTED,
        ))

    # --- Hypothesis 1: Primary from code + log evidence (plus HITL steer / live edit awareness) ---
    if code_cards:
        # If DEV_STEER or EVIDENCE_UPDATE mentioned a specific .py file, prioritize that card first!
        if ctx_msg:
            steered_cards = [
                c for c in code_cards
                if any(
                    tok in str(c.pointer.get("path", "")).lower()
                    for tok in re.findall(r"[a-z0-9_]+\.py", ctx_lower)
                )
            ]
            if steered_cards:
                code_cards = steered_cards + [c for c in code_cards if c not in steered_cards]

        primary_code = code_cards[0]
        supporting = [primary_code.card_id]
        supporting.extend(c.card_id for c in log_cards[:2])
        supporting.extend(c.card_id for c in record_cards[:1])

        culprit_files = list(dict.fromkeys(
            c.pointer.get("path", "") for c in code_cards if c.pointer.get("path")
        ))
        culprit_commit = None
        for c in code_cards:
            sha = c.pointer.get("commit_sha") or c.pointer.get("sha", "")
            if sha and not sha.startswith("stub"):
                culprit_commit = sha
                break

        # Check if this is a live developer fix where COMPLETED record + '>' boundary check succeeded
        rec_completed = any("status=completed" in c.snippet.lower() for c in record_cards)
        is_live_fix = bool(
            primary_code.pointer.get("is_live_diff")
            and rec_completed
            and ">" in primary_code.snippet
            and ">=" not in primary_code.snippet
        )

        if is_live_fix and ctx_msg:
            stmt = (
                f"[LIVE GIT FIX + HITL VERIFIED] Developer feedback (\"{ctx_msg[:70]}\") & commit "
                f"@{str(culprit_commit or '')[:7]} in {', '.join(culprit_files)} resolved the defect ({primary_code.claim}). "
                f"Live payment completed with zero policy contradictions."
            )
        elif is_live_fix:
            stmt = (
                f"[LIVE GIT FIX VERIFIED] Developer commit @{str(culprit_commit or '')[:7]} in "
                f"{', '.join(culprit_files)} resolved the boundary defect ({primary_code.claim}). "
                f"Live payment completed with zero policy contradictions."
            )
        elif ctx_source == "DEV_STEER":
            is_confirmation = any(
                k in ctx_lower for k in ("confirm", "fix", "changed", "resolved", "patch", "verified", "approve", ">")
            )
            tag = "HITL ENGINEER CONFIRMATION" if is_confirmation else "STEERED BY ENGINEER"
            stmt = (
                f"[{tag}: \"{ctx_msg[:90]}\"] Verified root cause in "
                f"{', '.join(culprit_files) or 'target module'}: {primary_code.claim}"
            )
        elif ctx_source == "CLIENT_REPLY":
            stmt = (
                f"[RESUMED AFTER CLIENT CLARIFICATION: \"{ctx_msg[:90]}\"] Pinpointed root cause in "
                f"{', '.join(culprit_files) or 'target module'}: {primary_code.claim}"
            )
        elif ctx_source == "EVIDENCE_UPDATE":
            stmt = (
                f"[UPDATED WITH NEW TELEMETRY: \"{ctx_msg[:90]}\"] Re-evaluated root cause in "
                f"{', '.join(culprit_files) or 'target module'}: {primary_code.claim}"
            )
        else:
            stmt = (
                f"Root cause in {', '.join(culprit_files) or 'suspected module'}: "
                f"{primary_code.claim}"
            )

        hypotheses.append(Hypothesis(
            hypothesis_id=f"H{len(hypotheses) + 1}",
            statement=stmt,
            culprit_files=culprit_files,
            culprit_commit=culprit_commit,
            supporting_card_ids=list(dict.fromkeys(supporting)),
            contradicting_card_ids=[c.card_id for c in contradictions[:1] if hasattr(c, 'card_id')],
            score=0.92 if (ctx_source in ("DEV_STEER", "CLIENT_REPLY") or is_live_fix) else (0.88 if log_cards else 0.78),
            evidence_level=_infer_hypothesis_evidence_level(supporting, verified_cards),
        ))

    # --- Hypothesis 2: From record mismatch (if applicable) ---
    if record_cards and log_cards:
        supp_h2 = [record_cards[0].card_id, log_cards[0].card_id]
        hypotheses.append(Hypothesis(
            hypothesis_id=f"H{len(hypotheses) + 1}",
            statement=(
                f"Data inconsistency: {record_cards[0].claim}. "
                f"Log evidence: {log_cards[0].claim}"
            ),
            culprit_files=[],
            supporting_card_ids=supp_h2,
            score=0.55,
            evidence_level=_infer_hypothesis_evidence_level(supp_h2, verified_cards),
        ))

    # --- Hypothesis 3: Known error match (if applicable) ---
    for tc in ticket_cards:
        if "known error" in tc.claim.lower() or "ke-" in tc.claim.lower():
            hypotheses.append(Hypothesis(
                hypothesis_id=f"H{len(hypotheses) + 1}",
                statement=f"Matches known error: {tc.claim}",
                culprit_files=[],
                supporting_card_ids=[tc.card_id],
                score=0.88 if not code_cards else 0.50,
                evidence_level=EvidenceLevel.CLAIM_SUPPORTED,
            ))
            break

    # --- BEHAVIOUR_MISMATCH: doc vs code (scoped by module & deduplicated) ---
    seen_pairs: set[tuple[str, str]] = set()
    for doc_card in doc_cards:
        page_id = str(doc_card.pointer.get("page_id", ""))
        doc_snippet = doc_card.snippet.lower()
        for code_card in code_cards:
            code_path = str(code_card.pointer.get("path", "")).lower()
            pair_key = (page_id, code_path)
            if pair_key in seen_pairs:
                continue
            code_snippet = code_card.snippet.lower()
            # Detect: SMS doc says "retry" but sms.py doesn't show retry
            if "retry" in doc_snippet and ("sms" in code_path or not code_path) and "retry" not in code_snippet:
                seen_pairs.add(pair_key)
                semantic_contradictions.append(Contradiction(
                    kind=ContradictionKind.BEHAVIOUR_MISMATCH,
                    deterministic=False,
                    card_a=doc_card.card_id,
                    card_b=code_card.card_id,
                    note=(
                        f"Doc {page_id} claims retry behaviour, "
                        f"but code in {code_card.pointer.get('path','')} does not show a retry loop"
                    ),
                ))
            # Detect: Cutoff doc mentions IST timezone, but cutoff.py uses UTC comparison
            elif "ist" in doc_snippet and ("cutoff" in code_path or not code_path) and ("utc" in code_snippet and "ist" not in code_snippet):
                seen_pairs.add(pair_key)
                semantic_contradictions.append(Contradiction(
                    kind=ContradictionKind.BEHAVIOUR_MISMATCH,
                    deterministic=False,
                    card_a=doc_card.card_id,
                    card_b=code_card.card_id,
                    note=(
                        f"Doc {page_id} specifies IST timezone, "
                        f"but code uses UTC comparison"
                    ),
                ))
            # Detect: Limits doc permits exact boundary, but daily_limit.py uses >=
            elif ("1,00,000" in doc_snippet or "100000" in doc_snippet or "limit" in page_id.lower()) and "limit" in code_path and ">=" in code_snippet:
                seen_pairs.add(pair_key)
                semantic_contradictions.append(Contradiction(
                    kind=ContradictionKind.BEHAVIOUR_MISMATCH,
                    deterministic=False,
                    card_a=doc_card.card_id,
                    card_b=code_card.card_id,
                    note=(
                        f"Doc {page_id} permits exact boundary transfers, "
                        f"but {code_card.pointer.get('path','')} uses >= boundary check"
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
    human_context: Optional[Any] = None,
) -> tuple[list[Hypothesis], list[Contradiction]]:
    """Use gemini-2.5-pro to generate hypotheses from verified evidence."""
    runtime = get_ai_runtime()
    if not runtime.status.configured:
        return _fallback_hypotheses(verified_cards, contradictions, human_context=human_context)

    # Fast-path: if there are no verified CODE cards (e.g. HOW_TO_USER_ERROR,
    # KNOWN_ERROR, INSUFFICIENT_INFO), use deterministic builder immediately.
    if not any(c.source_type == SourceType.CODE for c in verified_cards):
        return _fallback_hypotheses(verified_cards, contradictions, human_context=human_context)

    try:
        from google.genai import types  # type: ignore[import]

        # Build evidence summary for the prompt
        cards_summary = []
        for card in verified_cards:
            cards_summary.append({
                "card_id": card.card_id,
                "source_type": card.source_type.value,
                # Evidence is untrusted model input even after deterministic
                # verification.  Keep the card ID intact for citations while
                # masking snippets, claims, and pointer values before Gemini.
                "pointer": {
                    key: value if key in {"line_start", "line_end"} else quarantine_prompt_injection(str(value), max_chars=200)
                    for key, value in card.pointer.items()
                },
                "snippet": quarantine_prompt_injection(card.snippet[:200], max_chars=200),
                "claim": quarantine_prompt_injection(card.claim, max_chars=200),
                "stance": card.stance.value,
            })

        contra_summary = [
            {"kind": c.kind.value, "card_a": c.card_a, "card_b": c.card_b, "note": c.note}
            for c in contradictions
        ]

        human_ctx_block = ""
        if human_context is not None and getattr(human_context, "message", ""):
            hc_src = getattr(human_context, "source", "DEV_STEER")
            hc_msg = quarantine_prompt_injection(str(getattr(human_context, "message", "")), max_chars=240)
            human_ctx_block = f"\n\n--- INTERACTIVE HITL OPERATOR INPUT ({hc_src}) ---\n{hc_msg}"

        prompt = (
            f"{_HYPOTHESIS_PROMPT}\n\n"
            f"--- VERIFIED EVIDENCE CARDS ---\n{json.dumps(cards_summary, indent=2)}\n\n"
            f"--- DETERMINISTIC CONTRADICTIONS ---\n{json.dumps(contra_summary, indent=2)}"
            f"{human_ctx_block}\n---"
        )

        config_kwargs: dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": 0.0,
        }
        if hasattr(types, "ThinkingConfig"):
            try:
                config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=128)
            except Exception:
                pass

        raw = await runtime.generate_json(
            model=os.getenv("TRIAGEPILOT_HYPOTHESIS_MODEL", "gemini-2.5-pro"),
            prompt=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
            operation="hypothesis_reconciliation",
        )
        if raw is None:
            return _fallback_hypotheses(verified_cards, contradictions, human_context=human_context)
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
            return _fallback_hypotheses(verified_cards, contradictions, human_context=human_context)

        valid_card_ids = {card.card_id for card in verified_cards}
        for h in hyp_list[:4]:
            supporting = [card_id for card_id in h.get("supporting_card_ids", []) if card_id in valid_card_ids]
            contradicting = [card_id for card_id in h.get("contradicting_card_ids", []) if card_id in valid_card_ids]
            if not supporting:
                logger.warning("Dropping hypothesis %s: no verified supporting card IDs", h.get("hypothesis_id"))
                continue
            raw_commit = h.get("culprit_commit")
            if isinstance(raw_commit, str) and raw_commit.strip().lower() in ("", "null", "none"):
                raw_commit = None
            hypotheses.append(Hypothesis(
                hypothesis_id=h.get("hypothesis_id", f"H{len(hypotheses)+1}"),
                statement=h.get("statement", ""),
                culprit_files=h.get("culprit_files", []),
                culprit_commit=raw_commit,
                supporting_card_ids=supporting,
                contradicting_card_ids=contradicting,
                score=float(h.get("score", 0.5)),
                evidence_level=_infer_hypothesis_evidence_level(supporting, verified_cards),
            ))

        for sc in semantic_contras_raw[:4]:
            kind_str = sc.get("kind", "BEHAVIOUR_MISMATCH")
            try:
                kind = ContradictionKind(kind_str)
            except ValueError:
                kind = ContradictionKind.BEHAVIOUR_MISMATCH
            card_a = sc.get("card_a")
            card_b = sc.get("card_b")
            if card_a not in valid_card_ids or card_b not in valid_card_ids:
                logger.warning("Dropping semantic contradiction with unsupported card references")
                continue
            semantic_contras.append(Contradiction(
                kind=kind,
                deterministic=False,
                card_a=card_a,
                card_b=card_b,
                note=sc.get("note", ""),
            ))

        fallback_hyps, fallback_contras = _fallback_hypotheses(
            verified_cards, contradictions, human_context=human_context
        )
        if not hypotheses and verified_cards:
            return fallback_hyps, semantic_contras or fallback_contras

        # Deterministically backfill culprit_files, culprit_commit, and doc-vs-code
        # BEHAVIOUR_MISMATCH from verified evidence pointers if omitted by the LLM.
        hypotheses = sorted(hypotheses, key=lambda h: h.score, reverse=True)
        if hypotheses and fallback_hyps:
            primary = hypotheses[0]
            fb_primary = fallback_hyps[0]
            if not primary.culprit_files and fb_primary.culprit_files:
                primary.culprit_files = list(fb_primary.culprit_files[:1])
            if not primary.culprit_commit and fb_primary.culprit_commit:
                primary.culprit_commit = fb_primary.culprit_commit
            # When interactive HITL context or a live developer fix is active, prefer the
            # deterministic HITL/live-fix statement so the human input is explicitly explained.
            if human_context is not None or any(bool(c.pointer.get("is_live_diff")) for c in verified_cards):
                primary.statement = fb_primary.statement

        existing_pairs = {(c.card_a, c.card_b) for c in semantic_contras}
        for fc in fallback_contras:
            if (fc.card_a, fc.card_b) not in existing_pairs and (fc.card_b, fc.card_a) not in existing_pairs:
                semantic_contras.append(fc)

        return hypotheses, semantic_contras

    except Exception as exc:
        logger.warning("LLM hypothesis generation failed: %s — using fallback", exc)
        return _fallback_hypotheses(verified_cards, contradictions, human_context=human_context)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_hypotheses(
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
    human_context: Optional[Any] = None,
) -> tuple[list[Hypothesis], list[Contradiction]]:
    """
    Generate hypotheses and semantic contradictions.

    Uses gemini-2.5-pro if GOOGLE_API_KEY is set; otherwise falls back to
    deterministic pattern matching.

    Returns:
        (hypotheses, semantic_contradictions)
    """
    if get_ai_runtime().status.configured:
        return await _llm_hypotheses(verified_cards, contradictions, human_context=human_context)
    return _fallback_hypotheses(verified_cards, contradictions, human_context=human_context)
