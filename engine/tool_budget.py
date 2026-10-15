"""Hard per-investigation budget for specialist read-tool invocations."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


MAX_TOOL_CALLS = 12


class ToolBudgetExceeded(RuntimeError):
    """Raised before a port method would exceed the investigation budget."""


class ToolBudget:
    def __init__(self, requested: int) -> None:
        self.limit = max(0, min(int(requested), MAX_TOOL_CALLS))
        self.used = 0
        self.rejections: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def try_acquire(self, agent: str, tool: str) -> bool:
        with self._lock:
            if self.used >= self.limit:
                self.rejections.append(
                    {"agent": agent, "tool": tool, "limit": self.limit, "used": self.used}
                )
                return False
            self.used += 1
            return True


class BudgetedAdapter:
    """Transparent synchronous adapter proxy used inside executor threads.

    A proxy keeps the existing hexagonal port interfaces intact while ensuring
    every actual adapter method invocation consumes a shared, thread-safe unit.
    No model or agent can bypass this gate by issuing another port call.
    """

    def __init__(self, adapter: Any, budget: ToolBudget, agent: str) -> None:
        self._adapter = adapter
        self._budget = budget
        self._agent = agent

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._adapter, name)
        if not callable(target) or name.startswith("_"):
            return target

        def guarded(*args: Any, **kwargs: Any) -> Any:
            if not self._budget.try_acquire(self._agent, name):
                raise ToolBudgetExceeded(
                    f"Tool budget exhausted before {self._agent}.{name}"
                )
            return target(*args, **kwargs)

        return guarded


def budgeted_adapters(adapters: dict[str, Any], budget: ToolBudget) -> dict[str, Any]:
    mapping = {
        "history": "HistoryAgent",
        "knowledge": "KnowledgeAgent",
        "logs": "LogsAgent",
        "code": "CodeAgent",
        "record": "RecordAgent",
    }
    result = dict(adapters)
    for key, agent in mapping.items():
        if key in adapters:
            result[key] = BudgetedAdapter(adapters[key], budget, agent)
    return result
