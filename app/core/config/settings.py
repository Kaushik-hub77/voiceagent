"""
Application settings and configuration
"""

import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""

    # Application
    APP_NAME: str = "AI LLM Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Security
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    APP_TOKEN_SHARED_SECRET: str = "traineryone"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:8000", 
        "http://127.0.0.1:8000", 
        "http://127.0.0.1:3000",
        "https://apps.traineryhcm.com",
        "https://traineryhcm.com"  # Main domain
    ]
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # Trusted hosts
    TRUSTED_HOSTS: Optional[List[str]] = None

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"

    # LLM Providers - API Keys only (sensitive data)
    # Model selection and configuration is managed in model_config.yaml
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Sarvam voice (TTS) provider
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_TARGET_LANGUAGE_CODE: str = "en-IN"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_SPEAKER: str = "shubh"

    # External services
    EXTERNAL_API_BASE_URL: Optional[str] = None

    # Database (placeholder for future use)
    DATABASE_URL: Optional[str] = None

    # Redis (for caching/rate limiting)
    REDIS_URL: Optional[str] = None

    # Feature flags
    ENABLE_DRAFT_ASSISTANCE: bool = True
    ENABLE_BIAS_CHECKER: bool = True
    ENABLE_REVIEW_SUMMARIZER: bool = True

    # Model configuration file
    MODEL_CONFIG_PATH: str = "app/core/config/model_config.yaml"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "allow",
    }

    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value"""
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()

    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    @field_validator('TRUSTED_HOSTS', mode='before')
    @classmethod
    def parse_trusted_hosts(cls, v):
        """Parse trusted hosts from comma-separated string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',') if host.strip()]
        return v


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
