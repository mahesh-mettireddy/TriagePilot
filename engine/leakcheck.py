r"""
engine/leakcheck.py
-------------------
Deterministic scan of the customer-facing reply draft BEFORE it is returned
to the caller.

Detects leakage of internal artefacts that must never reach the customer:
  - Internal file paths   (e.g. app/transfers/cutoff.py, *.py references)
  - Stack-trace lines     (Traceback, File "...", line N, in <module>)
  - Internal hostnames    (localhost, *.internal, *.local, *.corp)
  - Raw git SHAs          (40-char hex strings)
  - Raw numeric IDs that look like internal record IDs (format: [A-Z]+-\d{4,})

If the draft fails the check, the caller MUST either:
  1. Regenerate the draft (once), or
  2. Mark the response as `needs_human_edit = True`.

Usage:
    result = check_customer_reply(draft_text)
    if not result.passed:
        # handle regeneration / flag
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Leak Detection Patterns
# ---------------------------------------------------------------------------

_LEAK_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Internal file paths: anything containing "app/" followed by .py / .js / .ts etc.
    ("internal_file_path", re.compile(
        r"\bapp/[\w/]+\.\w+",
        re.IGNORECASE,
    )),
    # Any bare .py filename reference (e.g. cutoff.py, calculator.py)
    ("python_file_reference", re.compile(
        r"\b\w+\.py\b",
        re.IGNORECASE,
    )),
    # Python stack-trace indicators
    ("stack_trace", re.compile(
        r"(Traceback \(most recent call last\)|"
        r'File "[^"]+", line \d+|'
        r"in <module>|"
        r"raise \w+Error)",
        re.IGNORECASE,
    )),
    # Internal hostnames / service-mesh addresses
    ("internal_hostname", re.compile(
        r"\b(localhost|127\.0\.0\.1|"
        r"[\w\-]+\.internal|"
        r"[\w\-]+\.local|"
        r"[\w\-]+\.corp|"
        r"[\w\-]+\.svc\.cluster\.local)\b",
        re.IGNORECASE,
    )),
    # Raw git SHA (40 hex chars, standalone)
    ("raw_git_sha", re.compile(
        r"\b[0-9a-f]{40}\b",
        re.IGNORECASE,
    )),
    # Short git SHA (7–12 hex chars surrounded by word boundaries)
    ("short_git_sha", re.compile(
        r"\b[0-9a-f]{7,12}\b",
        re.IGNORECASE,
    )),
    # Internal ticket / record IDs that look like TXN-1234, INC-9999, CHG-401
    ("internal_record_id", re.compile(
        r"\b(TXN|INC|CHG|KE|REQ|CR|JIRA|BUG|LOG)-\d{3,}\b",
        re.IGNORECASE,
    )),
]


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class LeakCheckResult:
    passed: bool
    notes: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_customer_reply(draft: str) -> LeakCheckResult:
    """
    Scan *draft* for any internal artefacts that must not reach the customer.

    Returns a :class:`LeakCheckResult`.  ``passed=True`` means the draft is
    safe to send; ``passed=False`` means it must be regenerated or flagged.

    The check is conservative: any partial match triggers a failure.
    """
    if not draft or not draft.strip():
        # Empty draft — trivially passes but note it
        return LeakCheckResult(passed=True, notes=["Draft is empty"])

    notes: list[str] = []
    matched: list[str] = []

    for label, pattern in _LEAK_PATTERNS:
        hits = pattern.findall(draft)
        if hits:
            # Deduplicate hits for the note
            unique_hits = list(dict.fromkeys(str(h) for h in hits))[:3]  # show max 3
            notes.append(
                f"[{label}] Detected internal artefact(s): {', '.join(unique_hits)}"
            )
            matched.append(label)

    passed = len(notes) == 0
    return LeakCheckResult(passed=passed, notes=notes, matched_patterns=matched)


def sanitize_or_flag(draft: str) -> tuple[str, LeakCheckResult]:
    """
    Attempt a best-effort sanitization of *draft* by redacting known patterns.

    This is a secondary safety net — the primary path is LLM regeneration.
    Returns ``(sanitized_draft, result_after_sanitization)``.

    If after sanitization the draft still fails, the caller must set
    ``needs_human_edit = True``.
    """
    working = draft
    for label, pattern in _LEAK_PATTERNS:
        if label in ("raw_git_sha", "short_git_sha"):
            working = pattern.sub("[REF_REDACTED]", working)
        elif label in ("internal_file_path", "python_file_reference"):
            working = pattern.sub("[FILE_REDACTED]", working)
        elif label == "stack_trace":
            working = pattern.sub("[TRACE_REDACTED]", working)
        elif label == "internal_hostname":
            working = pattern.sub("[HOST_REDACTED]", working)
        elif label == "internal_record_id":
            # Record IDs like TXN-2041 are sometimes legitimately customer-visible
            # if the customer already provided them — keep but do not auto-expose new ones.
            pass

    result = check_customer_reply(working)
    return working, result
