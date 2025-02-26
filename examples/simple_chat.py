"""
Simple chat example using the LLMResearch package.
"""

import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.config import Config
from llm_research.conversation import Conversation


def main():
    """
    Run a simple chat example.
    """
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("No .env file found. Using environment variables.")
    
    # Create a configuration manager
    config = Config()
    
    # Get the LLM provider
    try:
        # This will automatically use the configuration from the .env file
        provider_name = os.environ.get("DEFAULT_LLM_PROVIDER", "openai")
        provider_config = config.get_provider_config(provider_name)
        
        # Check if API key is set
        if not provider_config.get("api_key"):
            print(f"No API key found for provider '{provider_name}'.")
            print("Please set the appropriate API key in your .env file or environment variables.")
            print("Example: OPENAI_API_KEY=your_api_key")
            return
        
        # Get the LLM provider from the configuration
        from llm_research.main import get_llm_provider
        llm = get_llm_provider(config, provider_name)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Create a conversation manager
    conversation = Conversation(
        llm=llm,
        system_message="You are a helpful assistant that provides concise answers."
    )
    
    print("Simple Chat Example")
    print("-------------------")
    print("Type 'exit' or 'quit' to end the conversation.")
    print()
    
    # Start the chat loop
    while True:
        # Get user input
        user_input = input("You: ")
        
        # Check if the user wants to exit
        if user_input.lower() in ["exit", "quit"]:
            break
        
        # Add the user message to the conversation
        conversation.add_message("user", user_input)
        
        # Generate a response
        print("Assistant: ", end="", flush=True)
        
        try:
            # Use streaming for a more interactive experience
            for chunk in conversation.generate_response_stream(temperature=0.7):
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nThank you for chatting!")


if __name__ == "__main__":
    main()