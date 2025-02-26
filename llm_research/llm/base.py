"""
Base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    
    This class defines the interface that all LLM provider implementations must follow.
    """
    
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        **kwargs
    ):
        """
        Initialize the LLM provider.
        
        Args:
            model: The model name to use
            base_url: The base URL for the API
            api_key: The API key for authentication
            **kwargs: Additional provider-specific parameters
        """
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.kwargs = kwargs
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text based on the provided prompt.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            stop: Stop sequences to end generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            A dictionary containing the generated text and metadata
        """
        pass
    
    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ):
        """
        Generate text in a streaming fashion.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            stop: Stop sequences to end generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            An iterator yielding generated text chunks
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the provided text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        pass