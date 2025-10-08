from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
import os
import sys

# Add the parent directory to the path to import policy manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from policy_as_code_manager import get_policy_manager
from federated_server import get_federated_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
policy_bp = Blueprint('policy', __name__)

# Simple API key for demonstration
API_KEY = "federated-server-key-change-in-production"

@policy_bp.route('/v1/policies', methods=['GET'])
@cross_origin()
def list_policies():
    """List all policies in the repository."""
    try:
        policy_manager = get_policy_manager()
        policies = policy_manager.list_policies()
        
        # Convert metadata to dict format
        policies_dict = {}
        for name, metadata in policies.items():
            policies_dict[name] = {
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "author": metadata.author,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
                "hash": metadata.hash,
                "dependencies": metadata.dependencies,
                "tags": metadata.tags
            }
        
        return jsonify({
            "status": "success",
            "policies": policies_dict,
            "total_count": len(policies_dict)
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error listing policies: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies/<policy_name>', methods=['GET'])
@cross_origin()
def get_policy(policy_name):
    """Get a specific policy configuration."""
    try:
        version = request.args.get('version')
        
        policy_manager = get_policy_manager()
        policy_data = policy_manager.get_policy(policy_name, version)
        
        if policy_data is None:
            return jsonify({
                "status": "failure",
                "message": f"Policy '{policy_name}' not found"
            }), 404
        
        # Get metadata
        policies = policy_manager.list_policies()
        metadata = policies.get(policy_name)
        
        return jsonify({
            "status": "success",
            "policy": policy_data,
            "metadata": {
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "author": metadata.author,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
                "hash": metadata.hash,
                "dependencies": metadata.dependencies,
                "tags": metadata.tags
            } if metadata else None
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting policy '{policy_name}': {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting policy: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies', methods=['POST'])
@cross_origin()
def create_policy():
    """Create a new policy from template or direct configuration."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "failure",
                "message": "Missing request body"
            }), 400
        
        policy_manager = get_policy_manager()
        
        if 'template_name' in data:
            # Create from template
            policy_name = data.get('policy_name')
            template_name = data.get('template_name')
            template_params = data.get('template_params', {})
            
            if not policy_name:
                return jsonify({
                    "status": "failure",
                    "message": "Missing 'policy_name' for template creation"
                }), 400
            
            result = policy_manager.create_policy_from_template(
                policy_name, template_name, **template_params
            )
        else:
            # Create from direct configuration
            policy_name = data.get('name')
            if not policy_name:
                return jsonify({
                    "status": "failure",
                    "message": "Missing 'name' in policy configuration"
                }), 400
            
            # Validate the policy first
            validation_result = policy_manager.validate_policy(data)
            if not validation_result.valid:
                return jsonify({
                    "status": "failure",
                    "message": "Policy validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }), 400
            
            # Create the policy (this is a simplified approach)
            # In a real implementation, you'd want a proper create_policy method
            result = policy_manager.update_policy(policy_name, data, "major")
        
        if result.valid:
            return jsonify({
                "status": "success",
                "message": f"Policy '{policy_name}' created successfully",
                "metadata": {
                    "name": result.metadata.name,
                    "version": result.metadata.version,
                    "description": result.metadata.description,
                    "author": result.metadata.author,
                    "created_at": result.metadata.created_at,
                    "updated_at": result.metadata.updated_at,
                    "hash": result.metadata.hash,
                    "dependencies": result.metadata.dependencies,
                    "tags": result.metadata.tags
                } if result.metadata else None,
                "warnings": result.warnings
            }), 201
        else:
            return jsonify({
                "status": "failure",
                "message": "Failed to create policy",
                "errors": result.errors,
                "warnings": result.warnings
            }), 400
    
    except Exception as e:
        logger.error(f"Error creating policy: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error creating policy: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies/<policy_name>', methods=['PUT'])
@cross_origin()
def update_policy(policy_name):
    """Update an existing policy."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "failure",
                "message": "Missing request body"
            }), 400
        
        version_increment = data.get('version_increment', 'patch')
        policy_data = data.get('policy_data', data)
        
        policy_manager = get_policy_manager()
        result = policy_manager.update_policy(policy_name, policy_data, version_increment)
        
        if result.valid:
            return jsonify({
                "status": "success",
                "message": f"Policy '{policy_name}' updated successfully",
                "metadata": {
                    "name": result.metadata.name,
                    "version": result.metadata.version,
                    "description": result.metadata.description,
                    "author": result.metadata.author,
                    "created_at": result.metadata.created_at,
                    "updated_at": result.metadata.updated_at,
                    "hash": result.metadata.hash,
                    "dependencies": result.metadata.dependencies,
                    "tags": result.metadata.tags
                } if result.metadata else None,
                "warnings": result.warnings
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": "Failed to update policy",
                "errors": result.errors,
                "warnings": result.warnings
            }), 400
    
    except Exception as e:
        logger.error(f"Error updating policy '{policy_name}': {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error updating policy: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies/validate', methods=['POST'])
@cross_origin()
def validate_policy():
    """Validate a policy configuration without saving it."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "failure",
                "message": "Missing request body"
            }), 400
        
        policy_manager = get_policy_manager()
        result = policy_manager.validate_policy(data)
        
        return jsonify({
            "status": "success" if result.valid else "failure",
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        }), 200
    
    except Exception as e:
        logger.error(f"Error validating policy: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error validating policy: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies/export', methods=['POST'])
@cross_origin()
def export_policies():
    """Export policies for federated distribution."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json() or {}
        policy_names = data.get('policy_names')  # If None, exports all
        
        policy_manager = get_policy_manager()
        exported_data = policy_manager.export_policies_for_federation(policy_names)
        
        return jsonify({
            "status": "success",
            "exported_data": exported_data,
            "exported_count": len(exported_data.get("policies", {}))
        }), 200
    
    except Exception as e:
        logger.error(f"Error exporting policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error exporting policies: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies/import', methods=['POST'])
@cross_origin()
def import_policies():
    """Import policies from federated format."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data or 'federated_data' not in data:
            return jsonify({
                "status": "failure",
                "message": "Missing 'federated_data' in request body"
            }), 400
        
        federated_data = data['federated_data']
        overwrite_existing = data.get('overwrite_existing', False)
        
        policy_manager = get_policy_manager()
        results = policy_manager.import_federated_policies(federated_data, overwrite_existing)
        
        # Summarize results
        successful_imports = [r for r in results if r.valid]
        failed_imports = [r for r in results if not r.valid]
        
        return jsonify({
            "status": "success" if len(failed_imports) == 0 else "partial_success",
            "successful_imports": len(successful_imports),
            "failed_imports": len(failed_imports),
            "results": [
                {
                    "valid": r.valid,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "metadata": {
                        "name": r.metadata.name,
                        "version": r.metadata.version,
                        "description": r.metadata.description
                    } if r.metadata else None
                }
                for r in results
            ]
        }), 200
    
    except Exception as e:
        logger.error(f"Error importing policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error importing policies: {str(e)}"
        }), 500

@policy_bp.route('/v1/policies/distribute', methods=['POST'])
@cross_origin()
def distribute_policies():
    """Distribute policies to federated clients via the Flower server."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json() or {}
        policy_names = data.get('policy_names')  # If None, distributes all
        
        # Export policies for federation
        policy_manager = get_policy_manager()
        exported_data = policy_manager.export_policies_for_federation(policy_names)
        
        if not exported_data.get("policies"):
            return jsonify({
                "status": "failure",
                "message": "No policies to distribute"
            }), 400
        
        # Update the federated server with new policies
        federated_server = get_federated_server()
        
        # Convert exported policies to the format expected by the federated server
        server_policies = {}
        for policy_name, policy_config in exported_data["policies"].items():
            # Convert to the format expected by the guardrails system
            server_policies[policy_name] = {
                "description": policy_config.get("description", f"Policy {policy_name}"),
                "validators": [
                    v["name"] if isinstance(v, dict) else v 
                    for v in policy_config.get("validators", [])
                ]
            }
        
        success = federated_server.update_policies(server_policies)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Distributed {len(server_policies)} policies to federated clients",
                "policy_version": federated_server.strategy.policy_version,
                "distributed_policies": list(server_policies.keys())
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": "Failed to update federated server with new policies"
            }), 500
    
    except Exception as e:
        logger.error(f"Error distributing policies: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error distributing policies: {str(e)}"
        }), 500

