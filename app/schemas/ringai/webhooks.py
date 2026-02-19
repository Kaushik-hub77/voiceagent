"""
RingAI webhook event schemas
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CallRecordingWebhook(BaseModel):
    """Webhook payload from RingAI when call completes"""

    call_id: str = Field(description="RingAI call ID")
    status: str = Field(description="Call status (completed, failed, etc.)")
    phone_number: Optional[str] = Field(None, description="Phone number that was called")
    from_number: Optional[str] = Field(None, description="Caller ID number")
    duration: Optional[int] = Field(None, description="Call duration in seconds")
    transcription: Optional[str] = Field(None, description="Full call transcription text")
    recording_url: Optional[str] = Field(None, description="URL to download call recording")
    recording_text: Optional[str] = Field(None, description="Transcribed text from recording")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        extra = "allow"  # Accept any additional fields from RingAI


class CallRecording(BaseModel):
    """Stored call recording model"""

    call_id: str = Field(description="RingAI call ID")
    phone_number: str = Field(description="Phone number that was called")
    from_number: Optional[str] = Field(None, description="Caller ID number")
    status: str = Field(description="Call status")
    duration: Optional[int] = Field(None, description="Call duration in seconds")
    transcription: Optional[str] = Field(None, description="Full call transcription")
    recording_url: Optional[str] = Field(None, description="URL to download recording")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When call was initiated")
    completed_at: Optional[datetime] = Field(None, description="When call completed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

