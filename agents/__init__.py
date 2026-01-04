"""
STARK Agent Framework
=====================
Multi-agent orchestration system.
"""

from agents.base_agent import (
    BaseAgent,
    AgentType,
    AgentStatus,
    AgentResult,
    AgentOrchestrator,
    get_orchestrator,
    reset_orchestrator,
)

from agents.file_agent import FileAgent
from agents.code_agent import CodeAgent

# Autonomous multi-agent system
from agents.router_agent import RouterAgent, RoutePath
from agents.specialists import (
    RetrieverAgent,
    FastAnswerAgent,
    PlannerAgent,
    ArbiterAgent,
)
from agents.web_agent import WebAgent
from agents.autonomous_orchestrator import (
    AutonomousOrchestrator,
    get_autonomous_orchestrator,
    reset_autonomous_orchestrator,
)

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentType",
    "AgentStatus",
    "AgentResult",
    "AgentOrchestrator",
    "get_orchestrator",
    "reset_orchestrator",
    # Agents
    "FileAgent",
    "CodeAgent",
    "RouterAgent",
    "RetrieverAgent",
    "FastAnswerAgent",
    "PlannerAgent",
    "ArbiterAgent",
    "WebAgent",
    # Autonomous system
    "AutonomousOrchestrator",
    "get_autonomous_orchestrator",
    "reset_autonomous_orchestrator",
    "RoutePath",
]
