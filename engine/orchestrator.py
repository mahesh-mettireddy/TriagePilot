"""
engine/orchestrator.py
----------------------
End-to-end 12-step pipeline orchestrator for TriagePilot.

Coordinates the complete analysis workflow:
  1. Ingest & Deterministic PII Scrubbing (masking.py)
  2. Intake & Intelligent Router (planner.py)
  3. Selective Specialist Swarm (agents/specialists.py)
  4. Deterministic Verifier (verifier.py)
  5. Deterministic Reconciler (reconcile.py)
  6. Semantic Reconciler & Hypotheses (agents/hypothesis_agent.py)
  7. Deterministic Trust Scorer & Policy Gate (trust.py, policy.py)
  8. Questions & Report Generation (agents/report_agent.py)
  9. Deterministic Leak Check (leakcheck.py)
  10. SHA-256 Hash-Chained Audit Logging (audit.py)
  11. Interactive Pilot-in-the-Middle UI awaiting approval
  12. Idempotent Write-Back on approval (ports/WritePort)

Also supports Replay Mode for pre-cached scenario runs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import engine.audit as audit
from engine.adapters.fixture_adapter import get_adapters
from engine.agents.hypothesis_agent import generate_hypotheses
from engine.agents.report_agent import generate_report
from engine.agents.specialists import run_active_agents
from engine.masking import mask_ticket
from engine.planner import Planner, get_planner
from engine.policy import evaluate_policy_gate
from engine.reconcile import reconcile
from engine.schemas import (
    AgentRoutingPlan,
    Contradiction,
    EvidenceCard,
    HumanContext,
    HumanDecision,
    InvestigationCreateRequest,
    PolicyAction,
    ReportOutput,
    SSEEvent,
    TicketClass,
    TicketDTO,
    TrustSummary,
)
from engine.trust import compute_trust
from engine.verifier import verify_cards

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPLAYS_DIR = _REPO_ROOT / "data" / "replays"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InvestigationManager:
    """
    Manages in-memory state of active and completed investigations,
    their SSE event streams, and write-back decisions.
    """

    def __init__(self) -> None:
        self._investigations: dict[str, ReportOutput] = {}
        self._event_queues: dict[str, list[asyncio.Queue[Optional[SSEEvent]]]] = {}
        self._event_histories: dict[str, list[SSEEvent]] = {}
        self._adapters = get_adapters()
        self._planner = get_planner()

    def get_report(self, investigation_id: str) -> Optional[ReportOutput]:
        return self._investigations.get(investigation_id)

    def get_events(self, investigation_id: str) -> list[SSEEvent]:
        return self._event_histories.get(investigation_id, [])

    def register_listener(self, investigation_id: str) -> asyncio.Queue[Optional[SSEEvent]]:
        q: asyncio.Queue[Optional[SSEEvent]] = asyncio.Queue()
        if investigation_id not in self._event_queues:
            self._event_queues[investigation_id] = []
        self._event_queues[investigation_id].append(q)

        # Replay already-emitted historical events to this new listener
        for evt in self._event_histories.get(investigation_id, []):
            q.put_nowait(evt)

        # If investigation is already completed, signal end of stream
        if investigation_id in self._investigations:
            q.put_nowait(None)

        return q

    async def _emit_event(
        self,
        investigation_id: str,
        seq: list[int],
        event_type: str,
        data: dict[str, Any],
    ) -> SSEEvent:
        seq[0] += 1
        event = SSEEvent(
            seq=seq[0],
            ts=_utc_now(),
            type=event_type,  # type: ignore[arg-type]
            data=data,
        )
        if investigation_id not in self._event_histories:
            self._event_histories[investigation_id] = []
        self._event_histories[investigation_id].append(event)

        for q in self._event_queues.get(investigation_id, []):
            await q.put(event)

        return event

    async def _close_stream(self, investigation_id: str) -> None:
        for q in self._event_queues.get(investigation_id, []):
            await q.put(None)

    async def start_investigation(
        self,
        req: InvestigationCreateRequest,
        wait: bool = False,
    ) -> str:
        investigation_id = f"INV-{uuid.uuid4().hex[:8]}"
        self._event_histories[investigation_id] = []
        self._event_queues[investigation_id] = []

        if req.mode == "replay":
            task = asyncio.create_task(self._run_replay(investigation_id, req))
        else:
            task = asyncio.create_task(self._run_live(investigation_id, req))

        if wait:
            await task

        return investigation_id

    async def _run_replay(
        self,
        investigation_id: str,
        req: InvestigationCreateRequest,
    ) -> None:
        seq = [0]
        scenario_id = req.scenario_id or "S01"
        replay_file = _REPLAYS_DIR / f"{scenario_id}.json"

        # Check for followup / resumed replay
        if req.human_context and req.human_context.source == "CLIENT_REPLY":
            resumed_file = _REPLAYS_DIR / f"{scenario_id}_resumed.json"
            if resumed_file.exists():
                replay_file = resumed_file

        if replay_file.exists():
            try:
                data = json.loads(replay_file.read_text(encoding="utf-8"))
                events_data = data.get("events", [])
                report_data = data.get("report")

                for evt in events_data:
                    await self._emit_event(
                        investigation_id,
                        seq,
                        evt.get("type", "replay_fallback"),
                        evt.get("data", {}),
                    )
                    await asyncio.sleep(0.05)  # slight spacing for realistic UI streaming

                if report_data:
                    report = ReportOutput(**report_data)
                    report.investigation_id = investigation_id
                    report.mode_used = "replay"
                    self._investigations[investigation_id] = report
                    await self._close_stream(investigation_id)
                    return
            except Exception as exc:
                logger.warning("Failed to load replay file %s: %s — falling back to live", replay_file, exc)

        # If replay file not available, fall back to live execution
        await self._emit_event(
            investigation_id,
            seq,
            "replay_fallback",
            {"message": f"Replay data for {scenario_id} not found on disk; running live engine with fixture data."},
        )
        await self._run_live_pipeline(investigation_id, req, seq)

    async def _run_live(
        self,
        investigation_id: str,
        req: InvestigationCreateRequest,
    ) -> None:
        seq = [0]
        try:
            await self._run_live_pipeline(investigation_id, req, seq)
        except Exception as exc:
            logger.error("Error running investigation %s: %s", investigation_id, exc, exc_info=True)
            await self._emit_event(
                investigation_id,
                seq,
                "error",
                {"message": str(exc)},
            )
            await self._close_stream(investigation_id)

    async def _run_live_pipeline(
        self,
        investigation_id: str,
        req: InvestigationCreateRequest,
        seq: list[int],
    ) -> None:
        start_time = datetime.now(timezone.utc)
        scenario_id = req.scenario_id or "S01"
        raw_text = req.text or ""

        # Default ticket text lookup from bundle if not provided directly
        if not raw_text:
            ticket_path = _REPO_ROOT / "data" / "bundles" / scenario_id / "ticket.json"
            if ticket_path.exists():
                try:
                    ticket_json = json.loads(ticket_path.read_text(encoding="utf-8"))
                    raw_text = ticket_json.get("text", f"Issue in {scenario_id}")
                except Exception:
                    raw_text = f"Transfer issue in {scenario_id}"
            else:
                raw_text = f"Reported issue in scenario {scenario_id} for investigation."

        # Step 1: PII Masking & Injection Detection
        masking_res = mask_ticket(raw_text)
        audit.append(
            investigation_id,
            "masking_done",
            {"pii_redacted_count": masking_res.pii_redacted_count, "redacted_types": masking_res.redacted_types},
        )
        await self._emit_event(
            investigation_id,
            seq,
            "masking_done",
            {
                "pii_redacted_count": masking_res.pii_redacted_count,
                "redacted_types": masking_res.redacted_types,
                "injection_detected": masking_res.injection_detected,
                "injection_note": masking_res.injection_note,
            },
        )

        ticket_dto = TicketDTO(
            id=f"TKT-{scenario_id}",
            scenario_id=scenario_id,
            created_at=_utc_now(),
            text=raw_text,
            masked_text=masking_res.masked_text,
            pii_redacted_count=masking_res.pii_redacted_count,
            attachments=req.attachments,
            human_context=req.human_context,
        )

        # Step 2: Intake & Intelligent Router
        plan: AgentRoutingPlan = await self._planner.create_routing_plan(ticket_dto)
        audit.append(
            investigation_id,
            "plan_created",
            {
                "ticket_class": plan.ticket_class.value,
                "severity": plan.severity.value,
                "active_agents": plan.active_agents,
                "skipped_agents": plan.skipped_agents,
            },
        )
        await self._emit_event(
            investigation_id,
            seq,
            "plan_created",
            plan.model_dump(mode="json"),
        )

        # Security fast-exit check
        if plan.ticket_class == TicketClass.SECURITY_SENSITIVE:
            trust = TrustSummary(
                score=0.0,
                band=__import__("engine.schemas", fromlist=["DecisionBand"]).DecisionBand.LOW,
                policy_action=PolicyAction.ESCALATE_SECURITY,
                components=__import__("engine.schemas", fromlist=["TrustComponents"]).TrustComponents(),
                rationale="Security-sensitive ticket class detected. Fast-exit escalation triggered.",
            )
            report = await generate_report(
                ticket=ticket_dto,
                routing_plan=plan,
                verified_cards=[],
                dropped_cards=[],
                contradictions=[],
                hypotheses=[],
                trust=trust,
                investigation_id=investigation_id,
            )
            self._investigations[investigation_id] = report
            await self._emit_event(investigation_id, seq, "abstain", {"policy_action": "ESCALATE_SECURITY"})
            await self._emit_event(investigation_id, seq, "report_ready", report.model_dump(mode="json"))
            await self._close_stream(investigation_id)
            return

        # Step 3: Selective Specialist Swarm (Parallel Execution)
        # Create an intermediate queue to stream swarm events immediately
        swarm_queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        async def _forward_swarm_events():
            while True:
                evt = await swarm_queue.get()
                if evt is None:
                    break
                await self._emit_event(investigation_id, seq, evt.type, evt.data)

        forwarder_task = asyncio.create_task(_forward_swarm_events())
        cards: list[EvidenceCard] = await run_active_agents(
            ticket=ticket_dto,
            plan=plan,
            adapters=self._adapters,
            event_queue=swarm_queue,
        )
        await swarm_queue.put(None)  # signal forwarder to exit
        await forwarder_task

        # Step 4: Deterministic Verifier
        verified_cards, dropped_cards = verify_cards(cards, self._adapters, scenario_id)
        audit.append(
            investigation_id,
            "verifier_result",
            {
                "verified_count": len(verified_cards),
                "dropped_count": len(dropped_cards),
            },
        )
        await self._emit_event(
            investigation_id,
            seq,
            "verifier_result",
            {
                "verified_count": len(verified_cards),
                "dropped_count": len(dropped_cards),
                "dropped_reasons": [
                    {"card_id": c.card_id, "reason": c.verification.reason}
                    for c in dropped_cards
                ],
            },
        )

        # Step 5: Deterministic Reconciler
        det_contradictions: list[Contradiction] = reconcile(ticket_dto, verified_cards)
        for c in det_contradictions:
            await self._emit_event(
                investigation_id,
                seq,
                "contradiction_found",
                c.model_dump(mode="json"),
            )

        # Step 6: Semantic Reconciler & Hypotheses
        hypotheses, sem_contradictions = await generate_hypotheses(
            verified_cards, det_contradictions
        )
        all_contradictions = det_contradictions + sem_contradictions
        for sc in sem_contradictions:
            await self._emit_event(
                investigation_id,
                seq,
                "contradiction_found",
                sc.model_dump(mode="json"),
            )

        await self._emit_event(
            investigation_id,
            seq,
            "hypothesis_update",
            {"hypotheses": [h.model_dump(mode="json") for h in hypotheses]},
        )

        # Step 7: Deterministic Trust Scorer & Policy Gate
        trust: TrustSummary = compute_trust(
            verified_cards=verified_cards,
            dropped_cards=dropped_cards,
            contradictions=all_contradictions,
            hypotheses=hypotheses,
        )
        policy_action = evaluate_policy_gate(
            ticket_class=plan.ticket_class,
            trust=trust,
            injection_detected=plan.injection_detected,
        )
        trust.policy_action = policy_action

        audit.append(
            investigation_id,
            "trust_update",
            {
                "score": trust.score,
                "band": trust.band.value,
                "policy_action": trust.policy_action.value,
            },
        )
        await self._emit_event(
            investigation_id,
            seq,
            "trust_update",
            trust.model_dump(mode="json"),
        )

        if trust.policy_action == PolicyAction.ABSTAIN:
            await self._emit_event(
                investigation_id,
                seq,
                "abstain",
                {"rationale": trust.rationale},
            )

        # Step 8: Questions & Report Generator
        report: ReportOutput = await generate_report(
            ticket=ticket_dto,
            routing_plan=plan,
            verified_cards=verified_cards,
            dropped_cards=dropped_cards,
            contradictions=all_contradictions,
            hypotheses=hypotheses,
            trust=trust,
            investigation_id=investigation_id,
        )

        elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        report.metrics = {
            "tool_calls": len(cards),
            "tokens": 0,
            "latency_ms": elapsed_ms,
            "cost_usd": 0.0,
        }

        self._investigations[investigation_id] = report

        audit.append(
            investigation_id,
            "report_ready",
            {
                "summary": report.summary,
                "verified_claims_count": report.verified_claims_count,
                "dropped_claims_count": report.dropped_claims_count,
            },
        )
        await self._emit_event(
            investigation_id,
            seq,
            "report_ready",
            report.model_dump(mode="json"),
        )
        await self._emit_event(
            investigation_id,
            seq,
            "awaiting_approval",
            {"investigation_id": investigation_id},
        )

        await self._close_stream(investigation_id)

    async def apply_decision(
        self,
        investigation_id: str,
        decision: HumanDecision,
    ) -> ReportOutput:
        report = self._investigations.get(investigation_id)
        if not report:
            raise KeyError(f"Investigation {investigation_id} not found.")

        report.decision = decision
        seq = [len(self._event_histories.get(investigation_id, []))]

        await self._emit_event(
            investigation_id,
            seq,
            "decision",
            decision.model_dump(mode="json"),
        )

        if decision.status == "approved":
            write_adapter = self._adapters["write"]
            ref_info = {}
            if report.jira_draft:
                jira_res = write_adapter.create_issue(
                    {
                        **report.jira_draft.model_dump(mode="json"),
                        "investigation_id": investigation_id,
                    }
                )
                ref_info["jira"] = jira_res

            if report.customer_reply_draft:
                comment_res = write_adapter.post_comment(
                    report.ticket_id, report.customer_reply_draft
                )
                ref_info["comment"] = comment_res

            decision.write_back_ref = json.dumps(ref_info)
            await self._emit_event(
                investigation_id,
                seq,
                "write_back_done",
                ref_info,
            )

        return report


_manager: Optional[InvestigationManager] = None


def get_manager() -> InvestigationManager:
    global _manager
    if _manager is None:
        _manager = InvestigationManager()
    return _manager
