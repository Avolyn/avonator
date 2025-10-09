"""
Integration tests for the complete system
"""

import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch

@pytest.mark.integration
class TestIntegration:
    """Integration tests that test the complete system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation(self, client: TestClient, sample_texts):
        """Test complete end-to-end validation flow."""
        # Test normal text
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": sample_texts["normal"],
                "guardrail_name": "default"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_batch_processing_integration(self, client: TestClient):
        """Test batch processing with real validation."""
        texts = [
            "This is a normal message",
            "This is another normal message",
            "This is a third normal message"
        ]
        
        response = client.post(
            "/v1/guardrails/validate/batch",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "texts": texts,
                "guardrail_name": "default"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_processed"] == 3
        assert len(data["results"]) == 3
    
    @pytest.mark.asyncio
    async def test_caching_integration(self, client: TestClient, redis_client):
        """Test caching integration with Redis."""
        # First request
        response1 = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": "This is a test message for caching",
                "guardrail_name": "default"
            }
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cache_hit"] is False
        
        # Second identical request
        response2 = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": "This is a test message for caching",
                "guardrail_name": "default"
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cache_hit"] is True
        assert data2["execution_time_ms"] < data1["execution_time_ms"]
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, client: TestClient):
        """Test health check with all components."""
        response = client.get("/v1/guardrails/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "models_loaded" in data
        assert "memory_usage" in data
        assert "cache_status" in data
        assert "uptime_seconds" in data
    
    @pytest.mark.asyncio
    async def test_metrics_integration(self, client: TestClient):
        """Test metrics collection integration."""
        # Make some requests to generate metrics
        for _ in range(5):
            client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": "Test message for metrics",
                    "guardrail_name": "default"
                }
            )
        
        # Check metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200
        metrics_text = response.text
        assert "guardrails_requests_total" in metrics_text
        assert "guardrails_request_duration_seconds" in metrics_text
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, client: TestClient):
        """Test rate limiting integration."""
        # Make many requests to trigger rate limiting
        responses = []
        for i in range(120):  # Exceed rate limit
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": f"Test message {i}",
                    "guardrail_name": "default"
                }
            )
            responses.append(response)
        
        # Check that some requests were rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        successful = [r for r in responses if r.status_code == 200]
        
        assert len(rate_limited) > 0
        assert len(successful) > 0
    
    @pytest.mark.asyncio
    async def test_different_guardrails_integration(self, client: TestClient):
        """Test different guardrail configurations integration."""
        test_text = "This is a test message"
        guardrails = ["default", "strict", "permissive", "content_moderation"]
        
        for guardrail in guardrails:
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": test_text,
                    "guardrail_name": guardrail
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "validations" in data
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, client: TestClient):
        """Test error recovery and graceful degradation."""
        # Test with malformed request
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={"invalid": "request"}
        )
        assert response.status_code == 422
        
        # Test with valid request after error
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": "Valid test message",
                "guardrail_name": "default"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, client: TestClient):
        """Test handling of concurrent requests."""
        import asyncio
        
        async def make_request():
            async with httpx.AsyncClient() as ac:
                response = await ac.post(
                    "http://test/v1/guardrails/validate",
                    headers={"Authorization": "Bearer test-api-key"},
                    json={
                        "text": "Concurrent test message",
                        "guardrail_name": "default"
                    }
                )
                return response
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_memory_usage_integration(self, client: TestClient):
        """Test memory usage doesn't grow excessively."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests
        for i in range(100):
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": f"Memory test message {i}",
                    "guardrail_name": "default"
                }
            )
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self, client: TestClient):
        """Test configuration endpoint integration."""
        response = client.get(
            "/v1/guardrails/configs",
            headers={"Authorization": "Bearer test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "guardrails" in data
        assert "available_models" in data
        assert "cache_status" in data
        
        # Check that all expected guardrails are present
        expected_guardrails = ["default", "strict", "permissive", "content_moderation"]
        for guardrail in expected_guardrails:
            assert guardrail in data["guardrails"]
