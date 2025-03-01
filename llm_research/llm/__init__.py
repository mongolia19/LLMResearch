"""
LLM module for interfacing with various large language model providers.
"""

from typing import Optional
from llm_research.config import Config
from llm_research.llm.base import BaseLLM
from llm_research.llm.openai import OpenAILLM
from llm_research.llm.custom import CustomLLM
import getpass

def get_llm_provider(config: Config, provider_name: Optional[str] = None) -> BaseLLM:
    """
    Get an LLM provider instance based on the configuration.
    
    Args:
        config: The configuration manager
        provider_name: The name of the provider to use (optional)
        
    Returns:
        An LLM provider instance
    """
    # Get the provider configuration
    provider_config = config.get_provider_config(provider_name)
    
    # Check if the API key is set
    if not provider_config.get("api_key"):
        # Prompt for the API key
        api_key = getpass.getpass(f"Enter API key for {provider_name or 'default provider'}: ")
        provider_config["api_key"] = api_key
        
        # Save the API key
        config.set_provider_config(provider_name or config.config.get("default_provider", "openai"), provider_config)
    
    # Create the LLM provider instance
    provider_type = provider_config.get("type", "openai")
    
    if provider_type == "openai":
        return OpenAILLM(
            model=provider_config.get("model", "gpt-3.5-turbo"),
            base_url=provider_config.get("base_url", "https://api.openai.com/v1"),
            api_key=provider_config["api_key"]
        )
    else:
        return CustomLLM(
            model=provider_config.get("model", "default"),
            base_url=provider_config.get("base_url", ""),
            api_key=provider_config["api_key"],
            **provider_config.get("options", {})
        )

__all__ = ["BaseLLM", "OpenAILLM", "CustomLLM", "get_llm_provider"]