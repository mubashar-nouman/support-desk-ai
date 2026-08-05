#!/usr/bin/env python3
"""
Validate configuration and prompts.

Run this script to ensure your configuration is correct before starting the app.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, get_prompt_loader
from pydantic import SecretStr


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print('=' * 60)


def print_success(text: str) -> None:
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"❌ {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"⚠️  {text}")


def validate_settings() -> bool:
    """
    Validate application settings.
    
    Returns:
        True if all settings are valid
    """
    print_header("Validating Settings")
    
    all_valid = True
    
    # Check environment
    print(f"\n📍 Environment: {settings.environment.value}")
    print(f"   Debug mode: {settings.debug}")
    
    if settings.is_production and settings.debug:
        print_warning("Debug mode is enabled in production!")
        all_valid = False
    
    # Check LLM configuration
    print(f"\n🤖 LLM Provider: {settings.llm.provider.value}")
    selected_provider = settings.llm.provider.value
    
    # Claude
    claude_key = settings.llm.claude.api_key.get_secret_value()
    if claude_key and claude_key != "sk-ant-xxxxx":
        print_success(f"Claude API key configured")
        print(f"   Model: {settings.llm.claude.model}")
    elif selected_provider in ("claude", "both"):
        print_error("Claude API key not configured")
        all_valid = False
    
    # OpenAI
    openai_key = settings.llm.openai.api_key.get_secret_value()
    if openai_key and openai_key != "sk-xxxxx":
        print_success(f"OpenAI API key configured")
        print(f"   Model: {settings.llm.openai.model}")
        print(f"   Embedding: {settings.llm.openai.embedding_model}")
    elif selected_provider == "openai":
        print_error("OpenAI API key not configured")
        all_valid = False

    # Gemini
    gemini_key = settings.llm.gemini.api_key.get_secret_value()
    if gemini_key and gemini_key != "your-gemini-api-key":
        print_success("Gemini API key configured")
        print(f"   Model: {settings.llm.gemini.model}")
    elif selected_provider == "gemini":
        print_error("Gemini API key not configured")
        all_valid = False
    
    # Database
    print(f"\n💾 Database: {settings.database.url_safe}")
    print(f"   Pool size: {settings.database.pool_size}")
    
    if "localhost" in settings.database.url and settings.is_production:
        print_warning("Using localhost database in production!")
    
    # Redis
    print(f"\n🔴 Redis: {settings.redis.url}")
    print(f"   Max connections: {settings.redis.max_connections}")
    
    # Vector DB
    print(f"\n📊 Vector DB: {settings.vector_db.provider.value}")
    
    if settings.vector_db.provider.value == "chromadb":
        path = settings.vector_db.chromadb.path if settings.vector_db.chromadb else "Not configured"
        print(f"   ChromaDB path: {path}")
        if settings.is_production:
            print_warning("Using ChromaDB in production (consider Qdrant)")
    elif settings.vector_db.provider.value == "qdrant":
        if settings.vector_db.qdrant:
            print(f"   Qdrant URL: {settings.vector_db.qdrant.url}")
        else:
            print_error("Qdrant provider selected but not configured")
            all_valid = False
    
    # Agents
    print(f"\n🤖 Agents:")
    print(f"   Escalation enabled: {settings.agents.enable_escalation}")
    print(f"   Confidence threshold: {settings.agents.escalation_threshold}")
    print(f"   Max attempts: {settings.agents.max_resolution_attempts}")
    
    # API
    print(f"\n🌐 API:")
    print(f"   Host: {settings.api.host}:{settings.api.port}")
    print(f"   Workers: {settings.api.workers}")
    print(f"   CORS origins: {len(settings.api.allowed_origins)} configured")
    
    # Logging
    print(f"\n📝 Logging:")
    print(f"   Level: {settings.logging.level}")
    print(f"   Format: {settings.logging.format}")
    
    return all_valid


def validate_prompts() -> bool:
    """
    Validate prompts configuration.
    
    Returns:
        True if all prompts are valid
    """
    print_header("Validating Prompts")
    
    loader = get_prompt_loader()
    
    # Check that prompts file exists
    if not loader.prompts_path.exists():
        print_error(f"Prompts file not found: {loader.prompts_path}")
        return False
    
    print_success(f"Prompts file found: {loader.prompts_path}")
    
    # List all prompts
    all_prompts = loader.list_prompts()
    print(f"\n📄 Total prompts: {len(all_prompts)}")
    
    # Check system prompts
    print("\n🤖 System Prompts:")
    system_prompts = loader.list_prompts(prefix="system_prompts")
    for prompt_path in system_prompts:
        agent_name = prompt_path.split('.')[-1]
        try:
            prompt = loader.get_prompt(prompt_path)
            print_success(f"{agent_name}: {len(prompt)} characters")
        except Exception as e:
            print_error(f"{agent_name}: {e}")
            return False
    
    # Check templates
    print("\n📝 Templates:")
    templates = loader.list_prompts(prefix="templates")
    print(f"   Found {len(templates)} templates")
    
    # Validate prompts
    print("\n🔍 Running validation checks...")
    issues = loader.validate_prompts()
    
    if not issues:
        print_success("All prompts validated successfully!")
        return True
    
    # Report issues
    print_warning("Found some issues:")
    for issue_type, items in issues.items():
        print(f"\n   {issue_type}:")
        for item in items:
            print(f"   - {item}")
    
    return False


def validate_directories() -> bool:
    """
    Validate required directories exist.
    
    Returns:
        True if all directories exist or were created
    """
    print_header("Validating Directories")
    
    required_dirs = [
        settings.root_dir,
        settings.data_dir,
        settings.data_dir / "knowledge_base",
        settings.data_dir / "embeddings",
    ]
    
    all_valid = True
    
    for directory in required_dirs:
        if directory.exists():
            print_success(f"{directory.relative_to(settings.root_dir)}")
        else:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                print_success(f"{directory.relative_to(settings.root_dir)} (created)")
            except Exception as e:
                print_error(f"{directory.relative_to(settings.root_dir)}: {e}")
                all_valid = False
    
    return all_valid


def main():
    """Run all validation checks."""
    print("\n🔍 AI Customer Service - Configuration Validation")
    
    # Run validations
    settings_valid = validate_settings()
    prompts_valid = validate_prompts()
    dirs_valid = validate_directories()
    
    # Final summary
    print_header("Validation Summary")
    
    if settings_valid and prompts_valid and dirs_valid:
        print_success("All validation checks passed!")
        print("\n✨ Configuration is ready. You can start the application.")
        return 0
    else:
        print_error("Some validation checks failed!")
        print("\n⚠️  Please fix the issues above before starting the application.")
        
        if not settings_valid:
            print("\n💡 Tips for fixing settings:")
            print("   - Check your .env file")
            print("   - Ensure all required API keys are set")
            print("   - Verify database connection strings")
        
        if not prompts_valid:
            print("\n💡 Tips for fixing prompts:")
            print("   - Check config/prompts.yaml for syntax errors")
            print("   - Ensure all required prompts exist")
            print("   - Fix any validation issues reported above")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
