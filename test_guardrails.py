"""
Basic tests for FastAPI Guardrails Service

Run with: python -m pytest test_guardrails.py -v
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi_guardrails import app

# Create test client
client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["service"] == "FastAPI Guardrails Service"

def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/v1/guardrails/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "models_loaded" in data

def test_validate_text_success():
    """Test successful text validation."""
    response = client.post(
        "/v1/guardrails/validate",
        headers={"Authorization": "Bearer default-api-key-change-in-production"},
        json={
            "text": "This is a normal test message.",
            "guardrail_name": "default"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "valid" in data
    assert "validations" in data

def test_validate_text_unauthorized():
    """Test validation without API key."""
    response = client.post(
        "/v1/guardrails/validate",
        json={
            "text": "This is a test message.",
            "guardrail_name": "default"
        }
    )
    assert response.status_code == 401

def test_validate_text_invalid_key():
    """Test validation with invalid API key."""
    response = client.post(
        "/v1/guardrails/validate",
        headers={"Authorization": "Bearer invalid-key"},
        json={
            "text": "This is a test message.",
            "guardrail_name": "default"
        }
    )
    assert response.status_code == 401

def test_validate_text_empty():
    """Test validation with empty text."""
    response = client.post(
        "/v1/guardrails/validate",
        headers={"Authorization": "Bearer default-api-key-change-in-production"},
        json={
            "text": "",
            "guardrail_name": "default"
        }
    )
    assert response.status_code == 422  # Validation error

def test_validate_text_too_long():
    """Test validation with text exceeding max length."""
    long_text = "This is a very long text. " * 1000  # Exceeds default max length
    response = client.post(
        "/v1/guardrails/validate",
        headers={"Authorization": "Bearer default-api-key-change-in-production"},
        json={
            "text": long_text,
            "guardrail_name": "default"
        }
    )
    assert response.status_code == 422  # Validation error

def test_configs_endpoint():
    """Test configs endpoint."""
    response = client.get(
        "/v1/guardrails/configs",
        headers={"Authorization": "Bearer default-api-key-change-in-production"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "guardrails" in data
    assert "available_models" in data

def test_configs_unauthorized():
    """Test configs endpoint without API key."""
    response = client.get("/v1/guardrails/configs")
    assert response.status_code == 401

def test_different_guardrails():
    """Test different guardrail configurations."""
    guardrails = ["default", "strict", "permissive", "content_moderation"]
    
    for guardrail in guardrails:
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer default-api-key-change-in-production"},
            json={
                "text": "This is a test message.",
                "guardrail_name": guardrail
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

def test_validation_context():
    """Test validation with context."""
    response = client.post(
        "/v1/guardrails/validate",
        headers={"Authorization": "Bearer default-api-key-change-in-production"},
        json={
            "text": "This is a test message.",
            "guardrail_name": "default",
            "context": {
                "user_id": "test-user",
                "session_id": "test-session",
                "metadata": {"test": True}
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

# Async tests (if needed)
@pytest.mark.asyncio
async def test_async_validation():
    """Test async validation function directly."""
    from fastapi_guardrails import validate_text_with_guardrails
    
    result = await validate_text_with_guardrails(
        text="This is a test message.",
        guardrail_name="default"
    )
    
    assert result.status == "success"
    assert "valid" in result.__dict__
    assert "validations" in result.__dict__

if __name__ == "__main__":
    # Run tests directly
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
