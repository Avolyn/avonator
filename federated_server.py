"""
Federated Guardrails Server using Flower AI Framework

This module implements a Flower server that orchestrates the distribution of
guardrail policies across multiple clients in a federated manner.
"""

import json
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import threading

import flwr as fl
from flwr.common import (
    Parameters, 
    FitRes, 
    EvaluateRes, 
    parameters_to_ndarrays, 
    ndarrays_to_parameters,
    Status,
    Code
)
from flwr.server import ServerApp, ServerConfig
from flwr.server.strategy import Strategy, FedAvg
from flwr.server.client_manager import ClientManager
from flwr.server.client_proxy import ClientProxy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FederatedGuardrailsStrategy(Strategy):
    """
    Custom Flower strategy for federated guardrails policy distribution.
    
    This strategy focuses on distributing policy configurations rather than
    aggregating model weights like traditional federated learning.
    """
    
    def __init__(
        self,
        initial_policies: Dict[str, Any] = None,
        min_fit_clients: int = 1,
        min_evaluate_clients: int = 1,
        min_available_clients: int = 1,
        policy_storage_path: str = "server_policies"
    ):
        """
        Initialize the federated guardrails strategy.
        
        Args:
            initial_policies: Initial policy configurations to distribute
            min_fit_clients: Minimum number of clients for fit rounds
            min_evaluate_clients: Minimum number of clients for evaluation
            min_available_clients: Minimum number of available clients
            policy_storage_path: Path to store policy versions
        """
        self.current_policies = initial_policies or {}
        self.policy_version = 1
        self.min_fit_clients = min_fit_clients
        self.min_evaluate_clients = min_evaluate_clients
        self.min_available_clients = min_available_clients
        
        # Policy storage
        self.policy_storage_path = Path(policy_storage_path)
        self.policy_storage_path.mkdir(exist_ok=True)
        
        # Client metrics tracking
        self.client_metrics = {}
        self.metrics_lock = threading.Lock()
        
        # Load existing policies if available
        self._load_latest_policies()
        
        logger.info(f"Federated Guardrails Strategy initialized with {len(self.current_policies)} policies")
    
    def initialize_parameters(self, client_manager: ClientManager) -> Optional[Parameters]:
        """
        Initialize global policy parameters.
        
        Args:
            client_manager: Flower client manager
            
        Returns:
            Initial policy parameters
        """
        try:
            if not self.current_policies:
                # Default policies if none provided
                self.current_policies = {
                    "default": {
                        "description": "Default guardrail configuration",
                        "validators": ["length_check", "profanity_check"]
                    },
                    "strict": {
                        "description": "Strict content moderation",
                        "validators": ["length_check", "profanity_check", "toxic_language_check", "pii_check"]
                    }
                }
            
            policy_data = {
                "policies": self.current_policies,
                "version": self.policy_version,
                "timestamp": time.time()
            }
            
            serialized_data = pickle.dumps(policy_data)
            logger.info(f"Initialized policies version {self.policy_version}")
            
            return Parameters(tensors=[serialized_data], tensor_type="")
            
        except Exception as e:
            logger.error(f"Error initializing parameters: {str(e)}")
            return None
    
    def configure_fit(
        self, 
        server_round: int, 
        parameters: Parameters, 
        client_manager: ClientManager
    ) -> List[Tuple[ClientProxy, Dict[str, Any]]]:
        """
        Configure the next round of federated policy distribution.
        
        Args:
            server_round: Current server round number
            parameters: Current policy parameters
            client_manager: Flower client manager
            
        Returns:
            List of (client, config) tuples for the fit round
        """
        try:
            # Sample clients for this round
            sample_size = max(self.min_fit_clients, int(len(client_manager.all()) * 0.5))
            clients = client_manager.sample(
                num_clients=min(sample_size, len(client_manager.all())),
                min_num_clients=self.min_fit_clients
            )
            
            # Configuration for clients
            config = {
                "server_round": server_round,
                "policy_version": self.policy_version,
                "local_epochs": 1  # Not used for policy distribution, but required by Flower
            }
            
            logger.info(f"Round {server_round}: Configuring {len(clients)} clients for policy distribution")
            
            return [(client, config) for client in clients]
            
        except Exception as e:
            logger.error(f"Error configuring fit round {server_round}: {str(e)}")
            return []
    
    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]]
    ) -> Tuple[Optional[Parameters], Dict[str, Any]]:
        """
        Aggregate results from the fit round.
        
        For policy distribution, this mainly collects metrics from clients
        rather than aggregating model weights.
        
        Args:
            server_round: Current server round number
            results: Results from successful clients
            failures: Failed client results
            
        Returns:
            Tuple of (aggregated parameters, metrics)
        """
        try:
            if failures:
                logger.warning(f"Round {server_round}: {len(failures)} clients failed")
            
            # Collect metrics from successful clients
            aggregated_metrics = {
                "server_round": server_round,
                "successful_clients": len(results),
                "failed_clients": len(failures),
                "policy_version": self.policy_version,
                "client_metrics": {}
            }
            
            with self.metrics_lock:
                for client_proxy, fit_res in results:
                    client_id = client_proxy.cid
                    client_metrics = fit_res.metrics
                    
                    # Store client metrics
                    self.client_metrics[client_id] = {
                        "last_update": time.time(),
                        "metrics": client_metrics,
                        "server_round": server_round
                    }
                    
                    aggregated_metrics["client_metrics"][client_id] = client_metrics
            
            # Return the same policy parameters (no aggregation needed for policies)
            policy_data = {
                "policies": self.current_policies,
                "version": self.policy_version,
                "timestamp": time.time()
            }
            
            serialized_data = pickle.dumps(policy_data)
            parameters = Parameters(tensors=[serialized_data], tensor_type="")
            
            logger.info(f"Round {server_round}: Aggregated results from {len(results)} clients")
            
            return parameters, aggregated_metrics
            
        except Exception as e:
            logger.error(f"Error aggregating fit results for round {server_round}: {str(e)}")
            return None, {"error": str(e)}
    
    def configure_evaluate(
        self,
        server_round: int,
        parameters: Parameters,
        client_manager: ClientManager
    ) -> List[Tuple[ClientProxy, Dict[str, Any]]]:
        """
        Configure the evaluation round.
        
        Args:
            server_round: Current server round number
            parameters: Current policy parameters
            client_manager: Flower client manager
            
        Returns:
            List of (client, config) tuples for evaluation
        """
        try:
            # Sample clients for evaluation
            sample_size = max(self.min_evaluate_clients, int(len(client_manager.all()) * 0.3))
            clients = client_manager.sample(
                num_clients=min(sample_size, len(client_manager.all())),
                min_num_clients=self.min_evaluate_clients
            )
            
            config = {
                "server_round": server_round,
                "policy_version": self.policy_version
            }
            
            logger.info(f"Round {server_round}: Configuring {len(clients)} clients for evaluation")
            
            return [(client, config) for client in clients]
            
        except Exception as e:
            logger.error(f"Error configuring evaluate round {server_round}: {str(e)}")
            return []
    
    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        failures: List[Union[Tuple[ClientProxy, EvaluateRes], BaseException]]
    ) -> Tuple[Optional[float], Dict[str, Any]]:
        """
        Aggregate evaluation results from clients.
        
        Args:
            server_round: Current server round number
            results: Evaluation results from successful clients
            failures: Failed evaluation results
            
        Returns:
            Tuple of (aggregated loss, metrics)
        """
        try:
            if not results:
                logger.warning(f"Round {server_round}: No evaluation results received")
                return None, {}
            
            # Aggregate evaluation metrics
            total_examples = sum(evaluate_res.num_examples for _, evaluate_res in results)
            weighted_losses = [
                evaluate_res.loss * evaluate_res.num_examples 
                for _, evaluate_res in results
            ]
            
            aggregated_loss = sum(weighted_losses) / total_examples if total_examples > 0 else 0.0
            
            # Collect detailed metrics
            evaluation_metrics = {
                "server_round": server_round,
                "aggregated_loss": aggregated_loss,
                "total_examples": total_examples,
                "successful_evaluations": len(results),
                "failed_evaluations": len(failures),
                "policy_version": self.policy_version,
                "client_evaluations": {}
            }
            
            for client_proxy, evaluate_res in results:
                client_id = client_proxy.cid
                evaluation_metrics["client_evaluations"][client_id] = {
                    "loss": evaluate_res.loss,
                    "num_examples": evaluate_res.num_examples,
                    "metrics": evaluate_res.metrics
                }
            
            logger.info(f"Round {server_round}: Aggregated evaluation - Loss: {aggregated_loss:.4f}")
            
            return aggregated_loss, evaluation_metrics
            
        except Exception as e:
            logger.error(f"Error aggregating evaluation results for round {server_round}: {str(e)}")
            return None, {"error": str(e)}
    
    def evaluate(
        self,
        server_round: int,
        parameters: Parameters
    ) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Evaluate the current global policy state on the server side.
        
        Args:
            server_round: Current server round number
            parameters: Current policy parameters
            
        Returns:
            Tuple of (loss, metrics) or None
        """
        try:
            # Server-side evaluation of policy effectiveness
            with self.metrics_lock:
                total_clients = len(self.client_metrics)
                active_clients = sum(
                    1 for metrics in self.client_metrics.values()
                    if time.time() - metrics["last_update"] < 300  # Active within 5 minutes
                )
            
            # Simple policy health score
            policy_health = active_clients / total_clients if total_clients > 0 else 1.0
            loss = 1.0 - policy_health  # Lower loss means better health
            
            metrics = {
                "server_round": server_round,
                "policy_version": self.policy_version,
                "total_clients": total_clients,
                "active_clients": active_clients,
                "policy_health": policy_health,
                "policies_count": len(self.current_policies)
            }
            
            logger.info(f"Round {server_round}: Server evaluation - Policy health: {policy_health:.2%}")
            
            return loss, metrics
            
        except Exception as e:
            logger.error(f"Error in server evaluation for round {server_round}: {str(e)}")
            return None
    
    def update_policies(self, new_policies: Dict[str, Any]) -> bool:
        """
        Update the current policies and increment version.
        
        Args:
            new_policies: New policy configurations
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Validate new policies
            if not isinstance(new_policies, dict):
                logger.error("New policies must be a dictionary")
                return False
            
            # Update policies
            self.current_policies.update(new_policies)
            self.policy_version += 1
            
            # Save to storage
            self._save_policies()
            
            logger.info(f"Updated policies to version {self.policy_version}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating policies: {str(e)}")
            return False
    
    def get_client_metrics(self) -> Dict[str, Any]:
        """
        Get current client metrics.
        
        Returns:
            Dictionary of client metrics
        """
        with self.metrics_lock:
            return self.client_metrics.copy()
    
    def _save_policies(self):
        """Save current policies to storage."""
        try:
            policy_file = self.policy_storage_path / f"policies_v{self.policy_version}.json"
            
            policy_data = {
                "version": self.policy_version,
                "timestamp": time.time(),
                "policies": self.current_policies
            }
            
            with open(policy_file, 'w') as f:
                json.dump(policy_data, f, indent=2)
            
            # Also save as current
            current_file = self.policy_storage_path / "current_policies.json"
            with open(current_file, 'w') as f:
                json.dump(policy_data, f, indent=2)
            
            logger.info(f"Saved policies version {self.policy_version}")
            
        except Exception as e:
            logger.error(f"Error saving policies: {str(e)}")
    
    def _load_latest_policies(self):
        """Load the latest policies from storage."""
        try:
            current_file = self.policy_storage_path / "current_policies.json"
            
            if current_file.exists():
                with open(current_file, 'r') as f:
                    policy_data = json.load(f)
                
                self.current_policies = policy_data.get("policies", {})
                self.policy_version = policy_data.get("version", 1)
                
                logger.info(f"Loaded policies version {self.policy_version}")
            
        except Exception as e:
            logger.error(f"Error loading policies: {str(e)}")

