from engine.persistence import InvestigationStore
from engine.schemas import ExecutionMetadata, ReportOutput, SSEEvent


def test_local_investigation_store_round_trips_events_and_reports():
    store = InvestigationStore()
    report = ReportOutput(
        investigation_id="INV-TEST",
        ticket_id="TKT-TEST",
        scenario_id="S01",
        ticket_class="CODE_DEFECT",
        severity="P3",
        owner_team="team-payments",
        summary="test",
        routing_plan={
            "ticket_class": "CODE_DEFECT",
            "severity": "P3",
            "active_agents": ["CodeAgent"],
        },
        trust={
            "score": 0.2,
            "band": "LOW",
            "policy_action": "ABSTAIN",
            "components": {},
            "rationale": "insufficient",
        },
        customer_reply_draft="Need more information.",
        leak_check={"passed": True, "notes": []},
        audit_ref="audit:INV-TEST",
        execution=ExecutionMetadata(),
    )
    event = SSEEvent(seq=1, ts="2026-01-01T00:00:00Z", type="masking_done", data={})

    store.save_report(report)
    store.save_event(report.investigation_id, event)

    assert store.get_report(report.investigation_id).ticket_id == "TKT-TEST"
    assert store.get_events(report.investigation_id)[0].seq == 1
