"""
RingAI response schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CallInitiatedResponse(BaseModel):
    """Response after successfully initiating a call"""

    success: bool = Field(True, description="Whether the call was initiated successfully")
    call_id: Optional[str] = Field(None, description="RingAI call ID")
    status: str = Field(description="Call status")
    message: Optional[str] = Field(None, description="Additional message")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw response from RingAI API")

