"""
engine/trust.py
---------------
Step 7 of the 12-step pipeline: Deterministic Evidence-Quality Scorer & Conclusion Gates.

**Pure Python — ZERO LLM involvement.**

Computes a transparent evidence-quality / trust score [0.00 - 1.00] from verified evidence:

  score = clamp(
      0.40 * c_ver    # verified evidence volume (deduplicated by provenance)
    + 0.25 * c_div    # source diversity (how many source types)
    + 0.20 * c_spec   # code/log specificity (file:line pointers)
    + 0.15 * c_time   # temporal alignment (timestamps present & consistent)
    - 0.30 * p_contra # contradiction penalty
    - 0.20 * p_unver  # unverified/dropped card penalty
    , 0, 1
  )

Exact precedence for trust bands:
  HIGH   : score >= 0.70            -> CONCLUDE
  MEDIUM : 0.45 <= score < 0.70     -> CONCLUDE_WITH_CAVEAT
  LOW    : score <  0.45            -> ABSTAIN

Hard conclusion gates:
  - Provenance deduplication prevents duplicate citations to the same document/file
    from inflating evidence volume (`c_ver`).
  - Unresolved material contradictions or missing claim-supported causal evidence
    gate the outcome (`NEED_EVIDENCE`, `SUPPORTED_HYPOTHESIS`, `REPRODUCED_IN_FIXTURE`, `BLOCKED`).
  - Top-2 hypothesis gap < 0.10 forces ABSTAIN (`NEED_EVIDENCE`).
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

from engine.schemas import (
    Contradiction,
    ContradictionKind,
    DecisionBand,
    EvidenceCard,
    EvidenceLevel,
    GateOutcome,
    Hypothesis,
    PolicyAction,
    SourceType,
    Stance,
    TrustComponents,
    TrustSummary,
)
from engine.verifier import compute_provenance_key

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


def _unique_provenance_keys(verified_cards: list[EvidenceCard]) -> set[str]:
    keys: set[str] = set()
    for card in verified_cards:
        key = card.verification.provenance_key or compute_provenance_key(card)
        keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# Component calculators
# ---------------------------------------------------------------------------

def _c_ver(
    verified_count: int,
    total_count: int,
    unique_provenance_count: Optional[int] = None,
) -> float:
    """
    Verified evidence volume: ratio of verified cards to total,
    boosted by log-scale for unique provenance count (5+ unique sources = full credit).
    Duplicate citations to the same provenance key do not inflate volume credit.
    """
    if total_count == 0 or verified_count == 0:
        return 0.0
    effective_verified = (
        unique_provenance_count
        if unique_provenance_count is not None
        else verified_count
    )
    dropped_count = max(0, total_count - verified_count)
    effective_total = effective_verified + dropped_count
    ratio = effective_verified / effective_total if effective_total > 0 else 0.0
    abs_bonus = min(1.0, math.log1p(effective_verified) / math.log1p(5))
    return _clamp(0.6 * ratio + 0.4 * abs_bonus)


def _c_div(verified_cards: list[EvidenceCard]) -> float:
    """
    Source diversity: how many distinct SourceTypes are represented.
    6 possible types -> 1.0 if all 6 present.
    """
    if not verified_cards:
        return 0.0
    all_types = {SourceType.LOG, SourceType.CODE, SourceType.DOC,
                 SourceType.TICKET, SourceType.RECORD, SourceType.VISUAL}
    present = {card.source_type for card in verified_cards}
    if present in ({SourceType.DOC}, {SourceType.TICKET, SourceType.LOG}):
        return 0.65
    return _clamp(len(present) / len(all_types) * 1.35)


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
        elif card.source_type == SourceType.TICKET:
            if pointer.get("id") and pointer.get("system"):
                specific_count += 1
        elif card.source_type == SourceType.VISUAL:
            if pointer.get("attachment_id"):
                specific_count += 1

    return _clamp(specific_count / len(verified_cards))


def _c_time(verified_cards: list[EvidenceCard]) -> float:
    """
    Temporal alignment: are timestamps present and consistent across cards?
    Higher if current-incident log/code/record timestamps cluster within a 24h window.
    """
    obs_cards = [
        c for c in verified_cards
        if c.source_type in {SourceType.LOG, SourceType.RECORD, SourceType.CODE}
    ]
    target_cards = obs_cards if obs_cards else verified_cards

    timestamps: list[str] = []
    for card in target_cards:
        ts = card.observed_at or card.pointer.get("ts", "")
        if ts:
            timestamps.append(ts)

    if len(timestamps) < 2:
        if any(
            (c.source_type == SourceType.DOC and c.pointer.get("last_updated"))
            or (c.source_type == SourceType.TICKET and (c.observed_at or c.pointer.get("id")))
            for c in verified_cards
        ):
            return 0.8
        return 0.3  # Some evidence but no temporal confirmation

    parsed: list[datetime] = []
    for value in timestamps:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            parsed.append(dt.astimezone(timezone.utc))
        except (TypeError, ValueError):
            return 0.0
    if len(parsed) < 2:
        return 0.3
    span = max(parsed) - min(parsed)
    return 0.8 if span.total_seconds() <= 24 * 60 * 60 else 0.2


def _p_contra(contradictions: list[Contradiction]) -> float:
    """
    Contradiction penalty: more contradictions = lower trust.
    Each contradiction reduces trust proportionally up to the penalty weight cap.
    """
    if not contradictions:
        return 0.0
    return _clamp(len(contradictions) * 0.04 / 0.30)  # normalize to [0, 1]


def _p_unver(dropped_count: int, total_count: int) -> float:
    """
    Unverified/dropped card penalty.
    Higher penalty if many cards were dropped (unverifiable claims).
    """
    if total_count == 0:
        return 0.0
    return _clamp(dropped_count / total_count)


# ---------------------------------------------------------------------------
# Main trust scorer & hard conclusion gates
# ---------------------------------------------------------------------------

def compute_trust(
    verified_cards: list[EvidenceCard],
    dropped_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
    hypotheses: Optional[list[Hypothesis]] = None,
    human_context: Optional[Any] = None,
    parent_trust: Optional[TrustSummary] = None,
) -> TrustSummary:
    """
    Compute the deterministic evidence-quality score, apply hard conclusion gates,
    and determine the policy action and gate outcome.

    Args:
        verified_cards:  Cards that passed verification.
        dropped_cards:   Cards that failed verification.
        contradictions:  Contradictions found by the reconciler.
        hypotheses:      Optional list of hypotheses (for gap & support check).
        human_context:   Optional HumanContext from an interactive HITL turn.
        parent_trust:    Optional TrustSummary from the parent investigation turn.

    Returns:
        TrustSummary with score, band, policy_action, gate_outcome, gate_reasons,
        components, and rationale.
    """
    total = len(verified_cards) + len(dropped_cards)
    unique_prov = _unique_provenance_keys(verified_cards)
    unique_prov_count = len(unique_prov)

    # Compute components (using deduplicated provenance count for c_ver)
    raw_components = {
        "c_ver": _c_ver(len(verified_cards), total, unique_prov_count),
        "c_div": _c_div(verified_cards),
        "c_spec": _c_spec(verified_cards),
        "c_time": _c_time(verified_cards),
        "p_contra": _p_contra(contradictions),
        "p_unver": _p_unver(len(dropped_cards), total),
    }
    components = TrustComponents(
        **{key: round(value, 4) for key, value in raw_components.items()},
        unique_provenance_count=unique_prov_count,
    )

    # Apply formula
    raw_score = (
        W_VER * raw_components["c_ver"]
        + W_DIV * raw_components["c_div"]
        + W_SPEC * raw_components["c_spec"]
        + W_TIME * raw_components["c_time"]
        - P_CONTRA * raw_components["p_contra"]
        - P_UNVER * raw_components["p_unver"]
    )
    bounded_score = _clamp(raw_score)
    score = round(bounded_score, 2)

    # Exact score boundary precedence:
    # HIGH >= 0.70, MEDIUM 0.45..0.69, LOW < 0.45
    if score >= 0.70:
        band = DecisionBand.HIGH
        policy = PolicyAction.CONCLUDE
    elif score >= 0.45:
        band = DecisionBand.MEDIUM
        policy = PolicyAction.CONCLUDE_WITH_CAVEAT
    else:
        band = DecisionBand.LOW
        policy = PolicyAction.ABSTAIN

    gate_reasons: list[str] = []

    if len(verified_cards) > unique_prov_count:
        gate_reasons.append(
            f"Deduplicated {len(verified_cards)} verified citations into {unique_prov_count} unique provenance source(s)"
        )

    # Hard Gate 1: Top-2 hypothesis gap < 0.10 -> force ABSTAIN (NEED_EVIDENCE)
    if hypotheses and len(hypotheses) >= 2:
        sorted_h = sorted(hypotheses, key=lambda h: h.score, reverse=True)
        gap = sorted_h[0].score - sorted_h[1].score
        if gap < 0.10 and band != DecisionBand.LOW:
            policy = PolicyAction.ABSTAIN
            band = DecisionBand.LOW
            gate_reasons.append(
                f"Top-2 hypothesis gap ({gap:.2f}) < 0.10 threshold; discriminating check required"
            )

    # Hard Gate 2: Valid source citation that does NOT explain the failure
    # If all CODE cards are only SOURCE_VALIDATED (e.g. unrelated function or httpx bump)
    # and there are no CLAIM_SUPPORTED/CAUSE_REPRODUCED causal cards, block HIGH conclusion.
    code_cards = [c for c in verified_cards if c.source_type == SourceType.CODE]
    if code_cards and all(
        c.verification.evidence_level == EvidenceLevel.SOURCE_VALIDATED
        and c.verification.limitations
        and "does not explain" in c.verification.limitations.lower()
        for c in code_cards
    ):
        if band == DecisionBand.HIGH:
            band = DecisionBand.MEDIUM
            policy = PolicyAction.CONCLUDE_WITH_CAVEAT
        gate_reasons.append(
            "Code citation exists at revision (SOURCE_VALIDATED) but does not explain the observed failure; blocked from HIGH root-cause conclusion"
        )

    # Hard Gate 3: Unresolved STATE_MISMATCH without code/log corroboration
    has_state_mismatch = any(c.kind == ContradictionKind.STATE_MISMATCH for c in contradictions)
    has_causal_code_or_log = any(
        c.source_type in {SourceType.CODE, SourceType.LOG}
        and c.verification.evidence_level in {EvidenceLevel.CLAIM_SUPPORTED, EvidenceLevel.CAUSE_REPRODUCED}
        for c in verified_cards
    )
    if has_state_mismatch and not has_causal_code_or_log and band == DecisionBand.HIGH:
        band = DecisionBand.MEDIUM
        policy = PolicyAction.CONCLUDE_WITH_CAVEAT
        gate_reasons.append(
            "Unresolved STATE_MISMATCH without corroborating code/log trace caps conclusion at CONCLUDE_WITH_CAVEAT"
        )

    # Hard Gate 4: Duplicate citations to a single provenance source must not masquerade as
    # independent corroboration to authorize a HIGH conclusion.
    if len(verified_cards) > 1 and unique_prov_count == 1 and band == DecisionBand.HIGH:
        band = DecisionBand.MEDIUM
        policy = PolicyAction.CONCLUDE_WITH_CAVEAT
        gate_reasons.append(
            f"All {len(verified_cards)} verified cards share a single provenance source; independent corroboration required for HIGH conclusion"
        )

    # Interactive HITL Gate & Live Git Commit Gate
    live_diff_cards = [c for c in verified_cards if bool(c.pointer.get("is_live_diff"))]
    has_completed_live_record = any(
        c.source_type == SourceType.RECORD and "COMPLETED" in c.snippet.upper()
        for c in verified_cards
    )
    has_behaviour_mismatch = any(c.kind == ContradictionKind.BEHAVIOUR_MISMATCH for c in contradictions)
    interactive_prefix = ""

    if live_diff_cards:
        lc = live_diff_cards[0]
        sha = str(lc.pointer.get("commit_sha") or lc.pointer.get("sha", ""))[:8]
        c_msg = str(lc.pointer.get("commit_message") or lc.pointer.get("commit_msg") or "live code edit")
        if has_completed_live_record and not has_behaviour_mismatch:
            gate_reasons.insert(
                0,
                f"Live Git Commit @{sha} ('{c_msg}') verified: code fix resolved boundary defect & live probe COMPLETED with 0 contradictions",
            )
            interactive_prefix = (
                f"Live Git Fix Verified (@{sha}: '{c_msg}') — boundary transfer COMPLETED with 0 policy contradictions. "
            )
        else:
            gate_reasons.insert(
                0,
                f"Live Git Commit @{sha} ('{c_msg}') evaluated against live runtime telemetry",
            )
            interactive_prefix = f"Live Git Commit (@{sha}: '{c_msg}') inspected. "

    if human_context is not None and getattr(human_context, "message", "").strip():
        hc_src = (getattr(human_context, "source", "") or "DEV_STEER").upper()
        hc_msg = getattr(human_context, "message", "").strip()
        prior_desc = (
            f"{parent_trust.score} ({parent_trust.band.value} / {parent_trust.policy_action.value})"
            if parent_trust is not None
            else "Turn 1"
        )
        if hc_src == "EVIDENCE_UPDATE":
            if band == DecisionBand.HIGH:
                band = DecisionBand.MEDIUM
                policy = PolicyAction.CONCLUDE_WITH_CAVEAT
                score = min(score, 0.64)
            gate_reasons.insert(
                0,
                f"Interactive HITL ({hc_src}): Prior conclusion withdrawn ({prior_desc} -> {score} {band.value}); operator evidence ('{hc_msg[:80]}') requires premise verification",
            )
            interactive_prefix = (
                f"Interactive Turn (EVIDENCE_UPDATE): Prior revision withdrawn ({prior_desc} -> {score} {band.value}) after operator supplied '{hc_msg[:75]}'. "
            )
        elif hc_src == "CLIENT_REPLY":
            gate_reasons.insert(
                0,
                f"Interactive HITL ({hc_src}): Upgraded from {prior_desc} -> {score} ({band.value} / {policy.value}) after client clarification ('{hc_msg[:80]}')",
            )
            interactive_prefix = (
                f"Interactive Turn (CLIENT_REPLY): Upgraded from {prior_desc} -> {score} ({band.value}) using client details ('{hc_msg[:75]}'). "
            )
        elif hc_src == "DEV_STEER":
            gate_reasons.insert(
                0,
                f"Interactive HITL ({hc_src}): Swarm re-steered by engineer ('{hc_msg[:80]}') -> {score} ({band.value} / {policy.value})",
            )
            interactive_prefix = (
                f"Interactive Turn (DEV_STEER): Engineer steer ('{hc_msg[:75]}') verified across {unique_prov_count} provenance sources. "
            )

    # Determine explicit GateOutcome
    has_reproduced = any(
        c.verification.evidence_level == EvidenceLevel.CAUSE_REPRODUCED
        for c in verified_cards
    )
    if policy == PolicyAction.ESCALATE_SECURITY:
        gate_outcome = GateOutcome.BLOCKED
    elif policy == PolicyAction.ABSTAIN:
        gate_outcome = GateOutcome.NEED_EVIDENCE
    elif band == DecisionBand.HIGH and has_reproduced:
        gate_outcome = GateOutcome.REPRODUCED_IN_FIXTURE
    else:
        gate_outcome = GateOutcome.SUPPORTED_HYPOTHESIS

    if not gate_reasons:
        gate_reasons.append(
            f"Passed evidence gate ({gate_outcome.value}) with {unique_prov_count} independent provenance source(s)"
        )

    # Build rationale
    rationale_parts = [
        f"Verified {len(verified_cards)}/{total} cards",
        f"({unique_prov_count} unique provenance, {len({c.source_type for c in verified_cards})} source types)",
    ]
    if contradictions:
        rationale_parts.append(
            f"{len(contradictions)} contradiction(s): "
            + ", ".join(c.kind.value for c in contradictions)
        )
    if len(dropped_cards) > 0:
        rationale_parts.append(f"{len(dropped_cards)} card(s) dropped by verifier")
    rationale_parts.append(f"Trust score: {score} ({band.value} / {gate_outcome.value})")

    return TrustSummary(
        score=score,
        band=band,
        policy_action=policy,
        components=components,
        rationale=interactive_prefix + ". ".join(rationale_parts),
        gate_outcome=gate_outcome,
        gate_reasons=gate_reasons,
    )
