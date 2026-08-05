# LLM Client Module

Quick reference for the LLM client system. See [full documentation](../../docs/llm.md) for details.

## 📁 Files

```
src/llm/
├── __init__.py           # Package exports
├── client.py             # Main LLM client
├── providers/
│   ├── __init__.py
│   ├── base.py          # Base provider interface
│   ├── claude.py        # Anthropic Claude
│   └── openai.py        # OpenAI GPT
└── README.md            # This file
```

## 🚀 Quick Start

### Basic Usage

```python
from src.llm import get_llm_client, LLMMessage

# Get client instance
client = get_llm_client()

# Create messages
messages = [
    LLMMessage(role="user", content="What is the capital of France?")
]

# Generate response
response = await client.generate(messages)
print(response.content)  # "Paris is the capital of France..."
```

### With System Prompt

```python
messages = [
    LLMMessage(role="user", content="Classify this ticket")
]

response = await client.generate(
    messages,
    system_prompt="You are a ticket classification agent.",
    temperature=0.3,
    max_tokens=500
)
```

### Multi-turn Conversation

```python
messages = [
    LLMMessage(role="user", content="Hello!"),
    LLMMessage(role="assistant", content="Hi! How can I help?"),
    LLMMessage(role="user", content="I need password help")
]

response = await client.generate(messages)
```

## 🔧 Key Features

### 1. Automatic Fallback

```python
# Configured in .env:
# LLM__PROVIDER=both
# LLM__FALLBACK_ENABLED=true

# Client automatically tries fallback on failure
client = get_llm_client()  # Claude primary, OpenAI fallback
```

### 2. Retry Logic

Built-in retry with exponential backoff (3 attempts):
```python
# Automatically retries on transient failures
response = await client.generate(messages)
```

### 3. Token Counting

```python
text = "This is a sample message"
token_count = client.count_tokens(text)
print(f"Estimated tokens: {token_count}")
```

### 4. Usage Statistics

```python
stats = client.get_stats()
print(stats)
# {
#     'total_calls': 10,
#     'total_tokens': 5000,
#     'fallback_count': 1,
#     'fallback_rate': 0.1,
#     'primary_provider': 'claude'
# }
```

## 📊 Response Format

All providers return standardized `LLMResponse`:

```python
@dataclass
class LLMResponse:
    content: str              # Generated text
    model: str                # Model used
    provider: str             # Provider name
    prompt_tokens: int        # Input tokens
    completion_tokens: int    # Output tokens
    total_tokens: int         # Total tokens
    finish_reason: str        # Why it stopped
    metadata: Dict[str, Any]  # Provider-specific data
```

## 🔌 Provider Support

### Claude (Anthropic)
- Models: `claude-sonnet-4-20250514`, `claude-opus-4`, etc.
- Features: System prompts, function calling
- Token counting: ~4 chars/token

### OpenAI (GPT)
- Models: `gpt-4-turbo-preview`, `gpt-4`, etc.
- Features: System messages, function calling
- Token counting: ~4 chars/token

## ⚙️ Configuration

Set in `.env`:

```bash
# Provider selection
LLM__PROVIDER=both              # claude, openai, or both
LLM__FALLBACK_ENABLED=true

# Claude
LLM__CLAUDE__API_KEY=sk-ant-xxxxx
LLM__CLAUDE__MODEL=claude-sonnet-4-20250514
LLM__CLAUDE__TEMPERATURE=0.7
LLM__CLAUDE__MAX_TOKENS=4096

# OpenAI
LLM__OPENAI__API_KEY=sk-xxxxx
LLM__OPENAI__MODEL=gpt-4-turbo-preview
LLM__OPENAI__TEMPERATURE=0.7
LLM__OPENAI__MAX_TOKENS=4096
```

## 🧪 Testing

```bash
# Run LLM tests
uv run pytest tests/unit/test_llm_client.py -v

# With coverage
uv run pytest tests/unit/test_llm_client.py --cov=src/llm
```

## 🎯 Common Patterns

### Agent Integration

```python
from src.llm import get_llm_client, LLMMessage
from config import get_system_prompt

class MyAgent:
    def __init__(self):
        self.llm = get_llm_client()
        self.system_prompt = get_system_prompt("intake_agent")
    
    async def process(self, user_message: str):
        messages = [LLMMessage(role="user", content=user_message)]
        response = await self.llm.generate(
            messages,
            system_prompt=self.system_prompt
        )
        return response.content
```

### Error Handling

```python
try:
    response = await client.generate(messages)
except Exception as e:
    logger.error(f"LLM generation failed: {e}")
    # Handle failure (e.g., escalate to human)
```

### Custom Provider

```python
# Create client with specific provider
client = LLMClient(primary_provider="openai", fallback_enabled=False)
```

## 📚 Full Documentation

For complete documentation including:
- Architecture details
- Provider implementation guide
- Advanced usage patterns
- Troubleshooting

See: **[docs/llm.md](../../docs/llm.md)**

## ✅ Checklist

Before using in production:
- [ ] API keys configured in `.env`
- [ ] Provider selection appropriate (both recommended)
- [ ] Temperature/max_tokens tuned for use case
- [ ] Error handling implemented
- [ ] Token usage monitored
- [ ] Tests passing

---

**Status:** ✅ Production Ready  
**Test Coverage:** 90%+  
**Last Updated:** 2024-12
