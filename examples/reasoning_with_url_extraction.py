"""
Example script demonstrating multi-step reasoning with URL content extraction.

This script shows how to use the reasoning system with URL content extraction
to solve complex tasks that require retrieving and analyzing information from the web.
"""

import os
import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Add the parent directory to the path so we can import the llm_research package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.config import Config
from llm_research.reasoning import Reasoning
from llm_research.llm.openai import OpenAILLM
from llm_research.web_search import get_web_search_tool


def main():
    """Main entry point for the example script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Perform multi-step reasoning with URL content extraction')
    parser.add_argument('--task', '-t', required=True, help='The task to solve')
    parser.add_argument('--steps', '-s', type=int, default=3, help='Number of reasoning steps')
    parser.add_argument('--retries', '-r', type=int, default=3, help='Maximum number of retry attempts per subtask')
    parser.add_argument('--provider', '-p', help='The LLM provider to use')
    parser.add_argument('--bocha-api-key', help='Bocha API key for web search')
    parser.add_argument('--no-web-search', action='store_true', help='Disable web search')
    parser.add_argument('--no-url-extraction', action='store_true', help='Disable URL content extraction')
    args = parser.parse_args()
    
    console = Console()
    
    # Load the configuration
    config = Config()
    
    # Get the API key from the parameter, environment variable, or config
    api_key = args.bocha_api_key or os.environ.get("BOCHA_API_KEY")
    
    # If no API key is provided, check the config
    if not api_key:
        provider_config = config.get_provider_config("bocha")
        api_key = provider_config.get("api_key") if provider_config else None
    
    # Initialize web search tool if enabled
    web_search_tool = None
    if not args.no_web_search and api_key:
        try:
            web_search_tool = get_web_search_tool(api_key=api_key)
            console.print("[bold green]Web search enabled using Bocha API[/]")
        except Exception as e:
            console.print(f"[bold red]Error initializing web search:[/] {e}", style="red")
    elif not args.no_web_search:
        console.print("[bold yellow]Web search disabled: No API key provided[/]", style="yellow")
    else:
        console.print("[bold yellow]Web search disabled by user request[/]", style="yellow")
    
    # Get the LLM provider
    provider_config = config.get_provider_config(args.provider)
    llm = OpenAILLM(
        model=provider_config.get("model", "gpt-3.5-turbo"),
        base_url=provider_config.get("base_url", "https://api.openai.com/v1"),
        api_key=provider_config["api_key"]
    )
    
    # Create the reasoning manager
    reasoning = Reasoning(
        llm=llm,
        max_steps=args.steps,
        temperature=0.7,
        web_search=web_search_tool,
        extract_url_content=not args.no_url_extraction
    )
    
    # Display URL extraction status
    if args.no_url_extraction:
        console.print("[bold yellow]URL content extraction disabled by user request[/]", style="yellow")
    else:
        console.print("[bold green]URL content extraction enabled[/]")
    
    # Display task information
    console.print(Panel(
        f"[bold]Task:[/] {args.task}\n"
        f"[bold]Steps:[/] {args.steps}\n"
        f"[bold]Retries:[/] {args.retries}\n"
        f"[bold]Web Search:[/] {'Disabled' if args.no_web_search else 'Enabled'}\n"
        f"[bold]URL Extraction:[/] {'Disabled' if args.no_url_extraction else 'Enabled'}",
        title="Reasoning Configuration",
        border_style="blue"
    ))
    
    # Solve the task
    try:
        result = reasoning.solve_task(
            task=args.task,
            max_retries=args.retries,
            web_search_enabled=not args.no_web_search,
            extract_url_content=not args.no_url_extraction
        )
        
        # Display the result
        console.print("\n[bold green]Result:[/]")
        console.print(Markdown(result))
    except Exception as e:
        console.print(f"[bold red]Error during reasoning:[/] {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()