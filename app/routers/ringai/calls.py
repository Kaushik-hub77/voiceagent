"""
RingAI call endpoints
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.ringai.client import RingAIError, RingAIAuthenticationError, RingAIAPIError
from app.core.utils.logger import get_logger
from app.schemas.ringai.requests import InitiateCallRequest
from app.schemas.ringai.responses import CallInitiatedResponse
from app.services.ringai.call_service import RingAICallService

logger = get_logger(__name__)
router = APIRouter(prefix="/ringai", tags=["ringai"])

# Initialize service
_call_service = RingAICallService()


@router.post("/calls", response_model=CallInitiatedResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(request: InitiateCallRequest) -> CallInitiatedResponse:
    """
    Initiate an outbound call via RingAI

    This endpoint accepts call configuration including:
    - Contact information (name, mobile_number)
    - Agent configuration (agent_id - prompt configured in RingAI dashboard)
    - Call settings (timeouts, retries, time windows)
    - Custom arguments

    Args:
        request: Call initiation request with all configuration

    Returns:
        Call initiation response with call ID and status

    Raises:
        HTTPException: For validation or API errors
    """
    logger.info(
        "Received call initiation request",
        name=request.name,
        mobile_number=request.mobile_number,
        agent_id=request.agent_id,
    )

    try:
        response = await _call_service.initiate_call(request)
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
            mobile_number=request.mobile_number,
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
        logger.error("RingAI error", error=str(e), mobile_number=request.mobile_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error initiating call",
            error=str(e),
            mobile_number=request.mobile_number,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while initiating the call",
        ) from e

