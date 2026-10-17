"""
engine/next_check.py
--------------------
Deterministic Next-Useful-Check Selector.

Selects and ranks allowlisted diagnostic checks that discriminate between
competing hypotheses, request missing decisive inputs, or verify fixture/control
transactions without repeating already-completed lookups.
"""

from __future__ import annotations

from typing import List, Optional

from engine.schemas import (
    Contradiction,
    ContradictionKind,
    EvidenceCard,
    Hypothesis,
    NextCheck,
    PolicyAction,
    SourceType,
    TicketClass,
    TicketDTO,
    TrustSummary,
)


def select_next_checks(
    ticket: TicketDTO,
    verified_cards: List[EvidenceCard],
    contradictions: List[Contradiction],
    hypotheses: List[Hypothesis],
    trust: TrustSummary,
) -> tuple[Optional[NextCheck], List[NextCheck]]:
    """
    Build and rank allowlisted NextCheck objects for the current investigation state.
    Returns (primary_next_check, candidate_checks).
    """
    candidates: List[NextCheck] = []
    text = f"{ticket.masked_text or ticket.text} {' '.join(c.snippet for c in verified_cards)}".lower()
    has_code = any(c.source_type == SourceType.CODE for c in verified_cards)
    has_log = any(c.source_type == SourceType.LOG for c in verified_cards)
    has_record = any(c.source_type == SourceType.RECORD for c in verified_cards)
    has_doc = any(c.source_type == SourceType.DOC for c in verified_cards)

    hyp_ids = [h.hypothesis_id for h in hypotheses[:2]] or ["H1", "H2"]

    is_live_diff = any(bool(c.pointer.get("is_live_diff")) for c in verified_cards)
    has_completed_live_record = any(
        c.source_type == SourceType.RECORD and "COMPLETED" in c.snippet.upper()
        for c in verified_cards
    )
    has_behaviour_mismatch = any(
        c.kind == ContradictionKind.BEHAVIOUR_MISMATCH for c in contradictions
    )
    is_live_fix_verified = is_live_diff and has_completed_live_record and not has_behaviour_mismatch

    # 0a. Interactive HITL Turn-2+ checks (CLIENT_REPLY / DEV_STEER / EVIDENCE_UPDATE)
    if ticket.human_context and getattr(ticket.human_context, "message", "").strip():
        hc_source = (getattr(ticket.human_context, "source", "") or "DEV_STEER").upper()
        hc_msg = getattr(ticket.human_context, "message", "").strip()
        if hc_source == "EVIDENCE_UPDATE":
            candidates.append(
                NextCheck(
                    check_id="CHK-PREMISE-WITHDRAWAL-AUDIT",
                    title="Contradictory Evidence Applied: Prior Revision Withdrawn & Re-Evaluated",
                    target_system="Version-Bound Premise Gate & Operations",
                    purpose=(
                        f"Prior conclusion was automatically withdrawn after new operator evidence "
                        f"('{hc_msg[:110]}') invalidated the earlier premise."
                    ),
                    required_inputs=[
                        "Withdrawn revision hash",
                        f"Operator evidence: {hc_msg[:60]}",
                        "Updated policy gate",
                    ],
                    discriminates_hypotheses=hyp_ids,
                    expected_outcomes=[
                        "Confirm updated operational/compliance root cause before approving new revision",
                        "Prior stale report_hash is permanently blocked from write-back",
                    ],
                    effort_level="low",
                    status="recommended",
                )
            )
        elif hc_source == "CLIENT_REPLY" and trust.policy_action != PolicyAction.ABSTAIN:
            candidates.append(
                NextCheck(
                    check_id="CHK-CLIENT-CORRELATION-RESOLVED",
                    title="Client Clarification Correlated -> Verify Pinpointed Root Cause & Approve Write-Back",
                    target_system="Maker-Checker Gate & Verified Code/Log Trace",
                    purpose=(
                        f"Client follow-up ('{hc_msg[:100]}') resolved Turn-1 abstention and bound "
                        f"the incident to verified telemetry and code lines."
                    ),
                    required_inputs=[
                        f"Client reply: {hc_msg[:60]}",
                        "Verified code & ledger proof cards",
                        "report_hash",
                    ],
                    discriminates_hypotheses=hyp_ids,
                    expected_outcomes=[
                        "Approve write-back to dispatch engineering Jira & customer resolution",
                        "Use Engineer Steer if additional module inspection is needed",
                    ],
                    effort_level="low",
                    status="completed",
                )
            )
        elif hc_source == "DEV_STEER":
            candidates.append(
                NextCheck(
                    check_id="CHK-STEER-DIRECTIVE-VERIFIED",
                    title=f"Engineer Steer Executed: Re-Evaluated Swarm Against '{hc_msg[:52]}'",
                    target_system="Swarm Re-Router & Deterministic Verifier",
                    purpose=(
                        f"Executed developer steer ('{hc_msg[:110]}') across active specialists "
                        f"and re-scored hypothesis ranking."
                    ),
                    required_inputs=[
                        f"DEV_STEER: {hc_msg[:60]}",
                        "Updated verified evidence cards",
                        "report_revision",
                    ],
                    discriminates_hypotheses=hyp_ids,
                    expected_outcomes=[
                        "If steered hypothesis is confirmed -> Approve Maker-Checker write-back",
                        "If code fix is ready -> Commit in Live Repo Studio and re-run verification",
                    ],
                    effort_level="low",
                    status="completed",
                )
            )

    # 0b. Live Developer Git Fix Verified check
    if is_live_fix_verified:
        live_code_card = next((c for c in verified_cards if c.pointer.get("is_live_diff")), None)
        commit_sha = str(live_code_card.pointer.get("commit_sha") or live_code_card.pointer.get("sha", ""))[:8] if live_code_card else "HEAD"
        commit_msg = str(live_code_card.pointer.get("commit_message") or live_code_card.pointer.get("commit_msg") or "live fix") if live_code_card else "live fix"
        candidates.append(
            NextCheck(
                check_id="CHK-LIVE-FIX-VERIFIED",
                title=f"Live Git Fix Verified (@{commit_sha}): Boundary Transfer Succeeded Against Policy",
                target_system="Live Git Workspace & Maker-Checker Gate",
                purpose=(
                    f"Developer commit @{commit_sha} ('{commit_msg}') resolved the defect in live code. "
                    f"Live transaction probe completed with status COMPLETED and 0 contradictions."
                ),
                required_inputs=[
                    f"git commit @{commit_sha}",
                    "Live probe status=COMPLETED",
                    "DOC-LIMITS-01 policy alignment",
                ],
                discriminates_hypotheses=hyp_ids,
                expected_outcomes=[
                    "Approve & Execute Write-Back to record verified fix and close incident",
                    "Trigger additional live transaction probes if testing edge amounts",
                ],
                effort_level="low",
                status="completed",
            )
        )

    # 1. Missing decisive input check (ABSTAIN / INSUFFICIENT_INFO)
    if trust.policy_action == PolicyAction.ABSTAIN or ticket.ticket_class == TicketClass.INSUFFICIENT_INFO if hasattr(ticket, "ticket_class") else trust.policy_action == PolicyAction.ABSTAIN:
        candidates.append(
            NextCheck(
                check_id="CHK-CLIENT-TXN-CORRELATION",
                title="Request Transaction ID & Exact Failure Timestamp (with Timezone)",
                target_system="Client Portal / Ledger Lookup",
                purpose="Resolve underspecified incident report by binding symptom to a concrete ledger record and log window.",
                required_inputs=["transfer_id (TXN-*)", "observed_timestamp_ist"],
                discriminates_hypotheses=["H_CUTOFF_WINDOW", "H_DAILY_LIMIT", "H_GATEWAY_TIMEOUT"],
                expected_outcomes=[
                    "If TXN-1009 @ 16:02 IST -> confirms UTC vs IST cutoff defect in app/transfers/cutoff.py",
                    "If TXN-6001 @ INR 1,00,000 -> confirms >= boundary check in app/limits/daily_limit.py",
                ],
                effort_level="low",
                status="blocked_missing_input" if not has_record else "recommended",
            )
        )

    # 2. Boundary vs Recent Commit Control Comparison (S06 / daily_limit.py)
    if "limit" in text or "100000" in text or "1,00,000" in text or any("daily_limit" in f for h in hypotheses for f in h.culprit_files):
        candidates.append(
            NextCheck(
                check_id="CHK-BOUNDARY-CONTROL-DIFF",
                title="Compare Failed Boundary Transfer (INR 1,00,000) Against Sub-Boundary Control (INR 99,999.99) on Same Release",
                target_system="Transfers Demo Fixture & Git Blame",
                purpose="Discriminate between >= boundary operator bug in app/limits/daily_limit.py and unrelated recent httpx dependency bump.",
                required_inputs=["TXN-6001 (amount=100000.00)", "control_txn (amount=99999.99)", "git blame app/limits/daily_limit.py"],
                discriminates_hypotheses=hyp_ids,
                expected_outcomes=[
                    "If INR 99,999.99 succeeds on latest SHA while INR 1,00,000.00 fails -> proves strict >= boundary defect and exonerates httpx bump",
                    "If both fail -> indicates broader service or dependency regression",
                ],
                effort_level="low",
                status="completed" if (is_live_fix_verified or bool(ticket.human_context)) else "recommended",
            )
        )

    # 3. Timezone Cutoff Window Control Check (S01 / cutoff.py)
    if "cutoff" in text or "utc" in text or "ist" in text or any("cutoff" in f for h in hypotheses for f in h.culprit_files):
        candidates.append(
            NextCheck(
                check_id="CHK-TIMEZONE-CUTOFF-PROBE",
                title="Verify Same-Day Cutoff Comparison at 10:32 UTC (16:02 IST) vsDOC-CUTOFF-01 Policy",
                target_system="Transfers Service & Timezone Fixture",
                purpose="Confirm whether is_before_cutoff() compares raw UTC hour or localized Asia/Kolkata (IST) hour.",
                required_inputs=["TXN-1009 timestamp (2026-10-07T10:32:00Z)", "app/transfers/cutoff.py:14-24"],
                discriminates_hypotheses=hyp_ids,
                expected_outcomes=[
                    "If cutoff check compares UTC hour against 16:00 IST policy -> confirms timezone conversion defect",
                    "If client submitted after 16:30 IST -> expected policy rejection",
                ],
                effort_level="low",
                status="recommended",
            )
        )

    # 4. Decimal vs IEEE-754 Float Rounding Check (S02 / calculator.py)
    if "fee" in text or "rounding" in text or "2041" in text or any("calculator" in f for h in hypotheses for f in h.culprit_files):
        candidates.append(
            NextCheck(
                check_id="CHK-DECIMAL-FEE-QUANTIZE",
                title="Compare IEEE-754 Float Fee Product Against Decimal('0.01') Quantization on TXN-2041",
                target_system="Fee Calculator & Ledger Snapshot",
                purpose="Verify whether 1-paisa overcharge stems from binary floating-point representation in app/fees/calculator.py.",
                required_inputs=["TXN-2041 principal=803.40", "fee_tier=1.25%", "app/fees/calculator.py"],
                discriminates_hypotheses=hyp_ids,
                expected_outcomes=[
                    "If float round(803.40 * 0.0125, 2) yields 10.05 vs Decimal 10.04 -> confirms float rounding defect",
                    "If tier rate changed in config -> indicates fee schedule mismatch",
                ],
                effort_level="low",
                status="recommended",
            )
        )

    # 5. Idempotency Key Replay Check (S03 / idempotency.py)
    if "idempotency" in text or "duplicate" in text or "3011" in text or any("idempotency" in f for h in hypotheses for f in h.culprit_files):
        candidates.append(
            NextCheck(
                check_id="CHK-IDEMPOTENCY-CACHE-LOOKUP",
                title="Verify Idempotency Key Deduplication Guard Before Ledger Debit on TXN-3011 / TXN-3012",
                target_system="Idempotency Middleware & Ledger",
                purpose="Determine if concurrent double-click submissions bypassed _seen_keys lookup in app/transfers/idempotency.py.",
                required_inputs=["TXN-3011", "TXN-3012", "idempotency_key header"],
                discriminates_hypotheses=hyp_ids,
                expected_outcomes=[
                    "If both transactions share idempotency_key with distinct debits -> confirms missing pre-debit cache guard",
                    "If keys differ -> client-side retry generated distinct requests",
                ],
                effort_level="low",
                status="recommended",
            )
        )

    # 6. Stale Runbook vs Code Behaviour Audit (S04 / sms.py)
    if "sms" in text or "retry" in text or any(c.kind in {ContradictionKind.BEHAVIOUR_MISMATCH, ContradictionKind.STALE_DOC_FLAG} for c in contradictions):
        candidates.append(
            NextCheck(
                check_id="CHK-DOC-CODE-DRIFT-AUDIT",
                title="Cross-Check Runbook Retry Policy Against Commit History in app/notifications/sms.py",
                target_system="Git Diff & Knowledge Base (DOC-SMS-01)",
                purpose="Distinguish intentional retry removal from accidental regression and flag stale runbook documentation.",
                required_inputs=["git diff app/notifications/sms.py", "DOC-SMS-01#retry_policy"],
                discriminates_hypotheses=hyp_ids,
                expected_outcomes=[
                    "If commit removed retry loop without updating DOC-SMS-01 -> restore retry backoff and update runbook",
                    "If SMS gateway rejected payload -> inspect provider webhook status",
                ],
                effort_level="low",
                status="recommended",
            )
        )

    # 7. Default fallback discriminator if none of the specific domain checks matched
    if not candidates:
        if not has_log or not has_record:
            candidates.append(
                NextCheck(
                    check_id="CHK-TELEMETRY-CORROBORATION",
                    title="Fetch Corroborating Runtime Log & Masked Ledger Record for Reported Entity",
                    target_system="LogPort & RecordPort",
                    purpose="Establish runtime corroboration before authorizing an engineering handoff.",
                    required_inputs=["transfer_id or batch_id", "incident timestamp window"],
                    discriminates_hypotheses=hyp_ids,
                    expected_outcomes=[
                        "If log + record confirm error signature -> upgrades evidence to CLAIM_SUPPORTED / CAUSE_REPRODUCED",
                        "If no error in logs -> check Known Error catalog (KE-104) or user onboarding guide (DOC-BEN-02)",
                    ],
                    effort_level="low",
                    status="recommended",
                )
            )
        else:
            candidates.append(
                NextCheck(
                    check_id="CHK-HANDOFF-VERIFICATION",
                    title="Review Verified Engineering Handoff & Approve Version-Bound Write-Back",
                    target_system="Maker-Checker Gate",
                    purpose="All required discriminating checks across logs, records, code, and docs are complete.",
                    required_inputs=["report_revision", "report_hash"],
                    discriminates_hypotheses=hyp_ids,
                    expected_outcomes=[
                        "Approve write-back to persist verified engineering issue and customer reply",
                        "Supply corrected evidence if any operational premise changes",
                    ],
                    effort_level="low",
                    status="recommended",
                )
            )

    primary = candidates[0] if candidates else None
    return primary, candidates[:3]
