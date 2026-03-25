"""
FastAPI application for Government Scheme Copilot.

This module initializes the FastAPI server with CORS middleware,
health check endpoint, and configuration management.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import uvicorn
import logging
import sys
from config import settings
from api.endpoints import router as api_router
from models.errors import ErrorResponse, ErrorCode
from utils.error_handlers import setup_error_handlers
from utils.logging_config import initialize_logging
from utils.timeout_handler import configure_timeouts

# Initialize logging and error handling
initialize_logging()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.value),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Configure timeouts
configure_timeouts(
    default_timeout=settings.request_timeout,
    external_service_timeout=settings.external_service_timeout,
    database_timeout=10.0,
    cache_timeout=5.0
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events with configuration validation."""
    # Startup
    logger.info("🚀 Government Scheme Copilot API starting up...")
    
    try:
        # Validate configuration on startup
        logger.info("🔧 Validating configuration...")
        validation_results = settings.validate_configuration()
        
        if not validation_results["valid"]:
            logger.error("❌ Configuration validation failed:")
            for error in validation_results["errors"]:
                logger.error(f"  - {error}")
            raise RuntimeError("Invalid configuration - server cannot start")
        
        # Log warnings if any
        if validation_results["warnings"]:
            logger.warning("⚠️  Configuration warnings:")
            for warning in validation_results["warnings"]:
                logger.warning(f"  - {warning}")
        
        # Log configuration summary
        summary = validation_results["configuration_summary"]
        logger.info("✅ Configuration validated successfully:")
        logger.info(f"  📡 Server: {summary['server']}")
        logger.info(f"  🐛 Debug mode: {summary['debug_mode']}")
        logger.info(f"  🌐 External services: {summary['external_services']}")
        logger.info(f"  🗣️  Languages: {summary['languages']}")
        logger.info(f"  📊 Data source: {summary['data_source']}")
        
        logger.info("📊 Initializing services...")
        from api.endpoints import knowledge_base, search_service, response_service
        
        # Log scheme availability
        schemes_count = knowledge_base.get_scheme_count()
        logger.info(f"✅ Loaded {schemes_count} schemes into knowledge base")
        
        # Verify vectorizer is initialized
        if hasattr(search_service.embedding_service, 'fitted') and search_service.embedding_service.fitted:
            logger.info("✅ Semantic search embeddings initialized")
            
        logger.info("🎉 Startup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Government Scheme Copilot API shutting down...")
    logger.info("💾 Cleaning up resources...")
    try:
        from api.endpoints import search_service, response_service, knowledge_base
        if hasattr(search_service, '_executor'):
            search_service._executor.shutdown(wait=True)
        if hasattr(knowledge_base, '_executor'):
            knowledge_base._executor.shutdown(wait=True)
        if hasattr(response_service, '_cleanup_task') and response_service._cleanup_task:
            response_service._cleanup_task.cancel()
    except Exception as e:
        logger.error(f"⚠️ Error during cleanup: {e}")
        
    logger.info("👋 Shutdown completed")

# Initialize FastAPI application with configuration
app = FastAPI(
    title=settings.app_name,
    description="API for discovering and checking eligibility for Indian government schemes",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.debug
)

# CORS middleware configuration from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Set up comprehensive error handling
setup_error_handlers(app, enable_debug=settings.debug)

# Health check and configuration endpoints remain the same

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify server status and configuration.
    
    Returns:
        dict: Health status with timestamp and configuration info
    """
    try:
        # Perform basic configuration validation
        validation_results = settings.validate_configuration()
        
        health_status = {
            "status": "healthy" if validation_results["valid"] else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "service": settings.app_name,
            "version": settings.app_version,
            "configuration": {
                "valid": validation_results["valid"],
                "external_services": validation_results["configuration_summary"]["external_services"],
                "languages_supported": validation_results["configuration_summary"]["languages"]
            }
        }
        
        # Add warnings if any
        if validation_results["warnings"]:
            health_status["warnings"] = validation_results["warnings"]
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "service": settings.app_name,
                "error": "Configuration validation failed"
            }
        )

from fastapi.staticfiles import StaticFiles

# Mount the frontend directory to serve the React UI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/config")
async def get_config_info():
    """
    Get public configuration information (non-sensitive).
    
    Returns:
        dict: Public configuration settings
    """
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "api_prefix": settings.api_prefix,
        "features": {
            "semantic_search": settings.enable_semantic_search,
            "translation": settings.enable_translation and bool(settings.sarvam_api_key),
            "llm_responses": settings.enable_llm_responses and bool(settings.sarvam_api_key),
            "rate_limiting": settings.enable_rate_limiting
        },
        "search_settings": {
            "max_results": settings.max_search_results,
            "similarity_threshold": settings.similarity_threshold,
            "embedding_dimensions": settings.embedding_dimensions
        },
        "language_settings": {
            "default": settings.default_language.value,
            "supported": [lang.value for lang in settings.supported_languages]
        },
        "performance": {
            "cache_size": settings.cache_size,
            "request_timeout": settings.request_timeout,
            "max_concurrent_requests": settings.max_concurrent_requests
        }
    }

if __name__ == "__main__":
    try:
        logger.info(f"🌐 Starting server on {settings.host}:{settings.port}")
        logger.info(f"🔧 Debug mode: {settings.debug}")
        logger.info(f"🔄 Auto-reload: {settings.reload}")
        
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            workers=settings.workers if not settings.reload else 1,
            log_level=settings.log_level.value.lower(),
            access_log=settings.enable_request_logging
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)