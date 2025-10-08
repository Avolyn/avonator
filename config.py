"""
Configuration file for Guardrails API
This file defines the guardrail configurations that can be used by the API.
"""

import os

# API Configuration
API_KEY = os.environ.get('GUARDRAILS_API_KEY', 'default-api-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# Guardrail Configurations
# Each configuration defines a set of validators and their parameters
GUARDRAIL_CONFIGS = {
    "default": {
        "description": "Default guardrail with basic text validation",
        "validators": [
            {
                "name": "length_check",
                "max_length": 1000,
                "on_fail": "exception",
                "description": "Validates text length does not exceed maximum"
            },
            {
                "name": "profanity_check",
                "threshold": 0.8,
                "on_fail": "filter",
                "description": "Detects and optionally filters profanity"
            }
        ]
    },
    
    "toxic_language_guard": {
        "description": "Specialized guardrail for detecting toxic language",
        "validators": [
            {
                "name": "toxic_language",
                "threshold": 0.5,
                "on_fail": "exception",
                "description": "Detects toxic language patterns"
            },
            {
                "name": "length_check",
                "max_length": 2000,
                "on_fail": "exception",
                "description": "Validates text length"
            }
        ]
    },
    
    "pii_redaction_guard": {
        "description": "Guardrail for detecting and redacting PII",
        "validators": [
            {
                "name": "pii_detection",
                "redact": True,
                "on_fail": "filter",
                "description": "Detects and redacts personally identifiable information"
            },
            {
                "name": "length_check",
                "max_length": 5000,
                "on_fail": "exception",
                "description": "Validates text length"
            }
        ]
    },
    
    "content_moderation": {
        "description": "Comprehensive content moderation guardrail",
        "validators": [
            {
                "name": "toxic_language",
                "threshold": 0.3,
                "on_fail": "exception",
                "description": "Strict toxic language detection"
            },
            {
                "name": "profanity_check",
                "threshold": 0.6,
                "on_fail": "filter",
                "description": "Profanity detection and filtering"
            },
            {
                "name": "pii_detection",
                "redact": True,
                "on_fail": "filter",
                "description": "PII detection and redaction"
            },
            {
                "name": "length_check",
                "max_length": 1500,
                "on_fail": "exception",
                "description": "Text length validation"
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
    
    "profanity_check": {
        "default_threshold": 0.8,
        "profane_words": [
            "damn", "hell", "shit", "fuck", "bitch", "ass", "crap"
        ]
    },
    
    "toxic_language": {
        "default_threshold": 0.5,
        "toxic_phrases": [
            "you're stupid", "shut up", "go die", "kill yourself",
            "you suck", "hate you", "worthless", "loser"
        ]
    },
    
    "pii_detection": {
        "patterns": {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}-\d{3}-\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
        },
        "redaction_text": {
            "email": "[EMAIL_REDACTED]",
            "phone": "[PHONE_REDACTED]",
            "ssn": "[SSN_REDACTED]",
            "credit_card": "[CARD_REDACTED]"
        }
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

