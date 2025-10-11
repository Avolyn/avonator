# Docker & CI/CD Setup Guide

Complete guide for running the FastAPI Guardrails Service with Docker and automated CI/CD pipelines.

## Quick Start

### 1. **Complete Setup (Recommended)**
```bash
# Make setup script executable (Linux/Mac)
chmod +x setup.sh

# Run complete setup
./setup.sh setup

# Start development environment
./setup.sh dev
```

### 2. **Manual Setup**
```bash
# Clone and navigate to project
git clone <repository>
cd fastapi-guardrails

# Copy environment file
cp env.example .env

# Install dependencies
pip install -r enhanced_requirements.txt
python -m spacy download en_core_web_sm

# Build Docker images
docker build -t guardrails-api:latest .

# Start with Docker Compose
docker-compose up -d
```

## 🐳 Docker Setup

### **Multi-Stage Dockerfile**

The Dockerfile includes three optimized stages:

1. **Development** (`development`): Hot reload, debugging tools
2. **Production** (`production`): Optimized for performance
3. **Testing** (`testing`): Includes test dependencies

### **Docker Compose Configurations**

#### **Development** (`docker-compose.yml`)
```yaml
services:
  - guardrails-api (development mode)
  - redis (caching)
  - prometheus (metrics)
  - grafana (monitoring)
  - nginx (reverse proxy)
```

#### **Production** (`docker-compose.prod.yml`)
```yaml
services:
  - guardrails-api (production mode, 3 replicas)
  - redis (optimized)
  - prometheus (with retention)
  - grafana (with SSL)
  - nginx (with SSL)
  - loki (log aggregation)
  - promtail (log collection)
```

### **Docker Commands**

```bash
# Build all images
docker build -t guardrails-api:latest .
docker build --target development -t guardrails-api:dev .
docker build --target testing -t guardrails-api:test .

# Run development environment
docker-compose up -d

# Run production environment
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f guardrails-api

# Scale production
docker-compose -f docker-compose.prod.yml up -d --scale guardrails-api=5

# Stop all services
docker-compose down
docker-compose -f docker-compose.prod.yml down
```

## Testing Suite

### **Test Structure**
```
tests/
├── test_api_endpoints.py      # API endpoint tests
├── test_validators.py         # Validation logic tests
├── test_integration.py        # Integration tests
├── test_performance.py        # Performance tests
└── load_test.py              # Load testing with Locust
```

### **Running Tests**

```bash
# All tests
pytest tests/ -v

# Specific test categories
pytest tests/test_api_endpoints.py -v
pytest tests/test_integration.py -v
pytest tests/test_performance.py -v

# With coverage
pytest tests/ -v --cov=enhanced_guardrails --cov-report=html

# Performance tests only
pytest tests/test_performance.py -v --benchmark-only

# Load tests
locust -f tests/load_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless
```

### **Test Markers**
- `@pytest.mark.slow` - Slow tests (deselect with `-m "not slow"`)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.redis` - Tests requiring Redis

## CI/CD Pipeline

### **GitHub Actions Workflow** (`.github/workflows/ci-cd.yml`)

#### **Pipeline Stages:**

1. **Linting & Code Quality**
   - Black formatter check
   - isort import sorting
   - Flake8 linting
   - MyPy type checking

2. **Security Scanning**
   - Trivy vulnerability scanner
   - Bandit security linter
   - Safety dependency check

3. **Unit Tests**
   - FastAPI endpoint tests
   - Validator logic tests
   - Coverage reporting

4. **Integration Tests**
   - End-to-end validation flow
   - Redis caching integration
   - Health check integration

5. **Performance Tests**
   - Response time benchmarks
   - Load testing
   - Memory usage tests

6. **Docker Build & Test**
   - Multi-stage image builds
   - Container testing
   - Image security scanning

7. **Deployment**
   - Staging deployment (develop branch)
   - Production deployment (main branch)
   - Load testing on staging

### **Environment Variables for CI/CD**

Set these secrets in your GitHub repository:

```bash
# Required
GUARDRAILS_API_KEY=your-secure-api-key
DOCKER_USERNAME=your-dockerhub-username
DOCKER_PASSWORD=your-dockerhub-password

# Optional
JWT_SECRET=your-jwt-secret
GRAFANA_PASSWORD=your-grafana-password
GRAFANA_SECRET_KEY=your-grafana-secret
```

### **Manual CI/CD Commands**

```bash
# Run linting
black --check --diff .
isort --check-only --diff .
flake8 .
mypy enhanced_guardrails.py

