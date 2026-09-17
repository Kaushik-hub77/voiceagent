"""
RingAI request schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class CallRetryConfig(BaseModel):
    """Call retry configuration"""

    retry_count: int = Field(ge=0, le=10, description="Number of retry attempts")
    retry_busy: int = Field(ge=0, description="Retry delay for busy (seconds)")
    retry_not_picked: int = Field(ge=0, description="Retry delay for not picked (seconds)")
    retry_failed: int = Field(ge=0, description="Retry delay for failed (seconds)")


class CallTimeConfig(BaseModel):
    """Call time window configuration"""

    call_start_time: str = Field(description="Call start time in HH:MM format")
    call_end_time: str = Field(description="Call end time in HH:MM format")
    timezone: str = Field(description="Timezone (e.g., Asia/Kolkata)")

    @field_validator("call_start_time", "call_end_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format HH:MM"""
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
        except ValueError as e:
            raise ValueError("Time must be in HH:MM format with valid values") from e
        return v


class CallConfig(BaseModel):
    """Complete call configuration"""

    idle_timeout_warning: int = Field(ge=0, description="Idle timeout warning (seconds)")
    idle_timeout_end: int = Field(ge=0, description="Idle timeout end (seconds)")
    max_call_length: int = Field(ge=0, description="Maximum call length (seconds)")
    call_retry_config: Optional[CallRetryConfig] = Field(None, description="Retry configuration")
    call_time: Optional[CallTimeConfig] = Field(None, description="Call time window")

    @field_validator("idle_timeout_end")
    @classmethod
    def validate_idle_timeout(cls, v: int, info: ValidationInfo) -> int:
        """Ensure idle_timeout_end >= idle_timeout_warning"""
        if info.data and "idle_timeout_warning" in info.data:
            warning = info.data["idle_timeout_warning"]
            if v < warning:
                raise ValueError("idle_timeout_end must be >= idle_timeout_warning")
        return v


class CustomArgsValues(BaseModel):
    """Custom arguments for the call"""

    model_config = {"extra": "allow"}

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Return dict with all fields including extra"""
        return super().model_dump(**kwargs)


class InitiateCallRequest(BaseModel):
    """Request model for initiating a RingAI call"""

    name: str = Field(description="Name of the person to call")
    mobile_number: str = Field(description="Mobile number in E.164 format (e.g., +918778898282)")
    agent_id: str = Field(description="RingAI agent ID (prompt configured in RingAI dashboard)")
    from_number: Optional[str] = Field(None, description="Caller ID number in E.164 format")
    number_pool_id: Optional[str] = Field(None, description="Number pool ID to use instead of from_number")
    from_number_id: Optional[str] = Field(None, description="From number ID to use instead of from_number")
    custom_args_values: Optional[CustomArgsValues] = Field(None, description="Custom arguments")
    call_config: Optional[CallConfig] = Field(None, description="Call configuration")

    @field_validator("mobile_number", "from_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate E.164 phone number format"""
        if not v:
            return v
        if not v.startswith("+"):
            raise ValueError("Phone number must be in E.164 format (start with +)")
        if len(v) < 8 or len(v) > 15:
            raise ValueError("Phone number must be between 8 and 15 characters")
        # Check that remaining characters are digits
        if not v[1:].replace(" ", "").isdigit():
            raise ValueError("Phone number must contain only digits after +")
        return v.replace(" ", "")

    def to_ringai_payload(self) -> Dict[str, Any]:
        """
        Convert request to RingAI API payload format

        Returns:
            Dictionary ready for RingAI API
        """
        payload: Dict[str, Any] = {
            "name": self.name,
            "mobile_number": self.mobile_number,
            "agent_id": self.agent_id,
        }
        
        if self.from_number:
            payload["from_number"] = self.from_number
            
        if getattr(self, "number_pool_id", None):
            payload["number_pool_id"] = self.number_pool_id

        if getattr(self, "from_number_id", None):
            payload["from_number_id"] = self.from_number_id

        # Handle custom_args_values (prompts are configured in RingAI dashboard via agent_id)
        if self.custom_args_values:
            payload["custom_args_values"] = self.custom_args_values.model_dump(exclude_none=True)

        if self.call_config:
            call_config_dict: Dict[str, Any] = {
                "idle_timeout_warning": self.call_config.idle_timeout_warning,
                "idle_timeout_end": self.call_config.idle_timeout_end,
                "max_call_length": self.call_config.max_call_length,
            }

            if self.call_config.call_retry_config:
                call_config_dict["call_retry_config"] = self.call_config.call_retry_config.model_dump()

            if self.call_config.call_time:
                call_config_dict["call_time"] = self.call_config.call_time.model_dump()

            payload["call_config"] = call_config_dict

        return payload


class StartCampaignRequest(BaseModel):
    """Request model for starting a campaign"""
    agent_id: str = Field(description="ID of the agent that will handle all campaign calls")
    list_id: str = Field(description="ID of the uploaded campaign contact list")
    from_numbers: list[str] = Field(description="Array of phone numbers to use for outbound calls")
