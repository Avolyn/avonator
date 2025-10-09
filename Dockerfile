# Multi-stage Dockerfile for FastAPI Guardrails Service
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt enhanced_requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r enhanced_requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    black==23.11.0 \
    isort==5.12.0 \
    flake8==6.1.0 \
    mypy==1.7.1

# Copy source code
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/v1/guardrails/health || exit 1

# Development command
CMD ["uvicorn", "enhanced_guardrails:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Install production dependencies only
RUN pip install --no-cache-dir \
    gunicorn==21.2.0 \
    uvicorn[standard]==0.24.0

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/models /app/data

# Change ownership to appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/v1/guardrails/health || exit 1

# Production command
CMD ["gunicorn", "enhanced_guardrails:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# Testing stage
FROM development as testing

# Install additional testing dependencies
RUN pip install --no-cache-dir \
    pytest-xdist==3.5.0 \
    pytest-benchmark==4.0.0 \
    locust==2.17.0 \
    httpx==0.25.2

# Copy test files
COPY tests/ ./tests/
COPY conftest.py ./

# Run tests
CMD ["pytest", "tests/", "-v", "--cov=enhanced_guardrails", "--cov-report=html", "--cov-report=xml"]