"""
api/main.py
-----------
FastAPI application for TriagePilot.
Exposes the complete REST & SSE API for the React Cockpit and evaluation suite.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

import yaml
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sse_starlette.sse import EventSourceResponse

import engine.audit as audit
from api.a2a import router as a2a_router
from api.ratelimit import limiter
from api.sse import event_generator
from engine.adapters.live_adapter import (
    execute_live_demo_transaction,
    get_connectors_health,
    get_live_issues,
    reset_live_workspace,
    sync_live_workspace,
)
from engine.adk_orchestration import ADK_AVAILABLE, describe_adk_swarm
from engine.orchestrator import InvestigationManager, get_manager
from engine.ai_runtime import get_ai_runtime
from engine.persistence import get_investigation_store
from engine.observability import configure_structured_logging
from engine.schemas import (
    AuditChainEntry,
    HumanDecision,
    InvestigationCreateRequest,
    ReportOutput,
)
from eval.ablations import get_ablation_benchmarks
from eval.runner import GOLDEN_SCENARIOS_TRUTH, run_all_evals

logger = logging.getLogger("triagepilot.api")
configure_structured_logging()

app = FastAPI(
    title="TriagePilot API",
    description="Autonomous Initial Analyst & Evidentiary Bridge Backend",
    version="1.0.0",
)

app.include_router(a2a_router)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS setup.  Credentials and wildcard origins are intentionally not
# combined; production supplies TRIAGEPILOT_CORS_ORIGINS as a comma-separated
# allow-list.
_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "TRIAGEPILOT_CORS_ORIGINS", "http://localhost:5173,http://localhost:8080"
    ).split(",")
    if origin.strip()
]
if "*" in _cors_origins:
    raise RuntimeError("TRIAGEPILOT_CORS_ORIGINS must not contain '*' when credentials are enabled")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized JSON/attachment requests before parsing them."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        max_bytes = int(os.getenv("TRIAGEPILOT_MAX_REQUEST_BYTES", "65536"))
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request exceeds {max_bytes} byte limit"},
            )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_UI_DIST = _REPO_ROOT / "ui" / "dist"
_PROFILE_PATH = _REPO_ROOT / "profiles" / "transfers.yaml"

# Fallback profile if Member 2's transfers.yaml hasn't been merged
_FALLBACK_PROFILE: Dict[str, Any] = {
    "app_name": "TransfersDemoApp",
    "version": "1.0.0",
    "product": "transfers",
    "team_mappings": {
        "transfers": "team-payments",
        "fees": "team-core-ledger",
        "notifications": "team-comms",
        "limits": "team-risk",
        "settlement": "team-treasury",
    },
    "pii_rules": {
        "mask_email": True,
        "mask_phone": True,
        "mask_account": True,
        "mask_pan": True,
        "mask_ifsc": True,
        "mask_aadhaar": True,
    },
    "budgets": {
        "max_tool_calls": 12,
        "insufficient_info_cap": 3,
    },
}

SCENARIOS_METADATA = [
    {
        "id": "S01",
        "order": 1,
        "severity": "P1",
        "module": "transfers",
        "title": "Same-day transfers rejected after 4 PM IST",
        "ticket_class": "CODE_DEFECT",
        "tags": ["CODE_DEFECT", "TIME_MISMATCH"],
        "description": "Cutoff time check compared UTC instead of converting to Asia/Kolkata (IST).",
        "default_steer": "Inspect app/transfers/cutoff.py around is_before_cutoff() and verify UTC vs Asia/Kolkata (IST) timezone comparison.",
        "default_client_reply": "Rejection occurred at 4:02 PM IST on transfer TXN-1009 with error code CUTOFF_EXCEEDED.",
    },
    {
        "id": "S02",
        "order": 2,
        "severity": "P2",
        "module": "fees",
        "title": "Fee off by 0.01 on transfer TXN-2041",
        "ticket_class": "DATA_ISSUE",
        "tags": ["DATA_ISSUE", "RECORD_SNAPSHOT"],
        "description": "Binary float rounding drift in fee calculation instead of Decimal math.",
        "default_steer": "Check app/fees/calculator.py for IEEE-754 float rounding vs Decimal quantization on TXN-2041.",
        "default_client_reply": "Principal was INR 803.40 at 1.25% tier; ledger charged INR 10.05 instead of INR 10.04.",
    },
    {
        "id": "S03",
        "order": 3,
        "severity": "P1",
        "module": "transfers",
        "title": "Duplicate debit + Prompt Injection Guard",
        "ticket_class": "CODE_DEFECT",
        "tags": ["CODE_DEFECT", "PROMPT_INJECTION"],
        "description": "Missing idempotency key verification with adversarial instruction override in ticket.",
        "default_steer": "Inspect app/transfers/idempotency.py for missing cache lookup before debit execution on TXN-3011/TXN-3012.",
        "default_client_reply": "Both TXN-3011 and TXN-3012 were submitted within 400ms from the web portal.",
    },
    {
        "id": "S04",
        "order": 4,
        "severity": "P2",
        "module": "notifications",
        "title": "Beneficiary SMS never sent + Stale Runbook",
        "ticket_class": "CODE_DEFECT",
        "tags": ["BEHAVIOUR_MISMATCH", "STALE_DOC", "LOG_INJECTION"],
        "description": "SMS retry loop removed in code while runbook DOC-SMS-01 still promised 3 automatic retries.",
        "default_steer": "Compare app/notifications/sms.py git diff against runbook DOC-SMS-01#retry_policy for stale retry claims.",
        "default_client_reply": "Transfer TXN-4015 settled at 15:35 IST but beneficiary never received the SMS alert.",
    },
    {
        "id": "S06",
        "order": 5,
        "severity": "P2",
        "module": "limits",
        "title": "Transfer blocked at INR 1,00,000 + Vision OCR",
        "ticket_class": "CODE_DEFECT",
        "tags": ["CODE_DEFECT", "VISION_OCR", "BOUNDARY_BUG"],
        "description": "Strict >= vs > daily limit boundary check in daily_limit.py with attached UI error screenshot.",
        "default_steer": "Inspect app/limits/daily_limit.py boundary operator (>= vs >) against policy DOC-LIMITS-01 and ignore unrelated httpx bump.",
        "default_client_reply": "Attached portal screenshot showing TXN-6001 blocked at exactly INR 1,00,000.00 with zero prior transfers today.",
    },
    {
        "id": "S09",
        "order": 6,
        "severity": "P3",
        "module": "settlement",
        "title": "Bank-holiday NEFT settlement delay (KE-104)",
        "ticket_class": "KNOWN_ERROR",
        "tags": ["KNOWN_ERROR", "FAST_PATH"],
        "description": "NEFT holiday batch delay matching Known Error KE-104; router prunes Code and Record agents.",
        "default_steer": "Verify Known Error KE-104 match in HistoryAgent for BATCH-901 and confirm next-business-day settlement.",
        "default_client_reply": "Batch BATCH-901 was submitted on a regional clearing holiday at 09:15 IST.",
    },
    {
        "id": "S10",
        "order": 7,
        "severity": "P4",
        "module": "beneficiary",
        "title": "How to add an international beneficiary",
        "ticket_class": "HOW_TO_USER_ERROR",
        "tags": ["HOW_TO_USER_ERROR", "AGENT_PRUNING"],
        "description": "User how-to inquiry; router activates only KnowledgeAgent and prunes Logs, Code, and Record agents.",
        "default_steer": "Retrieve step-by-step international IBAN/SWIFT onboarding guide from DOC-BEN-02.",
        "default_client_reply": "We are trying to add a UK GBP vendor using SWIFT and IBAN on the corporate portal.",
    },
    {
        "id": "S11",
        "order": 8,
        "severity": "P2",
        "module": "transfers",
        "title": "Underspecified ticket -> Abstain -> Turn-2 Resume",
        "ticket_class": "INSUFFICIENT_INFO",
        "tags": ["INSUFFICIENT_INFO", "ABSTAIN_RESUME"],
        "description": "Vague ticket triggers principled abstention (Trust 0.22); client reply resumes to full root cause.",
        "default_steer": "After client supplies TXN-1009 and 4:15 PM IST timestamp, verify cutoff.py UTC vs IST defect.",
        "default_client_reply": "Happened at 4:15 PM IST on same-day transfer TXN-1009. Rejected with CUTOFF_EXCEEDED.",
    },
]


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for Cloud Run and uptime probes."""
    return {"status": "ok"}


