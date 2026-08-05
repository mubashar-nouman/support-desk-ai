# Agent System

Complete guide to the AI agent architecture and base agent class.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Base Agent Class](#base-agent-class)
- [Creating Agents](#creating-agents)
- [Testing](#testing)
- [Best Practices](#best-practices)

## Overview

The agent system provides a modular, extensible framework for building AI-powered agents that process customer support tickets.

### Key Concepts

**Agent**: A specialized AI component that performs one specific task in the workflow
**AgentState**: Shared state object that flows through all agents
**BaseAgent**: Abstract base class all agents inherit from
**Orchestrator**: Coordinates agent execution (coming in next phase)

### Agent Types

1. **Intake Agent** - Classifies and analyzes incoming messages
2. **Knowledge Agent** - Retrieves relevant information
3. **Resolution Agent** - Generates customer responses
4. **Action Agent** - Executes system actions
5. **Escalation Agent** - Determines if human intervention needed

## Architecture

### Class Hierarchy

```
BaseAgent (abstract)
    ├── process() [ABSTRACT]
    ├── execute() [CONCRETE]
    ├── Logging
    ├── Metrics
    └── Error Handling

IntakeAgent(BaseAgent)
KnowledgeAgent(BaseAgent)
ResolutionAgent(BaseAgent)
ActionAgent(BaseAgent)
EscalationAgent(BaseAgent)
```

### Execution Flow

```
State (input)
    ↓
Agent.execute()
    ├→ Check enabled
    ├→ Log start
    ├→ Agent.process() ← Your implementation
    ├→ Record metrics
    ├→ Log success/error
    ├→ Update history
    └→ Return state
    ↓
State (output)
```

### State Management

All agents work with `AgentState`:

```python
@dataclass
class AgentState:
    ticket_id: UUID
    customer_id: UUID
    messages: List[Message]
    current_message: str
    
    # Classification (set by Intake)
    category: Optional[str]
    priority: Optional[str]
    sentiment: Optional[str]
    
    # Knowledge (set by Knowledge Agent)
    retrieved_documents: List[Dict]
    knowledge_confidence: float
    
    # Resolution (set by Resolution Agent)
    proposed_response: Optional[str]
    response_confidence: float
    
    # Actions (set by Action Agent)
    actions_executed: List[str]
    
    # Escalation (set by Escalation Agent)
    should_escalate: bool
    escalation_reason: Optional[str]
    
    # Workflow
    agent_history: List[str]
    metadata: Dict[str, Any]
    error: Optional[str]
```

## Base Agent Class

### Core Components

#### 1. AgentMetrics

Tracks execution statistics:

```python
class AgentMetrics:
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_time: float
    
    @property
    def average_time(self) -> float
    @property
    def success_rate(self) -> float
```

#### 2. BaseAgent

Abstract base providing:
- LLM client integration
- Error handling
- Logging
- Metrics tracking
- Enable/disable functionality

**Key Methods:**

```python
class BaseAgent(ABC):
    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """Implement your agent logic here."""
        pass
    
    async def execute(self, state: AgentState) -> AgentState:
        """Wrapper with error handling, logging, metrics."""
        # Implemented by base class
```

### Metrics and Observability

**Automatic Logging:**
- Start of execution with context
- Completion time and status
- Errors with stack traces
- State transitions

**Metrics Tracked:**
- Total executions
- Success/failure counts
- Execution times
- Success rate

**Access Metrics:**
```python
metrics = agent.get_metrics()
# {
#     'agent_name': 'intake',
#     'total_executions': 100,
#     'successful_executions': 98,
#     'success_rate': 98.0,
#     'average_time': 1.234
# }
```

## Creating Agents

### Basic Agent Template

```python
from src.agents import BaseAgent
from src.models import AgentState
from src.llm import LLMMessage

class MyAgent(BaseAgent):
    """
    Agent description.
    
    Responsibilities:
    - Task 1
    - Task 2
    """
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Process agent state.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # 1. Extract what you need
        message = state.current_message
        
        # 2. Do your work (LLM call, logic, etc.)
        result = await self._do_work(message)
        
        # 3. Update state
        state.metadata["my_result"] = result
        
        # 4. Always return state
        return state
    
    async def _do_work(self, message: str) -> str:
        """Helper method for your logic."""
        # Your implementation
        return "result"
```

### Agent with LLM

```python
from config import get_system_prompt

class ClassificationAgent(BaseAgent):
    """Classifies customer messages."""
    
    def __init__(self, **kwargs):
        super().__init__(name="classification", **kwargs)
        self.system_prompt = get_system_prompt("intake_agent")
    
    async def process(self, state: AgentState) -> AgentState:
        """Classify the message."""
        # Prepare messages
        messages = [
            LLMMessage(
                role="user",
                content=state.current_message
            )
        ]
        
        # Call LLM
        response = await self.llm.generate(
            messages,
            system_prompt=self.system_prompt,
            temperature=0.3,
            max_tokens=100
        )
        
        # Update state
        state.category = response.content.strip()
        state.set_workflow_step("classification_complete")
        
        self.logger.info(f"Classified as: {state.category}")
        
        return state
```

### Agent with External API

```python
class ActionAgent(BaseAgent):
    """Executes system actions."""
    
    async def process(self, state: AgentState) -> AgentState:
        """Execute required actions."""
        # Check what actions are needed
        if state.requires_action:
            for action in state.actions_to_execute:
                try:
                    result = await self._execute_action(action)
                    state.mark_action_executed(action['name'])
                    state.action_results[action['name']] = result
                except Exception as e:
                    self.logger.error(f"Action failed: {e}")
                    state.action_results[action['name']] = {"error": str(e)}
        
        return state
    
    async def _execute_action(self, action: Dict) -> Dict:
        """Execute a single action."""
        action_type = action['type']
        
        if action_type == "send_email":
            return await self._send_email(action['params'])
        elif action_type == "create_ticket":
            return await self._create_ticket(action['params'])
        else:
            raise ValueError(f"Unknown action: {action_type}")
```

## Testing

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from src.agents import BaseAgent
from src.models import AgentState

class TestMyAgent:
    """Tests for MyAgent."""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        return Mock()
    
    @pytest.fixture
    def agent(self, mock_llm):
        """Create agent instance."""
        return MyAgent(name="test", llm_client=mock_llm)
    
    @pytest.fixture
    def state(self):
        """Create test state."""
        return AgentState(
            ticket_id=uuid4(),
            customer_id=uuid4(),
            current_message="Test message"
        )
    
    @pytest.mark.asyncio
    async def test_process_success(self, agent, state):
        """Test successful processing."""
        result = await agent.execute(state)
        
        assert result.error is None
        assert "test" in result.agent_history
        assert agent.metrics.successful_executions == 1
    
    @pytest.mark.asyncio
    async def test_process_with_llm(self, agent, state, mock_llm):
        """Test LLM integration."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "billing"
        agent.llm.generate = AsyncMock(return_value=mock_response)
        
        result = await agent.execute(state)
        
        assert result.category == "billing"
        agent.llm.generate.assert_called_once()
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_agent_chain():
    """Test multiple agents in sequence."""
    # Create agents
    intake = IntakeAgent(name="intake")
    knowledge = KnowledgeAgent(name="knowledge")
    resolution = ResolutionAgent(name="resolution")
    
    # Create initial state
    state = AgentState(
        ticket_id=uuid4(),
        customer_id=uuid4(),
        current_message="I need a refund"
    )
    
    # Execute chain
    state = await intake.execute(state)
    state = await knowledge.execute(state)
    state = await resolution.execute(state)
    
    # Verify
    assert state.category is not None
    assert len(state.retrieved_documents) > 0
    assert state.proposed_response is not None
    assert len(state.agent_history) == 3
```

## Best Practices

### 1. Single Responsibility

Each agent should do ONE thing well:

```python
# ✅ Good - Focused responsibility
class ClassificationAgent(BaseAgent):
    async def process(self, state):
        state.category = await self._classify(state.current_message)
        return state

# ❌ Bad - Too many responsibilities
class SuperAgent(BaseAgent):
    async def process(self, state):
        state.category = await self._classify()
        state.documents = await self._retrieve()
        state.response = await self._generate()
        # Too much!
```

### 2. Immutable State Updates

Don't create new state objects:

```python
# ✅ Good - Modify and return
async def process(self, state: AgentState) -> AgentState:
    state.category = "billing"
    return state

# ❌ Bad - Loses history
async def process(self, state: AgentState) -> AgentState:
    return AgentState(category="billing")  # Don't!
```

### 3. Descriptive Logging

Use structured logging with context:

```python
self.logger.info(
    "Classified message",
    extra={
        "category": state.category,
        "confidence": 0.95,
        "ticket_id": str(state.ticket_id)
    }
)
```

### 4. Graceful Error Handling

Let base class handle errors, but be defensive:

```python
async def process(self, state: AgentState) -> AgentState:
    try:
        # Your logic
        result = await self._risky_operation()
        state.result = result
    except SpecificError as e:
        # Handle specific errors
        self.logger.warning(f"Known issue: {e}")
        state.result = "default_value"
    # Let other errors bubble up to base class
    
    return state
```

### 5. Use Helper Methods

Keep `process()` clean and readable:

```python
async def process(self, state: AgentState) -> AgentState:
    """Main process method - high level."""
    # Extract
    message = state.current_message
    
    # Process
    category = await self._classify(message)
    confidence = await self._calculate_confidence(category)
    
    # Update
    state.category = category
    state.metadata["confidence"] = confidence
    
    return state

async def _classify(self, message: str) -> str:
    """Helper method - implementation details."""
    # Detailed logic here
```

## Summary

The agent system provides:
- ✅ Abstract base class with common functionality
- ✅ Automatic error handling and retry logic
- ✅ Built-in logging and observability
- ✅ Metrics tracking for all agents
- ✅ Easy testing with mocks
- ✅ Type-safe implementation

### Key Takeaways

1. Inherit from `BaseAgent`
2. Implement `async def process(state) -> state`
3. Return modified state
4. Let base class handle errors, logging, metrics
5. Test with mocks

---

**Documentation Version:** 1.0  
**Last Updated:** 2024-12  
**Status:** ✅ Production Ready
