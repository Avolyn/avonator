"""
Minimal FastAPI wrapper for LlamaGuard-7b service
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel

from llamaguard_service import (
    ValidationRequest, 
    ValidationResponse, 
    get_service,
    validate_text,
    validate_batch
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LlamaGuard-7b API",
    description="Minimal content safety validation service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextValidationRequest(BaseModel):
    text: str
    context: Optional[str] = None


class BatchValidationRequest(BaseModel):
    texts: List[str]
    contexts: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str


@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup"""
    logger.info("Starting LlamaGuard-7b service...")
    try:
        service = await get_service()
        await service.load_model()
        logger.info("Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down LlamaGuard-7b service...")
    try:
        service = await get_service()
        await service.cleanup()
        logger.info("Service cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        service = await get_service()
        is_healthy = await service.health_check()
        
        return HealthResponse(
            status="healthy" if is_healthy else "unhealthy",
            model_loaded=service._loaded,
            device=service.device
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            model_loaded=False,
            device="unknown"
        )


@app.post("/validate", response_model=ValidationResponse)
async def validate_single(request: TextValidationRequest):
    """Validate a single text for safety"""
    try:
        result = await validate_text(request.text, request.context)
        return result
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate/batch", response_model=List[ValidationResponse])
async def validate_multiple(request: BatchValidationRequest):
    """Validate multiple texts for safety"""
    try:
        results = await validate_batch(request.texts, request.contexts)
        return results
    except Exception as e:
        logger.error(f"Batch validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "LlamaGuard-7b API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "validate": "/validate",
            "batch": "/validate/batch",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
