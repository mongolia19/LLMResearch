"""
Configuration management for LLM providers.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """
    Configuration manager for LLM providers.
    
    This class handles loading, saving, and managing LLM configurations.
    """
    
    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file (optional)
            env_file: Path to the .env file (optional)
        """
        # Load environment variables from .env file
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
        else:
            # Try to load from default locations
            for env_path in ['.env', os.path.join(os.path.dirname(__file__), '..', '.env')]:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    break
        
        # Set the default config path if not provided
        if config_path is None:
            home_dir = os.path.expanduser("~")
            self.config_path = os.path.join(home_dir, ".llm_research", "config.yaml")
        else:
            self.config_path = config_path
        
        # Create the config directory if it doesn't exist
        config_dir = os.path.dirname(self.config_path)
        if config_dir:  # Only create directory if path is not empty
            os.makedirs(config_dir, exist_ok=True)
        
        # Load the configuration
        self.config = self._load_config()
        
        # Update configuration with environment variables
        self._update_from_env()
    
    def _update_from_env(self) -> None:
        """
        Update the configuration with environment variables.
        """
        # Ensure the llm_providers section exists
        if "llm_providers" not in self.config:
            self.config["llm_providers"] = {}
        
        # Update OpenAI configuration
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        openai_base_url = os.environ.get("OPENAI_BASE_URL")
        openai_model = os.environ.get("OPENAI_MODEL")
        
        if any([openai_api_key, openai_base_url, openai_model]):
            if "openai" not in self.config["llm_providers"]:
                self.config["llm_providers"]["openai"] = {}
            
            if openai_api_key:
                self.config["llm_providers"]["openai"]["api_key"] = openai_api_key
            
            if openai_base_url:
                self.config["llm_providers"]["openai"]["base_url"] = openai_base_url
            
            if openai_model:
                self.config["llm_providers"]["openai"]["model"] = openai_model
        
        # Update custom LLM configuration
        custom_llm_name = os.environ.get("CUSTOM_LLM_NAME")
        custom_llm_api_key = os.environ.get("CUSTOM_LLM_API_KEY")
        custom_llm_base_url = os.environ.get("CUSTOM_LLM_BASE_URL")
        custom_llm_model = os.environ.get("CUSTOM_LLM_MODEL")
        
        if custom_llm_name and any([custom_llm_api_key, custom_llm_base_url, custom_llm_model]):
            if custom_llm_name not in self.config["llm_providers"]:
                self.config["llm_providers"][custom_llm_name] = {
                    "type": "custom"
                }
            
            if custom_llm_api_key:
                self.config["llm_providers"][custom_llm_name]["api_key"] = custom_llm_api_key
            
            if custom_llm_base_url:
                self.config["llm_providers"][custom_llm_name]["base_url"] = custom_llm_base_url
            
            if custom_llm_model:
                self.config["llm_providers"][custom_llm_name]["model"] = custom_llm_model
        
        # Update default provider
        default_provider = os.environ.get("DEFAULT_LLM_PROVIDER")
        if default_provider and default_provider in self.config["llm_providers"]:
            self.config["default_provider"] = default_provider
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the config file.
        
        Returns:
            The configuration dictionary
        """
        # Check if the config file exists
        if not os.path.exists(self.config_path):
            # Create a default configuration
            default_config = {
                "llm_providers": {
                    "openai": {
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-3.5-turbo",
                        "api_key": ""
                    }
                },
                "default_provider": "openai"
            }
            
            # Save the default configuration
            self._save_config(default_config)
            
            return default_config
        
        # Load the configuration from the file
        with open(self.config_path, "r", encoding="utf-8") as f:
            if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
                return yaml.safe_load(f) or {}
            else:
                return json.load(f)
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        Save the configuration to the config file.
        
        Args:
            config: The configuration dictionary
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
                yaml.dump(config, f, default_flow_style=False)
            else:
                json.dump(config, f, indent=2)
    
    def get_provider_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the configuration for a specific provider.
        
        Args:
            provider_name: The name of the provider (optional, uses default if not provided)
            
        Returns:
            The provider configuration
            
        Raises:
            ValueError: If the provider doesn't exist
        """
        # Use the default provider if not specified
        if provider_name is None:
            provider_name = self.config.get("default_provider", "openai")
        
        # Check if the provider exists
        if provider_name not in self.config.get("llm_providers", {}):
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        # Return the provider configuration
        return self.config["llm_providers"][provider_name]
    
    def set_provider_config(self, provider_name: str, config: Dict[str, Any]) -> None:
        """
        Set the configuration for a specific provider.
        
        Args:
            provider_name: The name of the provider
            config: The provider configuration
        """
        # Ensure the llm_providers section exists
        if "llm_providers" not in self.config:
            self.config["llm_providers"] = {}
        
        # Update the provider configuration
        self.config["llm_providers"][provider_name] = config
        
        # Save the configuration
        self._save_config(self.config)
    
    def set_api_key(self, provider_name: str, api_key: str) -> None:
        """
        Set the API key for a specific provider.
        
        Args:
            provider_name: The name of the provider
            api_key: The API key
            
        Raises:
            ValueError: If the provider doesn't exist
        """
        # Check if the provider exists
        if provider_name not in self.config.get("llm_providers", {}):
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        # Update the API key
        self.config["llm_providers"][provider_name]["api_key"] = api_key
        
        # Save the configuration
        self._save_config(self.config)
    
    def set_default_provider(self, provider_name: str) -> None:
        """
        Set the default provider.
        
        Args:
            provider_name: The name of the provider
            
        Raises:
            ValueError: If the provider doesn't exist
        """
        # Check if the provider exists
        if provider_name not in self.config.get("llm_providers", {}):
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        # Update the default provider
        self.config["default_provider"] = provider_name
        
        # Save the configuration
        self._save_config(self.config)
    
    def list_providers(self) -> List[str]:
        """
        List all configured providers.
        
        Returns:
            A list of provider names
        """
        return list(self.config.get("llm_providers", {}).keys())
    
    def delete_provider(self, provider_name: str) -> None:
        """
        Delete a provider configuration.
        
        Args:
            provider_name: The name of the provider
            
        Raises:
            ValueError: If the provider doesn't exist or is the default provider
        """
        # Check if the provider exists
        if provider_name not in self.config.get("llm_providers", {}):
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        # Check if the provider is the default provider
        if provider_name == self.config.get("default_provider"):
            raise ValueError(f"Cannot delete the default provider '{provider_name}'")
        
        # Delete the provider
        del self.config["llm_providers"][provider_name]
        
        # Save the configuration
        self._save_config(self.config)