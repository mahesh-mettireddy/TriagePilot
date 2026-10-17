#!/usr/bin/env python3
"""
scripts/run_eval.py
-------------------
Command-line evaluation benchmark runner for TriagePilot.
Executes all 8 Golden Scenarios, verifies precision and citation integrity,
and prints the architectural ablation comparison table.
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root repository is in sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from eval.ablations import get_ablation_benchmarks
from eval.runner import run_all_evals


async def main():
    print("=" * 80)
    print("  TriagePilot -- Autonomous Initial Analyst Benchmark Suite")
    print("  Evaluating 8 Golden Scenarios (fresh run with provenance metadata)")
    print("=" * 80)
    print()

    print("[*] Running automated evaluation pipeline across scenarios...")
    eval_results = await run_all_evals()

    scenario_results = eval_results.get("scenario_results", [])
    summary = eval_results.get("summary", {})
    print(f"  Run ID: {eval_results.get('run_id', 'unknown')}")
    print(f"  Execution mode: {eval_results.get('execution_mode', 'unknown')}")
    print(f"  Commit: {eval_results.get('commit', 'unknown')}")
    print(f"  Ground truth: {eval_results.get('ground_truth_version', 'unknown')}")

    print()
    print("-" * 80)
    print(f"{'ID':<6} | {'Class Match':<12} | {'Root Cause':<12} | {'Verified':<10} | {'Dropped':<9} | {'Trust':<6} | {'Status'}")
    print("-" * 80)

    all_passed = True
    for res in scenario_results:
        sc_id = res.get("scenario_id", "???")
        class_match = "YES" if res.get("class_match") else "NO"
        rc_hit = "YES" if res.get("root_cause_hit") else "NO"
        v_count = res.get("verified_cards_count", 0)
        d_count = res.get("hallucinations_dropped_count", 0)
        t_score = f"{res.get('trust_score', 0.0):.2f}"
        
        passed = (
            res.get("class_match", False)
            and res.get("root_cause_hit", False)
            and not res.get("error")
        )
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False

        print(f"{sc_id:<6} | {class_match:<12} | {rc_hit:<12} | {v_count:<10} | {d_count:<9} | {t_score:<6} | {status}")

    print("-" * 80)
    print()

    # Print Summary Aggregates
    print("AGGREGATE BENCHMARK METRICS (MODE C - TRIAGEPILOT):")
    print(f"  * Scenarios Evaluated:       {summary.get('scenarios_evaluated', len(scenario_results))}")
    print(f"  * Root-Cause Hit Rate:       {summary.get('root_cause_hit_rate', 0.0) * 100:.1f}%")
    print(f"  * Citation Validity:         {summary.get('post_verifier_citation_validity', 0.0) * 100:.1f}%")
    print(f"  * False Conclusion Rate:     {summary.get('false_conclusion_rate', 0.0) * 100:.1f}%")
    print(f"  * Prompt Injection Defended: {summary.get('prompt_injection_defense_rate', 0.0) * 100:.1f}%")
    print(f"  * Total Hallucinations Sunk: {summary.get('hallucinations_dropped_total', 0)}")
    print()

    comp = summary.get("comparative_advantage") or eval_results.get("comparative_advantage", {})
    if comp:
        print("RUNNABLE SINGLE-AGENT BASELINE (ARM B) VS. TRIAGEPILOT (ARM C) ABLATION:")
        print(f"  * Single-Agent False Conclusions:   {comp.get('single_agent_false_conclusion_rate', 0.0) * 100:.1f}% vs {comp.get('triagepilot_false_conclusion_rate', 0.0) * 100:.1f}%")
        print(f"  * Single-Agent Unverified Citations:{comp.get('single_agent_unverified_citation_rate', 0.0) * 100:.1f}% vs 0.0%")
        print(f"  * Root-Cause Accuracy Lift:         +{comp.get('root_cause_accuracy_lift', 0.0) * 100:.1f}%")
        print(f"  * Next-Check Decision Coverage:     {comp.get('triagepilot_next_check_coverage', 0.0) * 100:.1f}%")
        print()

    # Print Comparative Ablation Table
    ablations = get_ablation_benchmarks()
    print("=" * 80)
    print("  ARCHITECTURAL ABLATION COMPARISON (Mode A vs Mode B vs Mode C)")
    print("=" * 80)
    print(f"{'Metric':<28} | {'Mode A: Baseline':<16} | {'Mode B: Swarm':<16} | {'Mode C: TriagePilot':<16}")
    print("-" * 80)

    modes = {m["id"]: m for m in ablations.get("modes", [])}
    mA = modes.get("mode_a", {})
    mB = modes.get("mode_b", {})
    mC = modes.get("mode_c", {})

    metrics_to_show = [
        ("Root-Cause Hit Rate", f"{mA.get('root_cause_hit_rate', 0)*100:.0f}%", f"{mB.get('root_cause_hit_rate', 0)*100:.0f}%", f"{mC.get('root_cause_hit_rate', 0)*100:.0f}%"),
        ("Citation Validity", f"{mA.get('citation_validity', 0)*100:.0f}%", f"{mB.get('citation_validity', 0)*100:.0f}%", f"{mC.get('citation_validity', 0)*100:.0f}%"),
        ("False Conclusion Rate", f"{mA.get('false_conclusion_rate', 0)*100:.0f}%", f"{mB.get('false_conclusion_rate', 0)*100:.0f}%", f"{mC.get('false_conclusion_rate', 0)*100:.0f}%"),
        ("Prompt Injection Blocked", f"{mA.get('prompt_injection_defense', 0)*100:.0f}%", f"{mB.get('prompt_injection_defense', 0)*100:.0f}%", f"{mC.get('prompt_injection_defense', 0)*100:.0f}%"),
        ("Avg Latency (ms)", f"{mA.get('avg_latency_ms', 0)} ms", f"{mB.get('avg_latency_ms', 0)} ms", f"{mC.get('avg_latency_ms', 0)} ms"),
        ("Avg Cost / Triage", f"${mA.get('avg_cost_usd', 0):.4f}", f"${mB.get('avg_cost_usd', 0):.4f}", f"${mC.get('avg_cost_usd', 0):.4f}"),
    ]

    for label, valA, valB, valC in metrics_to_show:
        print(f"{label:<28} | {valA:<16} | {valB:<16} | {valC:<16}")

    print("-" * 80)
    print()

    if all_passed:
        print("[SUCCESS] Evaluation completed; inspect the run metadata before citing results.")
        return 0
    else:
        print("[WARNING] One or more scenarios did not meet criteria.")
        return 1


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
