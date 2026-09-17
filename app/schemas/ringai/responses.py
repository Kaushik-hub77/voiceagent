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


class SaveCampaignResponse(BaseModel):
    """Response after successfully saving a campaign"""
    
    message: str = Field(description="Response message")
    list_id: str = Field(description="Campaign list ID")
    custom_args_values: list[Dict[str, Any]] = Field(default_factory=list)
    total_rows: int = Field(description="Total rows processed")
    successful_rows: int = Field(description="Successful rows")
    failed_rows: int = Field(description="Failed rows")


class StartCampaignResponse(BaseModel):
    """Response after successfully starting a campaign"""
    
    success: bool = Field(True, description="Whether the campaign was started successfully")
    message: Optional[str] = Field(None, description="Response message")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw response from RingAI API")
