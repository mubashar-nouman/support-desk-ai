"""
AI Agent module.

Provides base agent class and agent implementations.

Usage:
    from src.agents import BaseAgent
    
    class MyAgent(BaseAgent):
        async def process(self, state: AgentState) -> AgentState:
            # Your logic here
            return state
"""

from .base_agent import BaseAgent, AgentMetrics, AgentError

__all__ = [
    "BaseAgent",
    "AgentMetrics",
    "AgentError",
]