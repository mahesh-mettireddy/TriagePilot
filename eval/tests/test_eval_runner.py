"""
eval/tests/test_eval_runner.py
------------------------------
Unit tests for evaluation metrics, ablations, and scenario test runner.
"""

from __future__ import annotations

import pytest
from eval.ablations import get_ablation_benchmarks
from eval.metrics import aggregate_benchmark_metrics, compute_scenario_metrics
from eval.runner import GOLDEN_SCENARIOS_TRUTH, run_scenario_eval


def test_ablation_benchmarks():
    data = get_ablation_benchmarks()
    assert "modes" in data
    assert len(data["modes"]) == 3
    mode_c = next(m for m in data["modes"] if m["id"] == "mode_c")
    assert mode_c["citation_validity"] == 1.00
    assert mode_c["false_conclusion_rate"] == 0.00
    assert mode_c["prompt_injection_defense"] == 1.00


def test_aggregate_metrics():
    sample_results = [
        {
            "scenario_id": "S01",
            "root_cause_hit": True,
            "citation_validity": 1.0,
            "hallucinations_dropped_count": 2,
            "injection_blocked": True,
            "trust_band": "HIGH",
        },
        {
            "scenario_id": "S02",
            "root_cause_hit": True,
            "citation_validity": 1.0,
            "hallucinations_dropped_count": 1,
            "injection_blocked": True,
            "trust_band": "HIGH",
        },
    ]
    summary = aggregate_benchmark_metrics(sample_results)
    assert summary["scenarios_evaluated"] == 2
    assert summary["root_cause_hit_rate"] == 1.0
    assert summary["post_verifier_citation_validity"] == 1.0
    assert summary["false_conclusion_rate"] == 0.0
    assert summary["hallucinations_dropped_total"] == 3


@pytest.mark.asyncio
async def test_run_scenario_eval_s01():
    metrics = await run_scenario_eval("S01")
    assert metrics["scenario_id"] == "S01"
    assert "citation_validity" in metrics
    assert "trust_score" in metrics
    assert metrics["citation_validity"] > 0
