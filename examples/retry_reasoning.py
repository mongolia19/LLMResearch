"""
Retry reasoning example using the LLMResearch package.

This example demonstrates the retry mechanism for subtasks in the reasoning process.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.config import Config
from llm_research.reasoning import Reasoning


def main():
    """
    Run a retry reasoning example.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Retry reasoning example")
    parser.add_argument("--task", "-t", required=True, help="Task to solve")
    parser.add_argument("--steps", "-s", type=int, default=3, help="Number of reasoning steps")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Maximum number of retries per subtask")
    parser.add_argument("--provider", "-p", help="The LLM provider to use")
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
    
    # Create a reasoning manager
    reasoning = Reasoning(llm, max_steps=args.steps)
    
    print("\nSolving task with multi-step reasoning and retry mechanism...")
    print(f"Task: {args.task}")
    print(f"Using {args.steps} reasoning steps")
    print(f"Maximum retries per subtask: {args.retries}")
    print("\nThinking...\n")
    
    # Solve the task with retry mechanism
    try:
        result = reasoning.solve_task(
            task=args.task,
            max_tokens=1000,
            temperature=0.7,
            max_retries=args.retries  # Set the maximum number of retries
        )
        
        print("\nFinal Result:")
        print(result)
        
        # Print statistics
        print("\nReasoning Statistics:")
        steps = reasoning.get_steps()
        print(f"Total steps: {len(steps)}")
        
        # Count validation steps
        validation_steps = sum(1 for step in steps if "Evaluate if the following subtask has been completed" in step.prompt)
        print(f"Validation steps: {validation_steps}")
        
        # Calculate retry rate
        subtasks = len([step for step in steps if "Execute subtask:" in step.prompt])
        if subtasks > 0:
            retry_rate = (validation_steps - subtasks) / subtasks
            print(f"Retry rate: {retry_rate:.2f} retries per subtask")
        
    except Exception as e:
        print(f"Error during reasoning: {e}")


if __name__ == "__main__":
    main()