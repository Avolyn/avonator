"""
Performance and load tests
"""

import pytest
import asyncio
import time
import statistics
from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
import httpx

@pytest.mark.performance
class TestPerformance:
    """Performance and load tests."""
    
    def test_single_request_performance(self, client: TestClient):
        """Test performance of single validation request."""
        start_time = time.time()
        
        response = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": "This is a performance test message",
                "guardrail_name": "default"
            }
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code == 200
        assert duration < 2.0  # Should complete within 2 seconds
        
        data = response.json()
        assert data["execution_time_ms"] < 2000  # Internal execution time
    
    def test_batch_request_performance(self, client: TestClient):
        """Test performance of batch validation request."""
        texts = [f"Performance test message {i}" for i in range(10)]
        
        start_time = time.time()
        
        response = client.post(
            "/v1/guardrails/validate/batch",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "texts": texts,
                "guardrail_name": "default"
            }
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code == 200
        assert duration < 5.0  # Should complete within 5 seconds
        
        data = response.json()
        assert data["total_processed"] == 10
        assert data["execution_time_ms"] < 5000
    
    def test_concurrent_requests_performance(self, client: TestClient):
        """Test performance under concurrent load."""
        def make_request():
            return client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": "Concurrent performance test",
                    "guardrail_name": "default"
                }
            )
        
        # Test with 20 concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [future.result() for future in futures]
            end_time = time.time()
        
        duration = end_time - start_time
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Should handle 20 concurrent requests within reasonable time
        assert duration < 10.0
        
        # Check individual response times
        response_times = []
        for response in responses:
            data = response.json()
            response_times.append(data["execution_time_ms"])
        
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 1000  # Average response time under 1 second
    
    def test_memory_usage_under_load(self, client: TestClient):
        """Test memory usage under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make 50 requests
        for i in range(50):
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": f"Memory load test message {i}",
                    "guardrail_name": "default"
                }
            )
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 200 * 1024 * 1024  # Less than 200MB
    
    def test_cache_performance(self, client: TestClient):
        """Test cache performance impact."""
        test_text = "Cache performance test message"
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": test_text,
                "guardrail_name": "default"
            }
        )
        first_duration = time.time() - start_time
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = client.post(
            "/v1/guardrails/validate",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "text": test_text,
                "guardrail_name": "default"
            }
        )
        second_duration = time.time() - start_time
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["cache_hit"] is False
        assert data2["cache_hit"] is True
        
        # Cache hit should be significantly faster
        assert second_duration < first_duration * 0.5
    
    @pytest.mark.slow
    def test_sustained_load_performance(self, client: TestClient):
        """Test performance under sustained load."""
        def make_request():
            return client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": "Sustained load test message",
                    "guardrail_name": "default"
                }
            )
        
        # Run 100 requests over time
        start_time = time.time()
        response_times = []
        
        for i in range(100):
            request_start = time.time()
            response = make_request()
            request_duration = time.time() - request_start
            
            assert response.status_code == 200
            response_times.append(request_duration)
            
            # Small delay between requests
            time.sleep(0.01)
        
        total_duration = time.time() - start_time
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        
        # Performance assertions
        assert avg_response_time < 1.0  # Average under 1 second
        assert p95_response_time < 2.0  # 95th percentile under 2 seconds
        assert p99_response_time < 3.0  # 99th percentile under 3 seconds
        
        # Throughput should be reasonable
        throughput = 100 / total_duration
        assert throughput > 10  # At least 10 requests per second
    
    def test_different_text_lengths_performance(self, client: TestClient):
        """Test performance with different text lengths."""
        text_lengths = [10, 100, 1000, 5000]
        response_times = []
        
        for length in text_lengths:
            text = "A" * length
            
            start_time = time.time()
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": text,
                    "guardrail_name": "default"
                }
            )
            duration = time.time() - start_time
            
            assert response.status_code == 200
            response_times.append(duration)
        
        # Response time should scale reasonably with text length
        # Longer texts should take longer, but not exponentially
        for i in range(1, len(text_lengths)):
            time_ratio = response_times[i] / response_times[i-1]
            length_ratio = text_lengths[i] / text_lengths[i-1]
            
            # Time increase should be less than text length increase
            assert time_ratio < length_ratio
    
    def test_guardrail_performance_comparison(self, client: TestClient):
        """Test performance across different guardrail configurations."""
        test_text = "Performance comparison test message"
        guardrails = ["default", "strict", "permissive", "content_moderation"]
        response_times = {}
        
        for guardrail in guardrails:
            start_time = time.time()
            response = client.post(
                "/v1/guardrails/validate",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "text": test_text,
                    "guardrail_name": guardrail
                }
            )
            duration = time.time() - start_time
            
            assert response.status_code == 200
            response_times[guardrail] = duration
        
        # All guardrails should perform within reasonable time
        for guardrail, duration in response_times.items():
            assert duration < 2.0, f"Guardrail {guardrail} took too long: {duration}s"
    
    @pytest.mark.asyncio
    async def test_async_performance(self, client: TestClient):
        """Test async performance with httpx."""
        async def make_async_request():
            async with httpx.AsyncClient() as ac:
                response = await ac.post(
                    "http://test/v1/guardrails/validate",
                    headers={"Authorization": "Bearer test-api-key"},
                    json={
                        "text": "Async performance test",
                        "guardrail_name": "default"
                    }
                )
                return response
        
        # Test 20 async requests
        start_time = time.time()
        tasks = [make_async_request() for _ in range(20)]
        responses = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Async requests should be fast
        assert duration < 5.0
        
        # Check individual response times
        response_times = []
        for response in responses:
            data = response.json()
            response_times.append(data["execution_time_ms"])
        
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 1000  # Average under 1 second
