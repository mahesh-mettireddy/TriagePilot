"""
eval/tests/test_api.py
----------------------
Integration tests for FastAPI endpoints in api/main.py.
Uses FastAPI TestClient to test REST and SSE functionality.
"""

from __future__ import annotations

import time
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine.schemas import DecisionBand, PolicyAction

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_runtime_configuration():
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ai_mode"] in {"fallback", "vertex_ai", "api_key"}
    assert data["persistence"] in {"memory", "firestore"}
    assert isinstance(data["audit"], str)


def test_list_scenarios():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 8
    scenario_ids = [s["id"] for s in scenarios]
    for expected in ["S01", "S02", "S03", "S04", "S06", "S09", "S10", "S11"]:
        assert expected in scenario_ids


def test_get_profile():
    response = client.get("/api/profile")
    assert response.status_code == 200
    profile = response.json()
    assert "app_name" in profile or "version" in profile


def test_get_eval_results():
    response = client.get("/api/eval/results")
    assert response.status_code == 200
    data = response.json()
    assert "modes" in data
    assert len(data["modes"]) == 3
    mode_ids = [m["id"] for m in data["modes"]]
    assert "mode_a" in mode_ids
    assert "mode_b" in mode_ids
    assert "mode_c" in mode_ids


def test_audit_verify():
    response = client.get("/api/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert data["valid"] is True


def test_investigation_lifecycle():
    # 1. Start investigation
    payload = {
        "scenario_id": "S09",
        "mode": "live",
    }
    resp = client.post("/api/investigations?wait=true", json=payload)
    assert resp.status_code == 202
    inv_id = resp.json()["id"]
    assert inv_id.startswith("INV-")

    # 2. Poll until report is ready
    report = None
    for _ in range(50):
        r = client.get(f"/api/investigations/{inv_id}")
        if r.status_code == 200:
            report = r.json()
            break
        time.sleep(0.1)

    assert report is not None
    assert report["investigation_id"] == inv_id
    assert report["verified_claims_count"] > 0
    assert "leak_check" in report
    assert report["execution"]["mode"] in {"fallback", "vertex_ai", "api_key", "replay"}
    assert "provider" in report["execution"]

    # 3. Check audit chain
    chain_resp = client.get(f"/api/audit/chain?investigation_id={inv_id}")
    assert chain_resp.status_code == 200
    entries = chain_resp.json()
    assert len(entries) >= 2

    # 4. Operator decision: approve
    decision_payload = {
        "status": "approved",
        "by": "lead-engineer@bank.com",
        "reason": "Verified cutoff calculation defect in cutoff.py",
        "report_revision": report["report_revision"],
        "report_hash": report["report_hash"],
        "decision_id": "decision-test-api-001",
    }
    dec_resp = client.post(f"/api/investigations/{inv_id}/decision", json=decision_payload)
    assert dec_resp.status_code == 200
    updated_report = dec_resp.json()
    assert updated_report["decision"]["status"] == "approved"
    assert updated_report["decision"]["write_back_ref"] is not None


def test_nonexistent_investigation_404():
    response = client.get("/api/investigations/INV-NONEXISTENT")
    assert response.status_code == 404


def test_bundle_attachment_serving_and_security():
    resp = client.get("/api/bundles/S06/attachments/screenshot.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")

    bad_ext = client.get("/api/bundles/S06/attachments/ticket.json")
    assert bad_ext.status_code == 400

    missing = client.get("/api/bundles/S06/attachments/missing.png")
    assert missing.status_code == 404


def test_s06_visual_evidence_and_s03_injection_quarantine():
    s06_resp = client.post("/api/investigations?wait=true", json={"scenario_id": "S06", "mode": "live"})
    assert s06_resp.status_code == 202
    s06_id = s06_resp.json()["id"]
    s06_report = client.get(f"/api/investigations/{s06_id}").json()
    vis_cards = [c for c in s06_report["verified_cards"] if c["source_type"] == "visual"]
    assert len(vis_cards) == 1
    assert vis_cards[0]["pointer"]["image_url"] == "/api/bundles/S06/attachments/screenshot.png"

    s03_resp = client.post("/api/investigations?wait=true", json={"scenario_id": "S03", "mode": "live"})
    assert s03_resp.status_code == 202
    s03_id = s03_resp.json()["id"]
    s03_report = client.get(f"/api/investigations/{s03_id}").json()
    for card in s03_report["verified_cards"] + s03_report["dropped_cards"]:
        assert "ignore previous instructions" not in card["snippet"].lower()
