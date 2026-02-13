"""
Custom exceptions for the AI LLM Service
"""

from typing import Dict, Any, Optional


class LLMServiceError(Exception):
    """Base exception for LLM service errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}


class ValidationError(LLMServiceError):
    """Validation error"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class AuthenticationError(LLMServiceError):
    """Authentication error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTHENTICATION_ERROR")


class AuthorizationError(LLMServiceError):
    """Authorization error"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, error_code="AUTHORIZATION_ERROR")


class RateLimitError(LLMServiceError):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, error_code="RATE_LIMIT_ERROR")


class ModelNotAvailableError(LLMServiceError):
    """Requested model not available"""
    def __init__(self, model_name: str):
        super().__init__(
            f"Model '{model_name}' is not available",
            error_code="MODEL_NOT_AVAILABLE",
            details={"model_name": model_name}
        )


class PipelineError(LLMServiceError):
    """Pipeline execution error"""
    def __init__(self, pipeline_name: str, stage: str, message: str):
        super().__init__(
            f"Pipeline '{pipeline_name}' failed at stage '{stage}': {message}",
            error_code="PIPELINE_ERROR",
            details={"pipeline_name": pipeline_name, "stage": stage}
        )


class SafetyViolationError(LLMServiceError):
    """Safety violation detected"""
    def __init__(self, violation_type: str, severity: str):
        super().__init__(
            f"Safety violation detected: {violation_type}",
            error_code="SAFETY_VIOLATION",
            details={"violation_type": violation_type, "severity": severity}
        )


class ConfigurationError(LLMServiceError):
    """Configuration error"""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key} if config_key else {}
        )


class ExternalAPIError(LLMServiceError):
    """External API error"""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        api_url: Optional[str] = None,
        response_body: Optional[str] = None
    ):
        super().__init__(
            message,
            error_code="EXTERNAL_API_ERROR",
            details={
                "status_code": status_code,
                "api_url": api_url,
                "response_body": response_body
            }
        )
        self.status_code = status_code
        self.api_url = api_url
        self.response_body = response_body