"""
File-based reasoning example using the LLMResearch package.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.config import Config
from llm_research.file_handler import FileHandler
from llm_research.reasoning import Reasoning


def main():
    """
    Run a file-based reasoning example.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="File-based reasoning example")
    parser.add_argument("--file", "-f", required=True, help="Path to the file to analyze")
    parser.add_argument("--question", "-q", required=True, help="Question to answer about the file")
    parser.add_argument("--steps", "-s", type=int, default=3, help="Number of reasoning steps")
    parser.add_argument("--provider", "-p", help="The LLM provider to use")
    args = parser.parse_args()
    
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("No .env file found. Using environment variables.")
    
    # Check if the file exists
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        return
    
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
    
    # Create a file handler
    file_handler = FileHandler()
    
    # Read the file
    try:
        file_content = file_handler.read_file(args.file)
        print(f"Read file: {args.file} ({len(file_content)} characters)")
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Create a reasoning manager
    reasoning = Reasoning(llm, max_steps=args.steps)
    
    print("\nAnalyzing file with multi-step reasoning...")
    print(f"Question: {args.question}")
    print(f"Using {args.steps} reasoning steps")
    print("\nThinking...\n")
    
    # Perform chain-of-thought reasoning
    try:
        result = reasoning.chain_of_thought(
            question=args.question,
            context=file_content,
            temperature=0.7
        )
        
        print("Answer:")
        print(result)
        
        # Print the reasoning steps
        print("\nReasoning Steps:")
        for i, step in enumerate(reasoning.get_steps()):
            print(f"\nStep {i+1}:")
            print(f"Prompt: {step.prompt[:100]}..." if len(step.prompt) > 100 else f"Prompt: {step.prompt}")
            print(f"Response: {step.response}")
    except Exception as e:
        print(f"Error during reasoning: {e}")


if __name__ == "__main__":
    main()