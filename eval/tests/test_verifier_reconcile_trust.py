"""
eval/tests/test_verifier_reconcile_trust.py
---------------------------------------------
Unit tests for Phase 4: Verifier, Reconciler, Trust Scorer,
HypothesisAgent, and ReportAgent.
"""

from __future__ import annotations

import asyncio
import os

os.environ.pop("GOOGLE_API_KEY", None)

import pytest

from engine.adapters.fixture_adapter import get_adapters
from engine.agents.hypothesis_agent import generate_hypotheses, _fallback_hypotheses
from engine.agents.report_agent import generate_report
from engine.reconcile import reconcile
from engine.schemas import (
    AgentRoutingPlan,
    Contradiction,
    ContradictionKind,
    DecisionBand,
    EvidenceCard,
    Hypothesis,
    PolicyAction,
    ReportOutput,
    Severity,
    SourceType,
    Stance,
    TicketClass,
    TicketDTO,
    TrustSummary,
    VerificationResult,
    VerificationStatus,
)
from engine.trust import compute_trust
from engine.verifier import verify_cards


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _make_ticket(text: str = "Transfer TXN-1009 rejected at 4 PM IST"):
    return TicketDTO(
        id="TKT-TEST", scenario_id="S99",
        created_at="2026-10-14T07:00:00Z", text=text, masked_text=text,
    )


def _make_plan():
    return AgentRoutingPlan(
        ticket_class=TicketClass.CODE_DEFECT, severity=Severity.P3,
        extracted_entities={}, active_agents=["LogsAgent", "CodeAgent"],
        skipped_agents={}, max_tool_calls=12,
    )


def _make_card(card_id, source_type, pointer, snippet, claim, **kw):
    return EvidenceCard(
        card_id=card_id, specialist="TestAgent",
        source_type=source_type, pointer=pointer,
        snippet=snippet, claim=claim,
        verification=VerificationResult(status=VerificationStatus.PENDING),
        **kw,
    )


# ---------------------------------------------------------------------------
# Verifier Tests
# ---------------------------------------------------------------------------

