# FastAPI Guardrails Service

A streamlined, production-ready guardrail service built with FastAPI and powered by advanced NLP models. This service provides content validation, toxicity detection, sentiment analysis, and PII detection using spaCy, Stanza, and HuggingFace transformers instead of regex patterns.

## 🚀 Features

- **FastAPI-based**: Modern, fast, and automatically documented API
- **NLP-powered**: Uses spaCy, Stanza, and HuggingFace transformers for intelligent content analysis
- **Multiple Guardrail Configurations**: Pre-configured guardrails for different use cases
- **Security-first**: Built-in API key authentication, CORS, and security middleware
- **Production-ready**: Comprehensive error handling, logging, and monitoring
- **Async Support**: Full async/await support for high performance
- **Pydantic Validation**: Type-safe request/response models
- **Health Monitoring**: Built-in health checks and model status monitoring

## 🏗️ Architecture

### Core Components

1. **FastAPI Application** (`fastapi_guardrails.py`): Main service with API endpoints
2. **Configuration** (`config.py`): Centralized configuration management
3. **NLP Models**: spaCy, Stanza, and HuggingFace transformers
4. **Validators**: Modular validation functions for different content types

### Supported Validators

- **Length Check**: Validates text length against configurable limits
- **Toxicity Detection**: Uses HuggingFace models to detect toxic content
- **Sentiment Analysis**: Analyzes text sentiment using transformer models
- **PII Detection**: Identifies and redacts personally identifiable information using spaCy NER

## 📦 Installation

### Prerequisites

- Python 3.8+
- pip or conda

### Quick Start

1. **Clone and setup**:
```bash
git clone <repository>
cd fastapi-guardrails
pip install -r requirements.txt
```

2. **Download spaCy model**:
```bash
python -m spacy download en_core_web_sm
```

3. **Set environment variables** (optional):
```bash
export GUARDRAILS_API_KEY="your-secure-api-key"
export SPACY_MODEL="en_core_web_sm"
export HUGGINGFACE_MODEL="unitary/toxic-bert"
```

4. **Run the service**:
```bash
python fastapi_guardrails.py
```

The service will be available at `http://localhost:8000`

### Docker Installation

```bash
# Build the image
docker build -t fastapi-guardrails .

# Run the container
docker run -p 8000:8000 \
  -e GUARDRAILS_API_KEY="your-secure-api-key" \
  fastapi-guardrails
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDRAILS_API_KEY` | `default-api-key-change-in-production` | API key for authentication |
| `DEBUG` | `False` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `SPACY_MODEL` | `en_core_web_sm` | spaCy model to use |
| `STANZA_MODEL` | `en` | Stanza language model |
| `HUGGINGFACE_MODEL` | `unitary/toxic-bert` | HuggingFace toxicity model |
| `MAX_TEXT_LENGTH` | `10000` | Maximum text length for validation |
| `ENABLE_CORS` | `True` | Enable CORS middleware |

### Guardrail Configurations

The service comes with pre-configured guardrails:

- **`default`**: Balanced validation with toxicity and sentiment checks
- **`strict`**: Strict content moderation for sensitive applications
- **`permissive`**: Minimal validation for open platforms
- **`content_moderation`**: Comprehensive content moderation
- **`customer_service`**: Optimized for customer service applications

## 📚 API Documentation

### Interactive Documentation

Once the service is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

#### POST `/v1/guardrails/validate`

Validate text content using specified guardrails.

**Request Body**:
```json
{
  "text": "Text to validate",
  "guardrail_name": "default",
  "context": {
    "user_id": "optional-user-id",
    "session_id": "optional-session-id",
    "metadata": {}
  }
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Validation completed successfully",
  "valid": true,
  "validations": [
    {
      "validator_name": "toxicity_check",
      "status": "pass",
      "message": "No toxicity detected",
      "confidence": 0.95,
      "on_fail_action": "exception"
    }
  ],
  "processed_text": null,
  "execution_time_ms": 150.5,
  "model_info": {
    "spacy_model": "en_core_web_sm",
    "stanza_model": "en",
    "huggingface_model": "unitary/toxic-bert"
  }
}
```

