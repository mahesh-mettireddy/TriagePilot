"""
engine/agents/specialists.py
-----------------------------
The 5 specialist sub-agents that run in parallel during Step 3 of the pipeline.

Each agent:
  1. Receives the TicketDTO, AgentRoutingPlan, and its concrete port adapter.
  2. Queries the port to gather raw evidence.
  3. Constructs typed EvidenceCard objects (verification.status = PENDING — 
     the Verifier in Phase 4 will mark them VERIFIED or DROPPED).
  4. Returns a list[EvidenceCard].

Concurrency:
  run_active_agents() uses asyncio.gather to run all ACTIVE agents in parallel.
  Skipped agents emit an "agent_skipped" SSEEvent via the optional event_queue.

Event streaming:
  Pass an asyncio.Queue[SSEEvent] to run_active_agents().  Each agent puts
  events on the queue as they arrive.  The API layer (api/sse.py) drains
  this queue to the client.  If no queue is provided, events are discarded.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from engine.ports.base import (
    CodePort,
    HistoryPort,
    KnowledgePort,
    LogPort,
    RecordPort,
)
from engine.schemas import (
    AgentRoutingPlan,
    EvidenceCard,
    SourceType,
    Stance,
    SSEEvent,
    TicketDTO,
    VerificationResult,
    VerificationStatus,
)
from engine.adk_orchestration import build_adk_specialist_swarm, describe_adk_swarm
from engine.tool_budget import ToolBudget, budgeted_adapters

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _card_id(prefix: str, counter: list[int]) -> str:
    """Generate a deterministic card ID like HIST-001."""
    counter[0] += 1
    return f"{prefix}-{counter[0]:03d}"


def _make_event(seq_counter: list[int], event_type: str, data: dict[str, Any]) -> SSEEvent:
    seq_counter[0] += 1
    return SSEEvent(seq=seq_counter[0], ts=_utc_now(), type=event_type, data=data)


def _pending_card(**kwargs: Any) -> EvidenceCard:
    """Create an EvidenceCard with PENDING verification status."""
    return EvidenceCard(
        verification=VerificationResult(status=VerificationStatus.PENDING),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# HistoryAgent
# ---------------------------------------------------------------------------

class HistoryAgent:
    """
    Queries similar past tickets, known errors, and recent change records.
    Returns EvidenceCards from each data source.
    """

    PREFIX = "HIST"

    def __init__(self, port: HistoryPort) -> None:
        self._port = port

    async def run(
        self,
        ticket: TicketDTO,
        plan: AgentRoutingPlan,
        seq: list[int],
        queue: Optional[asyncio.Queue],
    ) -> list[EvidenceCard]:
        counter: list[int] = [0]
        cards: list[EvidenceCard] = []
        text = ticket.masked_text or ticket.text
        if ticket.human_context and ticket.human_context.message:
            text = f"{text}\n{ticket.human_context.message}"

        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "HistoryAgent", "tool": "similar_tickets"
        }))

        # 1. Similar past tickets
        try:
            similar = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._port.similar_tickets(text, limit=3)
            )
            for t in similar:
                card = _pending_card(
                    card_id=_card_id(self.PREFIX, counter),
                    specialist="HistoryAgent",
                    source_type=SourceType.TICKET,
                    pointer={"system": "ServiceDesk", "id": t.get("id", "?"), "field": "resolution"},
                    snippet=(t.get("resolution") or t.get("title", ""))[:400],
                    claim=f"Past ticket {t.get('id')} resolved as: {t.get('ticket_class', 'UNKNOWN')}",
                    stance=Stance.CONTEXT,
                    observed_at=t.get("resolved_at"),
                )
                cards.append(card)
                await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "HistoryAgent"}))
        except Exception as exc:
            logger.warning("HistoryAgent.similar_tickets failed: %s", exc)

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "HistoryAgent", "tool": "similar_tickets", "cards": len(cards)
        }))

        # 2. Known errors (queried when ticket class is KNOWN_ERROR or mentions holiday/settlement/batch/KE)
        text_lower = text.lower()
        should_check_ke = (
            plan.ticket_class.value == "KNOWN_ERROR"
            or any(k in text_lower for k in ("holiday", "settlement", "batch", "ke-", "known error"))
        )
        if should_check_ke:
            await _emit(queue, _make_event(seq, "tool_started", {
                "agent": "HistoryAgent", "tool": "known_errors"
            }))
            try:
                known = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._port.known_errors(text)
                )
                for ke in known[:2]:
                    card = _pending_card(
                        card_id=_card_id(self.PREFIX, counter),
                        specialist="HistoryAgent",
                        source_type=SourceType.TICKET,
                        pointer={"system": "KnowledgeBase", "id": ke.get("ke_id", "?"), "field": "workaround"},
                        snippet=(ke.get("workaround") or ke.get("symptoms", ""))[:400],
                        claim=f"Known Error {ke.get('ke_id')}: {ke.get('title', '')}",
                        stance=Stance.CONTEXT,
                    )
                    cards.append(card)
                    await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "HistoryAgent"}))
            except Exception as exc:
                logger.warning("HistoryAgent.known_errors failed: %s", exc)

            await _emit(queue, _make_event(seq, "tool_finished", {
                "agent": "HistoryAgent", "tool": "known_errors", "cards": len(cards)
            }))

        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "HistoryAgent", "tool": "recent_changes"
        }))

        # 3. Recent changes (last 14 days)
        try:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            window_start = (now - timedelta(days=14)).isoformat()
            changes = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._port.recent_changes(window_start, now.isoformat())
            )
            for chg in changes[:3]:
                card = _pending_card(
                    card_id=_card_id(self.PREFIX, counter),
                    specialist="HistoryAgent",
                    source_type=SourceType.TICKET,
                    pointer={"system": "ITSM", "id": chg.get("change_id", "?"), "field": "deployed_at"},
                    snippet=(
                        f"{chg.get('change_id')} — {chg.get('title','')} "
                        f"(deployed {chg.get('deployed_at','')}, "
                        f"modules: {', '.join(chg.get('modules_affected',[]))})"
                    )[:400],
                    claim=f"Change {chg.get('change_id')} deployed affecting {chg.get('modules_affected', [])}",
                    stance=Stance.CONTEXT,
                    observed_at=chg.get("deployed_at"),
                )
                cards.append(card)
                await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "HistoryAgent"}))
        except Exception as exc:
            logger.warning("HistoryAgent.recent_changes failed: %s", exc)

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "HistoryAgent", "tool": "recent_changes", "cards": len(cards)
        }))
        return cards


# ---------------------------------------------------------------------------
# KnowledgeAgent
# ---------------------------------------------------------------------------

class KnowledgeAgent:
    """Queries runbooks and architecture docs."""

    PREFIX = "KNOW"

    def __init__(self, port: KnowledgePort) -> None:
        self._port = port

    async def run(
        self,
        ticket: TicketDTO,
        plan: AgentRoutingPlan,
        seq: list[int],
        queue: Optional[asyncio.Queue],
    ) -> list[EvidenceCard]:
        counter: list[int] = [0]
        cards: list[EvidenceCard] = []
        text = ticket.masked_text or ticket.text
        if ticket.human_context and ticket.human_context.message:
            text = f"{text}\n{ticket.human_context.message}"

        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "KnowledgeAgent", "tool": "search_docs"
        }))

        try:
            docs = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._port.search_docs(text, limit=1)
            )
            for doc in docs:
                # Fetch the first section for the snippet
                section_name = ""
                if hasattr(self._port, "_pages"):
                    page = next(
                        (p for p in self._port._pages if p.get("page_id") == doc.get("page_id")),
                        None,
                    )
                    section_name = next(iter((page or {}).get("sections", {})), "")
                section_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda d=doc: self._port.get_doc_section(
                        d["page_id"], section_name
                    ),
                )
                snippet = (
                    section_data["content"][:400]
                    if section_data
                    else doc.get("summary", "")[:400]
                )
                card = _pending_card(
                    card_id=_card_id(self.PREFIX, counter),
                    specialist="KnowledgeAgent",
                    source_type=SourceType.DOC,
                    pointer={
                        "space": doc.get("space", "KB"),
                        "page_id": doc["page_id"],
                        "section": section_data.get("section", section_name) if section_data else section_name,
                        "last_updated": doc.get("last_updated", ""),
                    },
                    snippet=snippet,
                    claim=f"Doc {doc['page_id']}: {doc.get('title','')} (last updated {doc.get('last_updated','')})",
                    stance=Stance.CONTEXT,
                )
                cards.append(card)
                await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "KnowledgeAgent"}))
        except Exception as exc:
            logger.warning("KnowledgeAgent.search_docs failed: %s", exc)

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "KnowledgeAgent", "tool": "search_docs", "cards": len(cards)
        }))
        return cards


# ---------------------------------------------------------------------------
# LogsAgent
# ---------------------------------------------------------------------------

class LogsAgent:
    """Queries log events, error signatures, and trace lookups."""

    PREFIX = "LOG"

    def __init__(self, port: LogPort) -> None:
        self._port = port

    async def run(
        self,
        ticket: TicketDTO,
        plan: AgentRoutingPlan,
        seq: list[int],
        queue: Optional[asyncio.Queue],
    ) -> list[EvidenceCard]:
        import re as _re
        counter: list[int] = [0]
        cards: list[EvidenceCard] = []
        scenario_id = ticket.scenario_id or "S01"
        entities = plan.extracted_entities

        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "LogsAgent", "tool": "query_logs"
        }))

        # 1. Query logs (ERROR level first for conciseness)
        try:
            logs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._port.query_logs(
                    scenario_id,
                    filters={"level": "ERROR"},
                    limit=5,
                ),
            )
            for log in logs:
                message = log.get("message", "")
                # Check for prompt injection inside log lines
                from engine.masking import detect_prompt_injection
                inj, _ = detect_prompt_injection(message)
                stance = Stance.CONTRADICTS if inj else Stance.SUPPORTS

                card = _pending_card(
                    card_id=_card_id(self.PREFIX, counter),
                    specialist="LogsAgent",
                    source_type=SourceType.LOG,
                    pointer={
                        "log_id": log.get("log_id", "?"),
                        "ts": log.get("ts", ""),
                        "service": log.get("service", ""),
                    },
                    snippet=message[:400],
                    claim=(
                        f"ERROR in {log.get('service')} at {log.get('ts')}: "
                        f"{message[:80]}"
                    ),
                    stance=stance,
                    observed_at=log.get("ts"),
                )
                cards.append(card)
                await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "LogsAgent"}))
        except Exception as exc:
            logger.warning("LogsAgent.query_logs failed: %s", exc)

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "LogsAgent", "tool": "query_logs", "cards": len(cards)
        }))
        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "LogsAgent", "tool": "digest_signatures"
        }))

        # 2. Error signature digest
        try:
            sigs = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._port.digest_signatures(scenario_id)
            )
            for sig in sigs[:2]:
                card = _pending_card(
                    card_id=_card_id(self.PREFIX, counter),
                    specialist="LogsAgent",
                    source_type=SourceType.LOG,
                    pointer={
                        "log_id": sig.get("sample_log_id", "?"),
                        "ts": sig.get("first_seen", ""),
                        "service": "digest",
                    },
                    snippet=(
                        f"Error signature '{sig.get('signature','')}' "
                        f"seen {sig.get('count', 1)}x "
                        f"(first: {sig.get('first_seen','')}, last: {sig.get('last_seen','')})"
                    )[:400],
                    claim=f"Recurring error pattern: '{sig.get('signature','')}' ({sig.get('count',1)} occurrences)",
                    stance=Stance.SUPPORTS,
                    observed_at=sig.get("first_seen"),
                )
                cards.append(card)
                await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "LogsAgent"}))
        except Exception as exc:
            logger.warning("LogsAgent.digest_signatures failed: %s", exc)

        # 3. Trace lookup if trace IDs / TXN IDs in entities
        txn_ids = entities.get("transaction_ids", [])
        if txn_ids:
            await _emit(queue, _make_event(seq, "tool_started", {
                "agent": "LogsAgent", "tool": "trace_lookup"
            }))
            try:
                # Use the first TXN ID as a trace hint
                trace_logs = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._port.trace_lookup(scenario_id, f"trace-{txn_ids[0]}"),
                )
                for log in trace_logs[:3]:
                    card = _pending_card(
                        card_id=_card_id(self.PREFIX, counter),
                        specialist="LogsAgent",
                        source_type=SourceType.LOG,
                        pointer={
                            "log_id": log.get("log_id", "?"),
                            "ts": log.get("ts", ""),
                            "service": log.get("service", ""),
                        },
                        snippet=log.get("message", "")[:400],
                        claim=f"Trace event for {txn_ids[0]}: {log.get('message','')[:80]}",
                        stance=Stance.SUPPORTS,
                        observed_at=log.get("ts"),
                    )
                    cards.append(card)
                    await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "LogsAgent"}))
            except Exception as exc:
                logger.warning("LogsAgent.trace_lookup failed: %s", exc)
            await _emit(queue, _make_event(seq, "tool_finished", {
                "agent": "LogsAgent", "tool": "trace_lookup"
            }))

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "LogsAgent", "tool": "digest_signatures", "cards": len(cards)
        }))
        return cards


# ---------------------------------------------------------------------------
# CodeAgent
# ---------------------------------------------------------------------------

class CodeAgent:
    """Inspects the git repository: searches code, reads lines, git log/blame/diff."""

    PREFIX = "CODE"

    def __init__(self, port: CodePort) -> None:
        self._port = port

    async def run(
        self,
        ticket: TicketDTO,
        plan: AgentRoutingPlan,
        seq: list[int],
        queue: Optional[asyncio.Queue],
    ) -> list[EvidenceCard]:
        counter: list[int] = [0]
        cards: list[EvidenceCard] = []
        text = ticket.masked_text or ticket.text
        if ticket.human_context and ticket.human_context.message:
            text = f"{text}\n{ticket.human_context.message}"
        entities = plan.extracted_entities

        # Build search query from modules hint or ticket text
        dev_steer_files = [f for f in entities.get("dev_steer_focus", []) if isinstance(f, str) and len(f) <= 48]
        modules = entities.get("modules", [])
        fallback_hint = self._extract_code_hint(text)
        search_query = dev_steer_files[0] if dev_steer_files else (
            modules[0] if modules else fallback_hint
        )

        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "CodeAgent", "tool": "search_code", "query": search_query
        }))

        # 1. Search for relevant code
        try:
            def _search_with_fallback() -> list[dict[str, Any]]:
                hits = self._port.search_code(search_query, limit=5)
                if not hits and search_query != fallback_hint:
                    hits = self._port.search_code(fallback_hint, limit=5)
                return hits

            results = await asyncio.get_event_loop().run_in_executor(
                None, _search_with_fallback
            )
            for hit in results:
                pointer_data: dict[str, Any] = {
                    "repo": "clientrepo",
                    "path": hit.get("path", ""),
                    "line_start": hit.get("line_number", 1),
                    "line_end": hit.get("line_number", 1),
                    "sha": hit.get("sha", ""),
                }
                if hit.get("commit_sha"):
                    pointer_data["commit_sha"] = hit["commit_sha"]
                if hit.get("is_live_diff"):
                    pointer_data["is_live_diff"] = True
                    if hit.get("before_line"):
                        pointer_data["before_line"] = hit["before_line"]
                    if hit.get("commit_message"):
                        pointer_data["commit_message"] = hit["commit_message"]
                if hit.get("is_live_diff"):
                    before_part = f"from `{str(hit['before_line'])[:38]}` " if hit.get("before_line") else ""
                    after_part = str(hit.get("snippet", "")).splitlines()[-1][:42]
                    sha_short = str(hit.get("commit_sha", ""))[:7]
                    msg_short = str(hit.get("commit_message", ""))[:32]
                    msg_part = f" (@{sha_short}: {msg_short})" if msg_short else f" (@{sha_short})"
                    claim_text = (
                        f"Live Git Edit {hit.get('path','')}:{hit.get('line_number','')} — "
                        f"{before_part}-> `{after_part}`{msg_part}"
                    )[:200]
                else:
                    claim_text = (
                        f"Code match in {hit.get('path','')}:{hit.get('line_number','')} — {hit.get('snippet','')[:80]}"
                    )[:200]
                card = _pending_card(
                    card_id=_card_id(self.PREFIX, counter),
                    specialist="CodeAgent",
                    source_type=SourceType.CODE,
                    pointer=pointer_data,
                    snippet=hit.get("snippet", "")[:400],
                    claim=claim_text[:200],
                    stance=Stance.SUPPORTS,
                    observed_at=hit.get("commit_date"),
                )
                cards.append(card)
                await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "CodeAgent"}))
        except Exception as exc:
            logger.warning("CodeAgent.search_code failed: %s", exc)

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "CodeAgent", "tool": "search_code", "cards": len(cards)
        }))

        # 2. Git log for suspected files (enrich every matched file path with its latest commit SHA & timestamp)
        if cards:
            unique_paths: list[str] = []
            for c in cards:
                p = c.pointer.get("path", "")
                if p and p not in unique_paths:
                    unique_paths.append(p)
            for suspected_path in unique_paths[:3]:
                await _emit(queue, _make_event(seq, "tool_started", {
                    "agent": "CodeAgent", "tool": "git_log", "path": suspected_path
                }))
                try:
                    commits = await asyncio.get_event_loop().run_in_executor(
                        None, lambda p=suspected_path: self._port.git_log(p, n=5)
                    )
                    if commits:
                        latest = commits[0]
                        commit_date = latest.get("date")
                        commit_sha = latest.get("sha", "")
                        for c in cards:
                            if c.pointer.get("path") == suspected_path:
                                if commit_date and not c.observed_at:
                                    c.observed_at = commit_date
                                if commit_sha and not commit_sha.startswith("stub"):
                                    c.pointer["commit_sha"] = commit_sha
                except Exception as exc:
                    logger.warning("CodeAgent.git_log failed: %s", exc)

                await _emit(queue, _make_event(seq, "tool_finished", {
                    "agent": "CodeAgent", "tool": "git_log"
                }))

        return cards

    @staticmethod
    def _extract_code_hint(text: str) -> str:
        """Extract a code-relevant search term from ticket text."""
        import re
        lower = text.lower()
        # Look for .py file mentions first
        py_files = re.findall(r"\b\w+\.py\b", text)
        if py_files:
            return py_files[0]
        # Domain-specific keywords before generic "transfer"
        keyword_map = [
            (["cutoff", "same-day", "same_day", "4 pm", "4:15 pm", "16:00", "timezone"], "cutoff.py"),
            (["fee", "calculator", "rounding", "overbilled", "overcharged", "paisa", "tier", "gst", "commission", "deduction"], "calculator.py"),
            (["sms", "notification", "alert", "delivery"], "sms.py"),
            (["idempotency", "charged twice", "duplicate", "clicking transfer quickly", "double"], "idempotency.py"),
            (["daily limit", "daily_limit", "1,00,000", "100000", "limit exceeded", "limit", "cap", "maximum"], "daily_limit.py"),
            (["beneficiary", "international", "domestic", "swift", "bic", "iban", "ifsc", "cooling"], "manager.py"),
            (["settlement", "batch", "clearing", "neft"], "batch.py"),
        ]
        for triggers, hint in keyword_map:
            if any(t in lower for t in triggers):
                return hint
        return "cutoff"


# ---------------------------------------------------------------------------
# RecordAgent
# ---------------------------------------------------------------------------

class RecordAgent:
    """Fetches masked transaction/record snapshots. Zero raw SQL."""

    PREFIX = "REC"

    def __init__(self, port: RecordPort) -> None:
        self._port = port

    async def run(
        self,
        ticket: TicketDTO,
        plan: AgentRoutingPlan,
        seq: list[int],
        queue: Optional[asyncio.Queue],
    ) -> list[EvidenceCard]:
        counter: list[int] = [0]
        cards: list[EvidenceCard] = []
        scenario_id = ticket.scenario_id or "S01"
        txn_ids = plan.extracted_entities.get("transaction_ids", [])

        # Also look for TXN IDs in ticket text + human_context
        import re
        combined_text = ticket.masked_text or ticket.text
        if ticket.human_context and ticket.human_context.message:
            combined_text = f"{combined_text}\n{ticket.human_context.message}"
        text_txns = re.findall(r"TXN-[A-Z0-9]+", combined_text, re.IGNORECASE)
        all_txn_ids = list(dict.fromkeys(txn_ids + text_txns))

        if not all_txn_ids:
            logger.info("RecordAgent: no transaction IDs found — skipping")
            return []

        await _emit(queue, _make_event(seq, "tool_started", {
            "agent": "RecordAgent", "tool": "get_transfer_record"
        }))

        for txn_id in all_txn_ids[:3]:
            try:
                record = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda tid=txn_id: self._port.get_transfer_record(scenario_id, tid),
                )
                if record:
                    card = _pending_card(
                        card_id=_card_id(self.PREFIX, counter),
                        specialist="RecordAgent",
                        source_type=SourceType.RECORD,
                        pointer={
                            "table": "transfers",
                            "id": txn_id,
                            "field": "status",
                        },
                        snippet=(
                            f"Transfer {txn_id}: status={record.get('status')}, "
                            f"amount={record.get('amount')}, fee={record.get('fee')}, "
                            f"created_at={record.get('created_at')}, "
                            f"account={record.get('masked_account','[ACCT_REDACTED]')}"
                        )[:400],
                        claim=f"Record {txn_id}: status={record.get('status')}, amount={record.get('amount')}",
                        stance=Stance.SUPPORTS,
                        observed_at=record.get("created_at"),
                    )
                    cards.append(card)
                    await _emit(queue, _make_event(seq, "card_added", {"card_id": card.card_id, "agent": "RecordAgent"}))
                else:
                    logger.info("RecordAgent: no record found for %s in scenario %s", txn_id, scenario_id)
            except Exception as exc:
                logger.warning("RecordAgent.get_transfer_record(%s) failed: %s", txn_id, exc)

        await _emit(queue, _make_event(seq, "tool_finished", {
            "agent": "RecordAgent", "tool": "get_transfer_record", "cards": len(cards)
        }))
        return cards


# ---------------------------------------------------------------------------
# Parallel runner
# ---------------------------------------------------------------------------

async def _emit(
    queue: Optional[asyncio.Queue],
    event: SSEEvent,
) -> None:
    """Put an SSEEvent on the queue if provided; otherwise discard."""
    if queue is not None:
        await queue.put(event)


async def run_active_agents(
    ticket: TicketDTO,
    plan: AgentRoutingPlan,
    adapters: dict[str, Any],
    event_queue: Optional[asyncio.Queue] = None,
) -> list[EvidenceCard]:
    """
    Run all ACTIVE agents concurrently via asyncio.gather.

    Emits 'agent_skipped' SSEEvents for pruned agents.
    Returns the combined list of EvidenceCards from all active agents.

    Args:
        ticket:       The masked TicketDTO.
        plan:         AgentRoutingPlan from the planner.
        adapters:     Dict of port adapters from get_adapters().
        event_queue:  asyncio.Queue to stream SSEEvents; None to discard.
    """
    # Shared sequence counter (mutable list for closure mutation)
    seq: list[int] = [0]
    budget = ToolBudget(plan.max_tool_calls)
    guarded_adapters = budgeted_adapters(adapters, budget)

    # Register reusable ADK contracts only.  The installed path is explicitly
    # registration-only; deterministic ports remain the source of facts and
    # the shared budget is passed into ADK registration as a hard invariant.
    adk_swarm = build_adk_specialist_swarm(
        adapters,
        list(plan.active_agents),
        budget=budget,
    )
    adk_meta = describe_adk_swarm(list(plan.active_agents))
    await _emit(event_queue, _make_event(seq, "adk_orchestration", {
        "native_adk_registered": adk_swarm is not None,
        "native_adk_executed": False,
        "execution": "registration_only",
        "active_agents": list(plan.active_agents),
        "model": "gemini-2.5-flash",
        "tool_budget": budget.limit,
        "swarm_topology": adk_meta,
    }))

    # Emit agent_skipped for pruned agents
    for agent_name, reason in plan.skipped_agents.items():
        await _emit(event_queue, _make_event(seq, "agent_skipped", {
            "agent": agent_name,
            "reason": reason,
        }))

    # Build coroutines for each ACTIVE agent
    _agent_map = {
        "HistoryAgent":   lambda: HistoryAgent(guarded_adapters["history"]).run(ticket, plan, seq, event_queue),
        "KnowledgeAgent": lambda: KnowledgeAgent(guarded_adapters["knowledge"]).run(ticket, plan, seq, event_queue),
        "LogsAgent":      lambda: LogsAgent(guarded_adapters["logs"]).run(ticket, plan, seq, event_queue),
        "CodeAgent":      lambda: CodeAgent(guarded_adapters["code"]).run(ticket, plan, seq, event_queue),
        "RecordAgent":    lambda: RecordAgent(guarded_adapters["record"]).run(ticket, plan, seq, event_queue),
    }

    coros = [
        _agent_map[agent]()
        for agent in plan.active_agents
        if agent in _agent_map
    ]

    if not coros:
        logger.info("No active agents — SECURITY_SENSITIVE or all pruned.")
        plan.tool_calls_used = 0
        return []

    # Run all active agents in parallel
    results: list[list[EvidenceCard]] = await asyncio.gather(*coros, return_exceptions=False)

    # Flatten and return
    all_cards: list[EvidenceCard] = []
    for card_list in results:
        if isinstance(card_list, list):
            all_cards.extend(card_list)

    plan.tool_calls_used = budget.used
    plan.tool_budget_rejections = len(budget.rejections)
    for rejection in budget.rejections:
        await _emit(event_queue, _make_event(seq, "tool_budget_rejected", {
            **rejection,
            "message": "Tool invocation rejected before adapter execution; hard budget preserved.",
        }))

    logger.info(
        "Specialist swarm complete: %d active agents, %d evidence cards",
        len(plan.active_agents),
        len(all_cards),
    )
    return all_cards