class TestVerifier:
    def setup_method(self):
        self.adapters = get_adapters()

    def test_valid_log_card_verified(self):
        """A log card with matching log_id should be verified."""
        card = _make_card(
            "LOG-T1", SourceType.LOG,
            {"log_id": "LOG-001", "ts": "2026-10-07T10:35:00Z", "service": "transfers"},
            "TransferCutoffError: same_day transfer rejected",
            "Error in transfers service",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(verified) == 1
        assert verified[0].verification.status == VerificationStatus.VERIFIED

    def test_invalid_log_id_dropped(self):
        """A log card with a non-existent log_id should be dropped."""
        card = _make_card(
            "LOG-T2", SourceType.LOG,
            {"log_id": "LOG-NONEXISTENT", "ts": "2026-10-07T10:35:00Z", "service": "x"},
            "Some fake log message",
            "Fabricated claim",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(dropped) == 1
        assert "not found" in dropped[0].verification.reason.lower()

    def test_missing_log_id_dropped(self):
        card = _make_card(
            "LOG-T3", SourceType.LOG,
            {"log_id": "", "ts": "", "service": ""},
            "test", "test",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(dropped) == 1

    def test_ticket_card_with_valid_id_verified(self):
        card = _make_card(
            "TKT-T1", SourceType.TICKET,
            {"system": "ServiceDesk", "id": "INC-8801", "field": "resolution"},
            "Bug in cutoff.py comparing UTC instead of IST",
            "Past ticket INC-8801",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(verified) == 1

    def test_ticket_card_without_id_dropped(self):
        card = _make_card(
            "TKT-T2", SourceType.TICKET,
            {"system": "ServiceDesk", "id": "?", "field": "x"},
            "test", "test",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(dropped) == 1

    def test_record_card_known_txn_verified(self):
        card = _make_card(
            "REC-T1", SourceType.RECORD,
            {"table": "transfers", "id": "TXN-1009", "field": "status"},
            "TXN-1009 status=REJECTED amount=50000",
            "Record lookup",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(verified) == 1

    def test_record_card_unknown_txn_dropped(self):
        card = _make_card(
            "REC-T2", SourceType.RECORD,
            {"table": "transfers", "id": "TXN-FAKE", "field": "status"},
            "TXN-FAKE status=COMPLETED",
            "Fabricated record",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(dropped) == 1

    def test_visual_card_without_corroboration_dropped(self):
        card = _make_card(
            "VIS-T1", SourceType.VISUAL,
            {"attachment_id": "screenshot.png"},
            "Error shown on screen",
            "Visual evidence",
        )
        verified, dropped = verify_cards([card], self.adapters, "S99")
        assert len(dropped) == 1
        assert "corroborating" in dropped[0].verification.reason.lower()

    def test_visual_card_with_corroboration_verified(self):
        """Visual card should be verified if a non-visual card is also verified."""
        log_card = _make_card(
            "LOG-V1", SourceType.LOG,
            {"log_id": "LOG-001", "ts": "2026-10-07T10:35:00Z", "service": "transfers"},
            "TransferCutoffError",
            "Log evidence",
        )
        visual_card = _make_card(
            "VIS-V1", SourceType.VISUAL,
            {"attachment_id": "screenshot.png"},
            "Error displayed",
            "Visual evidence",
        )
        verified, dropped = verify_cards([log_card, visual_card], self.adapters, "S99")
        vis_verified = [c for c in verified if c.source_type == SourceType.VISUAL]
        assert len(vis_verified) == 1

    def test_mixed_cards_partition_correctly(self):
        """Test mix of valid and invalid cards."""
        valid_log = _make_card(
            "LOG-M1", SourceType.LOG,
            {"log_id": "LOG-001", "ts": "2026-10-07T10:35:00Z", "service": "transfers"},
            "TransferCutoffError",
            "Valid log",
        )
        invalid_log = _make_card(
            "LOG-M2", SourceType.LOG,
            {"log_id": "FAKE", "ts": "", "service": ""},
            "Fake", "Fake",
        )
        valid_ticket = _make_card(
            "TKT-M1", SourceType.TICKET,
            {"system": "SD", "id": "INC-123", "field": "x"},
            "Some resolution text",
            "Past ticket",
        )
        verified, dropped = verify_cards(
            [valid_log, invalid_log, valid_ticket], self.adapters, "S99"
        )
        assert len(verified) == 2
        assert len(dropped) == 1


# ---------------------------------------------------------------------------
# Reconciler Tests
# ---------------------------------------------------------------------------

class TestReconciler:
    def test_state_mismatch_detected(self):
        """Client says 'successful' but record says 'REJECTED'."""
        ticket = _make_ticket("My transfer was successful but I see no credit")
        record_card = _make_card(
            "REC-R1", SourceType.RECORD,
            {"table": "transfers", "id": "TXN-1009", "field": "status"},
            "TXN-1009 status=REJECTED",
            "Record shows REJECTED",
        )
        record_card.verification = VerificationResult(status=VerificationStatus.VERIFIED)
        contras = reconcile(ticket, [record_card])
        state_contras = [c for c in contras if c.kind == ContradictionKind.STATE_MISMATCH]
        assert len(state_contras) > 0

    def test_no_state_mismatch_when_consistent(self):
        """Client says 'failed' and record says 'REJECTED' — no mismatch."""
        ticket = _make_ticket("My transfer failed with an error")
        record_card = _make_card(
            "REC-R2", SourceType.RECORD,
            {"table": "transfers", "id": "TXN-1009", "field": "status"},
            "TXN-1009 status=REJECTED",
            "Record shows REJECTED",
        )
        record_card.verification = VerificationResult(status=VerificationStatus.VERIFIED)
        contras = reconcile(ticket, [record_card])
        state_contras = [c for c in contras if c.kind == ContradictionKind.STATE_MISMATCH]
        assert len(state_contras) == 0

    def test_stale_doc_flagged(self):
        """Doc updated Sep, code committed Oct — doc is stale."""
        doc_card = _make_card(
            "DOC-R1", SourceType.DOC,
            {"page_id": "DOC-SMS-01", "section": "retry", "last_updated": "2026-09-01T00:00:00Z"},
            "SMS retries 3 times", "Doc says retries",
        )
        doc_card.verification = VerificationResult(status=VerificationStatus.VERIFIED)
        code_card = _make_card(
            "CODE-R1", SourceType.CODE,
            {"repo": "cr", "path": "app/notifications/sms.py", "line_start": 10, "line_end": 20, "sha": "abc"},
            "send_sms()", "Code sends SMS once",
            observed_at="2026-10-10T08:00:00Z",
        )
        code_card.verification = VerificationResult(status=VerificationStatus.VERIFIED)
        contras = reconcile(_make_ticket(), [doc_card, code_card])
        stale = [c for c in contras if c.kind == ContradictionKind.STALE_DOC_FLAG]
        assert len(stale) > 0

    def test_empty_cards_no_contradictions(self):
        contras = reconcile(_make_ticket(), [])
        assert contras == []


# ---------------------------------------------------------------------------
# Trust Scorer Tests
# ---------------------------------------------------------------------------

class TestTrustScorer:
    def test_high_trust_with_many_verified_cards(self):
        cards = [
            _make_card(f"C{i}", st,
                       {"log_id": f"L{i}", "ts": f"2026-10-07T10:3{i}:00Z", "service": "x",
                        "path": "a.py", "line_start": i, "line_end": i, "sha": "abc",
                        "page_id": "D1", "section": "s", "id": f"TXN-{i}"},
                       f"snippet {i}", f"claim {i}", observed_at=f"2026-10-07T10:3{i}:00Z")
            for i, st in enumerate([
                SourceType.LOG, SourceType.CODE, SourceType.DOC,
                SourceType.TICKET, SourceType.RECORD,
            ])
        ]
        trust = compute_trust(cards, [], [])
        assert trust.score >= 0.60
        assert trust.band in (DecisionBand.HIGH, DecisionBand.MEDIUM)
        assert trust.policy_action in (PolicyAction.CONCLUDE, PolicyAction.CONCLUDE_WITH_CAVEAT)

    def test_low_trust_with_all_dropped(self):
        trust = compute_trust([], [_make_card("D1", SourceType.LOG, {}, "x", "x")], [])
        assert trust.score < 0.45
        assert trust.band == DecisionBand.LOW
        assert trust.policy_action == PolicyAction.ABSTAIN

    def test_contradiction_penalty_lowers_score(self):
        cards = [_make_card("C1", SourceType.LOG,
                            {"log_id": "L1", "ts": "2026-10-07T10:30:00Z", "service": "x"},
                            "snippet", "claim", observed_at="2026-10-07T10:30:00Z")]
        contra = [Contradiction(
            kind=ContradictionKind.TIME_MISMATCH, deterministic=True,
            note="30 min gap",
        )]
        score_clean = compute_trust(cards, [], []).score
        score_contra = compute_trust(cards, [], contra).score
        assert score_contra < score_clean

    def test_hypothesis_gap_triggers_abstain(self):
        cards = [_make_card("C1", SourceType.LOG,
                            {"log_id": "L1", "ts": "t", "service": "x"},
                            "s", "c", observed_at="t")]
        h1 = Hypothesis(hypothesis_id="H1", statement="a", score=0.55)
        h2 = Hypothesis(hypothesis_id="H2", statement="b", score=0.52)
        trust = compute_trust(cards, [], [], hypotheses=[h1, h2])
        # Gap is 0.03 < 0.10 — should abstain
        assert trust.policy_action == PolicyAction.ABSTAIN

    def test_components_are_populated(self):
        cards = [_make_card("C1", SourceType.LOG,
                            {"log_id": "L1", "ts": "t", "service": "x"},
                            "s", "c")]
        trust = compute_trust(cards, [], [])
        assert trust.components.c_ver > 0
        assert isinstance(trust.rationale, str)
        assert len(trust.rationale) > 0

    def test_score_clamped_between_0_and_1(self):
        # Edge case: many contradictions should not produce negative score
        contras = [
            Contradiction(kind=ContradictionKind.TIME_MISMATCH, deterministic=True, note="x")
            for _ in range(10)
        ]
        trust = compute_trust([], [], contras)
        assert 0.0 <= trust.score <= 1.0


# ---------------------------------------------------------------------------
# Hypothesis Agent Tests (fallback mode)
# ---------------------------------------------------------------------------

class TestHypothesisAgent:
    def test_fallback_returns_hypotheses_from_code_cards(self):
        code_card = _make_card(
            "CODE-H1", SourceType.CODE,
            {"repo": "cr", "path": "app/transfers/cutoff.py", "line_start": 18, "line_end": 20, "sha": "abc123"},
            "if datetime.utcnow().hour >= 16:",
            "UTC comparison instead of IST",
        )
        log_card = _make_card(
            "LOG-H1", SourceType.LOG,
            {"log_id": "L1", "ts": "2026-10-07T10:35:00Z", "service": "transfers"},
            "TransferCutoffError",
            "Transfer rejected at cutoff",
        )
        hypotheses, contras = _fallback_hypotheses([code_card, log_card], [])
        assert len(hypotheses) >= 1
        assert hypotheses[0].hypothesis_id == "H1"
        assert any("cutoff.py" in f for f in hypotheses[0].culprit_files)

    def test_fallback_detects_known_error(self):
        ke_card = _make_card(
            "TKT-KE", SourceType.TICKET,
            {"system": "KB", "id": "KE-104", "field": "workaround"},
            "Bank holiday delay workaround",
            "Known Error KE-104: bank holiday settlement delay",
        )
        hypotheses, _ = _fallback_hypotheses([ke_card], [])
        ke_hyp = [h for h in hypotheses if "known error" in h.statement.lower()]
        assert len(ke_hyp) > 0

    def test_capped_at_4_hypotheses(self):
        cards = [
            _make_card(f"CODE-{i}", SourceType.CODE,
                       {"repo": "cr", "path": f"app/mod{i}.py", "line_start": 1, "line_end": 1, "sha": "x"},
                       f"code {i}", f"claim {i}")
            for i in range(10)
        ]
        hypotheses, _ = _fallback_hypotheses(cards, [])
        assert len(hypotheses) <= 4

    def test_async_generate_hypotheses(self):
        code_card = _make_card(
            "CODE-A1", SourceType.CODE,
            {"repo": "cr", "path": "app/transfers/cutoff.py", "line_start": 18, "line_end": 20, "sha": "abc"},
            "UTC comparison", "UTC vs IST bug",
        )
        hypotheses, contras = run_async(generate_hypotheses([code_card], []))
        assert isinstance(hypotheses, list)
        assert isinstance(contras, list)


# ---------------------------------------------------------------------------
# Report Agent Tests
# ---------------------------------------------------------------------------

class TestReportAgent:
    def test_generates_complete_report(self):
        ticket = _make_ticket()
        plan = _make_plan()
        verified = [_make_card(
            "LOG-R1", SourceType.LOG,
            {"log_id": "L1", "ts": "2026-10-07T10:35:00Z", "service": "transfers"},
            "TransferCutoffError", "Error in transfers",
        )]
        trust = compute_trust(verified, [], [])
        hypotheses = [Hypothesis(
            hypothesis_id="H1",
            statement="UTC vs IST cutoff bug",
            culprit_files=["app/transfers/cutoff.py"],
            score=0.75,
        )]
        report = run_async(generate_report(
            ticket, plan, verified, [], [], hypotheses, trust, "inv-test-001"
        ))
        assert isinstance(report, ReportOutput)
        assert report.investigation_id == "inv-test-001"
        assert report.ticket_id == "TKT-TEST"
        assert report.verified_claims_count == 1
        assert len(report.customer_reply_draft) > 0
        assert report.leak_check is not None

    def test_customer_reply_no_internal_paths(self):
        """Customer reply must not contain .py file paths."""
        ticket = _make_ticket()
        plan = _make_plan()
        trust = TrustSummary(
            score=0.75, band=DecisionBand.HIGH,
            policy_action=PolicyAction.CONCLUDE,
            components=__import__("engine.schemas", fromlist=["TrustComponents"]).TrustComponents(),
            rationale="test",
        )
        hypotheses = [Hypothesis(
            hypothesis_id="H1",
            statement="Bug in app/transfers/cutoff.py comparing UTC",
            culprit_files=["app/transfers/cutoff.py"],
            score=0.75,
        )]
        report = run_async(generate_report(
            ticket, plan, [], [], [], hypotheses, trust, "inv-test-002"
        ))
        assert ".py" not in report.customer_reply_draft
        assert "app/" not in report.customer_reply_draft

    def test_abstain_report_asks_questions(self):
        ticket = _make_ticket("Transfers not working urgently")
        plan = _make_plan()
        trust = TrustSummary(
            score=0.22, band=DecisionBand.LOW,
            policy_action=PolicyAction.ABSTAIN,
            components=__import__("engine.schemas", fromlist=["TrustComponents"]).TrustComponents(),
            rationale="Insufficient evidence",
        )
        report = run_async(generate_report(
            ticket, plan, [], [], [], [], trust, "inv-test-003"
        ))
        assert len(report.questions_for_client) > 0
        assert len(report.questions_for_client) <= 2

    def test_jira_draft_generated_with_hypothesis(self):
        ticket = _make_ticket()
        plan = _make_plan()
        trust = compute_trust([], [], [])
        hypotheses = [Hypothesis(
            hypothesis_id="H1", statement="Cutoff bug",
            culprit_files=["app/transfers/cutoff.py"], score=0.70,
        )]
        report = run_async(generate_report(
            ticket, plan, [], [], [], hypotheses, trust, "inv-test-004"
        ))
        assert report.jira_draft is not None
        assert "TriagePilot" in report.jira_draft.title
        assert len(report.jira_draft.labels) > 0

    def test_kb_gap_detected_on_stale_doc(self):
        ticket = _make_ticket()
        plan = _make_plan()
        doc_card = _make_card(
            "DOC-KB1", SourceType.DOC,
            {"page_id": "DOC-SMS-01", "section": "retry", "last_updated": "2026-09-01T00:00:00Z"},
            "retries 3 times", "Doc says retries",
        )
        doc_card.verification = VerificationResult(status=VerificationStatus.VERIFIED)
        contra = Contradiction(
            kind=ContradictionKind.STALE_DOC_FLAG, deterministic=True,
            card_a="DOC-KB1", card_b="CODE-X",
            note="DOC-SMS-01 last updated 2026-09-01 but code changed 2026-10-10",
        )
        trust = compute_trust([doc_card], [], [contra])
        report = run_async(generate_report(
            ticket, plan, [doc_card], [], [contra], [], trust, "inv-test-005"
        ))
        assert report.kb_gap is not None
        assert report.kb_gap.page_id == "DOC-SMS-01"
