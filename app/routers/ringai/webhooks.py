"""
RingAI webhook endpoints for receiving call events
Supports all 4 event types: call_completed, recording_completed, 
platform_analysis_completed, client_analysis_completed
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse

from app.core.utils.logger import get_logger
from app.schemas.ringai.webhooks import (
    CallCompletedEvent,
    RecordingCompletedEvent,
    PlatformAnalysisCompletedEvent,
    ClientAnalysisCompletedEvent,
    CallRecording,
    process_transcript,
)
from app.services.ringai.recording_service import CallRecordingService

logger = get_logger(__name__)
router = APIRouter(prefix="/ringai/webhooks", tags=["ringai-webhooks"])

# Initialize services
_recording_service = CallRecordingService()


@router.post("/events", status_code=status.HTTP_200_OK)
async def handle_webhook_event(
    request: Request, 
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Unified webhook endpoint for all RingAI event types
    """
    try:
        # Parse webhook payload
        payload = await request.json()
        
        event_type = payload.get("event_type")
        call_id = payload.get("call_id")
        
        logger.info(
            "Received RingAI webhook",
            event_type=event_type,
            call_id=call_id,
            payload_keys=list(payload.keys()),
        )

        if not event_type:
            logger.warning("Webhook missing event_type", payload=payload)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing event_type in webhook payload",
            )

        if not call_id:
            logger.warning("Webhook missing call_id", payload=payload)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing call_id in webhook payload",
            )

        # Route to appropriate handler based on event type
        if event_type == "call_completed":
            await _handle_call_completed(payload)

        elif event_type == "recording_completed":
            await _handle_recording_completed(payload)

        elif event_type == "platform_analysis_completed":
            await _handle_platform_analysis(payload)

        elif event_type == "client_analysis_completed":
            await _handle_client_analysis(payload)

        else:
            logger.warning("Unknown event type", event_type=event_type, call_id=call_id)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "received", "message": f"Unknown event type: {event_type}"},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "event_type": event_type, "call_id": call_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing webhook", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "error", "message": "Error processed, check logs"},
        )



async def _handle_call_completed(payload: Dict[str, Any]) -> None:
    """Handle call_completed event"""
    try:
        event = CallCompletedEvent(**payload)
        
        user_id = None
        if event.custom_args_values:
            user_id = event.custom_args_values.get("user_id") or event.custom_args_values.get("userId")
        
        transcription_text = process_transcript(event.transcript)
        
        called_on = None
        if event.called_on:
            try:
                called_on = datetime.fromisoformat(event.called_on.replace("Z", "+00:00"))
            except Exception:
                pass
        
        recording = CallRecording(
            call_id=event.call_id,
            user_id=user_id,
            phone_number=event.to_number or "unknown",
            from_number=event.from_number,
            status=event.status or "completed",
            call_type=event.call_type,
            duration=event.call_duration,
            transcription=transcription_text,
            transcript_raw=[entry.model_dump() if hasattr(entry, "model_dump") else entry for entry in (event.transcript or [])],
            recording_url=event.recording_url,
            agent_id=event.agent_id,
            agent_name=event.agent_name,
            call_cost=event.call_cost,
            called_on=called_on,
            completed_at=datetime.utcnow(),
            metadata=payload,
        )

        await _recording_service.save_recording(recording)

        # Dispatch post-call WhatsApp follow-up
        try:
            from app.services.fast2sms_service import Fast2SMSService
            _fast2sms_service = Fast2SMSService()
            await _fast2sms_service.send_whatsapp_template(
                mobile_number=recording.phone_number,
                variables=[],
                media_url="https://cumma-images.s3.eu-north-1.amazonaws.com/enabler_studio.png",
                udf1=event.call_id,
            )
            logger.info("WhatsApp followup dispatched successfully from webhook", call_id=event.call_id)
        except Exception as e:
            logger.error("Failed to dispatch WhatsApp followup from webhook", call_id=event.call_id, error=str(e))

        logger.info(
            "Call completed event processed",
            call_id=event.call_id,
            user_id=user_id,
            phone_number=recording.phone_number,
            has_transcription=bool(transcription_text),
        )

    except Exception as e:
        logger.error("Error handling call_completed event", error=str(e), call_id=payload.get("call_id"))


async def _handle_recording_completed(payload: Dict[str, Any]) -> None:
    """Handle recording_completed event - update recording URL"""
    try:
        event = RecordingCompletedEvent(**payload)
        existing = await _recording_service.get_recording(event.call_id)
        
        if existing:
            existing.recording_url = event.recording_url
            existing.recording_duration = event.recording_duration
            
            if event.recording_url:
                filename = event.recording_url.split("/")[-1] if "/" in event.recording_url else f"{event.call_id}.mp3"
                existing.recording_filename = filename
            
            await _recording_service.save_recording(existing)
            logger.info("Recording completed event processed", call_id=event.call_id)
        else:
            logger.warning("Recording completed event but no call record found", call_id=event.call_id)

    except Exception as e:
        logger.error("Error handling recording_completed event", error=str(e), call_id=payload.get("call_id"))


async def _handle_platform_analysis(payload: Dict[str, Any]) -> None:
    """Handle platform_analysis_completed event"""
    try:
        event = PlatformAnalysisCompletedEvent(**payload)
        existing = await _recording_service.get_recording(event.call_id)
        
        if existing:
            existing.platform_analysis = event.analysis_data.model_dump() if hasattr(event.analysis_data, "model_dump") else event.analysis_data
            
            if not existing.transcription and event.transcript:
                existing.transcription = process_transcript(event.transcript)
                existing.transcript_raw = [entry.model_dump() if hasattr(entry, "model_dump") else entry for entry in event.transcript]
            
            await _recording_service.save_recording(existing)
            logger.info("Platform analysis completed event processed", call_id=event.call_id)
        else:
            logger.warning("Platform analysis event but no call record found", call_id=event.call_id)

    except Exception as e:
        logger.error("Error handling platform_analysis_completed event", error=str(e), call_id=payload.get("call_id"))


async def _handle_client_analysis(payload: Dict[str, Any]) -> None:
    """Handle client_analysis_completed event"""
    try:
        event = ClientAnalysisCompletedEvent(**payload)
        existing = await _recording_service.get_recording(event.call_id)
        
        if existing:
            existing.client_analysis = event.analysis_data
            await _recording_service.save_recording(existing)
            logger.info("Client analysis completed event processed", call_id=event.call_id)
        else:
            logger.warning("Client analysis event but no call record found", call_id=event.call_id)

    except Exception as e:
        logger.error("Error handling client_analysis_completed event", error=str(e), call_id=payload.get("call_id"))


@router.get("/recordings/{call_id}", response_model=CallRecording)
async def get_recording(call_id: str) -> CallRecording:
    recording = await _recording_service.get_recording(call_id)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording not found for call_id: {call_id}",
        )
    return recording


@router.get("/recordings", response_model=list[CallRecording])
async def list_recordings(phone_number: str = None, limit: int = 100) -> list[CallRecording]:
    if phone_number:
        recordings = await _recording_service.get_recordings_by_phone(phone_number)
    else:
        recordings = await _recording_service.list_recordings(limit=limit)
    return recordings


@router.get("/recordings/user/{user_id}", response_model=list[CallRecording])
async def get_recordings_by_user(user_id: str) -> list[CallRecording]:
    recordings = await _recording_service.get_recordings_by_user_id(user_id)
    return recordings