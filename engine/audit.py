"""
engine/audit.py
---------------
SHA-256 hash-chained audit log with optional Firestore persistence.

Every pipeline step is recorded as an :class:`AuditChainEntry`.  Each entry
hashes itself against the *previous* entry's hash, creating a tamper-evident
chain:

    entry.hash = SHA256(prev_hash || canonical_json(entry_payload))

Persistence backends (selected automatically):
  1. Firestore — if ``FIRESTORE_PROJECT`` env var is set and the Firestore
     client initialises without error.
  2. Local JSON file — if ``AUDIT_LOG_PATH`` env var is set (default:
     ``./audit_chain.json``).
  3. In-memory list — fallback for tests / standalone runs.

Public API
----------
    append(investigation_id, step, payload_summary) -> AuditChainEntry
    verify_chain()                                   -> dict
    get_chain(investigation_id?)                     -> list[AuditChainEntry]
    reset()                                          # test helper only
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from engine.schemas import AuditChainEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GENESIS_HASH = "0" * 64  # The hash of the virtual "block 0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: dict[str, Any]) -> str:
    """Produce a deterministic JSON string (sorted keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    """SHA-256 of ``prev_hash || canonical_json(payload)``."""
    raw = (prev_hash + _canonical_json(payload)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Storage backends
# ---------------------------------------------------------------------------

class _InMemoryStore:
    """Simple thread-safe in-memory store."""

    def __init__(self) -> None:
        self._entries: list[AuditChainEntry] = []
        self._lock = threading.Lock()

    def append(self, entry: AuditChainEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def all(self) -> list[AuditChainEntry]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class _JsonFileStore:
    """Append-only JSON-lines file store."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: AuditChainEntry) -> None:
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(entry.model_dump_json() + "\n")

    def all(self) -> list[AuditChainEntry]:
        with self._lock:
            if not self._path.exists():
                return []
            entries: list[AuditChainEntry] = []
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        entries.append(AuditChainEntry.model_validate_json(line))
            return entries

    def clear(self) -> None:
        with self._lock:
            if self._path.exists():
                self._path.write_text("", encoding="utf-8")


class _FirestoreStore:
    """Firestore-backed store (lazy initialisation)."""

    def __init__(self, project: str) -> None:
        # Lazy import so the module doesn't crash if google-cloud-firestore
        # is not installed or credentials are missing.
        from google.cloud import firestore  # type: ignore[import]

        self._db = firestore.Client(project=project)
        self._col = self._db.collection("audit_chain")
        self._lock = threading.Lock()

    def append(self, entry: AuditChainEntry) -> None:
        with self._lock:
            doc_id = f"{entry.seq:010d}_{entry.investigation_id}"
            self._col.document(doc_id).set(entry.model_dump(mode="json"))

    def all(self) -> list[AuditChainEntry]:
        with self._lock:
            docs = self._col.order_by("seq").stream()
            return [AuditChainEntry(**d.to_dict()) for d in docs]

    def clear(self) -> None:
        # Only used in tests; deletes all docs in the collection.
        with self._lock:
            for doc in self._col.stream():
                doc.reference.delete()


# ---------------------------------------------------------------------------
# AuditLog singleton
# ---------------------------------------------------------------------------

class AuditLog:
    """
    Thread-safe, hash-chained audit log.

    Instantiated once at module level as :data:`audit_log`.
    Use :func:`append`, :func:`verify_chain`, and :func:`get_chain` directly.
    """

    def __init__(self) -> None:
        self._store = self._build_store()
        self._seq_lock = threading.Lock()
        self._seq: int = self._load_next_seq()

    # ------------------------------------------------------------------
    # Backend selection
    # ------------------------------------------------------------------

    @staticmethod
    def _build_store() -> _InMemoryStore | _JsonFileStore | _FirestoreStore:
        fs_project = os.environ.get("FIRESTORE_PROJECT")
        if fs_project:
            try:
                return _FirestoreStore(project=fs_project)
            except Exception:
                pass  # Fall through to JSON / memory

        audit_path = os.environ.get("AUDIT_LOG_PATH", "")
        if audit_path:
            return _JsonFileStore(Path(audit_path))

        # Default: JSON file alongside the project root for easy inspection
        default_path = Path(os.environ.get("AUDIT_LOG_PATH", "audit_chain.json"))
        return _JsonFileStore(default_path)

    def _load_next_seq(self) -> int:
        existing = self._store.all()
        return (existing[-1].seq + 1) if existing else 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(
        self,
        investigation_id: str,
        step: str,
        payload_summary: dict[str, Any],
    ) -> AuditChainEntry:
        """
        Append a new entry to the audit chain and return it.

        Thread-safe. Computes ``hash = SHA256(prev_hash || canonical_json(payload))``.
        """
        with self._seq_lock:
            seq = self._seq
            ts = _utc_now()

            existing = self._store.all()
            prev_hash = existing[-1].hash if existing else _GENESIS_HASH

            payload_for_hash = {
                "seq": seq,
                "ts": ts,
                "investigation_id": investigation_id,
                "step": step,
                "payload_summary": payload_summary,
            }
            entry_hash = _compute_hash(prev_hash, payload_for_hash)

            entry = AuditChainEntry(
                seq=seq,
                ts=ts,
                investigation_id=investigation_id,
                step=step,
                payload_summary=payload_summary,
                prev_hash=prev_hash,
                hash=entry_hash,
            )
            self._store.append(entry)
            self._seq += 1

        return entry

    def verify_chain(self) -> dict[str, Any]:
        """
        Verify the integrity of the entire hash chain.

        Returns::

            {
                "valid": bool,
                "entries_checked": int,
                "first_broken_seq": int | None,
                "message": str,
            }
        """
        entries = self._store.all()
        if not entries:
            return {
                "valid": True,
                "entries_checked": 0,
                "first_broken_seq": None,
                "message": "Chain is empty",
            }

        prev_hash = _GENESIS_HASH
        for entry in entries:
            payload_for_hash = {
                "seq": entry.seq,
                "ts": entry.ts,
                "investigation_id": entry.investigation_id,
                "step": entry.step,
                "payload_summary": entry.payload_summary,
            }
            expected = _compute_hash(prev_hash, payload_for_hash)
            if entry.prev_hash != prev_hash or entry.hash != expected:
                return {
                    "valid": False,
                    "entries_checked": entry.seq,
                    "first_broken_seq": entry.seq,
                    "message": f"Chain broken at seq={entry.seq}",
                }
            prev_hash = entry.hash

        return {
            "valid": True,
            "entries_checked": len(entries),
            "first_broken_seq": None,
            "message": f"100% Tamper-Evident Chain Intact ({len(entries)} entries verified)",
        }

    def get_chain(
        self,
        investigation_id: Optional[str] = None,
    ) -> list[AuditChainEntry]:
        """
        Return all audit entries, optionally filtered by *investigation_id*.
        """
        all_entries = self._store.all()
        if investigation_id:
            return [e for e in all_entries if e.investigation_id == investigation_id]
        return all_entries

    def reset(self) -> None:
        """
        Clear all entries.  **For testing only — never call in production.**
        """
        self._store.clear()
        with self._seq_lock:
            self._seq = 1


# ---------------------------------------------------------------------------
# Module-level singleton + convenience functions
# ---------------------------------------------------------------------------

audit_log = AuditLog()


def append(
    investigation_id: str,
    step: str,
    payload_summary: dict[str, Any],
) -> AuditChainEntry:
    """Append an entry to the global :data:`audit_log`."""
    return audit_log.append(investigation_id, step, payload_summary)


def verify_chain() -> dict[str, Any]:
    """Verify the global :data:`audit_log` chain integrity."""
    return audit_log.verify_chain()


def get_chain(investigation_id: Optional[str] = None) -> list[AuditChainEntry]:
    """Return entries from the global :data:`audit_log`."""
    return audit_log.get_chain(investigation_id)
