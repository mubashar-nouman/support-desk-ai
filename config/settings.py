"""
Configuration settings for the AI Customer Service application.

This module provides type-safe, validated configuration management using Pydantic Settings.
All settings can be overridden via environment variables.

Usage :
    from config import settings

    api_key = settings.llm.claude.api_key
    db_url = settings.database.url

"""

from email.policy import default
from enum import Enum
import os
from os import path
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# ENUMS
# ============================================================

class Environment(str, Enum):
    """ Application Environment """
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LLMProvider(str, Enum):
    """ LLM provider options. """
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    BOTH = "both" # Claude primary, OpenAI fallback

class VectorDBProvider(str, Enum):
    """ Vector database provider. """
    CHROMADB = "chromadb" # local environment
    QDRANT = "qdrant" # production

# ============================================================
# LLM Configuration
# ============================================================

class ClaudeSettings(BaseSettings):
    """ Anthropic Claude configuration. """

    api_key: SecretStr = Field(
        ...,
        description = "Anthropic API Key"
    )
    model: str = Field(
        default = "claude-sonnet-4-20250514",
        description = "Claude model to use"
    )
    max_tokens: int = Field(
        default = 4096,
        ge = 1,
        le = 200000,
        description = "Maximum tokens in response"
    )
    temperature: float = Field(
        default = 0.7,
        ge = 0.0,
        le = 1.0,
        description = "Sampling temperature"
    )
    timeout: int = Field(
        default = 60,
        ge = 1,
        description = "Request timeout in seconds"
    )

    model_config = SettingsConfigDict(
        env_prefix = "LLM__CLAUDE__",
        case_sensitive = False
    )

    @field_validator('api_key', mode='after')
    @classmethod
    def validate_api_key(cls, v: SecretStr, info) -> SecretStr:
        """Validate Claude API key format."""
        key = v.get_secret_value()

        # Only require a real key when Claude is selected or used as fallback.
        if os.getenv("LLM__PROVIDER", "both").lower() == "gemini":
            return v

        # Skip validation in test mode
        if os.getenv('SKIP_API_KEY_VALIDATION') == 'true':
            return v
        
        if not key or not key.strip():
            raise ValueError("Claude API key cannot be empty")
        
        # Check for placeholders
        placeholders = ["xxxxx", "your-key", "placeholder", "change-me"]
        if any(p in key.lower() for p in placeholders):
            raise ValueError(
                "Claude API key appears to be a placeholder. "
                "Set LLM__CLAUDE__API_KEY in .env"
            )

        # Validate format
        if not key.startswith("sk-ant-"):
            raise ValueError("Invalid Claude API key format (should start with 'sk-ant-')")
        
        return v      

class OpenAISettings(BaseSettings):
    """ OpenAI configuration """

    api_key: SecretStr = Field(
        ...,
        description = "OpenAI API key"
    )
    model: str = Field(
        default = "gpt-4-turbo-preview",
        description = "OpenAI model to use"
    )
    max_tokens: int = Field(
        default = 4096,
        ge = 1,
        le = 128000,
        description = "Maximum tokens in response"
    )
    temperature: float = Field(
        default = 0.7,
        ge = 0.0,
        le = 2.0,
        description = "Sampling temperatrure"
    )
    timeout: int = Field(
        default = 60,
        ge = 1,
        description = "Request timeout in seconds"
    )
    embedding_model: str = Field(
        default = "text-embedding-3-small",
        description = "Embedding model for vectors"
    )
    embedding_dimensions: int = Field(
        default = 1536,
        description = "Embedding vector dimensions"
    )
    
    model_config = SettingsConfigDict(
        env_prefix = "LLM__OPENAI__",
        case_sensitive = False
    )

    @field_validator('api_key', mode = 'after')
    @classmethod
    def validate_api_key(cls, v: SecretStr, info) -> SecretStr:
        """Validate OpenAI API key format."""
        key = v.get_secret_value()

        # Only require a real key when OpenAI is selected or used as fallback.
        if os.getenv("LLM__PROVIDER", "both").lower() == "gemini":
            return v

        # Skip validation in test mode
        if os.getenv('SKIP_API_KEY_VALIDATION') == 'true':
            return v
        
        if not key or not key.strip():
            raise ValueError("OpenAI API key cannot be empty")
        
        placeholders = ["xxxxx", "your-key", "placeholder", "change-me"]
        if any(p in key.lower() for p in placeholders):
            raise ValueError(
                "OpenAI API key appears to be a placeholder. "
                "Set LLM__OPENAI__API_KEY in .env"
            )
        
        if not key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format (should start with 'sk-')")
        
        return v

