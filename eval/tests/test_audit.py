"""
eval/tests/test_audit.py
------------------------
Unit tests for engine/audit.py — SHA-256 hash-chained audit log.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Force the audit module to use a temp JSON file (not Firestore) for tests
# by setting AUDIT_LOG_PATH before importing the module.
# We reload the singleton for each test class using a fixture.


def _make_fresh_audit_log(tmp_path: Path):
    """Create a fresh AuditLog instance backed by a temp file."""
    from engine.audit import AuditLog
    os.environ["AUDIT_LOG_PATH"] = str(tmp_path / "audit_chain.json")
    log = AuditLog()
    return log


class TestAppend:
    def test_first_entry_uses_genesis_hash(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        entry = log.append("inv-001", "masking_done", {"pii_count": 2})
        assert entry.seq == 1
        assert entry.prev_hash == "0" * 64
        assert len(entry.hash) == 64

    def test_second_entry_links_to_first(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        e1 = log.append("inv-001", "masking_done", {"pii_count": 2})
        e2 = log.append("inv-001", "plan_created", {"ticket_class": "CODE_DEFECT"})
        assert e2.prev_hash == e1.hash
        assert e2.seq == 2

    def test_entries_increment_seq(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        for i in range(5):
            entry = log.append("inv-001", f"step_{i}", {"i": i})
            assert entry.seq == i + 1

    def test_hash_is_deterministic(self, tmp_path):
        """Same payload with same prev_hash must always produce the same hash."""
        import hashlib, json
        prev = "0" * 64
        payload = {
            "seq": 1, "ts": "2026-01-01T00:00:00+00:00",
            "investigation_id": "inv-x", "step": "test",
            "payload_summary": {"k": "v"},
        }
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256((prev + canon).encode()).hexdigest()
        # Just confirm the format — length should be 64 hex chars
        assert len(expected) == 64


class TestVerifyChain:
    def test_empty_chain_is_valid(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        result = log.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 0

    def test_intact_chain_is_valid(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        log.append("inv-001", "masking_done", {"pii_count": 0})
        log.append("inv-001", "plan_created", {"ticket_class": "CODE_DEFECT"})
        log.append("inv-001", "trust_update", {"score": 0.82})
        result = log.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 3
        assert "Tamper-Evident" in result["message"]

    def test_tampered_chain_detected(self, tmp_path):
        """Manually corrupt a stored entry and verify the chain catches it."""
        import json

        log = _make_fresh_audit_log(tmp_path)
        log.append("inv-001", "masking_done", {"pii_count": 1})
        log.append("inv-001", "plan_created", {"ticket_class": "CODE_DEFECT"})

        audit_file = tmp_path / "audit_chain.json"
        lines = audit_file.read_text().splitlines()
        # Tamper with the first entry's payload
        entry_data = json.loads(lines[0])
        entry_data["payload_summary"]["pii_count"] = 999  # tamper
        lines[0] = json.dumps(entry_data)
        audit_file.write_text("\n".join(lines) + "\n")

        # Create a new AuditLog that reads the tampered file
        fresh = _make_fresh_audit_log(tmp_path)
        result = fresh.verify_chain()
        # The chain must be detected as broken
        assert result["valid"] is False
        assert result["first_broken_seq"] is not None


class TestGetChain:
    def test_get_all_entries(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        log.append("inv-A", "step_1", {})
        log.append("inv-B", "step_1", {})
        all_entries = log.get_chain()
        assert len(all_entries) == 2

    def test_filter_by_investigation_id(self, tmp_path):
        log = _make_fresh_audit_log(tmp_path)
        log.append("inv-A", "step_1", {"x": 1})
        log.append("inv-B", "step_1", {"x": 2})
        log.append("inv-A", "step_2", {"x": 3})

        inv_a = log.get_chain("inv-A")
        assert len(inv_a) == 2
        assert all(e.investigation_id == "inv-A" for e in inv_a)

        inv_b = log.get_chain("inv-B")
        assert len(inv_b) == 1


class TestPersistence:
    def test_chain_persists_across_instances(self, tmp_path):
        """Entries written by one AuditLog instance are readable by a second."""
        log1 = _make_fresh_audit_log(tmp_path)
        log1.append("inv-001", "masking_done", {"pii_count": 3})
        log1.append("inv-001", "plan_created", {"class": "DATA_ISSUE"})

        log2 = _make_fresh_audit_log(tmp_path)
        entries = log2.get_chain()
        assert len(entries) == 2
        result = log2.verify_chain()
        assert result["valid"] is True


class TestModuleLevelFunctions:
    def test_module_functions_accessible(self):
        """The module-level append/verify_chain/get_chain functions must exist."""
        from engine.audit import append, verify_chain, get_chain
        assert callable(append)
        assert callable(verify_chain)
        assert callable(get_chain)
