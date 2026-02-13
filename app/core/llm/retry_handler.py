"""
Retry handler for LLM API calls with exponential backoff
"""

import asyncio
import random
from typing import Callable, Any, Optional
import time

from app.core.llm.base import RateLimitError, AuthenticationError, LLMClientError
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


class RetryHandler:
    """Handles retries for LLM API calls"""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            Exception: Last exception if all retries fail
        """

        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                logger.debug(
                    "Attempting function call",
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts
                )

                result = await func(*args, **kwargs)
                return result

            except RateLimitError as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, is_rate_limit=True)
                    logger.warning(
                        "Rate limit hit, retrying",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Rate limit retries exhausted", error=str(e))
                    raise

            except AuthenticationError as e:
                # Don't retry authentication errors
                logger.error("Authentication error, not retrying", error=str(e))
                raise

            except LLMClientError as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, is_rate_limit=False)
                    logger.warning(
                        "LLM client error, retrying",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Client error retries exhausted", error=str(e))
                    raise

            except Exception as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, is_rate_limit=False)
                    logger.warning(
                        "Unexpected error, retrying",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Unexpected error retries exhausted", error=str(e))
                    raise

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception

    def _calculate_delay(self, attempt: int, is_rate_limit: bool = False) -> float:
        """Calculate delay for next retry attempt"""

        # Exponential backoff
        delay = self.config.base_delay * (self.config.backoff_factor ** attempt)

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # For rate limits, add extra delay
        if is_rate_limit:
            delay *= 2

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter

        return delay


# Global retry handler instance
default_retry_handler = RetryHandler()


async def with_retry(
    func: Callable[..., Any],
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> Any:
    """
    Convenience function to execute with retry

    Args:
        func: Function to execute
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result
    """
    handler = RetryHandler(config)
    return await handler.execute_with_retry(func, *args, **kwargs)
