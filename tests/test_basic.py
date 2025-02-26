"""
Basic tests for the LLMResearch package.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.config import Config
from llm_research.file_handler import FileHandler
from llm_research.conversation import Conversation, Message
from llm_research.reasoning import Reasoning
from llm_research.llm.base import BaseLLM
from llm_research.llm.openai import OpenAILLM
from llm_research.llm.custom import CustomLLM


class MockLLM(BaseLLM):
    """
    Mock LLM provider for testing.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__("mock-model", "https://mock-api.com", "mock-api-key")
        self.responses = {
            "default": {"text": "This is a mock response.", "raw_response": {}}
        }
    
    def set_response(self, prompt, response):
        """Set a specific response for a prompt."""
        self.responses[prompt] = response
    
    def generate(self, prompt, **kwargs):
        """Generate a response based on the prompt."""
        return self.responses.get(prompt, self.responses["default"])
    
    def generate_stream(self, prompt, **kwargs):
        """Generate a streaming response based on the prompt."""
        response = self.responses.get(prompt, self.responses["default"])
        yield response["text"]
    
    def count_tokens(self, text):
        """Count the number of tokens in the text."""
        return len(text) // 4


class TestConfig(unittest.TestCase):
    """
    Tests for the Config class.
    """
    
    def setUp(self):
        # Create a temporary config file
        self.config_path = "test_config.yaml"
        self.config = Config(self.config_path)
    
    def tearDown(self):
        # Remove the temporary config file
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
    
    def test_get_provider_config(self):
        """Test getting a provider configuration."""
        # The default provider should exist
        provider_config = self.config.get_provider_config()
        self.assertIsNotNone(provider_config)
        self.assertIn("base_url", provider_config)
        self.assertIn("model", provider_config)
    
    def test_set_provider_config(self):
        """Test setting a provider configuration."""
        # Set a new provider configuration
        provider_config = {
            "base_url": "https://test-api.com",
            "model": "test-model",
            "api_key": "test-api-key"
        }
        self.config.set_provider_config("test", provider_config)
        
        # Get the provider configuration
        retrieved_config = self.config.get_provider_config("test")
        self.assertEqual(retrieved_config["base_url"], "https://test-api.com")
        self.assertEqual(retrieved_config["model"], "test-model")
        self.assertEqual(retrieved_config["api_key"], "test-api-key")


class TestFileHandler(unittest.TestCase):
    """
    Tests for the FileHandler class.
    """
    
    def setUp(self):
        self.file_handler = FileHandler()
        
        # Create a temporary test file
        self.test_file_path = "test_file.txt"
        with open(self.test_file_path, "w", encoding="utf-8") as f:
            f.write("This is a test file.\n" * 10)
    
    def tearDown(self):
        # Remove the temporary test file
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
    
    def test_read_file(self):
        """Test reading a file."""
        content = self.file_handler.read_file(self.test_file_path)
        self.assertIn("This is a test file.", content)
    
    def test_chunk_text(self):
        """Test chunking text."""
        # Create a file handler with a smaller chunk size for testing
        small_chunk_handler = FileHandler(chunk_size=100, chunk_overlap=10)
        text = "This is a test.\n" * 20
        chunks = small_chunk_handler.chunk_text(text)
        self.assertGreater(len(chunks), 1)


class TestConversation(unittest.TestCase):
    """
    Tests for the Conversation class.
    """
    
    def setUp(self):
        self.llm = MockLLM()
        self.conversation = Conversation(self.llm, system_message="You are a helpful assistant.")
    
    def test_add_message(self):
        """Test adding a message."""
        self.conversation.add_message("user", "Hello!")
        messages = self.conversation.get_messages()
        self.assertEqual(len(messages), 2)  # System message + user message
        self.assertEqual(messages[1].role, "user")
        self.assertEqual(messages[1].content, "Hello!")
    
    def test_generate_response(self):
        """Test generating a response."""
        self.llm.set_response("Hello!", {"text": "Hi there! How can I help you?", "raw_response": {}})
        self.conversation.add_message("user", "Hello!")
        response = self.conversation.generate_response()
        self.assertEqual(response, "This is a mock response.")  # Using default response


class TestReasoning(unittest.TestCase):
    """
    Tests for the Reasoning class.
    """
    
    def setUp(self):
        self.llm = MockLLM()
        self.reasoning = Reasoning(self.llm)
    
    def test_add_step(self):
        """Test adding a reasoning step."""
        self.reasoning.add_step("What is 2+2?", "4")
        steps = self.reasoning.get_steps()
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].prompt, "What is 2+2?")
        self.assertEqual(steps[0].response, "4")
    
    def test_execute_step(self):
        """Test executing a reasoning step."""
        self.llm.set_response(
            "What is 2+2?",
            {"text": "2+2=4", "raw_response": {}}
        )
        response = self.reasoning.execute_step("What is 2+2?")
        self.assertEqual(response, "2+2=4")


if __name__ == "__main__":
    unittest.main()