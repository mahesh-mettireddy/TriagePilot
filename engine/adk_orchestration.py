"""Registration-only Google ADK specialist contracts.

The installed ADK dependency is intentionally not executed by the portable
pipeline yet.  This module only validates that reusable ADK agents can be
constructed.  Its adapters are always wrapped in the shared :class:`ToolBudget`
before registration, so a future runner cannot bypass the investigation limit.
The deterministic specialist runner remains authoritative until a compatible
ADK Runner and typed EvidenceCard conversion are added.
"""

from __future__ import annotations

import logging
from typing import Any

from engine.adk_tools import (
    bind_code_tool,
    bind_history_tool,
    bind_knowledge_tool,
    bind_logs_tool,
    bind_record_tool,
)
from engine.tool_budget import ToolBudget, budgeted_adapters

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

try:  # pragma: no cover - optional dependency is exercised in cloud images
    from google.adk.agents import Agent, ParallelAgent  # type: ignore[import]

    ADK_AVAILABLE = True
    ADK_NATIVE_PACKAGE = True
except ImportError:  # pragma: no cover - portable ADK contract fallback
    @dataclass
    class Agent:  # type: ignore[no-redef]
        name: str
        model: str = "gemini-2.5-flash"
        instruction: str = ""
        tools: list[Any] = field(default_factory=list)

    @dataclass
    class ParallelAgent:  # type: ignore[no-redef]
        name: str
        sub_agents: list[Any] = field(default_factory=list)

    ADK_AVAILABLE = True
    ADK_NATIVE_PACKAGE = False

# Explicitly prevent callers from interpreting construction as execution.
ADK_REGISTRATION_ONLY = True

_SWARM_DEFINITIONS: dict[str, tuple[Any, str, str, str]] = {
    "HistoryAgent": (
        bind_history_tool,
        "Retrieve bounded similar tickets, Known Errors (KE-*), and deployment change records.",
        "history",
        "history_tool",
    ),
    "KnowledgeAgent": (
        bind_knowledge_tool,
        "Retrieve bounded runbook/architecture document summaries and policy sections.",
        "knowledge",
        "knowledge_tool",
    ),
    "LogsAgent": (
        bind_logs_tool,
        "Retrieve bounded structured error logs and signature digests for the active incident.",
        "logs",
        "logs_tool",
    ),
    "CodeAgent": (
        bind_code_tool,
        "Inspect the pinned Git repository, recent diff hunks, and commit SHAs.",
        "code",
        "code_tool",
    ),
    "RecordAgent": (
        bind_record_tool,
        "Retrieve masked transaction ledger snapshots by reference ID (zero raw SQL).",
        "record",
        "record_tool",
    ),
}


def build_adk_specialist_swarm(
    adapters: dict[str, Any] | None = None,
    active_agents: list[str] | None = None,
    *,
    budget: ToolBudget | None = None,
) -> Any | None:
    """Build a registration-only ADK ParallelAgent swarm with budgeted read-only tools."""
    if not ADK_AVAILABLE:
        return None

    if adapters is None:
        from engine.adapters.fixture_adapter import get_adapters
        adapters = get_adapters()
    if active_agents is None:
        active_agents = list(_SWARM_DEFINITIONS.keys())
    if budget is None:
        budget = ToolBudget(12)

    # Never bind raw adapters into an ADK function tool.  Even though this
    # function is registration-only today, the invariant protects any caller
    # that later wires a Runner around the returned graph.
    gated_adapters = budgeted_adapters(adapters, budget)

    children = []
    for name in active_agents:
        if name not in _SWARM_DEFINITIONS:
            continue
        binder, instruction, adapter_key, _tool_name = _SWARM_DEFINITIONS[name]
        try:
            children.append(
                Agent(
                    name=name,
                    model="gemini-2.5-flash",
                    instruction=instruction,
                    tools=[binder(gated_adapters[adapter_key])],
                )
            )
        except TypeError:
            logger.warning("Installed google-adk version cannot build %s", name)
            return None
    try:
        return ParallelAgent(name="TriagePilotSpecialistSwarm", sub_agents=children)
    except TypeError:
        return None


def describe_adk_swarm(active_agents: list[str] | None = None) -> dict[str, Any]:
    """Return structured metadata describing the Google ADK ParallelAgent topology."""
    selected = set(active_agents) if active_agents is not None else set(_SWARM_DEFINITIONS.keys())
    sub_agents = []
    for name, (_binder, instruction, adapter_key, tool_name) in _SWARM_DEFINITIONS.items():
        sub_agents.append(
            {
                "name": name,
                "model": "gemini-2.5-flash",
                "port": adapter_key,
                "tool": tool_name,
                "max_calls": 3,
                "active_for_ticket": name in selected,
                "instruction": instruction,
            }
        )
    return {
        "adk_available": ADK_AVAILABLE,
        "native_package_installed": ADK_NATIVE_PACKAGE,
        "root_agent": "TriagePilotSpecialistSwarm",
        "agent_type": "ParallelAgent",
        "orchestrator_type": "ParallelAgent",
        "model": "gemini-2.5-flash",
        "total_budget_calls": 12,
        "execution_mode": "registration_only_with_deterministic_verifier",
        "sub_agents": sub_agents,
    }

