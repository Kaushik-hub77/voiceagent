"""
RingAI call endpoints
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

from app.core.ringai.client import RingAIError, RingAIAuthenticationError, RingAIAPIError
from app.core.utils.logger import get_logger
from app.schemas.ringai.requests import InitiateCallRequest, StartCampaignRequest
from app.schemas.ringai.responses import CallInitiatedResponse, SaveCampaignResponse, StartCampaignResponse
from app.services.ringai.call_service import RingAICallService
from app.services.fast2sms_service import Fast2SMSService

logger = get_logger(__name__)
router = APIRouter(prefix="/ringai", tags=["ringai"])

# Initialize services
_call_service = RingAICallService()
_fast2sms_service = Fast2SMSService()

async def _send_whatsapp_followup(mobile_number: str, call_id: Optional[str] = None) -> None:
    """Dispatches WhatsApp template upon call initiation."""
    try:
        await _fast2sms_service.send_whatsapp_template(
            mobile_number=mobile_number,
            variables=[],
            media_url="https://cumma-images.s3.eu-north-1.amazonaws.com/enabler_studio.png",
            udf1=call_id,
        )
        logger.info("WhatsApp followup dispatched successfully", call_id=call_id)
    except Exception as e:
        logger.error("Failed to dispatch WhatsApp followup", call_id=call_id, error=str(e))


@router.post("/calls", response_model=CallInitiatedResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(request: InitiateCallRequest, background_tasks: BackgroundTasks) -> CallInitiatedResponse:
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
        
        # Schedule post-call WhatsApp follow-up in background immediately upon call initiation
        background_tasks.add_task(
            _send_whatsapp_followup, 
            request.mobile_number, 
            getattr(response, "call_id", None)
        )
        
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


@router.post("/campaign/save", response_model=SaveCampaignResponse, status_code=status.HTTP_201_CREATED)
async def save_campaign(
    file: UploadFile = File(...),
    variables_map: str = Form(...),
    agent_id: str = Form(...),
    call_config: str = Form(...),
    country_code: str = Form(...),
    campaign_start_time: str = Form(...),
    campaign_end_time: str = Form(...),
    campaign_name: str = Form(...),
    remove_invalid_rows: bool = Form(False),
    transliterate_callee_name: bool = Form(False)
) -> SaveCampaignResponse:
    """
    Save a new calling campaign via RingAI
    """
    logger.info("Received campaign save request", campaign_name=campaign_name)

    data = {
        "variables_map": variables_map,
        "agent_id": agent_id,
        "call_config": call_config,
        "country_code": country_code,
        "campaign_start_time": campaign_start_time,
        "campaign_end_time": campaign_end_time,
        "campaign_name": campaign_name,
        "remove_invalid_rows": str(remove_invalid_rows).lower(),
        "transliterate_callee_name": str(transliterate_callee_name).lower(),
    }
    
    file_content = await file.read()

    try:
        response = await _call_service.save_campaign(
            data=data, 
            file_content=file_content,
            filename=file.filename or "campaign.csv",
            content_type=file.content_type or "text/csv"
        )
        return response

    except RingAIAuthenticationError as e:
        logger.error("RingAI authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        ) from e
    except RingAIAPIError as e:
        logger.error("RingAI API error", error=str(e), status_code=e.status_code)
        status_code = status.HTTP_502_BAD_GATEWAY if e.status_code and e.status_code >= 500 else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=f"RingAI API error: {str(e)}",
        ) from e
    except RingAIError as e:
        logger.error("RingAI error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save campaign: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Unexpected error saving campaign", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving the campaign",
        ) from e


@router.post("/campaign/start", response_model=StartCampaignResponse, status_code=status.HTTP_200_OK)
async def start_campaign(request: StartCampaignRequest) -> StartCampaignResponse:
    """
    Start a saved campaign via RingAI
    """
    logger.info("Received campaign start request", list_id=request.list_id)
    
    try:
        response = await _call_service.start_campaign(request)
        return response
    except RingAIAuthenticationError as e:
        logger.error("RingAI authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        ) from e
    except RingAIAPIError as e:
        logger.error("RingAI API error", error=str(e), status_code=e.status_code)
        status_code = status.HTTP_502_BAD_GATEWAY if e.status_code and e.status_code >= 500 else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=f"RingAI API error: {str(e)}",
        ) from e
    except RingAIError as e:
        logger.error("RingAI error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start campaign: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Unexpected error starting campaign", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting the campaign",
        ) from e

