from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
import os
import sys

# Add the parent directory to the path to import plugin system
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from plugin_system import plugin_manager
from config import API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
plugin_bp = Blueprint('plugin', __name__)

@plugin_bp.route('/v1/plugins', methods=['GET'])
@cross_origin()
def list_plugins():
    """List all registered plugins and their status."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        plugins = plugin_manager.list_plugins()
        return jsonify({
            "status": "success",
            "plugins": plugins
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing plugins: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error listing plugins: {str(e)}"
        }), 500

@plugin_bp.route('/v1/plugins/active', methods=['GET'])
@cross_origin()
def get_active_plugin():
    """Get information about the currently active plugin."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        active_plugin = plugin_manager.get_active_plugin()
        if not active_plugin:
            return jsonify({
                "status": "failure",
                "message": "No active plugin"
            }), 404
        
        return jsonify({
            "status": "success",
            "active_plugin": {
                "name": active_plugin.name,
                "version": active_plugin.version,
                "healthy": active_plugin.health_check()
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting active plugin: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error getting active plugin: {str(e)}"
        }), 500

@plugin_bp.route('/v1/plugins/switch', methods=['POST'])
@cross_origin()
def switch_plugin():
    """Switch to a different plugin."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data or 'plugin_name' not in data:
            return jsonify({
                "status": "failure",
                "message": "Missing 'plugin_name' in request body"
            }), 400
        
        plugin_name = data['plugin_name']
        
        if plugin_manager.switch_plugin(plugin_name):
            return jsonify({
                "status": "success",
                "message": f"Successfully switched to plugin: {plugin_name}"
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": f"Failed to switch to plugin: {plugin_name}"
            }), 400
    
    except Exception as e:
        logger.error(f"Error switching plugin: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error switching plugin: {str(e)}"
        }), 500

@plugin_bp.route('/v1/plugins/load', methods=['POST'])
@cross_origin()
def load_plugin():
    """Dynamically load a plugin from a module."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        data = request.get_json()
        if not data or 'module_path' not in data or 'class_name' not in data:
            return jsonify({
                "status": "failure",
                "message": "Missing 'module_path' or 'class_name' in request body"
            }), 400
        
        module_path = data['module_path']
        class_name = data['class_name']
        config = data.get('config', {})
        
        if plugin_manager.load_plugin_from_module(module_path, class_name, config):
            return jsonify({
                "status": "success",
                "message": f"Successfully loaded plugin from {module_path}.{class_name}"
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": f"Failed to load plugin from {module_path}.{class_name}"
            }), 400
    
    except Exception as e:
        logger.error(f"Error loading plugin: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error loading plugin: {str(e)}"
        }), 500

@plugin_bp.route('/v1/plugins/<plugin_name>/health', methods=['GET'])
@cross_origin()
def check_plugin_health(plugin_name):
    """Check the health of a specific plugin."""
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    try:
        plugins = plugin_manager.list_plugins()
        if plugin_name not in plugins:
            return jsonify({
                "status": "failure",
                "message": f"Plugin {plugin_name} not found"
            }), 404
        
        plugin_info = plugins[plugin_name]
        return jsonify({
            "status": "success",
            "plugin_name": plugin_name,
            "healthy": plugin_info["healthy"],
            "version": plugin_info["version"]
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking plugin health: {str(e)}")
        return jsonify({
            "status": "failure",
            "message": f"Error checking plugin health: {str(e)}"
        }), 500

