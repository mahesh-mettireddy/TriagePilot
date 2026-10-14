"""
eval/tests/test_ports_adapters.py
----------------------------------
Unit tests for Phase 2: Ports & Adapters.

Tests run fully standalone using built-in fallback mock data —
no /data/ files or git repo required.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from engine.adapters.fixture_adapter import (
    FixtureHistoryAdapter,
    FixtureKnowledgeAdapter,
    FixtureLogAdapter,
    FixtureRecordAdapter,
    FixtureWriteAdapter,
    get_adapters,
)
from engine.ports.base import (
    CodePort,
    HistoryPort,
    KnowledgePort,
    LogPort,
    RecordPort,
    WritePort,
)


# ---------------------------------------------------------------------------
# Confirm all adapters implement their abstract port
# ---------------------------------------------------------------------------

class TestPortInheritance:
    def test_history_adapter_is_history_port(self):
        assert isinstance(FixtureHistoryAdapter(), HistoryPort)

    def test_knowledge_adapter_is_knowledge_port(self):
        assert isinstance(FixtureKnowledgeAdapter(), KnowledgePort)

    def test_log_adapter_is_log_port(self):
        assert isinstance(FixtureLogAdapter(), LogPort)

    def test_record_adapter_is_record_port(self):
        assert isinstance(FixtureRecordAdapter(), RecordPort)

    def test_write_adapter_is_write_port(self):
        assert isinstance(FixtureWriteAdapter(), WritePort)


# ---------------------------------------------------------------------------
# FixtureHistoryAdapter
# ---------------------------------------------------------------------------

class TestHistoryAdapter:
    def setup_method(self):
        self.adapter = FixtureHistoryAdapter()

    def test_similar_tickets_returns_list(self):
        results = self.adapter.similar_tickets("transfer rejected after 4 PM")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_similar_tickets_have_required_fields(self):
        results = self.adapter.similar_tickets("fee calculation issue")
        for t in results:
            assert "id" in t
            assert "title" in t
            assert "resolution" in t

    def test_known_errors_returns_list(self):
        errors = self.adapter.known_errors("pending settlement bank holiday")
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_known_errors_have_ke_id(self):
        errors = self.adapter.known_errors("any query")
        for ke in errors:
            assert "ke_id" in ke
            assert "workaround" in ke

    def test_known_error_ke104_present(self):
        """S09 scenario: KE-104 must be discoverable."""
        errors = self.adapter.known_errors("bank holiday settlement delay pending")
        ke_ids = [ke["ke_id"] for ke in errors]
        assert "KE-104" in ke_ids

    def test_recent_changes_returns_list(self):
        changes = self.adapter.recent_changes("2026-10-01T00:00:00Z", "2026-10-14T00:00:00Z")
        assert isinstance(changes, list)
        assert len(changes) > 0

    def test_recent_changes_have_required_fields(self):
        changes = self.adapter.recent_changes("2026-10-01T00:00:00Z", "2026-10-14T00:00:00Z")
        for c in changes:
            assert "change_id" in c
            assert "modules_affected" in c
            assert "deployed_at" in c


# ---------------------------------------------------------------------------
# FixtureKnowledgeAdapter
# ---------------------------------------------------------------------------

class TestKnowledgeAdapter:
    def setup_method(self):
        self.adapter = FixtureKnowledgeAdapter()

    def test_search_docs_returns_list(self):
        results = self.adapter.search_docs("SMS notification retry")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_docs_have_required_fields(self):
        results = self.adapter.search_docs("beneficiary")
        for doc in results:
            assert "page_id" in doc
            assert "title" in doc
            assert "last_updated" in doc

    def test_search_docs_finds_sms_runbook(self):
        """S04 scenario: DOC-SMS-01 must be discoverable."""
        results = self.adapter.search_docs("SMS notification retry")
        page_ids = [d["page_id"] for d in results]
        assert "DOC-SMS-01" in page_ids

    def test_search_docs_finds_beneficiary_guide(self):
        """S10 scenario: DOC-BEN-02 must be discoverable."""
        results = self.adapter.search_docs("add international beneficiary")
        page_ids = [d["page_id"] for d in results]
        assert "DOC-BEN-02" in page_ids

    def test_get_doc_section_returns_content(self):
        result = self.adapter.get_doc_section("DOC-SMS-01", "retry_policy")
        assert result is not None
        assert result["page_id"] == "DOC-SMS-01"
        assert "content" in result
        assert len(result["content"]) > 0

    def test_get_doc_section_missing_page_returns_none(self):
        result = self.adapter.get_doc_section("DOC-DOES-NOT-EXIST", "any_section")
        assert result is None

    def test_doc_sms01_last_updated_is_stale(self):
        """S04: DOC-SMS-01 last_updated must be before CHG-405 deploy date (2026-10-10)."""
        result = self.adapter.get_doc_section("DOC-SMS-01", "retry_policy")
        assert result is not None
        assert result["last_updated"] < "2026-10-10T00:00:00Z"  # STALE_DOC_FLAG trigger


# ---------------------------------------------------------------------------
# FixtureLogAdapter
# ---------------------------------------------------------------------------

class TestLogAdapter:
    def setup_method(self):
        self.adapter = FixtureLogAdapter()

    def test_query_logs_returns_list(self):
        # "S99" doesn't exist — should return fallback
        logs = self.adapter.query_logs("S99")
        assert isinstance(logs, list)
        assert len(logs) > 0

    def test_logs_have_required_fields(self):
        logs = self.adapter.query_logs("S99")
        for log in logs:
            assert "log_id" in log
            assert "ts" in log
            assert "service" in log
            assert "level" in log
            assert "message" in log

    def test_level_filter(self):
        logs = self.adapter.query_logs("S99", filters={"level": "ERROR"})
        assert all(l["level"].upper() == "ERROR" for l in logs)

    def test_limit_respected(self):
        logs = self.adapter.query_logs("S99", limit=1)
        assert len(logs) <= 1

    def test_digest_signatures_returns_list(self):
        sigs = self.adapter.digest_signatures("S99")
        assert isinstance(sigs, list)

    def test_digest_signatures_fields(self):
        sigs = self.adapter.digest_signatures("S99")
        for sig in sigs:
            assert "signature" in sig
            assert "count" in sig
            assert "sample_log_id" in sig

    def test_trace_lookup_returns_matching_logs(self):
        logs = self.adapter.trace_lookup("S99", "trace-abc123")
        assert isinstance(logs, list)
        for log in logs:
            assert log["trace_id"] == "trace-abc123"

    def test_trace_lookup_nonexistent_trace_returns_empty(self):
        logs = self.adapter.trace_lookup("S99", "trace-nonexistent-xyz")
        assert logs == []

    def test_query_logs_with_real_bundle(self, tmp_path, monkeypatch):
        """Test with a real JSONL file (simulating Member 2's bundle)."""
        bundle_dir = tmp_path / "bundles" / "S01"
        bundle_dir.mkdir(parents=True)
        log_file = bundle_dir / "logs.jsonl"
        test_logs = [
            {"log_id": "L1", "ts": "2026-10-07T10:30:00Z", "service": "transfers",
             "level": "ERROR", "trace_id": "t1", "message": "cutoff error"},
            {"log_id": "L2", "ts": "2026-10-07T10:31:00Z", "service": "api",
             "level": "INFO", "trace_id": "t1", "message": "request received"},
        ]
        log_file.write_text("\n".join(json.dumps(l) for l in test_logs))

        # Patch _BUNDLES_DIR
        import engine.adapters.fixture_adapter as fa
        original = fa._BUNDLES_DIR
        monkeypatch.setattr(fa, "_BUNDLES_DIR", tmp_path / "bundles")
        adapter = FixtureLogAdapter()
        logs = adapter.query_logs("S01")
        assert len(logs) == 2
        monkeypatch.setattr(fa, "_BUNDLES_DIR", original)


# ---------------------------------------------------------------------------
# FixtureRecordAdapter
# ---------------------------------------------------------------------------

class TestRecordAdapter:
    def setup_method(self):
        self.adapter = FixtureRecordAdapter()

    def test_get_known_transfer_record_from_fallback(self):
        record = self.adapter.get_transfer_record("S99", "TXN-1009")
        assert record is not None
        assert record["transfer_id"] == "TXN-1009"
        assert "status" in record
        assert "amount" in record

    def test_get_unknown_transfer_id_returns_none(self):
        record = self.adapter.get_transfer_record("S99", "TXN-DOESNOTEXIST")
        assert record is None

    def test_record_has_no_raw_pii(self):
        """Masked account must be present, not raw account number."""
        record = self.adapter.get_transfer_record("S99", "TXN-1009")
        assert record is not None
        assert "masked_account" in record

    def test_get_record_from_real_bundle(self, tmp_path, monkeypatch):
        """Test reading from a real bundle file."""
        bundle_dir = tmp_path / "bundles" / "S02"
        bundle_dir.mkdir(parents=True)
        snapshot = {"transfer_id": "TXN-2041", "status": "COMPLETED",
                    "amount": 100000.0, "fee": 1250.01,
                    "created_at": "2026-10-05T09:00:00Z",
                    "masked_account": "[ACCT_REDACTED]"}
        (bundle_dir / "record_snapshot.json").write_text(json.dumps(snapshot))

        import engine.adapters.fixture_adapter as fa
        monkeypatch.setattr(fa, "_BUNDLES_DIR", tmp_path / "bundles")
        adapter = FixtureRecordAdapter()
        record = adapter.get_transfer_record("S02", "TXN-2041")
        assert record is not None
        assert record["fee"] == 1250.01


# ---------------------------------------------------------------------------
# FixtureWriteAdapter
# ---------------------------------------------------------------------------

class TestWriteAdapter:
    def setup_method(self):
        self.adapter = FixtureWriteAdapter()

    def test_create_issue_returns_issue_key(self):
        result = self.adapter.create_issue({
            "title": "Test bug",
            "description": "desc",
            "investigation_id": "inv-test",
        })
        assert "issue_key" in result
        assert result["issue_key"].startswith("TRIAGE-")
        assert "url" in result

    def test_post_comment_returns_comment_id(self):
        result = self.adapter.post_comment("INC-9999", "This is a test comment.")
        assert "comment_id" in result
        assert result["comment_id"].startswith("CMT-")


# ---------------------------------------------------------------------------
# get_adapters() factory
# ---------------------------------------------------------------------------

class TestGetAdapters:
    def test_factory_returns_all_adapters(self):
        adapters = get_adapters()
        assert set(adapters.keys()) == {"history", "knowledge", "logs", "code", "record", "write"}

    def test_all_adapters_are_port_instances(self):
        adapters = get_adapters()
        assert isinstance(adapters["history"], HistoryPort)
        assert isinstance(adapters["knowledge"], KnowledgePort)
        assert isinstance(adapters["logs"], LogPort)
        assert isinstance(adapters["record"], RecordPort)
        assert isinstance(adapters["write"], WritePort)
