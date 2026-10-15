"""
engine/reconcile.py
-------------------
Step 5 of the 12-step pipeline: Deterministic Reconciler.

**Pure Python — ZERO LLM involvement.**

Compares verified EvidenceCards and ticket metadata to emit typed
Contradiction objects:

  TIME_MISMATCH:    |client_claimed_start_utc - first_error_log_utc| > 30 minutes
  STATE_MISMATCH:   Client claimed transfer status != RecordPort status
  STALE_DOC_FLAG:   doc.last_updated < culprit_commit.date
  CHANGE_MISMATCH:  Recent change touched the suspected module

Semantic mismatches (BEHAVIOUR_MISMATCH, SCOPE_MISMATCH) are handled by
the HypothesisAgent in Phase 4b using gemini-2.5-pro.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Optional

from engine.schemas import (
    Contradiction,
    ContradictionKind,
    EvidenceCard,
    SourceType,
    TicketDTO,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Timestamp parsing helper
# ---------------------------------------------------------------------------

def _parse_ts(ts_str: str) -> Optional[datetime]:
    """Best-effort ISO 8601 timestamp parse."""
    if not ts_str:
        return None
    try:
        # Handle Z suffix
        ts_str = ts_str.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(ts_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Individual contradiction checks
# ---------------------------------------------------------------------------

def _check_time_mismatch(
    ticket: TicketDTO,
    verified_cards: list[EvidenceCard],
) -> Optional[Contradiction]:
    """
    TIME_MISMATCH: |client_claimed_start - first_error_log| > 30 minutes.

    Searches for any timestamp in the ticket text and compares to the
    earliest ERROR log card's timestamp.
    """
    import re

    # Extract timestamps from ticket text
    text = ticket.masked_text or ticket.text
    # Match various timestamp formats
    ts_patterns = [
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?",
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)?(?:\s*IST)?",
        r"\d{1,2}:\d{2}\s*(?:AM|PM)\s*IST",
    ]
    client_ts_str = None
    for pattern in ts_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            client_ts_str = match.group(0)
            break

    if not client_ts_str:
        return None

    # Parse client timestamp (best effort).  Relative day/time claims are
    # resolved against the ticket creation date in the ticket's local zone.
    client_dt = _parse_ts(client_ts_str)
    if client_dt is None:
        created_dt = _parse_ts(ticket.created_at)
        if created_dt:
            day_match = re.match(
                r"(?i)(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
                r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s*ist)?",
                client_ts_str,
            )
            time_match = re.match(r"(?i)(\d{1,2}):(\d{2})\s*(am|pm)\s*ist", client_ts_str)
            local_zone = ZoneInfo("Asia/Kolkata") if "ist" in client_ts_str.lower() else created_dt.tzinfo
            local_created = created_dt.astimezone(local_zone or timezone.utc)
            if day_match:
                weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(day_match.group(1).lower())
                days_back = (local_created.weekday() - weekday) % 7
                hour = int(day_match.group(2))
                minute = int(day_match.group(3) or 0)
                meridiem = (day_match.group(4) or "").lower()
                if meridiem == "pm" and hour < 12:
                    hour += 12
                if meridiem == "am" and hour == 12:
                    hour = 0
                candidate_date = local_created.date() - timedelta(days=days_back)
                candidate = datetime(candidate_date.year, candidate_date.month, candidate_date.day, hour, minute, tzinfo=local_zone)
                if candidate > local_created:
                    candidate -= timedelta(days=7)
                client_dt = candidate.astimezone(timezone.utc)
            elif time_match:
                hour = int(time_match.group(1))
                meridiem = time_match.group(3).lower()
                if meridiem == "pm" and hour < 12:
                    hour += 12
                if meridiem == "am" and hour == 12:
                    hour = 0
                candidate = datetime(
                    local_created.year, local_created.month, local_created.day,
                    hour, int(time_match.group(2)), tzinfo=local_zone,
                )
                client_dt = candidate.astimezone(timezone.utc)

    # Find earliest ERROR log card timestamp
    earliest_log_ts: Optional[datetime] = None
    earliest_card_id: Optional[str] = None
    for card in verified_cards:
        if card.source_type == SourceType.LOG:
            card_ts = _parse_ts(card.pointer.get("ts", "") or card.observed_at or "")
            if card_ts:
                if earliest_log_ts is None or card_ts < earliest_log_ts:
                    earliest_log_ts = card_ts
                    earliest_card_id = card.card_id

    if client_dt is None or earliest_log_ts is None:
        return None

    # Compare — |client_ts - first_log_ts| > 30 minutes
    diff = abs((client_dt - earliest_log_ts).total_seconds())
    if diff > 30 * 60:  # 30 minutes
        hours = diff / 3600
        return Contradiction(
            kind=ContradictionKind.TIME_MISMATCH,
            deterministic=True,
            card_a=None,
            card_b=earliest_card_id,
            note=(
                f"Client claims issue started at {client_ts_str}, "
                f"but first error log is at {earliest_log_ts.isoformat()} — "
                f"difference of {hours:.1f} hours (>30 min threshold)"
            ),
        )
    return None


def _check_state_mismatch(
    ticket: TicketDTO,
    verified_cards: list[EvidenceCard],
) -> Optional[Contradiction]:
    """
    STATE_MISMATCH: Client claimed transfer status != RecordPort status.

    Looks for claims like "successful" or "completed" in ticket text
    vs. a RECORD card showing a different status.
    """
    text = (ticket.masked_text or ticket.text).lower()

    # Determine claimed state from ticket text
    client_claims_success = any(
        word in text
        for word in ["successful", "completed", "went through", "was debited"]
    )
    client_claims_failure = any(
        word in text
        for word in ["failed", "rejected", "blocked", "not working", "error"]
    )

    if not client_claims_success and not client_claims_failure:
        return None

    # Find RECORD cards
    for card in verified_cards:
        if card.source_type == SourceType.RECORD:
            snippet_lower = card.snippet.lower()
            actual_status = ""
            if "status=rejected" in snippet_lower or "rejected" in snippet_lower:
                actual_status = "REJECTED"
            elif "status=completed" in snippet_lower or "completed" in snippet_lower:
                actual_status = "COMPLETED"
            elif "status=pending" in snippet_lower or "pending" in snippet_lower:
                actual_status = "PENDING"

            if actual_status:
                mismatch = (
                    (client_claims_success and actual_status == "REJECTED")
                    or (client_claims_failure and actual_status == "COMPLETED")
                )
                if mismatch:
                    claimed = "successful/completed" if client_claims_success else "failed/rejected"
                    return Contradiction(
                        kind=ContradictionKind.STATE_MISMATCH,
                        deterministic=True,
                        card_a=None,
                        card_b=card.card_id,
                        note=(
                            f"Client claims transfer was {claimed}, "
                            f"but record shows status={actual_status}"
                        ),
                    )
    return None


def _check_stale_doc(
    verified_cards: list[EvidenceCard],
) -> list[Contradiction]:
    """
    STALE_DOC_FLAG: doc.last_updated < culprit_commit.date.

    If a DOC card's last_updated timestamp is older than any CODE card's
    commit date, the doc may be stale.
    """
    contradictions: list[Contradiction] = []

    # Find the latest commit date from CODE cards
    latest_commit_ts: Optional[datetime] = None
    latest_code_card_id: Optional[str] = None
    for card in verified_cards:
        if card.source_type == SourceType.CODE and card.observed_at:
            commit_dt = _parse_ts(card.observed_at)
            if commit_dt and (latest_commit_ts is None or commit_dt > latest_commit_ts):
                latest_commit_ts = commit_dt
                latest_code_card_id = card.card_id

    if latest_commit_ts is None:
        return contradictions

    # Check all DOC cards
    for card in verified_cards:
        if card.source_type == SourceType.DOC:
            doc_updated = card.pointer.get("last_updated", "")
            doc_dt = _parse_ts(doc_updated)
            if doc_dt and doc_dt < latest_commit_ts:
                contradictions.append(
                    Contradiction(
                        kind=ContradictionKind.STALE_DOC_FLAG,
                        deterministic=True,
                        card_a=card.card_id,
                        card_b=latest_code_card_id,
                        note=(
                            f"Doc {card.pointer.get('page_id','?')} was last updated "
                            f"{doc_updated}, but code was modified on "
                            f"{latest_commit_ts.isoformat()} — doc may be stale"
                        ),
                    )
                )
    return contradictions


def _check_change_mismatch(
    verified_cards: list[EvidenceCard],
) -> list[Contradiction]:
    """
    CHANGE_MISMATCH: A recent change record touches the same module
    as a code card's suspect file.
    """
    contradictions: list[Contradiction] = []

    # Collect modules from CODE cards
    code_paths: dict[str, str] = {}
    for card in verified_cards:
        if card.source_type == SourceType.CODE:
            path = card.pointer.get("path", "")
            if path:
                code_paths[path] = card.card_id

    # Check TICKET (HistoryAgent) cards that mention change records
    for card in verified_cards:
        if card.source_type == SourceType.TICKET and card.pointer.get("system") == "ITSM":
            snippet = card.snippet.lower()
            for path, code_card_id in code_paths.items():
                if path.lower() in snippet or path.split("/")[-1].lower() in snippet:
                    contradictions.append(
                        Contradiction(
                            kind=ContradictionKind.CHANGE_MISMATCH,
                            deterministic=True,
                            card_a=card.card_id,
                            card_b=code_card_id,
                            note=(
                                f"Change record {card.pointer.get('id','?')} "
                                f"affects module '{path}' which is also implicated in code analysis"
                            ),
                        )
                    )
    return contradictions


# ---------------------------------------------------------------------------
# Main reconciler entry point
# ---------------------------------------------------------------------------

def reconcile(
    ticket: TicketDTO,
    verified_cards: list[EvidenceCard],
) -> list[Contradiction]:
    """
    Run all deterministic reconciliation checks.

    Args:
        ticket:          The masked TicketDTO.
        verified_cards:  Only VERIFIED EvidenceCards (post-verifier).

    Returns:
        List of Contradiction objects found.
    """
    contradictions: list[Contradiction] = []

    # 1. TIME_MISMATCH
    time_c = _check_time_mismatch(ticket, verified_cards)
    if time_c:
        contradictions.append(time_c)

    # 2. STATE_MISMATCH
    state_c = _check_state_mismatch(ticket, verified_cards)
    if state_c:
        contradictions.append(state_c)

    # 3. STALE_DOC_FLAG
    contradictions.extend(_check_stale_doc(verified_cards))

    # 4. CHANGE_MISMATCH
    contradictions.extend(_check_change_mismatch(verified_cards))

    logger.info(
        "Reconciler complete: %d contradictions found (%s)",
        len(contradictions),
        ", ".join(c.kind.value for c in contradictions),
    )

    return contradictions
