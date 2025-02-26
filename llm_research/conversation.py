"""
Conversation management for LLM interactions.
"""

import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict

from llm_research.llm.base import BaseLLM


@dataclass
class Message:
    """
    A message in a conversation.
    """
    role: str  # "system", "user", "assistant", or "function"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Conversation:
    """
    Conversation manager for LLM interactions.
    
    This class handles maintaining conversation history, formatting prompts,
    and processing LLM responses.
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        system_message: Optional[str] = None,
        max_history: int = 10,
        token_limit: int = 4000
    ):
        """
        Initialize the conversation manager.
        
        Args:
            llm: The LLM provider to use
            system_message: The system message to use (optional)
            max_history: Maximum number of messages to keep in history
            token_limit: Maximum number of tokens to include in the prompt
        """
        self.llm = llm
        self.max_history = max_history
        self.token_limit = token_limit
        self.messages: List[Message] = []
        
        # Add the system message if provided
        if system_message:
            self.add_message("system", system_message)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: The role of the message sender ("system", "user", "assistant", or "function")
            content: The message content
            metadata: Additional metadata for the message (optional)
        """
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {}
        ))
        
        # Trim the history if it exceeds the maximum
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    def get_messages(self) -> List[Message]:
        """
        Get all messages in the conversation.
        
        Returns:
            A list of messages
        """
        return self.messages
    
    def get_formatted_messages(self) -> List[Dict[str, str]]:
        """
        Get messages formatted for the LLM API.
        
        Returns:
            A list of message dictionaries
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
    
    def get_prompt(self) -> str:
        """
        Get the conversation as a formatted prompt string.
        
        Returns:
            The formatted prompt
        """
        prompt = ""
        
        for msg in self.messages:
            if msg.role == "system":
                prompt += f"System: {msg.content}\n\n"
            elif msg.role == "user":
                prompt += f"User: {msg.content}\n\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n\n"
            elif msg.role == "function":
                prompt += f"Function: {msg.content}\n\n"
        
        prompt += "Assistant: "
        
        return prompt
    
    def _trim_messages_to_token_limit(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Trim messages to fit within the token limit.
        
        Args:
            messages: The messages to trim
            
        Returns:
            The trimmed messages
        """
        # Count tokens in the messages
        total_tokens = 0
        for msg in messages:
            total_tokens += self.llm.count_tokens(msg["content"])
            # Add some overhead for the message format
            total_tokens += 4  # Approximate overhead per message
        
        # If we're within the limit, return the messages as is
        if total_tokens <= self.token_limit:
            return messages
        
        # Otherwise, trim the messages
        trimmed_messages = []
        current_tokens = 0
        
        # Always keep the system message if present
        if messages and messages[0]["role"] == "system":
            system_msg = messages[0]
            system_tokens = self.llm.count_tokens(system_msg["content"]) + 4
            trimmed_messages.append(system_msg)
            current_tokens += system_tokens
            messages = messages[1:]
        
        # Add messages from the end (most recent first)
        for msg in reversed(messages):
            msg_tokens = self.llm.count_tokens(msg["content"]) + 4
            
            if current_tokens + msg_tokens <= self.token_limit:
                trimmed_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # If we can't add the full message, try to add a truncated version
                available_tokens = self.token_limit - current_tokens - 4
                if available_tokens > 20:  # Only add if we can include a meaningful amount
                    # Truncate the message content
                    truncated_content = msg["content"]
                    while self.llm.count_tokens(truncated_content) > available_tokens:
                        # Remove ~10% of the content at a time
                        truncate_point = int(len(truncated_content) * 0.9)
                        truncated_content = truncated_content[:truncate_point]
                    
                    # Add the truncated message
                    truncated_msg = msg.copy()
                    truncated_msg["content"] = truncated_content + "..."
                    trimmed_messages.insert(0, truncated_msg)
                
                break
        
        return trimmed_messages
    
    def generate_response(
        self,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM based on the conversation history.
        
        Args:
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The generated response
        """
        # Format the messages for the LLM
        messages = self.get_formatted_messages()
        
        # Trim the messages to fit within the token limit
        messages = self._trim_messages_to_token_limit(messages)
        
        # Generate the response
        if hasattr(self.llm, "chat") and callable(getattr(self.llm, "chat")):
            # Use the chat method if available
            response = self.llm.chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            generated_text = response["text"]
        else:
            # Fall back to the generate method
            prompt = self.get_prompt()
            response = self.llm.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            generated_text = response["text"]
        
        # Add the response to the conversation
        self.add_message("assistant", generated_text)
        
        return generated_text
    
    def generate_response_stream(
        self,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Generate a streaming response from the LLM.
        
        Args:
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            An iterator yielding response chunks
        """
        # Format the messages for the LLM
        messages = self.get_formatted_messages()
        
        # Trim the messages to fit within the token limit
        messages = self._trim_messages_to_token_limit(messages)
        
        # Generate the response
        if hasattr(self.llm, "chat_stream") and callable(getattr(self.llm, "chat_stream")):
            # Use the chat_stream method if available
            response_stream = self.llm.chat_stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
        else:
            # Fall back to the generate_stream method
            prompt = self.get_prompt()
            response_stream = self.llm.generate_stream(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
        
        # Collect the full response
        full_response = ""
        
        # Yield each chunk
        for chunk in response_stream:
            full_response += chunk
            yield chunk
        
        # Add the full response to the conversation
        self.add_message("assistant", full_response)
    
    def save_conversation(self, file_path: str) -> None:
        """
        Save the conversation to a file.
        
        Args:
            file_path: Path to save the conversation to
        """
        # Convert the messages to dictionaries
        messages_dict = [asdict(msg) for msg in self.messages]
        
        # Save the conversation to the file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(messages_dict, f, indent=2)
    
    def load_conversation(self, file_path: str) -> None:
        """
        Load a conversation from a file.
        
        Args:
            file_path: Path to load the conversation from
        """
        # Load the conversation from the file
        with open(file_path, "r", encoding="utf-8") as f:
            messages_dict = json.load(f)
        
        # Convert the dictionaries to Message objects
        self.messages = [Message(**msg) for msg in messages_dict]
    
    def clear_conversation(self) -> None:
        """
        Clear the conversation history.
        """
        # Keep the system message if present
        system_message = next((msg for msg in self.messages if msg.role == "system"), None)
        
        self.messages = []
        
        if system_message:
            self.messages.append(system_message)