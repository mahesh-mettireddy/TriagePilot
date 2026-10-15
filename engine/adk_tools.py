"""Typed, read-only ADK tool contracts backed by the hexagonal ports.

The functions are intentionally small and return bounded structured data.  They
are suitable as native Google ADK function tools when the optional ADK runtime
is installed, while the deterministic specialist implementations remain the
portable execution path for tests and replay.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool = True
    source: str
    records: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    truncated: bool = False
    error: str | None = None


def _bounded(source: str, records: list[dict[str, Any]], limit: int = 20) -> ToolResult:
    return ToolResult(
        source=source,
        records=records[:limit],
        truncated=len(records) > limit,
    )


def history_tool(adapter: Any, query: str) -> dict[str, Any]:
    return _bounded("history", adapter.similar_tickets(query, limit=3)).model_dump(mode="json")


def knowledge_tool(adapter: Any, query: str) -> dict[str, Any]:
    return _bounded("knowledge", adapter.search_docs(query, limit=4)).model_dump(mode="json")


def logs_tool(adapter: Any, scenario_id: str) -> dict[str, Any]:
    return _bounded("logs", adapter.query_logs(scenario_id, filters={"level": "ERROR"}, limit=5)).model_dump(mode="json")


def code_tool(adapter: Any, query: str) -> dict[str, Any]:
    return _bounded("code", adapter.search_code(query, limit=5)).model_dump(mode="json")


def record_tool(adapter: Any, scenario_id: str, transfer_id: str) -> dict[str, Any]:
    record = adapter.get_transfer_record(scenario_id, transfer_id)
    return _bounded("record", [record] if record else []).model_dump(mode="json")


def bind_tool(function: Any, adapter: Any) -> Any:
    """Bind a port adapter so ADK sees only model-supplied scalar arguments."""
    def bound(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return function(adapter, *args, **kwargs)

    bound.__name__ = getattr(function, "__name__", "bound_tool")
    bound.__doc__ = getattr(function, "__doc__", None)
    return bound


def bind_history_tool(adapter: Any) -> Any:
    def bound(query: str) -> dict[str, Any]:
        return history_tool(adapter, query)
    bound.__name__ = "history_tool"
    bound.__doc__ = "Retrieve bounded similar tickets for a masked ticket query."
    return bound


def bind_knowledge_tool(adapter: Any) -> Any:
    def bound(query: str) -> dict[str, Any]:
        return knowledge_tool(adapter, query)
    bound.__name__ = "knowledge_tool"
    bound.__doc__ = "Retrieve bounded document summaries for a masked query."
    return bound


def bind_logs_tool(adapter: Any) -> Any:
    def bound(scenario_id: str) -> dict[str, Any]:
        return logs_tool(adapter, scenario_id)
    bound.__name__ = "logs_tool"
    bound.__doc__ = "Retrieve bounded error logs for one scenario identifier."
    return bound


def bind_code_tool(adapter: Any) -> Any:
    def bound(query: str) -> dict[str, Any]:
        return code_tool(adapter, query)
    bound.__name__ = "code_tool"
    bound.__doc__ = "Search the pinned repository for a masked query."
    return bound


def bind_record_tool(adapter: Any) -> Any:
    def bound(scenario_id: str, transfer_id: str) -> dict[str, Any]:
        return record_tool(adapter, scenario_id, transfer_id)
    bound.__name__ = "record_tool"
    bound.__doc__ = "Retrieve one bounded, masked transfer record."
    return bound
