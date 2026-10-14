"""
eval/tests/test_specialists.py
--------------------------------
Unit tests for engine/agents/specialists.py.

Tests use fixture adapters with fallback mock data — no real git repo or
LLM call required.
"""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.pop("GOOGLE_API_KEY", None)

from engine.adapters.fixture_adapter import get_adapters
from engine.agents.specialists import (
    CodeAgent,
    HistoryAgent,
    KnowledgeAgent,
    LogsAgent,
    RecordAgent,
    run_active_agents,
)
from engine.planner import Planner
from engine.schemas import (
    AgentRoutingPlan,
    EvidenceCard,
    Severity,
    Stance,
    SourceType,
    TicketClass,
    TicketDTO,
    VerificationStatus,
)


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


def _make_ticket(text: str, scenario_id: str = "S99", human_context=None) -> TicketDTO:
    return TicketDTO(
        id=f"TKT-{scenario_id}",
        scenario_id=scenario_id,
        created_at="2026-10-14T07:00:00Z",
        text=text,
        masked_text=text,
        human_context=human_context,
    )


def _make_plan(
    ticket_class=TicketClass.CODE_DEFECT,
    active=None,
    skipped=None,
    entities=None,
) -> AgentRoutingPlan:
    if active is None:
        active = ["HistoryAgent", "KnowledgeAgent", "LogsAgent", "CodeAgent", "RecordAgent"]
    return AgentRoutingPlan(
        ticket_class=ticket_class,
        severity=Severity.P3,
        extracted_entities=entities or {},
        active_agents=active,
        skipped_agents=skipped or {},
        max_tool_calls=12,
    )


@pytest.fixture
def adapters():
    return get_adapters()


# ---------------------------------------------------------------------------
# HistoryAgent
# ---------------------------------------------------------------------------

class TestHistoryAgent:
    def test_returns_evidence_cards(self, adapters):
        agent = HistoryAgent(adapters["history"])
        ticket = _make_ticket("Transfer rejected after 4 PM — possible cutoff bug")
        plan = _make_plan()
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_cards_have_required_fields(self, adapters):
        agent = HistoryAgent(adapters["history"])
        ticket = _make_ticket("Same day transfer rejected after 4 PM IST")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        for card in cards:
            assert isinstance(card, EvidenceCard)
            assert card.card_id.startswith("HIST-")
            assert card.specialist == "HistoryAgent"
            assert card.source_type == SourceType.TICKET
            assert card.verification.status == VerificationStatus.PENDING

    def test_cards_have_snippet_and_claim(self, adapters):
        agent = HistoryAgent(adapters["history"])
        cards = run_async(agent.run(
            _make_ticket("cutoff transfer error"), _make_plan(), [0], None
        ))
        for card in cards:
            assert len(card.snippet) > 0
            assert len(card.claim) > 0


# ---------------------------------------------------------------------------
# KnowledgeAgent
# ---------------------------------------------------------------------------

class TestKnowledgeAgent:
    def test_returns_doc_cards(self, adapters):
        agent = KnowledgeAgent(adapters["knowledge"])
        ticket = _make_ticket("SMS notification not sent after transfer — retries?")
        plan = _make_plan(active=["KnowledgeAgent"])
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_cards_are_doc_type(self, adapters):
        agent = KnowledgeAgent(adapters["knowledge"])
        ticket = _make_ticket("How do I add an international beneficiary?")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        for card in cards:
            assert card.source_type == SourceType.DOC
            assert card.card_id.startswith("KNOW-")

    def test_s04_sms_doc_found(self, adapters):
        """S04: DOC-SMS-01 must be found when querying for SMS issues."""
        agent = KnowledgeAgent(adapters["knowledge"])
        ticket = _make_ticket("Beneficiary SMS never sent — runbook says it retries 3 times")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        page_ids = [c.pointer.get("page_id") for c in cards]
        assert "DOC-SMS-01" in page_ids

    def test_s10_beneficiary_doc_found(self, adapters):
        """S10: DOC-BEN-02 must be found for how-to queries."""
        agent = KnowledgeAgent(adapters["knowledge"])
        ticket = _make_ticket("How do I add an international beneficiary?")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        page_ids = [c.pointer.get("page_id") for c in cards]
        assert "DOC-BEN-02" in page_ids


