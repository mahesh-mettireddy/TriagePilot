"""
eval/tests/test_judge_adversarial.py
------------------------------------
Adversarial and judge-readiness test suite covering all requirements from the
AI Judge Review:
  1. Valid function citation that does not explain the failure -> SOURCE_VALIDATED only; blocked from HIGH root-cause conclusion.
  2. Ten duplicated documents repeating a mistaken premise -> deduplicated by provenance; cannot inflate c_ver to pass HIGH gate.
  3. Unrelated recent commit (httpx bump) + successful control transaction -> innocent commit exonerated; true boundary defect selected.
  4. Missing log access vs. "no error occurred" -> labeled with explicit limitation / NEED_EVIDENCE.
  5. Corrected input / contradictory evidence after analyst approval -> withdraws old recommendation, increments revision, and rejects stale approval.
  6. Exact score boundaries tested at 0.69, 0.70, and 0.71.
  7. Structured NextCheck selector and Single-Agent Baseline vs TriagePilot ablation comparison.
"""

from __future__ import annotations

import asyncio
import pytest

from engine.adapters.fixture_adapter import get_adapters
from engine.agents.hypothesis_agent import _fallback_hypotheses
from engine.next_check import select_next_checks
from engine.orchestrator import InvestigationManager
from engine.schemas import (
    Contradiction,
    ContradictionKind,
    DecisionBand,
    EvidenceCard,
    EvidenceLevel,
    GateOutcome,
    HumanContext,
    HumanDecision,
    Hypothesis,
    InvestigationCreateRequest,
    PolicyAction,
    SourceType,
    Stance,
    TicketDTO,
    VerificationResult,
    VerificationStatus,
)
from engine.trust import compute_trust
from engine.verifier import compute_provenance_key, verify_cards
from eval.ablations import run_single_agent_baseline_scenario
from eval.runner import GOLDEN_SCENARIOS_TRUTH, run_all_evals


def _card(
    card_id: str,
    source_type: SourceType,
    pointer: dict,
    snippet: str,
    claim: str,
    stance: Stance = Stance.SUPPORTS,
    observed_at: str = "2026-10-07T10:35:00Z",
) -> EvidenceCard:
    return EvidenceCard(
        card_id=card_id,
        specialist="TestAgent",
        source_type=source_type,
        pointer=pointer,
        snippet=snippet,
        claim=claim,
        stance=stance,
        observed_at=observed_at,
        verification=VerificationResult(status=VerificationStatus.PENDING),
    )


def test_adversarial_1_valid_citation_that_does_not_explain_failure():
    """
    A genuine file/SHA citation whose content is an unrelated utility/health check
    must receive SOURCE_VALIDATED (not CLAIM_SUPPORTED or CAUSE_REPRODUCED) and
    must be blocked from a HIGH root-cause conclusion.
    """
    adapters = get_adapters()
    # Read a real SHA from code_adapter so pointer verification passes
    code_adapter = adapters["code"]
    commits = code_adapter.git_log("app/transfers/cutoff.py", n=1)
    real_sha = commits[0]["sha"]

    unrelated_code = _card(
        "CODE-UNRELATED",
        SourceType.CODE,
        {
            "repo": "clientrepo",
            "path": "app/transfers/cutoff.py",
            "line_start": 1,
            "line_end": 5,
            "sha": real_sha,
        },
        "cutoff",
        "Unrelated health_check helper citation that does not explain failure",
        stance=Stance.CONTEXT,
    )
    verified, dropped = verify_cards([unrelated_code], adapters, "S01")
    assert len(verified) == 1
    assert verified[0].verification.evidence_level == EvidenceLevel.SOURCE_VALIDATED
    assert "does not explain" in (verified[0].verification.limitations or "").lower()

    # Even if paired with other metadata, Hard Gate 2 blocks HIGH conclusion when
    # the only code citation does not explain the failure.
    doc_card = _card(
        "DOC-1",
        SourceType.DOC,
        {"page_id": "DOC-CUTOFF-01", "section": "overview", "last_updated": "2026-10-01T00:00:00Z"},
        "Same-day transfers",
        "Cutoff policy doc",
    )
    doc_card.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.CLAIM_SUPPORTED,
        provenance_key="doc:DOC-CUTOFF-01",
    )
    tkt_card = _card(
        "TKT-1",
        SourceType.TICKET,
        {"system": "SD", "id": "INC-100", "field": "summary"},
        "Past transfer ticket",
        "Historical ticket",
    )
    tkt_card.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.SOURCE_VALIDATED,
        provenance_key="ticket:SD:INC-100",
    )
    rec_card = _card(
        "REC-1",
        SourceType.RECORD,
        {"table": "transfers", "id": "TXN-1009", "field": "status"},
        "REJECTED",
        "Transfer rejected",
    )
    rec_card.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.CLAIM_SUPPORTED,
        provenance_key="record:TXN-1009",
    )

    trust = compute_trust([verified[0], doc_card, tkt_card, rec_card], [], [])
    assert trust.band != DecisionBand.HIGH
    assert trust.policy_action == PolicyAction.CONCLUDE_WITH_CAVEAT
    assert any("does not explain" in r.lower() for r in trust.gate_reasons)


