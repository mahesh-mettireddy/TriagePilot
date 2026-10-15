"""
engine/agents/report_agent.py
-----------------------------
Step 8 of the 12-step pipeline: Report Generator.

Uses gemini-2.5-flash (or deterministic fallback) to produce:
  - Developer root-cause brief (summary)
  - Customer-safe reply draft (passed through leakcheck.py)
  - Jira bug draft with GitHub line permalinks
  - KB gap flag
  - <= 2 discriminating client questions (if ABSTAIN or MEDIUM)

Input: verified_cards, hypotheses, contradictions, trust_summary, ticket.
Output: ReportOutput (the final complete pipeline response).
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from engine.leakcheck import check_customer_reply, sanitize_or_flag
from engine.leakcheck import LeakCheckResult as _LeakCheckDC
from engine.masking import mask_for_model
from engine.policy import bind_report_revision
from engine.schemas import (
    ClientQuestion,
    Contradiction,
    DecisionBand,
    EvidenceCard,
    HumanDecision,
    Hypothesis,
    JiraDraft,
    KBGap,
    LeakCheckResult,
    PolicyAction,
    ReportOutput,
    SourceType,
    TicketDTO,
    TrustSummary,
    AgentRoutingPlan,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic report builder (fallback)
# ---------------------------------------------------------------------------

def _build_report_deterministic(
    ticket: TicketDTO,
    routing_plan: AgentRoutingPlan,
    verified_cards: list[EvidenceCard],
    dropped_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
    hypotheses: list[Hypothesis],
    trust: TrustSummary,
    investigation_id: str,
) -> ReportOutput:
    """Build a complete ReportOutput without LLM assistance."""

    # --- Developer summary ---
    primary_hypothesis = hypotheses[0] if hypotheses else None
    if primary_hypothesis:
        summary = (
            f"Root Cause: {primary_hypothesis.statement}\n"
            f"Culprit files: {', '.join(primary_hypothesis.culprit_files) or 'N/A'}\n"
            f"Confidence: {trust.band.value} (Trust score: {trust.score})"
        )
    else:
        summary = (
            f"Investigation completed with {len(verified_cards)} verified evidence cards. "
            f"Trust: {trust.score} ({trust.band.value}). "
            f"No clear root cause identified."
        )

    # --- Recommended actions ---
    actions: list[str] = []
    if primary_hypothesis and primary_hypothesis.culprit_files:
        actions.append(f"Review and fix: {', '.join(primary_hypothesis.culprit_files)}")
    if contradictions:
        contra_types = list({c.kind.value for c in contradictions})
        actions.append(f"Investigate contradictions: {', '.join(contra_types)}")
    if trust.policy_action == PolicyAction.ABSTAIN:
        actions.append("Gather additional information from the customer")
    elif trust.policy_action == PolicyAction.CONCLUDE_WITH_CAVEAT:
        actions.append("Verify root cause hypothesis with additional testing")
    actions.append("Update runbook documentation if stale docs were identified")

    # --- Workaround ---
    workaround = None
    for card in verified_cards:
        if card.source_type == SourceType.TICKET:
            pointer = card.pointer
            if pointer.get("system") == "KnowledgeBase" and "workaround" in pointer.get("field", ""):
                workaround = card.snippet
                break

    # --- Customer reply draft ---
    customer_reply = mask_for_model(
        _build_customer_reply(ticket, trust, primary_hypothesis, workaround),
        max_chars=4000,
    )

    # --- Leak check the customer reply ---
    leak_dc = check_customer_reply(customer_reply)
    if not leak_dc.passed:
        customer_reply, leak_dc_2 = sanitize_or_flag(customer_reply)
        all_notes = leak_dc.notes + leak_dc_2.notes
        leak_result = LeakCheckResult(passed=leak_dc_2.passed, notes=all_notes)
    else:
        leak_result = LeakCheckResult(passed=leak_dc.passed, notes=leak_dc.notes)

    # --- Questions for client (if ABSTAIN or MEDIUM) ---
    questions: list[ClientQuestion] = []
    if trust.policy_action in (PolicyAction.ABSTAIN, PolicyAction.CONCLUDE_WITH_CAVEAT):
        questions = _generate_questions(ticket, verified_cards, trust)

    # --- Jira draft ---
    jira_draft = _build_jira_draft(
        ticket, primary_hypothesis, verified_cards, contradictions
    )

    # --- KB gap ---
    kb_gap = _detect_kb_gap(verified_cards, contradictions)

    # --- Suggested diagnostic queries ---
    diag_queries: list[str] = []
    if primary_hypothesis:
        for f in primary_hypothesis.culprit_files[:2]:
            diag_queries.append(f"git log --oneline -10 {f}")
            diag_queries.append(f"git blame {f}")

    # --- Owner team (from profile or ticket) ---
    owner_team = "team-payments"  # default
    if ticket.product_hint == "notifications":
        owner_team = "team-comms"
    elif ticket.product_hint == "fees":
        owner_team = "team-core-ledger"

    report = ReportOutput(
        investigation_id=investigation_id,
        ticket_id=ticket.id,
        scenario_id=ticket.scenario_id,
        mode_used="live",
        ticket_class=routing_plan.ticket_class,
        severity=routing_plan.severity,
        owner_team=owner_team,
        summary=summary,
        routing_plan=routing_plan,
        probable_root_cause=primary_hypothesis,
        alternatives=hypotheses[1:],
        contradictions=contradictions,
        trust=trust,
        verified_cards=verified_cards,
        dropped_cards=dropped_cards,
        verified_claims_count=len(verified_cards),
        dropped_claims_count=len(dropped_cards),
        recommended_actions=actions,
        workaround=workaround,
        questions_for_client=questions,
        customer_reply_draft=customer_reply,
        leak_check=leak_result,
        jira_draft=jira_draft,
        kb_gap=kb_gap,
        suggested_diagnostic_queries=diag_queries,
        decision=HumanDecision(),
        audit_ref=f"audit:{investigation_id}",
        write_back_allowed=(
            trust.policy_action in (PolicyAction.CONCLUDE, PolicyAction.CONCLUDE_WITH_CAVEAT)
            and leak_result.passed
        ),
        needs_human_edit=not leak_result.passed,
    )
    report.summary = mask_for_model(report.summary, max_chars=4000)
    report.workaround = mask_for_model(report.workaround or "", max_chars=400) or None
    if report.probable_root_cause:
        report.probable_root_cause.statement = mask_for_model(
            report.probable_root_cause.statement, max_chars=400
        )
    report.alternatives = [
        hypothesis.model_copy(
            update={"statement": mask_for_model(hypothesis.statement, max_chars=400)}
        )
        for hypothesis in report.alternatives
    ]
    return bind_report_revision(report)


# ---------------------------------------------------------------------------
# Customer reply builder
# ---------------------------------------------------------------------------

def _build_customer_reply(
    ticket: TicketDTO,
    trust: TrustSummary,
    hypothesis: Optional[Hypothesis],
    workaround: Optional[str],
) -> str:
    """Build a safe customer-facing reply (NO internal paths or SHAs)."""
    if trust.policy_action == PolicyAction.ABSTAIN:
        return (
            "Thank you for contacting us. We need a bit more information to "
            "investigate your issue:\n"
            "1. When exactly did this issue start? (date and time with timezone)\n"
            "2. What was the transaction or reference number?\n\n"
            "Please reply with these details and we will resume the investigation immediately."
        )

    parts = ["Thank you for reporting this issue. Our team has completed an initial investigation."]

    if hypothesis:
        # Sanitise the statement to avoid leaking internal paths
        safe_statement = re.sub(r"app/[\w/]+\.\w+", "the affected module", hypothesis.statement)
        safe_statement = re.sub(r"\b\w+\.py\b", "the relevant code", safe_statement)
        parts.append(f"\nOur analysis indicates: {safe_statement}")

    if workaround:
        safe_workaround = re.sub(r"app/[\w/]+\.\w+", "the system", workaround)
        parts.append(f"\nIn the meantime, you can try this workaround: {safe_workaround}")

    if trust.policy_action == PolicyAction.CONCLUDE_WITH_CAVEAT:
        parts.append(
            "\nPlease note: we have identified the most likely cause but are "
            "conducting further verification. We will update you within 24 hours."
        )
    else:
        parts.append(
            "\nOur engineering team has been notified and a fix is being prepared. "
            "We apologise for the inconvenience."
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Question generator (for ABSTAIN / MEDIUM)
# ---------------------------------------------------------------------------

def _generate_questions(
    ticket: TicketDTO,
    verified_cards: list[EvidenceCard],
    trust: TrustSummary,
) -> list[ClientQuestion]:
    """Generate <= 2 discriminating questions for the client."""
    questions: list[ClientQuestion] = []
    text = (ticket.masked_text or ticket.text).lower()

    # Question 1: Missing timestamp
    has_timestamp = any(
        c.observed_at for c in verified_cards
    ) or re.search(r"\d{1,2}:\d{2}", text)
    if not has_timestamp:
        questions.append(ClientQuestion(
            text="When exactly did this issue first occur? Please include the date, time, and timezone (e.g., 4:15 PM IST on Oct 7).",
            discriminates=["TIME_MISMATCH", "temporal_alignment"],
        ))

    # Question 2: Missing transaction ID
    has_txn = "txn-" in text
    if not has_txn and len(questions) < 2:
        questions.append(ClientQuestion(
            text="Could you provide the transaction or reference number related to this issue?",
            discriminates=["record_lookup", "state_verification"],
        ))

    # Question 3: Ambiguous error description
    if len(questions) < 2:
        questions.append(ClientQuestion(
            text="What specific error message or behaviour did you observe? (e.g., 'Transfer rejected', a specific error code, or a screenshot)",
            discriminates=["error_classification", "code_defect_vs_config"],
        ))

    return questions[:2]


# ---------------------------------------------------------------------------
# Jira draft builder
# ---------------------------------------------------------------------------

def _build_jira_draft(
    ticket: TicketDTO,
    hypothesis: Optional[Hypothesis],
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
) -> Optional[JiraDraft]:
    """Build a Jira bug draft if a hypothesis with culprit files exists."""
    if not hypothesis:
        return None

    verified_ids = {card.card_id for card in verified_cards}
    supporting_ids = [
        card_id for card_id in hypothesis.supporting_card_ids if card_id in verified_ids
    ]
    if not supporting_ids:
        # A Jira claim without a verified proof anchor is not safe to draft.
        return None

    title = f"[TriagePilot] {mask_for_model(hypothesis.statement[:100], max_chars=100)}"
    desc_parts = [
        f"**Auto-generated by TriagePilot** from ticket {ticket.id}",
        f"\n## Root Cause Analysis",
        f"{mask_for_model(hypothesis.statement, max_chars=400)} (proof: {', '.join(supporting_ids)})",
        f"\n**Culprit files:** {', '.join(hypothesis.culprit_files) or 'To be determined'}",
    ]

    if hypothesis.culprit_commit:
        desc_parts.append(f"**Culprit commit:** `{hypothesis.culprit_commit[:12]}`")

    if contradictions:
        desc_parts.append("\n## Contradictions Detected")
        for c in contradictions:
            desc_parts.append(f"- **{c.kind.value}**: {c.note}")

    desc_parts.append(f"\n## Evidence ({len(verified_cards)} verified cards)")
    for card in verified_cards[:5]:
        desc_parts.append(
            f"- `{card.card_id}` [{card.source_type.value}]: "
            f"{mask_for_model(card.claim, max_chars=200)}"
        )
        proof_link = _proof_link(card)
        if proof_link:
            desc_parts.append(f"  - Proof: {proof_link}")

    # Evidence links
    evidence_links = [link for card in verified_cards if (link := _proof_link(card))]

    # Labels
    labels = ["triagepilot", "auto-generated", ticket.product_hint]
    if contradictions:
        labels.extend(c.kind.value.lower() for c in contradictions[:2])

    return JiraDraft(
        title=title,
        description="\n".join(desc_parts),
        repro_steps=[
            f"1. Original ticket: {ticket.id}",
            f"2. Scenario: {ticket.scenario_id or 'custom'}",
            f"3. See evidence cards in description",
        ],
        evidence_links=evidence_links,
        labels=labels,
    )


def _proof_link(card: EvidenceCard) -> Optional[str]:
    """Create a stable, source-aware proof locator for a verified card."""
    if card.github_permalink:
        return card.github_permalink
    pointer = card.pointer
    source = card.source_type.value
    if source == "log":
        return f"log://{pointer.get('log_id', '?')}?ts={pointer.get('ts', '')}"
    if source == "doc":
        return f"doc://{pointer.get('page_id', '?')}#{pointer.get('section', '')}"
    if source == "record":
        return f"record://{pointer.get('id', '?')}?field={pointer.get('field', '')}"
    if source == "ticket":
        return f"ticket://{pointer.get('system', 'unknown')}/{pointer.get('id', '?')}#{pointer.get('field', '')}"
    if source == "visual":
        return f"attachment://{pointer.get('attachment_id', '?')}"
    return None


# ---------------------------------------------------------------------------
# KB gap detector
# ---------------------------------------------------------------------------

def _detect_kb_gap(
    verified_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
) -> Optional[KBGap]:
    """Detect if any doc needs updating based on STALE_DOC_FLAG."""
    for c in contradictions:
        if c.kind.value == "STALE_DOC_FLAG":
            # Find the doc card
            for card in verified_cards:
                if card.card_id == c.card_a and card.source_type == SourceType.DOC:
                    return KBGap(
                        page_id=card.pointer.get("page_id", "?"),
                        issue=c.note,
                    )
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_report(
    ticket: TicketDTO,
    routing_plan: AgentRoutingPlan,
    verified_cards: list[EvidenceCard],
    dropped_cards: list[EvidenceCard],
    contradictions: list[Contradiction],
    hypotheses: list[Hypothesis],
    trust: TrustSummary,
    investigation_id: str,
) -> ReportOutput:
    """
    Generate the final ReportOutput.

    Uses deterministic builder (LLM report polishing can be added later).
    """
    return _build_report_deterministic(
        ticket=ticket,
        routing_plan=routing_plan,
        verified_cards=verified_cards,
        dropped_cards=dropped_cards,
        contradictions=contradictions,
        hypotheses=hypotheses,
        trust=trust,
        investigation_id=investigation_id,
    )
