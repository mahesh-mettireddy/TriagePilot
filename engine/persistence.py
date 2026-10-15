"""Durable investigation state with a Firestore adapter and local fallback."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from engine.schemas import ReportOutput, SSEEvent

logger = logging.getLogger(__name__)


class InvestigationStore:
    """Persist reports and ordered events when Firestore is enabled.

    Local development remains process-local by default. Production must opt in
    explicitly with TRIAGEPILOT_PERSISTENCE=firestore and a project setting.
    """

    def __init__(self) -> None:
        self._db: Any = None
        self.requested_mode = os.getenv("TRIAGEPILOT_PERSISTENCE", "memory").lower()
        self.mode = "memory"
        self.error: str | None = None
        if self.requested_mode == "firestore":
            self._configure_firestore()
        self._reports: dict[str, ReportOutput] = {}
        self._events: dict[str, list[SSEEvent]] = {}

    def _configure_firestore(self) -> None:
        project = os.getenv("FIRESTORE_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            logger.error("Firestore persistence requested but no project is configured")
            self.error = "Firestore persistence requested but no project is configured"
            return
        try:
            from google.cloud import firestore  # type: ignore[import]

            self._db = firestore.Client(project=project)
            self.mode = "firestore"
        except (ImportError, RuntimeError, ValueError) as exc:
            logger.error("Firestore initialization failed: %s", exc)
            self.error = f"Firestore initialization failed: {type(exc).__name__}"

    @property
    def ready(self) -> bool:
        return self.requested_mode != "firestore" or self.mode == "firestore"

    def save_report(self, report: ReportOutput) -> None:
        self._reports[report.investigation_id] = report
        if self._db is not None:
            self._db.collection("investigations").document(report.investigation_id).set(
                {"report": report.model_dump(mode="json"), "updated_at": report.metrics.get("updated_at")}
            )

    def get_report(self, investigation_id: str) -> ReportOutput | None:
        report = self._reports.get(investigation_id)
        if report is not None:
            return report
        if self._db is None:
            return None
        snapshot = self._db.collection("investigations").document(investigation_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        raw_report = data.get("report")
        if not raw_report:
            return None
        report = ReportOutput.model_validate(raw_report)
        self._reports[investigation_id] = report
        return report

    def save_event(self, investigation_id: str, event: SSEEvent) -> None:
        self._events.setdefault(investigation_id, []).append(event)
        if self._db is not None:
            self._db.collection("investigations").document(investigation_id).collection("events").document(
                f"{event.seq:010d}"
            ).set(event.model_dump(mode="json"))

    def get_events(self, investigation_id: str) -> list[SSEEvent]:
        events = list(self._events.get(investigation_id, []))
        if events or self._db is None:
            return events
        docs = self._db.collection("investigations").document(investigation_id).collection("events").order_by("seq").stream()
        events = [SSEEvent.model_validate(doc.to_dict()) for doc in docs]
        self._events[investigation_id] = events
        return events


_store = InvestigationStore()


def get_investigation_store() -> InvestigationStore:
    return _store
