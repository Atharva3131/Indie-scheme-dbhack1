"""
Test configuration management system.
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from config import Settings, create_settings, LanguageCode, LogLevel


class TestConfigurationSettings:
    """Test configuration settings and validation."""
    
    def test_default_configuration_values(self):
        """Test that default configuration values are set correctly."""
        settings = Settings()
        
        # Application settings
        assert settings.app_name == "Government Scheme Copilot"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.log_level == LogLevel.INFO
        
        # Server settings
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.reload is False
        assert settings.workers == 1
        
        # API settings
        assert settings.api_prefix == "/api"
        assert settings.cors_origins == ["*"]
        
        # External services
        assert settings.sarvam_api_key is None
        assert settings.enable_translation is True
        assert settings.enable_llm_responses is True
        
        # Search configuration
        assert settings.similarity_threshold == 0.1
        assert settings.max_search_results == 10
        assert settings.embedding_dimensions == 384
        assert settings.enable_semantic_search is True
        
        # Language settings
        assert settings.default_language == LanguageCode.ENGLISH
        assert LanguageCode.ENGLISH in settings.supported_languages
        assert LanguageCode.HINDI in settings.supported_languages
    
    def test_environment_variable_override(self):
        """Test that environment variables override default values."""
        env_vars = {
            "SCHEME_HOST": "localhost",
            "SCHEME_PORT": "9000",
            "SCHEME_DEBUG": "true",
            "SCHEME_SIMILARITY_THRESHOLD": "0.5",
            "SCHEME_MAX_SEARCH_RESULTS": "20",
            "SCHEME_SARVAM_API_KEY": "test_api_key",
            "SCHEME_DEFAULT_LANGUAGE": "hindi"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.host == "localhost"
            assert settings.port == 9000
            assert settings.debug is True
            assert settings.similarity_threshold == 0.5
            assert settings.max_search_results == 20
            assert settings.sarvam_api_key == "test_api_key"
            assert settings.default_language == LanguageCode.HINDI
    
    def test_port_validation(self):
        """Test port number validation."""
        # Valid port
        settings = Settings(port=8080)
        assert settings.port == 8080
        
        # Invalid ports should raise validation error
        with pytest.raises(ValueError):
            Settings(port=0)
        
        with pytest.raises(ValueError):
            Settings(port=70000)
    
    def test_similarity_threshold_validation(self):
        """Test similarity threshold validation."""
        # Valid threshold
        settings = Settings(similarity_threshold=0.7)
        assert settings.similarity_threshold == 0.7
        
        # Invalid thresholds should raise validation error
        with pytest.raises(ValueError):
            Settings(similarity_threshold=-0.1)
        
        with pytest.raises(ValueError):
            Settings(similarity_threshold=1.5)
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation."""
        # Valid origins
        settings = Settings(cors_origins=["http://localhost:3000", "https://example.com"])
        assert "http://localhost:3000" in settings.cors_origins
        assert "https://example.com" in settings.cors_origins
        
        # Empty list should default to ["*"]
        settings = Settings(cors_origins=[])
        assert settings.cors_origins == ["*"]
    
    def test_supported_languages_validation(self):
        """Test that default language is included in supported languages."""
        settings = Settings(
            default_language=LanguageCode.HINDI,
            supported_languages=[LanguageCode.ENGLISH]
        )
        
        # Run validation to trigger the language check
        validation_results = settings.validate_configuration()
        
        # Hindi should be automatically added to supported languages during validation
        assert LanguageCode.HINDI in settings.supported_languages
        assert LanguageCode.ENGLISH in settings.supported_languages
    
    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        # Create a temporary schemes file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"schemes": []}')
            temp_file = f.name
        
        try:
            settings = Settings(
                schemes_data_path=temp_file,
                sarvam_api_key="test_key"
            )
            
            validation_results = settings.validate_configuration()
            
            assert validation_results["valid"] is True
            assert "configuration_summary" in validation_results
            assert "external_services" in validation_results["configuration_summary"]
            
        finally:
            os.unlink(temp_file)
    
    def test_configuration_validation_missing_data_file(self):
        """Test configuration validation with missing data file."""
        settings = Settings(schemes_data_path="/nonexistent/file.json")
        
        validation_results = settings.validate_configuration()
        
        assert validation_results["valid"] is False
        assert any("not found" in error for error in validation_results["errors"])
    
    def test_configuration_validation_warnings(self):
        """Test configuration validation warnings."""
        settings = Settings(
            enable_translation=True,
            sarvam_api_key=None,  # This should generate a warning
            cache_size=6000,  # This should generate a warning
            cors_origins=["*"],
            debug=False  # CORS warning in production
        )
        
        validation_results = settings.validate_configuration()
        
        # Should have warnings but still be valid
        assert len(validation_results["warnings"]) > 0
        assert any("API key" in warning for warning in validation_results["warnings"])
    
    def test_get_external_service_config(self):
        """Test external service configuration getter."""
        settings = Settings(
            sarvam_api_key="test_key",
            sarvam_base_url="https://test.api.com",
            enable_translation=True,
            enable_llm_responses=False,
            external_service_timeout=15
        )
        
        config = settings.get_external_service_config()
        
        assert config["sarvam_api_key"] == "test_key"
        assert config["sarvam_base_url"] == "https://test.api.com"
        assert config["enable_translation"] is True
        assert config["enable_llm_responses"] is False
        assert config["timeout"] == 15
    
    def test_get_search_config(self):
        """Test search configuration getter."""
        settings = Settings(
            similarity_threshold=0.4,
            max_search_results=15,
            embedding_dimensions=512,
            enable_semantic_search=False
        )
        
        config = settings.get_search_config()
        
        assert config["similarity_threshold"] == 0.4
        assert config["max_results"] == 15
        assert config["embedding_dimensions"] == 512
        assert config["enable_semantic_search"] is False
    
    def test_get_performance_config(self):
        """Test performance configuration getter."""
        settings = Settings(
            cache_size=2000,
            cache_ttl=7200,
            request_timeout=45,
            max_concurrent_requests=200
        )
        
        config = settings.get_performance_config()
        
        assert config["cache_size"] == 2000
        assert config["cache_ttl"] == 7200
        assert config["request_timeout"] == 45
        assert config["max_concurrent_requests"] == 200


