"""
STARK Agent Framework
=====================
Base classes for multi-agent orchestration system.

Agents are specialized sub-systems that STARK can delegate tasks to.
Each agent has its own domain of expertise and can invoke tools/capabilities.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT TYPES & RESULTS
# =============================================================================

class AgentType(Enum):
    """Types of available agents."""
    RESEARCH = "research"
    CODE = "code"
    FILE = "file"
    WEB = "web"
    GENERAL = "general"


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentResult:
    """Result from agent execution."""
    
    # Core result
    success: bool
    output: str
    error: Optional[str] = None
    
    # Metadata
    agent_type: AgentType = AgentType.GENERAL
    agent_name: str = ""
    execution_time_ms: float = 0.0
    
    # Additional context
    steps_taken: List[str] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)
    sub_agents_called: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "agent_type": self.agent_type.value,
            "agent_name": self.agent_name,
            "execution_time_ms": self.execution_time_ms,
            "steps_taken": self.steps_taken,
            "artifacts_created": self.artifacts_created,
            "sub_agents_called": self.sub_agents_called,
        }


# =============================================================================
# BASE AGENT
# =============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all STARK agents.
    
    Each agent is a specialized component that can:
    1. Receive a task/query
    2. Execute domain-specific operations
    3. Return structured results
    
    Agents can call other agents for sub-tasks.
    """
    
    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        description: str = "",
        timeout: float = 60.0,
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent instance name
            agent_type: Type of agent
            description: What this agent does
            timeout: Max execution time in seconds
        """
        self.name = name
        self.agent_type = agent_type
        self.description = description
        self.timeout = timeout
        
        # State
        self.status = AgentStatus.IDLE
        self._execution_count = 0
        self._total_time_ms = 0.0
        self._success_count = 0
        
        # Agent registry (set by orchestrator)
        self._orchestrator = None
        
        logger.info(f"Initialized {self.agent_type.value} agent: {self.name}")
    
    def set_orchestrator(self, orchestrator: 'AgentOrchestrator') -> None:
        """Set the orchestrator reference for calling other agents."""
        self._orchestrator = orchestrator
    
    @abstractmethod
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute the agent's task.
        
        Args:
            task: Task description/query
            context: Additional context dict
            
        Returns:
            AgentResult with execution details
        """
        pass
    
    def run(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Run the agent with timeout and error handling.
        
        This is the public entry point. It wraps execute() with:
        - Timeout handling
        - Error catching
        - Stats tracking
        - Status management
        """
        self.status = AgentStatus.RUNNING
        self._execution_count += 1
        start_time = time.time()
        
        context = context or {}
        
        try:
            # Execute the agent's logic
            result = self.execute(task, context)
            
            # Update stats
            elapsed_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = elapsed_ms
            result.agent_name = self.name
            result.agent_type = self.agent_type
            
            self._total_time_ms += elapsed_ms
            
            if result.success:
                self._success_count += 1
                self.status = AgentStatus.SUCCESS
            else:
                self.status = AgentStatus.FAILED
            
            logger.info(
                f"{self.name} completed: {result.success} "
                f"({elapsed_ms:.0f}ms)"
            )
            
            return result
            
        except TimeoutError:
            self.status = AgentStatus.TIMEOUT
            return AgentResult(
                success=False,
                output="",
                error=f"Agent timed out after {self.timeout}s",
                agent_name=self.name,
                agent_type=self.agent_type,
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"{self.name} failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                agent_name=self.name,
                agent_type=self.agent_type,
            )
        
        finally:
            self.status = AgentStatus.IDLE
    
    def call_agent(self, agent_name: str, task: str, context: Dict = None) -> AgentResult:
        """
        Call another agent via the orchestrator.
        
        Args:
            agent_name: Name of agent to call
            task: Task for the agent
            context: Context dict
            
        Returns:
            AgentResult from the called agent
        """
        if self._orchestrator is None:
            raise RuntimeError(f"{self.name} has no orchestrator reference")
        
        logger.debug(f"{self.name} calling {agent_name}")
        return self._orchestrator.call_agent(agent_name, task, context)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics."""
        avg_time = self._total_time_ms / max(1, self._execution_count)
        success_rate = self._success_count / max(1, self._execution_count)
        
        return {
            "name": self.name,
            "type": self.agent_type.value,
            "status": self.status.value,
            "executions": self._execution_count,
            "successes": self._success_count,
            "success_rate": success_rate,
            "avg_time_ms": avg_time,
            "total_time_ms": self._total_time_ms,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', type={self.agent_type.value})"


# =============================================================================
# AGENT ORCHESTRATOR
# =============================================================================

class AgentOrchestrator:
    """
    Central orchestrator for managing and coordinating agents.
    
    Responsibilities:
    - Register/manage agents
    - Route tasks to appropriate agents
    - Handle agent-to-agent communication
    - Aggregate results
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        self._agents: Dict[str, BaseAgent] = {}
        self._executions = 0
        
        logger.info("AgentOrchestrator initialized")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: Agent instance to register
        """
        if agent.name in self._agents:
            logger.warning(f"Overwriting existing agent: {agent.name}")
        
        self._agents[agent.name] = agent
        agent.set_orchestrator(self)
        
        logger.info(f"Registered agent: {agent.name} ({agent.agent_type.value})")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """Get all agents of a specific type."""
        return [
            agent for agent in self._agents.values()
            if agent.agent_type == agent_type
        ]
    
    def call_agent(
        self,
        agent_name: str,
        task: str,
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Call a specific agent by name.
        
        Args:
            agent_name: Name of agent to call
            task: Task for the agent
            context: Optional context dict
            
        Returns:
            AgentResult from the agent
        """
        agent = self.get_agent(agent_name)
        
        if agent is None:
            return AgentResult(
                success=False,
                output="",
                error=f"Agent '{agent_name}' not found",
            )
        
        self._executions += 1
        return agent.run(task, context)
    
    def delegate_task(
        self,
        task: str,
        preferred_type: Optional[AgentType] = None,
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Delegate a task to the best available agent.
        
        Args:
            task: Task description
            preferred_type: Preferred agent type (optional)
            context: Context dict
            
        Returns:
            AgentResult from the selected agent
        """
        # If type specified, try to find agent of that type
        if preferred_type:
            agents = self.get_agents_by_type(preferred_type)
            if agents:
                return agents[0].run(task, context)
        
        # Fallback: use first available general agent
        general_agents = self.get_agents_by_type(AgentType.GENERAL)
        if general_agents:
            return general_agents[0].run(task, context)
        
        return AgentResult(
            success=False,
            output="",
            error="No suitable agent found",
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_agents": len(self._agents),
            "total_executions": self._executions,
            "agents": {
                name: agent.get_stats()
                for name, agent in self._agents.items()
            }
        }
    
    def list_agents(self) -> List[Dict[str, str]]:
        """List all registered agents."""
        return [
            {
                "name": agent.name,
                "type": agent.agent_type.value,
                "description": agent.description,
                "status": agent.status.value,
            }
            for agent in self._agents.values()
        ]
    
    def __repr__(self) -> str:
        return f"AgentOrchestrator(agents={len(self._agents)}, executions={self._executions})"


# =============================================================================
# SINGLETON
# =============================================================================

_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global agent orchestrator."""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    
    return _orchestrator_instance


def reset_orchestrator() -> None:
    """Reset orchestrator singleton (for testing)."""
    global _orchestrator_instance
    _orchestrator_instance = None
