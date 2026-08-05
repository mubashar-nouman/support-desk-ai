"""
Anthropic Claude provider implementation.
"""

import anthropic
from typing import List, Dict, Any

from ..base import BaseProvider, LLMResponse, LLMMessage

class ClaudeProvider(BaseProvider):
    """
    Anthropic Claude LLM provider.

    Implements the BaseProvider interface for Claude Models.
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        """ Initialize Claude Provider. """
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.AsyncAnthropic(api_key = api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    async def generate(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7, 
        max_tokens: int = 1000, 
        **kwargs) -> LLMResponse:
        """
        Generate completion using Claude.

        Converts our standard format to Claude's format.
        """

        # Convert our messages to Claude format.
        claude_messages = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                claude_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content
                    }
                )

        # Call Claude API
        kwargs_for_api = {
            "model": self.model,
            "messages": claude_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if system_prompt:
            kwargs_for_api["system"] = system_prompt

        response = await self.client.messages.create(**kwargs_for_api)

        # Convert Claude response to our standard format
        return LLMResponse(
            content = response.content[0].text,
            model = response.model,
            provider = self.provider_name,
            prompt_tokens = response.usage.input_tokens,
            completion_tokens = response.usage.output_tokens,
            total_tokens = response.usage.input_tokens + response.usage.output_tokens,
            finish_reason = response.stop_reason,
            metadata = {
                "id": response.id,
                "type": response.type
            }
        )

    def count_tokens(self, text: str) -> int:
        """
        Approximate token count for Claude.

        Claude iuses ~4 chars per token on an average.
        """
        return len(text) // 4