"""
RingAI call service - business logic for initiating calls
"""

import logging
from typing import Dict, Any, Optional

from app.core.ringai.client import RingAIClient, RingAIError
from app.core.utils.logger import get_logger
from app.schemas.ringai.requests import InitiateCallRequest
from app.schemas.ringai.responses import CallInitiatedResponse

logger = get_logger(__name__)


class RingAICallService:
    """Service for managing RingAI outbound calls"""

    def __init__(self, client: Optional[RingAIClient] = None):
        """
        Initialize call service

        Args:
            client: RingAI client instance (creates new if not provided)
        """
        self._client = client

    async def _get_client(self) -> RingAIClient:
        """Get or create RingAI client"""
        if self._client is None:
            self._client = RingAIClient()
        return self._client

    async def initiate_call(self, request: InitiateCallRequest) -> CallInitiatedResponse:
        """
        Initiate an outbound call via RingAI

        Args:
            request: Call initiation request

        Returns:
            Call initiation response

        Raises:
            RingAIError: For RingAI API errors
        """
        logger.info(
            "Initiating RingAI call",
            name=request.name,
            mobile_number=request.mobile_number,
            agent_id=request.agent_id,
        )

        # Build payload
        payload = request.to_ringai_payload()
        
        # Log payload structure for debugging
        logger.debug(
            "Built RingAI payload",
            has_system_prompt=bool(
                payload.get("custom_args_values", {}).get("system_prompt") if isinstance(payload.get("custom_args_values"), dict) else False
            ),
            custom_args_keys=list(payload.get("custom_args_values", {}).keys()) if isinstance(payload.get("custom_args_values"), dict) else [],
        )

        # Validate timezone if call_time is provided
        if request.call_config and request.call_config.call_time:
            timezone = request.call_config.call_time.timezone
            # Basic timezone validation (could be enhanced with pytz)
            if not timezone or "/" not in timezone:
                logger.warning("Invalid timezone format", timezone=timezone)

        try:
            client = await self._get_client()
            response = await client.initiate_call(payload)

            # Extract call ID from response (RingAI API structure may vary)
            call_id = response.get("call_id") or response.get("id") or response.get("callId")

            logger.info(
                "RingAI call initiated successfully",
                call_id=call_id,
                mobile_number=request.mobile_number,
            )

            return CallInitiatedResponse(
                success=True,
                call_id=call_id,
                status="initiated",
                message="Call initiated successfully",
                raw_response=response,
            )

        except RingAIError as e:
            logger.error(
                "Failed to initiate RingAI call",
                error=str(e),
                mobile_number=request.mobile_number,
                agent_id=request.agent_id,
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error initiating call",
                error=str(e),
                mobile_number=request.mobile_number,
            )
            raise RingAIError(f"Failed to initiate call: {str(e)}") from e

