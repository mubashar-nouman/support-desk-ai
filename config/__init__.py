"""
Configuration package for AI Customer Service.

Provides centralized access to settings and prompts.

Usage:
    from config import settings, get_prompt, render_template
    
    # Access settings
    api_key = settings.llm.claude.api_key.get_secret_value()
    db_url = settings.database.url
    
    # Get prompts
    system_prompt = get_prompt("system_prompts.intake_agent")
    
    # Render templates
    prompt = render_template(
        "templates.classify_ticket",
        message="I need help",
        context=""
    )
"""

from .settings import (
    # Settings instance
    settings,
    get_settings,
    
    # Settings classes (for type hints)
    Settings,
    LLMSettings,
    DatabaseSettings,
    RedisSettings,
    VectorDBSettings,
    AgentSettings,
    APISettings,
    LoggingSettings,
    
    # Enums
    Environment,
    LLMProvider,
    VectorDBProvider,
)

from .prompt_loader import (
    # Prompt loader
    get_prompt_loader,
    
    # Convenience functions
    get_prompt,
    render_template,
    get_system_prompt,
    reload_prompts,
    
    # Class for advanced usage
    PromptLoader,
)

__all__ = [
    # Settings
    "settings",
    "get_settings",
    "Settings",
    "LLMSettings",
    "DatabaseSettings",
    "RedisSettings",
    "VectorDBSettings",
    "AgentSettings",
    "APISettings",
    "LoggingSettings",
    
    # Enums
    "Environment",
    "LLMProvider",
    "VectorDBProvider",
    
    # Prompts
    "get_prompt_loader",
    "get_prompt",
    "render_template",
    "get_system_prompt",
    "reload_prompts",
    "PromptLoader",
]