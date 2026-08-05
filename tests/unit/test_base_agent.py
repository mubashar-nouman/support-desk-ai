"""
Unit tests for base agent class.

Tests abstract base, metrics tracking, error handling, and execution flow.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from src.agents import BaseAgent, AgentMetrics, AgentError
from src.models import AgentState
from src.llm import LLMClient


# Test implementation of BaseAgent
class SimpleTestAgent(BaseAgent):
    """Simple test agent that echoes input."""
    
    async def process(self, state: AgentState) -> AgentState:
        """Simple process that adds to history."""
        state.metadata["test_agent_ran"] = True
        return state


class FailingAgent(BaseAgent):
    """Test agent that always fails."""
    
    async def process(self, state: AgentState) -> AgentState:
        """Always raises an error."""
        raise ValueError("Intentional test error")


class TestAgentMetrics:
    """Tests for AgentMetrics class."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        metrics = AgentMetrics()
        
        assert metrics.total_executions == 0
        assert metrics.successful_executions == 0
        assert metrics.failed_executions == 0
        assert metrics.total_time == 0.0
        assert metrics.average_time == 0.0
        assert metrics.success_rate == 0.0
    
    def test_record_success(self):
        """Test recording successful execution."""
        metrics = AgentMetrics()
        
        metrics.record_success(1.5)
        
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 1
        assert metrics.failed_executions == 0
        assert metrics.total_time == 1.5
        assert metrics.average_time == 1.5
        assert metrics.success_rate == 100.0
    
    def test_record_failure(self):
        """Test recording failed execution."""
        metrics = AgentMetrics()
        
        metrics.record_failure(2.0)
        
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 0
        assert metrics.failed_executions == 1
        assert metrics.total_time == 2.0
        assert metrics.success_rate == 0.0
    
    def test_multiple_executions(self):
        """Test tracking multiple executions."""
        metrics = AgentMetrics()
        
        metrics.record_success(1.0)
        metrics.record_success(2.0)
        metrics.record_failure(3.0)
        
        assert metrics.total_executions == 3
        assert metrics.successful_executions == 2
        assert metrics.failed_executions == 1
        assert metrics.total_time == 6.0
        assert metrics.average_time == 2.0
        assert metrics.success_rate == pytest.approx(66.67, rel=0.01)
    
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = AgentMetrics()
        metrics.record_success(1.5)
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result['total_executions'] == 1
        assert result['successful_executions'] == 1
        assert result['success_rate'] == 100.0
        assert 'average_time' in result


class TestBaseAgent:
    """Tests for BaseAgent class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return Mock(spec=LLMClient)
    
    @pytest.fixture
    def agent_state(self):
        """Create test agent state."""
        return AgentState(
            ticket_id=uuid4(),
            customer_id=uuid4(),
            current_message="Test message"
        )
    
    def test_agent_initialization(self, mock_llm_client):
        """Test agent initialization."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        
        assert agent.name == "test_agent"
        assert agent.llm == mock_llm_client
        assert agent.enabled is True
        assert agent.metrics.total_executions == 0
    
    def test_agent_initialization_with_defaults(self):
        """Test agent initialization with default LLM client."""
        with patch('src.agents.base_agent.get_llm_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            agent = SimpleTestAgent(name="test_agent")
            
            assert agent.llm == mock_client
    
    def test_abstract_process_method(self):
        """Test that process() must be implemented."""
        # Can't instantiate BaseAgent directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAgent(name="abstract")
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, agent_state, mock_llm_client):
        """Test successful agent execution."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        
        result = await agent.execute(agent_state)
        
        # Check state was updated
        assert result.metadata.get("test_agent_ran") is True
        assert "test_agent" in result.agent_history
        
        # Check metrics
        assert agent.metrics.total_executions == 1
        assert agent.metrics.successful_executions == 1
        assert agent.metrics.failed_executions == 0
    
    @pytest.mark.asyncio
    async def test_failed_execution(self, agent_state, mock_llm_client):
        """Test agent execution with error."""
        agent = FailingAgent(name="failing_agent", llm_client=mock_llm_client)
        
        result = await agent.execute(agent_state)
        
        # Check error was recorded
        assert result.error is not None
        assert "failing_agent error" in result.error
        assert "failing_agent (failed)" in result.agent_history
        
        # Check metrics
        assert agent.metrics.total_executions == 1
        assert agent.metrics.successful_executions == 0
        assert agent.metrics.failed_executions == 1
    
    @pytest.mark.asyncio
    async def test_disabled_agent(self, agent_state, mock_llm_client):
        """Test that disabled agents are skipped."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client, enabled=False)
        
        result = await agent.execute(agent_state)
        
        # Agent should be skipped
        assert result.metadata.get("test_agent_ran") is not True
        assert "test_agent (skipped)" in result.agent_history
        
        # No executions recorded
        assert agent.metrics.total_executions == 0
    
    @pytest.mark.asyncio
    async def test_multiple_executions(self, mock_llm_client):
        """Test multiple agent executions."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        
        # Execute 3 times
        for _ in range(3):
            state = AgentState(
                ticket_id=uuid4(),
                customer_id=uuid4(),
                current_message="Test"
            )
            await agent.execute(state)
        
        assert agent.metrics.total_executions == 3
        assert agent.metrics.successful_executions == 3
    
    def test_get_metrics(self, mock_llm_client):
        """Test getting agent metrics."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        agent.metrics.record_success(1.0)
        
        metrics = agent.get_metrics()
        
        assert isinstance(metrics, dict)
        assert metrics['agent_name'] == 'test_agent'
        assert metrics['enabled'] is True
        assert metrics['total_executions'] == 1
    
    def test_reset_metrics(self, mock_llm_client):
        """Test resetting agent metrics."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        agent.metrics.record_success(1.0)
        
        agent.reset_metrics()
        
        assert agent.metrics.total_executions == 0
        assert agent.metrics.successful_executions == 0
    
    def test_enable_disable(self, mock_llm_client):
        """Test enabling and disabling agent."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        
        assert agent.enabled is True
        
        agent.disable()
        assert agent.enabled is False
        
        agent.enable()
        assert agent.enabled is True
    
    def test_repr(self, mock_llm_client):
        """Test agent string representation."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        
        repr_str = repr(agent)
        assert "SimpleTestAgent" in repr_str
        assert "test_agent" in repr_str
        assert "enabled=True" in repr_str
    
    def test_str(self, mock_llm_client):
        """Test agent string conversion."""
        agent = SimpleTestAgent(name="test_agent", llm_client=mock_llm_client)
        
        str_result = str(agent)
        assert "test_agent" in str_result
        assert "Agent" in str_result


class TestAgentError:
    """Tests for AgentError exception."""
    
    def test_agent_error_creation(self):
        """Test creating AgentError."""
        error = AgentError("test_agent", "Something went wrong")
        
        assert error.agent_name == "test_agent"
        assert "test_agent" in str(error)
        assert "Something went wrong" in str(error)
    
    def test_agent_error_with_original(self):
        """Test AgentError with original exception."""
        original = ValueError("Original error")
        error = AgentError("test_agent", "Wrapped error", original_error=original)
        
        assert error.original_error == original
        assert error.agent_name == "test_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])