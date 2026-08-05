"""
OpenAI provider implementation.
"""

import openai
from typing import List, Dict, Any

from ..base import BaseProvider, LLMResponse, LLMMessage


class OpenAIProvider(BaseProvider):
    """
    OpenAI LLM provider.
    
    Implements the BaseProvider interface for GPT models.
    """
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize OpenAI provider."""
        super().__init__(api_key, model, **kwargs)
        self.client = openai.AsyncOpenAI(api_key=api_key)
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using OpenAI.
        
        Converts our standard format to OpenAI's format.
        """
        # Convert our messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        choice = response.choices[0]
        
        # Convert OpenAI response to our standard format
        return LLMResponse(
            content=choice.message.content,
            model=response.model,
            provider=self.provider_name,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            finish_reason=choice.finish_reason,
            metadata={
                "id": response.id,
                "created": response.created
            }
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Approximate token count for OpenAI.
        
        GPT models use ~4 chars per token on average.
        """
        return len(text) // 4