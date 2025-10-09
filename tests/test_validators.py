"""
Test suite for validation logic
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from enhanced_guardrails import (
    validate_length,
    validate_toxicity,
    validate_sentiment,
    validate_pii,
    validate_text_with_guardrails
)

class TestValidators:
    """Test individual validator functions."""
    
    @pytest.mark.asyncio
    async def test_validate_length_pass(self):
        """Test length validation passes for valid text."""
        result = await validate_length("Short text", 100)
        assert result.status == "pass"
        assert result.validator_name == "length_check"
        assert "within acceptable limits" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_length_fail(self):
        """Test length validation fails for long text."""
        long_text = "This is a very long text. " * 50
        result = await validate_length(long_text, 100)
        assert result.status == "fail"
        assert result.validator_name == "length_check"
        assert "exceeds maximum" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_toxicity_pass(self, mock_models):
        """Test toxicity validation passes for clean text."""
        with patch('enhanced_guardrails.model_manager.get_pipeline') as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.return_value = [{"label": "NON_TOXIC", "score": 0.1}]
            mock_get_pipeline.return_value = mock_pipeline
            
            result = await validate_toxicity("This is a clean message", 0.7)
            assert result.status == "pass"
            assert result.validator_name == "toxicity_check"
            assert "No toxicity detected" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_toxicity_fail(self, mock_models):
        """Test toxicity validation fails for toxic text."""
        with patch('enhanced_guardrails.model_manager.get_pipeline') as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.return_value = [{"label": "TOXIC", "score": 0.9}]
            mock_get_pipeline.return_value = mock_pipeline
            
            result = await validate_toxicity("You are stupid!", 0.7)
            assert result.status == "fail"
            assert result.validator_name == "toxicity_check"
            assert "Toxicity detected" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_sentiment_pass(self, mock_models):
        """Test sentiment validation passes for positive text."""
        with patch('enhanced_guardrails.model_manager.get_pipeline') as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.return_value = [{"label": "POSITIVE", "score": 0.9}]
            mock_get_pipeline.return_value = mock_pipeline
            
            result = await validate_sentiment("This is great!", -0.5)
            assert result.status == "pass"
            assert result.validator_name == "sentiment_check"
            assert "acceptable" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_sentiment_fail(self, mock_models):
        """Test sentiment validation fails for negative text."""
        with patch('enhanced_guardrails.model_manager.get_pipeline') as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.9}]
            mock_get_pipeline.return_value = mock_pipeline
            
            result = await validate_sentiment("This is terrible!", -0.5)
            assert result.status == "fail"
            assert result.validator_name == "sentiment_check"
            assert "Negative sentiment" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_pii_pass(self, mock_models):
        """Test PII validation passes for text without PII."""
        with patch('enhanced_guardrails.model_manager.get_model') as mock_get_model:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            mock_doc.ents = []  # No entities
            mock_nlp.return_value = mock_doc
            mock_get_model.return_value = mock_nlp
            
            result = await validate_pii("This is a normal message")
            assert result.status == "pass"
            assert result.validator_name == "pii_detection"
            assert "No PII detected" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_pii_fail(self, mock_models):
        """Test PII validation fails for text with PII."""
        with patch('enhanced_guardrails.model_manager.get_model') as mock_get_model:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            
            # Mock entity with PII
            mock_entity = MagicMock()
            mock_entity.label_ = "PERSON"
            mock_entity.text = "John Smith"
            mock_doc.ents = [mock_entity]
            mock_nlp.return_value = mock_doc
            mock_get_model.return_value = mock_nlp
            
            result = await validate_pii("My name is John Smith")
            assert result.status == "fail"
            assert result.validator_name == "pii_detection"
            assert "PII detected" in result.message
            assert "redacted_text" in result.metadata
    
    @pytest.mark.asyncio
    async def test_validate_text_with_guardrails_success(self, mock_models):
        """Test complete validation pipeline succeeds."""
        with patch('enhanced_guardrails.model_manager.get_model'), \
             patch('enhanced_guardrails.model_manager.get_pipeline'):
            
            result = await validate_text_with_guardrails(
                text="This is a clean test message",
                guardrail_name="default"
            )
            
            assert result.status == "success"
            assert result.valid is True
            assert len(result.validations) > 0
            assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_validate_text_with_guardrails_failure(self, mock_models):
        """Test complete validation pipeline fails for invalid content."""
        with patch('enhanced_guardrails.model_manager.get_model'), \
             patch('enhanced_guardrails.model_manager.get_pipeline') as mock_get_pipeline:
            
            # Mock toxic content
            mock_pipeline = MagicMock()
            mock_pipeline.return_value = [{"label": "TOXIC", "score": 0.9}]
            mock_get_pipeline.return_value = mock_pipeline
            
            result = await validate_text_with_guardrails(
                text="You are stupid!",
                guardrail_name="strict"
            )
            
            assert result.status == "success"  # Validation completed
            assert result.valid is False  # But content is invalid
            assert any(v.status == "fail" for v in result.validations)
    
    @pytest.mark.asyncio
    async def test_validation_with_caching(self, mock_models):
        """Test validation with caching enabled."""
        with patch('enhanced_guardrails.cache_manager.get') as mock_cache_get, \
             patch('enhanced_guardrails.cache_manager.set') as mock_cache_set, \
             patch('enhanced_guardrails.model_manager.get_model'), \
             patch('enhanced_guardrails.model_manager.get_pipeline'):
            
            # First call - cache miss
            mock_cache_get.return_value = None
            result1 = await validate_text_with_guardrails(
                text="Test message",
                guardrail_name="default",
                skip_cache=False
            )
            
            assert result1.cache_hit is False
            mock_cache_set.assert_called_once()
            
            # Second call - cache hit
            mock_cache_get.return_value = result1.dict()
            result2 = await validate_text_with_guardrails(
                text="Test message",
                guardrail_name="default",
                skip_cache=False
            )
            
            assert result2.cache_hit is True
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, mock_models):
        """Test validation error handling."""
        with patch('enhanced_guardrails.model_manager.get_model') as mock_get_model:
            # Mock model error
            mock_get_model.side_effect = Exception("Model loading failed")
            
            result = await validate_text_with_guardrails(
                text="Test message",
                guardrail_name="default"
            )
            
            assert result.status == "failure"
            assert "error" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_validation_execution_time(self, mock_models):
        """Test that execution time is recorded."""
        with patch('enhanced_guardrails.model_manager.get_model'), \
             patch('enhanced_guardrails.model_manager.get_pipeline'):
            
            result = await validate_text_with_guardrails(
                text="Test message",
                guardrail_name="default"
            )
            
            assert result.execution_time_ms > 0
            assert isinstance(result.execution_time_ms, float)
    
    @pytest.mark.asyncio
    async def test_validation_confidence_scores(self, mock_models):
        """Test that confidence scores are recorded."""
        with patch('enhanced_guardrails.model_manager.get_pipeline') as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.return_value = [{"label": "NON_TOXIC", "score": 0.8}]
            mock_get_pipeline.return_value = mock_pipeline
            
            result = await validate_toxicity("Test message", 0.7)
            
            assert result.confidence is not None
            assert 0.0 <= result.confidence <= 1.0
