"""
Unit test for LLM client.

Tests provider initialization, message generation, fallback logic, and token counting.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.llm import LLMClient, LLMMessage, LLMResponse
from src.llm.providers.claude import ClaudeProvider
from src.llm.providers.openai import OpenAIProvider
from src.llm.providers.gemini import GeminiProvider

class TestLLMMessage:
    """ Tests for LLMMessage dataclass. """

    def test_create_message(self):
        """ Test creating a message. """
        msg = LLMMessage(role = "user", content = "hello")

        assert msg.role == "user"
        assert msg.content == "hello"

class TestLLMResponse:
    """ Tests for LLMResponse dataclass. """

    def test_create_response(self):
        """Test creating a response."""
        response = LLMResponse(
            content="Hi there!",
            model="claude-3",
            provider="claude",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            finish_reason="stop",
            metadata={}
        )

        assert response.content == "Hi there!"
        assert response.total_tokens == 15
        assert response.provider == "claude"

class TestProviders:
    """Tests for individual providers."""
    
    def test_claude_provider_initialization(self):
        """Test Claude provider initialization."""
        provider = ClaudeProvider(
            api_key="test-key",
            model="claude-3"
        )
        
        assert provider.provider_name == "claude"
        assert provider.model == "claude-3"
    
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(
            api_key="test-key",
            model="gpt-4"
        )
        
        assert provider.provider_name == "openai"
        assert provider.model == "gpt-4"

    def test_gemini_provider_initialization(self):
        provider = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")
        assert provider.provider_name == "gemini"
        assert provider.model == "gemini-2.5-flash"

    def test_token_counting(self):
        """Test approximate token counting."""
        provider = ClaudeProvider(api_key="test", model="claude-3")
        
        # ~4 chars per token
        tokens = provider.count_tokens("Hello world")  # 11 chars
        assert 2 <= tokens <= 3  # Should be ~2.75

@pytest.mark.asyncio
class TestLLMClient:
    """Tests for main LLM client."""
    
    @pytest.fixture
    def mock_claude_response(self):
        """Mock Claude API response."""
        return LLMResponse(
            content="This is a test response",
            model="claude-sonnet-4",
            provider="claude",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            finish_reason="stop",
            metadata={"id": "test-123"}
        )

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        return LLMResponse(
            content="This is an OpenAI response",
            model="gpt-4",
            provider="openai",
            prompt_tokens=10,
            completion_tokens=6,
            total_tokens=16,
            finish_reason="stop",
            metadata={"id": "test-456"}
        )

    async def test_client_initialization_claude_primary(self):
        """Test client initialization with Claude as primary."""
        with patch('src.llm.client.settings') as mock_settings:
            mock_settings.get_llm_client.return_value = "claude"
            mock_settings.llm.fallback_enabled = True
            mock_settings.llm.provider.value = "both"
            mock_settings.llm.claude.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.claude.model = "claude-3"
            mock_settings.llm.claude.timeout = 60
            mock_settings.llm.openai.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.openai.model = "gpt-4"
            mock_settings.llm.openai.timeout = 60
            
            client = LLMClient()
            
            assert client.primary_provider_name == "claude"
            assert client.fallback_provider is not None

    async def test_generate_with_primary_success(self, mock_claude_response):
        """Test successful generation with primary provider."""
        with patch('src.llm.client.settings') as mock_settings:
            mock_settings.get_llm_client.return_value = "claude"
            mock_settings.llm.fallback_enabled = False
            mock_settings.llm.provider.value = "claude"
            mock_settings.llm.claude.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.claude.model = "claude-3"
            mock_settings.llm.claude.timeout = 60
            mock_settings.llm.claude.temperature = 0.7
            mock_settings.llm.claude.max_tokens = 1000
            mock_settings.logging.log_llm_calls = False
            
            client = LLMClient()
            
            # Mock the provider's generate method
            client.primary_provider.generate = AsyncMock(return_value=mock_claude_response)
            
            messages = [LLMMessage(role="user", content="Hello")]
            response = await client.generate(messages)
            
            assert response.content == "This is a test response"
            assert response.provider == "claude"
            assert client.total_calls == 1
            assert client.total_tokens == 15

    async def test_fallback_on_primary_failure(self, mock_openai_response):
        """Test fallback to secondary provider on primary failure."""
        with patch('src.llm.client.settings') as mock_settings:
            mock_settings.get_llm_client.return_value = "claude"
            mock_settings.llm.fallback_enabled = True
            mock_settings.llm.provider.value = "both"
            mock_settings.llm.claude.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.claude.model = "claude-3"
            mock_settings.llm.claude.timeout = 60
            mock_settings.llm.claude.temperature = 0.7
            mock_settings.llm.claude.max_tokens = 1000
            mock_settings.llm.openai.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.openai.model = "gpt-4"
            mock_settings.llm.openai.timeout = 60
            mock_settings.logging.log_llm_calls = False
            
            client = LLMClient()
            
            # Mock primary provider to fail
            client.primary_provider.generate = AsyncMock(
                side_effect=Exception("Primary provider failed")
            )
            
            # Mock fallback provider to succeed
            client.fallback_provider.generate = AsyncMock(return_value=mock_openai_response)
            
            messages = [LLMMessage(role="user", content="Hello")]
            
            # Should succeed with fallback despite retries
            with patch('src.llm.client.retry', lambda **kwargs: lambda f: f):
                response = await client.generate(messages)
            
            assert response.content == "This is an OpenAI response"
            assert response.provider == "openai"
            assert client.fallback_count == 1

    async def test_system_prompt_prepending(self, mock_claude_response):
        """Test that system prompts are prepended correctly."""
        with patch('src.llm.client.settings') as mock_settings:
            mock_settings.get_llm_client.return_value = "claude"
            mock_settings.llm.fallback_enabled = False
            mock_settings.llm.provider.value = "claude"
            mock_settings.llm.claude.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.claude.model = "claude-3"
            mock_settings.llm.claude.timeout = 60
            mock_settings.llm.claude.temperature = 0.7
            mock_settings.llm.claude.max_tokens = 1000
            mock_settings.logging.log_llm_calls = False
            
            client = LLMClient()
            client.primary_provider.generate = AsyncMock(return_value=mock_claude_response)
            
            messages = [LLMMessage(role="user", content="Hello")]
            await client.generate(messages, system_prompt="You are a helpful assistant")
            
            # Check that generate was called with system message prepended
            call_args = client.primary_provider.generate.call_args
            called_messages = call_args.kwargs['messages']
            
            assert called_messages[0].role == "system"
            assert called_messages[0].content == "You are a helpful assistant"
            assert called_messages[1].role == "user"

    async def test_token_counting(self):
        """Test token counting."""
        with patch('src.llm.client.settings') as mock_settings:
            mock_settings.get_llm_client.return_value = "claude"
            mock_settings.llm.fallback_enabled = False
            mock_settings.llm.provider.value = "claude"
            mock_settings.llm.claude.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.claude.model = "claude-3"
            mock_settings.llm.claude.timeout = 60
            
            client = LLMClient()
            
            tokens = client.count_tokens("Hello world")
            assert tokens > 0

    async def test_get_stats(self, mock_claude_response):
        """Test statistics tracking."""
        with patch('src.llm.client.settings') as mock_settings:
            mock_settings.get_llm_client.return_value = "claude"
            mock_settings.llm.fallback_enabled = False
            mock_settings.llm.provider.value = "claude"
            mock_settings.llm.claude.api_key.get_secret_value.return_value = "sk-test"
            mock_settings.llm.claude.model = "claude-3"
            mock_settings.llm.claude.timeout = 60
            mock_settings.llm.claude.temperature = 0.7
            mock_settings.llm.claude.max_tokens = 1000
            mock_settings.logging.log_llm_calls = False
            
            client = LLMClient()
            client.primary_provider.generate = AsyncMock(return_value=mock_claude_response)
            
            # Make a call
            messages = [LLMMessage(role="user", content="Hello")]
            await client.generate(messages)
            
            stats = client.get_stats()
            
            assert stats['total_calls'] == 1
            assert stats['total_tokens'] == 15
            assert stats['fallback_count'] == 0
            assert stats['primary_provider'] == 'claude'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    
