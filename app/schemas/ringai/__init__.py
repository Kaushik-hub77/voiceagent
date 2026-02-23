"""
RingAI request and response schemas
"""

from app.schemas.ringai.requests import (
    CallRetryConfig,
    CallTimeConfig,
    CallConfig,
    CustomArgsValues,
    InitiateCallRequest,
)
from app.schemas.ringai.responses import CallInitiatedResponse
from app.schemas.ringai.webhooks import (
    CallCompletedEvent,
    RecordingCompletedEvent,
    PlatformAnalysisCompletedEvent,
    ClientAnalysisCompletedEvent,
    CallRecording,
    process_transcript,
)
from app.schemas.ringai.webhook_config import (
    ConfigureWebhookRequest,
    WebhookConfigurationResponse,
    EventSubscription,
)

__all__ = [
    "CallRetryConfig",
    "CallTimeConfig",
    "CallConfig",
    "CustomArgsValues",
    "InitiateCallRequest",
    "CallInitiatedResponse",
    "CallCompletedEvent",
    "RecordingCompletedEvent",
    "PlatformAnalysisCompletedEvent",
    "ClientAnalysisCompletedEvent",
    "CallRecording",
    "process_transcript",
    "ConfigureWebhookRequest",
    "WebhookConfigurationResponse",
    "EventSubscription",
]

