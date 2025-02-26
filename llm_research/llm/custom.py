"""
Custom LLM provider implementation for non-standard APIs.
"""

import json
import requests
from typing import Dict, List, Optional, Union, Any, Iterator, Callable

from llm_research.llm.base import BaseLLM


class CustomLLM(BaseLLM):
    """
    Custom LLM provider implementation for non-standard APIs.
    
    This class allows for configuring custom request and response handling
    for LLM providers that don't follow the OpenAI API format.
    """
    
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        request_formatter: Optional[Callable] = None,
        response_parser: Optional[Callable] = None,
        stream_parser: Optional[Callable] = None,
        token_counter: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize the Custom LLM provider.
        
        Args:
            model: The model name to use
            base_url: The base URL for the API
            api_key: The API key for authentication
            request_formatter: Function to format the request payload
            response_parser: Function to parse the response
            stream_parser: Function to parse streaming responses
            token_counter: Function to count tokens
            **kwargs: Additional provider-specific parameters
        """
        super().__init__(model, base_url, api_key, **kwargs)
        
        # Ensure base_url doesn't end with a slash
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        
        # Set up the API endpoint (can be overridden in kwargs)
        self.api_endpoint = kwargs.get("api_endpoint", f"{self.base_url}/generate")
        
        # Set up the headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Update headers with any provided in kwargs
        if "headers" in kwargs:
            self.headers.update(kwargs["headers"])
        
        # Set up custom formatters and parsers
        self.request_formatter = request_formatter or self._default_request_formatter
        self.response_parser = response_parser or self._default_response_parser
        self.stream_parser = stream_parser or self._default_stream_parser
        self.token_counter = token_counter or self._default_token_counter
    
    def _default_request_formatter(
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
        Default request formatter.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            stop: Stop sequences to end generation
            **kwargs: Additional parameters
            
        Returns:
            A dictionary containing the request payload
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
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
        
        return payload
    
    def _default_response_parser(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default response parser.
        
        Args:
            response_data: The raw response data
            
        Returns:
            A dictionary containing the parsed response
        """
        # Try to extract text from common response formats
        text = ""
        
        if "choices" in response_data and len(response_data["choices"]) > 0:
            # OpenAI-like format
            choice = response_data["choices"][0]
            if "text" in choice:
                text = choice["text"]
            elif "message" in choice and "content" in choice["message"]:
                text = choice["message"]["content"]
        elif "output" in response_data:
            # Some APIs use an "output" field
            text = response_data["output"]
        elif "generated_text" in response_data:
            # Some APIs use a "generated_text" field
            text = response_data["generated_text"]
        elif "response" in response_data:
            # Some APIs use a "response" field
            text = response_data["response"]
        
        return {
            "text": text,
            "raw_response": response_data
        }
    
    def _default_stream_parser(self, chunk: str) -> Optional[str]:
        """
        Default stream parser.
        
        Args:
            chunk: A chunk of the streaming response
            
        Returns:
            The parsed text chunk, or None if no text was found
        """
        try:
            data = json.loads(chunk)
            
            # Try to extract text from common streaming formats
            if "choices" in data and len(data["choices"]) > 0:
                # OpenAI-like format
                choice = data["choices"][0]
                if "text" in choice:
                    return choice["text"]
                elif "delta" in choice and "content" in choice["delta"]:
                    return choice["delta"]["content"]
            elif "output" in data:
                return data["output"]
            elif "generated_text" in data:
                return data["generated_text"]
            elif "response" in data:
                return data["response"]
            
            return None
        except json.JSONDecodeError:
            return None
    
    def _default_token_counter(self, text: str) -> int:
        """
        Default token counter.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The estimated number of tokens
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
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
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            stop: Stop sequences to end generation
            **kwargs: Additional parameters
            
        Returns:
            A dictionary containing the generated text and metadata
        """
        # Format the request payload
        payload = self.request_formatter(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            **kwargs
        )
        
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
        
        # Parse the response using the custom parser
        return self.response_parser(result)
    
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
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            stop: Stop sequences to end generation
            **kwargs: Additional parameters
            
        Returns:
            An iterator yielding generated text chunks
        """
        # Format the request payload
        payload = self.request_formatter(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=True,
            **kwargs
        )
        
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
                line = line.decode("utf-8")
                
                # Remove the "data: " prefix if present
                if line.startswith("data: "):
                    line = line[6:]
                
                # Skip the "[DONE]" message
                if line == "[DONE]":
                    break
                
                # Parse the chunk using the custom parser
                chunk_text = self.stream_parser(line)
                if chunk_text:
                    yield chunk_text
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the provided text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        return self.token_counter(text)