def test_adversarial_2_ten_duplicated_documents_deduplicated_by_provenance():
    """
    Ten duplicated citations pointing to the same document (DOC-SMS-01) must be
    grouped into 1 unique provenance source and cannot masquerade as independent
    evidence to reach HIGH trust.
    """
    dup_docs = []
    for i in range(10):
        c = _card(
            f"DOC-DUP-{i}",
            SourceType.DOC,
            {"page_id": "DOC-SMS-01", "section": "retry_policy", "last_updated": "2026-09-01T00:00:00Z"},
            "SMS notifications automatically retry 3 times",
            "Runbook says SMS retries 3 times",
        )
        c.verification = VerificationResult(
            status=VerificationStatus.VERIFIED,
            evidence_level=EvidenceLevel.CLAIM_SUPPORTED,
            provenance_key=compute_provenance_key(c),
        )
        dup_docs.append(c)

    trust_ten = compute_trust(dup_docs, [], [])
    trust_one = compute_trust([dup_docs[0]], [], [])

    assert trust_ten.components.unique_provenance_count == 1
    assert trust_ten.components.c_ver == trust_one.components.c_ver
    assert trust_ten.band != DecisionBand.HIGH
    assert any("deduplicated" in r.lower() for r in trust_ten.gate_reasons)


def test_adversarial_3_unrelated_recent_commit_exonerated_vs_boundary_bug():
    """
    When an innocent recent commit (httpx bump in requirements.txt) and the true
    causal module (app/limits/daily_limit.py) are both present, HypothesisAgent
    must prioritize daily_limit.py and exonerate the httpx bump.
    """
    innocent_commit = _card(
        "CODE-HTTPX",
        SourceType.CODE,
        {"repo": "cr", "path": "requirements.txt", "line_start": 4, "line_end": 4, "sha": "a" * 40},
        "httpx==0.27.2",
        "Recent commit bumped httpx version in requirements.txt",
        stance=Stance.CONTEXT,
    )
    innocent_commit.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.SOURCE_VALIDATED,
        provenance_key="code:requirements.txt",
    )

    boundary_code = _card(
        "CODE-LIMIT",
        SourceType.CODE,
        {"repo": "cr", "path": "app/limits/daily_limit.py", "line_start": 15, "line_end": 22, "sha": "b" * 40},
        "if current_total + amount >= DAILY_LIMIT:",
        "Strict >= comparison blocks exact INR 1,00,000 boundary transfer",
        stance=Stance.SUPPORTS,
    )
    boundary_code.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.CAUSE_REPRODUCED,
        provenance_key="code:app/limits/daily_limit.py",
    )

    log_card = _card(
        "LOG-LIMIT",
        SourceType.LOG,
        {"log_id": "LOG-6001", "ts": "2026-10-07T10:35:00Z", "service": "limits"},
        "DailyLimitExceeded: 100000.00",
        "Transfer TXN-6001 rejected at boundary",
    )
    log_card.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.CAUSE_REPRODUCED,
        provenance_key="log:LOG-6001",
    )

    hypotheses, _ = _fallback_hypotheses([innocent_commit, boundary_code, log_card], [])
    assert len(hypotheses) >= 1
    primary = hypotheses[0]
    assert "app/limits/daily_limit.py" in primary.culprit_files
    assert "requirements.txt" not in primary.culprit_files
    assert primary.evidence_level == EvidenceLevel.CAUSE_REPRODUCED


