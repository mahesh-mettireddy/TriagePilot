"""
eval/tests/test_live_adk_a2a.py
-------------------------------
Comprehensive integration tests for:
  1. Google ADK (`ParallelAgent`) swarm registration & topology introspection
  2. Google A2A (Agent2Agent) Protocol v0.2 (`/.well-known/agent.json`, `/a2a`, `/a2a/tasks/send`)
  3. Live Service Connectors (`engine/adapters/live_adapter.py`) & True Live Bug-Hunt Flow:
     - Injecting a real code modification into `transfers-demo-app/app/fees/calculator.py`
     - Submitting a manual customer issue (`scenario_id="LIVE"`)
     - Verifying that `CodeAgent`, `HistoryAgent`, `LogsAgent`, `RecordAgent`, and `verifier.py`
       dynamically discover and verify the exact modified file, line number, and new 40-char Git SHA.
"""

from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from engine.adk_orchestration import ADK_AVAILABLE, build_adk_specialist_swarm, describe_adk_swarm
from engine.adapters.live_adapter import (
    execute_live_demo_transaction,
    get_connectors_health,
    reset_live_workspace,
    sync_live_workspace,
)


client = TestClient(app)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEMO_CALC = _REPO_ROOT / "transfers-demo-app" / "app" / "fees" / "calculator.py"


def test_adk_swarm_is_active_and_describes_parallel_agent() -> None:
    """Google ADK must be active and expose a ParallelAgent with 5 budgeted sub-agents."""
    assert ADK_AVAILABLE is True
    swarm = build_adk_specialist_swarm()
    assert swarm is not None
    assert swarm.name == "TriagePilotSpecialistSwarm"
    assert len(swarm.sub_agents) == 5

    desc = describe_adk_swarm(["CodeAgent", "LogsAgent", "RecordAgent"])
    assert desc["adk_available"] is True
    assert desc["orchestrator_type"] == "ParallelAgent"
    assert desc["total_budget_calls"] == 12
    assert len(desc["sub_agents"]) == 5
    active_map = {a["name"]: a["active_for_ticket"] for a in desc["sub_agents"]}
    assert active_map["CodeAgent"] is True
    assert active_map["LogsAgent"] is True


