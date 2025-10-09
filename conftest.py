"""
Pytest configuration and fixtures for FastAPI Guardrails Service
"""

import pytest
import asyncio
import httpx
import redis
import aioredis
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import os
import tempfile
import shutil
from typing import AsyncGenerator, Generator

# Set test environment variables
os.environ.update({
    "GUARDRAILS_API_KEY": "test-api-key",
    "REDIS_URL": "redis://localhost:6379/1",  # Use different DB for tests
    "DEBUG": "True",
    "LOG_LEVEL": "DEBUG",
    "CACHE_DEFAULT_TTL": "60"
})

from enhanced_guardrails import app, model_manager, cache_manager

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def redis_client():
    """Create a Redis client for testing."""
    client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    # Clear test database
    client.flushdb()
    yield client
    # Clean up after tests
    client.flushdb()
    client.close()

@pytest.fixture
async def async_redis():
    """Create an async Redis client for testing."""
    redis_client = aioredis.from_url("redis://localhost:6379/1")
    # Clear test database
    await redis_client.flushdb()
    yield redis_client
    # Clean up after tests
    await redis_client.flushdb()
    await redis_client.close()

@pytest.fixture
def mock_models():
    """Mock NLP models for testing."""
    # Mock spaCy model
    mock_spacy = MagicMock()
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_spacy.return_value = mock_doc
    
    # Mock HuggingFace pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [{"label": "NON_TOXIC", "score": 0.1}]
    
    # Replace models in model_manager
    model_manager.models["spacy_test"] = mock_spacy
    model_manager.pipelines["toxicity_test"] = mock_pipeline
    
    yield {
        "spacy": mock_spacy,
        "pipeline": mock_pipeline
    }
    
    # Clean up
    model_manager.models.clear()
    model_manager.pipelines.clear()

@pytest.fixture
def sample_texts():
    """Sample texts for testing different scenarios."""
    return {
        "normal": "This is a normal test message.",
        "toxic": "You are such a stupid idiot!",
        "long": "This is a very long text. " * 100,
        "pii": "My name is John Smith and my email is john@example.com.",
        "negative": "This is absolutely terrible and I hate everything about it.",
        "empty": "",
        "whitespace": "   \n\t   "
    }

@pytest.fixture
def sample_requests():
    """Sample validation requests for testing."""
    return {
        "basic": {
            "text": "This is a test message",
            "guardrail_name": "default"
        },
        "with_context": {
            "text": "This is a test message",
            "guardrail_name": "default",
            "context": {
                "user_id": "test-user",
                "session_id": "test-session"
            }
        },
        "batch": {
            "texts": [
                "This is test message 1",
                "This is test message 2",
                "This is test message 3"
            ],
            "guardrail_name": "default"
        }
    }

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Setup test environment before each test."""
    # Initialize cache manager for tests
    await cache_manager.connect()
    yield
    # Cleanup after each test
    if cache_manager.redis:
        await cache_manager.redis.close()

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add slow marker to tests that take longer
        if "load_test" in item.name or "stress_test" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Add integration marker to tests that test multiple components
        if "integration" in item.name or "e2e" in item.name:
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance tests
        if "performance" in item.name or "benchmark" in item.name:
            item.add_marker(pytest.mark.performance)
        
        # Add redis marker to tests that use Redis
        if "cache" in item.name or "redis" in item.name:
            item.add_marker(pytest.mark.redis)