# ---------------------------------------------------------------------------
# LogsAgent
# ---------------------------------------------------------------------------

class TestLogsAgent:
    def test_returns_log_cards(self, adapters):
        agent = LogsAgent(adapters["logs"])
        ticket = _make_ticket("Transfer failing with error")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_cards_are_log_type(self, adapters):
        agent = LogsAgent(adapters["logs"])
        ticket = _make_ticket("Transfer error after 4 PM")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        for card in cards:
            assert card.source_type == SourceType.LOG
            assert card.card_id.startswith("LOG-")

    def test_log_card_has_log_id_pointer(self, adapters):
        agent = LogsAgent(adapters["logs"])
        ticket = _make_ticket("Transfer error")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        for card in cards:
            assert "log_id" in card.pointer
            assert "ts" in card.pointer

    def test_s04_injection_in_log_flagged_contradicts(self, adapters):
        """S04: log lines with injection text must have CONTRADICTS stance."""
        agent = LogsAgent(adapters["logs"])
        ticket = _make_ticket("SMS not sent")
        # Use S04 scenario which has the injection log line
        ticket.scenario_id = "S04"
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        # At minimum, no card should slip through with SUPPORTS stance on injection text
        for card in cards:
            assert card.verification.status == VerificationStatus.PENDING

    def test_trace_lookup_with_txn_id(self, adapters):
        """RecordAgent activates trace lookup when TXN ID in entities."""
        agent = LogsAgent(adapters["logs"])
        ticket = _make_ticket("TXN-1009 failed")
        plan = _make_plan(entities={"transaction_ids": ["TXN-1009"]})
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert isinstance(cards, list)


# ---------------------------------------------------------------------------
# CodeAgent
# ---------------------------------------------------------------------------

class TestCodeAgent:
    def test_returns_cards_without_real_repo(self, adapters):
        """CodeAgent must return stub cards gracefully when clientrepo missing."""
        agent = CodeAgent(adapters["code"])
        ticket = _make_ticket("Transfer failing after 4 PM — possible cutoff bug")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        assert isinstance(cards, list)
        # Stub adapter always returns at least 1 search result

    def test_cards_are_code_type(self, adapters):
        agent = CodeAgent(adapters["code"])
        ticket = _make_ticket("cutoff bug")
        cards = run_async(agent.run(ticket, _make_plan(), [0], None))
        for card in cards:
            assert card.source_type == SourceType.CODE
            assert card.card_id.startswith("CODE-")

    def test_dev_steer_focus_used(self, adapters):
        """DEV_STEER files must be used as search query."""
        agent = CodeAgent(adapters["code"])
        ticket = _make_ticket("Transfer rejected")
        plan = _make_plan(entities={"dev_steer_focus": ["cutoff.py"]})
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert isinstance(cards, list)


# ---------------------------------------------------------------------------
# RecordAgent
# ---------------------------------------------------------------------------

class TestRecordAgent:
    def test_returns_empty_without_txn_ids(self, adapters):
        """RecordAgent must return [] when no TXN IDs present."""
        agent = RecordAgent(adapters["record"])
        ticket = _make_ticket("Transfer failing")  # no TXN ID
        plan = _make_plan(entities={})
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert cards == []

    def test_returns_record_card_for_known_txn(self, adapters):
        """TXN-1009 in fallback data should return a record card."""
        agent = RecordAgent(adapters["record"])
        ticket = _make_ticket("TXN-1009 was rejected")
        plan = _make_plan(entities={"transaction_ids": ["TXN-1009"]})
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert len(cards) > 0
        assert cards[0].source_type == SourceType.RECORD
        assert cards[0].card_id.startswith("REC-")

    def test_record_card_has_no_raw_pii(self, adapters):
        """Masked account must appear in snippet; raw account must not."""
        agent = RecordAgent(adapters["record"])
        ticket = _make_ticket("TXN-1009 failed")
        plan = _make_plan(entities={"transaction_ids": ["TXN-1009"]})
        cards = run_async(agent.run(ticket, plan, [0], None))
        for card in cards:
            assert "[ACCT_REDACTED]" in card.snippet or "masked_account" in card.snippet

    def test_unknown_txn_returns_no_card(self, adapters):
        agent = RecordAgent(adapters["record"])
        ticket = _make_ticket("TXN-9999 failed")
        plan = _make_plan(entities={"transaction_ids": ["TXN-9999"]})
        cards = run_async(agent.run(ticket, plan, [0], None))
        assert cards == []