# Run security scans
trivy fs .
bandit -r .
safety check

# Run tests
pytest tests/ -v --cov=enhanced_guardrails --cov-report=xml

# Build and test Docker
docker build --target testing -t guardrails-api:test .
docker run --rm guardrails-api:test

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=300s --headless
```

## Monitoring & Observability

### **Prometheus Metrics**
- Request duration and count
- Model inference timing
- Cache hit/miss ratios
- Memory and CPU usage
- Business metrics (toxicity, PII detection)

### **Grafana Dashboards**
- Service health overview
- Performance metrics
- Error rates and trends
- Resource utilization

### **Log Aggregation**
- Structured JSON logging
- Request tracing with correlation IDs
- Centralized log collection with Loki
- Log analysis with Grafana

### **Health Checks**
- Application health: `/v1/guardrails/health`
- Metrics endpoint: `/metrics`
- Docker health checks
- Kubernetes liveness/readiness probes

## Deployment Options

### **1. Docker Compose (Recommended for Development)**
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### **2. Kubernetes (Production)**
```bash
# Deploy to Kubernetes
kubectl apply -f kubernetes_deployment.yaml

# Check status
kubectl get pods -n guardrails
kubectl get services -n guardrails
```

### **3. Cloud Platforms**
- **AWS ECS/Fargate**: Use provided Docker images
- **Google Cloud Run**: Deploy as containerized service
- **Azure Container Instances**: Run as managed containers
- **DigitalOcean App Platform**: Deploy with managed infrastructure

## 🔧 Configuration

### **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDRAILS_API_KEY` | `default-api-key` | API authentication key |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `DEBUG` | `False` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SPACY_MODEL` | `en_core_web_sm` | spaCy model |
| `HUGGINGFACE_MODEL` | `unitary/toxic-bert` | HuggingFace model |
| `CACHE_DEFAULT_TTL` | `300` | Cache TTL in seconds |
| `RATE_LIMIT_REQUESTS` | `100` | Rate limit per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

### **Docker Environment Files**
- `.env` - Development configuration
- `.env.prod` - Production configuration
- `env.example` - Template file

## Development Workflow

### **1. Local Development**
```bash
# Start development environment
./setup.sh dev

# Make changes to code
# Hot reload is enabled

# Run tests
./setup.sh test

# View logs
docker-compose logs -f guardrails-api
```

### **2. Testing Changes**
```bash
# Run specific tests
pytest tests/test_api_endpoints.py -v

# Run with coverage
pytest tests/ -v --cov=enhanced_guardrails --cov-report=html

# Run load tests
./setup.sh load-test
```

### **3. Code Quality**
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy enhanced_guardrails.py

# Security scan
bandit -r .
safety check
```

## Troubleshooting

### **Common Issues**

1. **Port Conflicts**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Use different ports
   docker-compose up -d --scale guardrails-api=0
   docker run -p 8001:8000 guardrails-api:latest
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis status
   docker-compose logs redis
   
   # Restart Redis
   docker-compose restart redis
   ```

3. **Model Loading Issues**
   ```bash
   # Check model download
   python -m spacy download en_core_web_sm
   
   # Check Docker logs
   docker-compose logs guardrails-api
   ```

4. **Memory Issues**
   ```bash
   # Check memory usage
   docker stats
   
   # Increase memory limits in docker-compose.yml
   ```

### **Debug Commands**
```bash
# Enter container
docker exec -it guardrails-api bash

# Check logs
docker-compose logs -f --tail=100 guardrails-api

# Restart services
docker-compose restart

# Clean up
docker-compose down -v
docker system prune -f
```

## Performance Optimization

### **Docker Optimizations**
- Multi-stage builds for smaller images
- Layer caching for faster builds
- Health checks for better orchestration
- Resource limits for stability

### **Application Optimizations**
- Model caching and lazy loading
- Redis caching for validation results
- Async processing with thread pools
- Connection pooling

### **Monitoring Optimizations**
- Prometheus metrics collection
- Grafana dashboards for visualization
- Log aggregation and analysis
- Alerting on performance thresholds


2. **Configure monitoring** with Prometheus and Grafana
3. **Deploy to your preferred platform** (Kubernetes, cloud, etc.)
4. **Set up alerting** for production monitoring
5. **Customize validators** for your specific use case

The complete setup provides a production-ready, scalable, and maintainable FastAPI Guardrails Service with comprehensive testing, monitoring, and deployment capabilities.
