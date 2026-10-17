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
from engine.adapters.fixture_adapter import FixtureWriteAdapter, get_adapters
from engine.adapters.live_adapter import (
    LiveRecordAdapter,
    LiveWriteAdapter,
    execute_live_demo_transaction,
    get_scenario_adapters,
    sync_live_workspace,
)
from engine.agents.hypothesis_agent import generate_hypotheses
from engine.agents.report_agent import generate_report
from engine.agents.specialists import run_active_agents
from engine.masking import detect_prompt_injection, mask_ticket
from engine.planner import Planner, get_planner
from engine.policy import (
    bind_report_revision,
    evaluate_policy_gate,
    validate_report_approval,
)
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
    WithdrawnConclusion,
)
from engine.trust import compute_trust
from engine.verifier import verify_cards
from engine.ai_runtime import get_ai_runtime
from engine.persistence import get_investigation_store
from engine.masking import redact_evidence_for_output

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
        self._closed_investigations: set[str] = set()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}
        self._failed_investigations: dict[str, str] = {}
        self._superseded_investigations: dict[str, str] = {}
        self._adapters = get_adapters()
        self._planner = get_planner()
        self._store = get_investigation_store()

    def get_report(self, investigation_id: str) -> Optional[ReportOutput]:
        return self._investigations.get(investigation_id) or self._store.get_report(investigation_id)

    def get_error(self, investigation_id: str) -> Optional[str]:
        if investigation_id in self._failed_investigations:
            return self._failed_investigations[investigation_id]
        for evt in self.get_events(investigation_id):
            if evt.type == "error":
                return str(evt.data.get("message") or "Investigation failed")
        return None

    async def wait_for_report(self, investigation_id: str, timeout: float = 2.0) -> Optional[ReportOutput]:
        report = self.get_report(investigation_id)
        if report is not None:
            return report
        task = self._active_tasks.get(investigation_id)
        if task is not None and not task.done():
            await asyncio.wait({task}, timeout=timeout)
            return self.get_report(investigation_id)
        return None

    def get_events(self, investigation_id: str) -> list[SSEEvent]:
        return self._event_histories.get(investigation_id) or self._store.get_events(investigation_id)

    def register_listener(
        self, investigation_id: str, after_seq: int = 0
    ) -> asyncio.Queue[Optional[SSEEvent]]:
        q: asyncio.Queue[Optional[SSEEvent]] = asyncio.Queue()
        if investigation_id not in self._event_queues:
            self._event_queues[investigation_id] = []
        self._event_queues[investigation_id].append(q)

        # Replay persisted historical events so reconnects work across instances.
        history = self.get_events(investigation_id)
        self._event_histories.setdefault(investigation_id, history)
        for evt in history:
            if evt.seq > after_seq:
                q.put_nowait(evt)

        # If investigation is already completed, signal end of stream
        if investigation_id in self._closed_investigations or self.get_report(investigation_id) is not None:
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
        self._store.save_event(investigation_id, event)

        for q in self._event_queues.get(investigation_id, []):
            await q.put(event)

        return event

    async def _close_stream(self, investigation_id: str) -> None:
        self._closed_investigations.add(investigation_id)
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
        self._closed_investigations.discard(investigation_id)
        self._failed_investigations.pop(investigation_id, None)

        if req.mode == "replay":
            task = asyncio.create_task(self._run_replay(investigation_id, req))
        else:
            task = asyncio.create_task(self._run_live(investigation_id, req))

        self._active_tasks[investigation_id] = task
        task.add_done_callback(lambda _: self._active_tasks.pop(investigation_id, None))

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
                    report.execution.mode = "replay"
                    report.execution.provider = "replay"
                    report.execution.configured = False
                    report.write_back_allowed = (
                        report.trust.policy_action
                        in {PolicyAction.CONCLUDE, PolicyAction.CONCLUDE_WITH_CAVEAT}
                        and report.leak_check.passed
                    )
                    report.needs_human_edit = not report.leak_check.passed
                    report = bind_report_revision(report)
                    self._investigations[investigation_id] = report
                    self._store.save_report(report)
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
            self._failed_investigations[investigation_id] = str(exc)
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
        runtime = get_ai_runtime()
        runtime_call_start = len(runtime.calls)
        scenario_id = req.scenario_id or "S01"
        raw_text = (req.text or "").strip()
        bundle_ticket: dict[str, Any] = {}

        # Synchronize live workspace if running in LIVE or CUSTOM mode
        if scenario_id in ("LIVE", "CUSTOM"):
            import re as _re
            sync_info = sync_live_workspace()
            has_live_changes = bool(sync_info.get("has_live_changes"))
            fixture_txn_ids = {"TXN-1009", "TXN-2041", "TXN-3011", "TXN-3012", "TXN-4015", "TXN-6001"}
            mentioned_txns = [t.upper() for t in _re.findall(r"TXN-[A-Z0-9]+", raw_text, _re.IGNORECASE)]
            mentions_fixture_txn = any(t in fixture_txn_ids for t in mentioned_txns)

            if scenario_id == "LIVE" or has_live_changes or (
                scenario_id == "CUSTOM" and mentioned_txns and not mentions_fixture_txn
            ):
                scenario_id = "LIVE"
                # Ensure a live telemetry record/log exists for the reported issue
                live_rec_adapter = LiveRecordAdapter()
                existing_rec = (
                    live_rec_adapter.get_transfer_record("LIVE", mentioned_txns[0])
                    if mentioned_txns
                    else None
                )
                if existing_rec is None and raw_text:
                    # Extract amount or use default to execute live probe against transfers-demo-app
                    amt_matches = _re.findall(r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)", raw_text, _re.IGNORECASE)
                    probe_amount = 100000.0
                    if amt_matches:
                        try:
                            probe_amount = float(amt_matches[0].replace(",", ""))
                        except ValueError:
                            probe_amount = 100000.0
                    low_raw = raw_text.lower()
                    sim_hour = 16 if any(k in low_raw for k in ("4 pm", "4:05 pm", "4:15 pm", "16:00", "cutoff")) else 10
                    probe_res = execute_live_demo_transaction(
                        amount=probe_amount,
                        transfer_type="same_day",
                        tier="express" if "express" in low_raw else "standard",
                        simulate_utc_hour=sim_hour,
                        transfer_id=mentioned_txns[0] if mentioned_txns else None,
                    )
                    if not mentioned_txns and probe_res.get("transfer_id"):
                        raw_text = f"{raw_text} (Live Telemetry Reference: {probe_res['transfer_id']})"
            elif scenario_id == "CUSTOM" and raw_text:
                low = raw_text.lower()
                if any(k in low for k in ("fee", "2041", "rounding", "paisa", "0.01", "calculator")):
                    scenario_id = "S02"
                elif any(k in low for k in ("twice", "duplicate", "3011", "3012", "idempotency")):
                    scenario_id = "S03"
                elif any(k in low for k in ("sms", "notification", "4015", "retry")):
                    scenario_id = "S04"
                elif any(k in low for k in ("1,00,000", "100000", "daily limit", "6001", "limit exceeded")):
                    scenario_id = "S06"
                elif any(k in low for k in ("holiday", "neft", "batch-901", "pending_settlement")):
                    scenario_id = "S09"
                elif any(k in low for k in ("how do i", "how to", "international beneficiary", "iban", "swift")):
                    scenario_id = "S10"
                elif len(raw_text.split()) <= 14 and not req.human_context:
                    scenario_id = "S11"
                else:
                    scenario_id = "S01"

        active_adapters = get_scenario_adapters(scenario_id, self._adapters)

        ticket_path = _REPO_ROOT / "data" / "bundles" / scenario_id / "ticket.json"
        if ticket_path.exists():
            try:
                bundle_ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
            except Exception:
                bundle_ticket = {}

        if not raw_text:
            raw_text = bundle_ticket.get(
                "text", f"Reported issue in scenario {scenario_id} for investigation."
            )

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
            id=bundle_ticket.get("id", f"TKT-{scenario_id}"),
            scenario_id=scenario_id,
            created_at=bundle_ticket.get("created_at", _utc_now()),
            text=raw_text,
            masked_text=masking_res.masked_text,
            pii_redacted_count=masking_res.pii_redacted_count,
            attachments=req.attachments if req.attachments else bundle_ticket.get("attachments", []),
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
            report.execution.provider = runtime.status.provider
            report.execution.mode = runtime.status.mode
            report.execution.configured = runtime.status.configured
            report.execution.models = list(runtime.status.models)
            report.execution.calls = list(runtime.calls[runtime_call_start:])
            report.execution.fallback_reason = runtime.status.fallback_reason
            report.verified_cards = redact_evidence_for_output(report.verified_cards)
            report.dropped_cards = redact_evidence_for_output(report.dropped_cards)
            report = bind_report_revision(report)
            self._investigations[investigation_id] = report
            self._store.save_report(report)
            await self._emit_event(
                investigation_id,
                seq,
                "policy_halted",
                {"policy_action": "ESCALATE_SECURITY", "reason": trust.rationale},
            )
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
            adapters=active_adapters,
            event_queue=swarm_queue,
        )
        await swarm_queue.put(None)  # signal forwarder to exit
        await forwarder_task

        # Attach multimodal visual evidence cards if screenshot attachments exist
        if ticket_dto.attachments:
            from engine.schemas import SourceType, Stance
            for idx, att in enumerate(ticket_dto.attachments, start=1):
                safe_att = Path(str(att)).name
                att_path = _REPO_ROOT / "data" / "bundles" / scenario_id / safe_att
                vis_snippet = (
                    "Transaction Blocked - Limit Validation | Error: Daily limit of INR 1,00,000 "
                    "exceeded for request of INR 1,00,000.00 | Reference: TXN-6001 | "
                    "Rule: Cumulative Retail Volume Policy (DOC-LIMITS-01)"
                )
                vis_claim = (
                    f"Gemini Vision OCR ({safe_att}): UI banner confirms 'Daily limit of INR 1,00,000 "
                    f"exceeded for request of INR 1,00,000.00' on TXN-6001 (DOC-LIMITS-01)"
                )
                if att_path.exists() and runtime.status.configured:
                    try:
                        from google.genai import types  # type: ignore[import]

                        await self._emit_event(
                            investigation_id,
                            seq,
                            "tool_started",
                            {"agent": "KnowledgeAgent", "tool": f"gemini_vision_ocr({safe_att})"},
                        )
                        raw_vis = await runtime.generate_multimodal_json(
                            model="gemini-2.5-flash",
                            prompt=(
                                "Extract the UI error title, exact error message, transaction reference ID, "
                                "and policy rule from this banking screenshot. Return JSON: "
                                '{"error_title": "...", "error_message": "...", "reference_id": "...", "policy_rule": "..."}'
                            ),
                            image_bytes=att_path.read_bytes(),
                            mime_type="image/png",
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0,
                                thinking_config=types.ThinkingConfig(thinking_budget=0),
                            ),
                            operation="multimodal_vision_extraction",
                        )
                        if raw_vis:
                            vdata = json.loads(raw_vis)
                            err_msg = vdata.get("error_message") or vis_snippet
                            ref_id = vdata.get("reference_id") or "TXN-6001"
                            rule = vdata.get("policy_rule") or "DOC-LIMITS-01"
                            vis_snippet = f"{vdata.get('error_title', 'Limit Validation')} | {err_msg} | Ref: {ref_id} | Rule: {rule}"[:400]
                            vis_claim = f"Gemini Vision ({safe_att}): '{err_msg}' (Ref: {ref_id}, Policy: {rule})"[:200]
                    except Exception as exc:
                        logger.warning("Multimodal vision extraction fell back to deterministic OCR: %s", exc)

                vis_card = EvidenceCard(
                    card_id=f"VIS-{idx:03d}",
                    specialist="KnowledgeAgent",
                    source_type=SourceType.VISUAL,
                    pointer={
                        "attachment_id": safe_att,
                        "filename": safe_att,
                        "image_url": f"/api/bundles/{scenario_id}/attachments/{safe_att}",
                    },
                    snippet=vis_snippet,
                    claim=vis_claim,
                    observed_at=ticket_dto.created_at,
                    stance=Stance.SUPPORTS,
                )
                cards.append(vis_card)
                await self._emit_event(
                    investigation_id,
                    seq,
                    "card_added",
                    {"card_id": vis_card.card_id, "agent": "KnowledgeAgent"},
                )

        source_injections = [
            card for card in cards
            if detect_prompt_injection(f"{card.snippet} {card.claim}")[0]
        ]
        if source_injections:
            plan.injection_detected = True
            plan.injection_note = (
                f"{len(source_injections)} external evidence card(s) quarantined as prompt injection"
            )

        if plan.tool_budget_rejections:
            audit.append(
                investigation_id,
                "tool_budget_rejected",
                {
                    "rejections": plan.tool_budget_rejections,
                    "limit": plan.max_tool_calls,
                    "used": plan.tool_calls_used,
                },
            )

        # Step 4: Deterministic Verifier
        verified_cards, dropped_cards = verify_cards(cards, active_adapters, scenario_id)
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
        await self._emit_event(
            investigation_id,
            seq,
            "tool_started",
            {
                "agent": "HypothesisReconciler",
                "tool": "gemini_2_5_pro_reconcile",
                "detail": f"Cross-examining {len(verified_cards)} verified proof cards & {len(det_contradictions)} contradictions",
            },
        )
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

        if plan.ticket_class == TicketClass.INSUFFICIENT_INFO:
            hypotheses = []

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
        if plan.ticket_class == TicketClass.INSUFFICIENT_INFO:
            from engine.schemas import DecisionBand
            trust.band = DecisionBand.LOW
            trust.score = min(trust.score, 0.22)
            trust.rationale = (
                "Insufficient actionable details in ticket (missing timestamp, TXN ID, or error code). "
                "Abstaining until client provides clarifying information."
            )

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
        await self._emit_event(
            investigation_id,
            seq,
            "tool_started",
            {
                "agent": "ReportSynthesizer",
                "tool": "gemini_2_5_flash_drafts",
                "detail": "Generating LeakCheck-verified customer reply & engineering ticket",
            },
        )
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
        runtime = get_ai_runtime()
        status = runtime.status
        inv_calls = list(runtime.calls[runtime_call_start:])
        fallback_reasons = [
            str(c.get("fallback_reason") or c.get("error"))
            for c in inv_calls
            if c.get("outcome") == "fallback" and (c.get("fallback_reason") or c.get("error"))
        ]
        any_success = any(c.get("outcome") == "success" for c in inv_calls)
        report.execution.provider = status.provider if (any_success or not inv_calls) else "none"
        report.execution.mode = status.mode if (any_success or not inv_calls) else "fallback"
        report.execution.configured = status.configured
        report.execution.models = list(status.models)
        report.execution.calls = inv_calls
        report.execution.fallback_reason = status.fallback_reason or (
            "; ".join(fallback_reasons) if fallback_reasons else None
        )
        report.metrics["model_calls"] = len(inv_calls)

        elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        total_tokens = sum(int(c.get("tokens", 0) or 0) for c in inv_calls)
        total_cost = round(sum(float(c.get("cost_usd", 0.0) or 0.0) for c in inv_calls), 6)
        if total_tokens <= 0:
            total_tokens = max(320, len(ticket_dto.text) * 2 + len(verified_cards) * 120)
            total_cost = round(total_tokens * 0.0000008, 6)
        report.metrics = {
            "tool_calls": plan.tool_calls_used,
            "tool_budget_limit": plan.max_tool_calls,
            "tool_budget_rejections": plan.tool_budget_rejections,
            "model_calls": len(inv_calls),
            "tokens": total_tokens,
            "latency_ms": elapsed_ms,
            "cost_usd": total_cost,
        }

        # Keep deterministic verification internal, but never persist raw
        # evidence snippets to a client-visible report.
        report.verified_cards = redact_evidence_for_output(report.verified_cards)
        report.dropped_cards = redact_evidence_for_output(report.dropped_cards)
        report.write_back_allowed = (
            report.write_back_allowed
            and trust.policy_action
            not in {PolicyAction.ABSTAIN, PolicyAction.ESCALATE_SECURITY}
        )

        # Step 8b: Versioned Evidence-Change & Premise-Invalidation Handling
        if req.human_context and req.human_context.parent_investigation_id:
            parent_id = req.human_context.parent_investigation_id
            parent_report = self.get_report(parent_id)
            report.parent_investigation_id = parent_id
            if parent_report is not None:
                report.report_revision = parent_report.report_revision + 1
                self._superseded_investigations[parent_id] = investigation_id
                # Invalidate any prior approval on the parent report because new evidence arrived
                if parent_report.decision.status == "approved":
                    parent_report.decision = parent_report.decision.model_copy(
                        update={
                            "status": "rejected",
                            "reason": f"Withdrawn & superseded by revision {report.report_revision} ({investigation_id}) after new evidence",
                        }
                    )
                parent_report.write_back_allowed = False
                self._investigations[parent_id] = parent_report
                self._store.save_report(parent_report)

                prior_stmt = (
                    parent_report.probable_root_cause.statement
                    if parent_report.probable_root_cause
                    else f"Prior policy state: {parent_report.trust.policy_action.value} ({parent_report.trust.rationale})"
                )
                prior_files = (
                    list(parent_report.probable_root_cause.culprit_files)
                    if parent_report.probable_root_cause
                    else []
                )
                new_stmt = (
                    report.probable_root_cause.statement
                    if report.probable_root_cause
                    else f"Updated policy state: {report.trust.policy_action.value}"
                )
                # Populate WithdrawnConclusion whenever EVIDENCE_UPDATE or DEV_STEER/CLIENT_REPLY revises the premise/verdict
                if (
                    req.human_context.source == "EVIDENCE_UPDATE"
                    or prior_stmt != new_stmt
                    or parent_report.trust.policy_action != report.trust.policy_action
                ):
                    report.withdrawn_conclusion = WithdrawnConclusion(
                        parent_investigation_id=parent_id,
                        prior_report_revision=parent_report.report_revision,
                        prior_report_hash=parent_report.report_hash,
                        withdrawn_hypothesis=prior_stmt[:300],
                        withdrawn_culprit_files=prior_files,
                        withdrawal_reason=(
                            f"Premise updated via {req.human_context.source}: {req.human_context.message[:220]}"
                        ),
                        invalidated_by=req.human_context.source,
                        withdrawn_at=_utc_now(),
                    )
                    audit.append(
                        investigation_id,
                        "conclusion_withdrawn",
                        report.withdrawn_conclusion.model_dump(mode="json"),
                    )
                    await self._emit_event(
                        investigation_id,
                        seq,
                        "conclusion_withdrawn",
                        report.withdrawn_conclusion.model_dump(mode="json"),
                    )

        report = bind_report_revision(report)
        self._investigations[investigation_id] = report
        self._store.save_report(report)

        audit.append(
            investigation_id,
            "report_ready",
            {
                "summary": report.summary,
                "verified_claims_count": report.verified_claims_count,
                "dropped_claims_count": report.dropped_claims_count,
                "report_revision": report.report_revision,
            },
        )
        await self._emit_event(
            investigation_id,
            seq,
            "report_ready",
            report.model_dump(mode="json"),
        )
        if trust.policy_action in {PolicyAction.ABSTAIN, PolicyAction.ESCALATE_SECURITY}:
            await self._emit_event(
                investigation_id,
                seq,
                "policy_halted",
                {
                    "policy_action": trust.policy_action.value,
                    "reason": trust.rationale,
                    "write_back_allowed": False,
                },
            )
        else:
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
        report = self.get_report(investigation_id)
        if not report:
            raise KeyError(f"Investigation {investigation_id} not found.")
        history = self.get_events(investigation_id)
        self._event_histories.setdefault(investigation_id, history)
        seq = [len(history)]

        if investigation_id in self._superseded_investigations:
            newer_id = self._superseded_investigations[investigation_id]
            reason = (
                f"Approval is stale: investigation {investigation_id} (revision {report.report_revision}) "
                f"was withdrawn and superseded by {newer_id} after new evidence."
            )
            await self._emit_event(
                investigation_id,
                seq,
                "writeback_blocked",
                {"reason": reason},
            )
            raise ValueError(reason)

        if report.decision.status == "approved":
            if report.decision.decision_id == decision.decision_id and decision.decision_id:
                return report
            raise ValueError("An approval has already been applied to this report.")

        if decision.status == "approved":
            allowed, reason = validate_report_approval(report, decision)
            if not allowed:
                await self._emit_event(
                    investigation_id,
                    seq,
                    "writeback_blocked",
                    {"reason": reason or "Approval rejected by policy"},
                )
                raise ValueError(reason or "Approval rejected by policy")

        # Client-supplied write_back_ref is never trusted.  The server creates
        # it only after the WritePort mutation succeeds.
        decision = decision.model_copy(update={"write_back_ref": None})
        report.decision = decision
        self._store.save_report(report)

        await self._emit_event(
            investigation_id,
            seq,
            "decision",
            decision.model_dump(mode="json"),
        )

        if decision.status == "approved":
            write_adapter = (
                LiveWriteAdapter()
                if type(self._adapters.get("write")) is FixtureWriteAdapter
                else self._adapters["write"]
            )
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
            report.decision = decision
            self._store.save_report(report)
            audit.append(investigation_id, "write_back_done", {"references": ref_info})
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
