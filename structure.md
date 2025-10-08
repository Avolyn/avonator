# Project Structure

This document provides an overview of the complete Guardrails AI API solution structure.

## Root Directory Structure

```
guardrails-ai-solution/
├── README.md                    # Main project documentation
├── DEPLOYMENT_GUIDE.md          # Comprehensive deployment guide
├── project_structure.md         # This file
├── guardrails_api/              # Main guardrails API service
├── llm_chatbot_example/         # Example chatbot integration
├── config.py                    # Shared configuration
├── plugin_system.py             # Plugin architecture implementation
└── docker-compose.yml           # Docker deployment configuration
```

## Guardrails API Service (`guardrails_api/`)

```
guardrails_api/
├── src/
│   ├── main.py                  # Flask application entry point
│   ├── models/                  # Database models (if needed)
│   │   └── user.py
│   ├── routes/                  # API route blueprints
│   │   ├── guardrails.py        # Main guardrails validation endpoints
│   │   ├── plugin_management.py # Plugin management endpoints
│   │   └── user.py              # User management (template)
│   ├── static/                  # Static files
│   │   └── index.html           # Basic API test interface
│   └── database/                # Database files
│       └── app.db
├── venv/                        # Python virtual environment
├── requirements.txt             # Python dependencies
├── config.py                    # Configuration settings
├── plugin_system.py             # Plugin system implementation
└── gunicorn.conf.py             # Production server configuration
```

## LLM Chatbot Example (`llm_chatbot_example/`)

```
llm_chatbot_example/
├── src/
│   ├── main.py                  # Flask application entry point
│   ├── models/                  # Database models
│   │   └── user.py
│   ├── routes/                  # API route blueprints
│   │   ├── chatbot.py           # Main chatbot endpoints
│   │   └── user.py              # User management (template)
│   ├── static/                  # Static files and web interface
│   │   ├── index.html           # Default template interface
│   │   └── chatbot.html         # Interactive chatbot interface
│   └── database/                # Database files
│       └── app.db
├── venv/                        # Python virtual environment
├── requirements.txt             # Python dependencies
└── gunicorn.conf.py             # Production server configuration
```

## Key Components

### 1. Guardrails API Service

**Purpose**: Standalone microservice providing text validation capabilities

**Key Files**:
- `src/main.py` - Flask application with CORS and blueprint registration
- `src/routes/guardrails.py` - Main validation endpoints using plugin system
- `src/routes/plugin_management.py` - Plugin management and switching
- `config.py` - Guardrail configurations and validator settings
- `plugin_system.py` - Abstract plugin interface and implementations

**API Endpoints**:
- `GET /api/v1/guardrails/health` - Service health check
- `POST /api/v1/guardrails/validate` - Text validation
- `GET /api/v1/guardrails/configs` - List available guardrail configurations
- `GET /api/v1/plugins` - List all plugins
- `POST /api/v1/plugins/switch` - Switch active plugin
- `POST /api/v1/plugins/load` - Load new plugin dynamically

### 2. LLM Chatbot Example

**Purpose**: Demonstrates integration with the guardrails service

**Key Files**:
- `src/main.py` - Flask application setup
- `src/routes/chatbot.py` - Chatbot logic with guardrails integration
- `src/static/chatbot.html` - Interactive web interface

**Features**:
- Input validation before LLM processing
- Output validation after LLM response
- Configurable guardrail profiles
- Real-time validation feedback
- Health monitoring of dependencies

### 3. Plugin System

**Purpose**: Enables easy replacement of guardrails implementations

**Components**:
- `GuardrailsPlugin` - Abstract base class
- `MockGuardrailsPlugin` - Default implementation with mock validators
- `OpenAIModerationPlugin` - Example external API integration
- `PluginManager` - Handles plugin registration and switching

**Benefits**:
- Standardized interface across implementations
- Hot-swapping of guardrails providers
- Easy integration of new validation services
- Consistent API contract regardless of backend

### 4. Configuration System

**Purpose**: Centralized configuration management

**Features**:
- Environment-based configuration
- Multiple guardrail profiles
- Validator-specific settings
- Plugin configuration support

**Guardrail Profiles**:
- `default` - Basic validation (length + profanity)
- `toxic_language_guard` - Toxic language detection
- `pii_redaction_guard` - PII detection and redaction
- `content_moderation` - Comprehensive content filtering

## Data Flow

```
User Input
    ↓
LLM Chatbot Service
    ↓
[Input Validation]
    ↓
Guardrails API Service
    ↓
Active Plugin (Mock/OpenAI/Custom)
    ↓
Validation Results
    ↓
LLM Processing (if input valid)
    ↓
[Output Validation]
    ↓
Guardrails API Service
    ↓
Final Response to User
```

## Integration Points

### 1. HTTP API Integration
- RESTful endpoints for validation
- JSON request/response format
- API key authentication
- CORS support for web applications

### 2. Plugin Integration
- Abstract interface for new implementations
- Configuration-driven plugin selection
- Runtime plugin switching
- Health monitoring

### 3. Configuration Integration
- Environment variable support
- File-based configuration
- Dynamic configuration updates
- Profile-based settings

## Extensibility

### Adding New Validators

1. **In Mock Plugin**: Add validator logic to `MockGuardrailsPlugin`
2. **In Configuration**: Define validator settings in `config.py`
3. **New Plugin**: Create new plugin class implementing `GuardrailsPlugin`

### Adding New Guardrail Profiles

1. Add profile to `GUARDRAIL_CONFIGS` in `config.py`
2. Define validator combinations and settings
3. Test with validation endpoint

### Custom Plugin Development

1. Inherit from `GuardrailsPlugin`
2. Implement required methods:
   - `initialize(config)`
   - `validate_text(text, guardrail_name, context)`
   - `get_available_guardrails()`
   - `health_check()`
3. Register with plugin manager
4. Configure and test

## Testing Strategy

### Unit Tests
- Individual validator logic
- Plugin interface compliance
- Configuration parsing
- API endpoint responses

### Integration Tests
- End-to-end validation flow
- Plugin switching functionality
- Service health checks
- Error handling scenarios

### Performance Tests
- Validation response times
- Concurrent request handling
- Memory usage under load
- Plugin switching overhead

## Security Considerations

### API Security
- API key authentication
- Input validation and sanitization
- Rate limiting
- CORS configuration

### Data Security
- No persistent storage of validated text
- Secure configuration management
- Audit logging
- Error message sanitization

### Infrastructure Security
- Container security best practices
- Network segmentation
- Secrets management
- Regular security updates

## Monitoring and Observability

### Health Checks
- Service availability
- Plugin health status
- Dependency connectivity
- Resource utilization

### Metrics
- Request/response times
- Validation success/failure rates
- Plugin performance
- Error rates by type

### Logging
- Structured JSON logging
- Request tracing
- Error details
- Performance metrics

## Deployment Options

### Development
- Local Flask development servers
- File-based configuration
- Mock plugins for testing

### Production
- Gunicorn WSGI server
- Environment-based configuration
- Production-ready plugins
- Load balancing and scaling

### Containerized
- Docker images for each service
- Docker Compose orchestration
- Health checks and restart policies
- Volume mounts for configuration

### Cloud Native
- Kubernetes deployments
- Service mesh integration
- Auto-scaling capabilities
- Cloud provider integrations

This structure provides a solid foundation for a production-ready guardrails solution while maintaining flexibility for future enhancements and integrations.

