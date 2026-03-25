"""
Custom exception classes for the Government Scheme Copilot.

This module defines custom exceptions for different error scenarios
with proper error codes and context information.
"""

from typing import Optional, Dict, Any
from models.errors import ErrorCode, ErrorSeverity


class SchemeAPIException(Exception):
    """
    Base exception class for all Scheme API errors.
    
    This provides a consistent interface for all custom exceptions
    with error codes, severity levels, and additional context.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Standardized error code
            severity: Error severity level
            details: Additional context information
            original_exception: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.details = details or {}
        self.original_exception = original_exception
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        result = {
            "message": self.message,
            "error_code": self.error_code.value,
            "severity": self.severity.value,
            "details": self.details
        }
        
        if self.original_exception:
            result["details"]["original_error"] = str(self.original_exception)
            result["details"]["original_type"] = type(self.original_exception).__name__
        
        return result


class ValidationException(SchemeAPIException):
    """Exception raised for input validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        expected_format: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if field_name:
            details['field_name'] = field_name
        if invalid_value is not None:
            details['invalid_value'] = invalid_value
        if expected_format:
            details['expected_format'] = expected_format
        
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_INPUT,
            severity=ErrorSeverity.LOW,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )


class SchemeNotFoundException(SchemeAPIException):
    """Exception raised when a requested scheme is not found."""
    
    def __init__(
        self,
        scheme_id: Optional[str] = None,
        search_criteria: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if scheme_id:
            message = f"Scheme with ID '{scheme_id}' not found"
            details = {'scheme_id': scheme_id}
        elif search_criteria:
            message = "No schemes found matching the specified criteria"
            details = {'search_criteria': search_criteria}
        else:
            message = "Requested scheme not found"
            details = {}
        
        details.update(kwargs.get('details', {}))
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SCHEME_NOT_FOUND,
            severity=ErrorSeverity.LOW,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )


class ExternalServiceException(SchemeAPIException):
    """Exception raised for external service failures."""
    
    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
        fallback_available: bool = False,
        **kwargs
    ):
        if not message:
            message = f"External service '{service_name}' is unavailable"
        
        details = kwargs.get('details', {})
        details.update({
            'service_name': service_name,
            'fallback_available': fallback_available
        })
        
        if status_code:
            details['status_code'] = status_code
        if retry_after:
            details['retry_after'] = retry_after
        
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            severity=ErrorSeverity.MEDIUM if fallback_available else ErrorSeverity.HIGH,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )


class TranslationServiceException(ExternalServiceException):
    """Exception raised for translation service failures."""
    
    def __init__(
        self,
        target_language: str,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Translation to '{target_language}' failed"
        
        details = kwargs.get('details', {})
        details['target_language'] = target_language
        
        super().__init__(
            service_name="Sarvam AI Translation",
            message=message,
            fallback_available=True,  # Can fallback to English
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )
        
        # Override error code for translation-specific errors
        self.error_code = ErrorCode.TRANSLATION_SERVICE_ERROR


class EmbeddingServiceException(ExternalServiceException):
    """Exception raised for embedding service failures."""
    
    def __init__(
        self,
        query: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = "Embedding generation failed"
        
        details = kwargs.get('details', {})
        if query:
            details['query'] = query[:100]  # Truncate for privacy
        
        super().__init__(
            service_name="Embedding Service",
            message=message,
            fallback_available=True,  # Can use zero vectors
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )
        
        # Override error code for embedding-specific errors
        self.error_code = ErrorCode.EMBEDDING_SERVICE_ERROR


class TimeoutException(SchemeAPIException):
    """Exception raised for timeout scenarios."""
    
    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        
        details = kwargs.get('details', {})
        details.update({
            'operation': operation,
            'timeout_seconds': timeout_seconds
        })
        
        super().__init__(
            message=message,
            error_code=ErrorCode.REQUEST_TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )


class ExternalServiceTimeoutException(TimeoutException):
    """Exception raised for external service timeout scenarios."""
    
    def __init__(
        self,
        service_name: str,
        timeout_seconds: float,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"External service '{service_name}' timed out after {timeout_seconds} seconds"
        
        details = kwargs.get('details', {})
        details['service_name'] = service_name
        
        super().__init__(
            operation=f"External service call to {service_name}",
            timeout_seconds=timeout_seconds,
            message=message,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )
        
        # Override error code for external service timeouts
        self.error_code = ErrorCode.EXTERNAL_SERVICE_TIMEOUT


class RateLimitException(SchemeAPIException):
    """Exception raised for rate limiting scenarios."""
    
    def __init__(
        self,
        rate_limit_type: str,
        limit: int,
        window_seconds: int,
        retry_after: int,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Rate limit exceeded: {limit} {rate_limit_type} per {window_seconds} seconds"
        
        details = kwargs.get('details', {})
        details.update({
            'rate_limit_type': rate_limit_type,
            'limit': limit,
            'window_seconds': window_seconds,
            'retry_after': retry_after
        })
        
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            severity=ErrorSeverity.LOW,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )


class ConfigurationException(SchemeAPIException):
    """Exception raised for configuration errors."""
    
    def __init__(
        self,
        config_key: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            if config_key:
                message = f"Invalid configuration for '{config_key}'"
            else:
                message = "Configuration error"
        
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )


class ProcessingException(SchemeAPIException):
    """Exception raised for general processing errors."""
    
    def __init__(
        self,
        operation: str,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            message = f"Processing failed for operation: {operation}"
        
        details = kwargs.get('details', {})
        details['operation'] = operation
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **{k: v for k, v in kwargs.items() if k != 'details'}
        )