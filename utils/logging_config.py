"""
Logging configuration with privacy protection for the Government Scheme Copilot.

This module provides structured logging with user privacy protection,
error tracking, and performance monitoring capabilities.
"""

import logging
import logging.handlers
import sys
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pathlib import Path

from config import settings


class PrivacyProtectedFormatter(logging.Formatter):
    """
    Custom formatter that sanitizes sensitive information from log messages.
    
    This formatter automatically redacts common sensitive patterns like
    API keys, phone numbers, email addresses, and other PII.
    """
    
    # Patterns for sensitive information
    SENSITIVE_PATTERNS = {
        'api_key': re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})', re.IGNORECASE),
        'bearer_token': re.compile(r'(bearer\s+)([a-zA-Z0-9_.-]{20,})', re.IGNORECASE),
        'password': re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s]{6,})', re.IGNORECASE),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'(\+91|91)?[-.\s]?[6-9]\d{9}'),
        'aadhaar': re.compile(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'),
        'pan': re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
        'credit_card': re.compile(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'),
    }
    
    def __init__(self, *args, **kwargs):
        """Initialize the privacy-protected formatter."""
        super().__init__(*args, **kwargs)
    
    def sanitize_message(self, message: str) -> str:
        """
        Sanitize log message by redacting sensitive information.
        
        Args:
            message: Original log message
            
        Returns:
            Sanitized message with sensitive data redacted
        """
        sanitized = message
        
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            if pattern_name in ['api_key', 'bearer_token', 'password']:
                # Keep the field name but redact the value
                sanitized = pattern.sub(r'\1***REDACTED***', sanitized)
            else:
                # Completely redact the sensitive data
                sanitized = pattern.sub(f'***{pattern_name.upper()}_REDACTED***', sanitized)
        
        return sanitized
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with privacy protection.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted and sanitized log message
        """
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.sanitize_message(record.msg)
        
        # Sanitize arguments if present
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self.sanitize_message(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return super().format(record)


class JSONFormatter(PrivacyProtectedFormatter):
    """
    JSON formatter for structured logging with privacy protection.
    
    This formatter outputs logs in JSON format for better parsing
    and analysis while maintaining privacy protection.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log message
        """
        # First apply privacy protection
        super().format(record)
        
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        
        return json.dumps(log_entry, ensure_ascii=False)


class PerformanceLogger:
    """
    Logger for tracking performance metrics and slow operations.
    
    This class provides methods for logging performance data
    while maintaining privacy protection.
    """
    
    def __init__(self, logger_name: str = "performance"):
        """
        Initialize performance logger.
        
        Args:
            logger_name: Name of the logger instance
        """
        self.logger = logging.getLogger(logger_name)
    
    def log_operation_time(
        self,
        operation: str,
        duration_ms: float,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log operation timing information.
        
        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            request_id: Request identifier
            additional_data: Additional context data
        """
        extra = {
            'operation': operation,
            'duration': duration_ms
        }
        
        if request_id:
            extra['request_id'] = request_id
        
        if additional_data:
            # Sanitize additional data
            sanitized_data = self._sanitize_data(additional_data)
            extra.update(sanitized_data)
        
        if duration_ms > 1000:  # Log slow operations (>1s) as warnings
            self.logger.warning(f"Slow operation: {operation} took {duration_ms:.2f}ms", extra=extra)
        elif duration_ms > 500:  # Log moderately slow operations (>500ms) as info
            self.logger.info(f"Operation: {operation} took {duration_ms:.2f}ms", extra=extra)
        else:
            self.logger.debug(f"Operation: {operation} took {duration_ms:.2f}ms", extra=extra)
    
    def log_external_service_call(
        self,
        service_name: str,
        operation: str,
        duration_ms: float,
        status_code: Optional[int] = None,
        success: bool = True,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log external service call metrics.
        
        Args:
            service_name: Name of external service
            operation: Operation performed
            duration_ms: Duration in milliseconds
            status_code: HTTP status code if applicable
            success: Whether the call was successful
            request_id: Request identifier
        """
        extra = {
            'operation': f"{service_name}:{operation}",
            'duration': duration_ms,
            'service_name': service_name,
            'success': success
        }
        
        if status_code:
            extra['status_code'] = status_code
        
        if request_id:
            extra['request_id'] = request_id
        
        level = logging.INFO if success else logging.WARNING
        status = "succeeded" if success else "failed"
        
        self.logger.log(
            level,
            f"External service call {status}: {service_name}.{operation} "
            f"took {duration_ms:.2f}ms",
            extra=extra
        )
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data dictionary for logging.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data dictionary
        """
        sanitized = {}
        sensitive_keys = {'password', 'api_key', 'token', 'secret', 'auth'}
        
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Set up application logging with privacy protection.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Path to log file (optional)
        enable_console: Whether to enable console logging
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = PrivacyProtectedFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set up specific loggers
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Performance logger
    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(logging.INFO)
    
    # Security logger for authentication/authorization events
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.INFO)
    
    logging.info(f"Logging configured: level={log_level}, format={log_format}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with privacy protection.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_performance_logger() -> PerformanceLogger:
    """
    Get performance logger instance.
    
    Returns:
        PerformanceLogger instance
    """
    return PerformanceLogger()


# Initialize logging based on settings
def initialize_logging() -> None:
    """Initialize logging configuration from settings."""
    setup_logging(
        log_level=settings.log_level.value,
        log_format="json" if settings.enable_json_logging else "text",
        log_file=settings.log_file_path,
        enable_console=True,
        max_file_size=settings.max_log_file_size,
        backup_count=settings.log_backup_count
    )