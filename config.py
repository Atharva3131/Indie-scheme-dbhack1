"""
Configuration management for Government Scheme Copilot.

This module provides environment-based configuration using Pydantic Settings
with comprehensive validation and support for .env file loading.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import logging

logger = logging.getLogger(__name__)

"""
Configuration management for Government Scheme Copilot.

This module provides environment-based configuration using Pydantic Settings
with comprehensive validation and support for .env file loading.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import logging

logger = logging.getLogger(__name__)

class LanguageCode(str, Enum):
    """Supported language codes."""
    ENGLISH = "english"
    HINDI = "hindi"

class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Settings(BaseSettings):
    """
    Application configuration settings with validation.
    
    All settings can be overridden via environment variables with SCHEME_ prefix.
    Example: SCHEME_HOST=localhost will set host to "localhost"
    """
    
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="SCHEME_",
        case_sensitive=False,
        validate_assignment=True
    )
    
    # Application Settings
    app_name: str = Field(default="Government Scheme Copilot", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    workers: int = Field(default=1, ge=1, le=10, description="Number of worker processes")
    
    # API Settings
    api_prefix: str = Field(default="/api", description="API route prefix")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    max_request_size: int = Field(default=1024*1024, ge=1024, description="Maximum request size in bytes")
    
    # External Services Configuration
    sarvam_api_key: Optional[str] = Field(default=None, description="Sarvam AI API key")
    sarvam_base_url: str = Field(default="https://api.sarvam.ai", description="Sarvam AI base URL")
    enable_translation: bool = Field(default=True, description="Enable translation services")
    enable_llm_responses: bool = Field(default=True, description="Enable LLM-generated responses")
    external_service_timeout: int = Field(default=10, ge=1, le=60, description="External service timeout in seconds")
    
    # Search Configuration
    similarity_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum similarity threshold for search results")
    max_search_results: int = Field(default=10, ge=1, le=50, description="Maximum number of search results")
    embedding_dimensions: int = Field(default=384, ge=100, le=2048, description="Embedding vector dimensions")
    enable_semantic_search: bool = Field(default=True, description="Enable semantic search functionality")
    
    # Language Settings
    default_language: LanguageCode = Field(default=LanguageCode.ENGLISH, description="Default response language")
    supported_languages: List[LanguageCode] = Field(
        default=[LanguageCode.ENGLISH, LanguageCode.HINDI], 
        description="List of supported languages"
    )
    
    # Performance Settings
    cache_size: int = Field(default=1000, ge=10, le=10000, description="Response cache size")
    cache_ttl: int = Field(default=3600, ge=60, le=86400, description="Cache TTL in seconds")
    request_timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    max_concurrent_requests: int = Field(default=100, ge=1, le=1000, description="Maximum concurrent requests")
    
    # Data Settings
    schemes_data_path: str = Field(default="data/schemes.json", description="Path to schemes data file")
    backup_data_path: Optional[str] = Field(default=None, description="Path to backup schemes data file")
    data_validation_enabled: bool = Field(default=True, description="Enable data validation on startup")
    
    # Security Settings
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_requests: int = Field(default=100, ge=1, le=10000, description="Rate limit requests per minute")
    enable_request_logging: bool = Field(default=True, description="Enable request logging")
    
    # Logging Settings
    enable_json_logging: bool = Field(default=False, description="Enable JSON formatted logging")
    log_file_path: Optional[str] = Field(default=None, description="Path to log file (optional)")
    max_log_file_size: int = Field(default=10*1024*1024, ge=1024*1024, description="Maximum log file size in bytes")
    log_backup_count: int = Field(default=5, ge=1, le=20, description="Number of log backup files to keep")
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins format."""
        if not v:
            return ["*"]
        
        for origin in v:
            if origin != "*" and not (origin.startswith("http://") or origin.startswith("https://")):
                logger.warning(f"CORS origin '{origin}' should start with http:// or https://")
        
        return v
    
    @field_validator('sarvam_api_key')
    @classmethod
    def validate_sarvam_api_key(cls, v, info):
        """Validate Sarvam API key when translation is enabled."""
        # Note: In Pydantic V2, we can't access other field values during validation
        # This validation will be done in validate_configuration method instead
        return v
    
    @field_validator('schemes_data_path')
    @classmethod
    def validate_schemes_data_path(cls, v):
        """Validate schemes data path exists."""
        if not os.path.exists(v):
            logger.warning(f"Schemes data file not found at: {v}")
        return v
    
    @field_validator('supported_languages')
    @classmethod
    def validate_supported_languages(cls, v, info):
        """Ensure default language is in supported languages."""
        # Note: In Pydantic V2, we can't access other field values during validation
        # This validation will be done in validate_configuration method instead
        return v
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the complete configuration and return validation results.
        
        Returns:
            Dict containing validation status and any warnings/errors
        """
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "configuration_summary": {}
        }
        
        # Check data file accessibility
        if not os.path.exists(self.schemes_data_path):
            validation_results["errors"].append(
                f"Schemes data file not found: {self.schemes_data_path}"
            )
            validation_results["valid"] = False
        
        # Check external service configuration
        if (self.enable_translation or self.enable_llm_responses) and not self.sarvam_api_key:
            validation_results["warnings"].append(
                "External services enabled but no API key provided - services will be disabled"
            )
        
        # Check performance settings
        if self.cache_size > 5000:
            validation_results["warnings"].append(
                f"Large cache size ({self.cache_size}) may consume significant memory"
            )
        
        # Check security settings
        if "*" in self.cors_origins and not self.debug:
            validation_results["warnings"].append(
                "CORS allows all origins - consider restricting for production"
            )
        
        # Ensure default language is in supported languages
        if self.default_language not in self.supported_languages:
            self.supported_languages.append(self.default_language)
            validation_results["warnings"].append(
                f"Added default language {self.default_language.value} to supported languages"
            )
        
        # Generate configuration summary
        validation_results["configuration_summary"] = {
            "server": f"{self.host}:{self.port}",
            "debug_mode": self.debug,
            "external_services": {
                "translation": self.enable_translation and bool(self.sarvam_api_key),
                "llm_responses": self.enable_llm_responses and bool(self.sarvam_api_key),
                "semantic_search": self.enable_semantic_search
            },
            "performance": {
                "cache_size": self.cache_size,
                "max_results": self.max_search_results,
                "similarity_threshold": self.similarity_threshold
            },
            "languages": [lang.value for lang in self.supported_languages],
            "data_source": self.schemes_data_path
        }
        
        return validation_results
    
    def get_external_service_config(self) -> Dict[str, Any]:
        """Get configuration for external services."""
        return {
            "sarvam_api_key": self.sarvam_api_key,
            "sarvam_base_url": self.sarvam_base_url,
            "enable_translation": self.enable_translation and bool(self.sarvam_api_key),
            "enable_llm_responses": self.enable_llm_responses and bool(self.sarvam_api_key),
            "timeout": self.external_service_timeout
        }
    
    def get_search_config(self) -> Dict[str, Any]:
        """Get configuration for search services."""
        return {
            "similarity_threshold": self.similarity_threshold,
            "max_results": self.max_search_results,
            "embedding_dimensions": self.embedding_dimensions,
            "enable_semantic_search": self.enable_semantic_search
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get configuration for performance settings."""
        return {
            "cache_size": self.cache_size,
            "cache_ttl": self.cache_ttl,
            "request_timeout": self.request_timeout,
            "max_concurrent_requests": self.max_concurrent_requests
        }

def create_settings() -> Settings:
    """
    Create and validate settings instance.
    
    Returns:
        Validated Settings instance
        
    Raises:
        ValueError: If configuration validation fails
    """
    try:
        settings = Settings()
        validation_results = settings.validate_configuration()
        
        if not validation_results["valid"]:
            error_msg = "Configuration validation failed:\n" + "\n".join(validation_results["errors"])
            raise ValueError(error_msg)
        
        # Log warnings
        for warning in validation_results["warnings"]:
            logger.warning(warning)
        
        # Log configuration summary
        logger.info("Configuration loaded successfully:")
        summary = validation_results["configuration_summary"]
        logger.info(f"  Server: {summary['server']}")
        logger.info(f"  Debug mode: {summary['debug_mode']}")
        logger.info(f"  External services: {summary['external_services']}")
        logger.info(f"  Languages: {summary['languages']}")
        
        return settings
        
    except Exception as e:
        logger.error(f"Failed to create settings: {e}")
        raise

# Global settings instance
settings = create_settings()