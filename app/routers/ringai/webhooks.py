"""
RingAI webhook endpoints for receiving call events
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.utils.logger import get_logger
from app.schemas.ringai.webhooks import CallRecordingWebhook, CallRecording
from app.services.ringai.recording_service import CallRecordingService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/ringai/webhooks", tags=["ringai-webhooks"])

# Initialize recording service
_recording_service = CallRecordingService()


@router.post("/call-completed", status_code=status.HTTP_200_OK)
async def handle_call_completed(request: Request) -> JSONResponse:
    """
    Webhook endpoint for RingAI call completion events

    RingAI will POST to this endpoint when a call completes with:
    - Call ID
    - Transcription
    - Recording URL
    - Call metadata

    Configure this URL in RingAI dashboard webhook settings.
    """
    try:
        # Parse webhook payload (RingAI may send JSON or form data)
        try:
            payload = await request.json()
        except Exception:
            # Try form data if JSON fails
            form_data = await request.form()
            payload = dict(form_data)

        logger.info("Received RingAI webhook", event_type="call-completed", payload_keys=list(payload.keys()))

        # Parse webhook data
        webhook_data = CallRecordingWebhook(
            call_id=payload.get("call_id") or payload.get("callId") or payload.get("id"),
            status=payload.get("status", "completed"),
            phone_number=payload.get("phone_number") or payload.get("mobile_number"),
            from_number=payload.get("from_number") or payload.get("fromNumber"),
            duration=payload.get("duration"),
            transcription=payload.get("transcription") or payload.get("transcript"),
            recording_url=payload.get("recording_url") or payload.get("recordingUrl"),
            recording_text=payload.get("recording_text") or payload.get("text"),
            metadata=payload,
            timestamp=datetime.utcnow(),
        )

        if not webhook_data.call_id:
            logger.warning("Webhook missing call_id", payload=payload)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing call_id in webhook payload",
            )

        # Convert to CallRecording and save
        recording = CallRecording(
            call_id=webhook_data.call_id,
            phone_number=webhook_data.phone_number or "unknown",
            from_number=webhook_data.from_number,
            status=webhook_data.status,
            duration=webhook_data.duration,
            transcription=webhook_data.transcription or webhook_data.recording_text,
            recording_url=webhook_data.recording_url,
            completed_at=webhook_data.timestamp or datetime.utcnow(),
            metadata=webhook_data.metadata,
        )

        await _recording_service.save_recording(recording)

        logger.info(
            "Call recording saved successfully",
            call_id=recording.call_id,
            phone_number=recording.phone_number,
            has_transcription=bool(recording.transcription),
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "message": "Recording saved", "call_id": recording.call_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing webhook", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}",
        ) from e


@router.get("/recordings/{call_id}", response_model=CallRecording)
async def get_recording(call_id: str) -> CallRecording:
    """
    Retrieve call recording by call ID

    Args:
        call_id: RingAI call ID

    Returns:
        Call recording with transcription and metadata
    """
    recording = await _recording_service.get_recording(call_id)
    
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording not found for call_id: {call_id}",
        )
    
    return recording


@router.get("/recordings", response_model=list[CallRecording])
async def list_recordings(phone_number: str = None, limit: int = 100) -> list[CallRecording]:
    """
    List call recordings

    Args:
        phone_number: Filter by phone number (optional)
        limit: Maximum number of recordings to return (default: 100)

    Returns:
        List of call recordings
    """
    if phone_number:
        recordings = await _recording_service.get_recordings_by_phone(phone_number)
    else:
        recordings = await _recording_service.list_recordings(limit=limit)
    
    return recordings

