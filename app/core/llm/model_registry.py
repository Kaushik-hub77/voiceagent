"""
Model registry for managing LLM providers and models
"""

from typing import Dict, Any, Optional, Type
import yaml
import os

from app.core.llm.base import LLMClient
from app.core.llm.openai_client import OpenAIClient
from app.core.config.settings import settings
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """Registry for LLM models and providers"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.config = self._load_config()
        
        # Load model definitions from config
        self.models = self.config.get("models", {})
        
        # Load pipeline-specific configurations
        self.pipeline_models = self.config.get("pipeline_models", {})
        self.pipeline_configs = self.config.get("pipeline_configs", {})
        
        # Set default model from config (config is source of truth)
        self.default_model = self.config.get("default_model", "gpt-4-turbo")
        
        # Validate default model exists in config
        if self.default_model not in self.models:
            logger.warning(
                f"Default model '{self.default_model}' not found in config, "
                f"falling back to first available model"
            )
            self.default_model = list(self.models.keys())[0] if self.models else "gpt-3.5-turbo"
        
        # Initialize providers after models/default are set
        self.providers = self._initialize_providers()

        logger.info(
            "Model registry initialized",
            default_model=self.default_model,
            available_models=len(self.models),
            pipeline_configs=len(self.pipeline_models)
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from YAML file"""
        config_path = os.getenv(
            "MODEL_CONFIG_PATH",
            "app/core/config/model_config.yaml"
        )

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Model config loaded", path=config_path)
                return config
        except Exception as e:
            logger.error("Failed to load model config", error=str(e), path=config_path)
            # Return minimal fallback config
            return {
                "default_model": "gpt-3.5-turbo",
                "models": {},
                "providers": {}
            }

    def _initialize_providers(self) -> Dict[str, LLMClient]:
        """Initialize LLM provider clients"""

        providers = {}
        provider_configs = self.config.get("providers", {})

        # OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        if openai_api_key:
            try:
                openai_config = provider_configs.get("openai", {})
                openai_config["models"] = {
                    name: config for name, config in self.models.items()
                    if config.get("provider") == "openai"
                }
                providers["openai"] = OpenAIClient(
                    api_key=openai_api_key,
                    config=openai_config
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI provider", error=str(e))

        # Anthropic (placeholder)
        if os.getenv("ANTHROPIC_API_KEY"):
            logger.info("Anthropic provider configuration found (not implemented yet)")

        # Google (placeholder)
        if os.getenv("GOOGLE_API_KEY"):
            logger.info("Google provider configuration found (not implemented yet)")

        return providers

    def get_client(self, model_name: str) -> Optional[LLMClient]:
        """
        Get the appropriate client for a model

        Args:
            model_name: Name of the model

        Returns:
            LLM client instance or None if not available
        """

        model_config = self.models.get(model_name)
        if not model_config:
            logger.warning("Model not found in registry", model=model_name)
            return None

        provider_name = model_config.get("provider")
        if not provider_name:
            logger.warning("No provider specified for model", model=model_name)
            return None

        client = self.providers.get(provider_name)
        if not client:
            logger.warning(
                "Provider not available",
                provider=provider_name,
                model=model_name
            )
            return None

        return client

    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model"""
        return self.models.get(model_name)

    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """List all available models with their configurations"""
        available_models = {}

        for model_name, model_config in self.models.items():
            provider_name = model_config.get("provider")
            if provider_name and provider_name in self.providers:
                available_models[model_name] = model_config

        return available_models

    def get_default_model(self) -> str:
        """Get the default model name"""
        return self.default_model

    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available"""
        model_config = self.models.get(model_name)
        if not model_config:
            return False

        provider_name = model_config.get("provider")
        return provider_name in self.providers

    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """Get the provider name for a model"""
        model_config = self.models.get(model_name)
        return model_config.get("provider") if model_config else None

    def get_model_for_pipeline(self, pipeline_name: str) -> str:
        """
        Get the recommended model for a specific pipeline
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Model name to use for the pipeline
        """
        pipeline_config = self.pipeline_models.get(pipeline_name)
        
        if not pipeline_config:
            logger.debug(
                f"No specific model config for pipeline '{pipeline_name}', using default"
            )
            return self.default_model
        
        # Try primary model first
        primary_model = pipeline_config.get("primary")
        if primary_model and self.is_model_available(primary_model):
            logger.debug(
                f"Using primary model for pipeline",
                pipeline=pipeline_name,
                model=primary_model
            )
            return primary_model
        
        # Fallback to fallback model
        fallback_model = pipeline_config.get("fallback")
        if fallback_model and self.is_model_available(fallback_model):
            logger.info(
                f"Primary model not available, using fallback",
                pipeline=pipeline_name,
                primary=primary_model,
                fallback=fallback_model
            )
            return fallback_model
        
        # Last resort: use default
        logger.warning(
            f"Neither primary nor fallback model available for pipeline, using default",
            pipeline=pipeline_name,
            default=self.default_model
        )
        return self.default_model

    def get_pipeline_config(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get LLM configuration parameters for a specific pipeline
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Configuration dictionary with temperature, max_tokens, etc.
        """
        config = self.pipeline_configs.get(pipeline_name)
        
        if not config:
            logger.debug(
                f"No specific config for pipeline '{pipeline_name}', using general"
            )
            config = self.pipeline_configs.get("general", {})
        
        return {
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 2000),
            "top_p": config.get("top_p", 0.95),
            "frequency_penalty": config.get("frequency_penalty"),
            "presence_penalty": config.get("presence_penalty"),
        }

    def list_pipeline_configurations(self) -> Dict[str, Dict[str, Any]]:
        """List all pipeline configurations"""
        return {
            pipeline_name: {
                "model": self.pipeline_models.get(pipeline_name, {}),
                "config": self.pipeline_configs.get(pipeline_name, {})
            }
            for pipeline_name in set(
                list(self.pipeline_models.keys()) + list(self.pipeline_configs.keys())
            )
        }

    async def health_check_all_providers(self) -> Dict[str, bool]:
        """Check health of all providers"""
        results = {}

        for provider_name, client in self.providers.items():
            try:
                is_healthy = await client.health_check()
                results[provider_name] = is_healthy
            except Exception as e:
                logger.error(
                    "Provider health check failed",
                    provider=provider_name,
                    error=str(e)
                )
                results[provider_name] = False

        return results
