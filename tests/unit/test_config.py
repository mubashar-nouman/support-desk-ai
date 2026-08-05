"""
Unit tests for configuration system.

Tests settings loading, validation, and prompt management.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from config import (
    settings,
    get_settings,
    Settings,
    Environment,
    LLMProvider,
    VectorDBProvider,
    get_prompt,
    render_template,
    get_system_prompt,
    PromptLoader,
)


class TestSettings:
    """Tests for Settings configuration."""
    
    def test_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
        assert s1 is settings
    
    def test_default_values(self):
        """Test default configuration values."""
        assert settings.app_name == "AI Customer Service"
        assert settings.environment in [
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION
        ]
        assert settings.llm.provider in [
            LLMProvider.CLAUDE,
            LLMProvider.OPENAI,
            LLMProvider.BOTH
        ]
    
    def test_environment_properties(self):
        """Test environment helper properties."""
        # These depend on actual environment, just test they work
        assert isinstance(settings.is_development, bool)
        assert isinstance(settings.is_production, bool)
    
    def test_llm_settings(self):
        """Test LLM configuration."""
        assert hasattr(settings.llm, 'claude')
        assert hasattr(settings.llm, 'openai')
        assert settings.llm.fallback_enabled in [True, False]
        assert settings.llm.max_retries >= 0
    
    def test_claude_settings(self):
        """Test Claude configuration."""
        claude = settings.llm.claude
        assert claude.model is not None
        assert 0 <= claude.temperature <= 1.0
        assert claude.max_tokens > 0
        assert claude.timeout > 0
    
    def test_openai_settings(self):
        """Test OpenAI configuration."""
        openai = settings.llm.openai
        assert openai.model is not None
        assert 0 <= openai.temperature <= 2.0
        assert openai.max_tokens > 0
        assert openai.embedding_model is not None
        assert openai.embedding_dimensions > 0
    
    def test_database_settings(self):
        """Test database configuration."""
        db = settings.database
        assert db.url is not None
        assert db.pool_size > 0
        assert db.max_overflow >= 0
        assert isinstance(db.echo, bool)
    
    def test_database_url_masking(self):
        """Test that database URL masks password."""
        db = settings.database
        safe_url = db.url_safe
        
        # If URL has password, it should be masked
        if "@" in db.url and ":" in db.url.split("@")[0]:
            assert "****" in safe_url
            # Password should not appear in safe URL
            if "password" in db.url:
                assert "password" not in safe_url or "****" in safe_url
    
    def test_redis_settings(self):
        """Test Redis configuration."""
        redis = settings.redis
        assert redis.url is not None
        assert redis.max_connections > 0
    
    def test_vector_db_settings(self):
        """Test vector database configuration."""
        vdb = settings.vector_db
        assert vdb.provider in [
            VectorDBProvider.CHROMADB,
            VectorDBProvider.QDRANT
        ]
        assert vdb.top_k > 0
        assert 0 <= vdb.similarity_threshold <= 1.0
    
    def test_agent_settings(self):
        """Test agent configuration."""
        agents = settings.agents
        assert isinstance(agents.enable_escalation, bool)
        assert 0 <= agents.escalation_threshold <= 1.0
        assert agents.max_resolution_attempts > 0
        assert agents.max_response_length > 0
    
    def test_api_settings(self):
        """Test API configuration."""
        api = settings.api
        assert api.host is not None
        assert 1024 <= api.port <= 65535
        assert api.workers > 0
        assert isinstance(api.allowed_origins, list)
    
    def test_logging_settings(self):
        """Test logging configuration."""
        logging = settings.logging
        assert logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert logging.format in ["json", "text"]
    
    def test_paths(self):
        """Test path configuration."""
        assert isinstance(settings.root_dir, Path)
        assert isinstance(settings.data_dir, Path)
        assert settings.root_dir.exists()
    
    def test_get_llm_client(self):
        """Test LLM client selection."""
        client = settings.get_llm_client()
        assert client in ["claude", "openai"]


class TestPromptLoader:
    """Tests for prompt loading and management."""
    
    @pytest.fixture
    def loader(self):
        """Create a PromptLoader instance."""
        return PromptLoader()
    
    def test_load_prompts(self, loader):
        """Test that prompts load successfully."""
        prompts = loader.prompts
        assert isinstance(prompts, dict)
        assert len(prompts) > 0
    
    def test_get_system_prompt(self, loader):
        """Test getting system prompts."""
        prompt = loader.get_system_prompt("intake_agent")
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert "Intake Agent" in prompt
    
    def test_get_system_prompt_all_agents(self, loader):
        """Test all agent system prompts exist."""
        agents = [
            "intake_agent",
            "knowledge_agent",
            "resolution_agent",
            "action_agent",
            "escalation_agent"
        ]
        
        for agent in agents:
            prompt = loader.get_system_prompt(agent)
            assert isinstance(prompt, str)
            assert len(prompt) > 50
    
    def test_get_prompt_by_path(self, loader):
        """Test getting prompts by dot-notation path."""
        prompt = loader.get_prompt("system_prompts.intake_agent")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    
    def test_get_prompt_invalid_path(self, loader):
        """Test that invalid paths raise KeyError."""
        with pytest.raises(KeyError):
            loader.get_prompt("nonexistent.path")
        
        with pytest.raises(KeyError):
            loader.get_prompt("system_prompts.nonexistent_agent")
    
    def test_render_template(self, loader):
        """Test template rendering with variables."""
        rendered = loader.render_template(
            "templates.classify_ticket",
            message="I forgot my password",
            context="User tried logging in 3 times"
        )
        
        assert isinstance(rendered, str)
        assert "I forgot my password" in rendered
        assert "{message}" not in rendered  # Variable should be substituted
    
    def test_render_template_missing_variable(self, loader):
        """Test that missing variables raise ValueError."""
        with pytest.raises(ValueError, match="Missing template variables"):
            loader.render_template(
                "templates.classify_ticket",
                message="Test"
                # Missing 'context' variable
            )
    
    def test_get_error_message(self, loader):
        """Test getting error messages."""
        error = loader.get_error_message(
            "generic_error",
            ticket_id="TICKET-123"
        )
        
        assert isinstance(error, str)
        assert "TICKET-123" in error
    
    def test_get_greeting(self, loader):
        """Test getting greeting messages."""
        greeting = loader.get_greeting(
            "first_time",
            customer_name="John",
            company_name="Acme Inc"
        )
        
        assert isinstance(greeting, str)
        assert "John" in greeting
    
    def test_get_closing(self, loader):
        """Test getting closing messages."""
        closing = loader.get_closing(
            "escalated",
            sla_time="2 hours",
            ticket_id="TICKET-123"
        )
        
        assert isinstance(closing, str)
        assert "2 hours" in closing
        assert "TICKET-123" in closing
    
    def test_list_prompts(self, loader):
        """Test listing all prompts."""
        all_prompts = loader.list_prompts()
        assert isinstance(all_prompts, list)
        assert len(all_prompts) > 0
        assert "system_prompts.intake_agent" in all_prompts
    
    def test_list_prompts_with_prefix(self, loader):
        """Test listing prompts with prefix filter."""
        system_prompts = loader.list_prompts(prefix="system_prompts")
        assert all(p.startswith("system_prompts") for p in system_prompts)
        assert len(system_prompts) >= 5  # We have 5 agent system prompts
    
    def test_validate_prompts(self, loader):
        """Test prompt validation."""
        issues = loader.validate_prompts()
        
        # Should be a dict
        assert isinstance(issues, dict)
        
        # Ideally no issues, but if there are, they should be categorized
        if issues:
            valid_categories = [
                'empty_prompts',
                'unmatched_braces',
                'suspiciously_short',
                'load_errors'
            ]
            for category in issues.keys():
                assert category in valid_categories
    
    def test_caching(self, loader):
        """Test that caching works."""
        # First call
        prompt1 = loader.get_cached_prompt("system_prompts.intake_agent")
        
        # Second call should be cached
        prompt2 = loader.get_cached_prompt("system_prompts.intake_agent")
        
        assert prompt1 == prompt2
        assert prompt1 is prompt2  # Same object reference (cached)
    
    def test_reload_prompts(self, loader):
        """Test prompt reloading."""
        prompt1 = loader.get_prompt("system_prompts.intake_agent")
        
        # Reload
        loader.reload()
        
        prompt2 = loader.get_prompt("system_prompts.intake_agent")
        
        # Content should be the same
        assert prompt1 == prompt2


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_get_prompt_function(self):
        """Test get_prompt convenience function."""
        prompt = get_prompt("system_prompts.intake_agent")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    
    def test_render_template_function(self):
        """Test render_template convenience function."""
        rendered = render_template(
            "templates.assess_sentiment",
            message="I'm so frustrated!"
        )
        assert isinstance(rendered, str)
        assert "frustrated" in rendered
    
    def test_get_system_prompt_function(self):
        """Test get_system_prompt convenience function."""
        prompt = get_system_prompt("resolution_agent")
        assert isinstance(prompt, str)
        assert "Resolution Agent" in prompt


class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_settings_and_prompts_together(self):
        """Test using settings and prompts together."""
        # Get LLM settings
        llm_provider = settings.get_llm_client()
        
        # Get agent prompt
        prompt = get_system_prompt("intake_agent")
        
        # Both should work
        assert llm_provider in ["claude", "openai"]
        assert isinstance(prompt, str)
    
    def test_all_required_prompts_exist(self):
        """Test that all prompts referenced in settings exist."""
        required_prompts = [
            "system_prompts.intake_agent",
            "system_prompts.knowledge_agent",
            "system_prompts.resolution_agent",
            "system_prompts.action_agent",
            "system_prompts.escalation_agent",
        ]
        
        for prompt_path in required_prompts:
            prompt = get_prompt(prompt_path)
            assert isinstance(prompt, str)
            assert len(prompt) > 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])