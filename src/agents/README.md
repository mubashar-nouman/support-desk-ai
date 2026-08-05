# Agents Module

Quick reference for AI agents. See [full documentation](../../docs/agents.md) for details.

## 📁 Files

```
src/agents/
├── __init__.py          # Package exports
├── base_agent.py        # Abstract base class
└── README.md           # This file
```

## 🚀 Quick Start

### Creating a New Agent

```python
from src.agents import BaseAgent
from src.models import AgentState

class MyAgent(BaseAgent):
    """My custom agent."""
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Process the agent state.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        # Your agent logic here
        state.metadata["my_agent_result"] = "success"
        
        # Always update the state
        return state

# Use the agent
agent = MyAgent(name="my_agent")
result = await agent.execute(state)
```

### Using LLM in Agents

```python
from src.llm import LLMMessage

class ClassificationAgent(BaseAgent):
    """Classifies customer messages."""
    
    async def process(self, state: AgentState) -> AgentState:
        """Classify the message using LLM."""
        # Create LLM messages
        messages = [
            LLMMessage(role="user", content=state.current_message)
        ]
        
        # Call LLM
        response = await self.llm.generate(
            messages,
            system_prompt="Classify this message",
            temperature=0.3
        )
        
        # Update state
        state.category = response.content
        
        return state
```

## 🔧 Key Features

### 1. Automatic Error Handling

```python
# Errors are caught automatically
# State.error is set
# Metrics are tracked
result = await agent.execute(state)

if result.error:
    print(f"Agent failed: {result.error}")
```

### 2. Built-in Logging

```python
# Logs automatically include:
# - Start/end of execution
# - Execution time
# - Errors with stack traces
# - Ticket/customer IDs

# Access agent logger
agent.logger.info("Custom log message")
```

### 3. Metrics Tracking

```python
# Get agent metrics
metrics = agent.get_metrics()

print(metrics)
# {
#     'agent_name': 'my_agent',
#     'total_executions': 10,
#     'successful_executions': 9,
#     'failed_executions': 1,
#     'success_rate': 90.0,
#     'average_time': 1.23
# }
```

### 4. Enable/Disable Agents

```python
# Disable an agent
agent.disable()

# Agent will be skipped during execution
result = await agent.execute(state)

# Re-enable
agent.enable()
```

## 📊 BaseAgent API

### Properties

```python
agent.name          # Agent name
agent.llm           # LLM client instance
agent.enabled       # Whether agent is enabled
agent.logger        # Logger instance
agent.metrics       # Metrics tracker
```

### Methods

```python
# Must implement (abstract)
async def process(state: AgentState) -> AgentState

# Provided by base class
async def execute(state: AgentState) -> AgentState
def get_metrics() -> Dict[str, Any]
def reset_metrics() -> None
def enable() -> None
def disable() -> None
```

## 🎯 Agent Lifecycle

```
1. execute() called
    ↓
2. Check if enabled
    ↓
3. Log start
    ↓
4. Call process() (your implementation)
    ↓
5. Record metrics
    ↓
6. Log success/error
    ↓
7. Update agent history
    ↓
8. Return updated state
```

## 💡 Best Practices

### 1. Always Return State

```python
# ✅ Good
async def process(self, state: AgentState) -> AgentState:
    state.category = "billing"
    return state

# ❌ Bad
async def process(self, state: AgentState) -> AgentState:
    state.category = "billing"
    # Missing return!
```

### 2. Add to Agent History

```python
# Base class does this automatically in execute()
# But you can add custom entries:
state.add_agent_to_history("my_agent: classified as billing")
```

### 3. Use Descriptive Names

```python
# ✅ Good
agent = IntakeAgent(name="intake")
agent = ResolutionAgent(name="resolution")

# ❌ Bad
agent = MyAgent(name="agent1")
```

### 4. Handle State Properly

```python
# ✅ Good - Modify and return
async def process(self, state: AgentState) -> AgentState:
    state.category = "billing"
    return state

# ❌ Bad - Creating new state loses history
async def process(self, state: AgentState) -> AgentState:
    return AgentState(...)  # Don't do this!
```

## 🧪 Testing Agents

```python
import pytest
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_my_agent():
    """Test agent execution."""
    # Create mock LLM
    mock_llm = Mock()
    
    # Create agent
    agent = MyAgent(name="test", llm_client=mock_llm)
    
    # Create test state
    state = AgentState(
        ticket_id=uuid4(),
        customer_id=uuid4(),
        current_message="Test"
    )
    
    # Execute
    result = await agent.execute(state)
    
    # Assert
    assert result.error is None
    assert "test" in result.agent_history
```

## 📚 Full Documentation

For complete documentation including:
- Detailed architecture
- Advanced patterns
- Error handling strategies
- Integration examples

See: **[docs/agents.md](../../docs/agents.md)**

---

**Status:** ✅ Production Ready  
**Test Coverage:** 95%+  
**Last Updated:** 2024-12
