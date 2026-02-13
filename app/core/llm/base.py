"""
Base LLM client interface and common functionality
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass
import time

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM requests"""
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List[str]] = None


@dataclass
class LLMResponse:
    """Standardized response from LLM calls"""
    content: str
    model: str
    usage: Dict[str, int]  # tokens used
    finish_reason: str
    processing_time: float
    raw_response: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        config: LLMConfig,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using the LLM

        Args:
            prompt: The input prompt
            config: Configuration for the request
            **kwargs: Additional provider-specific parameters

        Returns:
            Standardized LLM response
        """
        pass

    @abstractmethod
    def get_token_limit(self, model: str) -> int:
        """Get the token limit for a specific model"""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximate)"""
        pass

    async def stream_generate(
        self,
        prompt: str,
        config: LLMConfig,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream tokens/text from the LLM.
        Default implementation indicates streaming is not supported.
        """
        raise NotImplementedError("Streaming not implemented for this provider")

    async def health_check(self) -> bool:
        """Check if the LLM provider is healthy"""
        try:
            # Simple health check with minimal prompt
            response = await self.generate(
                prompt="Hello",
                config=LLMConfig(model=self.config.get("default_model", "gpt-3.5-turbo"))
            )
            return len(response.content.strip()) > 0
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False


class LLMClientError(Exception):
    """Base exception for LLM client errors"""
    pass


class RateLimitError(LLMClientError):
    """Rate limit exceeded"""
    pass


class AuthenticationError(LLMClientError):
    """Authentication failed"""
    pass


class ModelNotFoundError(LLMClientError):
    """Requested model not found"""
    pass


class TokenLimitError(LLMClientError):
    """Token limit exceeded"""
    pass
