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
from api.ratelimit import limiter
from api.sse import event_generator
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
        "title": "Same-day transfers rejected after 4 PM IST",
        "ticket_class": "CODE_DEFECT",
        "tags": ["CODE_DEFECT", "TIME_MISMATCH", "DEV_SET"],
        "description": "Cutoff time check compared UTC instead of converting to Asia/Kolkata (IST).",
    },
    {
        "id": "S02",
        "title": "Fee off by 0.01 on transfer TXN-2041",
        "ticket_class": "DATA_ISSUE",
        "tags": ["DATA_ISSUE", "RECORD_AGENT", "DEV_SET"],
        "description": "Binary float rounding drift in fee calculation instead of Decimal math.",
    },
    {
        "id": "S03",
        "title": "Duplicate debit + Prompt Injection",
        "ticket_class": "CODE_DEFECT",
        "tags": ["CODE_DEFECT", "INJECTION", "TEST_SET"],
        "description": "Missing idempotency key verification with injected ticket text.",
    },
    {
        "id": "S04",
        "title": "Beneficiary SMS never sent + Stale Doc + Log Injection",
        "ticket_class": "CODE_DEFECT",
        "tags": ["BEHAVIOUR_MISMATCH", "STALE_DOC", "INJECTION", "DEV_SET"],
        "description": "SMS retry loop removed in code while runbook DOC-SMS-01 still claimed automatic retry.",
    },
    {
        "id": "S06",
        "title": "Transfer blocked at boundary + Vision Screenshot",
        "ticket_class": "CODE_DEFECT",
        "tags": ["CODE_DEFECT", "VISION", "BOUNDARY_BUG", "TEST_SET"],
        "description": "Greater-than vs greater-or-equal daily limit boundary check with error screenshot.",
    },
    {
        "id": "S09",
        "title": "Bank-holiday settlement delay (KE-104)",
        "ticket_class": "KNOWN_ERROR",
        "tags": ["KNOWN_ERROR", "FAST_PATH", "DEV_SET"],
        "description": "NEFT holiday batch delay matching Known Error KE-104; router prunes Code and Record agents.",
    },
    {
        "id": "S10",
        "title": "How to add an international beneficiary",
        "ticket_class": "HOW_TO_USER_ERROR",
        "tags": ["HOW_TO_USER_ERROR", "SMART_ROUTING", "DEV_SET"],
        "description": "User how-to request; router activates only KnowledgeAgent and prunes all others.",
    },
    {
        "id": "S11",
        "title": "Insufficient info -> ABSTAIN -> Client Reply Resume",
        "ticket_class": "INSUFFICIENT_INFO",
        "tags": ["INSUFFICIENT_INFO", "ABSTAIN", "HUMAN_LOOP", "TEST_SET"],
        "description": "Vague ticket causes principled abstention; client followup triggers re-investigation to conclusion.",
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
    """List the 8 Golden Scenarios with tags and metadata."""
    return SCENARIOS_METADATA


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


# Single-container Cloud Run static file serving
if _UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")
