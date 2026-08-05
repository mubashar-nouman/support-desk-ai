# LLM Client System

Complete guide to the unified LLM client with provider fallback.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Providers](#providers)
- [Usage Patterns](#usage-patterns)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The LLM client provides a unified interface for interacting with multiple LLM providers (Claude, OpenAI) with automatic fallback, retry logic, and comprehensive observability.

### Key Features

- **Provider Agnostic** - Same interface for all providers
- **Automatic Fallback** - Switch to backup provider on failure
- **Retry Logic** - Exponential backoff on transient errors
- **Token Tracking** - Monitor usage across all calls
- **Observable** - Comprehensive logging
- **Type Safe** - Full type hints and validation

### Architecture

```
Application
    ↓
LLMClient (unified interface)
    ↓
Provider Factory
    ↓
┌─────────────┬─────────────┐
│   Claude    │   OpenAI    │
│  Provider   │  Provider   │
└─────────────┴─────────────┘
```

## Architecture

### Component Overview

**LLMClient** - Main interface
- Manages provider selection
- Handles fallback logic
- Tracks usage statistics
- Implements retry logic

**BaseProvider** - Abstract interface
- Defines provider contract
- Standardizes input/output
- Token counting interface

**ClaudeProvider** - Anthropic implementation
- Claude API integration
- Message format conversion
- Claude-specific features

**OpenAIProvider** - OpenAI implementation
- OpenAI API integration
- Message format conversion
- GPT-specific features

### Data Flow

```
1. Application creates LLMMessage objects
2. LLMClient receives generate() request
3. Primary provider attempts generation
4. On failure, fallback provider tries (if enabled)
5. Retries on transient errors (exponential backoff)
6. Returns standardized LLMResponse
7. Tracks tokens and statistics
```

### Standardized Formats

**Input Format (LLMMessage)**:
```python
@dataclass
class LLMMessage:
    role: str      # "user", "assistant", "system"
    content: str   # Message content
```

**Output Format (LLMResponse)**:
```python
@dataclass
class LLMResponse:
    content: str              # Generated text
    model: str                # Model identifier
    provider: str             # Provider name
    prompt_tokens: int        # Input token count
    completion_tokens: int    # Output token count
    total_tokens: int         # Total tokens
    finish_reason: str        # Completion reason
    metadata: Dict[str, Any]  # Provider metadata
```

## Quick Start

### Installation

Dependencies are already in `pyproject.toml`:
```toml
anthropic>=0.18.0
openai>=1.12.0
tenacity>=8.2.0
```

### Basic Usage

```python
from src.llm import get_llm_client, LLMMessage

# Initialize client (singleton)
client = get_llm_client()

# Create message
messages = [
    LLMMessage(role="user", content="What is 2+2?")
]

# Generate response
response = await client.generate(messages)

print(response.content)      # "2+2 equals 4"
print(response.total_tokens) # Token count
print(response.provider)     # "claude" or "openai"
```

### With System Prompt

```python
messages = [
    LLMMessage(role="user", content="Classify: I need a refund")
]

response = await client.generate(
    messages,
    system_prompt="You are a ticket classifier. Respond with category only.",
    temperature=0.3,
    max_tokens=50
)
```

### Multi-turn Conversation

```python
messages = [
    LLMMessage(role="user", content="Hi"),
    LLMMessage(role="assistant", content="Hello! How can I help?"),
    LLMMessage(role="user", content="I forgot my password"),
]

response = await client.generate(messages)
```

## Providers

### Claude (Anthropic)

**Features**:
- Claude Opus 4, Sonnet 4, Haiku models
- System prompts (separate from messages)
- Extended context (200K tokens)
- Strong reasoning capabilities

**Configuration**:
```bash
LLM__CLAUDE__API_KEY=sk-ant-xxxxx
LLM__CLAUDE__MODEL=claude-sonnet-4-20250514
LLM__CLAUDE__TEMPERATURE=0.7
LLM__CLAUDE__MAX_TOKENS=4096
LLM__CLAUDE__TIMEOUT=60
```

**Token Counting**:
~4 characters per token (approximate)

### OpenAI (GPT)

**Features**:
- GPT-4 Turbo, GPT-4, GPT-3.5
- Function calling
- JSON mode
- Vision capabilities (future)

**Configuration**:
```bash
LLM__OPENAI__API_KEY=sk-xxxxx
LLM__OPENAI__MODEL=gpt-4-turbo-preview
LLM__OPENAI__TEMPERATURE=0.7
LLM__OPENAI__MAX_TOKENS=4096
LLM__OPENAI__TIMEOUT=60
```

**Token Counting**:
~4 characters per token (approximate)

### Provider Selection

**Claude Only**:
```bash
LLM__PROVIDER=claude
LLM__FALLBACK_ENABLED=false
```

**OpenAI Only**:
```bash
LLM__PROVIDER=openai
LLM__FALLBACK_ENABLED=false
```

**Both (Recommended)**:
```bash
LLM__PROVIDER=both
LLM__FALLBACK_ENABLED=true
# Claude is primary, OpenAI is fallback
```

## Usage Patterns

### Pattern 1: Agent Integration

```python
from src.llm import get_llm_client, LLMMessage
from config import get_system_prompt

class ClassificationAgent:
    def __init__(self):
        self.llm = get_llm_client()
        self.system_prompt = get_system_prompt("intake_agent")
    
    async def classify(self, message: str) -> str:
        """Classify a customer message."""
        messages = [LLMMessage(role="user", content=message)]
        
        response = await self.llm.generate(
            messages,
            system_prompt=self.system_prompt,
            temperature=0.3,  # Lower for classification
            max_tokens=100
        )
        
        return response.content
```

### Pattern 2: With Prompt Template

```python
from config import render_template

async def classify_ticket(message: str) -> str:
    """Classify ticket using template."""
    client = get_llm_client()
    
    # Render prompt from template
    prompt = render_template(
        "templates.classify_ticket",
        message=message,
        context=""
    )
    
    messages = [LLMMessage(role="user", content=prompt)]
    response = await client.generate(messages, temperature=0.3)
    
    return response.content
```

### Pattern 3: Streaming (Future)

```python
# Future enhancement for streaming responses
async def generate_streaming(messages: List[LLMMessage]):
    client = get_llm_client()
    
    async for chunk in client.generate_stream(messages):
        print(chunk.content, end="", flush=True)
```

### Pattern 4: Custom Provider

```python
# Create client with specific configuration
client = LLMClient(
    primary_provider="openai",
    fallback_enabled=False
)

response = await client.generate(messages)
```

### Pattern 5: Error Handling

```python
from tenacity import RetryError

async def safe_generate(messages):
    """Generate with comprehensive error handling."""
    try:
        client = get_llm_client()
        response = await client.generate(messages)
        return response.content
        
    except RetryError as e:
        logger.error(f"All retry attempts failed: {e}")
        # Escalate to human
        return None
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        # Fix configuration
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

## Configuration

### Environment Variables

All LLM settings are in `.env`:

```bash
# ============================================================================
# LLM CONFIGURATION
# ============================================================================

LLM__PROVIDER=both                    # claude, openai, both
LLM__FALLBACK_ENABLED=true
LLM__MAX_RETRIES=3
LLM__RETRY_DELAY=1.0

# Claude
LLM__CLAUDE__API_KEY=sk-ant-xxxxx
LLM__CLAUDE__MODEL=claude-sonnet-4-20250514
LLM__CLAUDE__MAX_TOKENS=4096
LLM__CLAUDE__TEMPERATURE=0.7
LLM__CLAUDE__TIMEOUT=60

# OpenAI
LLM__OPENAI__API_KEY=sk-xxxxx
LLM__OPENAI__MODEL=gpt-4-turbo-preview
LLM__OPENAI__MAX_TOKENS=4096
LLM__OPENAI__TEMPERATURE=0.7
LLM__OPENAI__TIMEOUT=60
```

### Retry Configuration

Built-in retry using `tenacity`:
- **Attempts**: 3 (configurable via settings.llm.max_retries)
- **Wait**: Exponential backoff (1s, 2s, 4s, ...)
- **Max wait**: 10 seconds

### Logging

Enable LLM call logging:
```bash
LOGGING__LOG_LLM_CALLS=true
LOGGING__LEVEL=INFO
```

Logs include:
- Provider used
- Model name
- Token counts
- Finish reason
- Fallback events

## Testing

### Run Tests

```bash
# All LLM tests
uv run pytest tests/unit/test_llm_client.py -v

# With coverage
uv run pytest tests/unit/test_llm_client.py --cov=src/llm

# Specific test
uv run pytest tests/unit/test_llm_client.py::TestLLMClient::test_generate_with_primary_success -v
```

### Test Coverage

Current coverage: **90%+**

Covered scenarios:
- Provider initialization
- Message generation
- Fallback on failure
- System prompt handling
- Token counting
- Statistics tracking
- Error handling

### Mock Testing

Tests use mocks to avoid actual API calls:

```python
@pytest.mark.asyncio
async def test_my_feature():
    with patch('src.llm.client.settings') as mock_settings:
        # Configure mock settings
        mock_settings.get_llm_client.return_value = "claude"
        
        client = LLMClient()
        client.primary_provider.generate = AsyncMock(
            return_value=mock_response
        )
        
        response = await client.generate(messages)
        assert response.content == "expected"
```

## Troubleshooting

### Issue: API Key Not Configured

**Error**:
```
ValueError: Claude API key not configured
```

**Solution**:
```bash
# Add to .env
LLM__CLAUDE__API_KEY=sk-ant-your-actual-key-here
```

### Issue: All Providers Failed

**Error**:
```
Exception: All LLM providers failed
```

**Causes & Solutions**:
1. **Network issues** - Check internet connectivity
2. **API quota exceeded** - Check provider dashboard
3. **Invalid API key** - Verify keys in .env
4. **Rate limiting** - Wait and retry

### Issue: Unexpected Fallback

**Symptom**: Always using fallback provider

**Solutions**:
1. Check primary provider API key
2. Review logs for error messages
3. Test primary provider independently:
   ```python
   client = LLMClient(primary_provider="claude", fallback_enabled=False)
   ```

### Issue: High Token Usage

**Solutions**:
1. Reduce `max_tokens` in requests
2. Use shorter system prompts
3. Trim conversation history
4. Monitor with `client.get_stats()`

### Issue: Slow Responses

**Causes**:
1. Large `max_tokens` setting
2. Long input messages
3. Complex reasoning required
4. Provider latency

**Solutions**:
1. Reduce max_tokens
2. Use faster models (Haiku, GPT-3.5)
3. Implement streaming (future)

## Best Practices

### 1. Use Global Client

```python
# ✅ Good - Reuse client
client = get_llm_client()

# ❌ Bad - Create new client each time
client = LLMClient()  # Don't do this repeatedly
```

### 2. Set Appropriate Temperature

```python
# Classification, extraction (deterministic)
response = await client.generate(messages, temperature=0.3)

# Creative writing, variation
response = await client.generate(messages, temperature=0.8)
```

### 3. Limit Max Tokens

```python
# Classification - short output
response = await client.generate(messages, max_tokens=100)

# Full response - longer output
response = await client.generate(messages, max_tokens=500)
```

### 4. Use System Prompts

```python
# ✅ Good - Clear instructions
system_prompt = "You are a classifier. Respond with category only."

# ❌ Bad - Instructions in user message
user_message = "Classify this: I need help. Also respond with just the category."
```

### 5. Handle Errors Gracefully

```python
try:
    response = await client.generate(messages)
except Exception as e:
    logger.error(f"LLM failed: {e}")
    # Fallback: escalate to human
    escalate_to_human(ticket)
```

### 6. Monitor Usage

```python
# Periodically check statistics
stats = client.get_stats()
logger.info(f"LLM stats: {stats}")

# Alert on high fallback rate
if stats['fallback_rate'] > 0.1:
    logger.warning("High fallback rate - check primary provider")
```

### 7. Test with Mocks

```python
# Don't make real API calls in tests
@pytest.mark.asyncio
async def test_agent():
    with patch('src.llm.get_llm_client') as mock_get_client:
        mock_client = Mock()
        mock_client.generate = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Test your code
```

## Summary

The LLM client system provides:
- ✅ Unified interface for Claude + OpenAI
- ✅ Automatic fallback on failures
- ✅ Retry logic with exponential backoff
- ✅ Comprehensive logging
- ✅ Token usage tracking
- ✅ Type-safe implementation
- ✅ Fully tested (90%+ coverage)

### Performance Characteristics

- **Average latency**: 1-3 seconds (depends on provider)
- **Retry attempts**: Up to 3 with exponential backoff
- **Fallback time**: ~1-2 seconds on failure
- **Token throughput**: Depends on provider limits

### Next Steps

1. Use in agent implementations
2. Monitor fallback rates
3. Tune temperature/max_tokens per use case
4. Implement streaming (future enhancement)

---

**Documentation Version:** 1.0  
**Last Updated:** 2024-12  
**Status:** ✅ Production Ready
