"""
Federated Guardrails Client using Flower AI Framework

This module implements a Flower client that enables the Guardrails API Service
to participate in federated learning for policy distribution and updates.
"""

import json
import logging
import os
import sys
from typing import Dict, List, Tuple, Optional, Any
import pickle
import threading
import time
from pathlib import Path

import flwr as fl
from flwr.common import Parameters, FitRes, EvaluateRes, Status, Code
from flwr.client import Client, ClientApp, NumPyClient

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from plugin_system import plugin_manager, GuardrailsPlugin
from config import GUARDRAIL_CONFIGS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FederatedGuardrailsClient(NumPyClient):
    """
    Flower client implementation for federated guardrails policy distribution.
    
    This client receives policy updates from the Flower server and applies them
    to the local guardrails system. It can also send back anonymized metrics
    about policy effectiveness.
    """
    
    def __init__(self, client_id: str = "guardrails-client"):
        """
        Initialize the federated guardrails client.
        
        Args:
            client_id: Unique identifier for this client
        """
        self.client_id = client_id
        self.policy_version = 0
        self.policy_storage_path = Path("federated_policies")
        self.policy_storage_path.mkdir(exist_ok=True)
        
        # Metrics for tracking policy effectiveness
        self.validation_metrics = {
            "total_validations": 0,
            "failed_validations": 0,
            "validation_types": {},
            "policy_version": self.policy_version
        }
        
        # Thread-safe lock for metrics updates
        self.metrics_lock = threading.Lock()
        
        # Load existing policies if available
        self._load_local_policies()
        
        logger.info(f"Federated Guardrails Client {client_id} initialized")
    
    def get_parameters(self, config: Dict[str, Any]) -> List[bytes]:
        """
        Return the current policy parameters.
        
        In traditional federated learning, this would return model weights.
        For guardrails, we return the current policy configurations.
        
        Args:
            config: Configuration from the server
            
        Returns:
            Serialized policy parameters
        """
        try:
            # Get current guardrail configurations
            active_plugin = plugin_manager.get_active_plugin()
            if active_plugin:
                current_policies = active_plugin.get_available_guardrails()
            else:
                current_policies = GUARDRAIL_CONFIGS
            
            # Add metadata
            policy_data = {
                "policies": current_policies,
                "version": self.policy_version,
                "client_id": self.client_id,
                "timestamp": time.time()
            }
            
            # Serialize the policy data
            serialized_data = pickle.dumps(policy_data)
            
            logger.info(f"Returning policy parameters (version {self.policy_version})")
            return [serialized_data]
            
        except Exception as e:
            logger.error(f"Error getting parameters: {str(e)}")
            return [pickle.dumps({"error": str(e)})]
    
    def fit(self, parameters: List[bytes], config: Dict[str, Any]) -> Tuple[List[bytes], int, Dict[str, Any]]:
        """
        Receive and apply new policy parameters from the server.
        
        Args:
            parameters: Serialized policy parameters from server
            config: Configuration from server
            
        Returns:
            Tuple of (updated parameters, number of examples, metrics)
        """
        try:
            if not parameters:
                logger.warning("No parameters received from server")
                return self.get_parameters(config), 0, {}
            
            # Deserialize the policy data
            policy_data = pickle.loads(parameters[0])
            
            if "error" in policy_data:
                logger.error(f"Received error from server: {policy_data['error']}")
                return self.get_parameters(config), 0, {"error": policy_data["error"]}
            
            # Extract new policies
            new_policies = policy_data.get("policies", {})
            new_version = policy_data.get("version", self.policy_version + 1)
            
            logger.info(f"Received policy update (version {new_version})")
            
            # Apply the new policies
            success = self._apply_new_policies(new_policies, new_version)
            
            if success:
                self.policy_version = new_version
                self._save_local_policies(new_policies, new_version)
                
                # Return updated parameters and metrics
                metrics = self._get_current_metrics()
                return self.get_parameters(config), 1, metrics
            else:
                logger.error("Failed to apply new policies")
                return self.get_parameters(config), 0, {"error": "Failed to apply policies"}
                
        except Exception as e:
            logger.error(f"Error in fit method: {str(e)}")
            return self.get_parameters(config), 0, {"error": str(e)}
    
    def evaluate(self, parameters: List[bytes], config: Dict[str, Any]) -> Tuple[float, int, Dict[str, Any]]:
        """
        Evaluate the current policy effectiveness.
        
        Args:
            parameters: Policy parameters (not used for evaluation)
            config: Configuration from server
            
        Returns:
            Tuple of (loss, number of examples, metrics)
        """
        try:
            metrics = self._get_current_metrics()
            
            # Calculate a simple "loss" based on validation failure rate
            total_validations = metrics.get("total_validations", 1)
            failed_validations = metrics.get("failed_validations", 0)
            failure_rate = failed_validations / total_validations if total_validations > 0 else 0
            
            logger.info(f"Policy evaluation - Failure rate: {failure_rate:.2%}")
            
            return failure_rate, total_validations, metrics
            
        except Exception as e:
            logger.error(f"Error in evaluate method: {str(e)}")
            return 1.0, 0, {"error": str(e)}
    
    def _apply_new_policies(self, new_policies: Dict[str, Any], version: int) -> bool:
        """
        Apply new policies to the local guardrails system.
        
        Args:
            new_policies: Dictionary of new policy configurations
            version: Version number of the policies
            
        Returns:
            True if policies were applied successfully, False otherwise
        """
        try:
            # Update the global GUARDRAIL_CONFIGS
            global GUARDRAIL_CONFIGS
            
            # Validate the new policies before applying
            if not self._validate_policies(new_policies):
                logger.error("Policy validation failed")
                return False
            
            # Create a backup of current policies
            backup_policies = GUARDRAIL_CONFIGS.copy()
            
            try:
                # Update the configurations
                GUARDRAIL_CONFIGS.update(new_policies)
                
                # If we have an active plugin, we might need to reinitialize it
                # with the new configurations
                active_plugin = plugin_manager.get_active_plugin()
                if active_plugin and hasattr(active_plugin, 'update_configurations'):
                    active_plugin.update_configurations(new_policies)
                
                logger.info(f"Successfully applied {len(new_policies)} policy updates")
                return True
                
            except Exception as e:
                # Rollback on failure
                GUARDRAIL_CONFIGS.clear()
                GUARDRAIL_CONFIGS.update(backup_policies)
                logger.error(f"Failed to apply policies, rolled back: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying new policies: {str(e)}")
            return False
    
    def _validate_policies(self, policies: Dict[str, Any]) -> bool:
        """
        Validate policy configurations before applying them.
        
        Args:
            policies: Policy configurations to validate
            
        Returns:
            True if policies are valid, False otherwise
        """
        try:
            for policy_name, policy_config in policies.items():
                # Check required fields
                if not isinstance(policy_config, dict):
                    logger.error(f"Policy {policy_name} is not a dictionary")
                    return False
                
                # Check for required keys
                required_keys = ["validators"]
                for key in required_keys:
                    if key not in policy_config:
                        logger.error(f"Policy {policy_name} missing required key: {key}")
                        return False
                
                # Validate validators list
                validators = policy_config["validators"]
                if not isinstance(validators, list):
                    logger.error(f"Policy {policy_name} validators must be a list")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating policies: {str(e)}")
            return False
    
    def _save_local_policies(self, policies: Dict[str, Any], version: int):
        """
        Save policies to local storage for persistence.
        
        Args:
            policies: Policy configurations to save
            version: Version number of the policies
        """
        try:
            policy_file = self.policy_storage_path / f"policies_v{version}.json"
            
            policy_data = {
                "version": version,
                "timestamp": time.time(),
                "policies": policies
            }
            
            with open(policy_file, 'w') as f:
                json.dump(policy_data, f, indent=2)
            
            # Also save as the current policies
            current_file = self.policy_storage_path / "current_policies.json"
            with open(current_file, 'w') as f:
                json.dump(policy_data, f, indent=2)
            
            logger.info(f"Saved policies version {version} to {policy_file}")
            
        except Exception as e:
            logger.error(f"Error saving policies: {str(e)}")
    
    def _load_local_policies(self):
        """
        Load policies from local storage if available.
        """
        try:
            current_file = self.policy_storage_path / "current_policies.json"
            
            if current_file.exists():
                with open(current_file, 'r') as f:
                    policy_data = json.load(f)
                
                self.policy_version = policy_data.get("version", 0)
                policies = policy_data.get("policies", {})
                
                if policies:
                    self._apply_new_policies(policies, self.policy_version)
                    logger.info(f"Loaded local policies version {self.policy_version}")
            
        except Exception as e:
            logger.error(f"Error loading local policies: {str(e)}")
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current validation metrics.
        
        Returns:
            Dictionary of current metrics
        """
        with self.metrics_lock:
            return self.validation_metrics.copy()
    
    def update_validation_metrics(self, validation_result: Dict[str, Any]):
        """
        Update validation metrics based on a validation result.
        
        Args:
            validation_result: Result from a guardrails validation
        """
        try:
            with self.metrics_lock:
                self.validation_metrics["total_validations"] += 1
                
                if not validation_result.get("valid", True):
                    self.validation_metrics["failed_validations"] += 1
                
                # Track validation types
                validations = validation_result.get("validations", [])
                for validation in validations:
                    validator_name = validation.get("validator_name", "unknown")
                    status = validation.get("status", "unknown")
                    
                    if validator_name not in self.validation_metrics["validation_types"]:
                        self.validation_metrics["validation_types"][validator_name] = {
                            "total": 0, "failed": 0
                        }
                    
                    self.validation_metrics["validation_types"][validator_name]["total"] += 1
                    if status == "fail":
                        self.validation_metrics["validation_types"][validator_name]["failed"] += 1
                
                self.validation_metrics["policy_version"] = self.policy_version
                
        except Exception as e:
            logger.error(f"Error updating validation metrics: {str(e)}")

# Global instance of the federated client
federated_client = None

def get_federated_client(client_id: str = None) -> FederatedGuardrailsClient:
    """
    Get or create the global federated client instance.
    
    Args:
        client_id: Optional client ID
        
    Returns:
        FederatedGuardrailsClient instance
    """
    global federated_client
    
    if federated_client is None:
        if client_id is None:
            client_id = f"guardrails-client-{os.getpid()}"
        federated_client = FederatedGuardrailsClient(client_id)
    
    return federated_client

def create_flower_client_app(client_id: str = None) -> ClientApp:
    """
    Create a Flower ClientApp for the guardrails service.
    
    Args:
        client_id: Optional client ID
        
    Returns:
        Flower ClientApp instance
    """
    def client_fn(context):
        return get_federated_client(client_id)
    
    return ClientApp(client_fn=client_fn)

if __name__ == "__main__":
    # This allows running the client directly for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Federated Guardrails Client")
    parser.add_argument("--server", type=str, default="localhost:8080", 
                       help="Flower server address")
    parser.add_argument("--client-id", type=str, default=None,
                       help="Client ID")
    
    args = parser.parse_args()
    
    # Create and start the client
    client = get_federated_client(args.client_id)
    
    logger.info(f"Starting Flower client, connecting to {args.server}")
    
    # Start the Flower client
    fl.client.start_client(
        server_address=args.server,
        client=client
    )

