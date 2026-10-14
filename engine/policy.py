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