@app.get("/readyz")
async def readiness_check() -> Dict[str, Any]:
    """Report dependency configuration without exposing credentials."""
    runtime = get_ai_runtime()
    store = get_investigation_store()
    requested_execution = os.getenv("TRIAGEPILOT_EXECUTION_MODE", "development").lower()
    live_required = requested_execution == "live"
    ai_ready = not live_required or runtime.status.mode in {"vertex_ai", "api_key"}
    ready = ai_ready and store.ready
    payload = {
        "status": "ok" if ready else "not_ready",
        "ai_mode": runtime.status.mode,
        "ai_configured": runtime.status.configured,
        "execution_mode": requested_execution,
        "ai_ready": ai_ready,
        "persistence": store.mode,
        "persistence_requested": store.requested_mode,
        "persistence_ready": store.ready,
        "persistence_error": store.error,
        "audit": audit.backend_status(),
    }
    if not ready:
        return JSONResponse(status_code=503, content=payload)  # type: ignore[return-value]
    return payload


@app.post("/api/investigations", status_code=202)
@limiter.limit("60/minute")
async def create_investigation(
    request: Request,
    body: InvestigationCreateRequest,
    wait: bool = False,
) -> Dict[str, str]:
    """
    Start a new investigation (live or replay mode). Returns the investigation ID.
    If wait=True, waits for completion before returning.
    """
    manager = get_manager()
    inv_id = await manager.start_investigation(body, wait=wait)
    return {"id": inv_id}


