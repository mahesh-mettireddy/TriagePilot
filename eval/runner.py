"""
eval/runner.py
--------------
Automated evaluation test runner across the 8 Golden Scenarios.
Runs all scenarios through the engine pipeline and measures precision,
citation accuracy, and hallucination reduction.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.orchestrator import get_manager
from engine.schemas import EvaluationRun, InvestigationCreateRequest
from eval.metrics import aggregate_benchmark_metrics, compute_scenario_metrics

GOLDEN_SCENARIOS_TRUTH: Dict[str, Dict[str, Any]] = {
    "S01": {
        "title": "Same-day transfers rejected after 4 PM IST",
        "ticket_class": "CODE_DEFECT",
        "culprit_module": "cutoff.py",
        "expected_contradiction": "TIME_MISMATCH",
        "expected_trust_band": "HIGH",
        "has_injection": False,
    },
    "S02": {
        "title": "Fee off by 0.01 on transfer TXN-2041",
        "ticket_class": "DATA_ISSUE",
        "culprit_module": "calculator.py",
        "expected_trust_band": "HIGH",
        "has_injection": False,
    },
    "S03": {
        "title": "Duplicate debit on double-click + Ticket Prompt Injection",
        "ticket_class": "CODE_DEFECT",
        "culprit_module": "idempotency.py",
        "expected_trust_band": "HIGH",
        "has_injection": True,
    },
    "S04": {
        "title": "Beneficiary SMS never sent + Stale Doc + Log Injection",
        "ticket_class": "CODE_DEFECT",
        "culprit_module": "sms.py",
        "expected_contradiction": "BEHAVIOUR_MISMATCH",
        "expected_trust_band": "HIGH",
        "has_injection": True,
    },
    "S06": {
        "title": "Transfer blocked at boundary + Vision Screenshot",
        "ticket_class": "CODE_DEFECT",
        "culprit_module": "daily_limit.py",
        "expected_trust_band": "HIGH",
        "has_injection": False,
    },
    "S09": {
        "title": "Bank-holiday settlement delay matches Known Error KE-104",
        "ticket_class": "KNOWN_ERROR",
        "culprit_module": None,
        "expected_trust_band": "HIGH",
        "has_injection": False,
    },
    "S10": {
        "title": "How to add an international beneficiary",
        "ticket_class": "HOW_TO_USER_ERROR",
        "culprit_module": None,
        "expected_trust_band": "HIGH",
        "has_injection": False,
    },
    "S11": {
        "title": "Insufficient info -> ABSTAIN -> Client Reply Resume",
        "ticket_class": "INSUFFICIENT_INFO",
        "culprit_module": "cutoff.py",
        "expected_trust_band": "LOW",
        "has_injection": False,
    },
}


async def run_scenario_eval(
    scenario_id: str, *, mode: str = "live"
) -> Dict[str, Any]:
    manager = get_manager()
    req = InvestigationCreateRequest(scenario_id=scenario_id, mode=mode)  # type: ignore[arg-type]
    inv_id = await manager.start_investigation(req)

    # Wait for investigation to finish (wait for report)
    report = None
    for _ in range(60):
        report = manager.get_report(inv_id)
        if report is not None:
            break
        await asyncio.sleep(0.1)

    if report is None:
        raise TimeoutError(f"Investigation {inv_id} for {scenario_id} did not finish in time")

    truth = GOLDEN_SCENARIOS_TRUTH.get(scenario_id, {})
    return compute_scenario_metrics(report, truth)


def _current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _ground_truth_version() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    digest.update(json.dumps(GOLDEN_SCENARIOS_TRUTH, sort_keys=True).encode("utf-8"))
    for scenario_id in sorted(GOLDEN_SCENARIOS_TRUTH):
        for name in ("ticket.json", "ground_truth.yaml"):
            path = root / "data" / "bundles" / scenario_id / name
            if path.exists():
                digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


async def run_all_evals(
    *, execution_mode: str = "live_evaluation"
) -> Dict[str, Any]:
    if execution_mode not in {"live_evaluation", "replay_evaluation"}:
        raise ValueError("execution_mode must be live_evaluation or replay_evaluation")
    results = []
    scenario_mode = "replay" if execution_mode == "replay_evaluation" else "live"
    for sc_id in GOLDEN_SCENARIOS_TRUTH:
        try:
            res = await run_scenario_eval(sc_id, mode=scenario_mode)
            results.append(res)
        except Exception as exc:
            results.append({
                "scenario_id": sc_id,
                "status": "error",
                "error": str(exc),
                "evidence_count": 0,
                "verified_cards_count": 0,
                "dropped_cards_count": 0,
                "root_cause_hit": False,
                "class_match": False,
                "citation_validity": 0.0,
                "abstention": False,
                "false_conclusion": False,
                "latency_ms": 0,
                "cost_usd": 0.0,
            })

    aggregate = aggregate_benchmark_metrics(results)
    models = sorted({model for result in results for model in result.get("models", [])})
    providers = sorted({result.get("provider", "none") for result in results if result.get("provider")})
    run = EvaluationRun(
        run_id=f"EVAL-{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        commit=_current_commit(),
        provider=", ".join(providers) or "none",
        models=models,
        execution_mode=execution_mode,  # type: ignore[arg-type]
        scenario_set=list(GOLDEN_SCENARIOS_TRUTH),
        ground_truth_version=_ground_truth_version(),
        latency_ms=sum(result.get("latency_ms", 0) for result in results),
        cost_usd=sum(result.get("cost_usd", 0.0) for result in results),
        scenario_results=results,
        summary=aggregate,
    )
    return run.model_dump(mode="json")
