"""
Test suite for API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestAPIEndpoints:
    """Test API endpoint functionality."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns service information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "Enhanced FastAPI Guardrails Service"
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/v1/guardrails/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "models_loaded" in data
        assert "uptime_seconds" in data
    
    def test_metrics_endpoint(self, client: TestClient):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "guardrails_requests_total" in response.text
    
    def test_validate_text_success(self, client: TestClient, sample_requests):
        """Test successful text validation."""
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json=sample_requests["basic"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "valid" in data
        assert "validations" in data
        assert "execution_time_ms" in data
    
    def test_validate_text_unauthorized(self, client: TestClient, sample_requests):
        """Test validation without API key."""
        response = client.post(
            "/v1/guardrails/validate",
            json=sample_requests["basic"]
        )
        assert response.status_code == 401
    
    def test_validate_text_invalid_key(self, client: TestClient, sample_requests):
        """Test validation with invalid API key."""
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer invalid-key"},
            json=sample_requests["basic"]
        )
        assert response.status_code == 401
    
    def test_validate_text_empty(self, client: TestClient):
        """Test validation with empty text."""
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={"text": "", "guardrail_name": "default"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_validate_text_too_long(self, client: TestClient):
        """Test validation with text exceeding max length."""
        long_text = "This is a very long text. " * 10000  # Exceeds max length
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={"text": long_text, "guardrail_name": "default"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_validate_batch_success(self, client: TestClient, sample_requests):
        """Test successful batch validation."""
        response = client.post(
            "/v1/guardrails/validate/batch",
            headers={"Authorization": "Bearer test-api-key"},
            json=sample_requests["batch"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data
        assert "total_processed" in data
        assert "total_valid" in data
        assert len(data["results"]) == 3
    
    def test_validate_batch_unauthorized(self, client: TestClient, sample_requests):
        """Test batch validation without API key."""
        response = client.post(
            "/v1/guardrails/validate/batch",
            json=sample_requests["batch"]
        )
        assert response.status_code == 401
    
    def test_validate_batch_empty(self, client: TestClient):
        """Test batch validation with empty texts list."""
        response = client.post(
            "/v1/guardrails/validate/batch",
            headers={"Authorization": "Bearer test-api-key"},
            json={"texts": [], "guardrail_name": "default"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_validate_batch_too_many(self, client: TestClient):
        """Test batch validation with too many texts."""
        texts = [f"Text {i}" for i in range(101)]  # Exceeds max batch size
        response = client.post(
            "/v1/guardrails/validate/batch",
            headers={"Authorization": "Bearer test-api-key"},
            json={"texts": texts, "guardrail_name": "default"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_configs_endpoint(self, client: TestClient):
        """Test configs endpoint."""
        response = client.get(
            "/v1/guardrails/configs",
            headers={"Authorization": "Bearer test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "guardrails" in data
        assert "available_models" in data
    
    def test_configs_unauthorized(self, client: TestClient):
        """Test configs endpoint without API key."""
        response = client.get("/v1/guardrails/configs")
        assert response.status_code == 401
    
    def test_different_guardrails(self, client: TestClient, sample_requests):
        """Test different guardrail configurations."""
        guardrails = ["default", "strict", "permissive", "content_moderation"]
        
        for guardrail in guardrails:
            request_data = sample_requests["basic"].copy()
            request_data["guardrail_name"] = guardrail
            
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json=request_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_validation_with_context(self, client: TestClient, sample_requests):
        """Test validation with context information."""
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json=sample_requests["with_context"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "request_id" in data
    
    def test_validation_caching(self, client: TestClient, sample_requests):
        """Test that validation results are cached."""
        # First request
        response1 = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json=sample_requests["basic"]
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second identical request (should hit cache)
        response2 = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json=sample_requests["basic"]
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Cache hit should be faster
        assert data2["cache_hit"] is True
        assert data2["execution_time_ms"] < data1["execution_time_ms"]
    
    def test_validation_skip_cache(self, client: TestClient, sample_requests):
        """Test validation with cache skipping."""
        request_data = sample_requests["basic"].copy()
        request_data["skip_cache"] = True
        
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json=request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is False
    
    def test_rate_limiting(self, client: TestClient, sample_requests):
        """Test rate limiting functionality."""
        # Make many requests quickly to trigger rate limiting
        responses = []
        for _ in range(150):  # Exceed rate limit
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json=sample_requests["basic"]
            )
            responses.append(response)
        
        # Some requests should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/v1/guardrails/validate")
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_error_handling(self, client: TestClient):
        """Test error handling for malformed requests."""
        # Invalid JSON
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            data="invalid json"
        )
        assert response.status_code == 422
        
        # Missing required fields
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={"guardrail_name": "default"}
        )
        assert response.status_code == 422
