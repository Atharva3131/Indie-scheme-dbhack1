"""
Timeout handling utilities for external API calls and operations.

This module provides decorators and context managers for handling
timeouts gracefully with proper error reporting.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from contextlib import asynccontextmanager

from models.exceptions import TimeoutException, ExternalServiceTimeoutException

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TimeoutConfig:
    """Configuration for timeout handling."""
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        external_service_timeout: float = 15.0,
        database_timeout: float = 10.0,
        cache_timeout: float = 5.0
    ):
        """
        Initialize timeout configuration.
        
        Args:
            default_timeout: Default timeout for general operations
            external_service_timeout: Timeout for external API calls
            database_timeout: Timeout for database operations
            cache_timeout: Timeout for cache operations
        """
        self.default_timeout = default_timeout
        self.external_service_timeout = external_service_timeout
        self.database_timeout = database_timeout
        self.cache_timeout = cache_timeout


# Global timeout configuration
timeout_config = TimeoutConfig()


def with_timeout(
    timeout_seconds: Optional[float] = None,
    operation_name: Optional[str] = None,
    raise_on_timeout: bool = True
):
    """
    Decorator to add timeout handling to async functions.
    
    Args:
        timeout_seconds: Timeout in seconds (uses default if None)
        operation_name: Name of operation for error messages
        raise_on_timeout: Whether to raise exception on timeout
        
    Returns:
        Decorated function with timeout handling
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            timeout = timeout_seconds or timeout_config.default_timeout
            op_name = operation_name or func.__name__
            
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError as e:
                logger.warning(f"Operation '{op_name}' timed out after {timeout} seconds")
                
                if raise_on_timeout:
                    raise TimeoutException(
                        operation=op_name,
                        timeout_seconds=timeout,
                        original_exception=e
                    )
                else:
                    return None
        
        return wrapper
    return decorator


def with_external_service_timeout(
    service_name: str,
    timeout_seconds: Optional[float] = None,
    fallback_value: Any = None
):
    """
    Decorator for external service calls with timeout handling.
    
    Args:
        service_name: Name of the external service
        timeout_seconds: Timeout in seconds (uses external service default if None)
        fallback_value: Value to return on timeout (raises exception if None)
        
    Returns:
        Decorated function with external service timeout handling
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            timeout = timeout_seconds or timeout_config.external_service_timeout
            
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError as e:
                logger.warning(f"External service '{service_name}' timed out after {timeout} seconds")
                
                if fallback_value is not None:
                    logger.info(f"Using fallback value for '{service_name}' timeout")
                    return fallback_value
                else:
                    raise ExternalServiceTimeoutException(
                        service_name=service_name,
                        timeout_seconds=timeout,
                        original_exception=e
                    )
        
        return wrapper
    return decorator


@asynccontextmanager
async def timeout_context(
    timeout_seconds: float,
    operation_name: str = "operation"
):
    """
    Async context manager for timeout handling.
    
    Args:
        timeout_seconds: Timeout in seconds
        operation_name: Name of operation for error messages
        
    Yields:
        Context for the timed operation
        
    Raises:
        TimeoutException: If operation times out
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            yield
    except asyncio.TimeoutError as e:
        logger.warning(f"Context operation '{operation_name}' timed out after {timeout_seconds} seconds")
        raise TimeoutException(
            operation=operation_name,
            timeout_seconds=timeout_seconds,
            original_exception=e
        )


