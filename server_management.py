from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
import os
import sys
import threading

# Add the parent directory to the path to import federated server
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from federated_server import get_federated_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
server_bp = Blueprint('server', __name__)

# Simple API key for demonstration (in production, use proper authentication)
API_KEY = "federated-server-key-change-in-production"

@server_bp.route('/v1/server/status', methods=['GET'])
@cross_origin()
def get_server_status():
    """Get the status of the federated server."""
    try:
        server = get_federated_server()
        status = server.get_server_status()
        
        return jsonify({
            "status": "success",
            "server": status
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting server status: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting server status: {str(e)}"
        }), 500

@server_bp.route('/v1/server/start', methods=['POST'])
@cross_origin()
def start_server():
    """Start the federated learning server."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json() or {}
        server_address = data.get('server_address', '0.0.0.0:8080')
        num_rounds = data.get('num_rounds', 10)
        
        server = get_federated_server(server_address, num_rounds)
        
        if server.is_running:
            return jsonify({
                "status": "failure",
                "message": "Server is already running"
            }), 400
        
        # Start server in non-blocking mode
        server.start_server(blocking=False)
        
        return jsonify({
            "status": "success",
            "message": f"Federated server started on {server_address}",
            "server_address": server_address,
            "num_rounds": num_rounds
        }), 200
    
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error starting server: {str(e)}"
        }), 500

@server_bp.route('/v1/server/stop', methods=['POST'])
@cross_origin()
def stop_server():
    """Stop the federated learning server."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        server = get_federated_server()
        
        if not server.is_running:
            return jsonify({
                "status": "failure",
                "message": "Server is not currently running"
            }), 400
        
        server.stop_server()
        
        return jsonify({
            "status": "success",
            "message": "Federated server stopped"
        }), 200
    
    except Exception as e:
        logger.error(f"Error stopping server: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error stopping server: {str(e)}"
        }), 500

@server_bp.route('/v1/server/policies', methods=['GET'])
@cross_origin()
def get_server_policies():
    """Get current policies from the server."""
    try:
        server = get_federated_server()
        
        policies_info = {
            "version": server.strategy.policy_version,
            "policies": server.strategy.current_policies,
            "policies_count": len(server.strategy.current_policies)
        }
        
        return jsonify({
            "status": "success",
            "policies": policies_info
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting server policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting server policies: {str(e)}"
        }), 500

@server_bp.route('/v1/server/policies', methods=['POST'])
@cross_origin()
def update_server_policies():
    """Update policies on the server."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data or 'policies' not in data:
            return jsonify({
                "status": "failure",
                "message": "Missing 'policies' in request body"
            }), 400
        
        new_policies = data['policies']
        
        server = get_federated_server()
        success = server.update_policies(new_policies)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Policies updated to version {server.strategy.policy_version}",
                "policy_version": server.strategy.policy_version
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": "Failed to update policies"
            }), 400
    
    except Exception as e:
        logger.error(f"Error updating server policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error updating server policies: {str(e)}"
        }), 500

@server_bp.route('/v1/server/clients', methods=['GET'])
@cross_origin()
def get_client_metrics():
    """Get metrics from all connected clients."""
    try:
        server = get_federated_server()
        client_metrics = server.strategy.get_client_metrics()
        
        return jsonify({
            "status": "success",
            "client_metrics": client_metrics,
            "total_clients": len(client_metrics)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting client metrics: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting client metrics: {str(e)}"
        }), 500

@server_bp.route('/v1/server/health', methods=['GET'])
@cross_origin()
def server_health():
    """Health check endpoint for the server management API."""
    return jsonify({
        "service": "federated-server-management",
        "status": "healthy",
        "version": "1.0.0"
    }), 200

