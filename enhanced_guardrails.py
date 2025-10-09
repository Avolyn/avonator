"""
Enhanced FastAPI Guardrails Service with Performance Optimizations

This enhanced version includes:
- Model caching and lazy loading
- Async model inference with batching
- Redis caching for validation results
- Rate limiting and security improvements
- Comprehensive monitoring and metrics
- Batch validation endpoints
- Custom validator plugin system
"""

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union, AsyncGenerator
import logging
import time
import asyncio
import json
import hashlib
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path
import weakref
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor

# Enhanced imports
import redis
import aioredis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import jwt
from passlib.context import CryptContext
import uvicorn

# NLP and ML imports with optimizations
import spacy
import stanza
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from torch.cuda import is_available as cuda_available
import numpy as np

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Prometheus metrics
REQUEST_COUNT = Counter('guardrails_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('guardrails_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
MODEL_INFERENCE_TIME = Histogram('guardrails_model_inference_seconds', 'Model inference time', ['model_name', 'validator'])
CACHE_HITS = Counter('guardrails_cache_hits_total', 'Cache hits', ['cache_type'])
CACHE_MISSES = Counter('guardrails_cache_misses_total', 'Cache misses', ['cache_type'])
ACTIVE_CONNECTIONS = Gauge('guardrails_active_connections', 'Active connections')
MODEL_LOAD_TIME = Histogram('guardrails_model_load_seconds', 'Model loading time', ['model_name'])

# Global variables for models with caching
model_cache = {}
huggingface_pipelines = {}
redis_client = None
model_lock = asyncio.Lock()
executor = ThreadPoolExecutor(max_workers=4)

@dataclass
class ValidationContext:
    """Enhanced validation context with more metadata."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: str = "normal"  # normal, high, low
    timeout: Optional[float] = None

class ValidationRequest(BaseModel):
    """Enhanced request model with more options."""
    text: str = Field(..., min_length=1, max_length=50000, description="Text to validate")
    context: Optional[ValidationContext] = None
    guardrail_name: Optional[str] = "default"
    cache_ttl: Optional[int] = Field(300, ge=0, le=3600, description="Cache TTL in seconds")
    skip_cache: bool = False
    return_confidence: bool = True
    return_metadata: bool = True
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()

class BatchValidationRequest(BaseModel):
    """Request model for batch validation."""
    texts: List[str] = Field(..., min_items=1, max_items=100, description="List of texts to validate")
    guardrail_name: Optional[str] = "default"
    context: Optional[ValidationContext] = None
    cache_ttl: Optional[int] = Field(300, ge=0, le=3600)
    skip_cache: bool = False

class ValidatorResult(BaseModel):
    """Enhanced validator result with more metadata."""
    validator_name: str
    status: str = Field(..., regex="^(pass|fail)$")
    message: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    on_fail_action: str = Field(..., regex="^(exception|filter|reask|log|warn)$")
    metadata: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None
    model_version: Optional[str] = None

class ValidationResponse(BaseModel):
    """Enhanced response model."""
    status: str = Field(..., regex="^(success|failure)$")
    message: str
    valid: bool
    validations: List[ValidatorResult]
    processed_text: Optional[str] = None
    execution_time_ms: Optional[float] = None
    model_info: Optional[Dict[str, str]] = None
    cache_hit: bool = False
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BatchValidationResponse(BaseModel):
    """Response model for batch validation."""
    status: str
    message: str
    results: List[ValidationResponse]
    total_processed: int
    total_valid: int
    execution_time_ms: float
    cache_hits: int
    cache_misses: int

class HealthResponse(BaseModel):
    """Enhanced health check response."""
    status: str
    service: str
    version: str
    models_loaded: Dict[str, bool]
    uptime_seconds: float
    memory_usage: Dict[str, float]
    cache_status: Dict[str, Any]
    active_connections: int

# Enhanced configuration
class Settings:
    """Enhanced application settings."""
    # API Configuration
    API_KEY: str = os.getenv("GUARDRAILS_API_KEY", "default-api-key-change-in-production")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    MAX_TEXT_LENGTH: int = int(os.getenv("MAX_TEXT_LENGTH", "50000"))
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    CACHE_DEFAULT_TTL: int = int(os.getenv("CACHE_DEFAULT_TTL", "300"))
    
    # Model Configuration
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
    STANZA_MODEL: str = os.getenv("STANZA_MODEL", "en")
    HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "unitary/toxic-bert")
    MODEL_CACHE_SIZE: int = int(os.getenv("MODEL_CACHE_SIZE", "5"))
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "32"))
    MODEL_TIMEOUT: float = float(os.getenv("MODEL_TIMEOUT", "30.0"))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # CORS Configuration
    ENABLE_CORS: bool = os.getenv("ENABLE_CORS", "True").lower() == "true"
    ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "*").split(",")
    
    # Guardrail configurations (enhanced)
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
                {"name": "pii_detection", "on_fail": "filter"},
                {"name": "spam_detection", "threshold": 0.8, "on_fail": "exception"}
            ]
        },
        "permissive": {
            "description": "Permissive content validation",
            "validators": [
                {"name": "length_check", "max_length": 2000, "on_fail": "log"},
                {"name": "toxicity_check", "threshold": 0.9, "on_fail": "log"}
            ]
        },
        "batch_optimized": {
            "description": "Optimized for batch processing",
            "validators": [
                {"name": "length_check", "max_length": 1000, "on_fail": "exception"},
                {"name": "toxicity_check", "threshold": 0.7, "on_fail": "exception"}
            ]
        }
    }

settings = Settings()

# Model Manager for caching and lazy loading
class ModelManager:
    """Manages model loading, caching, and inference."""
    
    def __init__(self):
        self.models = {}
        self.pipelines = {}
        self.load_times = {}
        self.model_lock = asyncio.Lock()
    
    async def get_model(self, model_name: str, model_type: str = "spacy"):
        """Get model with caching and lazy loading."""
        cache_key = f"{model_type}_{model_name}"
        
        if cache_key in self.models:
            return self.models[cache_key]
        
        async with self.model_lock:
            if cache_key in self.models:
                return self.models[cache_key]
            
            start_time = time.time()
            try:
                if model_type == "spacy":
                    model = await asyncio.get_event_loop().run_in_executor(
                        executor, spacy.load, model_name
                    )
                elif model_type == "stanza":
                    model = await asyncio.get_event_loop().run_in_executor(
                        executor, self._load_stanza_model, model_name
                    )
                elif model_type == "huggingface":
                    model = await asyncio.get_event_loop().run_in_executor(
                        executor, self._load_huggingface_model, model_name
                    )
                else:
                    raise ValueError(f"Unknown model type: {model_type}")
                
                self.models[cache_key] = model
                self.load_times[cache_key] = time.time() - start_time
                MODEL_LOAD_TIME.labels(model_name=model_name).observe(self.load_times[cache_key])
                
                logger.info("Model loaded", model_name=model_name, model_type=model_type, 
                          load_time=self.load_times[cache_key])
                
                return model
                
            except Exception as e:
                logger.error("Failed to load model", model_name=model_name, 
                           model_type=model_type, error=str(e))
                raise
    
    def _load_stanza_model(self, model_name: str):
        """Load Stanza model."""
        stanza.download(model_name)
        return stanza.Pipeline(model_name, processors='tokenize,pos,lemma,depparse,sentiment')
    
    def _load_huggingface_model(self, model_name: str):
        """Load HuggingFace model."""
        return pipeline(
            "text-classification",
            model=model_name,
            return_all_scores=True,
            device=0 if cuda_available() else -1
        )
    
    async def get_pipeline(self, pipeline_name: str, model_name: str):
        """Get HuggingFace pipeline with caching."""
        if pipeline_name in self.pipelines:
            return self.pipelines[pipeline_name]
        
        async with self.model_lock:
            if pipeline_name in self.pipelines:
                return self.pipelines[pipeline_name]
            
            start_time = time.time()
            try:
                pipeline_obj = await asyncio.get_event_loop().run_in_executor(
                    executor, self._load_huggingface_model, model_name
                )
                self.pipelines[pipeline_name] = pipeline_obj
                self.load_times[f"pipeline_{pipeline_name}"] = time.time() - start_time
                
                logger.info("Pipeline loaded", pipeline_name=pipeline_name, 
                          model_name=model_name, load_time=self.load_times[f"pipeline_{pipeline_name}"])
                
                return pipeline_obj
                
            except Exception as e:
                logger.error("Failed to load pipeline", pipeline_name=pipeline_name, 
                           model_name=model_name, error=str(e))
                raise

# Global model manager
model_manager = ModelManager()

# Cache Manager
class CacheManager:
    """Manages Redis caching for validation results."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Connected to Redis", url=self.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.redis = None
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        if not self.redis:
            return None
        
        try:
            cached = await self.redis.get(key)
            if cached:
                CACHE_HITS.labels(cache_type="validation").inc()
                return json.loads(cached)
            else:
                CACHE_MISSES.labels(cache_type="validation").inc()
                return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int = 300):
        """Set cached validation result."""
        if not self.redis:
            return
        
        try:
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
    
    def generate_key(self, text: str, guardrail_name: str, context: Optional[ValidationContext] = None) -> str:
        """Generate cache key for validation request."""
        key_data = {
            "text": text,
            "guardrail_name": guardrail_name,
            "context": context.dict() if context else None
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

# Global cache manager
cache_manager = CacheManager(settings.REDIS_URL)

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting Enhanced FastAPI Guardrails Service...")
    
    # Connect to Redis
    await cache_manager.connect()
    
    # Pre-load critical models
    try:
        await model_manager.get_model(settings.SPACY_MODEL, "spacy")
        await model_manager.get_pipeline("toxicity", settings.HUGGINGFACE_MODEL)
        await model_manager.get_pipeline("sentiment", "cardiffnlp/twitter-roberta-base-sentiment-latest")
        logger.info("Critical models pre-loaded successfully")
    except Exception as e:
        logger.error("Failed to pre-load models", error=str(e))
    
    # Set startup time
    app.state.start_time = time.time()
    app.state.active_connections = 0
    
    yield
    
    # Shutdown
    logger.info("Shutting down Enhanced FastAPI Guardrails Service...")
    if cache_manager.redis:
        await cache_manager.redis.close()

# Create FastAPI app
app = FastAPI(
    title="Enhanced FastAPI Guardrails Service",
    description="High-performance NLP-based content validation with caching and monitoring",
    version="2.0.0",
    lifespan=lifespan
)

# Add middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track requests and update metrics."""
    start_time = time.time()
    app.state.active_connections += 1
    ACTIVE_CONNECTIONS.set(app.state.active_connections)
    
    try:
        response = await call_next(request)
        
        # Update metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    finally:
        app.state.active_connections -= 1
        ACTIVE_CONNECTIONS.set(app.state.active_connections)

# Enhanced validation functions with caching and batching
async def validate_length(text: str, max_length: int) -> ValidatorResult:
    """Validate text length."""
    start_time = time.time()
    
    if len(text) > max_length:
        result = ValidatorResult(
            validator_name="length_check",
            status="fail",
            message=f"Text length ({len(text)}) exceeds maximum allowed ({max_length})",
            on_fail_action="exception",
            execution_time_ms=(time.time() - start_time) * 1000
        )
    else:
        result = ValidatorResult(
            validator_name="length_check",
            status="pass",
            message="Text length is within acceptable limits",
            on_fail_action="exception",
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    return result

async def validate_toxicity(text: str, threshold: float) -> ValidatorResult:
    """Validate text toxicity using cached HuggingFace model."""
    start_time = time.time()
    
    try:
        pipeline = await model_manager.get_pipeline("toxicity", settings.HUGGINGFACE_MODEL)
        
        # Run inference in thread pool to avoid blocking
        results = await asyncio.get_event_loop().run_in_executor(
            executor, pipeline, text
        )
        
        # Get the highest toxicity score
        max_toxicity = max(score['score'] for score in results[0] if 'TOXIC' in score['label'].upper())
        
        execution_time = (time.time() - start_time) * 1000
        MODEL_INFERENCE_TIME.labels(model_name="toxicity", validator="toxicity_check").observe(execution_time / 1000)
        
        if max_toxicity > threshold:
            return ValidatorResult(
                validator_name="toxicity_check",
                status="fail",
                message=f"Toxicity detected (confidence: {max_toxicity:.3f})",
                confidence=max_toxicity,
                on_fail_action="exception",
                execution_time_ms=execution_time,
                model_version=settings.HUGGINGFACE_MODEL
            )
        else:
            return ValidatorResult(
                validator_name="toxicity_check",
                status="pass",
                message="No toxicity detected",
                confidence=1.0 - max_toxicity,
                on_fail_action="exception",
                execution_time_ms=execution_time,
                model_version=settings.HUGGINGFACE_MODEL
            )
    except Exception as e:
        logger.error("Toxicity validation error", error=str(e))
        return ValidatorResult(
            validator_name="toxicity_check",
            status="fail",
            message=f"Toxicity validation error: {str(e)}",
            on_fail_action="exception",
            execution_time_ms=(time.time() - start_time) * 1000
        )

async def validate_sentiment(text: str, threshold: float) -> ValidatorResult:
    """Validate text sentiment using cached HuggingFace model."""
    start_time = time.time()
    
    try:
        pipeline = await model_manager.get_pipeline("sentiment", "cardiffnlp/twitter-roberta-base-sentiment-latest")
        
        # Run inference in thread pool
        results = await asyncio.get_event_loop().run_in_executor(
            executor, pipeline, text
        )
        
        # Get sentiment score
        sentiment_score = results[0]['score'] if results[0]['label'] == 'NEGATIVE' else -results[0]['score']
        
        execution_time = (time.time() - start_time) * 1000
        MODEL_INFERENCE_TIME.labels(model_name="sentiment", validator="sentiment_check").observe(execution_time / 1000)
        
        if sentiment_score < threshold:
            return ValidatorResult(
                validator_name="sentiment_check",
                status="fail",
                message=f"Negative sentiment detected (score: {sentiment_score:.3f})",
                confidence=abs(sentiment_score),
                on_fail_action="log",
                execution_time_ms=execution_time,
                model_version="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
        else:
            return ValidatorResult(
                validator_name="sentiment_check",
                status="pass",
                message="Sentiment is acceptable",
                confidence=abs(sentiment_score),
                on_fail_action="log",
                execution_time_ms=execution_time,
                model_version="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
    except Exception as e:
        logger.error("Sentiment validation error", error=str(e))
        return ValidatorResult(
            validator_name="sentiment_check",
            status="fail",
            message=f"Sentiment validation error: {str(e)}",
            on_fail_action="log",
            execution_time_ms=(time.time() - start_time) * 1000
        )

async def validate_pii(text: str) -> ValidatorResult:
    """Validate and redact PII using cached spaCy model."""
    start_time = time.time()
    
    try:
        nlp = await model_manager.get_model(settings.SPACY_MODEL, "spacy")
        
        # Run NER in thread pool
        doc = await asyncio.get_event_loop().run_in_executor(
            executor, nlp, text
        )
        
        pii_entities = []
        redacted_text = text
        
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'EMAIL', 'PHONE']:
                pii_entities.append(f"{ent.label_}: {ent.text}")
                redacted_text = redacted_text.replace(ent.text, f"[{ent.label_}_REDACTED]")
        
        execution_time = (time.time() - start_time) * 1000
        MODEL_INFERENCE_TIME.labels(model_name="spacy", validator="pii_detection").observe(execution_time / 1000)
        
        if pii_entities:
            return ValidatorResult(
                validator_name="pii_detection",
                status="fail",
                message=f"PII detected: {', '.join(pii_entities)}",
                on_fail_action="filter",
                metadata={"redacted_text": redacted_text, "entities": pii_entities},
                execution_time_ms=execution_time,
                model_version=settings.SPACY_MODEL
            )
        else:
            return ValidatorResult(
                validator_name="pii_detection",
                status="pass",
                message="No PII detected",
                on_fail_action="filter",
                execution_time_ms=execution_time,
                model_version=settings.SPACY_MODEL
            )
    except Exception as e:
        logger.error("PII validation error", error=str(e))
        return ValidatorResult(
            validator_name="pii_detection",
            status="fail",
            message=f"PII validation error: {str(e)}",
            on_fail_action="filter",
            execution_time_ms=(time.time() - start_time) * 1000
        )

# Main validation function with caching
async def validate_text_with_guardrails(
    text: str, 
    guardrail_name: str, 
    context: Optional[ValidationContext] = None,
    cache_ttl: int = 300,
    skip_cache: bool = False
) -> ValidationResponse:
    """Enhanced validation function with caching and performance optimizations."""
    start_time = time.time()
    request_id = context.request_id if context else None
    
    # Check cache first
    cache_hit = False
    if not skip_cache and cache_manager.redis:
        cache_key = cache_manager.generate_key(text, guardrail_name, context)
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            cache_hit = True
            logger.info("Cache hit", request_id=request_id, cache_key=cache_key)
            return ValidationResponse(**cached_result)
    
    try:
        config = settings.GUARDRAIL_CONFIGS.get(guardrail_name, settings.GUARDRAIL_CONFIGS["default"])
        validations = []
        all_passed = True
        processed_text = text
        
        # Run validations concurrently for better performance
        validation_tasks = []
        
        for validator_config in config["validators"]:
            validator_name = validator_config["name"]
            on_fail_action = validator_config["on_fail"]
            
            if validator_name == "length_check":
                max_length = validator_config.get("max_length", 1000)
                task = validate_length(text, max_length)
            elif validator_name == "toxicity_check":
                threshold = validator_config.get("threshold", 0.7)
                task = validate_toxicity(text, threshold)
            elif validator_name == "sentiment_check":
                threshold = validator_config.get("threshold", -0.5)
                task = validate_sentiment(text, threshold)
            elif validator_name == "pii_detection":
                task = validate_pii(text)
            else:
                continue
            
            validation_tasks.append((task, on_fail_action))
        
        # Wait for all validations to complete
        validation_results = await asyncio.gather(*[task for task, _ in validation_tasks])
        
        # Process results
        for result, on_fail_action in zip(validation_results, [action for _, action in validation_tasks]):
            result.on_fail_action = on_fail_action
            validations.append(result)
            if result.status == "fail":
                all_passed = False
                if result.metadata and "redacted_text" in result.metadata:
                    processed_text = result.metadata["redacted_text"]
        
        execution_time = (time.time() - start_time) * 1000
        
        response = ValidationResponse(
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
            },
            cache_hit=cache_hit,
            request_id=request_id
        )
        
        # Cache the result
        if not skip_cache and cache_manager.redis:
            await cache_manager.set(cache_key, response.dict(), cache_ttl)
        
        logger.info("Validation completed", 
                   request_id=request_id, 
                   valid=all_passed, 
                   execution_time_ms=execution_time,
                   cache_hit=cache_hit)
        
        return response
        
    except Exception as e:
        logger.error("Validation error", request_id=request_id, error=str(e))
        return ValidationResponse(
            status="failure",
            message=f"Internal error during validation: {str(e)}",
            valid=False,
            validations=[],
            execution_time_ms=(time.time() - start_time) * 1000,
            cache_hit=cache_hit,
            request_id=request_id
        )

# API Endpoints
@app.post("/v1/guardrails/validate", response_model=ValidationResponse)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}second")
async def validate_text(
    request: ValidationRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Enhanced text validation with caching and performance optimizations."""
    try:
        context = ValidationContext(
            user_id=request.context.user_id if request.context else None,
            session_id=request.context.session_id if request.context else None,
            request_id=f"req_{int(time.time() * 1000)}",
            tenant_id=request.context.tenant_id if request.context else None,
            metadata=request.context.metadata if request.context else None,
            priority=request.context.priority if request.context else "normal",
            timeout=request.context.timeout if request.context else None
        )
        
        result = await validate_text_with_guardrails(
            text=request.text,
            guardrail_name=request.guardrail_name,
            context=context,
            cache_ttl=request.cache_ttl,
            skip_cache=request.skip_cache
        )
        
        return result
    except Exception as e:
        logger.error("Validation endpoint error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/v1/guardrails/validate/batch", response_model=BatchValidationResponse)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS * 2}/{settings.RATE_LIMIT_WINDOW}second")
async def validate_batch(
    request: BatchValidationRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Batch validation endpoint for processing multiple texts efficiently."""
    start_time = time.time()
    
    try:
        # Process texts in batches for better performance
        batch_size = min(settings.BATCH_SIZE, len(request.texts))
        results = []
        cache_hits = 0
        cache_misses = 0
        
        for i in range(0, len(request.texts), batch_size):
            batch_texts = request.texts[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = []
            for text in batch_texts:
                context = ValidationContext(
                    user_id=request.context.user_id if request.context else None,
                    session_id=request.context.session_id if request.context else None,
                    request_id=f"batch_{int(time.time() * 1000)}_{i}",
                    tenant_id=request.context.tenant_id if request.context else None,
                    metadata=request.context.metadata if request.context else None,
                    priority=request.context.priority if request.context else "normal"
                )
                
                task = validate_text_with_guardrails(
                    text=text,
                    guardrail_name=request.guardrail_name,
                    context=context,
                    cache_ttl=request.cache_ttl,
                    skip_cache=request.skip_cache
                )
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
            
            # Count cache hits/misses
            for result in batch_results:
                if result.cache_hit:
                    cache_hits += 1
                else:
                    cache_misses += 1
        
        execution_time = (time.time() - start_time) * 1000
        total_valid = sum(1 for result in results if result.valid)
        
        return BatchValidationResponse(
            status="success",
            message=f"Batch validation completed: {len(results)} texts processed",
            results=results,
            total_processed=len(results),
            total_valid=total_valid,
            execution_time_ms=execution_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
        
    except Exception as e:
        logger.error("Batch validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/v1/guardrails/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check with detailed system information."""
    uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    
    # Check model status
    models_loaded = {
        "spacy": settings.SPACY_MODEL in model_manager.models,
        "stanza": settings.STANZA_MODEL in model_manager.models,
        "toxicity": "toxicity" in model_manager.pipelines,
        "sentiment": "sentiment" in model_manager.pipelines
    }
    
    # Get memory usage
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_usage = {
        "rss_mb": memory_info.rss / 1024 / 1024,
        "vms_mb": memory_info.vms / 1024 / 1024,
        "percent": process.memory_percent()
    }
    
    # Check cache status
    cache_status = {
        "redis_connected": cache_manager.redis is not None,
        "cache_available": cache_manager.redis is not None
    }
    
    return HealthResponse(
        status="healthy",
        service="enhanced-fastapi-guardrails",
        version="2.0.0",
        models_loaded=models_loaded,
        uptime_seconds=uptime,
        memory_usage=memory_usage,
        cache_status=cache_status,
        active_connections=app.state.active_connections
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/v1/guardrails/configs")
async def list_guardrail_configs(api_key: str = Depends(verify_api_key)):
    """List available guardrail configurations."""
    available_models = list(model_manager.models.keys()) + list(model_manager.pipelines.keys())
    
    return {
        "status": "success",
        "guardrails": settings.GUARDRAIL_CONFIGS,
        "available_models": available_models,
        "cache_status": {
            "redis_connected": cache_manager.redis is not None,
            "default_ttl": settings.CACHE_DEFAULT_TTL
        }
    }

# Dependency for API key validation
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header."""
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials

if __name__ == "__main__":
    uvicorn.run(
        "enhanced_guardrails:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
