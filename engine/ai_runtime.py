"""Google AI runtime configuration and observable model execution."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from engine.observability import emit_log, increment_metric

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIRuntimeStatus:
    provider: str
    mode: str
    configured: bool
    models: tuple[str, ...]
    fallback_reason: str | None = None


class AIRuntime:
    """One configured Google GenAI client with explicit execution provenance."""

    def __init__(self) -> None:
        self._client: Any = None
        self._status = self._configure()
        self.calls: list[dict[str, Any]] = []

    @staticmethod
    def _configure() -> AIRuntimeStatus:
        use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"1", "true", "yes"}
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        api_key = os.getenv("GOOGLE_API_KEY")

        if use_vertex and project:
            # Vertex mode is valid only when Application Default Credentials
            # can be discovered.  Do not advertise a live provider when the
            # container merely has a project string but no credential chain.
            try:
                import google.auth  # type: ignore[import]

                google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            except Exception as exc:
                reason = "Vertex AI requested but Application Default Credentials are unavailable"
                logger.warning("%s: %s", reason, type(exc).__name__)
                return AIRuntimeStatus(
                    provider="none",
                    mode="fallback",
                    configured=False,
                    models=(),
                    fallback_reason=reason,
                )
            return AIRuntimeStatus(
                provider="vertex_ai",
                mode="vertex_ai",
                configured=True,
                models=("gemini-2.5-flash", "gemini-2.5-pro"),
            )
        if api_key:
            return AIRuntimeStatus(
                provider="google_genai",
                mode="api_key",
                configured=True,
                models=("gemini-2.5-flash", "gemini-2.5-pro"),
            )

        reason = "Set GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT, or GOOGLE_API_KEY."
        logger.warning("Google AI is not configured; using deterministic fallback. %s", reason)
        return AIRuntimeStatus(
            provider="none",
            mode="fallback",
            configured=False,
            models=(),
            fallback_reason=reason,
        )

    @property
    def status(self) -> AIRuntimeStatus:
        return self._status

    def client(self) -> Any | None:
        if self._client is not None:
            return self._client
        if not self._status.configured:
            return None
        try:
            from google import genai  # type: ignore[import]

            if self._status.mode == "vertex_ai":
                self._client = genai.Client(
                    vertexai=True,
                    project=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID"),
                    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                )
            else:
                self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
            return self._client
        except (ImportError, KeyError, RuntimeError, ValueError) as exc:
            logger.error("Google AI client initialization failed; switching to fallback: %s", exc)
            self._status = AIRuntimeStatus(
                provider="none",
                mode="fallback",
                configured=False,
                models=(),
                fallback_reason=f"Client initialization failed: {exc}",
            )
            return None

    async def generate_json(
        self,
        *,
        model: str,
        prompt: str,
        config: Any,
        operation: str,
    ) -> str | None:
        bounded_prompt = prompt[: int(os.getenv("TRIAGEPILOT_MAX_MODEL_INPUT_CHARS", "12000"))]
        if len(prompt) > len(bounded_prompt):
            logger.warning("Model input exceeded configured size and was truncated")
        client = self.client()
        if client is None:
            self.calls.append({
                "operation": operation,
                "model": model,
                "provider": self._status.provider,
                "mode": "fallback",
                "latency_ms": 0,
                "outcome": "fallback",
                "fallback_reason": self._status.fallback_reason,
            })
            increment_metric("model_fallbacks")
            return None

        loop = asyncio.get_running_loop()

        def call() -> Any:
            return client.models.generate_content(
                model=model,
                contents=bounded_prompt,
                config=config,
            )

        try:
            started = time.perf_counter()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, call),
                timeout=float(os.getenv("TRIAGEPILOT_MODEL_TIMEOUT_SECONDS", "25")),
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            text = getattr(response, "text", None)
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Model returned an empty response")
            self.calls.append({
                "operation": operation,
                "model": model,
                "provider": self._status.provider,
                "mode": self._status.mode,
                "latency_ms": latency_ms,
                "outcome": "success",
            })
            increment_metric("model_calls")
            increment_metric("model_latency_ms", latency_ms)
            emit_log(
                logger,
                "Google AI model call completed",
                operation=operation,
                provider=self._status.provider,
                model=model,
                latency_ms=latency_ms,
                outcome="success",
            )
            return text.strip()
        except Exception as exc:
            raw_err = str(exc).strip() or type(exc).__name__
            safe_error = re.sub(r"(?i)(token|key|secret|password)\s*[=:]\s*\S+", r"\1=[REDACTED]", raw_err)[:500]
            logger.error("Google AI operation %s failed: %s", operation, safe_error)
            self.calls.append({
                "operation": operation,
                "model": model,
                "provider": self._status.provider,
                "mode": "fallback",
                "latency_ms": 0,
                "outcome": "fallback",
                "error": safe_error,
                "fallback_reason": f"{operation} failed: {safe_error}",
            })
            increment_metric("model_fallbacks")
            emit_log(
                logger,
                "Google AI model call fell back",
                operation=operation,
                provider=self._status.provider,
                model=model,
                outcome="fallback",
                fallback=True,
                error=safe_error,
                level=logging.WARNING,
            )
            return None

    async def generate_multimodal_json(
        self,
        *,
        model: str,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        config: Any,
        operation: str,
    ) -> str | None:
        bounded_prompt = prompt[: int(os.getenv("TRIAGEPILOT_MAX_MODEL_INPUT_CHARS", "12000"))]
        client = self.client()
        if client is None or not image_bytes:
            self.calls.append({
                "operation": operation,
                "model": model,
                "provider": self._status.provider,
                "mode": "fallback",
                "latency_ms": 0,
                "outcome": "fallback",
                "fallback_reason": self._status.fallback_reason or "No image bytes or unconfigured client",
            })
            increment_metric("model_fallbacks")
            return None

        loop = asyncio.get_running_loop()

        def call() -> Any:
            from google.genai import types  # type: ignore[import]

            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            return client.models.generate_content(
                model=model,
                contents=[image_part, bounded_prompt],
                config=config,
            )

        try:
            started = time.perf_counter()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, call),
                timeout=float(os.getenv("TRIAGEPILOT_MODEL_TIMEOUT_SECONDS", "25")),
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            text = getattr(response, "text", None)
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Model returned an empty multimodal response")
            self.calls.append({
                "operation": operation,
                "model": model,
                "provider": self._status.provider,
                "mode": self._status.mode,
                "latency_ms": latency_ms,
                "outcome": "success",
            })
            increment_metric("model_calls")
            increment_metric("model_latency_ms", latency_ms)
            emit_log(
                logger,
                "Google AI multimodal model call completed",
                operation=operation,
                provider=self._status.provider,
                model=model,
                latency_ms=latency_ms,
                outcome="success",
            )
            return text.strip()
        except Exception as exc:
            raw_err = str(exc).strip() or type(exc).__name__
            safe_error = re.sub(r"(?i)(token|key|secret|password)\s*[=:]\s*\S+", r"\1=[REDACTED]", raw_err)[:500]
            logger.error("Google AI multimodal operation %s failed: %s", operation, safe_error)
            self.calls.append({
                "operation": operation,
                "model": model,
                "provider": self._status.provider,
                "mode": "fallback",
                "latency_ms": 0,
                "outcome": "fallback",
                "error": safe_error,
                "fallback_reason": f"{operation} failed: {safe_error}",
            })
            increment_metric("model_fallbacks")
            return None


_runtime = AIRuntime()


def get_ai_runtime() -> AIRuntime:
    return _runtime

