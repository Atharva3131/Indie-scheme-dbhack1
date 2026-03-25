"""
Error handling models for the Government Scheme Copilot.

This module contains Pydantic models for structured error responses
and error code definitions.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Enumeration for standardized error codes."""
    
    # Input validation errors (400)
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"
    INVALID_AGE_RANGE = "INVALID_AGE_RANGE"
    INVALID_INCOME_VALUE = "INVALID_INCOME_VALUE"
    INVALID_CATEGORY = "INVALID_CATEGORY"
    INVALID_STATE = "INVALID_STATE"
    INVALID_QUERY_LENGTH = "INVALID_QUERY_LENGTH"
    INVALID_PAGINATION = "INVALID_PAGINATION"
    
    # Resource not found errors (404)
    SCHEME_NOT_FOUND = "SCHEME_NOT_FOUND"
    USER_PROFILE_NOT_FOUND = "USER_PROFILE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    
    # External service errors (503)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TRANSLATION_SERVICE_ERROR = "TRANSLATION_SERVICE_ERROR"
    SARVAM_AI_ERROR = "SARVAM_AI_ERROR"
    EMBEDDING_SERVICE_ERROR = "EMBEDDING_SERVICE_ERROR"
    
    # Rate limiting errors (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    API_QUOTA_EXCEEDED = "API_QUOTA_EXCEEDED"
    
    # Internal server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    
    # Authentication/Authorization errors (401/403)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    
    # Timeout errors (408)
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"


class ErrorSeverity(str, Enum):
    """Enumeration for error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorResponse(BaseModel):
    """
    Standardized error response model.
    
    This model provides consistent error information across
    all API endpoints with proper error codes and details.
    """
    status: str = Field(default="error", description="Response status (always 'error')")
    error_code: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details and context")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error occurrence timestamp")
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracking")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Error severity level")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "Age must be between 0 and 120",
                "details": {
                    "field": "age",
                    "provided_value": 150,
                    "valid_range": "0-120"
                },
                "timestamp": "2024-01-01T00:00:00Z",
                "request_id": "req_123456789",
                "severity": "medium"
            }
        }
        
        @staticmethod
        def json_schema_serialization_defaults_required():
            return True


class ValidationErrorDetail(BaseModel):
    """
    Detailed validation error information.
    
    This model provides specific information about
    field validation failures.
    """
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    invalid_value: Optional[Any] = Field(None, description="The invalid value that was provided")
    expected_type: Optional[str] = Field(None, description="Expected data type or format")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "field": "age",
                "message": "ensure this value is greater than or equal to 0",
                "invalid_value": -5,
                "expected_type": "integer >= 0"
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """
    Specialized error response for validation failures.
    
    This model extends ErrorResponse with detailed validation
    error information for multiple field failures.
    """
    validation_errors: List[ValidationErrorDetail] = Field(..., description="List of validation errors")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "Request validation failed",
                "details": {
                    "total_errors": 2,
                    "failed_fields": ["age", "income"]
                },
                "validation_errors": [
                    {
                        "field": "age",
                        "message": "ensure this value is greater than or equal to 0",
                        "invalid_value": -5,
                        "expected_type": "integer >= 0"
                    },
                    {
                        "field": "income",
                        "message": "ensure this value is greater than or equal to 0",
                        "invalid_value": -1000,
                        "expected_type": "float >= 0"
                    }
                ],
                "timestamp": "2024-01-01T00:00:00Z",
                "severity": "medium"
            }
        }


class ExternalServiceErrorResponse(ErrorResponse):
    """
    Specialized error response for external service failures.
    
    This model extends ErrorResponse with information about
    external service integration failures.
    """
    service_name: str = Field(..., description="Name of the external service that failed")
    service_status_code: Optional[int] = Field(None, description="HTTP status code from external service")
    retry_after: Optional[int] = Field(None, description="Suggested retry delay in seconds")
    fallback_used: bool = Field(default=False, description="Whether fallback mechanism was used")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_code": "TRANSLATION_SERVICE_ERROR",
                "message": "Translation service is temporarily unavailable",
                "details": {
                    "attempted_language": "hindi",
                    "fallback_response": "Response provided in English"
                },
                "service_name": "Sarvam AI Translation",
                "service_status_code": 503,
                "retry_after": 60,
                "fallback_used": True,
                "timestamp": "2024-01-01T00:00:00Z",
                "severity": "medium"
            }
        }


class RateLimitErrorResponse(ErrorResponse):
    """
    Specialized error response for rate limiting.
    
    This model extends ErrorResponse with rate limiting
    information and retry guidance.
    """
    rate_limit_type: str = Field(..., description="Type of rate limit exceeded")
    limit: int = Field(..., description="Rate limit threshold")
    window_seconds: int = Field(..., description="Rate limit window in seconds")
    retry_after: int = Field(..., description="Seconds until rate limit resets")
    requests_remaining: int = Field(default=0, description="Remaining requests in current window")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "API rate limit exceeded",
                "details": {
                    "client_ip": "192.168.1.1",
                    "endpoint": "/api/search"
                },
                "rate_limit_type": "requests_per_minute",
                "limit": 100,
                "window_seconds": 60,
                "retry_after": 45,
                "requests_remaining": 0,
                "timestamp": "2024-01-01T00:00:00Z",
                "severity": "low"
            }
        }


# HTTP status code mappings for error codes
ERROR_CODE_STATUS_MAP = {
    # 400 Bad Request
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.MISSING_REQUIRED_FIELD: 400,
    ErrorCode.INVALID_FIELD_VALUE: 400,
    ErrorCode.INVALID_AGE_RANGE: 400,
    ErrorCode.INVALID_INCOME_VALUE: 400,
    ErrorCode.INVALID_CATEGORY: 400,
    ErrorCode.INVALID_STATE: 400,
    ErrorCode.INVALID_QUERY_LENGTH: 400,
    ErrorCode.INVALID_PAGINATION: 400,
    
    # 401 Unauthorized
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INVALID_API_KEY: 401,
    
    # 403 Forbidden
    ErrorCode.FORBIDDEN: 403,
    
    # 404 Not Found
    ErrorCode.SCHEME_NOT_FOUND: 404,
    ErrorCode.USER_PROFILE_NOT_FOUND: 404,
    ErrorCode.ENDPOINT_NOT_FOUND: 404,
    
    # 408 Request Timeout
    ErrorCode.REQUEST_TIMEOUT: 408,
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: 408,
    
    # 429 Too Many Requests
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.API_QUOTA_EXCEEDED: 429,
    
    # 500 Internal Server Error
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.CONFIGURATION_ERROR: 500,
    ErrorCode.PROCESSING_ERROR: 500,
    
    # 503 Service Unavailable
    ErrorCode.EXTERNAL_SERVICE_ERROR: 503,
    ErrorCode.TRANSLATION_SERVICE_ERROR: 503,
    ErrorCode.SARVAM_AI_ERROR: 503,
    ErrorCode.EMBEDDING_SERVICE_ERROR: 503,
}


def get_http_status_code(error_code: ErrorCode) -> int:
    """
    Get the appropriate HTTP status code for an error code.
    
    Args:
        error_code: The error code to map
        
    Returns:
        HTTP status code (defaults to 500 if not found)
    """
    return ERROR_CODE_STATUS_MAP.get(error_code, 500)