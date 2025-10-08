"""
Plugin System for Guardrails API

This module provides a plugin architecture that allows for easy replacement
of the guardrails implementation. The system supports loading different
guardrails providers (e.g., Guardrails AI, OpenAI Moderation, custom implementations)
through a standardized interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import importlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Standard validation result format across all plugins."""
    validator_name: str
    status: str  # "pass" or "fail"
    message: str
    on_fail_action: str
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class GuardrailsResponse:
    """Standard response format for all guardrails plugins."""
    status: str  # "success" or "failure"
    message: str
    valid: bool
    validations: List[ValidationResult]
    processed_text: Optional[str] = None
    plugin_name: str = ""
    execution_time_ms: Optional[float] = None

class GuardrailsPlugin(ABC):
    """
    Abstract base class for all guardrails plugins.
    
    This interface ensures that any guardrails implementation can be
    easily swapped in without changing the API contract.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this plugin."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of this plugin."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the plugin with configuration.
        
        Args:
            config: Plugin-specific configuration dictionary
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_text(self, text: str, guardrail_name: str, context: Optional[Dict[str, Any]] = None) -> GuardrailsResponse:
        """
        Validate text using the plugin's implementation.
        
        Args:
            text: The text to validate
            guardrail_name: Name of the guardrail configuration to use
            context: Optional context information
            
        Returns:
            GuardrailsResponse with validation results
        """
        pass
    
    @abstractmethod
    def get_available_guardrails(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of available guardrail configurations.
        
        Returns:
            Dictionary mapping guardrail names to their configurations
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the plugin is healthy and ready to process requests.
        
        Returns:
            True if healthy, False otherwise
        """
        pass

