"""
RingAI webhook event schemas matching official API documentation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class TranscriptEntry(BaseModel):
    """Single transcript entry (bot or user message)"""

    bot: Optional[str] = Field(None, description="Bot message")
    user: Optional[str] = Field(None, description="User message")

    class Config:
        extra = "allow"


class AnalysisData(BaseModel):
    """Analysis data from platform or client analysis events"""

    key_points: Optional[List[str]] = Field(None, description="Key conversation points")
    action_items: Optional[List[str]] = Field(None, description="Action items")
    summary: Optional[str] = Field(None, description="Conversation summary")
    classification: Optional[str] = Field(None, description="Call classification")
    callback_requested: Optional[bool] = Field(None, description="Whether callback was requested")
    callback_requested_time: Optional[str] = Field(None, description="Callback request timestamp")
    status: Optional[str] = Field(None, description="Analysis status")
    call_disconnect_reason: Optional[str] = Field(None, description="Why call disconnected")
    timezone: Optional[str] = Field(None, description="Call timezone")
    
    # Client analysis fields (dynamic)
    class Config:
        extra = "allow"  # Allow custom analysis fields


class BaseWebhookEvent(BaseModel):
    """Base webhook event with common fields"""

    event_type: str = Field(description="Event type: call_completed, recording_completed, etc.")
    call_id: str = Field(description="Unique call identifier")
    call_sid: Optional[str] = Field(None, description="Telephony provider call ID")
    agent_id: Optional[str] = Field(None, description="AI agent ID")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
    agent_name: Optional[str] = Field(None, description="Agent display name")
    version_id: Optional[str] = Field(None, description="Agent version UUID")
    call_cost: Optional[float] = Field(None, description="Call cost in credits")
    overall_latency_seconds: Optional[float] = Field(None, description="Total response latency")
    first_utterance_seconds: Optional[float] = Field(None, description="Time to first AI response")
    custom_args_values: Optional[Dict[str, Any]] = Field(None, description="Custom data from call initiation")
    to_number: Optional[str] = Field(None, description="Phone number that received call")
    from_number: Optional[str] = Field(None, description="Phone number that made call")
    bulk_list_id: Optional[str] = Field(None, description="Bulk list ID if applicable")
    called_on: Optional[str] = Field(None, description="Call timestamp (ISO 8601 UTC)")

    class Config:
        extra = "allow"


class CallCompletedEvent(BaseWebhookEvent):
    """call_completed event payload"""

    event_type: str = Field(default="call_completed", description="Event type")
    call_duration: Optional[float] = Field(None, description="Call duration in seconds")
    agent_message_count: Optional[int] = Field(None, description="Number of agent messages")
    user_message_count: Optional[int] = Field(None, description="Number of user messages")
    call_type: Optional[str] = Field(None, description="inbound, outbound, or webcall")
    status: Optional[str] = Field(None, description="completed, failed, or retry")
    transcript: Optional[List[TranscriptEntry]] = Field(None, description="Conversation transcript array")
    retry_count: Optional[int] = Field(None, description="Number of retry attempts")
    recording_url: Optional[str] = Field(None, description="Recording URL (may be null initially)")


class RecordingCompletedEvent(BaseWebhookEvent):
    """recording_completed event payload"""

    event_type: str = Field(default="recording_completed", description="Event type")
    recording_url: str = Field(description="URL of the processed recording")
    recording_duration: Optional[float] = Field(None, description="Recording duration in seconds")


class PlatformAnalysisCompletedEvent(BaseWebhookEvent):
    """platform_analysis_completed event payload"""

    event_type: str = Field(default="platform_analysis_completed", description="Event type")
    analysis_data: AnalysisData = Field(description="Platform analysis results")
    call_type: Optional[str] = Field(None, description="inbound, outbound, or webcall")
    status: Optional[str] = Field(None, description="Call status")
    transcript: Optional[List[TranscriptEntry]] = Field(None, description="Conversation transcript")
    call_duration: Optional[float] = Field(None, description="Call duration in seconds")
    agent_message_count: Optional[int] = Field(None, description="Number of agent messages")
    user_message_count: Optional[int] = Field(None, description="Number of user messages")


class ClientAnalysisCompletedEvent(BaseWebhookEvent):
    """client_analysis_completed event payload"""

    event_type: str = Field(default="client_analysis_completed", description="Event type")
    analysis_data: Dict[str, Any] = Field(description="Custom analysis results (structure varies)")
    call_type: Optional[str] = Field(None, description="inbound, outbound, or webcall")
    status: Optional[str] = Field(None, description="Call status")
    transcript: Optional[List[TranscriptEntry]] = Field(None, description="Conversation transcript")
    call_duration: Optional[float] = Field(None, description="Call duration in seconds")
    agent_message_count: Optional[int] = Field(None, description="Number of agent messages")
    user_message_count: Optional[int] = Field(None, description="Number of user messages")


class CallRecording(BaseModel):
    """Stored call recording model with processed data"""

    call_id: str = Field(description="RingAI call ID")
    user_id: Optional[str] = Field(None, description="User ID extracted from custom_args_values")
    phone_number: str = Field(description="Phone number that was called (to_number)")
    from_number: Optional[str] = Field(None, description="Caller ID number")
    status: str = Field(description="Call status")
    call_type: Optional[str] = Field(None, description="inbound, outbound, or webcall")
    duration: Optional[float] = Field(None, description="Call duration in seconds")
    transcription: Optional[str] = Field(None, description="Full call transcription as readable text")
    transcript_raw: Optional[List[Dict[str, Any]]] = Field(None, description="Raw transcript array")
    recording_url: Optional[str] = Field(None, description="URL to download recording")
    recording_filename: Optional[str] = Field(None, description="Recording filename for CloudFront")
    recording_duration: Optional[float] = Field(None, description="Recording duration in seconds")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    agent_name: Optional[str] = Field(None, description="Agent name")
    call_cost: Optional[float] = Field(None, description="Call cost")
    platform_analysis: Optional[Dict[str, Any]] = Field(None, description="Platform analysis data")
    client_analysis: Optional[Dict[str, Any]] = Field(None, description="Client analysis data")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When call was initiated")
    completed_at: Optional[datetime] = Field(None, description="When call completed")
    called_on: Optional[datetime] = Field(None, description="Call timestamp from RingAI")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


def process_transcript(transcript: Optional[List[TranscriptEntry]]) -> str:
    """
    Convert transcript array to readable text format
    
    Args:
        transcript: List of transcript entries
        
    Returns:
        Formatted transcript as string
    """
    if not transcript:
        return ""
    
    lines = []
    for entry in transcript:
        if isinstance(entry, dict):
            # Handle dict format
            if "bot" in entry and entry["bot"]:
                lines.append(f"Bot: {entry['bot']}")
            elif "user" in entry and entry["user"]:
                lines.append(f"User: {entry['user']}")
        elif isinstance(entry, TranscriptEntry):
            # Handle Pydantic model
            if entry.bot:
                lines.append(f"Bot: {entry.bot}")
            elif entry.user:
                lines.append(f"User: {entry.user}")
    
    return "\n".join(lines)
