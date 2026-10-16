"""
api/a2a.py
----------
Official Google Agent2Agent (A2A) Protocol implementation for TriagePilot.

Exposes:
  - GET  /.well-known/agent.json : Canonical A2A AgentCard discovery document
  - GET  /api/a2a/agent-card     : Alias for UI / API inspection
  - POST /a2a/tasks/send         : A2A Task submission (supports both REST and JSON-RPC 2.0)
  - POST /a2a                    : Canonical A2A JSON-RPC 2.0 endpoint (`tasks/send`, `tasks/get`)
  - GET  /a2a/tasks/{task_id}    : Retrieve A2A Task state and verified Evidentiary Artifacts

Enables Tier-1 Customer Support Agents, Banking Portals, and peer enterprise
agents to discover TriagePilot's capabilities and delegate live incident
investigations over the open A2A protocol.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from engine.adk_orchestration import describe_adk_swarm
from engine.orchestrator import get_manager
from engine.schemas import HumanContext, InvestigationCreateRequest, PolicyAction, ReportOutput

router = APIRouter(tags=["A2A Protocol"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_agent_card(base_url: str = "") -> Dict[str, Any]:
    """Construct the canonical Google A2A AgentCard descriptor."""
    root = base_url.rstrip("/") if base_url else ""
    adk_info = describe_adk_swarm()
    return {
        "name": "TriagePilot Autonomous Incident Analyst",
        "description": (
            "Enterprise neuro-symbolic incident analyst and evidentiary bridge. "
            "Coordinates a 5-specialist Google ADK swarm across Git repositories, "
            "structured telemetry, transaction ledgers, and SOP runbooks with "
            "100% deterministic Python citation verification and SHA-256 audit governance."
        ),
        "url": f"{root}/a2a",
        "version": "1.0.0",
        "protocolVersion": "0.2.1",
        "provider": {
            "organization": "TriagePilot Enterprise",
            "url": f"{root}/",
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "authentication": {
            "schemes": ["None", "Bearer"],
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["application/json", "text/markdown"],
        "adkOrchestration": adk_info,
        "skills": [
            {
                "id": "incident_root_cause_triage",
                "name": "Autonomous 4-Way Root Cause Triage",
                "description": (
                    "Ingests customer or service incident reports, scrubs PII deterministically, "
                    "and dispatches a selective Google ADK specialist swarm across Logs, Git AST, "
                    "Transaction Records, Runbooks, and ITSM History."
                ),
                "tags": ["incident-response", "sre", "root-cause-analysis", "adk-swarm"],
                "examples": [
                    "Investigate rejected same-day transfer TXN-1009 after 4:00 PM IST.",
                    "Triage live fee calculation discrepancy on recent commit in transfers-demo-app.",
                ],
            },
            {
                "id": "deterministic_evidence_verification",
                "name": "Deterministic Citation & Contradiction Verification",
                "description": (
                    "Pure-Python verification of every model-proposed EvidenceCard against "
                    "pinned 40-character Git commit SHAs, ±1s UTC log timestamps, and "
                    "4-way cross-source contradiction detection (TIME_MISMATCH, BEHAVIOUR_MISMATCH, STALE_DOC_FLAG)."
                ),
                "tags": ["verification", "zero-hallucination", "neuro-symbolic", "governance"],
                "examples": [
                    "Verify whether commit SHA and line numbers match live repository state.",
                ],
            },
            {
                "id": "maker_checker_remediation",
                "name": "Maker-Checker Issue & Customer Response Drafting",
                "description": (
                    "Generates LeakCheck-sanitized customer replies and engineering bug drafts "
                    "bound by SHA-256 report revision hashes prior to human approval."
                ),
                "tags": ["maker-checker", "jira", "github-issues", "leak-check"],
                "examples": [
                    "Draft customer-safe explanation and engineering bug report for approved incident.",
                ],
            },
        ],
        "adk_orchestration": describe_adk_swarm(),
    }


def _report_to_a2a_task(task_id: str, report: ReportOutput) -> Dict[str, Any]:
    """Convert a TriagePilot ReportOutput into a standard A2A Task object with Artifacts."""
    if report.trust.policy_action == PolicyAction.ABSTAIN:
        a2a_state = "input-required"
    elif report.trust.policy_action == PolicyAction.ESCALATE_SECURITY:
        a2a_state = "failed"
    else:
        a2a_state = "completed"

    artifacts: List[Dict[str, Any]] = [
        {
            "name": "verified_triage_report",
            "description": "Complete neuro-symbolic ReportOutput with verified evidence cards and trust math",
            "parts": [
                {
                    "type": "text",
                    "text": report.summary,
                },
                {
                    "type": "data",
                    "data": {
                        "investigation_id": report.investigation_id,
                        "ticket_class": report.ticket_class.value,
                        "severity": report.severity.value,
                        "trust_score": report.trust.score,
                        "trust_band": report.trust.band.value,
                        "policy_action": report.trust.policy_action.value,
                        "verified_claims_count": report.verified_claims_count,
                        "dropped_claims_count": report.dropped_claims_count,
                        "culprit_files": (
                            report.probable_root_cause.culprit_files
                            if report.probable_root_cause
                            else []
                        ),
                        "culprit_commit": (
                            report.probable_root_cause.culprit_commit
                            if report.probable_root_cause
                            else None
                        ),
                        "report_hash": report.report_hash,
                    },
                },
            ],
        },
        {
            "name": "customer_safe_reply",
            "description": "LeakCheck-sanitized customer response draft",
            "parts": [
                {
                    "type": "text",
                    "text": report.customer_reply_draft,
                }
            ],
        },
    ]

    if report.jira_draft:
        artifacts.append(
            {
                "name": "engineering_issue_draft",
                "description": "Verified engineering issue draft with Git commit permalinks",
                "parts": [
                    {
                        "type": "data",
                        "data": report.jira_draft.model_dump(mode="json"),
                    }
                ],
            }
        )

    return {
        "id": task_id,
        "sessionId": report.investigation_id,
        "investigation_id": report.investigation_id,
        "status": {
            "state": a2a_state,
            "timestamp": _utc_now(),
            "message": {
                "role": "agent",
                "parts": [{"type": "text", "text": report.summary}],
            },
        },
        "artifacts": artifacts,
        "metadata": {
            "protocol": "A2A/0.2.1",
            "adk_active_agents": report.routing_plan.active_agents,
            "tool_calls_used": report.metrics.get("tool_calls", 0),
            "report_hash": report.report_hash,
            "audit_ref": report.audit_ref,
        },
    }


def _extract_text_from_a2a_params(params: Dict[str, Any]) -> tuple[str, str, Optional[HumanContext]]:
    """Extract ticket text, scenario_id, and optional HumanContext from an A2A payload."""
    scenario_id = str(params.get("scenario_id") or params.get("metadata", {}).get("scenario_id") or "LIVE")
    text_chunks: List[str] = []

    if isinstance(params.get("text"), str) and params["text"].strip():
        text_chunks.append(params["text"].strip())

    msg = params.get("message") or {}
    if isinstance(msg, dict):
        for part in msg.get("parts", []):
            if isinstance(part, dict):
                if part.get("type") == "text" and part.get("text"):
                    text_chunks.append(str(part["text"]).strip())
                elif part.get("type") == "data" and isinstance(part.get("data"), dict):
                    d = part["data"]
                    if d.get("text"):
                        text_chunks.append(str(d["text"]).strip())
                    if d.get("scenario_id"):
                        scenario_id = str(d["scenario_id"])

    combined_text = "\n".join(text_chunks).strip()
    human_ctx = None
    if params.get("human_context") and isinstance(params["human_context"], dict):
        human_ctx = HumanContext(**params["human_context"])

    return combined_text, scenario_id, human_ctx


@router.get("/.well-known/agent.json")
@router.get("/api/a2a/agent-card")
async def get_a2a_agent_card(request: Request) -> Dict[str, Any]:
    """Return the canonical Google A2A AgentCard discovery document."""
    base = str(request.base_url).rstrip("/")
    return build_agent_card(base)


_A2A_TASK_MAP: Dict[str, str] = {}


@router.post("/a2a/tasks/send")
async def a2a_send_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept an A2A Task submission from an external agent or client service,
    execute TriagePilot's neuro-symbolic investigation pipeline, and return
    the completed A2A Task with verified Artifacts.
    """
    params = payload.get("params", payload) if isinstance(payload, dict) else {}
    task_id = str(params.get("id") or f"a2a-task-{uuid.uuid4().hex[:8]}")
    text, scenario_id, human_ctx = _extract_text_from_a2a_params(params)

    if not text and scenario_id in ("LIVE", "CUSTOM"):
        text = "Live transaction incident escalated via A2A protocol for root-cause verification."

    manager = get_manager()
    req = InvestigationCreateRequest(
        scenario_id=scenario_id,
        text=text or None,
        mode="live",
        human_context=human_ctx,
    )
    inv_id = await manager.start_investigation(req, wait=True)
    _A2A_TASK_MAP[task_id] = inv_id
    report = await manager.wait_for_report(inv_id, timeout=10.0)
    if report is None:
        raise HTTPException(status_code=500, detail=f"A2A task {task_id} investigation {inv_id} did not complete")

    task_result = _report_to_a2a_task(task_id, report)
    if "jsonrpc" in payload:
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", task_id),
            "result": task_result,
        }
    return task_result