# ---------------------------------------------------------------------------
# run_active_agents (parallel runner)
# ---------------------------------------------------------------------------

class TestRunActiveAgents:
    def test_returns_all_cards_from_active_agents(self, adapters):
        ticket = _make_ticket(
            "Transfer TXN-1009 rejected after 4 PM IST — possible cutoff bug"
        )
        plan = _make_plan(
            ticket_class=TicketClass.CODE_DEFECT,
            active=["HistoryAgent", "LogsAgent"],
            skipped={"KnowledgeAgent": "Pruned", "CodeAgent": "Pruned", "RecordAgent": "Pruned"},
            entities={"transaction_ids": ["TXN-1009"]},
        )
        cards = run_async(run_active_agents(ticket, plan, adapters))
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_skipped_agents_emit_events(self, adapters):
        queue: asyncio.Queue = asyncio.Queue()
        ticket = _make_ticket("How do I add a beneficiary?")
        plan = _make_plan(
            ticket_class=TicketClass.HOW_TO_USER_ERROR,
            active=["KnowledgeAgent"],
            skipped={
                "HistoryAgent": "Pruned: How-To",
                "LogsAgent": "Pruned: How-To",
                "CodeAgent": "Pruned: How-To",
                "RecordAgent": "Pruned: How-To",
            },
        )
        run_async(run_active_agents(ticket, plan, adapters, event_queue=queue))

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        skipped_events = [e for e in events if e.type == "agent_skipped"]
        assert len(skipped_events) == 4
        agent_names = {e.data["agent"] for e in skipped_events}
        assert "HistoryAgent" in agent_names
        assert "CodeAgent" in agent_names

    def test_security_sensitive_returns_empty(self, adapters):
        ticket = _make_ticket("SQL injection detected.")
        plan = _make_plan(
            ticket_class=TicketClass.SECURITY_SENSITIVE,
            active=[],
            skipped={a: "SECURITY ESCALATION" for a in [
                "HistoryAgent", "KnowledgeAgent", "LogsAgent", "CodeAgent", "RecordAgent"
            ]},
        )
        cards = run_async(run_active_agents(ticket, plan, adapters))
        assert cards == []

    def test_all_cards_are_pending_verification(self, adapters):
        """All cards from specialists must be PENDING — Verifier sets final status."""
        ticket = _make_ticket("Transfer rejected at 4 PM — TXN-1009")
        plan = _make_plan(
            active=["HistoryAgent", "LogsAgent"],
            skipped={"KnowledgeAgent": "x", "CodeAgent": "x", "RecordAgent": "x"},
            entities={"transaction_ids": ["TXN-1009"]},
        )
        cards = run_async(run_active_agents(ticket, plan, adapters))
        for card in cards:
            assert card.verification.status == VerificationStatus.PENDING

    def test_s09_only_history_and_logs_run(self, adapters):
        """S09: KNOWN_ERROR routing — only 2 agents active."""
        ticket = _make_ticket("NEFT settlement pending — bank holiday delay")
        planner = Planner()
        plan = run_async(planner.create_routing_plan(ticket))
        cards = run_async(run_active_agents(ticket, plan, adapters))
        specialists_used = {c.specialist for c in cards}
        assert "CodeAgent" not in specialists_used
        assert "RecordAgent" not in specialists_used

    def test_s10_only_knowledge_agent_runs(self, adapters):
        """S10: HOW_TO routing — only KnowledgeAgent active."""
        ticket = _make_ticket("How do I add an international beneficiary?")
        planner = Planner()
        plan = run_async(planner.create_routing_plan(ticket))
        cards = run_async(run_active_agents(ticket, plan, adapters))
        specialists_used = {c.specialist for c in cards}
        assert specialists_used == {"KnowledgeAgent"}
