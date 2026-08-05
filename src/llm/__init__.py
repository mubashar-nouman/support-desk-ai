"""
LLM client module.

Provides unified interface for interacting with LLM providers (Claude, OpenAI)
with automatic fallback and retry logic.

Usage:
    from src.llm import get_llm_client, LLMMessage
    
    client = get_llm_client()
    messages = [LLMMessage(role="user", content="Hello!")]
    response = await client.generate(messages)
"""

from .client import LLMClient, get_llm_client
from .base import LLMResponse, LLMMessage, BaseProvider

__all__ = [
    "LLMClient",
    "get_llm_client",
    "LLMResponse",
    "LLMMessage",
    "BaseProvider",
]