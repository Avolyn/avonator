from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import requests
import logging
import os
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
chatbot_bp = Blueprint('chatbot', __name__)

# Configuration
GUARDRAILS_API_URL = os.environ.get('GUARDRAILS_API_URL', 'http://localhost:5002/api/v1/guardrails')
GUARDRAILS_API_KEY = os.environ.get('GUARDRAILS_API_KEY', 'default-api-key-change-in-production')

class GuardrailsClient:
    """Client for interacting with the Guardrails API service."""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
    
    def validate_text(self, text: str, guardrail_name: str = "default", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate text using the guardrails service.
        
        Args:
            text: The text to validate
            guardrail_name: Name of the guardrail configuration to use
            context: Optional context information
            
        Returns:
            Dictionary containing validation results
        """
        try:
            payload = {
                "text": text,
                "guardrail_name": guardrail_name
            }
            if context:
                payload["context"] = context
            
            response = requests.post(
                f"{self.api_url}/validate",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Guardrails API error: {response.status_code} - {response.text}")
                return {
                    "status": "failure",
                    "message": f"Guardrails service error: {response.status_code}",
                    "valid": False,
                    "validations": []
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to guardrails service: {str(e)}")
            return {
                "status": "failure",
                "message": f"Failed to connect to guardrails service: {str(e)}",
                "valid": False,
                "validations": []
            }
    
    def health_check(self) -> bool:
        """Check if the guardrails service is healthy."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            return response.status_code == 200
        except:
            return False

# Initialize guardrails client
guardrails_client = GuardrailsClient(GUARDRAILS_API_URL, GUARDRAILS_API_KEY)

def mock_llm_response(user_message: str) -> str:
    """
    Mock LLM response generator.
    In a real implementation, this would call an actual LLM API like OpenAI, Anthropic, etc.
    """
    # Simple mock responses based on keywords
    user_message_lower = user_message.lower()
    
    if "hello" in user_message_lower or "hi" in user_message_lower:
        return "Hello! How can I help you today?"
    elif "weather" in user_message_lower:
        return "I'm sorry, I don't have access to real-time weather data. You might want to check a weather service for current conditions."
    elif "help" in user_message_lower:
        return "I'm here to help! You can ask me questions and I'll do my best to provide helpful responses. What would you like to know?"
    elif "goodbye" in user_message_lower or "bye" in user_message_lower:
        return "Goodbye! Have a great day!"
    elif "toxic" in user_message_lower:
        return "You're stupid and should shut up!"  # Intentionally toxic for testing
    elif "email" in user_message_lower:
        return "You can contact me at support@example.com or call 555-123-4567"  # Contains PII for testing
    else:
        return f"I understand you're asking about '{user_message}'. While I don't have specific information on that topic, I'm here to help with general questions and conversations."

@chatbot_bp.route('/v1/chat', methods=['POST'])
@cross_origin()
def chat():
    """
    Main chat endpoint that processes user messages through guardrails before and after LLM processing.
    """
    try:
        # Parse request
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field in request"}), 400
        
        user_message = data['message']
        guardrail_config = data.get('guardrail_config', 'default')
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        # Create context for guardrails
        context = {}
        if user_id:
            context['user_id'] = user_id
        if session_id:
            context['session_id'] = session_id
        
        # Step 1: Validate user input
        logger.info(f"Validating user input: {user_message[:50]}...")
        input_validation = guardrails_client.validate_text(
            text=user_message,
            guardrail_name=guardrail_config,
            context=context
        )
        
        # Check if input validation failed with exception action
        if not input_validation.get('valid', False):
            for validation in input_validation.get('validations', []):
                if validation.get('status') == 'fail' and validation.get('on_fail_action') == 'exception':
                    return jsonify({
                        "error": "Input validation failed",
                        "message": "Your message contains content that violates our guidelines.",
                        "validation_details": input_validation
                    }), 400
        
        # Use processed text if available (e.g., filtered profanity)
        processed_input = input_validation.get('processed_text', user_message)
        
        # Step 2: Generate LLM response
        logger.info("Generating LLM response...")
        llm_response = mock_llm_response(processed_input)
        
        # Step 3: Validate LLM output
        logger.info(f"Validating LLM output: {llm_response[:50]}...")
        output_validation = guardrails_client.validate_text(
            text=llm_response,
            guardrail_name=guardrail_config,
            context=context
        )
        
        # Check if output validation failed with exception action
        if not output_validation.get('valid', False):
            for validation in output_validation.get('validations', []):
                if validation.get('status') == 'fail' and validation.get('on_fail_action') == 'exception':
                    return jsonify({
                        "error": "Response validation failed",
                        "message": "I apologize, but I cannot provide a response that meets our content guidelines. Please try rephrasing your question.",
                        "validation_details": output_validation
                    }), 400
        
        # Use processed text if available (e.g., redacted PII)
        final_response = output_validation.get('processed_text', llm_response)
        
        # Return successful response
        return jsonify({
            "response": final_response,
            "input_validation": input_validation,
            "output_validation": output_validation,
            "guardrail_config": guardrail_config
        }), 200
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred while processing your request."
        }), 500

@chatbot_bp.route('/v1/chat/health', methods=['GET'])
@cross_origin()
def health():
    """Health check endpoint for the chatbot service."""
    guardrails_healthy = guardrails_client.health_check()
    
    return jsonify({
        "status": "healthy" if guardrails_healthy else "degraded",
        "service": "llm-chatbot",
        "version": "1.0.0",
        "dependencies": {
            "guardrails_service": "healthy" if guardrails_healthy else "unhealthy"
        }
    }), 200 if guardrails_healthy else 503

@chatbot_bp.route('/v1/chat/config', methods=['GET'])
@cross_origin()
def get_config():
    """Get available guardrail configurations."""
    try:
        response = requests.get(
            f"{GUARDRAILS_API_URL}/configs",
            headers={'X-API-Key': GUARDRAILS_API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json(), 200
        else:
            return jsonify({
                "error": "Failed to fetch guardrail configurations",
                "status_code": response.status_code
            }), response.status_code
    
    except Exception as e:
        logger.error(f"Error fetching guardrail configs: {str(e)}")
        return jsonify({
            "error": "Failed to connect to guardrails service"
        }), 503