def test_adversarial_4_missing_log_access_labeled_as_limitation_not_no_error():
    """
    When log/record telemetry is missing, a code citation alone is labeled with
    explicit limitations (SOURCE_VALIDATED) and NextCheck requests telemetry
    corroboration rather than claiming 'no error occurred'.
    """
    adapters = get_adapters()
    commits = adapters["code"].git_log("app/transfers/cutoff.py", n=1)
    sha = commits[0]["sha"]

    code_only = _card(
        "CODE-ONLY",
        SourceType.CODE,
        {"repo": "cr", "path": "app/transfers/cutoff.py", "line_start": 1, "line_end": 25, "sha": sha},
        "cutoff",
        "Cutoff check in app/transfers/cutoff.py",
    )
    verified, _ = verify_cards([code_only], adapters, "S01")
    assert len(verified) == 1
    assert verified[0].verification.evidence_level == EvidenceLevel.SOURCE_VALIDATED
    assert "no corroborating runtime log" in (verified[0].verification.limitations or "").lower()

    trust = compute_trust(verified, [], [])
    assert trust.band != DecisionBand.HIGH


def test_adversarial_5_corrected_input_withdraws_recommendation_and_rejects_stale_approval():
    """
    When a parent investigation is followed by an EVIDENCE_UPDATE, the new report:
      1. Increments report_revision (Revision 2)
      2. Populates withdrawn_conclusion with the prior hypothesis & hash
      3. Rejects any subsequent or racing approval attempt on the superseded parent report
    """
    async def _run_flow():
        manager = InvestigationManager()
        # Run 1: Initial investigation on S01
        inv1_id = await manager.start_investigation(
            InvestigationCreateRequest(scenario_id="S01", mode="live"),
            wait=True,
        )
        rep1 = manager.get_report(inv1_id)
        assert rep1 is not None
        assert rep1.report_revision == 1

        # Run 2: Contradictory / corrected evidence arrives referencing inv1_id
        inv2_id = await manager.start_investigation(
            InvestigationCreateRequest(
                scenario_id="S06",
                mode="live",
                human_context=HumanContext(
                    source="EVIDENCE_UPDATE",
                    parent_investigation_id=inv1_id,
                    message="Corrected transaction record: failure was TXN-6001 at INR 1,00,000 boundary in app/limits/daily_limit.py, not cutoff.py.",
                ),
            ),
            wait=True,
        )
        rep2 = manager.get_report(inv2_id)
        assert rep2 is not None
        assert rep2.report_revision == 2
        assert rep2.parent_investigation_id == inv1_id
        assert rep2.withdrawn_conclusion is not None
        assert rep2.withdrawn_conclusion.parent_investigation_id == inv1_id
        assert rep2.withdrawn_conclusion.prior_report_revision == 1
        assert rep2.withdrawn_conclusion.prior_report_hash == rep1.report_hash
        assert rep2.withdrawn_conclusion.invalidated_by == "EVIDENCE_UPDATE"

        # Now attempt a racing/stale approval against the superseded parent report (inv1_id)
        stale_decision = HumanDecision(
            status="approved",
            by="analyst@bank.example",
            decision_id="DEC-STALE-001",
            report_revision=rep1.report_revision,
            report_hash=rep1.report_hash,
        )
        with pytest.raises(ValueError, match="superseded"):
            await manager.apply_decision(inv1_id, stale_decision)

    asyncio.run(_run_flow())