class GeminiSettings(BaseSettings):
    """Google Gemini configuration."""

    api_key: SecretStr = Field(..., description="Google Gemini API key")
    model: str = Field(default="gemini-2.5-flash", description="Gemini model to use")
    max_tokens: int = Field(default=4096, ge=1, le=65536)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: int = Field(default=60, ge=1)

    model_config = SettingsConfigDict(env_prefix="LLM__GEMINI__", case_sensitive=False)

    @field_validator("api_key", mode="after")
    @classmethod
    def validate_api_key(cls, v: SecretStr, info) -> SecretStr:
        import os
        key = v.get_secret_value()
        if os.getenv("SKIP_API_KEY_VALIDATION") == "true":
            return v
        if not key or not key.strip():
            raise ValueError("Gemini API key cannot be empty")
        if any(p in key.lower() for p in ("xxxxx", "your-key", "placeholder", "change-me")):
            raise ValueError("Gemini API key appears to be a placeholder. Set LLM__GEMINI__API_KEY in .env")
        return v

class LLMSettings(BaseSettings):
    """ LLM provider configuration. """

    provider: LLMProvider = Field(
        default = LLMProvider.BOTH,
        description = "Which LLM provider(s) to use"
    )
    claude: ClaudeSettings
    openai: OpenAISettings
    gemini: GeminiSettings

    fallback_enabled: bool = Field(
        default = True,
        description = "Enable fallback to secondary provider"
    )
    max_retries: int = Field(
        default = 3,
        ge = 0,
        description = "Maximum retry attempts"
    )
    retry_delay: float = Field(
        default = 1.0,
        ge = 0.0,
        description = "Delay between retries in seconds"
    )

    model_config = SettingsConfigDict(
        env_prefix = "LLM__",
        case_sensitive = False
    )

# ==================================================================
# DATABASE CONFIGURATION
# ==================================================================

class DatabaseSettings(BaseSettings):
    """ PostgresSQL database configuration. """

    url: str = Field(
        default = "postgresql+asyncpg://user:password@localhost:5432/customer_service",
        description = "Database connection URL"
    )
    pool_size: int = Field(
        default = 10,
        ge = 1,
        le = 100,
        description = "Connection pool size"
    )
    max_overflow: int = Field(
        default = 20,
        ge = 0,
        description = "Maximum overflow connections."
    )
    pool_timeout: int = Field(
        default = 30,
        ge = 1,
        description = "Pool checkout timeout in seconds"
    )
    echo: bool = Field(
        default = False,
        description = "Log all SQL statements"
    )

    model_config = SettingsConfigDict(
        env_prefix = "DATABASE__",
        case_sensitive = False
    )

    @property
    def url_safe(self) -> str:
        """ Get URL with password masked for logging. """
        if "@" in self.url:
            parts = self.url.split("@")
            if "://" in parts[0]:
                protocol, credentials = parts[0].split("://")
                if ":" in credentials:
                    user, _ = credentials.split(":", 1)
                    return f"{protocol}://{user}:****@{parts[1]}"
        return self.url

class RedisSettings(BaseSettings):
    """ Redis configuration for caching and state management. """

    url: str = Field(
        default = "redis://localhost:6379/0",
        description = "Redis connection URL"
    )
    max_connections: int = Field(
        default = 50,
        ge = 1,
        description = "Maximum connection pool size"
    )
    socket_timeout: int = Field(
        default = 5,
        ge = 1,
        description = "Socket timeout in seconds"
    )
    socket_connect_timeout: int = Field(
        default = 5,
        ge = 1,
        description = "Socket connect timeout in seconds"
    )

    model_config = SettingsConfigDict(
        env_prefix = "REDIS__",
        case_sensitive = False,
        extra = "ignore"
    )

