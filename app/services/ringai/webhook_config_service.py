"""
Service for configuring RingAI webhook subscriptions
"""

from typing import List, Dict, Any, Optional

from app.core.ringai.client import RingAIClient, RingAIError
from app.core.utils.logger import get_logger
from app.schemas.ringai.webhook_config import ConfigureWebhookRequest, WebhookConfigurationResponse, EventSubscription

logger = get_logger(__name__)

class WebhookConfigService:
    """Service for managing RingAI webhook subscriptions"""

    def __init__(self, client: Optional[RingAIClient] = None):
        """
        Initialize webhook config service

        Args:
            client: RingAI client instance (creates new if not provided)
        """
        self._client = client

    async def _get_client(self) -> RingAIClient:
        """Get or create RingAI client"""
        if self._client is None:
            self._client = RingAIClient()
        return self._client

    async def configure_webhooks(self, request: ConfigureWebhookRequest) -> WebhookConfigurationResponse:
        """
        Configure webhook subscriptions for an agent

        Args:
            request: Webhook configuration request

        Returns:
            Configuration response

        Raises:
            RingAIError: For RingAI API errors
        """
        logger.info(
            "Configuring webhook subscriptions",
            agent_id=request.agent_id,
            event_count=len(request.event_subscriptions),
        )

        try:
            # Build event subscriptions payload
            event_subscriptions = []
            for sub in request.event_subscriptions:
                subscription_dict: Dict[str, Any] = {
                    "event_type": sub.event_type,
                    "callback_url": sub.callback_url,
                    "method_type": sub.method_type,
                }
                
                if sub.headers:
                    subscription_dict["headers"] = sub.headers
                
                event_subscriptions.append(subscription_dict)

            client = await self._get_client()
            response = await client.configure_webhook_subscriptions(
                agent_id=request.agent_id,
                event_subscriptions=event_subscriptions,
            )

            logger.info(
                "Webhook subscriptions configured successfully",
                agent_id=request.agent_id,
            )

            return WebhookConfigurationResponse(
                success=True,
                agent_id=request.agent_id,
                message="Webhook subscriptions configured successfully",
                raw_response=response,
            )

        except RingAIError as e:
            logger.error(
                "Failed to configure webhook subscriptions",
                error=str(e),
                agent_id=request.agent_id,
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error configuring webhooks",
                error=str(e),
                agent_id=request.agent_id,
            )
            raise RingAIError(f"Failed to configure webhooks: {str(e)}") from e

    async def get_subscriptions(self, agent_id: str) -> Dict[str, Any]:
        """
        Get current webhook subscriptions for an agent

        Args:
            agent_id: RingAI agent ID

        Returns:
            Agent data including event_subscriptions

        Raises:
            RingAIError: For RingAI API errors
        """
        logger.info("Getting agent subscriptions", agent_id=agent_id)

        try:
            client = await self._get_client()
            response = await client.get_agent_subscriptions(agent_id)

            return response

        except RingAIError as e:
            logger.error("Failed to get subscriptions", error=str(e), agent_id=agent_id)
            raise
        except Exception as e:
            logger.error("Unexpected error getting subscriptions", error=str(e), agent_id=agent_id)
            raise RingAIError(f"Failed to get subscriptions: {str(e)}") from e

