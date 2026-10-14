"""
eval/runner.py
--------------
Automated evaluation test runner across the 8 Golden Scenarios.
Runs all scenarios through the engine pipeline and measures precision,
citation accuracy, and hallucination reduction.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from engine.orchestrator import get_manager
from engine.schemas import InvestigationCreateRequest
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


async def run_scenario_eval(scenario_id: str) -> Dict[str, Any]:
    manager = get_manager()
    req = InvestigationCreateRequest(scenario_id=scenario_id, mode="live")
    inv_id = await manager.start_investigation(req)

    # Wait for investigation to finish (wait for report)
    for _ in range(60):
        report = manager.get_report(inv_id)
        if report is not None:
            break
        await asyncio.sleep(0.1)

    if report is None:
        raise TimeoutError(f"Investigation {inv_id} for {scenario_id} did not finish in time")

    truth = GOLDEN_SCENARIOS_TRUTH.get(scenario_id, {})
    return compute_scenario_metrics(report, truth)


async def run_all_evals() -> Dict[str, Any]:
    results = []
    for sc_id in GOLDEN_SCENARIOS_TRUTH:
        try:
            res = await run_scenario_eval(sc_id)
            results.append(res)
        except Exception as exc:
            results.append({
                "scenario_id": sc_id,
                "error": str(exc),
                "root_cause_hit": False,
                "citation_validity": 0.0,
            })

    aggregate = aggregate_benchmark_metrics(results)
    return {
        "scenario_results": results,
        "summary": aggregate,
    }