#### GET `/v1/guardrails/health`

Check service health and model status.

**Response**:
```json
{
  "status": "healthy",
  "service": "fastapi-guardrails",
  "version": "1.0.0",
  "models_loaded": {
    "spacy": true,
    "stanza": true,
    "toxicity": true,
    "sentiment": true
  },
  "uptime_seconds": 3600.5
}
```

#### GET `/v1/guardrails/configs`

Get available guardrail configurations (requires API key).

## 🚀 Usage Examples

### Python Client

```python
import asyncio
import httpx

async def validate_text():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/guardrails/validate",
            headers={"Authorization": "Bearer your-api-key"},
            json={
                "text": "Hello, this is a test message.",
                "guardrail_name": "default"
            }
        )
        result = response.json()
        print(f"Valid: {result['valid']}")

asyncio.run(validate_text())
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/v1/guardrails/health

# Validate text
curl -X POST http://localhost:8000/v1/guardrails/validate \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a test message",
    "guardrail_name": "default"
  }'

# Get configurations
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/v1/guardrails/configs
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:8000/v1/guardrails/validate', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: 'This is a test message',
    guardrail_name: 'default'
  })
});

const result = await response.json();
console.log('Valid:', result.valid);
```

## 🔒 Security Features

- **API Key Authentication**: Secure endpoint access
- **CORS Support**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic models for request validation
- **Rate Limiting**: Configurable rate limiting (optional)
- **Trusted Hosts**: Host validation middleware
- **Error Handling**: Secure error responses without information leakage

## 🧪 Testing

Run the example usage script:

```bash
python example_usage.py
```

This will demonstrate various validation scenarios and guardrail configurations.

## 📊 Monitoring and Logging

The service includes comprehensive logging and monitoring:

- **Structured Logging**: JSON-formatted logs for easy parsing
- **Health Checks**: Model status and service health monitoring
- **Performance Metrics**: Execution time tracking
- **Error Tracking**: Detailed error logging and reporting

## 🔧 Customization

### Adding Custom Validators

1. Create a new validator function in `fastapi_guardrails.py`:

```python
async def validate_custom(text: str, **kwargs) -> ValidatorResult:
    # Your custom validation logic
    pass
```

2. Add the validator to a guardrail configuration in `config.py`:

```python
"custom_guardrail": {
    "description": "Custom validation",
    "validators": [
        {"name": "custom_validator", "param": "value", "on_fail": "exception"}
    ]
}
```

3. Add the validator to the main validation function.

### Using Different NLP Models

Update the model loading in `fastapi_guardrails.py`:

```python
# Load different spaCy model
nlp_models['spacy'] = spacy.load("en_core_web_lg")

# Load different HuggingFace model
huggingface_pipelines['toxicity'] = pipeline(
    "text-classification",
    model="facebook/roberta-hate-speech-dynabench-r4-target"
)
```

## 🚀 Deployment

### Production Deployment

1. **Set secure API key**:
```bash
export GUARDRAILS_API_KEY="your-very-secure-api-key"
```

2. **Use production WSGI server**:
```bash
uvicorn fastapi_guardrails:app --host 0.0.0.0 --port 8000 --workers 4
```

3. **Use reverse proxy** (nginx example):
```nginx
server {
    listen 80;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .
EXPOSE 8000

CMD ["uvicorn", "fastapi_guardrails:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the [API documentation](http://localhost:8000/docs)
2. Review the example usage script
3. Check the logs for error details
4. Open an issue on GitHub

## 🔄 Migration from Flask Version

This FastAPI version provides several improvements over the original Flask implementation:

- **Better Performance**: Async support and better request handling
- **Type Safety**: Pydantic models for validation
- **Auto Documentation**: Built-in Swagger/OpenAPI documentation
- **Modern Security**: Better security patterns and middleware
- **NLP Models**: Advanced ML-based validation instead of regex
- **Production Ready**: Better error handling and monitoring

To migrate from the Flask version:

1. Update your API calls to use the new endpoint structure
2. Update authentication to use Bearer tokens
3. Update response parsing to handle the new response format
4. Test with the new validation logic
