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

try:  # pragma: no cover - optional dependency is exercised in cloud images
    from google.adk.agents import Agent, ParallelAgent  # type: ignore[import]

    ADK_AVAILABLE = True
except ImportError:  # pragma: no cover - local test environment
    Agent = Any  # type: ignore[misc,assignment]
    ParallelAgent = Any  # type: ignore[misc,assignment]
ADK_AVAILABLE = False

# Explicitly prevent callers from interpreting construction as execution.
ADK_REGISTRATION_ONLY = True


def build_adk_specialist_swarm(
    adapters: dict[str, Any],
    active_agents: list[str],
    *,
    budget: ToolBudget,
) -> Any | None:
    """Build a registration-only ADK swarm with budgeted read-only tools."""
    if not ADK_AVAILABLE:
        return None

    # Never bind raw adapters into an ADK function tool.  Even though this
    # function is registration-only today, the invariant protects any caller
    # that later wires a Runner around the returned graph.
    gated_adapters = budgeted_adapters(adapters, budget)

    definitions = {
        "HistoryAgent": (bind_history_tool, "Retrieve bounded similar tickets and known-error context.", "history"),
        "KnowledgeAgent": (bind_knowledge_tool, "Retrieve bounded runbook/document summaries.", "knowledge"),
        "LogsAgent": (bind_logs_tool, "Retrieve bounded error logs for one scenario.", "logs"),
        "CodeAgent": (bind_code_tool, "Search the pinned repository and return structured hits.", "code"),
        "RecordAgent": (bind_record_tool, "Retrieve one masked transfer record by identifier.", "record"),
    }
    children = []
    for name in active_agents:
        if name not in definitions:
            continue
        binder, instruction, adapter_key = definitions[name]
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
            # Older ADK releases use the same concepts but may not accept all
            # optional constructor fields.  Failing closed preserves the
            # deterministic port path rather than inventing a cloud success.
            logger.warning("Installed google-adk version cannot build %s", name)
            return None
    try:
        return ParallelAgent(name="ProofTriageSpecialistSwarm", sub_agents=children)
    except TypeError:
        return None
