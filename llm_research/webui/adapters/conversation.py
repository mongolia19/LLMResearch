"""
Adapter for conversation functionality.
"""

from typing import List, Dict, Any, Optional, Iterator

from llm_research.llm.base import BaseLLM
from llm_research.conversation import Conversation as LLMConversation

class ConversationAdapter:
    """
    Adapter for the LLMResearch conversation functionality.
    
    This class provides a simplified interface to the LLMResearch conversation
    functionality for use in the WebUI.
    """
    
    def __init__(self, llm: BaseLLM, system_message: Optional[str] = None):
        """
        Initialize the conversation adapter.
        
        Args:
            llm: The LLM provider to use
            system_message: Optional system message to initialize the conversation
        """
        self.llm = llm
        self.conversation = LLMConversation(llm, system_message=system_message)
        self.context = ""
    
    def add_context(self, context: str) -> None:
        """
        Add context to the conversation.
        
        Args:
            context: The context to add
        """
        self.context += context + "\n\n"
        self.conversation.add_context(self.context)
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: The role of the message sender
            content: The message content
        """
        self.conversation.add_message(role, content)
    
    def generate_response(self, temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            The generated response
        """
        return self.conversation.generate_response(
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def generate_response_stream(self, temperature: float = 0.7, max_tokens: Optional[int] = None) -> Iterator[str]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            An iterator yielding response chunks
        """
        return self.conversation.generate_response_stream(
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            A list of message dictionaries
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in self.conversation.get_messages()
        ]
    
    def clear_history(self, keep_system_message: bool = True) -> None:
        """
        Clear the conversation history.
        
        Args:
            keep_system_message: Whether to keep the system message
        """
        self.conversation.clear_conversation()
        
        # Re-add the context if any
        if self.context:
            self.conversation.add_context(self.context)