"""
engine/policy.py
----------------
Policy Gate and Maker-Checker Governance Rules.

Enforces organizational policies on top of the mathematical trust score:
  - ESCALATE_SECURITY: triggered immediately on security-sensitive tickets.
  - ABSTAIN: triggered if trust score < 0.45 or top-2 hypothesis score gap < 0.10.
  - CONCLUDE_WITH_CAVEAT: trust score between 0.45 and 0.70.
  - CONCLUDE: trust score >= 0.70 with sufficient evidence.

Maker-Checker Gate:
  - Any external mutation (WritePort: Jira creation, client comment posting)
    MUST be preceded by an explicit HumanDecision (status="approved").
  - Evaluates whether an investigation report is ready for automatic suggestion
    or requires mandatory human intervention.
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from engine.schemas import (
    HumanDecision,
    PolicyAction,
    ReportOutput,
    TicketClass,
    TrustSummary,
)


def evaluate_policy_gate(
    ticket_class: TicketClass,
    trust: TrustSummary,
    injection_detected: bool = False,
) -> PolicyAction:
    """
    Determine the definitive PolicyAction for an investigation.
    Security sensitivity or severe injection overrides standard score-based policy.
    """
    if ticket_class == TicketClass.SECURITY_SENSITIVE:
        return PolicyAction.ESCALATE_SECURITY

    # Return the policy action already determined by mathematical trust
    return trust.policy_action


def can_execute_writeback(decision: HumanDecision) -> tuple[bool, Optional[str]]:
    """
    Check if writeback (e.g. Jira issue creation, ticket comment) is authorized.

    Maker-checker rule: Only status == "approved" allows write-back.
    """
    if decision.status == "approved":
        return True, None
    if decision.status == "rejected":
        return False, "Write-back rejected by operator."
    if decision.status == "edited":
        # Edited drafts must still be confirmed/approved
        return False, "Draft was edited; awaiting final approval."
    return False, "Write-back requires explicit human approval."


def compute_report_hash(report: ReportOutput) -> str:
    """Return the stable approval-binding hash for a report revision.

    The decision and the hash field itself are deliberately excluded.  This
    lets the report be updated with the eventual human decision without
    changing the artifact the reviewer approved.
    """
    payload = report.model_dump(
        mode="json",
        exclude={"decision", "report_hash"},
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def bind_report_revision(report: ReportOutput) -> ReportOutput:
    """Populate the report hash used by the maker-checker gate."""
    report.report_hash = compute_report_hash(report)
    return report


def validate_report_approval(
    report: ReportOutput,
    decision: HumanDecision,
) -> tuple[bool, Optional[str]]:
    """Fail closed for unsafe, stale, or replayed approvals."""
    allowed, reason = can_execute_writeback(decision)
    if not allowed:
        return False, reason
    if report.trust.policy_action in {
        PolicyAction.ABSTAIN,
        PolicyAction.ESCALATE_SECURITY,
    }:
        return False, f"Write-back blocked by policy action {report.trust.policy_action.value}."
    if report.needs_human_edit or not report.leak_check.passed:
        return False, "Write-back blocked until the customer-facing draft passes leak checks."
    if not decision.decision_id:
        return False, "Approved decisions require a unique decision_id."
    if decision.report_revision != report.report_revision:
        return False, "Approval is stale: report_revision does not match the current report."
    if decision.report_hash != report.report_hash:
        return False, "Approval is stale: report_hash does not match the current report."
    return True, None
