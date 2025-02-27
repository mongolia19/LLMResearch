"""
Web search reasoning example using the LLMResearch package.

This example demonstrates how to use the web search feature in the reasoning process.
"""

import os
import sys
import argparse
import getpass
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.config import Config
from llm_research.reasoning import Reasoning
from llm_research.web_search import get_web_search_tool


def main():
    """
    Run a web search reasoning example.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Web search reasoning example")
    parser.add_argument("--task", "-t", required=True, help="Task to solve")
    parser.add_argument("--steps", "-s", type=int, default=3, help="Number of reasoning steps")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Maximum number of retry attempts per subtask")
    parser.add_argument("--provider", "-p", help="The LLM provider to use")
    parser.add_argument("--bocha-api-key", "-k", help="Bocha API key for web search")
    args = parser.parse_args()
    
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
        provider_name = args.provider or os.environ.get("DEFAULT_LLM_PROVIDER", "openai")
        
        # Get the LLM provider from the configuration
        from llm_research.main import get_llm_provider
        llm = get_llm_provider(config, provider_name)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Initialize web search tool
    web_search_tool = None
    try:
        # Get the API key from the parameter, environment variable, or config
        api_key = args.bocha_api_key or os.environ.get("BOCHA_API_KEY")
        
        # If no API key is provided, check the config
        if not api_key:
            provider_config = config.get_provider_config("bocha")
            api_key = provider_config.get("api_key") if provider_config else None
        
        # If still no API key, prompt the user
        if not api_key:
            import getpass
            api_key = getpass.getpass("Enter Bocha API key: ")
            
            # Save the API key in the config
            if api_key:
                bocha_config = {
                    "api_key": api_key,
                    "type": "web_search"
                }
                config.set_provider_config("bocha", bocha_config)
        
        if api_key:
            web_search_tool = get_web_search_tool(api_key=api_key)
            print("Web search enabled using Bocha API")
        else:
            print("Web search disabled: No API key provided")
    except Exception as e:
        print(f"Error initializing web search: {e}")
    
    # Create a reasoning manager with web search
    reasoning = Reasoning(llm, max_steps=args.steps, web_search=web_search_tool)
    
    print("\nSolving task with multi-step reasoning and web search...")
    print(f"Task: {args.task}")
    print(f"Using {args.steps} reasoning steps")
    print(f"Maximum retries per subtask: {args.retries}")
    print("\nThinking...\n")
    
    # Solve the task with web search
    try:
        result = reasoning.solve_task(
            task=args.task,
            max_tokens=1000,
            temperature=0.7,
            max_retries=args.retries,
            web_search_enabled=True
        )
        
        print("\nFinal Result:")
        print(result)
        
        # Print statistics
        print("\nReasoning Statistics:")
        steps = reasoning.get_steps()
        print(f"Total steps: {len(steps)}")
        
        # Count search steps
        search_steps = sum(1 for step in steps if "SEARCH:" in step.response)
        print(f"Web search steps: {search_steps}")
        
    except Exception as e:
        print(f"Error during reasoning: {e}")


if __name__ == "__main__":
    main()