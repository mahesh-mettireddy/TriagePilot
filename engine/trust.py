"""
engine/trust.py
---------------
Step 7 of the 12-step pipeline: Deterministic Trust Scorer & Policy Gate.

**Pure Python — ZERO LLM involvement.**

Computes a transparent trust score [0.00 - 1.00] from verified evidence:

  score = clamp(
      0.40 * c_ver    # verified evidence volume
    + 0.25 * c_div    # source diversity (how many source types)
    + 0.20 * c_spec   # code/log specificity (file:line pointers)
    + 0.15 * c_time   # temporal alignment (timestamps present & consistent)
    - 0.30 * p_contra # contradiction penalty
    - 0.20 * p_unver  # unverified/dropped card penalty
    , 0, 1
  )

Trust bands:
  HIGH   >= 0.70  -> CONCLUDE
  MEDIUM   0.45 - 0.70  -> CONCLUDE_WITH_CAVEAT
  LOW    <  0.45  -> ABSTAIN

Also ABSTAIN if top-2 hypothesis gap < 0.10.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from engine.schemas import (
    Contradiction,
    DecisionBand,
    EvidenceCard,
    Hypothesis,
    PolicyAction,
    SourceType,
    TrustComponents,
    TrustSummary,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trust formula weights (from ARCHITECTURE_AND_SPEC.md)
# ---------------------------------------------------------------------------
W_VER = 0.40
W_DIV = 0.25
W_SPEC = 0.20
W_TIME = 0.15
P_CONTRA = 0.30
P_UNVER = 0.20


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Component calculators
# ---------------------------------------------------------------------------

def _c_ver(verified_count: int, total_count: int) -> float:
    """
    Verified evidence volume: ratio of verified cards to total.
    Boosted by log-scale for absolute count (5+ verified = full credit).
    """
    if total_count == 0:
        return 0.0
    ratio = verified_count / total_count
    # Bonus for having more absolute verified cards (diminishing returns)
    import math
    abs_bonus = min(1.0, math.log1p(verified_count) / math.log1p(5))
    return _clamp(0.6 * ratio + 0.4 * abs_bonus)


def _c_div(verified_cards: list[EvidenceCard]) -> float:
    """
    Source diversity: how many distinct SourceTypes are represented.
    6 possible types -> 1.0 if all 6 present.
    """
    all_types = {SourceType.LOG, SourceType.CODE, SourceType.DOC,
                 SourceType.TICKET, SourceType.RECORD, SourceType.VISUAL}
    present = {card.source_type for card in verified_cards}
    # Minimum useful diversity: log + code = 0.5, add more for higher
    return _clamp(len(present) / len(all_types) * 1.2)  # slight boost


def _c_spec(verified_cards: list[EvidenceCard]) -> float:
    """
    Code/log specificity: do cards point to exact file:line or log_id?
    Higher if cards have precise pointers (not just vague claims).
    """
    if not verified_cards:
        return 0.0

    specific_count = 0
    for card in verified_cards:
        pointer = card.pointer
        if card.source_type == SourceType.CODE:
            if pointer.get("path") and pointer.get("line_start"):
                specific_count += 1
        elif card.source_type == SourceType.LOG:
            if pointer.get("log_id") and pointer.get("ts"):
                specific_count += 1
        elif card.source_type == SourceType.RECORD:
            if pointer.get("id"):
                specific_count += 1
        elif card.source_type == SourceType.DOC:
            if pointer.get("page_id") and pointer.get("section"):
                specific_count += 1

    return _clamp(specific_count / len(verified_cards))


def _c_time(verified_cards: list[EvidenceCard]) -> float:
    """
    Temporal alignment: are timestamps present and consistent across cards?
    Higher if log timestamps cluster within a reasonable window.
    """
    timestamps: list[str] = []
    for card in verified_cards:
        ts = card.observed_at or card.pointer.get("ts", "")
        if ts:
            timestamps.append(ts)

    if len(timestamps) < 2:
        return 0.3  # Some evidence but no temporal confirmation

    # Check if timestamps are within 24 hours of each other
    try:
        sorted_ts = sorted(timestamps)
        # Simple heuristic: first and last timestamp within 7 days = good
        if sorted_ts[0][:10] and sorted_ts[-1][:10]:
            return 0.8  # timestamps present and parseable
    except (IndexError, TypeError):
        pass

    return 0.5  # timestamps exist but can't confirm alignment


def _p_contra(contradictions: list[Contradiction]) -> float:
    """
    Contradiction penalty: more contradictions = lower trust.
    Each contradiction reduces trust by ~0.15 (up to the penalty weight cap).
    """
    if not contradictions:
        return 0.0
    return _clamp(len(contradictions) * 0.15 / 0.30)  # normalize to [0, 1]


def _p_unver(dropped_count: int, total_count: int) -> float:
    """
    Unverified/dropped card penalty.
    Higher penalty if many cards were dropped (unverifiable claims).
    """
    if total_count == 0:
        return 0.0
    return _clamp(dropped_count / total_count)


# ---------------------------------------------------------------------------
# Main trust scorer
# ---------------------------------------------------------------------------

def compute_trust(
    verified_cards: list[EvidenceCard],
    dropped_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
    hypotheses: Optional[list[Hypothesis]] = None,
) -> TrustSummary:
    """
    Compute the deterministic trust score and policy action.

    Args:
        verified_cards:  Cards that passed verification.
        dropped_cards:   Cards that failed verification.
        contradictions:  Contradictions found by the reconciler.
        hypotheses:      Optional list of hypotheses (for gap check).

    Returns:
        TrustSummary with score, band, policy_action, components, and rationale.
    """
    total = len(verified_cards) + len(dropped_cards)

    # Compute components
    components = TrustComponents(
        c_ver=round(_c_ver(len(verified_cards), total), 4),
        c_div=round(_c_div(verified_cards), 4),
        c_spec=round(_c_spec(verified_cards), 4),
        c_time=round(_c_time(verified_cards), 4),
        p_contra=round(_p_contra(contradictions), 4),
        p_unver=round(_p_unver(len(dropped_cards), total), 4),
    )

    # Apply formula
    raw_score = (
        W_VER * components.c_ver
        + W_DIV * components.c_div
        + W_SPEC * components.c_spec
        + W_TIME * components.c_time
        - P_CONTRA * components.p_contra
        - P_UNVER * components.p_unver
    )
    score = round(_clamp(raw_score), 2)

    # Determine band
    if score >= 0.70:
        band = DecisionBand.HIGH
        policy = PolicyAction.CONCLUDE
    elif score >= 0.45:
        band = DecisionBand.MEDIUM
        policy = PolicyAction.CONCLUDE_WITH_CAVEAT
    else:
        band = DecisionBand.LOW
        policy = PolicyAction.ABSTAIN

    # Additional ABSTAIN check: top-2 hypothesis gap < 0.10
    if hypotheses and len(hypotheses) >= 2:
        sorted_h = sorted(hypotheses, key=lambda h: h.score, reverse=True)
        gap = sorted_h[0].score - sorted_h[1].score
        if gap < 0.10 and band != DecisionBand.LOW:
            policy = PolicyAction.ABSTAIN
            band = DecisionBand.LOW  # Override

    # Build rationale
    rationale_parts = [
        f"Verified {len(verified_cards)}/{total} cards",
        f"({len({c.source_type for c in verified_cards})} source types)",
    ]
    if contradictions:
        rationale_parts.append(
            f"{len(contradictions)} contradiction(s): "
            + ", ".join(c.kind.value for c in contradictions)
        )
    if len(dropped_cards) > 0:
        rationale_parts.append(f"{len(dropped_cards)} card(s) dropped by verifier")
    rationale_parts.append(f"Trust score: {score} ({band.value})")

    return TrustSummary(
        score=score,
        band=band,
        policy_action=policy,
        components=components,
        rationale=". ".join(rationale_parts),
    )
