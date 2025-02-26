"""
OpenAI-compatible LLM provider implementation.
"""

import json
import requests
from typing import Dict, List, Optional, Union, Any, Iterator

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from llm_research.llm.base import BaseLLM


class OpenAILLM(BaseLLM):
    """
    OpenAI-compatible LLM provider implementation.
    
    This class implements the BaseLLM interface for OpenAI and compatible APIs.
    """
    
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        **kwargs
    ):
        """
        Initialize the OpenAI LLM provider.
        
        Args:
            model: The model name to use
            base_url: The base URL for the API (e.g., "https://api.openai.com/v1")
            api_key: The API key for authentication
            **kwargs: Additional provider-specific parameters
        """
        super().__init__(model, base_url, api_key, **kwargs)
        
        # Ensure base_url doesn't end with a slash
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        
        # Set up the API endpoint
        self.api_endpoint = f"{self.base_url}/chat/completions"
        
        # Set up the headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Set up the encoding for token counting
        self.encoding = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fall back to cl100k_base for unknown models
                self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def _create_messages(self, prompt: str) -> List[Dict[str, str]]:
        """
        Create the messages array for the API request.
        
        Args:
            prompt: The input prompt
            
        Returns:
            A list of message dictionaries
        """
        return [{"role": "user", "content": prompt}]
    
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
        # Create the request payload
        payload = {
            "model": self.model,
            "messages": self._create_messages(prompt),
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }
        
        # Add optional parameters if provided
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        if stop is not None:
            payload["stop"] = stop if isinstance(stop, list) else [stop]
        
        # Add any additional parameters
        for key, value in kwargs.items():
            payload[key] = value
        
        # Make the API request
        response = requests.post(
            self.api_endpoint,
            headers=self.headers,
            data=json.dumps(payload)
        )
        
        # Check for errors
        if response.status_code != 200:
            error_msg = f"API request failed with status code {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg += f": {error_data['error']['message']}"
            except:
                error_msg += f": {response.text}"
            
            raise Exception(error_msg)
        
        # Parse the response
        result = response.json()
        
        # Extract the generated text
        generated_text = result["choices"][0]["message"]["content"]
        
        # Return the result
        return {
            "text": generated_text,
            "raw_response": result
        }
    
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
    ) -> Iterator[str]:
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
        # Create the request payload
        payload = {
            "model": self.model,
            "messages": self._create_messages(prompt),
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stream": True
        }
        
        # Add optional parameters if provided
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        if stop is not None:
            payload["stop"] = stop if isinstance(stop, list) else [stop]
        
        # Add any additional parameters
        for key, value in kwargs.items():
            payload[key] = value
        
        # Make the API request
        response = requests.post(
            self.api_endpoint,
            headers=self.headers,
            data=json.dumps(payload),
            stream=True
        )
        
        # Check for errors
        if response.status_code != 200:
            error_msg = f"API request failed with status code {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg += f": {error_data['error']['message']}"
            except:
                error_msg += f": {response.text}"
            
            raise Exception(error_msg)
        
        # Process the streaming response
        for line in response.iter_lines():
            if line:
                # Remove the "data: " prefix
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                
                # Skip the "[DONE]" message
                if line == "[DONE]":
                    break
                
                try:
                    # Parse the JSON data
                    data = json.loads(line)
                    
                    # Extract the delta content if available
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                except json.JSONDecodeError:
                    # Skip invalid JSON
                    continue
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the provided text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        if TIKTOKEN_AVAILABLE and self.encoding is not None:
            return len(self.encoding.encode(text))
        else:
            # Fallback: rough estimate (not accurate)
            return len(text) // 4