# ===========================================================
# Vector Database Configuration 
# ===========================================================

class ChromaDBSettings(BaseSettings):
    """ ChromaDB configuration (for local development) """

    path: str = Field(
        default = "./data/chroma",
        description = "Path to ChromaDB storage"
    )
    collection_name: str = Field(
        default = "customer_service_kb",
        description = "Collection name for knowledge base"
    )

    model_config = SettingsConfigDict(
        env_prefix = "VECTOR_DB__CHROMADB__",
        case_sensitive = False
    )

class QdrantSettings(BaseSettings):
    """ Qdrant configuration (for production). """

    url: str = Field(
        ...,
        description = "Qdrant server URL"
    )
    api_key: Optional[SecretStr] = Field(
        None,
        description = "Qdrant API key for (for cloud)"
    )
    collection_name: str = Field(
        default = "customer_service_kb",
        description = "Collection name for knowledge base"
    )
    vector_size: int = Field(
        default = 1536,
        description = "Vector dimensions (must match embedding model)"
    )

    model_config = SettingsConfigDict(
        env_prefix = "VECTOR_DB__QDRANT__",
        case_sensitive = False
    )

class VectorDBSettings(BaseSettings):
    """ Vector database configuration. """

    provider: VectorDBProvider = Field(
        default = VectorDBProvider.CHROMADB,
        description = "Vector DB provider"
    )
    chromadb: Optional[ChromaDBSettings] = None
    qdrant: Optional[QdrantSettings] = None

    top_k: int = Field(
        default = 5,
        ge = 1,
        le = 50,
        description = "Number of results to retrieve"
    )
    similarity_threshold: float = Field(
        default = 0.7,
        ge = 0.0,
        le = 1.0,
        description = "Minimum similarity score for results"
    )

    model_config = SettingsConfigDict(
        env_prefix = "VECTOR_DB__",
        case_sensitive = False
    )

    def model_post_init(self, __context) -> None:
        """Validate provider configuration after initialization."""
        # Ensure the selected provider has configuration
        if self.provider == VectorDBProvider.CHROMADB:
            if self.chromadb is None:
                self.chromadb = ChromaDBSettings()
        elif self.provider == VectorDBProvider.QDRANT:
            if self.qdrant is None:
                raise ValueError(
                    "Qdrant configuration required when VECTOR_DB__PROVIDER=qdrant. "
                    "Please set VECTOR_DB__QDRANT__URL and other Qdrant settings."
                )

# ============================================================================
# Agent Configuration
# ============================================================================

class AgentSettings(BaseSettings):
    """ Agent behaviour configuration . """

    # Escalation settings
    enable_escalation: bool = Field(
        default = True,
        description = "Enable automatic escalation to humans"
    )
    escalation_threshold: float = Field(
        default = 0.8,
        ge = 0.0,
        le = 1.0,
        description = "Confidence threshold for escalation"
    )
    max_resolution_attempts: int = Field(
        default = 3,
        ge = 1,
        description = "Max attempts before escalating"
    )

    # Knowledge retrieval
    knowledge_threshold: float = Field(
        default = 0.7,
        ge = 0.0,
        le = 1.0,
        description = "Minimum confidence for using knowledge"
    )

    # Response generation
    max_response_length: int = Field(
        default = 500,
        ge = 50,
        le = 2000,
        description = "Maximum response length in words"
    )
    require_citations: bool = Field(
        default = True,
        description = "Require citations in resoponse"
    )

    model_config = SettingsConfigDict(
        env_prefix = "AGENTS__",
        case_sensitive = False,
        extra="ignore"
    )

# ============================================================================
# API Configuration
# ============================================================================

