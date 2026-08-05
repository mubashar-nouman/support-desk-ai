"""Google Gemini provider implementation."""

from typing import List

from google import genai
from google.genai import types

from ..base import BaseProvider, LLMMessage, LLMResponse


class GeminiProvider(BaseProvider):
    """Google Gemini provider using the async GenAI client."""

    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(self, messages: List[LLMMessage], temperature: float = 0.7,
                       max_tokens: int = 1000, **kwargs) -> LLMResponse:
        system_instruction = None
        contents = []
        for message in messages:
            if message.role == "system":
                system_instruction = message.content
            else:
                contents.append(types.Content(
                    role="model" if message.role == "assistant" else "user",
                    parts=[types.Part.from_text(text=message.content)],
                ))

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
            **kwargs,
        )
        response = await self.client.aio.models.generate_content(
            model=self.model, contents=contents, config=config
        )
        usage = response.usage_metadata
        finish_reason = str(response.candidates[0].finish_reason) if response.candidates else "stop"
        return LLMResponse(
            content=response.text or "",
            model=self.model,
            provider=self.provider_name,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            total_tokens=getattr(usage, "total_token_count", 0) or 0,
            finish_reason=finish_reason,
            metadata={"response": response},
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
