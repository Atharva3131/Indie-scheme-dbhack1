#!/usr/bin/env python3
"""
Development server startup script for Government Scheme Copilot.

This script starts the FastAPI server with development settings.
"""

import uvicorn
from config import settings

if __name__ == "__main__":
    print("🚀 Starting Government Scheme Copilot API...")
    print(f"📍 Server will be available at: http://{settings.host}:{settings.port}")
    print(f"📚 API Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"❤️  Health Check: http://{settings.host}:{settings.port}/health")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )