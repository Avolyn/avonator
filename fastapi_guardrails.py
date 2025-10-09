"""
FastAPI-based Guardrails Service with NLP Models

A streamlined guardrail service built on FastAPI with NLP-based content validation
using spaCy, Stanza, and HuggingFace transformers instead of regex patterns.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
import logging
import time
import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path

# NLP and ML imports
import spacy
import stanza
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Global variables for models
nlp_models = {}
huggingface_pipelines = {}

class ValidationContext(BaseModel):
    """Context information for validation requests."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ValidationRequest(BaseModel):
    """Request model for text validation."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to validate")
    context: Optional[ValidationContext] = None
    guardrail_name: Optional[str] = "default"
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()

class ValidatorResult(BaseModel):
    """Result of a single validator."""
    validator_name: str
    status: str = Field(..., regex="^(pass|fail)$")
    message: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    on_fail_action: str = Field(..., regex="^(exception|filter|reask|log)$")
    metadata: Optional[Dict[str, Any]] = None

class ValidationResponse(BaseModel):
    """Response model for validation results."""
    status: str = Field(..., regex="^(success|failure)$")
    message: str
    valid: bool
    validations: List[ValidatorResult]
    processed_text: Optional[str] = None
    execution_time_ms: Optional[float] = None
    model_info: Optional[Dict[str, str]] = None

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    models_loaded: Dict[str, bool]
    uptime_seconds: float

class ConfigResponse(BaseModel):
    """Configuration response model."""
    status: str
    guardrails: Dict[str, Dict[str, Any]]
    available_models: List[str]

# Configuration
class Settings:
    """Application settings."""
    API_KEY: str = os.getenv("GUARDRAILS_API_KEY", "default-api-key-change-in-production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    MAX_TEXT_LENGTH: int = int(os.getenv("MAX_TEXT_LENGTH", "10000"))
    ENABLE_CORS: bool = os.getenv("ENABLE_CORS", "True").lower() == "true"
    ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "*").split(",")
    
    # NLP Model settings
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
    STANZA_MODEL: str = os.getenv("STANZA_MODEL", "en")
    HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "unitary/toxic-bert")
    
    # Guardrail configurations
    GUARDRAIL_CONFIGS = {
        "default": {
            "description": "Default guardrail with basic NLP validation",
            "validators": [
                {"name": "length_check", "max_length": 1000, "on_fail": "exception"},
                {"name": "toxicity_check", "threshold": 0.7, "on_fail": "exception"},
                {"name": "sentiment_check", "threshold": -0.5, "on_fail": "log"}
            ]
        },
        "strict": {
            "description": "Strict content moderation",
            "validators": [
                {"name": "length_check", "max_length": 500, "on_fail": "exception"},
                {"name": "toxicity_check", "threshold": 0.3, "on_fail": "exception"},
                {"name": "sentiment_check", "threshold": -0.3, "on_fail": "exception"},
                {"name": "pii_detection", "on_fail": "filter"}
            ]
        },
        "permissive": {
            "description": "Permissive content validation",
            "validators": [
                {"name": "length_check", "max_length": 2000, "on_fail": "log"},
                {"name": "toxicity_check", "threshold": 0.9, "on_fail": "log"}
            ]
        }
    }

settings = Settings()

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting FastAPI Guardrails Service...")
    await load_nlp_models()
    logger.info("All models loaded successfully")
    yield
    # Shutdown
    logger.info("Shutting down FastAPI Guardrails Service...")

# Create FastAPI app
app = FastAPI(
    title="FastAPI Guardrails Service",
    description="NLP-based content validation and guardrails",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Dependency for API key validation
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header."""
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials

# NLP Model Loading Functions
async def load_nlp_models():
    """Load all required NLP models."""
    try:
        # Load spaCy model
        logger.info(f"Loading spaCy model: {settings.SPACY_MODEL}")
        nlp_models['spacy'] = spacy.load(settings.SPACY_MODEL)
        logger.info("spaCy model loaded successfully")
        
        # Load Stanza model
        logger.info(f"Loading Stanza model: {settings.STANZA_MODEL}")
        stanza.download(settings.STANZA_MODEL)
        nlp_models['stanza'] = stanza.Pipeline(settings.STANZA_MODEL, processors='tokenize,pos,lemma,depparse,sentiment')
        logger.info("Stanza model loaded successfully")
        
        # Load HuggingFace model
        logger.info(f"Loading HuggingFace model: {settings.HUGGINGFACE_MODEL}")
        huggingface_pipelines['toxicity'] = pipeline(
            "text-classification",
            model=settings.HUGGINGFACE_MODEL,
            return_all_scores=True
        )
        logger.info("HuggingFace toxicity model loaded successfully")
        
        # Load sentiment analysis pipeline
        huggingface_pipelines['sentiment'] = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            return_all_scores=True
        )
        logger.info("HuggingFace sentiment model loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading NLP models: {str(e)}")
        raise

# Validation Functions
async def validate_length(text: str, max_length: int) -> ValidatorResult:
    """Validate text length."""
    if len(text) > max_length:
        return ValidatorResult(
            validator_name="length_check",
            status="fail",
            message=f"Text length ({len(text)}) exceeds maximum allowed ({max_length})",
            on_fail_action="exception"
        )
    return ValidatorResult(
        validator_name="length_check",
        status="pass",
        message="Text length is within acceptable limits",
        on_fail_action="exception"
    )

async def validate_toxicity(text: str, threshold: float) -> ValidatorResult:
    """Validate text toxicity using HuggingFace model."""
    try:
        results = huggingface_pipelines['toxicity'](text)
        # Get the highest toxicity score
        max_toxicity = max(score['score'] for score in results[0] if 'TOXIC' in score['label'].upper())
        
        if max_toxicity > threshold:
            return ValidatorResult(
                validator_name="toxicity_check",
                status="fail",
                message=f"Toxicity detected (confidence: {max_toxicity:.3f})",
                confidence=max_toxicity,
                on_fail_action="exception"
            )
        return ValidatorResult(
            validator_name="toxicity_check",
            status="pass",
            message="No toxicity detected",
            confidence=1.0 - max_toxicity,
            on_fail_action="exception"
        )
    except Exception as e:
        logger.error(f"Error in toxicity validation: {str(e)}")
        return ValidatorResult(
            validator_name="toxicity_check",
            status="fail",
            message=f"Toxicity validation error: {str(e)}",
            on_fail_action="exception"
        )

async def validate_sentiment(text: str, threshold: float) -> ValidatorResult:
    """Validate text sentiment using HuggingFace model."""
    try:
        results = huggingface_pipelines['sentiment'](text)
        # Get sentiment score (negative sentiment has negative values)
        sentiment_score = results[0]['score'] if results[0]['label'] == 'NEGATIVE' else -results[0]['score']
        
        if sentiment_score < threshold:
            return ValidatorResult(
                validator_name="sentiment_check",
                status="fail",
                message=f"Negative sentiment detected (score: {sentiment_score:.3f})",
                confidence=abs(sentiment_score),
                on_fail_action="log"
            )
        return ValidatorResult(
            validator_name="sentiment_check",
            status="pass",
            message="Sentiment is acceptable",
            confidence=abs(sentiment_score),
            on_fail_action="log"
        )
    except Exception as e:
        logger.error(f"Error in sentiment validation: {str(e)}")
        return ValidatorResult(
            validator_name="sentiment_check",
            status="fail",
            message=f"Sentiment validation error: {str(e)}",
            on_fail_action="log"
        )

async def validate_pii(text: str) -> ValidatorResult:
    """Validate and redact PII using spaCy NER."""
    try:
        doc = nlp_models['spacy'](text)
        pii_entities = []
        redacted_text = text
        
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'EMAIL', 'PHONE']:
                pii_entities.append(f"{ent.label_}: {ent.text}")
                redacted_text = redacted_text.replace(ent.text, f"[{ent.label_}_REDACTED]")
        
        if pii_entities:
            return ValidatorResult(
                validator_name="pii_detection",
                status="fail",
                message=f"PII detected: {', '.join(pii_entities)}",
                on_fail_action="filter",
                metadata={"redacted_text": redacted_text, "entities": pii_entities}
            )
        return ValidatorResult(
            validator_name="pii_detection",
            status="pass",
            message="No PII detected",
            on_fail_action="filter"
        )
    except Exception as e:
        logger.error(f"Error in PII validation: {str(e)}")
        return ValidatorResult(
            validator_name="pii_detection",
            status="fail",
            message=f"PII validation error: {str(e)}",
            on_fail_action="filter"
        )

# Main validation function
async def validate_text_with_guardrails(text: str, guardrail_name: str, context: Optional[ValidationContext] = None) -> ValidationResponse:
    """Main validation function using NLP models."""
    start_time = time.time()
    
    try:
        config = settings.GUARDRAIL_CONFIGS.get(guardrail_name, settings.GUARDRAIL_CONFIGS["default"])
        validations = []
        all_passed = True
        processed_text = text
        
        for validator_config in config["validators"]:
            validator_name = validator_config["name"]
            on_fail_action = validator_config["on_fail"]
            
            if validator_name == "length_check":
                max_length = validator_config.get("max_length", 1000)
                result = await validate_length(text, max_length)
                result.on_fail_action = on_fail_action
                validations.append(result)
                if result.status == "fail":
                    all_passed = False
                    
            elif validator_name == "toxicity_check":
                threshold = validator_config.get("threshold", 0.7)
                result = await validate_toxicity(text, threshold)
                result.on_fail_action = on_fail_action
                validations.append(result)
                if result.status == "fail":
                    all_passed = False
                    
            elif validator_name == "sentiment_check":
                threshold = validator_config.get("threshold", -0.5)
                result = await validate_sentiment(text, threshold)
                result.on_fail_action = on_fail_action
                validations.append(result)
                if result.status == "fail":
                    all_passed = False
                    
            elif validator_name == "pii_detection":
                result = await validate_pii(text)
                result.on_fail_action = on_fail_action
                validations.append(result)
                if result.status == "fail":
                    all_passed = False
                    if result.metadata and "redacted_text" in result.metadata:
                        processed_text = result.metadata["redacted_text"]
        
        execution_time = (time.time() - start_time) * 1000
        
        return ValidationResponse(
            status="success",
            message="Validation completed successfully",
            valid=all_passed,
            validations=validations,
            processed_text=processed_text if processed_text != text else None,
            execution_time_ms=execution_time,
            model_info={
                "spacy_model": settings.SPACY_MODEL,
                "stanza_model": settings.STANZA_MODEL,
                "huggingface_model": settings.HUGGINGFACE_MODEL
            }
        )
        
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return ValidationResponse(
            status="failure",
            message=f"Internal error during validation: {str(e)}",
            valid=False,
            validations=[],
            execution_time_ms=(time.time() - start_time) * 1000
        )

# API Endpoints
@app.post("/v1/guardrails/validate", response_model=ValidationResponse)
async def validate_text(
    request: ValidationRequest,
    api_key: str = Depends(verify_api_key)
):
    """Validate text using configured guardrails and NLP models."""
    try:
        result = await validate_text_with_guardrails(
            text=request.text,
            guardrail_name=request.guardrail_name,
            context=request.context
        )
        return result
    except Exception as e:
        logger.error(f"Unexpected error in validate_text endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/v1/guardrails/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    models_loaded = {
        "spacy": "spacy" in nlp_models,
        "stanza": "stanza" in nlp_models,
        "toxicity": "toxicity" in huggingface_pipelines,
        "sentiment": "sentiment" in huggingface_pipelines
    }
    
    return HealthResponse(
        status="healthy",
        service="fastapi-guardrails",
        version="1.0.0",
        models_loaded=models_loaded,
        uptime_seconds=uptime
    )

@app.get("/v1/guardrails/configs", response_model=ConfigResponse)
async def list_guardrail_configs(api_key: str = Depends(verify_api_key)):
    """List available guardrail configurations."""
    available_models = list(nlp_models.keys()) + list(huggingface_pipelines.keys())
    
    return ConfigResponse(
        status="success",
        guardrails=settings.GUARDRAIL_CONFIGS,
        available_models=available_models
    )

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with service information."""
    return {
        "service": "FastAPI Guardrails Service",
        "version": "1.0.0",
        "description": "NLP-based content validation and guardrails",
        "endpoints": {
            "validate": "/v1/guardrails/validate",
            "health": "/v1/guardrails/health",
            "configs": "/v1/guardrails/configs",
            "docs": "/docs"
        }
    }

# Set startup time
app.state.start_time = time.time()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi_guardrails:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
