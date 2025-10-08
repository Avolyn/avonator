from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import requests
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
federated_bp = Blueprint('federated', __name__)

# Configuration
GUARDRAILS_API_BASE = os.environ.get('GUARDRAILS_API_BASE', 'http://localhost:5002')
GUARDRAILS_API_KEY = os.environ.get('GUARDRAILS_API_KEY', 'default-api-key-change-in-production')

@federated_bp.route('/v1/federated/status', methods=['GET'])
@cross_origin()
def get_federated_status():
    """Get the status of the federated guardrails system."""
    try:
        # Get guardrails service status
        guardrails_status = {}
        try:
            response = requests.get(
                f"{GUARDRAILS_API_BASE}/api/v1/guardrails/health",
                timeout=5
            )
            if response.status_code == 200:
                guardrails_status = response.json()
        except Exception as e:
            logger.debug(f"Could not get guardrails status: {str(e)}")
            guardrails_status = {"status": "unreachable", "error": str(e)}
        
        # Get federated client status
        federated_client_status = {}
        try:
            response = requests.get(
                f"{GUARDRAILS_API_BASE}/api/v1/federated/status",
                timeout=5
            )
            if response.status_code == 200:
                federated_client_status = response.json()
        except Exception as e:
            logger.debug(f"Could not get federated client status: {str(e)}")
            federated_client_status = {"status": "unreachable", "error": str(e)}
        
        return jsonify({
            "status": "success",
            "chatbot_service": {
                "status": "healthy",
                "service": "llm-chatbot-with-federated-guardrails",
                "version": "1.0.0"
            },
            "guardrails_service": guardrails_status,
            "federated_client": federated_client_status
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting federated status: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting federated status: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/connect', methods=['POST'])
@cross_origin()
def connect_to_federated_server():
    """Connect the guardrails client to a federated server."""
    try:
        data = request.get_json()
        if not data or 'server_address' not in data:
            return jsonify({
                "status": "failure",
                "message": "Missing 'server_address' in request body"
            }), 400
        
        # Forward the connection request to the guardrails service
        response = requests.post(
            f"{GUARDRAILS_API_BASE}/api/v1/federated/connect",
            json=data,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': GUARDRAILS_API_KEY
            },
            timeout=30
        )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error connecting to federated server: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error connecting to federated server: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/disconnect', methods=['POST'])
@cross_origin()
def disconnect_from_federated_server():
    """Disconnect the guardrails client from the federated server."""
    try:
        # Forward the disconnection request to the guardrails service
        response = requests.post(
            f"{GUARDRAILS_API_BASE}/api/v1/federated/disconnect",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': GUARDRAILS_API_KEY
            },
            timeout=30
        )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error disconnecting from federated server: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error disconnecting from federated server: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/metrics', methods=['GET'])
@cross_origin()
def get_federated_metrics():
    """Get federated learning metrics from the guardrails client."""
    try:
        response = requests.get(
            f"{GUARDRAILS_API_BASE}/api/v1/federated/metrics",
            headers={
                'X-API-Key': GUARDRAILS_API_KEY
            },
            timeout=10
        )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error getting federated metrics: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting federated metrics: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/policies', methods=['GET'])
@cross_origin()
def get_federated_policies():
    """Get current federated policies from the guardrails client."""
    try:
        response = requests.get(
            f"{GUARDRAILS_API_BASE}/api/v1/federated/policies",
            headers={
                'X-API-Key': GUARDRAILS_API_KEY
            },
            timeout=10
        )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error getting federated policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting federated policies: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/reset-metrics', methods=['POST'])
@cross_origin()
def reset_federated_metrics():
    """Reset federated learning metrics on the guardrails client."""
    try:
        response = requests.post(
            f"{GUARDRAILS_API_BASE}/api/v1/federated/reset-metrics",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': GUARDRAILS_API_KEY
            },
            timeout=10
        )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error resetting federated metrics: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error resetting federated metrics: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/demo', methods=['POST'])
@cross_origin()
def federated_demo():
    """
    Demonstrate federated guardrails by showing how policies are applied
    and how metrics are collected across the federated system.
    """
    try:
        data = request.get_json() or {}
        test_messages = data.get('test_messages', [
            "Hello, how are you?",
            "This is a damn test message",  # Contains profanity
            "Contact me at john.doe@email.com",  # Contains PII
            "You are stupid and worthless"  # Toxic content
        ])
        
        results = []
        
        for message in test_messages:
            # Test the message through the chatbot (which uses guardrails)
            try:
                chat_response = requests.post(
                    f"http://localhost:5003/api/v1/chat",
                    json={"message": message, "guardrail_config": "strict"},
                    timeout=10
                )
                
                result = {
                    "input_message": message,
                    "chat_response": chat_response.json() if chat_response.status_code == 200 else None,
                    "status_code": chat_response.status_code
                }
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    "input_message": message,
                    "error": str(e),
                    "status_code": 500
                })
        
        # Get current federated metrics
        try:
            metrics_response = requests.get(
                f"{GUARDRAILS_API_BASE}/api/v1/federated/metrics",
                headers={'X-API-Key': GUARDRAILS_API_KEY},
                timeout=10
            )
            
            federated_metrics = metrics_response.json() if metrics_response.status_code == 200 else {}
        except Exception as e:
            federated_metrics = {"error": str(e)}
        
        return jsonify({
            "status": "success",
            "demo_results": results,
            "federated_metrics": federated_metrics,
            "message": "Federated guardrails demo completed. Check the results to see how different types of content are handled."
        }), 200
    
    except Exception as e:
        logger.error(f"Error in federated demo: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error in federated demo: {str(e)}"
        }), 500

