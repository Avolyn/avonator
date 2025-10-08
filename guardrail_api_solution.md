# Guardrails AI API Solution

A modular, API-driven guardrails solution designed for easy integration with LLM chatbots. This solution provides plug-and-play functionality with a standardized REST API interface that allows for easy replacement of the underlying guardrails implementation.

## Overview

This project consists of two main components:

1. **Guardrails API Service** - A standalone microservice that provides text validation using configurable guardrails
2. **LLM Chatbot Example** - A demonstration chatbot that integrates with the guardrails service

## Key Features

- **Modular Plugin Architecture** - Easy to swap between different guardrails implementations
- **RESTful API** - Standard HTTP API for seamless integration
- **Configurable Guardrails** - Multiple pre-configured validation profiles
- **Real-time Validation** - Both input and output validation for LLM interactions
- **Health Monitoring** - Built-in health checks and service monitoring
- **Cross-Origin Support** - CORS enabled for web application integration

## Architecture

The solution follows a microservices architecture with clear separation of concerns:

```
┌─────────────────┐    HTTP API    ┌──────────────────┐
│   LLM Chatbot   │ ──────────────► │  Guardrails API  │
│    Service      │                 │     Service      │
└─────────────────┘                 └──────────────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │  Plugin System   │
                                    │                  │
                                    │ ┌──────────────┐ │
                                    │ │ Mock Plugin  │ │
                                    │ └──────────────┘ │
                                    │ ┌──────────────┐ │
                                    │ │OpenAI Plugin │ │
                                    │ └──────────────┘ │
                                    │ ┌──────────────┐ │
                                    │ │Custom Plugin │ │
                                    │ └──────────────┘ │
                                    └──────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- pip
- Virtual environment (recommended)

### 1. Start the Guardrails API Service

```bash
cd guardrails_api
source venv/bin/activate
pip install -r requirements.txt
FLASK_APP=src/main.py flask run --host=0.0.0.0 --port=5002
```

### 2. Start the Example Chatbot Service

```bash
cd llm_chatbot_example
source venv/bin/activate
pip install -r requirements.txt
GUARDRAILS_API_URL=http://localhost:5002/api/v1/guardrails FLASK_APP=src/main.py flask run --host=0.0.0.0 --port=5003
```

### 3. Test the Integration

```bash
# Test guardrails service health
curl -X GET http://localhost:5002/api/v1/guardrails/health

# Test chatbot service health
curl -X GET http://localhost:5003/api/v1/chat/health

# Send a message to the chatbot
curl -X POST http://localhost:5003/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?", "guardrail_config": "default"}'
```

## API Documentation

### Guardrails API Service

#### Base URL: `http://localhost:5002/api/v1`

#### Authentication
All endpoints require an API key passed in the `X-API-Key` header.

#### Endpoints

##### Health Check
```http
GET /guardrails/health
```

Response:
```json
{
  "status": "healthy",
  "service": "guardrails-api",
  "version": "1.0.0"
}
```

##### Validate Text
```http
POST /guardrails/validate
Content-Type: application/json
X-API-Key: your-api-key

{
  "text": "Text to validate",
  "guardrail_name": "default",
  "context": {
    "user_id": "user123",
    "session_id": "session456"
  }
}
```

Response:
```json
{
  "status": "success",
  "message": "Validation completed successfully",
  "valid": false,
  "validations": [
    {
      "validator_name": "profanity_check",
      "status": "fail",
      "message": "Profanity detected in text",
      "on_fail_action": "filter"
    }
  ],
  "processed_text": "Filtered text with **** replacing profanity",
  "plugin_info": {
    "name": "mock_guardrails",
    "execution_time_ms": 0.05
  }
}
```

##### List Guardrail Configurations
```http
GET /guardrails/configs
X-API-Key: your-api-key
```

##### Plugin Management
```http
GET /plugins                    # List all plugins
GET /plugins/active            # Get active plugin info
POST /plugins/switch           # Switch active plugin
POST /plugins/load             # Load new plugin
GET /plugins/{name}/health     # Check plugin health
```

### LLM Chatbot API

#### Base URL: `http://localhost:5003/api/v1`

