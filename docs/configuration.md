# Configuration System

Complete guide to the AI Customer Service configuration system.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Settings Reference](#settings-reference)
- [Prompt System](#prompt-system)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Validation](#validation)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The configuration system provides type-safe, validated configuration management using Pydantic Settings. It supports:

- **Multi-environment setup** (development, staging, production)
- **Type safety** with full IDE autocomplete
- **Secret management** (API keys never logged)
- **Multi-LLM support** (Claude + OpenAI with fallback)
- **Flexible prompt management** (YAML-based templates)
- **Comprehensive validation** (catch errors before they happen)

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `settings.py` | Main settings configuration | `config/settings.py` |
| `prompts.yaml` | Agent prompts and templates | `config/prompts.yaml` |
| `prompt_loader.py` | Prompt management system | `config/prompt_loader.py` |
| `.env.example` | Environment template | `.env.example` |
| Tests | Configuration tests | `tests/unit/test_config.py` |
| Validation | Config validation script | `scripts/validate_config.py` |

## Quick Start

### 1. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your actual values
nano .env  # or your preferred editor
```

### 2. Minimum Required Configuration

At minimum, you need these API keys in `.env`:

```bash
# LLM APIs (at least one required)
LLM__CLAUDE__API_KEY=sk-ant-your-actual-key-here
LLM__OPENAI__API_KEY=sk-your-actual-key-here
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Validate Configuration

```bash
# Run validation script
uv run python scripts/validate_config.py

# Expected output:
# ✅ All validation checks passed!
# ✨ Configuration is ready. You can start the application.
```

### 5. Run Tests

```bash
# Test configuration
uv run pytest tests/unit/test_config.py -v

# Expected: 30+ tests pass
```

### 6. Use in Your Code

```python
from config import settings, get_prompt

# Access settings
api_key = settings.llm.claude.api_key.get_secret_value()
model = settings.llm.claude.model

# Load prompts
system_prompt = get_prompt("system_prompts.intake_agent")
```

## Architecture

### Settings Hierarchy

```
Settings (root)
├── Application Settings
│   ├── app_name, app_version
│   ├── environment, debug
│   └── secret_key
├── LLM Settings
│   ├── provider (claude, openai, both)
│   ├── Claude Settings
│   │   ├── api_key, model
│   │   ├── max_tokens, temperature
│   │   └── timeout
│   ├── OpenAI Settings
│   │   ├── api_key, model
│   │   ├── max_tokens, temperature
│   │   ├── embedding_model
│   │   └── embedding_dimensions
│   └── Fallback & Retry
├── Database Settings
│   ├── PostgreSQL (url, pool_size, ...)
│   └── Redis (url, max_connections, ...)
├── Vector DB Settings
│   ├── provider (chromadb, qdrant)
│   ├── ChromaDB Settings
│   └── Qdrant Settings
├── Agent Settings
│   ├── Escalation config
│   ├── Knowledge retrieval
│   └── Response generation
├── API Settings
│   ├── Server config
│   ├── CORS
│   └── Rate limiting
└── Logging Settings
```

### Design Patterns

**1. Nested Settings with Pydantic**
```python
class Settings(BaseSettings):
    llm: LLMSettings
    database: DatabaseSettings
    # ...
```

**2. Environment Variable Mapping**
```bash
# Double underscore for nesting
LLM__CLAUDE__API_KEY → settings.llm.claude.api_key
DATABASE__POOL_SIZE → settings.database.pool_size
```

**3. Singleton Pattern**
```python
# Global instance
settings = Settings()

# Always returns same instance
def get_settings() -> Settings:
    return settings
```

**4. Secret Management**
```python
# Secrets use SecretStr (never logged)
api_key: SecretStr

# Access when needed
key = settings.llm.claude.api_key.get_secret_value()
```

## Settings Reference

### Application Settings

```python
settings.app_name: str              # Application name
settings.app_version: str           # Version number
settings.environment: Environment   # dev, staging, production
settings.debug: bool                # Debug mode flag
settings.secret_key: SecretStr      # Encryption key
settings.root_dir: Path             # Project root
settings.data_dir: Path             # Data directory
```

**Helper Properties:**
```python
settings.is_development: bool       # True if environment == development
settings.is_production: bool        # True if environment == production
```

### LLM Settings

```python
# Provider Selection
settings.llm.provider: LLMProvider  # claude, openai, both
settings.llm.fallback_enabled: bool # Enable fallback
settings.llm.max_retries: int       # Retry attempts
settings.llm.retry_delay: float     # Delay between retries

# Claude Configuration
settings.llm.claude.api_key: SecretStr
settings.llm.claude.model: str
settings.llm.claude.max_tokens: int
settings.llm.claude.temperature: float
settings.llm.claude.timeout: int

# OpenAI Configuration
settings.llm.openai.api_key: SecretStr
settings.llm.openai.model: str
settings.llm.openai.max_tokens: int
settings.llm.openai.temperature: float
settings.llm.openai.embedding_model: str
settings.llm.openai.embedding_dimensions: int
```

**Helper Methods:**
```python
settings.get_llm_client() -> str    # Returns "claude" or "openai"
```

### Database Settings

```python
# PostgreSQL
settings.database.url: str
settings.database.pool_size: int
settings.database.max_overflow: int
settings.database.pool_timeout: int
settings.database.echo: bool        # Log SQL queries

# Redis
settings.redis.url: str
settings.redis.max_connections: int
settings.redis.socket_timeout: int
settings.redis.decode_responses: bool
```

**Helper Properties:**
```python
settings.database.url_safe: str     # URL with password masked
```

### Vector DB Settings

```python
# Provider
settings.vector_db.provider: VectorDBProvider  # chromadb, qdrant
settings.vector_db.top_k: int                  # Results to retrieve
settings.vector_db.similarity_threshold: float # Min similarity

# ChromaDB (local development)
settings.vector_db.chromadb.path: str
settings.vector_db.chromadb.collection_name: str

# Qdrant (production)
settings.vector_db.qdrant.url: str
settings.vector_db.qdrant.api_key: SecretStr
settings.vector_db.qdrant.collection_name: str
settings.vector_db.qdrant.vector_size: int
```

### Agent Settings

```python
# Escalation
settings.agents.enable_escalation: bool
settings.agents.escalation_confidence_threshold: float
settings.agents.max_resolution_attempts: int

# Knowledge Retrieval
settings.agents.knowledge_confidence_threshold: float

# Response Generation
settings.agents.max_response_length: int
settings.agents.require_citations: bool
```

### API Settings

```python
settings.api.host: str
settings.api.port: int
settings.api.workers: int
settings.api.reload: bool           # Auto-reload on changes
settings.api.allowed_origins: list  # CORS origins
settings.api.rate_limit_per_minute: int
settings.api.rate_limit_per_hour: int
```

### Logging Settings

```python
settings.logging.level: str         # DEBUG, INFO, WARNING, ERROR
settings.logging.format: str        # json, text
settings.logging.log_file: str      # Path to log file
settings.logging.log_sql: bool
settings.logging.log_requests: bool
settings.logging.log_llm_calls: bool
```

## Prompt System

### Prompt Categories

**System Prompts** - Agent personalities and instructions
```python
from config import get_system_prompt

intake_prompt = get_system_prompt("intake_agent")
knowledge_prompt = get_system_prompt("knowledge_agent")
resolution_prompt = get_system_prompt("resolution_agent")
action_prompt = get_system_prompt("action_agent")
escalation_prompt = get_system_prompt("escalation_agent")
```

**Templates** - Reusable prompt components with variables
```python
from config import render_template

# Classify ticket
prompt = render_template(
    "templates.classify_ticket",
    message="I forgot my password",
    context=""
)

# Generate response
prompt = render_template(
    "templates.generate_response",
    message=user_message,
    knowledge=retrieved_docs,
    customer_tier="premium",
    ticket_count=5,
    sentiment="neutral"
)
```

**Error Messages**
```python
from config import get_prompt

error = get_prompt("error_messages.generic_error").format(
    ticket_id="TICKET-123"
)
```

**Greetings & Closings**
```python
greeting = get_prompt("greetings.first_time").format(
    customer_name="John",
    company_name="Acme Inc"
)

closing = get_prompt("closings.resolved")
```

### Prompt Loader API

```python
from config import get_prompt_loader

loader = get_prompt_loader()

# Get prompt by path
prompt = loader.get_prompt("system_prompts.intake_agent")

# Render template
rendered = loader.render_template(
    "templates.classify_ticket",
    message="Help!",
    context=""
)

# List available prompts
all_prompts = loader.list_prompts()
system_prompts = loader.list_prompts(prefix="system_prompts")

# Validate prompts
issues = loader.validate_prompts()

# Reload prompts (useful in development)
loader.reload()
```

### Adding New Prompts

1. Edit `config/prompts.yaml`
2. Add prompt under appropriate section
3. Use YAML multiline syntax (`|` or `>`)
4. Include variable placeholders: `{variable_name}`
5. Reload in development (automatic in production)

Example:
```yaml
templates:
  my_new_template: |
    This is a new template with {variable1} and {variable2}.
    It can span multiple lines.
```

Usage:
```python
prompt = render_template(
    "templates.my_new_template",
    variable1="value1",
    variable2="value2"
)
```

## Environment Variables

### Variable Naming Convention

Use double underscore (`__`) for nesting:

```bash
SECTION__SUBSECTION__KEY=value

# Examples:
LLM__CLAUDE__API_KEY=sk-ant-xxxxx
DATABASE__POOL_SIZE=10
AGENTS__ENABLE_ESCALATION=true
```

### Environment Files

**`.env`** - Your actual configuration (never commit!)
```bash
# Add to .gitignore
.env
.env.local
```

**`.env.example`** - Template for team (commit this!)
```bash
# Copy this to .env and fill in actual values
LLM__CLAUDE__API_KEY=sk-ant-xxxxx
```

### Loading Priority

1. Default values in code
2. `.env` file
3. Environment variables
4. Explicit overrides

```python
# This means environment variables override .env file values
```

### Common Configurations

**Local Development:**
```bash
ENVIRONMENT=development
DEBUG=true
VECTOR_DB__PROVIDER=chromadb
DATABASE__ECHO=true
API__RELOAD=true
```

**Production:**
```bash
ENVIRONMENT=production
DEBUG=false
VECTOR_DB__PROVIDER=qdrant
DATABASE__ECHO=false
API__RELOAD=false
```

## Testing

### Run All Configuration Tests

```bash
# All tests
uv run pytest tests/unit/test_config.py -v

# With coverage
uv run pytest tests/unit/test_config.py --cov=config

# Specific test class
uv run pytest tests/unit/test_config.py::TestSettings -v
```

### Test Categories

**Settings Tests** - Validate settings loading and validation
```bash
uv run pytest tests/unit/test_config.py::TestSettings -v
```

**Prompt Tests** - Validate prompt loading and rendering
```bash
uv run pytest tests/unit/test_config.py::TestPromptLoader -v
```

**Integration Tests** - Test settings + prompts together
```bash
uv run pytest tests/unit/test_config.py::TestConfigIntegration -v
```

### Expected Results

```
===================== test session starts ======================
collected 30 items

tests/unit/test_config.py::TestSettings::test_settings_singleton PASSED
tests/unit/test_config.py::TestSettings::test_default_values PASSED
[... 28 more tests ...]

===================== 30 passed in 0.5s =======================
```

## Validation

### Validation Script

```bash
# Run comprehensive validation
uv run python scripts/validate_config.py
```

### What Gets Validated

✅ **Settings Validation**
- API keys configured correctly
- Database connections valid
- Environment appropriate for mode
- All required settings present

✅ **Prompt Validation**
- Prompts file exists and loads
- All required prompts present
- No syntax errors in YAML
- Templates have valid variables
- No empty or malformed prompts

✅ **Directory Validation**
- Required directories exist
- Creates missing directories
- Correct permissions

### Validation Output

**Success:**
```
🔍 AI Customer Service - Configuration Validation

============================================================
  Validating Settings
============================================================

📍 Environment: development
   Debug mode: true

🤖 LLM Provider: both
✅ Claude API key configured
   Model: claude-sonnet-4-20250514
✅ OpenAI API key configured
   Model: gpt-4-turbo-preview

[... more checks ...]

============================================================
  Validation Summary
============================================================
✅ All validation checks passed!

✨ Configuration is ready. You can start the application.
```

**Failure:**
```
❌ Claude API key not configured
❌ Qdrant provider selected but not configured

⚠️  Please fix the issues above before starting the application.

💡 Tips for fixing settings:
   - Check your .env file
   - Ensure all required API keys are set
```

## Best Practices

### 1. Security

✅ **Do:**
- Use `.env` for secrets (never commit!)
- Use `SecretStr` for sensitive values
- Rotate API keys regularly
- Use different keys for dev/prod

❌ **Don't:**
- Commit `.env` to git
- Log API keys or secrets
- Use production keys in development
- Share keys in code or docs

### 2. Environment Management

✅ **Do:**
- Use `.env.example` as template
- Document all variables
- Validate on startup
- Use environment-specific values

❌ **Don't:**
- Hardcode configuration in code
- Mix dev and prod settings
- Skip validation
- Assume defaults are correct

### 3. Prompt Management

✅ **Do:**
- Use templates for reusable prompts
- Version control prompts.yaml
- Validate prompts on load
- Document variable requirements

❌ **Don't:**
- Hardcode prompts in code
- Skip variable validation
- Use bare string formatting
- Ignore validation warnings

### 4. Testing

✅ **Do:**
- Test configuration changes
- Validate before deploying
- Test with realistic values
- Test error cases

❌ **Don't:**
- Skip validation script
- Deploy without testing
- Assume defaults work
- Ignore test failures

## Troubleshooting

### Common Issues

**Issue: "Claude API key not configured"**
```bash
# Solution: Add to .env
LLM__CLAUDE__API_KEY=sk-ant-your-actual-key-here
```

**Issue: "Prompts file not found"**
```bash
# Solution: Ensure prompts.yaml exists
ls config/prompts.yaml

# If missing, copy from repo
```

**Issue: "Validation error for AgentState"**
```bash
# Solution: Check .env for typos
# Ensure variable names use __ for nesting
# Example: LLM__CLAUDE__API_KEY (not LLM_CLAUDE_API_KEY)
```

**Issue: "Missing template variables"**
```python
# Solution: Provide all required variables
render_template(
    "templates.classify_ticket",
    message="...",
    context=""  # ← Don't forget this!
)
```

**Issue: Database connection fails**
```bash
# Solution: Verify DATABASE__URL format
# Correct: postgresql+asyncpg://user:pass@host:5432/db
# Must include +asyncpg for async support
```

### Debug Mode

Enable debug logging:
```bash
LOGGING__LEVEL=DEBUG
DEBUG=true
```

Check loaded settings:
```python
from config import settings
print(settings.model_dump())  # Show all settings
```

Validate prompts:
```python
from config import get_prompt_loader
loader = get_prompt_loader()
issues = loader.validate_prompts()
print(issues)
```

### Getting Help

1. Run validation script: `uv run python scripts/validate_config.py`
2. Check test output: `uv run pytest tests/unit/test_config.py -v`
3. Review `.env.example` for correct format
4. Check logs for detailed errors

## Summary

The configuration system provides:
- ✅ Type-safe, validated settings
- ✅ Multi-environment support
- ✅ Secure secret management
- ✅ Flexible prompt templates
- ✅ Comprehensive validation
- ✅ Full test coverage

**Key Files:**
- `config/settings.py` - Main configuration
- `config/prompts.yaml` - Agent prompts
- `.env` - Your local settings
- `scripts/validate_config.py` - Validation

**Next Steps:**
1. Complete `.env` setup
2. Run validation: `uv run python scripts/validate_config.py`
3. Run tests: `uv run pytest tests/unit/test_config.py -v`
4. Start building agents using these settings!

---

**Documentation Version:** 1.0  
**Last Updated:** 2024-12  
**Status:** ✅ Production Ready
