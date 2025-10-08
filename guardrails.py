from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, Any, List
import logging
import os
import sys
import re

# Add the parent directory to the path to import config and plugin system
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import GUARDRAIL_CONFIGS, VALIDATOR_CONFIGS, API_KEY
from plugin_system import plugin_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
guardrails_bp = Blueprint('guardrails', __name__)

# Pydantic models for request/response validation
class ValidationContext(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ValidationRequest(BaseModel):
    text: str
    context: Optional[ValidationContext] = None
    guardrail_name: Optional[str] = "default"

class ValidatorResult(BaseModel):
    validator_name: str
    status: str  # "pass" or "fail"
    message: str
    on_fail_action: str

class ValidationResponse(BaseModel):
    status: str  # "success" or "failure"
    message: str
    valid: bool
    validations: List[ValidatorResult]
    processed_text: Optional[str] = None

def validate_text_with_mock_guardrails(text: str, guardrail_name: str, context: Optional[ValidationContext] = None) -> ValidationResponse:
    """
    Mock implementation of text validation using guardrails.
    In a real implementation, this would use the actual Guardrails AI library.
    """
    try:
        config = GUARDRAIL_CONFIGS.get(guardrail_name, GUARDRAIL_CONFIGS["default"])
        validations = []
        all_passed = True
        processed_text = text
        
        for validator_config in config["validators"]:
            validator_name = validator_config["name"]
            on_fail_action = validator_config["on_fail"]
            
            # Mock validation logic
            if validator_name == "length_check":
                max_length = validator_config.get("max_length", 1000)
                if len(text) > max_length:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="fail",
                        message=f"Text length ({len(text)}) exceeds maximum allowed ({max_length})",
                        on_fail_action=on_fail_action
                    ))
                    all_passed = False
                else:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="pass",
                        message="Text length is within acceptable limits",
                        on_fail_action=on_fail_action
                    ))
            
            elif validator_name == "profanity_check":
                # Use profanity words from config
                profane_words = VALIDATOR_CONFIGS["profanity_check"]["profane_words"]
                found_profanity = any(word in text.lower() for word in profane_words)
                if found_profanity:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="fail",
                        message="Profanity detected in text",
                        on_fail_action=on_fail_action
                    ))
                    all_passed = False
                    if on_fail_action == "filter":
                        # Mock text filtering
                        for word in profane_words:
                            processed_text = processed_text.replace(word, "*" * len(word))
                else:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="pass",
                        message="No profanity detected",
                        on_fail_action=on_fail_action
                    ))
            
            elif validator_name == "toxic_language":
                # Use toxic phrases from config
                toxic_phrases = VALIDATOR_CONFIGS["toxic_language"]["toxic_phrases"]
                found_toxic = any(phrase in text.lower() for phrase in toxic_phrases)
                if found_toxic:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="fail",
                        message="Toxic language detected",
                        on_fail_action=on_fail_action
                    ))
                    all_passed = False
                else:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="pass",
                        message="No toxic language detected",
                        on_fail_action=on_fail_action
                    ))
            
            elif validator_name == "pii_detection":
                # Use PII patterns from config
                patterns = VALIDATOR_CONFIGS["pii_detection"]["patterns"]
                redaction_text = VALIDATOR_CONFIGS["pii_detection"]["redaction_text"]
                
                pii_found = {}
                for pii_type, pattern in patterns.items():
                    matches = re.findall(pattern, text)
                    if matches:
                        pii_found[pii_type] = len(matches)
                
                if pii_found:
                    pii_summary = ", ".join([f"{count} {pii_type}(s)" for pii_type, count in pii_found.items()])
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="fail",
                        message=f"PII detected: {pii_summary}",
                        on_fail_action=on_fail_action
                    ))
                    all_passed = False
                    if validator_config.get("redact", False):
                        # Redact PII using config patterns
                        for pii_type, pattern in patterns.items():
                            processed_text = re.sub(pattern, redaction_text[pii_type], processed_text)
                else:
                    validations.append(ValidatorResult(
                        validator_name=validator_name,
                        status="pass",
                        message="No PII detected",
                        on_fail_action=on_fail_action
                    ))
        
        return ValidationResponse(
            status="success",
            message="Validation completed successfully",
            valid=all_passed,
            validations=validations,
            processed_text=processed_text if processed_text != text else None
        )
    
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return ValidationResponse(
            status="failure",
            message=f"Internal error during validation: {str(e)}",
            valid=False,
            validations=[],
            processed_text=None
        )

@guardrails_bp.route('/v1/guardrails/validate', methods=['POST'])
@cross_origin()
def validate_text():
    """
    Validate text using configured guardrails.
    """
    try:
        # Validate request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Parse and validate request using Pydantic
        try:
            validation_request = ValidationRequest(**request_data)
        except ValidationError as e:
            return jsonify({"error": "Invalid request format", "details": e.errors()}), 400
        
        # Check API key (simple implementation)
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        
        # Perform validation using the active plugin
        active_plugin = plugin_manager.get_active_plugin()
        if not active_plugin:
            return jsonify({
                "status": "failure",
                "message": "No active guardrails plugin available",
                "valid": False,
                "validations": []
            }), 503
        
        result = active_plugin.validate_text(
            text=validation_request.text,
            guardrail_name=validation_request.guardrail_name,
            context=validation_request.context.model_dump() if validation_request.context else None
        )
        
        # Convert plugin response to API response format
        api_response = {
            "status": result.status,
            "message": result.message,
            "valid": result.valid,
            "validations": [
                {
                    "validator_name": v.validator_name,
                    "status": v.status,
                    "message": v.message,
                    "on_fail_action": v.on_fail_action
                }
                for v in result.validations
            ],
            "processed_text": result.processed_text,
            "plugin_info": {
                "name": result.plugin_name,
                "execution_time_ms": result.execution_time_ms
            }
        }
        
        # Update federated client metrics if available
        try:
            from federated_client import get_federated_client
            federated_client = get_federated_client()
            federated_client.update_validation_metrics(api_response)
        except Exception as e:
            logger.debug(f"Could not update federated metrics: {str(e)}")
        
        # Return response
        return jsonify(api_response), 200
    
    except Exception as e:
        logger.error(f"Unexpected error in validate_text endpoint: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": "Internal server error",
            "valid": False,
            "validations": []
        }), 500

@guardrails_bp.route('/v1/guardrails/health', methods=['GET'])
@cross_origin()
def health_check():
    """
    Health check endpoint.
    """
    return jsonify({
        "status": "healthy",
        "service": "guardrails-api",
        "version": "1.0.0"
    }), 200

@guardrails_bp.route('/v1/guardrails/configs', methods=['GET'])
@cross_origin()
def list_guardrail_configs():
    """
    List available guardrail configurations.
    """
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    active_plugin = plugin_manager.get_active_plugin()
    if not active_plugin:
        return jsonify({
            "status": "failure",
            "message": "No active guardrails plugin available"
        }), 503
    
    try:
        configs = active_plugin.get_available_guardrails()
        formatted_configs = {}
        for name, config in configs.items():
            formatted_configs[name] = {
                "validators": config.get("validators", []),
                "description": config.get("description", f"Guardrail configuration: {name}")
            }
        
        return jsonify({
            "status": "success",
            "configs": formatted_configs,
            "plugin_info": {
                "name": active_plugin.name,
                "version": active_plugin.version
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting guardrail configs: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting guardrail configs: {str(e)}"
        }), 500

