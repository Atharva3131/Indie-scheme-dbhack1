"""
Global exception handlers for the Government Scheme Copilot.

This module provides centralized error handling with proper logging,
user privacy protection, and consistent error responses.
"""

import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import httpx

from models.errors import (
    ErrorResponse, ValidationErrorResponse, ExternalServiceErrorResponse,
    RateLimitErrorResponse, ErrorCode, ErrorSeverity, get_http_status_code
)
from models.exceptions import (
    SchemeAPIException, ValidationException, SchemeNotFoundException,
    ExternalServiceException, TimeoutException, RateLimitException,
    ConfigurationException, ProcessingException
)

# Configure logger for error handling
logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling with privacy protection and logging.
    
    This class provides methods for handling different types of errors
    while ensuring user privacy and proper error logging.
    """
    
    def __init__(self, enable_debug: bool = False):
        """
        Initialize error handler.
        
        Args:
            enable_debug: Whether to include debug information in responses
        """
        self.enable_debug = enable_debug
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID for error tracking."""
        return f"req_{uuid.uuid4().hex[:12]}"
    
    def sanitize_user_data(self, data: Any) -> Any:
        """
        Sanitize user data to protect privacy in logs.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data with sensitive information masked
        """
        if isinstance(data, dict):
            sanitized = {}
            sensitive_fields = {
                'api_key', 'password', 'token', 'secret', 'auth',
                'phone', 'email', 'aadhaar', 'pan', 'address'
            }
            
            for key, value in data.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in sensitive_fields):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self.sanitize_user_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        
        elif isinstance(data, list):
            return [self.sanitize_user_data(item) for item in data]
        
        elif isinstance(data, str) and len(data) > 100:
            # Truncate long strings to prevent log spam
            return data[:100] + "...[truncated]"
        
        return data
    
    def log_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with proper privacy protection.
        
        Args:
            error: The exception that occurred
            request: FastAPI request object (optional)
            request_id: Unique request identifier
            additional_context: Additional context for logging
        """
        context = {
            "request_id": request_id,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        # Add request information if available
        if request:
            context.update({
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "client_ip": request.client.host if request.client else "unknown"
            })
        
        # Add additional context
        if additional_context:
            context.update(self.sanitize_user_data(additional_context))
        
        # Log based on error severity
        if isinstance(error, SchemeAPIException):
            if error.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"Critical error: {context}")
            elif error.severity == ErrorSeverity.HIGH:
                logger.error(f"High severity error: {context}")
            elif error.severity == ErrorSeverity.MEDIUM:
                logger.warning(f"Medium severity error: {context}")
            else:
                logger.info(f"Low severity error: {context}")
        else:
            logger.error(f"Unhandled error: {context}")
        
        # Log stack trace for debugging (only in debug mode)
        if self.enable_debug:
            logger.debug(f"Stack trace for {request_id}: {traceback.format_exc()}")
    
    def create_error_response(
        self,
        error: Exception,
        request_id: str,
        status_code: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            error: The exception that occurred
            request_id: Unique request identifier
            status_code: HTTP status code (auto-determined if not provided)
            
        Returns:
            Error response dictionary
        """
        timestamp = datetime.now(timezone.utc)
        
        if isinstance(error, SchemeAPIException):
            response = ErrorResponse(
                error_code=error.error_code,
                message=error.message,
                details=error.details if self.enable_debug else None,
                timestamp=timestamp,
                request_id=request_id,
                severity=error.severity
            )
            status_code = status_code or get_http_status_code(error.error_code)
        
        elif isinstance(error, ValidationError):
            response = ValidationErrorResponse(
                error_code=ErrorCode.INVALID_INPUT,
                message="Request validation failed",
                details={"validation_errors": error.errors()} if self.enable_debug else None,
                validation_errors=[],  # Will be populated by specific handler
                timestamp=timestamp,
                request_id=request_id
            )
            status_code = status_code or 400
        
        elif isinstance(error, HTTPException):
            response = ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=error.detail,
                timestamp=timestamp,
                request_id=request_id
            )
            status_code = status_code or error.status_code
        
        else:
            # Generic error handling
            response = ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                details={"original_error": str(error)} if self.enable_debug else None,
                timestamp=timestamp,
                request_id=request_id,
                severity=ErrorSeverity.HIGH
            )
            status_code = status_code or 500
        
        # Convert to dict and handle datetime serialization
        response_dict = response.model_dump()
        if 'timestamp' in response_dict and isinstance(response_dict['timestamp'], datetime):
            response_dict['timestamp'] = response_dict['timestamp'].isoformat() + "Z"
        
        return {
            "status_code": status_code,
            "content": response_dict
        }


# Global error handler instance
error_handler = ErrorHandler()


