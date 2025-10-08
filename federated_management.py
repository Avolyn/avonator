from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
import os
import sys
import threading
import subprocess

# Add the parent directory to the path to import federated client
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
federated_bp = Blueprint('federated', __name__)

# Global variables for client management
federated_client_process = None
federated_client_thread = None
client_status = {"connected": False, "server_address": None, "client_id": None}

@federated_bp.route('/v1/federated/status', methods=['GET'])
@cross_origin()
def get_federated_status():
    """Get the status of the federated client connection."""
    try:
        # Try to get metrics from the federated client if it's running
        metrics = {}
        try:
            from federated_client import get_federated_client
            federated_client = get_federated_client()
            metrics = federated_client._get_current_metrics()
        except Exception as e:
            logger.debug(f"Could not get federated client metrics: {str(e)}")
        
        return jsonify({
            "status": "success",
            "federated_client": client_status,
            "metrics": metrics
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
    """Connect to a Flower federated learning server."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data or 'server_address' not in data:
            return jsonify({
                "status": "failure",
                "message": "Missing 'server_address' in request body"
            }), 400
        
        server_address = data['server_address']
        client_id = data.get('client_id', f"guardrails-client-{os.getpid()}")
        
        # Check if already connected
        global client_status
        if client_status["connected"]:
            return jsonify({
                "status": "failure",
                "message": f"Already connected to {client_status['server_address']}"
            }), 400
        
        # Start the federated client in a separate thread
        def start_client():
            try:
                import flwr as fl
                from federated_client import get_federated_client
                
                client = get_federated_client(client_id)
                
                logger.info(f"Connecting to Flower server at {server_address}")
                
                # Update status
                client_status["connected"] = True
                client_status["server_address"] = server_address
                client_status["client_id"] = client_id
                
                # Start the client (this will block)
                fl.client.start_client(
                    server_address=server_address,
                    client=client
                )
                
            except Exception as e:
                logger.error(f"Error in federated client: {str(e)}")
                client_status["connected"] = False
                client_status["server_address"] = None
                client_status["client_id"] = None
        
        # Start the client thread
        global federated_client_thread
        federated_client_thread = threading.Thread(target=start_client, daemon=True)
        federated_client_thread.start()
        
        # Give it a moment to start
        import time
        time.sleep(1)
        
        return jsonify({
            "status": "success",
            "message": f"Connecting to federated server at {server_address}",
            "client_id": client_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error connecting to federated server: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error connecting to federated server: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/disconnect', methods=['POST'])
@cross_origin()
def disconnect_from_federated_server():
    """Disconnect from the federated learning server."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        global client_status, federated_client_thread
        
        if not client_status["connected"]:
            return jsonify({
                "status": "failure",
                "message": "Not currently connected to a federated server"
            }), 400
        
        # Update status
        client_status["connected"] = False
        server_address = client_status["server_address"]
        client_status["server_address"] = None
        client_status["client_id"] = None
        
        # Note: Flower clients don't have a clean disconnect mechanism
        # The thread will terminate when the server connection is lost
        
        return jsonify({
            "status": "success",
            "message": f"Disconnected from federated server at {server_address}"
        }), 200
    
    except Exception as e:
        logger.error(f"Error disconnecting from federated server: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error disconnecting from federated server: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/metrics', methods=['GET'])
@cross_origin()
def get_federated_metrics():
    """Get detailed metrics from the federated client."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        from federated_client import get_federated_client
        federated_client = get_federated_client()
        metrics = federated_client._get_current_metrics()
        
        return jsonify({
            "status": "success",
            "metrics": metrics,
            "client_status": client_status
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting federated metrics: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting federated metrics: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/policies', methods=['GET'])
@cross_origin()
def get_federated_policies():
    """Get the current federated policies and version."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        from federated_client import get_federated_client
        federated_client = get_federated_client()
        
        # Get current policies from the client
        policy_params = federated_client.get_parameters({})
        
        if policy_params:
            import pickle
            policy_data = pickle.loads(policy_params[0])
            
            return jsonify({
                "status": "success",
                "policy_data": policy_data,
                "client_status": client_status
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": "No policy data available"
            }), 404
    
    except Exception as e:
        logger.error(f"Error getting federated policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting federated policies: {str(e)}"
        }), 500

@federated_bp.route('/v1/federated/reset-metrics', methods=['POST'])
@cross_origin()
def reset_federated_metrics():
    """Reset the federated client metrics."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        from federated_client import get_federated_client
        federated_client = get_federated_client()
        
        # Reset metrics
        with federated_client.metrics_lock:
            federated_client.validation_metrics = {
                "total_validations": 0,
                "failed_validations": 0,
                "validation_types": {},
                "policy_version": federated_client.policy_version
            }
        
        return jsonify({
            "status": "success",
            "message": "Federated client metrics reset successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error resetting federated metrics: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error resetting federated metrics: {str(e)}"
        }), 500

