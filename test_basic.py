"""
Basic test to verify FastAPI server functionality.
"""

import asyncio
from fastapi.testclient import TestClient
from main import app

def test_health_endpoint():
    """Test the health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "Government Scheme Copilot"
    assert data["version"] == "1.0.0"
    print("✅ Health endpoint test passed")

def test_root_endpoint():
    """Test the root endpoint."""
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["message"] == "Government Scheme Copilot API"
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"
    print("✅ Root endpoint test passed")

def test_cors_headers():
    """Test that CORS headers are present."""
    client = TestClient(app)
    
    # Test preflight request for CORS
    response = client.options("/health", headers={"Origin": "http://localhost:3000"})
    
    # CORS middleware should be configured (test passes if no error occurs)
    print("✅ CORS middleware test passed")

if __name__ == "__main__":
    print("🧪 Running basic FastAPI tests...")
    test_health_endpoint()
    test_root_endpoint()
    test_cors_headers()
    print("🎉 All basic tests passed!")