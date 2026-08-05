"""
Base agent class for all AI agents.

All agents inherit from BaseAgent and implement the process() method.
"""

import logging
from sys import float_repr_style
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from src.models import AgentState
from src.llm import LLMClient, get_llm_client

class AgentMetrics:
    """
    Tracks agent execution metrics.

    Attributes:
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        total_time: Total execution time in seconds
        average_time: Average execution time
    """

    def __init__(self):
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_time = 0.0

    @property
    def average_time(self) -> float:
        """ Calculate average execution time. """
        if self.total_executions == 0:
            return 0.0
        return self.total_time / self.total_executions

    @property
    def success_rate(self) -> float:
        """ Calculate success rate as percentage. """
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100

    def record_success(self, execution_time: float) -> None:
        """ Record a successful execution. """
        self.total_executions += 1
        self.successful_executions += 1
        self.total_time += execution_time

    def record_failure(self, execution_time: float) -> None:
        """ Record a failed execution. """
        self.total_executions += 1
        self.failed_executions += 1
        self.total_time += execution_time

    def to_dict(self) -> Dict[str, Any]:
        """ Convert metrics to dictionary. """
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": round(self.success_rate, 2),
            "total_time": round(self.total_time, 2),
            "average_time": round(self.average_time, 3),
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    All agents must inherit from this class and implement the process() method.
    The execute() method wraps process() with error handling,logging, and metrics.

    Attribute:
        name: Agent Name (e.g. "intake", "resolution")
        llm: LLM client for AI operations
        logger: Logger instance
        metrics: Execution metrics tracker

    Example:
        >> class MyAgent(BaseAgent):
        ...     async def process(self, state: AgentState) -> AgentState:
        ...        # Your agent logic here
        ...         state.add_agent_to_history(self.name)
        ...          eturn state

        >> agent = MyAgent(name = "my_agent")
        >> result = await agent.execute(state)
    """

    def __init__(
        self,
        name: str,
        llm_client: Optional[LLMClient] = None,
        enabled: bool = True
    ):

        """
        Initialize base agent.

        Args:
            name: Agent name (used for logging and tracking)
            llm_client: LLM client instance (uses global if None)
            enabled: Whether agent is enabled
        """

        self.name = name
        self.llm = llm_client or get_llm_client()
        self.enabled = enabled
        self.logger = logging.getLogger(f"agent.{name}")
        self.metrics = AgentMetrics()

        self.logger.info(f"Agent '{name}' initialized (enabled = {enabled})")

    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """
        Process agent state. Must be implemented by subclasses.

        This is the core agent logic. Each agent implements its own processing.

        Args:
            state: Current agent state
        
        Returns:
            Updated agent state

        Raises:
            NotImplementationError: If not implemented by subclass
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement process()")

    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute agent with error handling, logging, and metrics.

        This method wraps process() with:
        - Pre/post execution logging
        - Error handling
        - Execution time tracking
        - Metrics collection
        - Agent history tracking

        Args:
            state: Current agent state

        Returns:
            Updated agent state (may contain error if execution failed)
        """

        # Check if agent is enabled 
        if not self.enabled:
            self.logger.warning(f"Agent '{self.name}' is disabled, skipping")
            state.add_agent_to_history(f"{self.name} (skipped)")
            return state

        # Start timing
        start_time = time.time()

        # Log start
        self._log_start(state)

        try:
            # Execute agent logic
            updated_state = await self.process(state)

            # Record execution time
            execution_time = time.time() - start_time

            # Update metrics
            self.metrics.record_success(execution_time)

            # Log success
            self._log_success(updated_state, execution_time)

            # Add to agent history
            updated_state.add_agent_to_history(self.name)

            return updated_state

        except Exception as e:
            # Record execution time
            execution_time = time.time() - start_time
            
            # Update metrics
            self.metrics.record_failure(execution_time)
            
            # Log error
            self._log_error(state, e, execution_time)
            
            # Update state with error
            state.error = f"{self.name} error: {str(e)}"
            state.add_agent_to_history(f"{self.name} (failed)")
            
            # Don't re-raise - let orchestrator handle
            return state
    
    def _log_start(self, state: AgentState) -> None:
        """Log agent execution start."""
        self.logger.info(
            f"Starting {self.name} agent",
            extra={
                "ticket_id": str(state.ticket_id),
                "customer_id": str(state.customer_id),
                "workflow_step": state.workflow_step,
                "message_count": len(state.messages),
            }
        )
    
    def _log_success(self, state: AgentState, execution_time: float) -> None:
        """Log successful agent execution."""
        self.logger.info(
            f"Completed {self.name} agent successfully",
            extra={
                "ticket_id": str(state.ticket_id),
                "execution_time": round(execution_time, 3),
                "workflow_step": state.workflow_step,
                "should_escalate": state.should_escalate,
            }
        )
    
    def _log_error(self, state: AgentState, error: Exception, execution_time: float) -> None:
        """Log agent execution error."""
        self.logger.error(
            f"Error in {self.name} agent: {error}",
            extra={
                "ticket_id": str(state.ticket_id),
                "execution_time": round(execution_time, 3),
                "error_type": type(error).__name__,
            },
            exc_info=True
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent execution metrics.
        
        Returns:
            Dictionary with metrics
        """
        return {
            "agent_name": self.name,
            "enabled": self.enabled,
            **self.metrics.to_dict()
        }
    
    def reset_metrics(self) -> None:
        """Reset agent metrics."""
        self.metrics = AgentMetrics()
        self.logger.info(f"Reset metrics for {self.name} agent")
    
    def enable(self) -> None:
        """Enable agent."""
        self.enabled = True
        self.logger.info(f"Enabled {self.name} agent")
    
    def disable(self) -> None:
        """Disable agent."""
        self.enabled = False
        self.logger.warning(f"Disabled {self.name} agent")
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"enabled={self.enabled}, executions={self.metrics.total_executions})"
        )
    
    def __str__(self) -> str:
        return f"{self.name} Agent"

class AgentError(Exception):
    """
    Base exception for agent errors.
    
    Use this for agent-specific errors that should be caught and handled.
    """
    
    def __init__(self, agent_name: str, message: str, original_error: Optional[Exception] = None):
        self.agent_name = agent_name
        self.original_error = original_error
        super().__init__(f"[{agent_name}] {message}")