@router.post("/a2a")
async def a2a_jsonrpc_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical JSON-RPC 2.0 endpoint for Google A2A protocol (`tasks/send`, `tasks/get`)."""
    method = payload.get("method", "tasks/send")
    rpc_id = payload.get("id", "1")
    params = payload.get("params", {})

    if method in ("tasks/send", "message/send"):
        return await a2a_send_task(payload)

    if method == "tasks/get":
        task_id = str(params.get("id") or "")
        inv_id = _A2A_TASK_MAP.get(task_id, task_id)
        manager = get_manager()
        report = manager.get_report(inv_id)
        if not report:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32001, "message": f"Task {task_id} not found"},
            }
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": _report_to_a2a_task(task_id, report),
        }

    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": -32601, "message": f"Unsupported A2A method: {method}"},
    }


@router.get("/a2a/tasks/{task_id}")
async def a2a_get_task(task_id: str) -> Dict[str, Any]:
    """Fetch an A2A Task by its task ID or investigation ID."""
    inv_id = _A2A_TASK_MAP.get(task_id, task_id)
    manager = get_manager()
    report = await manager.wait_for_report(inv_id, timeout=2.0)
    if report is None:
        raise HTTPException(status_code=404, detail=f"A2A Task {task_id} not found")
    return _report_to_a2a_task(task_id, report)
