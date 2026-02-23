"""
RingAI webhook configuration endpoints
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from app.core.ringai.client import RingAIError, RingAIAuthenticationError, RingAIAPIError
from app.core.utils.exceptions import ConfigurationError
from app.core.utils.logger import get_logger
from app.schemas.ringai.webhook_config import (
    ConfigureWebhookRequest,
    WebhookConfigurationResponse,
    EventSubscription,
)
from app.services.ringai.webhook_config_service import WebhookConfigService

logger = get_logger(__name__)
router = APIRouter(prefix="/ringai/webhooks", tags=["ringai-webhooks"])

# Initialize service
_webhook_config_service = WebhookConfigService()


@router.post("/configure", response_model=WebhookConfigurationResponse, status_code=status.HTTP_200_OK)
async def configure_webhooks(request: ConfigureWebhookRequest) -> WebhookConfigurationResponse:
    """
    Configure webhook subscriptions for a RingAI agent

    This endpoint allows you to programmatically configure webhooks instead of
    using the RingAI dashboard. You can subscribe to any or all of these events:
    - call_completed: Call finishes (transcript, duration, status)
    - recording_completed: Recording is processed and ready
    - platform_analysis_completed: AI analysis completes
    - client_analysis_completed: Custom analysis completes

    Args:
        request: Webhook configuration request

    Returns:
        Configuration response

    Raises:
        HTTPException: For validation or API errors
    """
    logger.info(
        "Received webhook configuration request",
        agent_id=request.agent_id,
        event_count=len(request.event_subscriptions),
    )

    try:
        response = await _webhook_config_service.configure_webhooks(request)
        return response

    except RingAIAuthenticationError as e:
        logger.error("RingAI authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        ) from e

    except RingAIAPIError as e:
        logger.error(
            "RingAI API error",
            error=str(e),
            status_code=e.status_code,
            agent_id=request.agent_id,
        )
        status_code = (
            status.HTTP_502_BAD_GATEWAY
            if e.status_code and e.status_code >= 500
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"RingAI API error: {str(e)}",
        ) from e

    except RingAIError as e:
        logger.error("RingAI error", error=str(e), agent_id=request.agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure webhooks: {str(e)}",
        ) from e

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration error: {str(e)}",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error configuring webhooks",
            error=str(e),
            agent_id=request.agent_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while configuring webhooks",
        ) from e


@router.get("/subscriptions/{agent_id}")
async def get_subscriptions(agent_id: str) -> Dict[str, Any]:
    """
    Get current webhook subscriptions for an agent

    Args:
        agent_id: RingAI agent ID

    Returns:
        Agent data including event_subscriptions
    """
    logger.info("Getting agent subscriptions", agent_id=agent_id)

    try:
        subscriptions = await _webhook_config_service.get_subscriptions(agent_id)
        return subscriptions

    except RingAIAuthenticationError as e:
        logger.error("RingAI authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        ) from e

    except RingAIAPIError as e:
        logger.error("RingAI API error", error=str(e), status_code=e.status_code, agent_id=agent_id)
        status_code = (
            status.HTTP_502_BAD_GATEWAY
            if e.status_code and e.status_code >= 500
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"RingAI API error: {str(e)}",
        ) from e

    except RingAIError as e:
        logger.error("RingAI error", error=str(e), agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscriptions: {str(e)}",
        ) from e

    except Exception as e:
        logger.error("Unexpected error getting subscriptions", error=str(e), agent_id=agent_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting subscriptions",
        ) from e

