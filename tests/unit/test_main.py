"""
Tests for the main FastAPI application.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "приложение" in data
    assert data["приложение"] == "Vera Platform"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["статус"] == "ok"
    assert data["сервис"] == "Vera API"


@pytest.mark.asyncio
async def test_secure_endpoint_unauthorized():
    """Test that secure endpoint requires authentication."""
    response = client.get("/api/secure")
    assert response.status_code == 403  # Should be 401 or 403 for unauthorized


# Add more test cases as needed