class TestCreateSettings:
    """Test the create_settings function."""
    
    def test_create_settings_success(self):
        """Test successful settings creation."""
        # Create a temporary schemes file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"schemes": []}')
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {"SCHEME_SCHEMES_DATA_PATH": temp_file}):
                settings = create_settings()
                assert isinstance(settings, Settings)
                assert settings.schemes_data_path == temp_file
        finally:
            os.unlink(temp_file)
    
    def test_create_settings_validation_failure(self):
        """Test settings creation with validation failure."""
        with patch.dict(os.environ, {"SCHEME_SCHEMES_DATA_PATH": "/nonexistent/file.json"}):
            with pytest.raises(ValueError, match="Configuration validation failed"):
                create_settings()
    
    @patch('config.logger')
    def test_create_settings_logging(self, mock_logger):
        """Test that create_settings logs appropriately."""
        # Create a temporary schemes file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"schemes": []}')
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {"SCHEME_SCHEMES_DATA_PATH": temp_file}):
                settings = create_settings()
                
                # Verify info logging was called
                mock_logger.info.assert_called()
                
                # Check that configuration summary was logged
                info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
                assert any("Configuration loaded successfully" in call for call in info_calls)
                
        finally:
            os.unlink(temp_file)


class TestConfigurationIntegration:
    """Test configuration integration with the application."""
    
    def test_configuration_with_env_file(self):
        """Test configuration loading from .env file."""
        # Create a temporary .env file
        env_content = """
SCHEME_HOST=test.example.com
SCHEME_PORT=9999
SCHEME_DEBUG=true
SCHEME_SARVAM_API_KEY=env_file_key
SCHEME_SIMILARITY_THRESHOLD=0.8
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file = f.name
        
        try:
            # Mock the model_config to use our temporary env file
            with patch.dict(os.environ, {
                "SCHEME_HOST": "test.example.com",
                "SCHEME_PORT": "9999", 
                "SCHEME_DEBUG": "true",
                "SCHEME_SARVAM_API_KEY": "env_file_key",
                "SCHEME_SIMILARITY_THRESHOLD": "0.8"
            }):
                settings = Settings()
                
                assert settings.host == "test.example.com"
                assert settings.port == 9999
                assert settings.debug is True
                assert settings.sarvam_api_key == "env_file_key"
                assert settings.similarity_threshold == 0.8
                
        finally:
            os.unlink(env_file)
    
    def test_external_services_disabled_without_api_key(self):
        """Test that external services are properly disabled without API key."""
        settings = Settings(
            sarvam_api_key=None,
            enable_translation=True,
            enable_llm_responses=True
        )
        
        external_config = settings.get_external_service_config()
        
        # Services should be disabled even if enabled in config
        assert external_config["enable_translation"] is False
        assert external_config["enable_llm_responses"] is False
    
    def test_external_services_enabled_with_api_key(self):
        """Test that external services are enabled with API key."""
        settings = Settings(
            sarvam_api_key="valid_key",
            enable_translation=True,
            enable_llm_responses=True
        )
        
        external_config = settings.get_external_service_config()
        
        # Services should be enabled with valid API key
        assert external_config["enable_translation"] is True
        assert external_config["enable_llm_responses"] is True