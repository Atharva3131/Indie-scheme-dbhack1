# Government Scheme Copilot API

A FastAPI-based REST API for discovering and checking eligibility for Indian government schemes. This application converts the original Databricks-based implementation into a standalone, deployable service.

## Features

- 🔍 Semantic search for government schemes
- ✅ Eligibility checking based on user profiles
- 🌐 Multilingual support (English/Hindi)
- 📊 30+ curated government schemes
- 🚀 Fast in-memory operations
- 📖 Auto-generated API documentation

## Quick Start

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Unix/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# Add your Sarvam AI API key if using translation features
```

### 4. Run the Server

```bash
# Development mode
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root Endpoint**: http://localhost:8000/

## Project Structure

```
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── services/              # Business logic services
├── models/                # Pydantic data models
├── data/                  # Mock data and utilities
└── tests/                 # Unit and property tests
```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /` - Root endpoint with API information
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

## Environment Variables

All configuration can be set via environment variables with the `SCHEME_` prefix:

- `SCHEME_HOST` - Server host (default: 0.0.0.0)
- `SCHEME_PORT` - Server port (default: 8000)
- `SCHEME_DEBUG` - Debug mode (default: false)
- `SCHEME_SARVAM_API_KEY` - Sarvam AI API key for translation

See `.env.example` for complete list of configuration options.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run property-based tests only
pytest -m property
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## License

This project is licensed under the MIT License.