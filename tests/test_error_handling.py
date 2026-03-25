"""
Tests for comprehensive error handling implementation.

This module tests custom exceptions, global error handlers,
timeout mechanisms, and graceful degradation.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models.exceptions import (
    SchemeAPIException, ValidationException, ExternalServiceException,
    TimeoutException, TranslationServiceException
)
from models.errors import ErrorCode, ErrorSeverity
from utils.timeout_handler import timeout_manager, with_timeout
from utils.error_handlers import error_handler


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_scheme_api_exception_creation(self):
        """Test basic SchemeAPIException creation."""
        exc = SchemeAPIException(
            message="Test error",
            error_code=ErrorCode.INVALID_INPUT,
            severity=ErrorSeverity.LOW,
            details={"field": "test"}
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == ErrorCode.INVALID_INPUT
        assert exc.severity == ErrorSeverity.LOW
        assert exc.details == {"field": "test"}
    
    def test_validation_exception(self):
        """Test ValidationException with field information."""
        exc = ValidationException(
            message="Invalid age",
            field_name="age",
            invalid_value=-5,
            expected_format="integer >= 0"
        )
        
        assert exc.error_code == ErrorCode.INVALID_INPUT
        assert exc.details["field_name"] == "age"
        assert exc.details["invalid_value"] == -5
    
    def test_external_service_exception(self):
        """Test ExternalServiceException with service details."""
        exc = ExternalServiceException(
            service_name="Sarvam AI",
            message="Service unavailable",
            status_code=503,
            fallback_available=True
        )
        
        assert exc.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert exc.details["service_name"] == "Sarvam AI"
        assert exc.details["status_code"] == 503
        assert exc.details["fallback_available"] is True
    
    def test_translation_service_exception(self):
        """Test TranslationServiceException specifics."""
        exc = TranslationServiceException(
            target_language="hindi",
            message="Translation failed"
        )
        
        assert exc.error_code == ErrorCode.TRANSLATION_SERVICE_ERROR
        assert exc.details["target_language"] == "hindi"
        assert exc.details["service_name"] == "Sarvam AI Translation"
    
    def test_timeout_exception(self):
        """Test TimeoutException with operation details."""
        exc = TimeoutException(
            operation="search_schemes",
            timeout_seconds=30.0,
            message="Operation timed out"
        )
        
        assert exc.error_code == ErrorCode.REQUEST_TIMEOUT
        assert exc.details["operation"] == "search_schemes"
        assert exc.details["timeout_seconds"] == 30.0


class TestTimeoutHandling:
    """Test timeout handling mechanisms."""
    
    @pytest.mark.asyncio
    async def test_timeout_decorator_success(self):
        """Test timeout decorator with successful operation."""
        
        @with_timeout(timeout_seconds=1.0, operation_name="test_op")
        async def fast_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await fast_operation()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_timeout_decorator_timeout(self):
        """Test timeout decorator with timeout scenario."""
        
        @with_timeout(timeout_seconds=0.1, operation_name="test_op")
        async def slow_operation():
            await asyncio.sleep(1.0)
            return "success"
        
        with pytest.raises(TimeoutException) as exc_info:
            await slow_operation()
        
        assert exc_info.value.details["operation"] == "test_op"
        assert exc_info.value.details["timeout_seconds"] == 0.1
    
    @pytest.mark.asyncio
    async def test_timeout_manager_external_service(self):
        """Test timeout manager for external service calls."""
        
        async def mock_service_call():
            await asyncio.sleep(0.1)
            return {"status": "success"}
        
        result = await timeout_manager.external_service_call(
            mock_service_call(),
            service_name="Test Service",
            timeout_seconds=1.0
        )
        
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_timeout_manager_with_fallback(self):
        """Test timeout manager with fallback value."""
        
        async def slow_service_call():
            await asyncio.sleep(1.0)
            return {"status": "success"}
        
        result = await timeout_manager.external_service_call(
            slow_service_call(),
            service_name="Test Service",
            timeout_seconds=0.1,
            fallback_value={"status": "fallback"}
        )
        
        assert result["status"] == "fallback"


class TestErrorHandlers:
    """Test global error handlers."""
    
    def test_error_handler_sanitization(self):
        """Test user data sanitization."""
        sensitive_data = {
            "api_key": "secret123",
            "password": "mypassword",
            "email": "user@example.com",
            "phone": "9876543210",
            "normal_field": "normal_value"
        }
        
        sanitized = error_handler.sanitize_user_data(sensitive_data)
        
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["password"] == "***REDACTED***"
        # Email and phone use different redaction patterns
        assert "REDACTED" in sanitized["email"]
        assert "REDACTED" in sanitized["phone"]
        assert sanitized["normal_field"] == "normal_value"
    
    def test_error_response_creation(self):
        """Test error response creation."""
        exc = ValidationException(
            message="Invalid input",
            field_name="age",
            invalid_value=-5
        )
        
        response_data = error_handler.create_error_response(
            exc, 
            request_id="test_123"
        )
        
        assert response_data["status_code"] == 400
        assert response_data["content"]["error_code"] == "INVALID_INPUT"
        assert response_data["content"]["message"] == "Invalid input"
        assert response_data["content"]["request_id"] == "test_123"


class TestAPIErrorHandling:
    """Test API-level error handling."""
    
    def test_validation_error_response(self):
        """Test API validation error handling."""
        client = TestClient(app)
        
        # Send invalid request to eligibility endpoint
        response = client.post(
            "/api/eligibility",
            json={
                "user_profile": {
                    "age": -5,  # Invalid age
                    "income": "invalid",  # Invalid type
                    "category": "InvalidCategory",  # Invalid enum
                    "occupation": "student"
                    # Missing required state field
                }
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert data["error_code"] == "INVALID_INPUT"
        assert "validation_errors" in data
    
    def test_not_found_error(self):
        """Test 404 error handling."""
        client = TestClient(app)
        
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
        # The response might be a FastAPI default 404, so check for basic structure
        data = response.json()
        assert "detail" in data or "status" in data
    
    def test_health_check_success(self):
        """Test health check endpoint."""
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        assert "configuration" in data


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""
    
    @pytest.mark.asyncio
    async def test_external_service_fallback(self):
        """Test fallback when external service fails."""
        from services.response import ResponseService
        
        # Mock a failing external service
        with patch('services.response.SarvamAIService') as mock_sarvam:
            mock_sarvam.return_value.llm_available = False
            
            response_service = ResponseService()
            
            # Should use fallback formatting
            result = await response_service.format_schemes(
                schemes=[],
                language="english"
            )
            
            # Should return a fallback response, not raise an exception
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_configuration_validation(self):
        """Test configuration validation on startup."""
        from config import settings
        
        validation_result = settings.validate_configuration()
        
        assert "valid" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result
        assert "configuration_summary" in validation_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])