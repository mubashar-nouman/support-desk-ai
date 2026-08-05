"""
Unified LLM client with provider fallback.

This is the main interface for all LLM interactions in the application.
"""

import logging
from typing import List, Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings, settings
from .base import BaseProvider, LLMResponse, LLMMessage
from .providers.claude import ClaudeProvider
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified LLM client with automatic fallback.

    Features:
    - Provider agnostic interface
    - Automatic fallback on failure
    - Retry logic
    - Token usage tracking
    - Logging and observability

    Example:
        >>> client = LLMClient()
        >>> messages = [
        ...     LLMMessage(role="user", content="Hello!")
        ... ]
        >>> response = await client.generate(messages)
        >>> print(response.content)

    """

    def __init__(
        self,
        primary_provider: Optional[str] = None,
        fallback_enabled: bool = True
    ):
        """
        Initialize LLM client.

        Args:
            primary_provider: Primary provider to use ('claude', 'openai', or None for config)
            fallback_enabled: Enable fallback to secondary provider.
        """

        self.fallback_enabled = fallback_enabled and settings.llm.fallback_enabled

        # Determine providers based on config
        if primary_provider:
            self.primary_provider_name = primary_provider
        else:
            self.primary_provider_name = settings.get_llm_client()

        # Initialize providers
        self.primary_provider = self._create_provider(self.primary_provider_name)

        # Setup fallback provider
        self.fallback_provider = None
        if self.fallback_enabled and settings.llm.provider.value == "both":
            fallback_name = "openai" if self.primary_provider_name == "claude" else "claude"
            try:
                self.fallback_provider = self._create_provider(fallback_name)
                logger.info(
                    f"LLM client initialized: primary={self.primary_provider_name}, "
                    f"fallback={fallback_name}"
                )
            except Exception as e:
                logger.warning(f"Fallback provider {fallback_name} not available: {e}")
                self.fallback_provider = None

        else:
            logger.info(f"LLM client initialized: primary={self.primary_provider_name}, no fallback")

       # Tracking
        self.total_calls = 0
        self.total_tokens = 0
        self.fallback_count = 0

    def _create_provider(self, provider_name: str) -> BaseProvider:
        """
        Create a provider instance.

        Args:
            provider_name: Provider name ('claude' or 'openai')
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is invalid or not configured

        """
        if provider_name == "claude":
            api_key = settings.llm.claude.api_key.get_secret_value()
            # key already validated by Pydantic in Settings
            return ClaudeProvider(
                api_key=api_key,
                model=settings.llm.claude.model,
                timeout=settings.llm.claude.timeout
            )

        elif provider_name == "openai":
            api_key = settings.llm.openai.api_key.get_secret_value()
            # key already validated by Pydantic in Settings
            return OpenAIProvider(
                api_key=api_key,
                model=settings.llm.openai.model,
                timeout=settings.llm.openai.timeout
            )
        elif provider_name == "gemini":
            return GeminiProvider(
                api_key=settings.llm.gemini.api_key.get_secret_value(),
                model=settings.llm.gemini.model,
                timeout=settings.llm.gemini.timeout,
            )
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion with automatic fallback.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature (uses config default if None)
            max_tokens: Maximum tokens (uses config default if None)
            system_prompt: System prompt to prepend
            **kwargs: Provider-specific parameters
            
        Returns:
            LLM response
            
        Raises:
            Exception: If all providers fail
        """

        # Add system prompt if provided
        if system_prompt:
            messages = [LLMMessage(role="system", content=system_prompt)] + messages

        # Use config defaults if not specified
        if temperature is None:
            temperature = settings.llm.claude.temperature
        if max_tokens is None:
            max_tokens = settings.llm.claude.max_tokens

        # Try primary provider
        try:
            response = await self._generate_with_provider(
                self.primary_provider,
                messages,
                temperature,
                max_tokens,
                **kwargs
            )
            
            self._log_success(self.primary_provider.provider_name, response)
            return response
            
        except Exception as e:
            logger.warning(
                f"Primary provider {self.primary_provider_name} failed: {e}",
                exc_info=True
            )

            # Try fallback if enabled
            if self.fallback_provider:
                logger.info(f"Attempting fallback to {self.fallback_provider.provider_name}")
                self.fallback_count += 1
                
                try:
                    response = await self._generate_with_provider(
                        self.fallback_provider,
                        messages,
                        temperature,
                        max_tokens,
                        **kwargs
                    )
                    
                    self._log_success(self.fallback_provider.provider_name, response, is_fallback=True)
                    return response
                    
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback provider {self.fallback_provider.provider_name} also failed: {fallback_error}",
                        exc_info=True
                    )
            
            # All providers failed
            raise Exception(f"All LLM providers failed. Last error: {e}")
    
    async def _generate_with_provider(
        self,
        provider: BaseProvider,
        messages: List[LLMMessage],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """
        Generate with a specific provider.
        
        Args:
            provider: Provider instance
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Provider-specific parameters
            
        Returns:
            LLM response
        """
        if settings.logging.log_llm_calls:
            logger.debug(
                f"Calling {provider.provider_name} with {len(messages)} messages, "
                f"temp={temperature}, max_tokens={max_tokens}"
            )
        
        response = await provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response
    
    def _log_success(
        self,
        provider_name: str,
        response: LLMResponse,
        is_fallback: bool = False
    ) -> None:
        """Log successful LLM call."""
        self.total_calls += 1
        self.total_tokens += response.total_tokens
        
        fallback_msg = " (fallback)" if is_fallback else ""
        
        if settings.logging.log_llm_calls:
            logger.info(
                f"LLM call successful{fallback_msg}: provider={provider_name}, "
                f"model={response.model}, tokens={response.total_tokens}, "
                f"finish={response.finish_reason}"
            )
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using primary provider.
        
        Args:
            text: Text to count
            
        Returns:
            Approximate token count
        """
        return self.primary_provider.count_tokens(text)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "fallback_count": self.fallback_count,
            "fallback_rate": (
                self.fallback_count / self.total_calls 
                if self.total_calls > 0 else 0
            ),
            "primary_provider": self.primary_provider_name,
            "fallback_enabled": self.fallback_enabled
        }
    
    def __repr__(self) -> str:
        return (
            f"LLMClient(primary={self.primary_provider_name}, "
            f"fallback={self.fallback_provider.provider_name if self.fallback_provider else None})"
        )

# Global client instance (optional - can also create per-request)
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get global LLM client instance (singleton).
    
    Returns:
        LLM client instance
        
    Example:
        >>> client = get_llm_client()
        >>> response = await client.generate(messages)
    """
    global _client
    if _client is None:
        _client = LLMClient()
    return _client   

