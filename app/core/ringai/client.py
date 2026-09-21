"""
RingAI HTTP client for making outbound calls
"""

import logging
from typing import Any, Dict, Optional, List

import httpx
from httpx import AsyncClient, Response

from app.core.config.settings import get_settings
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


class RingAIError(Exception):
    """Base exception for RingAI operations"""

    pass


class RingAIAuthenticationError(RingAIError):
    """Authentication error with RingAI API"""

    pass


class RingAIAPIError(RingAIError):
    """API error from RingAI"""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RingAIClient:
    """Async HTTP client for RingAI API"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize RingAI client

        Args:
            api_key: RingAI API key (defaults to RING_API_KEY from settings)
            base_url: RingAI base URL (defaults to RING_BASE_URL from settings)
        """
        settings = get_settings()
        self.api_key = api_key or settings.RING_API_KEY
        self.base_url = (base_url or settings.RING_BASE_URL or "").rstrip("/")

        if not self.api_key:
            raise ValueError("RING_API_KEY must be set")
        if not self.base_url:
            raise ValueError("RING_BASE_URL must be set")

        self._client: Optional[AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized"""
        if self._client is None:
            self._client = AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
            )

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _handle_response(self, response: Response) -> Dict[str, Any]:
        """
        Handle HTTP response and raise appropriate errors

        Args:
            response: HTTP response

        Returns:
            Response JSON data

        Raises:
            RingAIAuthenticationError: For 401/403 errors
            RingAIAPIError: For other API errors
        """
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {"message": e.response.text or "Unknown error"}

            logger.error(
                "RingAI API error",
                status_code=status_code,
                error=error_data,
                url=str(e.request.url),
            )

            if status_code in (401, 403):
                raise RingAIAuthenticationError(
                    f"Authentication failed: {error_data.get('message', 'Invalid API key')}"
                ) from e

            raise RingAIAPIError(
                f"RingAI API error: {error_data.get('message', 'Unknown error')}",
                status_code=status_code,
                response=error_data,
            ) from e

        try:
            return response.json()
        except Exception as e:
            logger.warning("Failed to parse JSON response", error=str(e), text=response.text[:200])
            return {"raw_response": response.text}

    async def initiate_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiate an outbound call via RingAI

        Args:
            payload: Call configuration payload

        Returns:
            Response data from RingAI API

        Raises:
            RingAIAuthenticationError: For authentication errors
            RingAIAPIError: For API errors
        """
        await self._ensure_client()

        endpoint = "/calling/v2/outbound/individual"
        logger.info("Initiating RingAI call", endpoint=endpoint)

        try:
            response = await self._client.post(endpoint, json=payload)
            result = self._handle_response(response)

            logger.info(
                "RingAI call initiated successfully",
                # agent_id=payload.get("agent_id"),
                # mobile_number=payload.get("mobile_number"),
            )

            return result

        except httpx.RequestError as e:
            logger.error("Request error calling RingAI", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Request failed: {str(e)}") from e
        except (RingAIAuthenticationError, RingAIAPIError):
            raise
        except Exception as e:
            logger.error("Unexpected error calling RingAI", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Unexpected error: {str(e)}") from e

#    //saving campaign before making bulk api calls
    async def save_campaign(self, data: Dict[str, Any], files: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a bulk calling campaign
        """
        endpoint = "/campaign/save"
        logger.info("Initiating campaign save", endpoint=endpoint)

        try:
            # Use a separate client WITHOUT the default Content-Type: application/json
            # so httpx can auto-set the correct multipart/form-data boundary
            async with AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"X-API-KEY": self.api_key},
            ) as multipart_client:
                response = await multipart_client.post(endpoint, data=data, files=files)
            result = self._handle_response(response)

            logger.info("RingAI campaign saved successfully")

            return result

        except httpx.RequestError as e:
            logger.error("Request error saving campaign", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Request failed: {str(e)}") from e
        except (RingAIAuthenticationError, RingAIAPIError):
            raise
        except Exception as e:
            logger.error("Unexpected error saving campaign", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Unexpected error: {str(e)}") from e

    async def start_campaign(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a bulk calling campaign
        """
        await self._ensure_client()

        endpoint = "/campaign/start"
        logger.info("Starting campaign", endpoint=endpoint)

        try:
            response = await self._client.post(endpoint, json=payload)
            result = self._handle_response(response)

            logger.info("RingAI campaign started successfully")

            return result

        except httpx.RequestError as e:
            logger.error("Request error starting campaign", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Request failed: {str(e)}") from e
        except (RingAIAuthenticationError, RingAIAPIError):
            raise
        except Exception as e:
            logger.error("Unexpected error starting campaign", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Unexpected error: {str(e)}") from e

    async def configure_webhook_subscriptions(
        self, agent_id: str, event_subscriptions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Configure webhook subscriptions for an agent

        Args:
            agent_id: RingAI agent ID
            event_subscriptions: List of event subscription configurations

        Returns:
            Response data from RingAI API

        Raises:
            RingAIAuthenticationError: For authentication errors
            RingAIAPIError: For API errors
        """
        await self._ensure_client()

        endpoint = "/agent/v1"
        payload = {
            "operation": "edit_event_subscriptions",
            "agent_id": agent_id,
            "event_subscriptions": event_subscriptions,
        }

        logger.info(
            "Configuring webhook subscriptions",
            agent_id=agent_id,
            event_count=len(event_subscriptions),
        )

        try:
            response = await self._client.patch(endpoint, json=payload)
            result = self._handle_response(response)

            logger.info(
                "Webhook subscriptions configured successfully",
                agent_id=agent_id,
            )

            return result

        except httpx.RequestError as e:
            logger.error("Request error configuring webhooks", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Request failed: {str(e)}") from e
        except (RingAIAuthenticationError, RingAIAPIError):
            raise
        except Exception as e:
            logger.error("Unexpected error configuring webhooks", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Unexpected error: {str(e)}") from e

    async def get_agent_subscriptions(self, agent_id: str) -> Dict[str, Any]:
        """
        Get current webhook subscriptions for an agent

        Args:
            agent_id: RingAI agent ID

        Returns:
            Agent data including event_subscriptions

        Raises:
            RingAIAuthenticationError: For authentication errors
            RingAIAPIError: For API errors
        """
        await self._ensure_client()

        endpoint = f"/agent/v1/{agent_id}"

        logger.info("Getting agent subscriptions", agent_id=agent_id)

        try:
            response = await self._client.get(endpoint)
            result = self._handle_response(response)

            return result

        except httpx.RequestError as e:
            logger.error("Request error getting subscriptions", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Request failed: {str(e)}") from e
        except (RingAIAuthenticationError, RingAIAPIError):
            raise
        except Exception as e:
            logger.error("Unexpected error getting subscriptions", error=str(e), endpoint=endpoint)
            raise RingAIAPIError(f"Unexpected error: {str(e)}") from e

