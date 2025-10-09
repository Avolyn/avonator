#!/usr/bin/env python3
"""
Startup script for FastAPI Guardrails Service

This script handles model downloading and service startup with proper error handling.
"""

import asyncio
import sys
import os
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    logger.info(f"Python version: {sys.version}")

def install_requirements():
    """Install required packages."""
    logger.info("Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install requirements: {e}")
        sys.exit(1)

def download_spacy_model(model_name="en_core_web_sm"):
    """Download spaCy model if not present."""
    try:
        import spacy
        nlp = spacy.load(model_name)
        logger.info(f"spaCy model {model_name} is already available")
    except OSError:
        logger.info(f"Downloading spaCy model: {model_name}")
        try:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", model_name])
            logger.info(f"spaCy model {model_name} downloaded successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download spaCy model: {e}")
            logger.info("You can download it manually with: python -m spacy download en_core_web_sm")
            sys.exit(1)

def check_environment():
    """Check environment variables and configuration."""
    api_key = os.getenv("GUARDRAILS_API_KEY", "default-api-key-change-in-production")
    if api_key == "default-api-key-change-in-production":
        logger.warning("Using default API key. Set GUARDRAILS_API_KEY environment variable for production!")
    
    logger.info("Environment check completed")

def create_directories():
    """Create necessary directories."""
    directories = ["logs", "models", "data"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")

async def test_imports():
    """Test if all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        import fastapi
        import uvicorn
        import spacy
        import stanza
        import transformers
        import torch
        logger.info("All imports successful")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("Please install requirements: pip install -r requirements.txt")
        sys.exit(1)

def start_service():
    """Start the FastAPI service."""
    logger.info("Starting FastAPI Guardrails Service...")
    try:
        import uvicorn
        from fastapi_guardrails import app
        
        # Get configuration from environment
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        debug = os.getenv("DEBUG", "False").lower() == "true"
        
        logger.info(f"Starting server on {host}:{port}")
        logger.info(f"Debug mode: {debug}")
        logger.info(f"API documentation: http://{host}:{port}/docs")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=debug,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)

def main():
    """Main startup function."""
    logger.info("🚀 FastAPI Guardrails Service Startup")
    logger.info("=" * 50)
    
    # Pre-flight checks
    check_python_version()
    check_environment()
    create_directories()
    
    # Install dependencies if needed
    if not os.path.exists("requirements.txt"):
        logger.error("requirements.txt not found")
        sys.exit(1)
    
    # Test imports
    asyncio.run(test_imports())
    
    # Download spaCy model
    spacy_model = os.getenv("SPACY_MODEL", "en_core_web_sm")
    download_spacy_model(spacy_model)
    
    logger.info("✅ All checks passed. Starting service...")
    logger.info("=" * 50)
    
    # Start the service
    start_service()

if __name__ == "__main__":
    main()
