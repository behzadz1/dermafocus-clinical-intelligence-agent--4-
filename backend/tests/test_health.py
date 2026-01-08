"""
Tests for Health Check Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "operational"


def test_health_check():
    """Test basic health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


def test_detailed_health_check():
    """Test detailed health check with dependencies"""
    response = client.get("/api/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "anthropic" in data["dependencies"]
    assert "pinecone" in data["dependencies"]
    assert "openai" in data["dependencies"]


def test_readiness_probe():
    """Test Kubernetes readiness probe"""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_liveness_probe():
    """Test Kubernetes liveness probe"""
    response = client.get("/api/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_api_documentation():
    """Test that API documentation is available (in debug mode)"""
    # This will only work when DEBUG=True
    response = client.get("/docs")
    # In production, this should return 404
    # In development, should return 200
    assert response.status_code in [200, 404]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
