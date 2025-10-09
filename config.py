"""
Configuration file for FastAPI Guardrails Service
"""

import os
from typing import List, Dict, Any
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    api_key: str = Field(default="default-api-key-change-in-production", env="GUARDRAILS_API_KEY")
    debug: bool = Field(default=False, env="DEBUG")
    max_text_length: int = Field(default=10000, env="MAX_TEXT_LENGTH")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # CORS Configuration
    enable_cors: bool = Field(default=True, env="ENABLE_CORS")
    allowed_origins: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # NLP Model Configuration
    spacy_model: str = Field(default="en_core_web_sm", env="SPACY_MODEL")
    stanza_model: str = Field(default="en", env="STANZA_MODEL")
    huggingface_model: str = Field(default="unitary/toxic-bert", env="HUGGINGFACE_MODEL")
    
    # Model Loading Configuration
    load_models_on_startup: bool = Field(default=True, env="LOAD_MODELS_ON_STARTUP")
    model_cache_dir: str = Field(default="./models", env="MODEL_CACHE_DIR")
    
    # Validation Configuration
    default_guardrail: str = Field(default="default", env="DEFAULT_GUARDRAIL")
    max_validation_time: float = Field(default=30.0, env="MAX_VALIDATION_TIME")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    
    # Rate Limiting (if implemented)
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Guardrail configurations
GUARDRAIL_CONFIGS = {
    "default": {
        "description": "Default guardrail with basic NLP validation",
        "validators": [
            {
                "name": "length_check",
                "max_length": 1000,
                "on_fail": "exception",
                "description": "Validates text length does not exceed maximum"
            },
            {
                "name": "toxicity_check",
                "threshold": 0.7,
                "on_fail": "exception",
                "description": "Detects toxic content using ML models"
            },
            {
                "name": "sentiment_check",
                "threshold": -0.5,
                "on_fail": "log",
                "description": "Checks for overly negative sentiment"
            }
        ]
    },
    
    "strict": {
        "description": "Strict content moderation for sensitive applications",
        "validators": [
            {
                "name": "length_check",
                "max_length": 500,
                "on_fail": "exception",
                "description": "Strict length limits"
            },
            {
                "name": "toxicity_check",
                "threshold": 0.3,
                "on_fail": "exception",
                "description": "Very sensitive toxicity detection"
            },
            {
                "name": "sentiment_check",
                "threshold": -0.3,
                "on_fail": "exception",
                "description": "Strict sentiment requirements"
            },
            {
                "name": "pii_detection",
                "on_fail": "filter",
                "description": "Detects and redacts personally identifiable information"
            }
        ]
    },
    
    "permissive": {
        "description": "Permissive content validation for open platforms",
        "validators": [
            {
                "name": "length_check",
                "max_length": 2000,
                "on_fail": "log",
                "description": "Basic length validation"
            },
            {
                "name": "toxicity_check",
                "threshold": 0.9,
                "on_fail": "log",
                "description": "Only flag extremely toxic content"
            }
        ]
    },
    
    "content_moderation": {
        "description": "Comprehensive content moderation",
        "validators": [
            {
                "name": "length_check",
                "max_length": 1500,
                "on_fail": "exception",
                "description": "Text length validation"
            },
            {
                "name": "toxicity_check",
                "threshold": 0.5,
                "on_fail": "exception",
                "description": "Moderate toxicity detection"
            },
            {
                "name": "sentiment_check",
                "threshold": -0.4,
                "on_fail": "log",
                "description": "Sentiment analysis"
            },
            {
                "name": "pii_detection",
                "on_fail": "filter",
                "description": "PII detection and redaction"
            }
        ]
    },
    
    "customer_service": {
        "description": "Guardrails for customer service applications",
        "validators": [
            {
                "name": "length_check",
                "max_length": 3000,
                "on_fail": "exception",
                "description": "Allow longer customer messages"
            },
            {
                "name": "toxicity_check",
                "threshold": 0.6,
                "on_fail": "log",
                "description": "Detect customer frustration"
            },
            {
                "name": "sentiment_check",
                "threshold": -0.6,
                "on_fail": "log",
                "description": "Monitor customer satisfaction"
            },
            {
                "name": "pii_detection",
                "on_fail": "filter",
                "description": "Protect customer privacy"
            }
        ]
    }
}

# Validator-specific configurations
VALIDATOR_CONFIGS = {
    "length_check": {
        "default_max_length": 1000,
        "absolute_max_length": 10000
    },
    
    "toxicity_check": {
        "default_threshold": 0.7,
        "model_options": [
            "unitary/toxic-bert",
            "facebook/roberta-hate-speech-dynabench-r4-target",
            "microsoft/DialoGPT-medium"
        ]
    },
    
    "sentiment_check": {
        "default_threshold": -0.5,
        "model_options": [
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "nlptown/bert-base-multilingual-uncased-sentiment",
            "distilbert-base-uncased-finetuned-sst-2-english"
        ]
    },
    
    "pii_detection": {
        "spacy_entities": ["PERSON", "ORG", "GPE", "EMAIL", "PHONE"],
        "redaction_patterns": {
            "PERSON": "[PERSON_REDACTED]",
            "ORG": "[ORGANIZATION_REDACTED]",
            "GPE": "[LOCATION_REDACTED]",
            "EMAIL": "[EMAIL_REDACTED]",
            "PHONE": "[PHONE_REDACTED]"
        }
    }
}

# Model loading configurations
MODEL_CONFIGS = {
    "spacy": {
        "models": {
            "en_core_web_sm": {
                "size": "small",
                "description": "Small English model with basic NER",
                "download_command": "python -m spacy download en_core_web_sm"
            },
            "en_core_web_md": {
                "size": "medium",
                "description": "Medium English model with word vectors",
                "download_command": "python -m spacy download en_core_web_md"
            },
            "en_core_web_lg": {
                "size": "large",
                "description": "Large English model with word vectors",
                "download_command": "python -m spacy download en_core_web_lg"
            }
        }
    },
    
    "stanza": {
        "models": {
            "en": {
                "description": "English language processing",
                "processors": "tokenize,pos,lemma,depparse,sentiment"
            },
            "es": {
                "description": "Spanish language processing",
                "processors": "tokenize,pos,lemma,depparse,sentiment"
            },
            "fr": {
                "description": "French language processing",
                "processors": "tokenize,pos,lemma,depparse,sentiment"
            }
        }
    },
    
    "huggingface": {
        "toxicity_models": [
            "unitary/toxic-bert",
            "facebook/roberta-hate-speech-dynabench-r4-target",
            "microsoft/DialoGPT-medium"
        ],
        "sentiment_models": [
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "nlptown/bert-base-multilingual-uncased-sentiment",
            "distilbert-base-uncased-finetuned-sst-2-english"
        ]
    }
}

# Create settings instance
settings = Settings()

# Export commonly used configurations
API_KEY = settings.api_key
DEBUG = settings.debug
MAX_TEXT_LENGTH = settings.max_text_length
HOST = settings.host
PORT = settings.port
WORKERS = settings.workers
ENABLE_CORS = settings.enable_cors
ALLOWED_ORIGINS = settings.allowed_origins
ALLOWED_HOSTS = settings.allowed_hosts
SPACY_MODEL = settings.spacy_model
STANZA_MODEL = settings.stanza_model
HUGGINGFACE_MODEL = settings.huggingface_model