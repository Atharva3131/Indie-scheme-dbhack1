# Project Structure

This document outlines the current project structure for the Government Scheme Copilot FastAPI application.

## Current Structure

```
├── main.py                     # FastAPI application entry point
├── config.py                   # Configuration management with Pydantic Settings
├── requirements.txt            # Python dependencies
├── start_server.py            # Development server startup script
├── test_basic.py              # Basic functionality tests
├── README.md                  # Project documentation
├── PROJECT_STRUCTURE.md       # This file
├── .env.example               # Environment variables template
├── venv/                      # Python virtual environment
├── services/                  # Business logic services (to be implemented)
│   └── __init__.py
├── models/                    # Pydantic data models (to be implemented)
│   └── __init__.py
├── data/                      # Mock data and utilities (to be implemented)
│   └── __init__.py
└── tests/                     # Test suite
    ├── __init__.py
    └── test_server_startup.py  # Server startup tests
```

## Implemented Components

### ✅ Core FastAPI Application (`main.py`)
- FastAPI server initialization with modern lifespan events
- CORS middleware configuration for frontend integration
- Health check endpoint at `/health`
- Root endpoint with API navigation information
- Auto-generated OpenAPI documentation at `/docs`

### ✅ Configuration Management (`config.py`)
- Pydantic Settings for environment-based configuration
- Support for .env file loading
- Configurable server settings (host, port, debug mode)
- External service configuration (Sarvam AI API key)
- Search and performance settings

### ✅ Development Tools
- `start_server.py` - Development server with auto-reload
- `test_basic.py` - Basic functionality verification
- Comprehensive test suite in `tests/` directory

### ✅ Documentation
- `README.md` with setup instructions
- `.env.example` with configuration template
- Auto-generated API documentation

## Next Steps (Upcoming Tasks)

### 🔄 Data Models (`models/`)
- UserProfile, SchemeModel, EligibilityModel
- API request/response models
- Error response models

### 🔄 Services (`services/`)
- KnowledgeBaseService - In-memory scheme data management
- EligibilityService - User profile matching logic
- SearchService - Semantic search functionality
- ResponseService - Multilingual response formatting

### 🔄 Mock Data (`data/`)
- schemes.json with 30+ government schemes
- Pre-computed embeddings for semantic search
- Data loading utilities

### 🔄 API Endpoints
- POST /api/eligibility - Eligibility checking
- POST /api/search - Semantic search
- GET /api/schemes - Browse all schemes
- POST /api/format - Response formatting

## Requirements Satisfied

✅ **Requirement 1.1**: FastAPI_Server SHALL initialize with all required dependencies  
✅ **Requirement 1.2**: FastAPI_Server SHALL serve on configurable host and port  
✅ **Requirement 1.3**: FastAPI_Server SHALL include CORS middleware for frontend integration  
✅ **Requirement 1.4**: FastAPI_Server SHALL provide health check endpoint  
✅ **Requirement 1.5**: FastAPI_Server SHALL handle graceful startup and shutdown  

## Testing Status

- ✅ Health endpoint functionality
- ✅ Root endpoint navigation
- ✅ CORS middleware configuration
- ✅ API documentation accessibility
- ✅ Startup/shutdown event handling
- ✅ Configuration loading
- ✅ Modern FastAPI patterns (lifespan events, timezone-aware datetime)

## Development Commands

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix/macOS

# Start development server
python start_server.py

# Run tests
python test_basic.py
python -m pytest tests/ -v

# Install dependencies
pip install -r requirements.txt
```