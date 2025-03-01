"""
Configuration for the LLMResearch WebUI.
"""

import os
import json
from typing import Dict, Any, Optional

class WebUIConfig:
    """
    Configuration manager for the WebUI.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file (optional)
        """
        self.config_path = config_path or os.path.join(
            os.path.expanduser('~'),
            '.llm_research',
            'webui_config.json'
        )
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the file.
        
        Returns:
            The configuration dictionary
        """
        # Default configuration
        default_config = {
            'theme': 'light',
            'max_history': 100,
            'web_search_enabled': True,
            'extract_url_content': True,
            'temperature': 0.7,
            'max_tokens': None,
            'reasoning_steps': 5,
            'retries': 3
        }
        
        # Try to load from file
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                # Update with defaults for missing keys
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default if file doesn't exist or is invalid
            return default_config
    
    def save_config(self) -> None:
        """
        Save the configuration to the file.
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Save the configuration
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key
            default: Default value if the key doesn't exist
            
        Returns:
            The configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key
            value: The configuration value
        """
        self.config[key] = value
        self.save_config()
    
    def update(self, config: Dict[str, Any]) -> None:
        """
        Update multiple configuration values.
        
        Args:
            config: Dictionary of configuration values to update
        """
        self.config.update(config)
        self.save_config()