##### Chat Endpoint
```http
POST /chat
Content-Type: application/json

{
  "message": "User message",
  "guardrail_config": "default",
  "user_id": "user123",
  "session_id": "session456"
}
```

Response:
```json
{
  "response": "Chatbot response",
  "input_validation": { /* validation results */ },
  "output_validation": { /* validation results */ },
  "guardrail_config": "default"
}
```

## Configuration

### Guardrail Configurations

The system comes with several pre-configured guardrail profiles:

1. **default** - Basic text validation with length check and profanity filtering
2. **toxic_language_guard** - Specialized for detecting toxic language
3. **pii_redaction_guard** - Detects and redacts personally identifiable information
4. **content_moderation** - Comprehensive content moderation

### Environment Variables

- `GUARDRAILS_API_KEY` - API key for the guardrails service
- `GUARDRAILS_API_URL` - URL of the guardrails service (for chatbot integration)
- `DEBUG` - Enable debug mode

## Plugin System

The plugin system allows for easy replacement of the guardrails implementation without changing the API interface.

### Creating a Custom Plugin

1. Inherit from the `GuardrailsPlugin` abstract base class
2. Implement the required methods:
   - `initialize(config)` - Initialize the plugin
   - `validate_text(text, guardrail_name, context)` - Perform validation
   - `get_available_guardrails()` - Return available configurations
   - `health_check()` - Check plugin health

3. Register the plugin with the plugin manager

Example:
```python
class CustomGuardrailsPlugin(GuardrailsPlugin):
    @property
    def name(self):
        return "custom_guardrails"
    
    @property
    def version(self):
        return "1.0.0"
    
    def initialize(self, config):
        # Initialize your plugin
        return True
    
    def validate_text(self, text, guardrail_name, context):
        # Implement your validation logic
        return GuardrailsResponse(...)
    
    # ... implement other required methods
```

### Available Plugins

1. **MockGuardrailsPlugin** - Default plugin with mock validation logic
2. **OpenAIModerationPlugin** - Integration with OpenAI's Moderation API (requires API key)

## Testing

The solution includes comprehensive testing capabilities:

### Manual Testing

Use the provided curl commands to test individual endpoints and integration scenarios.

### Web Interface

Access the chatbot web interface at `http://localhost:5003/chatbot.html` for interactive testing.

### Test Scenarios

1. **Normal Message** - "Hello, how are you?"
2. **Profanity Filtering** - "This damn thing is broken!"
3. **PII Detection** - "Contact me at john@example.com"
4. **Toxic Language** - "You're stupid!"

## Deployment

### Production Deployment

For production deployment, consider:

1. Using a production WSGI server (e.g., Gunicorn)
2. Setting up proper API key management
3. Configuring logging and monitoring
4. Using environment-specific configuration files
5. Setting up health checks and alerting

### Docker Deployment

Both services can be containerized using Docker for easier deployment and scaling.

## Security Considerations

1. **API Key Management** - Use strong, unique API keys and rotate them regularly
2. **Input Validation** - All inputs are validated before processing
3. **Rate Limiting** - Consider implementing rate limiting for production use
4. **HTTPS** - Use HTTPS in production environments
5. **Logging** - Ensure sensitive data is not logged

## Monitoring and Observability

The solution includes built-in monitoring capabilities:

1. **Health Checks** - All services provide health check endpoints
2. **Execution Metrics** - Validation execution times are tracked
3. **Plugin Status** - Plugin health is monitored
4. **Dependency Checks** - Service dependencies are validated

## Troubleshooting

### Common Issues

1. **Service Not Starting** - Check port availability and dependencies
2. **Plugin Not Loading** - Verify plugin configuration and dependencies
3. **Validation Errors** - Check API key and request format
4. **Connection Issues** - Verify service URLs and network connectivity

### Logging

All services provide detailed logging for troubleshooting:

```bash
# View guardrails service logs
tail -f guardrails_api/logs/app.log

# View chatbot service logs
tail -f llm_chatbot_example/logs/app.log
```

## Contributing

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For support and questions:

1. Check the troubleshooting section
2. Review the API documentation
3. Examine the example implementations
4. Create an issue in the project repository

