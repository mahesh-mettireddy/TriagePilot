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
from typing import Any, Optional


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

    # 7. Commonly labelled customer names.  This intentionally requires a
    # label so ordinary prose and product names are not destroyed.
    (re.compile(
        r"(?i)\b(?:name|customer|user|reporter)\s*[:=-]\s*"
        r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}"
    ), "[NAME_REDACTED]"),

    # Common prose forms and honorifics.  These stay deliberately narrow so
    # product names and ordinary capitalised words are not blanket-redacted.
    (re.compile(
        r"(?i)\b(?:my\s+name\s+is|customer\s+is|reporter\s+is)\s+"
        r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}"
    ), "[NAME_REDACTED]"),
    (re.compile(
        r"\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"
    ), "[NAME_REDACTED]"),

    # 8. Obfuscated national/account identifiers such as 1234-XX-9012 or
    # 12XX 34XX 9012.  Do not match transaction IDs or ordinary words.
    (re.compile(r"\b(?:\d{2,4}[ -]?X{2,4}[ -]?\d{2,4}(?:[ -]?X{2,4})?)\b", re.I), "[ID_REDACTED]"),
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


def mask_for_model(text: str, *, max_chars: int = 12000) -> str:
    """Return bounded, deterministic-safe text for every model/provider call."""
    if not text:
        return ""
    return scrub_pii(text[:max_chars]).masked_text


def quarantine_prompt_injection(text: str, *, max_chars: int = 12000) -> str:
    """Mask PII and replace instruction-like phrases with inert markers.

    Detection remains available to policy code through :func:`detect_prompt_injection`;
    this helper is only for model-boundary content so untrusted source text is
    treated as data rather than executable instructions.
    """
    safe = mask_for_model(text, max_chars=max_chars)
    for phrase in _INJECTION_PHRASES:
        safe = re.sub(re.escape(phrase), "[INJECTION_QUARANTINED]", safe, flags=re.IGNORECASE)
    return safe


def redact_evidence_for_output(cards: list[Any]) -> list[Any]:
    """Copy evidence cards and remove PII before reports or API responses.

    Verification runs before this function and therefore still validates the
    source's original snippet.  The returned copies retain the proof pointer,
    card ID, and verifier status while masking claim/snippet text and any
    pointer values that could contain a sensitive field.
    """
    redacted: list[Any] = []
    for card in cards:
        try:
            clone = card.model_copy(deep=True)
            clone.snippet = quarantine_prompt_injection(clone.snippet, max_chars=400)
            clone.claim = quarantine_prompt_injection(clone.claim, max_chars=200)
            clone.pointer = {
                str(key): mask_for_model(str(value), max_chars=200)
                if key not in {"line_start", "line_end"}
                else value
                for key, value in clone.pointer.items()
            }
            redacted.append(clone)
        except AttributeError:
            redacted.append(card)
    return redacted
