"""
LLM provider implementations.

Available providers:
- Claude (Anthropic)
- OpenAI (GPT)
- Gemini (Google)

Each provider module imports its vendor SDK at module level, so they are
resolved lazily through ``__getattr__`` (PEP 562). Importing this package
therefore does not require every SDK to be installed - only the one belonging
to the provider actually being used. This keeps serverless bundles small.
"""

from ..base import BaseProvider, LLMResponse, LLMMessage

_PROVIDER_MODULES = {
    "ClaudeProvider": ".claude",
    "OpenAIProvider": ".openai",
    "GeminiProvider": ".gemini",
}


def __getattr__(name: str):
    module_name = _PROVIDER_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module_name, __name__), name)


__all__ = [
    "BaseProvider",
    "LLMResponse",
    "LLMMessage",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
]