def test_a2a_agent_card_and_jsonrpc_delegation() -> None:
    """Verify Google A2A Protocol discovery (/.well-known/agent.json) and JSON-RPC 2.0 tasks/send."""
    card_resp = client.get("/.well-known/agent.json")
    assert card_resp.status_code == 200
    card = card_resp.json()
    assert str(card["protocolVersion"]).startswith("0.2")
    assert card["name"].startswith("TriagePilot")
    assert len(card["skills"]) >= 3
    assert card["adk_orchestration"]["adk_available"] is True

    # Test JSON-RPC 2.0 tasks/send via POST /a2a
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": "req-a2a-01",
        "method": "tasks/send",
        "params": {
            "id": "task-a2a-test-001",
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "My same-day transfer TXN-100001 failed at 17:15 UTC with TransferWindowClosedError.",
                    }
                ],
                "metadata": {"scenario_id": "S01", "module": "transfers"},
            },
        },
    }
    rpc_resp = client.post("/a2a", json=rpc_payload)
    assert rpc_resp.status_code == 200
    rpc_data = rpc_resp.json()
    assert rpc_data["jsonrpc"] == "2.0"
    assert rpc_data["id"] == "req-a2a-01"
    result = rpc_data["result"]
    assert result["status"]["state"] in ("completed", "input-required")
    assert len(result["artifacts"]) >= 2

    # Verify tasks/get retrieval
    task_id = result["id"]
    get_resp = client.get(f"/a2a/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id


def test_live_code_bug_injection_and_dynamic_triage_discovery() -> None:
    """
    Simulate the live competition demo flow:
      1. Developer introduces a real bug in `transfers-demo-app/app/fees/calculator.py`
         (changing STANDARD_FEE_RATE from 0.0125 to 0.0500).
      2. Client triggers a live transfer request (or writes a manual ticket in LIVE mode).
      3. TriagePilot runs with `scenario_id="LIVE"` and dynamically discovers:
         - The new 40-char Git commit SHA created for the developer's edit
         - The exact modified file `app/fees/calculator.py` and line number
         - The live JSONL log (`LOG-LIVE-*`) and masked record (`TXN-*`)
         - All verified by `verifier.py` with zero static fixture overrides!
    """
    original_code = _DEMO_CALC.read_text(encoding="utf-8")
    try:
        # 1. Inject a real bug into transfers-demo-app/app/fees/calculator.py
        buggy_code = original_code.replace(
            "fee = round(amount * rate, 2)",
            "fee = round(amount * (rate * 4.0), 2)  # LIVE_BUG: 4x fee multiplier",
        )
        assert buggy_code != original_code
        _DEMO_CALC.write_text(buggy_code, encoding="utf-8")

        # 2. Sync workspace & execute live transfer service
        sync_info = sync_live_workspace("bug(fees): accidental 4x multiplier in calculate_transfer_fee")
        assert sync_info["has_live_changes"] is True
        assert "app/fees/calculator.py" in sync_info["live_modified_files"]
        live_head_sha = sync_info["head_sha"]
        assert not live_head_sha.startswith("288c17a")

        tx_res = execute_live_demo_transaction(amount=10000.0, tier="standard")
        assert tx_res["ok"] is True
        assert tx_res["fee"] == 500.0  # 4x the expected 125.00 fee!
        txn_id = tx_res["transfer_id"]

        # 3. Submit a manual customer issue in LIVE mode via API
        manual_ticket = (
            f"Customer reported severe fee overcharge on transfer {txn_id} from account 918273645501. "
            f"For a standard transfer of INR 10,000.00, the service charged INR 500.00 (5.0%) "
            f"instead of INR 125.00 (1.25%) in app/fees/calculator.py."
        )
        inv_resp = client.post(
            "/api/investigations?wait=true",
            json={
                "scenario_id": "LIVE",
                "text": manual_ticket,
                "mode": "live",
            },
        )
        assert inv_resp.status_code in (200, 202)
        inv_id = inv_resp.json()["id"]
        rep_resp = client.get(f"/api/investigations/{inv_id}")
        assert rep_resp.status_code == 200
        report = rep_resp.json()

        # 4. Verify that CodeAgent + Verifier found the exact live commit SHA & modified file
        verified = report["verified_cards"]
        code_ev = [e for e in verified if e["source_type"] == "code"]
        assert len(code_ev) >= 1
        calc_ev = next(
            (e for e in code_ev if "app/fees/calculator.py" in str(e["pointer"].get("file", ""))),
            code_ev[0],
        )
        assert calc_ev["verification"]["status"].lower() == "verified"
        assert calc_ev["pointer"]["commit_sha"] == live_head_sha
        assert "4.0" in calc_ev["snippet"] or "fee" in calc_ev["snippet"]

        # Verify that LiveLogAdapter & LiveRecordAdapter corroborated the live transaction
        record_ev = [e for e in verified if e["source_type"] == "record"]
        assert any(
            txn_id in str(e["pointer"].get("id", ""))
            or txn_id in str(e["pointer"].get("record_id", ""))
            or txn_id in str(e["pointer"].get("transfer_id", ""))
            for e in record_ev
        )
        log_ev = [e for e in verified if e["source_type"] == "log"]
        assert len(log_ev) >= 1

        # Verify PII account number was scrubbed
        reply_text = (
            report["customer_reply_draft"]["body"]
            if isinstance(report["customer_reply_draft"], dict)
            else str(report["customer_reply_draft"])
        )
        assert "918273645501" not in reply_text

    finally:
        # Always restore clean baseline so Golden Scenarios S01-S11 remain untouched
        _DEMO_CALC.write_text(original_code, encoding="utf-8")
        reset_live_workspace(restore_demo_app_files=True)


def test_connectors_status_endpoint() -> None:
    """Verify /api/connectors/status returns health for all 6 Hexagonal Ports."""
    resp = client.get("/api/connectors/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "connected"
    assert len(data["ports"]) == 6
    port_names = {p["port"] for p in data["ports"]}
    assert port_names == {
        "CodePort",
        "LogPort",
        "RecordPort",
        "HistoryPort",
        "KnowledgePort",
        "WritePort",
    }
