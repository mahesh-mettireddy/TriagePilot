"""
eval/tests/test_leakcheck.py
----------------------------
Unit tests for engine/leakcheck.py — deterministic customer reply
leak scanner.
"""

import pytest
from engine.leakcheck import check_customer_reply, sanitize_or_flag, LeakCheckResult


# ---------------------------------------------------------------------------
# Clean drafts — should PASS
# ---------------------------------------------------------------------------

class TestCleanDrafts:
    def test_plain_customer_reply(self):
        draft = (
            "We have identified the issue and our team is working on a fix. "
            "You should see normal service restored within 2 hours. "
            "We apologise for the inconvenience."
        )
        result = check_customer_reply(draft)
        assert result.passed is True
        assert result.notes == []

    def test_empty_draft_passes(self):
        result = check_customer_reply("")
        assert result.passed is True

    def test_plain_workaround_reply(self):
        draft = (
            "As a workaround, please try initiating the transfer before 4 PM IST. "
            "Our engineering team has been notified."
        )
        result = check_customer_reply(draft)
        assert result.passed is True


# ---------------------------------------------------------------------------
# File path leaks — should FAIL
# ---------------------------------------------------------------------------

class TestFilePathLeaks:
    def test_internal_python_path(self):
        draft = "The bug is in app/transfers/cutoff.py and will be fixed soon."
        result = check_customer_reply(draft)
        assert result.passed is False
        assert any("path" in n or "file" in n.lower() for n in result.notes)

    def test_bare_py_filename(self):
        draft = "We found an issue in calculator.py that caused the fee mismatch."
        result = check_customer_reply(draft)
        assert result.passed is False

    def test_nested_module_path(self):
        draft = "app/notifications/sms.py was recently modified."
        result = check_customer_reply(draft)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Stack trace leaks — should FAIL
# ---------------------------------------------------------------------------

class TestStackTraceLeaks:
    def test_traceback_header(self):
        draft = "Traceback (most recent call last): File transfer.py, line 42"
        result = check_customer_reply(draft)
        assert result.passed is False

    def test_file_line_pattern(self):
        draft = 'File "cutoff.py", line 23, in check_cutoff'
        result = check_customer_reply(draft)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Internal hostname leaks — should FAIL
# ---------------------------------------------------------------------------

class TestHostnameLeaks:
    def test_localhost(self):
        draft = "Please retry connecting to localhost on port 8080."
        result = check_customer_reply(draft)
        assert result.passed is False

    def test_internal_hostname(self):
        draft = "The service is at payments-svc.internal."
        result = check_customer_reply(draft)
        assert result.passed is False

    def test_loopback_ip(self):
        draft = "Service available at 127.0.0.1"
        result = check_customer_reply(draft)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Git SHA leaks — should FAIL
# ---------------------------------------------------------------------------

class TestGitSHALeaks:
    def test_40_char_sha(self):
        sha = "a" * 40
        draft = f"The fix was merged in commit {sha}."
        result = check_customer_reply(draft)
        assert result.passed is False

    def test_short_sha(self):
        draft = "This was introduced in commit abc1234."
        result = check_customer_reply(draft)
        assert result.passed is False


# ---------------------------------------------------------------------------
# LeakCheckResult type tests
# ---------------------------------------------------------------------------

class TestResultType:
    def test_returns_leak_check_result(self):
        result = check_customer_reply("Hello, your issue is resolved.")
        assert isinstance(result, LeakCheckResult)
        assert isinstance(result.passed, bool)
        assert isinstance(result.notes, list)

    def test_matched_patterns_populated_on_failure(self):
        draft = "Check app/transfers/cutoff.py"
        result = check_customer_reply(draft)
        assert result.passed is False
        assert len(result.matched_patterns) > 0


# ---------------------------------------------------------------------------
# sanitize_or_flag helper
# ---------------------------------------------------------------------------

class TestSanitizeOrFlag:
    def test_sanitizes_file_paths(self):
        draft = "The issue is in app/transfers/cutoff.py"
        sanitized, result = sanitize_or_flag(draft)
        assert "app/transfers/cutoff.py" not in sanitized
        assert "[FILE_REDACTED]" in sanitized or "[" in sanitized

    def test_sanitizes_git_sha(self):
        sha = "b" * 40
        draft = f"Fixed in commit {sha}"
        sanitized, result = sanitize_or_flag(draft)
        assert sha not in sanitized

    def test_clean_draft_unchanged(self):
        draft = "Your transfer is being reviewed by our team."
        sanitized, result = sanitize_or_flag(draft)
        assert result.passed is True
