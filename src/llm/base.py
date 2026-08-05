"""
Base LLM provider interface.

All LLM providers must implement this interface.
"""

from abc import ABC, abstractmethod
from importlib.resources import contents
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """
    Standardized LLM response format.

    All providers return this format for consistency.
    """
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str
    metadata: Dict[str, Any]

@dataclass
class LLMMessage:
    """
    Message format for LLM conversations.

    Attributes:
        role: Message role (user, assistant, system)
        content: Message content
    """
    role: str
    content: str

class BaseProvider(ABC):
    """
    Abstact base class for LLM providers.

    All provider implementations (Claude, OpenAI) inherit from this.
    """
    def __init__(self, api_key: str, model: str, **kwargs):
        """
        Initialize provider.

        Args:
            api_key: Provider API Key
            model: Model identifier
            **kwargs: Provider specific settings
        """
        self.api_key = api_key
        self.model = model
        self.settings = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """ Return provider name (e.g. 'claude', 'openai'). """
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from messages.

        Args:
            messages: Conversation History
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            Standardized LLM response

        Raises:
            Exception: On provider errors
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Approximate token count
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model = {self.model})"