class MockGuardrailsPlugin(GuardrailsPlugin):
    """
    Mock implementation of guardrails plugin for testing and development.
    This is the default plugin that provides the mock validation logic.
    """
    
    def __init__(self):
        self._initialized = False
        self._config = {}
    
    @property
    def name(self) -> str:
        return "mock_guardrails"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the mock plugin with configuration."""
        try:
            self._config = config
            self._initialized = True
            logger.info(f"Mock guardrails plugin initialized with config: {list(config.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize mock plugin: {str(e)}")
            return False
    
    def validate_text(self, text: str, guardrail_name: str, context: Optional[Dict[str, Any]] = None) -> GuardrailsResponse:
        """Validate text using mock implementation."""
        import time
        start_time = time.time()
        
        try:
            # Import the existing mock validation logic
            from src.routes.guardrails import validate_text_with_mock_guardrails, ValidationContext
            
            # Convert context to ValidationContext if provided
            validation_context = None
            if context:
                validation_context = ValidationContext(**context)
            
            # Use the existing mock validation
            result = validate_text_with_mock_guardrails(text, guardrail_name, validation_context)
            
            # Convert to plugin response format
            validations = []
            for v in result.validations:
                validations.append(ValidationResult(
                    validator_name=v.validator_name,
                    status=v.status,
                    message=v.message,
                    on_fail_action=v.on_fail_action
                ))
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return GuardrailsResponse(
                status=result.status,
                message=result.message,
                valid=result.valid,
                validations=validations,
                processed_text=result.processed_text,
                plugin_name=self.name,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error in mock validation: {str(e)}")
            return GuardrailsResponse(
                status="failure",
                message=f"Plugin error: {str(e)}",
                valid=False,
                validations=[],
                plugin_name=self.name
            )
    
    def get_available_guardrails(self) -> Dict[str, Dict[str, Any]]:
        """Get available guardrail configurations from config."""
        from config import GUARDRAIL_CONFIGS
        return GUARDRAIL_CONFIGS
    
    def health_check(self) -> bool:
        """Check if the mock plugin is healthy."""
        return self._initialized

class OpenAIModerationPlugin(GuardrailsPlugin):
    """
    Plugin that uses OpenAI's Moderation API for content filtering.
    This demonstrates how to integrate with external services.
    """
    
    def __init__(self):
        self._initialized = False
        self._api_key = None
    
    @property
    def name(self) -> str:
        return "openai_moderation"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize OpenAI moderation plugin."""
        try:
            self._api_key = config.get('openai_api_key')
            if not self._api_key:
                logger.warning("OpenAI API key not provided, plugin will not be functional")
                return False
            
            self._initialized = True
            logger.info("OpenAI moderation plugin initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI moderation plugin: {str(e)}")
            return False
    
    def validate_text(self, text: str, guardrail_name: str, context: Optional[Dict[str, Any]] = None) -> GuardrailsResponse:
        """Validate text using OpenAI Moderation API."""
        import time
        start_time = time.time()
        
        if not self._initialized or not self._api_key:
            return GuardrailsResponse(
                status="failure",
                message="Plugin not properly initialized",
                valid=False,
                validations=[],
                plugin_name=self.name
            )
        
        try:
            # This would make an actual API call to OpenAI
            # For demo purposes, we'll simulate the response
            validations = [
                ValidationResult(
                    validator_name="openai_moderation",
                    status="pass",  # Would be determined by API response
                    message="Content passed OpenAI moderation",
                    on_fail_action="exception",
                    confidence=0.95
                )
            ]
            
            execution_time = (time.time() - start_time) * 1000
            
            return GuardrailsResponse(
                status="success",
                message="OpenAI moderation completed",
                valid=True,
                validations=validations,
                plugin_name=self.name,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error in OpenAI moderation: {str(e)}")
            return GuardrailsResponse(
                status="failure",
                message=f"OpenAI moderation error: {str(e)}",
                valid=False,
                validations=[],
                plugin_name=self.name
            )
    
    def get_available_guardrails(self) -> Dict[str, Dict[str, Any]]:
        """Get available OpenAI moderation configurations."""
        return {
            "openai_content_policy": {
                "description": "OpenAI content policy moderation",
                "validators": ["openai_moderation"]
            }
        }
    
    def health_check(self) -> bool:
        """Check if OpenAI moderation is available."""
        return self._initialized and self._api_key is not None

class PluginManager:
    """
    Manages loading and switching between different guardrails plugins.
    """
    
    def __init__(self):
        self._plugins: Dict[str, GuardrailsPlugin] = {}
        self._active_plugin: Optional[GuardrailsPlugin] = None
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_plugin(self, plugin: GuardrailsPlugin, config: Dict[str, Any] = None) -> bool:
        """
        Register a new plugin with the manager.
        
        Args:
            plugin: The plugin instance to register
            config: Configuration for the plugin
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            if config and not plugin.initialize(config):
                logger.error(f"Failed to initialize plugin {plugin.name}")
                return False
            
            self._plugins[plugin.name] = plugin
            self._plugin_configs[plugin.name] = config or {}
            
            # Set as active plugin if it's the first one
            if self._active_plugin is None:
                self._active_plugin = plugin
            
            logger.info(f"Plugin {plugin.name} v{plugin.version} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering plugin {plugin.name}: {str(e)}")
            return False
    
    def switch_plugin(self, plugin_name: str) -> bool:
        """
        Switch to a different plugin.
        
        Args:
            plugin_name: Name of the plugin to switch to
            
        Returns:
            True if switch successful, False otherwise
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin {plugin_name} not found")
            return False
        
        plugin = self._plugins[plugin_name]
        if not plugin.health_check():
            logger.error(f"Plugin {plugin_name} is not healthy")
            return False
        
        self._active_plugin = plugin
        logger.info(f"Switched to plugin: {plugin_name}")
        return True
    
    def get_active_plugin(self) -> Optional[GuardrailsPlugin]:
        """Get the currently active plugin."""
        return self._active_plugin
    
    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """List all registered plugins and their status."""
        plugins_info = {}
        for name, plugin in self._plugins.items():
            plugins_info[name] = {
                "name": plugin.name,
                "version": plugin.version,
                "healthy": plugin.health_check(),
                "active": plugin == self._active_plugin
            }
        return plugins_info
    
    def load_plugin_from_module(self, module_path: str, class_name: str, config: Dict[str, Any] = None) -> bool:
        """
        Dynamically load a plugin from a Python module.
        
        Args:
            module_path: Path to the module (e.g., 'plugins.custom_guardrails')
            class_name: Name of the plugin class
            config: Configuration for the plugin
            
        Returns:
            True if loading successful, False otherwise
        """
        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            plugin_instance = plugin_class()
            
            return self.register_plugin(plugin_instance, config)
            
        except Exception as e:
            logger.error(f"Error loading plugin from {module_path}.{class_name}: {str(e)}")
            return False

# Global plugin manager instance
plugin_manager = PluginManager()

def initialize_default_plugins():
    """Initialize the default plugins."""
    # Register mock plugin as default
    mock_plugin = MockGuardrailsPlugin()
    plugin_manager.register_plugin(mock_plugin, {})
    
    # Register OpenAI moderation plugin (will not be functional without API key)
    openai_plugin = OpenAIModerationPlugin()
    plugin_manager.register_plugin(openai_plugin, {})
    
    logger.info("Default plugins initialized")

# Initialize plugins when module is imported
initialize_default_plugins()

