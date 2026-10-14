"""
engine/masking.py
-----------------
Deterministic PII scrubber + prompt injection detector.

Runs BEFORE any LLM call — zero LLM involvement here.

PII patterns redacted:
  - Email           -> [EMAIL_REDACTED]
  - Phone (IN)      -> [PHONE_REDACTED]
  - Account number  -> [ACCT_REDACTED]   (10–16 contiguous digits)
  - PAN             -> [PAN_REDACTED]    ([A-Z]{5}[0-9]{4}[A-Z])
  - IFSC            -> [IFSC_REDACTED]   ([A-Z]{4}0[A-Z0-9]{6})
  - 12-digit gov ID -> [Aadhaar Redacted]

Prompt injection phrases detected (case-insensitive):
  "ignore previous instructions", "system override", "ignore all rules",
  "forget your instructions", "disregard previous", "act as",
  "you are now", "jailbreak", "ignore all previous", "new instructions"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# PII Regex Patterns
# Order matters: more-specific patterns should come first.
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 1. Email  (before generic digit patterns)
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[EMAIL_REDACTED]"),

    # 2. PAN card (5 alpha + 4 digits + 1 alpha) — before generic 10-16 digit rule
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[PAN_REDACTED]"),

    # 3. IFSC code ([A-Z]{4}0[A-Z0-9]{6}) — bank branch code
    (re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), "[IFSC_REDACTED]"),

    # 4. Indian phone numbers: 10 digits starting with 6-9, optional +91 / 0 prefix.
    #    Must come BEFORE the Aadhaar/account rules so "+91XXXXXXXXXX" is consumed here.
    (re.compile(r"(?<!\d)(?:\+91[\s\-]?|0)?[6-9]\d{9}(?!\d)"), "[PHONE_REDACTED]"),

    # 5. 12-digit government ID (Aadhaar) — after phone so "+91..." is already masked.
    (re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"), "[Aadhaar Redacted]"),

    # 6. Account numbers: 10–16 contiguous digits (catches bank accounts, card numbers).
    (re.compile(r"\b\d{10,16}\b"), "[ACCT_REDACTED]"),
]

# ---------------------------------------------------------------------------
# Prompt Injection Phrases
# ---------------------------------------------------------------------------
_INJECTION_PHRASES: list[str] = [
    "ignore previous instructions",
    "ignore all previous",
    "ignore all rules",
    "system override",
    "forget your instructions",
    "disregard previous",
    "act as ",           # trailing space avoids matching "act as a" in normal prose
    "you are now",
    "jailbreak",
    "new instructions:",
    "system instruction:",
    "override previous",
    "ignore errors and",
    "mark resolved",
    "output status=",
    "output no_bug",
]


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------
@dataclass
class MaskingResult:
    masked_text: str
    pii_redacted_count: int
    injection_detected: bool
    injection_note: Optional[str] = None
    redacted_types: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrub_pii(text: str) -> MaskingResult:
    """
    Apply all PII regex patterns sequentially to *text*.

    Returns a :class:`MaskingResult` with the masked text and metadata.
    The function is idempotent: running it twice on already-masked text
    will not double-redact (because placeholders no longer match raw patterns).
    """
    working = text
    total_redacted = 0
    redacted_types: list[str] = []

    for pattern, placeholder in _PII_PATTERNS:
        matches = pattern.findall(working)
        if matches:
            total_redacted += len(matches)
            redacted_types.append(placeholder)
            working = pattern.sub(placeholder, working)

    # Deduplicate redacted_types list while preserving order
    seen: set[str] = set()
    unique_types: list[str] = []
    for t in redacted_types:
        if t not in seen:
            seen.add(t)
            unique_types.append(t)

    injected, note = detect_prompt_injection(working)

    return MaskingResult(
        masked_text=working,
        pii_redacted_count=total_redacted,
        injection_detected=injected,
        injection_note=note,
        redacted_types=unique_types,
    )


def detect_prompt_injection(text: str) -> tuple[bool, Optional[str]]:
    """
    Scan *text* for known prompt-injection phrases.

    Returns ``(True, matched_phrase)`` on the first match,
    ``(False, None)`` if clean.

    Operates on lower-cased text so it is case-insensitive.
    """
    lower = text.lower()
    for phrase in _INJECTION_PHRASES:
        if phrase.lower() in lower:
            return True, f"Potential prompt injection detected: '{phrase.strip()}'"
    return False, None


def mask_ticket(text: str) -> MaskingResult:
    """
    Convenience wrapper: scrub PII and detect prompt injection together.

    This is the single entry-point called by the pipeline before any LLM step.
    Raises :class:`ValueError` if *text* is empty.
    """
    if not text or not text.strip():
        raise ValueError("Ticket text must not be empty")
    return scrub_pii(text)