def setup_error_handlers(app, enable_debug: bool = False):
    """
    Set up global exception handlers for FastAPI application.
    
    Args:
        app: FastAPI application instance
        enable_debug: Whether to enable debug mode for error responses
    """
    global error_handler
    error_handler = ErrorHandler(enable_debug=enable_debug)
    
    @app.exception_handler(SchemeAPIException)
    async def scheme_api_exception_handler(request: Request, exc: SchemeAPIException):
        """Handle custom SchemeAPI exceptions."""
        request_id = error_handler.generate_request_id()
        
        # Log the error
        error_handler.log_error(exc, request, request_id)
        
        # Create response
        response_data = error_handler.create_error_response(exc, request_id)
        
        return JSONResponse(
            status_code=response_data["status_code"],
            content=response_data["content"]
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        request_id = error_handler.generate_request_id()
        
        # Log the error
        error_handler.log_error(exc, request, request_id)
        
        # Create detailed validation error response
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "invalid_value": error.get("input"),
                "expected_type": error.get("type")
            })
        
        response = ValidationErrorResponse(
            error_code=ErrorCode.INVALID_INPUT,
            message="Request validation failed",
            details={
                "total_errors": len(validation_errors),
                "failed_fields": [err["field"] for err in validation_errors]
            },
            validation_errors=validation_errors,
            timestamp=datetime.now(timezone.utc),
            request_id=request_id
        )
        
        # Convert to dict and handle datetime serialization
        response_dict = response.model_dump()
        if 'timestamp' in response_dict and isinstance(response_dict['timestamp'], datetime):
            response_dict['timestamp'] = response_dict['timestamp'].isoformat() + "Z"
        
        return JSONResponse(
            status_code=400,
            content=response_dict
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        request_id = error_handler.generate_request_id()
        
        # Log the error
        error_handler.log_error(exc, request, request_id)
        
        # Create response
        response_data = error_handler.create_error_response(exc, request_id)
        
        return JSONResponse(
            status_code=response_data["status_code"],
            content=response_data["content"]
        )
    
    @app.exception_handler(httpx.HTTPError)
    async def httpx_exception_handler(request: Request, exc: httpx.HTTPError):
        """Handle HTTPX client errors (external service failures)."""
        request_id = error_handler.generate_request_id()
        
        # Convert to ExternalServiceException
        service_exception = ExternalServiceException(
            service_name="External API",
            message="External service request failed",
            original_exception=exc
        )
        
        # Log the error
        error_handler.log_error(service_exception, request, request_id)
        
        # Create response
        response = ExternalServiceErrorResponse(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="External service is temporarily unavailable",
            details={"service_error": str(exc)} if enable_debug else None,
            service_name="External API",
            service_status_code=getattr(exc.response, 'status_code', None) if hasattr(exc, 'response') else None,
            retry_after=60,
            fallback_used=False,
            timestamp=datetime.now(timezone.utc),
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=503,
            content=response.dict()
        )
    
    @app.exception_handler(TimeoutError)
    async def timeout_exception_handler(request: Request, exc: TimeoutError):
        """Handle timeout errors."""
        request_id = error_handler.generate_request_id()
        
        # Convert to TimeoutException
        timeout_exception = TimeoutException(
            operation="Request processing",
            timeout_seconds=30,  # Default timeout
            original_exception=exc
        )
        
        # Log the error
        error_handler.log_error(timeout_exception, request, request_id)
        
        # Create response
        response_data = error_handler.create_error_response(timeout_exception, request_id)
        
        return JSONResponse(
            status_code=response_data["status_code"],
            content=response_data["content"]
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle all other unhandled exceptions."""
        request_id = error_handler.generate_request_id()
        
        # Log the error
        error_handler.log_error(exc, request, request_id)
        
        # Create generic error response
        response = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again later.",
            details={"error_type": type(exc).__name__} if enable_debug else None,
            timestamp=datetime.now(timezone.utc),
            request_id=request_id,
            severity=ErrorSeverity.HIGH
        )
        
        # Convert to dict and handle datetime serialization
        response_dict = response.model_dump()
        if 'timestamp' in response_dict and isinstance(response_dict['timestamp'], datetime):
            response_dict['timestamp'] = response_dict['timestamp'].isoformat() + "Z"
        
        return JSONResponse(
            status_code=500,
            content=response_dict
        )


def handle_graceful_degradation(
    operation_name: str,
    fallback_function,
    *args,
    **kwargs
):
    """
    Decorator for graceful degradation of external service calls.
    
    Args:
        operation_name: Name of the operation for logging
        fallback_function: Function to call if main operation fails
        *args, **kwargs: Arguments to pass to fallback function
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*func_args, **func_kwargs):
            try:
                return await func(*func_args, **func_kwargs)
            except Exception as e:
                logger.warning(f"Operation '{operation_name}' failed, using fallback: {e}")
                
                if fallback_function:
                    try:
                        return await fallback_function(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback for '{operation_name}' also failed: {fallback_error}")
                        raise ExternalServiceException(
                            service_name=operation_name,
                            message=f"Both primary and fallback operations failed",
                            original_exception=e
                        )
                else:
                    raise ExternalServiceException(
                        service_name=operation_name,
                        message=f"Operation failed and no fallback available",
                        original_exception=e
                    )
        
        return wrapper
    return decorator