class APISettings(BaseSettings):
    """ API server configuration. """

    host: str = Field(
        default = "0.0.0.0", 
        description = "API server host"
    )
    port: int = Field(
        default = 8000,
        ge = 1024,
        le = 65535,
        description = "API server port"
    )
    workers: int = Field(
        default = 4,
        ge = 1,
        description = "Number of worker processes"
    )
    reload: bool = Field(
        default = False,
        description = "Enable auto-reload (dev only)"
    )

    # CORS
    allowed_origins: list[str] = Field(
        default = ["http://localhost:3000", "http://localhost:8000"],
        description = "Allowed CORS origins"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(
        default = 60,
        ge = 1,
        description = "Requests per minute per IP"
    )
    rate_limit_per_hour: int = Field(
        default = 1000,
        ge = 1,
        description = "Requests per hour per IP"
    )

    model_config = SettingsConfigDict(
        env_prefix = "API__",
        case_sensitive = False
    )

# ============================================================================
# Logging Configuration
# ============================================================================

class LoggingSettings(BaseSettings):
    """ Logging configuration. """

    level: str = Field(
        default = "INFO",
        description = "Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default = "json",
        description = "Log format (json or text)"
    )
    log_file: Optional[str] = Field(
        None,
        description = "Log file path (None for stdout only)"
    )

    # What to log
    log_sql: bool = Field(
        default = False,
        description = "Log SQL queries"
    )
    log_requests: bool = Field(
        default = True,
        description = "Log API requests"
    )
    log_llm_calls: bool = Field(
        default = True,
        description = "Log LLM API calls"
    )

    model_config = SettingsConfigDict(
        env_prefix = "LOGGING__",
        case_sensitive = False
    )

# ============================================================================
# Main Settings
# ============================================================================

class Settings(BaseSettings):
    """
    Main application settings.

    All settings can be overridden via environment variables using the double
    underscore notation. (e.g. LLM__CLAUDE__API_KEY).

    Example:
        export LLM__CLAUDE__API_KEY="sk-..."
        export DATABASE__URL="postgressql://..."
    """

    # Application
    app_name: str = Field(
        default = "AI Customer Service",
        description = "Application name"
    )
    app_version: str = Field(
        default = "0.1.0",
        description = "Application version"
    )
    environment: Environment = Field(
        default = False,
        description = "Runtime environment"
    )
    debug: bool = Field(
        default = False,
        description = "Debug mode"
    )
    secret_key: SecretStr = Field(
        default = "change-me-in-production",
        description = "Secret key for encryption"
    )

    # Component Settings
    llm: LLMSettings
    database: DatabaseSettings = Field(default_factory = DatabaseSettings)
    redis: RedisSettings = Field(default_factory = RedisSettings)
    vector_db: VectorDBSettings
    agents: AgentSettings = Field(default_factory = AgentSettings)
    api: APISettings = Field(default_factory = APISettings)
    logging: LoggingSettings = Field(default_factory = LoggingSettings)

    # Paths
    root_dir: Path = Field(
        default_factory = lambda: Path(__file__).parent.parent,
        description = "Project root directory"
    )
    data_dir: Path = Field(
        default_factory = lambda: Path(__file__).parent.parent,
        description = "Project root directory"
    )
    data_dir: Path = Field(
        default_factory = lambda: Path(__file__).parent.parent / "data",
        description = "Data directory"
    )

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        env_nested_delimiter = "__",
        case_sensitive = False,
        extra = "ignore"
    )

    @field_validator('debug', mode = 'after')
    @classmethod
    def validate_debug_mode(cls, v, info):
        """ Warn if debug is enabled in production. """
        environment = info.data.get('environment')
        if v and environment == Environment.PRODUCTION:
            import warnings
            warnings.warn("Debug mode is enabled in production environment")
        return v

    @property
    def is_development(self) -> bool:
        """ Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """ Check if running in production mode. """
        return self.environment == Environment.PRODUCTION

    def get_llm_client(self) -> str:
        """ Get primary LLM provider. """
        if self.llm.provider == LLMProvider.OPENAI:
            return "openai"
        if self.llm.provider == LLMProvider.GEMINI:
            return "gemini"
        return "claude" # Claude is default for BOTH and CLAUDE

# ===================================================================
# SETTINGS INSTANCE
# ===================================================================

# Global settings instance - import this throughout the app
settings = Settings()

# Convinience function for dependency injection.
def get_settings() -> Settings:
    """
    Get settings instance (useful for FastAPI dependency injection).

    Example:
        @app.get("/health")
        def health(settings: Settings = Depends(get_settings)):
            return {'status': "ok", "environment": settings.environment}
    """
    return settings
