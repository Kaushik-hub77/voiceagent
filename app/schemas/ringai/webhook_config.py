"""
Webhook configuration schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EventSubscription(BaseModel):
    """Event subscription configuration"""

    event_type: str = Field(
        description="Event type: call_completed, recording_completed, platform_analysis_completed, client_analysis_completed"
    )
    callback_url: str = Field(description="Full HTTPS URL for webhook callback")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers for webhook (e.g., Authorization)")
    method_type: str = Field(default="POST", description="HTTP method: POST, PUT, or PATCH")


class ConfigureWebhookRequest(BaseModel):
    """Request to configure webhook subscriptions"""

    agent_id: str = Field(description="RingAI agent ID")
    event_subscriptions: List[EventSubscription] = Field(description="List of event subscriptions to configure")
    webhook_base_url: Optional[str] = Field(
        None, description="Base URL for webhooks (will be prepended to /api/v1/ringai/webhooks/events)"
    )


class WebhookConfigurationResponse(BaseModel):
    """Response from webhook configuration"""

    success: bool = Field(description="Whether configuration was successful")
    agent_id: str = Field(description="Agent ID")
    message: Optional[str] = Field(None, description="Response message")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw response from RingAI API")

