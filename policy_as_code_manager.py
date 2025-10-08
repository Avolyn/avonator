"""
Policy-as-Code Management System for Federated Guardrails

This module provides a comprehensive system for managing guardrail policies
as code, including version control, validation, and federated distribution.
"""

import json
import yaml
import os
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
import importlib.util
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PolicyMetadata:
    """Metadata for a policy configuration."""
    name: str
    version: str
    description: str
    author: str
    created_at: str
    updated_at: str
    hash: str
    dependencies: List[str]
    tags: List[str]

@dataclass
class PolicyValidationResult:
    """Result of policy validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Optional[PolicyMetadata] = None

class PolicyAsCodeManager:
    """
    Manages guardrail policies as code with version control and validation.
    """
    
    def __init__(self, policy_repository_path: str = "policy_repository"):
        """
        Initialize the policy-as-code manager.
        
        Args:
            policy_repository_path: Path to the policy repository
        """
        self.repository_path = Path(policy_repository_path)
        self.repository_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.repository_path / "policies").mkdir(exist_ok=True)
        (self.repository_path / "templates").mkdir(exist_ok=True)
        (self.repository_path / "versions").mkdir(exist_ok=True)
        (self.repository_path / "metadata").mkdir(exist_ok=True)
        
        # Policy registry
        self.policy_registry = {}
        self._load_policy_registry()
        
        logger.info(f"Policy-as-Code Manager initialized with repository at {self.repository_path}")
    
    def create_policy_from_template(
        self, 
        policy_name: str, 
        template_name: str = "basic_guardrail",
        **kwargs
    ) -> PolicyValidationResult:
        """
        Create a new policy from a template.
        
        Args:
            policy_name: Name of the new policy
            template_name: Name of the template to use
            **kwargs: Template parameters
            
        Returns:
            PolicyValidationResult with creation status
        """
        try:
            template_path = self.repository_path / "templates" / f"{template_name}.yaml"
            
            if not template_path.exists():
                # Create a basic template if it doesn't exist
                self._create_basic_template()
            
            # Load template
            with open(template_path, 'r') as f:
                template_data = yaml.safe_load(f)
            
            # Apply template parameters
            policy_data = self._apply_template_parameters(template_data, **kwargs)
            
            # Add metadata
            metadata = PolicyMetadata(
                name=policy_name,
                version="1.0.0",
                description=policy_data.get("description", f"Policy {policy_name}"),
                author=kwargs.get("author", "system"),
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                hash=self._calculate_policy_hash(policy_data),
                dependencies=policy_data.get("dependencies", []),
                tags=policy_data.get("tags", [])
            )
            
            # Save policy
            policy_file = self.repository_path / "policies" / f"{policy_name}.yaml"
            with open(policy_file, 'w') as f:
                yaml.dump(policy_data, f, default_flow_style=False)
            
            # Save metadata
            metadata_file = self.repository_path / "metadata" / f"{policy_name}.json"
            with open(metadata_file, 'w') as f:
                json.dump(asdict(metadata), f, indent=2)
            
            # Update registry
            self.policy_registry[policy_name] = metadata
            self._save_policy_registry()
            
            logger.info(f"Created policy '{policy_name}' from template '{template_name}'")
            
            return PolicyValidationResult(
                valid=True,
                errors=[],
                warnings=[],
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating policy from template: {str(e)}")
            return PolicyValidationResult(
                valid=False,
                errors=[str(e)],
                warnings=[]
            )
    
    def validate_policy(self, policy_data: Dict[str, Any]) -> PolicyValidationResult:
        """
        Validate a policy configuration.
        
        Args:
            policy_data: Policy configuration to validate
            
        Returns:
            PolicyValidationResult with validation status
        """
        errors = []
        warnings = []
        
        try:
            # Required fields validation
            required_fields = ["name", "description", "validators"]
            for field in required_fields:
                if field not in policy_data:
                    errors.append(f"Missing required field: {field}")
            
            # Validators validation
            if "validators" in policy_data:
                validators = policy_data["validators"]
                if not isinstance(validators, list):
                    errors.append("'validators' must be a list")
                else:
                    for i, validator in enumerate(validators):
                        if isinstance(validator, dict):
                            if "name" not in validator:
                                errors.append(f"Validator {i} missing 'name' field")
                            if "config" in validator and not isinstance(validator["config"], dict):
                                errors.append(f"Validator {i} 'config' must be a dictionary")
                        elif isinstance(validator, str):
                            # Simple validator name - this is acceptable
                            pass
                        else:
                            errors.append(f"Validator {i} must be a string or dictionary")
            
            # Policy-specific validation
            if "on_fail_action" in policy_data:
                valid_actions = ["exception", "filter", "warn", "log"]
                if policy_data["on_fail_action"] not in valid_actions:
                    errors.append(f"Invalid on_fail_action. Must be one of: {valid_actions}")
            
            # Dependencies validation
            if "dependencies" in policy_data:
                dependencies = policy_data["dependencies"]
                if not isinstance(dependencies, list):
                    errors.append("'dependencies' must be a list")
                else:
                    for dep in dependencies:
                        if not isinstance(dep, str):
                            errors.append("All dependencies must be strings")
                        elif dep not in self.policy_registry:
                            warnings.append(f"Dependency '{dep}' not found in registry")
            
            # Custom validator code validation
            if "custom_validators" in policy_data:
                custom_validators = policy_data["custom_validators"]
                if isinstance(custom_validators, dict):
                    for validator_name, validator_code in custom_validators.items():
                        validation_result = self._validate_custom_validator_code(validator_code)
                        if not validation_result:
                            errors.append(f"Invalid custom validator code for '{validator_name}'")
            
            # Performance warnings
            if "validators" in policy_data and len(policy_data["validators"]) > 10:
                warnings.append("Policy has more than 10 validators, which may impact performance")
            
            is_valid = len(errors) == 0
            
            return PolicyValidationResult(
                valid=is_valid,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error validating policy: {str(e)}")
            return PolicyValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[]
            )
    
    def update_policy(
        self, 
        policy_name: str, 
        policy_data: Dict[str, Any],
        version_increment: str = "patch"
    ) -> PolicyValidationResult:
        """
        Update an existing policy.
        
        Args:
            policy_name: Name of the policy to update
            policy_data: New policy configuration
            version_increment: Type of version increment (major, minor, patch)
            
        Returns:
            PolicyValidationResult with update status
        """
        try:
            # Validate the new policy data
            validation_result = self.validate_policy(policy_data)
            if not validation_result.valid:
                return validation_result
            
            # Check if policy exists
            if policy_name not in self.policy_registry:
                return PolicyValidationResult(
                    valid=False,
                    errors=[f"Policy '{policy_name}' not found in registry"],
                    warnings=[]
                )
            
            # Get current metadata
            current_metadata = self.policy_registry[policy_name]
            
            # Create backup of current version
            self._backup_policy_version(policy_name, current_metadata.version)
            
            # Calculate new version
            new_version = self._increment_version(current_metadata.version, version_increment)
            
            # Update metadata
            new_metadata = PolicyMetadata(
                name=policy_name,
                version=new_version,
                description=policy_data.get("description", current_metadata.description),
                author=policy_data.get("author", current_metadata.author),
                created_at=current_metadata.created_at,
                updated_at=datetime.utcnow().isoformat(),
                hash=self._calculate_policy_hash(policy_data),
                dependencies=policy_data.get("dependencies", []),
                tags=policy_data.get("tags", current_metadata.tags)
            )
            
            # Save updated policy
            policy_file = self.repository_path / "policies" / f"{policy_name}.yaml"
            with open(policy_file, 'w') as f:
                yaml.dump(policy_data, f, default_flow_style=False)
            
            # Save updated metadata
            metadata_file = self.repository_path / "metadata" / f"{policy_name}.json"
            with open(metadata_file, 'w') as f:
                json.dump(asdict(new_metadata), f, indent=2)
            
            # Update registry
            self.policy_registry[policy_name] = new_metadata
            self._save_policy_registry()
            
            logger.info(f"Updated policy '{policy_name}' to version {new_version}")
            
            return PolicyValidationResult(
                valid=True,
                errors=[],
                warnings=validation_result.warnings,
                metadata=new_metadata
            )
            
        except Exception as e:
            logger.error(f"Error updating policy: {str(e)}")
            return PolicyValidationResult(
                valid=False,
                errors=[str(e)],
                warnings=[]
            )
    
    def get_policy(self, policy_name: str, version: str = None) -> Optional[Dict[str, Any]]:
        """
        Get a policy configuration.
        
        Args:
            policy_name: Name of the policy
            version: Specific version (if None, gets latest)
            
        Returns:
            Policy configuration or None if not found
        """
        try:
            if version is None:
                # Get latest version
                policy_file = self.repository_path / "policies" / f"{policy_name}.yaml"
            else:
                # Get specific version
                policy_file = self.repository_path / "versions" / f"{policy_name}_v{version}.yaml"
            
            if not policy_file.exists():
                return None
            
            with open(policy_file, 'r') as f:
                return yaml.safe_load(f)
                
        except Exception as e:
            logger.error(f"Error getting policy '{policy_name}': {str(e)}")
            return None
    
    def list_policies(self) -> Dict[str, PolicyMetadata]:
        """
        List all policies in the registry.
        
        Returns:
            Dictionary of policy names to metadata
        """
        return self.policy_registry.copy()
    
    def export_policies_for_federation(
        self, 
        policy_names: List[str] = None
    ) -> Dict[str, Any]:
        """
        Export policies in a format suitable for federated distribution.
        
        Args:
            policy_names: List of policy names to export (if None, exports all)
            
        Returns:
            Dictionary with policies and metadata for federation
        """
        try:
            if policy_names is None:
                policy_names = list(self.policy_registry.keys())
            
            federated_policies = {}
            metadata_collection = {}
            
            for policy_name in policy_names:
                if policy_name in self.policy_registry:
                    policy_data = self.get_policy(policy_name)
                    if policy_data:
                        # Convert to federated format
                        federated_policy = self._convert_to_federated_format(policy_data)
                        federated_policies[policy_name] = federated_policy
                        metadata_collection[policy_name] = asdict(self.policy_registry[policy_name])
            
            return {
                "policies": federated_policies,
                "metadata": metadata_collection,
                "export_timestamp": datetime.utcnow().isoformat(),
                "format_version": "1.0"
            }
            
        except Exception as e:
            logger.error(f"Error exporting policies for federation: {str(e)}")
            return {}
    
    def import_federated_policies(
        self, 
        federated_data: Dict[str, Any],
        overwrite_existing: bool = False
    ) -> List[PolicyValidationResult]:
        """
        Import policies from federated format.
        
        Args:
            federated_data: Federated policy data
            overwrite_existing: Whether to overwrite existing policies
            
        Returns:
            List of validation results for each imported policy
        """
        results = []
        
        try:
            policies = federated_data.get("policies", {})
            metadata_collection = federated_data.get("metadata", {})
            
            for policy_name, policy_config in policies.items():
                try:
                    # Check if policy already exists
                    if policy_name in self.policy_registry and not overwrite_existing:
                        results.append(PolicyValidationResult(
                            valid=False,
                            errors=[f"Policy '{policy_name}' already exists and overwrite_existing=False"],
                            warnings=[]
                        ))
                        continue
                    
                    # Convert from federated format
                    policy_data = self._convert_from_federated_format(policy_config)
                    
                    # Validate the policy
                    validation_result = self.validate_policy(policy_data)
                    if not validation_result.valid:
                        results.append(validation_result)
                        continue
                    
                    # Import metadata if available
                    if policy_name in metadata_collection:
                        metadata_dict = metadata_collection[policy_name]
                        metadata = PolicyMetadata(**metadata_dict)
                    else:
                        # Create default metadata
                        metadata = PolicyMetadata(
                            name=policy_name,
                            version="1.0.0",
                            description=policy_data.get("description", f"Imported policy {policy_name}"),
                            author="federated_import",
                            created_at=datetime.utcnow().isoformat(),
                            updated_at=datetime.utcnow().isoformat(),
                            hash=self._calculate_policy_hash(policy_data),
                            dependencies=policy_data.get("dependencies", []),
                            tags=policy_data.get("tags", ["imported"])
                        )
                    
                    # Save policy
                    policy_file = self.repository_path / "policies" / f"{policy_name}.yaml"
                    with open(policy_file, 'w') as f:
                        yaml.dump(policy_data, f, default_flow_style=False)
                    
                    # Save metadata
                    metadata_file = self.repository_path / "metadata" / f"{policy_name}.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(asdict(metadata), f, indent=2)
                    
                    # Update registry
                    self.policy_registry[policy_name] = metadata
                    
                    results.append(PolicyValidationResult(
                        valid=True,
                        errors=[],
                        warnings=[],
                        metadata=metadata
                    ))
                    
                    logger.info(f"Imported policy '{policy_name}' from federated data")
                    
                except Exception as e:
                    logger.error(f"Error importing policy '{policy_name}': {str(e)}")
                    results.append(PolicyValidationResult(
                        valid=False,
                        errors=[str(e)],
                        warnings=[]
                    ))
            
            # Save updated registry
            self._save_policy_registry()
            
            return results
            
        except Exception as e:
            logger.error(f"Error importing federated policies: {str(e)}")
            return [PolicyValidationResult(
                valid=False,
                errors=[str(e)],
                warnings=[]
            )]
    
    def _create_basic_template(self):
        """Create a basic policy template."""
        template_data = {
            "name": "{{policy_name}}",
            "description": "{{description|default('Basic guardrail policy')}}",
            "validators": [
                {
                    "name": "length_check",
                    "config": {
                        "max_length": "{{max_length|default(1000)}}",
                        "min_length": "{{min_length|default(1)}}"
                    }
                },
                {
                    "name": "profanity_check",
                    "config": {
                        "action": "{{profanity_action|default('filter')}}"
                    }
                }
            ],
            "on_fail_action": "{{on_fail_action|default('exception')}}",
            "tags": ["{{template_name}}", "basic"],
            "dependencies": []
        }
        
        template_path = self.repository_path / "templates" / "basic_guardrail.yaml"
        with open(template_path, 'w') as f:
            yaml.dump(template_data, f, default_flow_style=False)
    
    def _apply_template_parameters(self, template_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Apply parameters to a template."""
        # Simple template parameter substitution
        template_str = yaml.dump(template_data)
        
        # Replace template variables
        for key, value in kwargs.items():
            template_str = template_str.replace(f"{{{{{key}}}}}", str(value))
        
        # Handle default values (simplified)
        import re
        default_pattern = r'\{\{(\w+)\|default\(([^)]+)\)\}\}'
        
        def replace_default(match):
            var_name = match.group(1)
            default_value = match.group(2).strip("'\"")
            return kwargs.get(var_name, default_value)
        
        template_str = re.sub(default_pattern, replace_default, template_str)
        
        return yaml.safe_load(template_str)
    
    def _calculate_policy_hash(self, policy_data: Dict[str, Any]) -> str:
        """Calculate hash of policy data."""
        policy_str = json.dumps(policy_data, sort_keys=True)
        return hashlib.sha256(policy_str.encode()).hexdigest()[:16]
    
    def _increment_version(self, current_version: str, increment_type: str) -> str:
        """Increment version number."""
        try:
            major, minor, patch = map(int, current_version.split('.'))
            
            if increment_type == "major":
                major += 1
                minor = 0
                patch = 0
            elif increment_type == "minor":
                minor += 1
                patch = 0
            else:  # patch
                patch += 1
            
            return f"{major}.{minor}.{patch}"
            
        except Exception:
            # If version parsing fails, just increment patch
            return f"{current_version}.1"
    
    def _backup_policy_version(self, policy_name: str, version: str):
        """Backup current policy version."""
        try:
            current_file = self.repository_path / "policies" / f"{policy_name}.yaml"
            backup_file = self.repository_path / "versions" / f"{policy_name}_v{version}.yaml"
            
            if current_file.exists():
                import shutil
                shutil.copy2(current_file, backup_file)
                
        except Exception as e:
            logger.warning(f"Could not backup policy version: {str(e)}")
    
    def _convert_to_federated_format(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert policy to federated format."""
        # For now, the federated format is the same as the internal format
        # In the future, this could include compression, encryption, etc.
        return policy_data.copy()
    
    def _convert_from_federated_format(self, federated_policy: Dict[str, Any]) -> Dict[str, Any]:
        """Convert policy from federated format."""
        # For now, the federated format is the same as the internal format
        return federated_policy.copy()
    
    def _validate_custom_validator_code(self, validator_code: str) -> bool:
        """Validate custom validator code."""
        try:
            # Basic syntax validation
            compile(validator_code, '<string>', 'exec')
            
            # Check for dangerous operations (basic security check)
            dangerous_keywords = ['import os', 'import sys', 'exec', 'eval', '__import__']
            for keyword in dangerous_keywords:
                if keyword in validator_code:
                    return False
            
            return True
            
        except SyntaxError:
            return False
    
    def _load_policy_registry(self):
        """Load the policy registry from disk."""
        try:
            registry_file = self.repository_path / "registry.json"
            
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                
                for policy_name, metadata_dict in registry_data.items():
                    self.policy_registry[policy_name] = PolicyMetadata(**metadata_dict)
                    
        except Exception as e:
            logger.warning(f"Could not load policy registry: {str(e)}")
    
    def _save_policy_registry(self):
        """Save the policy registry to disk."""
        try:
            registry_file = self.repository_path / "registry.json"
            
            registry_data = {}
            for policy_name, metadata in self.policy_registry.items():
                registry_data[policy_name] = asdict(metadata)
            
            with open(registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save policy registry: {str(e)}")

# Global policy manager instance
policy_manager = None

def get_policy_manager(repository_path: str = "policy_repository") -> PolicyAsCodeManager:
    """
    Get or create the global policy manager instance.
    
    Args:
        repository_path: Path to the policy repository
        
    Returns:
        PolicyAsCodeManager instance
    """
    global policy_manager
    
    if policy_manager is None:
        policy_manager = PolicyAsCodeManager(repository_path)
    
    return policy_manager

