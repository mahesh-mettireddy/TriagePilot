"""Structured Cloud Logging compatible telemetry for ProofTriage.

The application deliberately keeps this module dependency-light.  JSON records
are emitted through the normal Python logging pipeline, so Cloud Run can collect
them without an agent.  A small in-process counter is retained for readiness
and judge diagnostics; production deployments may additionally export the same
measurements through Cloud Monitoring when configured.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import Counter
from typing import Any


_SENSITIVE_KEY = re.compile(r"(token|secret|password|api[_-]?key|credential|authorization)", re.I)
_PII = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:\+?\d[\d\s-]{8,}\d)|\b\d{10,16}\b|\b[A-Z]{5}\d{4}[A-Z]\b)",
    re.I,
)


def _safe(value: Any, key: str = "") -> Any:
    if _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _safe(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v, key) for v in value]
    if isinstance(value, str):
        return _PII.sub("[PII_REDACTED]", value)[:4000]
    return value


class CloudJsonFormatter(logging.Formatter):
    """Format records as one-line structured JSON accepted by Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": time.time(),
        }
        for field in (
            "investigation_id",
            "scenario_id",
            "operation",
            "provider",
            "model",
            "latency_ms",
            "tokens",
            "cost_usd",
            "outcome",
            "fallback",
            "error",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(_safe(payload), sort_keys=True, default=str)


_metrics = Counter()
_metrics_lock = threading.Lock()


def configure_structured_logging() -> None:
    """Install JSON formatting once when explicitly requested or on Cloud Run."""
    if os.getenv("TRIAGEPILOT_JSON_LOGS", "true").lower() not in {"1", "true", "yes"}:
        return
    root = logging.getLogger()
    if any(isinstance(handler.formatter, CloudJsonFormatter) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(CloudJsonFormatter())
    root.addHandler(handler)
    root.setLevel(os.getenv("TRIAGEPILOT_LOG_LEVEL", "INFO").upper())


def emit_log(
    logger: logging.Logger,
    message: str,
    *,
    investigation_id: str | None = None,
    scenario_id: str | None = None,
    operation: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    tokens: int | None = None,
    cost_usd: float | None = None,
    outcome: str | None = None,
    fallback: bool = False,
    error: str | None = None,
    level: int = logging.INFO,
    **kwargs: Any,
) -> None:
    extra = {
        "investigation_id": investigation_id,
        "scenario_id": scenario_id,
        "operation": operation,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "cost_usd": cost_usd,
        "outcome": outcome,
        "fallback": fallback,
        "error": error,
        **kwargs,
    }
    logger.log(level, _safe(message), extra=extra)


def increment_metric(name: str, value: int = 1) -> None:
    with _metrics_lock:
        _metrics[name] += value


def metrics_snapshot() -> dict[str, int]:
    with _metrics_lock:
        return dict(_metrics)


def reset_metrics() -> None:
    with _metrics_lock:
        _metrics.clear()
