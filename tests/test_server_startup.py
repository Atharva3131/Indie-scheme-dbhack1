"""
Test FastAPI server startup and basic functionality.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

class TestServerStartup:
    """Test server startup and basic endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint_response_format(self):
        """Test health endpoint returns correct format."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = ["status", "timestamp", "service", "version", "configuration"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify field values
        assert data["status"] == "healthy"
        assert data["service"] == "Government Scheme Copilot"
        assert data["version"] == "1.0.0"
        
        # Verify timestamp format (ISO 8601 with Z suffix)
        assert data["timestamp"].endswith("Z")
        
        # Verify configuration section
        config = data["configuration"]
        assert "valid" in config
        assert "external_services" in config
        assert "languages_supported" in config
        assert config["valid"] is True
    
    def test_root_endpoint_provides_navigation(self):
        """Test root endpoint provides navigation information."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify navigation fields
        assert data["message"] == "Government Scheme Copilot API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
        assert data["api_prefix"] == "/api"
        
        # Verify new fields from configuration
        assert "supported_languages" in data
        assert "features" in data
        assert "english" in data["supported_languages"]
        assert "hindi" in data["supported_languages"]
    
    def test_cors_middleware_configured(self):
        """Test CORS middleware is properly configured."""
        # Test that CORS middleware doesn't cause errors
        response = self.client.get("/health")
        assert response.status_code == 200
        
        # Test with origin header
        response = self.client.get(
            "/health", 
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
    
    def test_api_documentation_accessible(self):
        """Test that API documentation endpoints are accessible."""
        # Test OpenAPI schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert schema["info"]["title"] == "Government Scheme Copilot"
        assert schema["info"]["version"] == "1.0.0"
    
    def test_startup_shutdown_events(self):
        """Test that startup and shutdown events are configured."""
        # This test verifies the app can be created without errors
        # The actual startup/shutdown events are tested implicitly
        # when the TestClient is created and destroyed
        assert app is not None
        assert hasattr(app, 'router')
        
        # Verify health endpoint is registered
        routes = [route.path for route in app.routes]
        assert "/health" in routes
        assert "/" in routes
        assert "/config" in routes
    
    def test_config_endpoint_provides_public_configuration(self):
        """Test config endpoint returns public configuration information."""
        response = self.client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required sections
        required_sections = ["app_name", "version", "api_prefix", "features", 
                           "search_settings", "language_settings", "performance"]
        for section in required_sections:
            assert section in data, f"Missing required section: {section}"
        
        # Verify no sensitive information is exposed
        assert "sarvam_api_key" not in str(data)
        
        # Verify feature flags
        features = data["features"]
        assert "semantic_search" in features
        assert "translation" in features
        assert "llm_responses" in features
        
        # Verify language settings
        lang_settings = data["language_settings"]
        assert "default" in lang_settings
        assert "supported" in lang_settings
        assert lang_settings["default"] == "english"
        assert "english" in lang_settings["supported"]