"""
OpenAI LLM client implementation
"""

import openai
from typing import Dict, Any, Optional, AsyncIterator
import tiktoken
import time

from app.core.llm.base import LLMClient, LLMConfig, LLMResponse, RateLimitError, AuthenticationError
from app.core.utils.logger import get_logger
from app.core.utils.tracer import record_llm_call

logger = get_logger(__name__)


class OpenAIClient(LLMClient):
    """OpenAI API client"""

    def __init__(self, api_key: str, config: Dict[str, Any]):
        super().__init__(api_key, config)
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=config.get("timeout", 60)
        )
        self.model_configs = config.get("models", {})

    @staticmethod
    def _token_param(model: str, max_tokens: Optional[int]) -> Dict[str, int]:
        """
        OpenAI Chat Completions now uses `max_completion_tokens` for newer models
        (e.g., gpt-4.x / gpt-5.x). Older models still accept `max_tokens`.
        """
        if max_tokens is None:
            return {}
        if model.startswith(("gpt-4", "gpt-5")):
            return {"max_completion_tokens": max_tokens}
        return {"max_tokens": max_tokens}

    async def generate(
        self,
        prompt: str,
        config: LLMConfig,
        **kwargs
    ) -> LLMResponse:
        """Generate text using OpenAI API"""

        start_time = time.time()

        try:
            # Prepare request parameters
            request_params: Dict[str, Any] = {
                "model": config.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": config.temperature,
                "top_p": config.top_p,
                "frequency_penalty": config.frequency_penalty,
                "presence_penalty": config.presence_penalty,
                "stop": config.stop_sequences,
            }
            request_params.update(self._token_param(config.model, config.max_tokens))

            # Remove None values
            request_params = {k: v for k, v in request_params.items() if v is not None}

            # Add any additional kwargs
            request_params.update(kwargs)

            # Gate response_format by model capabilities to avoid 400s on older models.
            # (We still keep the runtime retry logic below as a second line of defense.)
            if "response_format" in request_params:
                model = str(config.model or "")
                supports_json_mode = model.startswith(("gpt-4o", "gpt-4.1", "gpt-5"))
                if not supports_json_mode:
                    request_params.pop("response_format", None)

            self.logger.info(
                "Making OpenAI API call",
                model=config.model,
                prompt_length=len(prompt)
            )

            # Make API call (with safe fallback if response_format isn't supported)
            try:
                response = await self.client.chat.completions.create(**request_params)
            except Exception as e:
                # Some models/accounts may not support response_format. If caller requested it,
                # retry once without it.
                if "response_format" in request_params:
                    self.logger.warning(
                        "OpenAI call failed with response_format; retrying without response_format",
                        model=config.model,
                        error_type=type(e).__name__
                    )
                    request_params.pop("response_format", None)
                    response = await self.client.chat.completions.create(**request_params)
                else:
                    raise

            processing_time = time.time() - start_time
            # Record per-request metrics (contextvar-based)
            record_llm_call(processing_time)

            # Extract response data
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason

            # Extract usage information
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            return LLMResponse(
                content=content,
                model=response.model,  # Use actual model from OpenAI response, not config
                usage=usage,
                finish_reason=finish_reason,
                processing_time=processing_time,
                raw_response=response.model_dump()
            )

        except openai.RateLimitError as e:
            self.logger.warning("OpenAI rate limit exceeded", error=str(e))
            raise RateLimitError(f"Rate limit exceeded: {str(e)}")

        except openai.AuthenticationError as e:
            self.logger.error("OpenAI authentication failed", error=str(e))
            raise AuthenticationError(f"Authentication failed: {str(e)}")

        except Exception as e:
            self.logger.error("OpenAI API call failed", error=str(e))
            raise Exception(f"OpenAI API call failed: {str(e)}")

    def get_token_limit(self, model: str) -> int:
        """Get token limit for OpenAI model"""
        # Get model config from our configuration
        model_config = self.model_configs.get(model, {})
        return model_config.get("context_window", 4096)

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        try:
            # Try to get encoding for the model
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimate of 4 characters per token
            return len(text) // 4

    async def stream_generate(
        self,
        prompt: str,
        config: LLMConfig,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream tokens using OpenAI Chat Completions API"""

        try:
            request_params = {
                "model": config.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": config.temperature,
                "top_p": config.top_p,
                "frequency_penalty": config.frequency_penalty,
                "presence_penalty": config.presence_penalty,
                "stop": config.stop_sequences,
                "stream": True,
            }
            request_params.update(self._token_param(config.model, config.max_tokens))

            # Remove None values
            request_params = {k: v for k, v in request_params.items() if v is not None}
            request_params.update(kwargs)

            self.logger.info(
                "Starting OpenAI streaming call",
                model=config.model,
                prompt_length=len(prompt)
            )

            stream = await self.client.chat.completions.create(**request_params)

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        except openai.RateLimitError as e:
            self.logger.warning("OpenAI streaming rate limit exceeded", error=str(e))
            raise RateLimitError(f"Rate limit exceeded: {str(e)}")
        except openai.AuthenticationError as e:
            self.logger.error("OpenAI streaming authentication failed", error=str(e))
            raise AuthenticationError(f"Authentication failed: {str(e)}")
        except Exception as e:
            self.logger.error("OpenAI streaming call failed", error=str(e))
            raise Exception(f"OpenAI streaming call failed: {str(e)}")