class FederatedGuardrailsServer:
    """
    Wrapper class for the Flower server with additional management capabilities.
    """
    
    def __init__(
        self,
        strategy: FederatedGuardrailsStrategy = None,
        server_address: str = "0.0.0.0:8080",
        num_rounds: int = 10
    ):
        """
        Initialize the federated guardrails server.
        
        Args:
            strategy: Federated learning strategy
            server_address: Server bind address
            num_rounds: Number of federated rounds
        """
        self.strategy = strategy or FederatedGuardrailsStrategy()
        self.server_address = server_address
        self.num_rounds = num_rounds
        self.server_thread = None
        self.is_running = False
        
        logger.info(f"Federated Guardrails Server initialized on {server_address}")
    
    def start_server(self, blocking: bool = True):
        """
        Start the Flower server.
        
        Args:
            blocking: Whether to block the current thread
        """
        try:
            config = ServerConfig(num_rounds=self.num_rounds)
            
            if blocking:
                logger.info(f"Starting Flower server on {self.server_address}")
                self.is_running = True
                
                fl.server.start_server(
                    server_address=self.server_address,
                    config=config,
                    strategy=self.strategy
                )
            else:
                def run_server():
                    logger.info(f"Starting Flower server on {self.server_address}")
                    self.is_running = True
                    
                    fl.server.start_server(
                        server_address=self.server_address,
                        config=config,
                        strategy=self.strategy
                    )
                    
                    self.is_running = False
                
                self.server_thread = threading.Thread(target=run_server, daemon=True)
                self.server_thread.start()
                
                # Give it a moment to start
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
            self.is_running = False
    
    def stop_server(self):
        """Stop the Flower server."""
        self.is_running = False
        if self.server_thread and self.server_thread.is_alive():
            logger.info("Stopping Flower server")
            # Note: Flower doesn't have a clean shutdown mechanism
            # The thread will terminate when the server stops
    
    def update_policies(self, new_policies: Dict[str, Any]) -> bool:
        """
        Update policies on the server.
        
        Args:
            new_policies: New policy configurations
            
        Returns:
            True if successful, False otherwise
        """
        return self.strategy.update_policies(new_policies)
    
    def get_server_status(self) -> Dict[str, Any]:
        """
        Get current server status.
        
        Returns:
            Dictionary with server status information
        """
        return {
            "running": self.is_running,
            "address": self.server_address,
            "num_rounds": self.num_rounds,
            "policy_version": self.strategy.policy_version,
            "policies_count": len(self.strategy.current_policies),
            "client_metrics": self.strategy.get_client_metrics()
        }

# Global server instance
federated_server = None

def get_federated_server(
    server_address: str = "0.0.0.0:8080",
    num_rounds: int = 10
) -> FederatedGuardrailsServer:
    """
    Get or create the global federated server instance.
    
    Args:
        server_address: Server bind address
        num_rounds: Number of federated rounds
        
    Returns:
        FederatedGuardrailsServer instance
    """
    global federated_server
    
    if federated_server is None:
        strategy = FederatedGuardrailsStrategy()
        federated_server = FederatedGuardrailsServer(
            strategy=strategy,
            server_address=server_address,
            num_rounds=num_rounds
        )
    
    return federated_server

if __name__ == "__main__":
    # This allows running the server directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Federated Guardrails Server")
    parser.add_argument("--address", type=str, default="0.0.0.0:8080",
                       help="Server bind address")
    parser.add_argument("--rounds", type=int, default=10,
                       help="Number of federated rounds")
    
    args = parser.parse_args()
    
    # Create and start the server
    server = get_federated_server(args.address, args.rounds)
    server.start_server(blocking=True)