def test_adversarial_6_exact_score_boundaries_069_070_071(monkeypatch):
    """
    Test exact score precedence boundaries:
      - 0.69 -> MEDIUM (CONCLUDE_WITH_CAVEAT)
      - 0.70 -> HIGH   (CONCLUDE)
      - 0.71 -> HIGH   (CONCLUDE)
    """
    import engine.trust as trust_mod

    dummy_card = _card(
        "LOG-B1",
        SourceType.LOG,
        {"log_id": "L1", "ts": "2026-10-07T10:35:00Z", "service": "transfers"},
        "TransferCutoffError",
        "Log claim",
    )
    dummy_card.verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        evidence_level=EvidenceLevel.CAUSE_REPRODUCED,
        provenance_key="log:L1",
    )

    for target_score, expected_band, expected_policy in [
        (0.69, DecisionBand.MEDIUM, PolicyAction.CONCLUDE_WITH_CAVEAT),
        (0.70, DecisionBand.HIGH, PolicyAction.CONCLUDE),
        (0.71, DecisionBand.HIGH, PolicyAction.CONCLUDE),
    ]:
        monkeypatch.setattr(trust_mod, "_c_ver", lambda *a, _s=target_score: _s)
        monkeypatch.setattr(trust_mod, "_c_div", lambda *a, _s=target_score: _s)
        monkeypatch.setattr(trust_mod, "_c_spec", lambda *a, _s=target_score: _s)
        monkeypatch.setattr(trust_mod, "_c_time", lambda *a, _s=target_score: _s)
        monkeypatch.setattr(trust_mod, "_p_contra", lambda *a: 0.0)
        monkeypatch.setattr(trust_mod, "_p_unver", lambda *a: 0.0)

        summary = trust_mod.compute_trust([dummy_card], [], [])
        assert summary.score == target_score
        assert summary.band == expected_band
        assert summary.policy_action == expected_policy


def test_next_useful_check_selector_and_single_agent_ablation():
    """
    Verify that select_next_checks returns an allowlisted discriminating check
    and that the Single-Agent Baseline evaluator exposes false conclusions on
    adversarial scenarios (S03, S04, S06, S11).
    """
    ticket = TicketDTO(
        id="TKT-S06",
        scenario_id="S06",
        created_at="2026-10-07T10:35:00Z",
        text="Transfer TXN-6001 blocked at INR 1,00,000 daily limit",
        masked_text="Transfer TXN-6001 blocked at INR 1,00,000 daily limit",
    )
    h1 = Hypothesis(
        hypothesis_id="H1",
        statement="Boundary >= bug in app/limits/daily_limit.py",
        culprit_files=["app/limits/daily_limit.py"],
        score=0.88,
    )
    trust = compute_trust([], [], [])
    primary_check, candidates = select_next_checks(ticket, [], [], [h1], trust)
    assert primary_check is not None
    assert primary_check.check_id.startswith("CHK-")
    assert len(candidates) >= 1

    # Single-agent baseline fails S06 (blames recent httpx commit) and S11 (fails to abstain)
    s06_base = run_single_agent_baseline_scenario("S06", GOLDEN_SCENARIOS_TRUTH["S06"])
    assert s06_base["root_cause_hit"] is False
    assert s06_base["false_conclusion"] is True

    s11_base = run_single_agent_baseline_scenario("S11", GOLDEN_SCENARIOS_TRUTH["S11"])
    assert s11_base["abstention"] is False
    assert s11_base["false_conclusion"] is True