@app.get("/api/investigations/{investigation_id}/events")
async def stream_events(
    request: Request,
    investigation_id: str,
) -> EventSourceResponse:
    """
    Stream SSE events for the given investigation in real time.
    """
    manager = get_manager()
    try:
        after_seq = int(request.headers.get("last-event-id", "0") or "0")
    except ValueError:
        after_seq = 0
    queue = manager.register_listener(investigation_id, after_seq=max(0, after_seq))
    return EventSourceResponse(
        event_generator(queue),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/investigations/{investigation_id}")
async def get_investigation_report(
    investigation_id: str,
) -> ReportOutput:
    """
    Fetch the completed ReportOutput for an investigation.
    """
    manager = get_manager()
    report = await manager.wait_for_report(investigation_id)
    if report is None:
        error = manager.get_error(investigation_id)
        if error:
            raise HTTPException(
                status_code=500,
                detail=f"Investigation {investigation_id} failed: {error}",
            )
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found or still processing.")
    return report


@app.post("/api/investigations/{investigation_id}/decision")
async def record_decision(
    investigation_id: str,
    decision: HumanDecision,
) -> ReportOutput:
    """
    Record operator maker-checker decision: approved, edited, or rejected.
    If approved, executes WritePort mutations.
    """
    manager = get_manager()
    try:
        updated_report = await manager.apply_decision(investigation_id, decision)
        return updated_report
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/scenarios")
async def list_scenarios() -> List[Dict[str, Any]]:
    """List the 8 Golden Scenarios with tags, metadata, and authentic customer ticket text."""
    import json
    enriched: List[Dict[str, Any]] = []
    for item in SCENARIOS_METADATA:
        entry = dict(item)
        ticket_file = _REPO_ROOT / "data" / "bundles" / item["id"] / "ticket.json"
        if ticket_file.exists():
            try:
                tdata = json.loads(ticket_file.read_text(encoding="utf-8"))
                entry["ticket_id"] = tdata.get("id", f"TCK-{item['id']}")
                entry["created_at"] = tdata.get("created_at")
                entry["channel"] = tdata.get("channel", "portal")
                entry["product_hint"] = tdata.get("product_hint", entry.get("module", "transfers"))
                entry["ticket_text"] = tdata.get("text", item["description"])
                entry["attachments"] = tdata.get("attachments", [])
            except Exception:
                entry["ticket_id"] = f"TCK-{item['id']}"
                entry["ticket_text"] = item["description"]
        else:
            entry["ticket_id"] = f"TCK-{item['id']}"
            entry["ticket_text"] = item["description"]
        enriched.append(entry)
    return enriched


@app.get("/api/bundles/{scenario_id}/attachments/{filename}")
async def get_bundle_attachment(scenario_id: str, filename: str) -> Response:
    """Serve visual evidence attachments (e.g. S06 screenshot.png) with strict path validation."""
    import re as _re
    from fastapi.responses import FileResponse

    if not _re.fullmatch(r"S\d{2}", scenario_id) or not _re.fullmatch(
        r"[\w\-]+\.(?:png|jpg|jpeg|webp)", filename, _re.IGNORECASE
    ):
        raise HTTPException(status_code=400, detail="Invalid scenario or attachment filename.")
    bundle_dir = (_REPO_ROOT / "data" / "bundles" / scenario_id).resolve()
    target = (bundle_dir / filename).resolve()
    if bundle_dir not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found.")
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return FileResponse(str(target), media_type=media_type)


@app.get("/api/profile")
async def get_system_profile() -> Dict[str, Any]:
    """Return the active system profile configuration."""
    if _PROFILE_PATH.exists():
        try:
            return yaml.safe_load(_PROFILE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _FALLBACK_PROFILE


@app.get("/api/eval/results")
async def get_eval_results() -> Dict[str, Any]:
    """Return comparative A/B/C ablation benchmarks."""
    return get_ablation_benchmarks()


@app.post("/api/eval/run")
async def run_evaluation_suite(
    execution_mode: Literal["live_evaluation", "replay_evaluation"] = "live_evaluation",
) -> Dict[str, Any]:
    """Execute a freshly identified live or replay evaluation run."""
    results = await run_all_evals(execution_mode=execution_mode)
    return results


@app.get("/api/audit/verify")
async def verify_audit_chain() -> Dict[str, Any]:
    """
    Verify the cryptographic integrity of the SHA-256 hash-chained audit log.
    """
    return audit.verify_chain()


@app.get("/api/audit/chain")
async def get_audit_chain(
    investigation_id: Optional[str] = None,
) -> List[AuditChainEntry]:
    """Fetch all audit chain entries, optionally filtered by investigation ID."""
    return audit.get_chain(investigation_id)


@app.get("/api/connectors/status")
async def connectors_status() -> Dict[str, Any]:
    """Return live health of all 6 Hexagonal Ports, Git workspace SHA, ADK swarm, and A2A protocol."""
    health = get_connectors_health()
    health["adk"] = describe_adk_swarm()
    health["a2a"] = {
        "enabled": True,
        "protocol_version": "0.2.1",
        "agent_card_url": "/.well-known/agent.json",
        "task_endpoint": "/a2a/tasks/send",
    }
    return health


@app.post("/api/live/sync")
async def sync_live_repo(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Synchronize any edits in transfers-demo-app/app/ into the live Git repository."""
    commit_msg = (payload or {}).get("commit_message") if isinstance(payload, dict) else None
    return sync_live_workspace(commit_message=commit_msg)


@app.post("/api/live/trigger")
async def trigger_live_transaction(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a live transaction against transfers-demo-app/app (hot-reloading any
    edited Python files), emit structured JSONL logs & masked records, and return
    a pre-formatted incident ticket payload ready for live investigation.
    """
    body = payload or {}
    amount = float(body.get("amount", 100000.0))
    transfer_type = str(body.get("transfer_type", "same_day"))
    tier = str(body.get("tier", "standard"))
    sender_account = str(body.get("sender_account", "918273645501"))
    beneficiary_account = str(body.get("beneficiary_account", "102938475610"))
    simulate_utc_hour = body.get("simulate_utc_hour")
    if simulate_utc_hour is not None:
        simulate_utc_hour = int(simulate_utc_hour)

    result = execute_live_demo_transaction(
        amount=amount,
        transfer_type=transfer_type,
        tier=tier,
        sender_account=sender_account,
        beneficiary_account=beneficiary_account,
        simulate_utc_hour=simulate_utc_hour,
    )
    txn_id = result["transfer_id"]
    if not result["ok"]:
        suggested_ticket = (
            f"Customer transfer {txn_id} for INR {amount:,.2f} from account {sender_account} "
            f"was rejected with {result.get('error_type')}: '{result.get('error_message')}'. "
            f"Please investigate the root cause across live logs, ledger state, and recent commits."
        )
    else:
        fee = result.get("fee", 0.0)
        expected_fee = round(amount * (0.02 if tier == "express" else 0.0125), 2)
        if abs(fee - expected_fee) >= 0.01:
            suggested_ticket = (
                f"Customer reported incorrect fee deduction on transfer {txn_id} (account {sender_account}): "
                f"principal INR {amount:,.2f} ({tier} tier) was charged fee INR {fee:,.2f} instead of expected INR {expected_fee:,.2f}."
            )
        else:
            suggested_ticket = (
                f"Customer inquiry regarding transfer {txn_id} for INR {amount:,.2f} (fee INR {fee:,.2f}) "
                f"from account {sender_account}. Verify execution trace and recent service changes."
            )

    result["suggested_ticket"] = suggested_ticket
    return result


@app.get("/api/live/issues")
async def list_live_issues() -> List[Dict[str, Any]]:
    """Return all engineering issues persisted via LiveWriteAdapter."""
    return get_live_issues()


@app.post("/api/live/reset")
async def reset_live_repo(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Reset the live Git workspace to the clean baseline commit."""
    restore = bool((payload or {}).get("restore_demo_app_files", False))
    return reset_live_workspace(restore_demo_app_files=restore)


# Single-container Cloud Run static file serving
if _UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")