class TimeoutManager:
    """
    Manager for handling multiple timeout scenarios.
    
    This class provides methods for different types of operations
    with appropriate timeout values and error handling.
    """
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        """
        Initialize timeout manager.
        
        Args:
            config: Timeout configuration (uses global if None)
        """
        self.config = config or timeout_config
    
    async def execute_with_timeout(
        self,
        coro,
        timeout_seconds: Optional[float] = None,
        operation_name: str = "operation",
        fallback_value: Any = None
    ) -> Any:
        """
        Execute coroutine with timeout handling.
        
        Args:
            coro: Coroutine to execute
            timeout_seconds: Timeout in seconds
            operation_name: Name for logging and errors
            fallback_value: Value to return on timeout (raises if None)
            
        Returns:
            Result of coroutine or fallback value
            
        Raises:
            TimeoutException: If timeout occurs and no fallback
        """
        timeout = timeout_seconds or self.config.default_timeout
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning(f"Operation '{operation_name}' timed out after {timeout} seconds")
            
            if fallback_value is not None:
                logger.info(f"Using fallback value for '{operation_name}' timeout")
                return fallback_value
            else:
                raise TimeoutException(
                    operation=operation_name,
                    timeout_seconds=timeout,
                    original_exception=e
                )
    
    async def external_service_call(
        self,
        coro,
        service_name: str,
        timeout_seconds: Optional[float] = None,
        fallback_value: Any = None
    ) -> Any:
        """
        Execute external service call with timeout.
        
        Args:
            coro: Coroutine for external service call
            service_name: Name of external service
            timeout_seconds: Timeout in seconds
            fallback_value: Value to return on timeout
            
        Returns:
            Result of service call or fallback value
            
        Raises:
            ExternalServiceTimeoutException: If timeout occurs and no fallback
        """
        timeout = timeout_seconds or self.config.external_service_timeout
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning(f"External service '{service_name}' timed out after {timeout} seconds")
            
            if fallback_value is not None:
                logger.info(f"Using fallback value for '{service_name}' timeout")
                return fallback_value
            else:
                raise ExternalServiceTimeoutException(
                    service_name=service_name,
                    timeout_seconds=timeout,
                    original_exception=e
                )
    
    async def database_operation(
        self,
        coro,
        operation_name: str = "database_operation",
        timeout_seconds: Optional[float] = None
    ) -> Any:
        """
        Execute database operation with timeout.
        
        Args:
            coro: Coroutine for database operation
            operation_name: Name of database operation
            timeout_seconds: Timeout in seconds
            
        Returns:
            Result of database operation
            
        Raises:
            TimeoutException: If timeout occurs
        """
        timeout = timeout_seconds or self.config.database_timeout
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.error(f"Database operation '{operation_name}' timed out after {timeout} seconds")
            raise TimeoutException(
                operation=f"Database: {operation_name}",
                timeout_seconds=timeout,
                original_exception=e
            )
    
    async def cache_operation(
        self,
        coro,
        operation_name: str = "cache_operation",
        timeout_seconds: Optional[float] = None,
        fallback_value: Any = None
    ) -> Any:
        """
        Execute cache operation with timeout.
        
        Args:
            coro: Coroutine for cache operation
            operation_name: Name of cache operation
            timeout_seconds: Timeout in seconds
            fallback_value: Value to return on timeout
            
        Returns:
            Result of cache operation or fallback value
        """
        timeout = timeout_seconds or self.config.cache_timeout
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning(f"Cache operation '{operation_name}' timed out after {timeout} seconds")
            
            if fallback_value is not None:
                logger.info(f"Using fallback value for cache timeout: {operation_name}")
                return fallback_value
            else:
                # Cache timeouts are usually not critical
                logger.info(f"Cache timeout for '{operation_name}', continuing without cache")
                return None


# Global timeout manager instance
timeout_manager = TimeoutManager()


def configure_timeouts(
    default_timeout: float = 30.0,
    external_service_timeout: float = 15.0,
    database_timeout: float = 10.0,
    cache_timeout: float = 5.0
) -> None:
    """
    Configure global timeout settings.
    
    Args:
        default_timeout: Default timeout for general operations
        external_service_timeout: Timeout for external API calls
        database_timeout: Timeout for database operations
        cache_timeout: Timeout for cache operations
    """
    global timeout_config, timeout_manager
    
    timeout_config = TimeoutConfig(
        default_timeout=default_timeout,
        external_service_timeout=external_service_timeout,
        database_timeout=database_timeout,
        cache_timeout=cache_timeout
    )
    
    timeout_manager = TimeoutManager(timeout_config)
    
    logger.info(f"Timeout configuration updated: "
                f"default={default_timeout}s, "
                f"external={external_service_timeout}s, "
                f"database={database_timeout}s, "
                f"cache={cache_timeout}s")