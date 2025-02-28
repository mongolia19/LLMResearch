"""
Example script demonstrating URL content extraction using docling.

This script shows how to use the URL extraction functionality programmatically.
"""

import os
import sys
import argparse
from rich.console import Console
from rich.markdown import Markdown

# Add the parent directory to the path so we can import the llm_research package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.url_extractor import get_url_extractor
from llm_research.llm.base import BaseLLM
from llm_research.config import Config
from llm_research.llm.openai import OpenAILLM


def get_llm_provider(config, provider_name=None):
    """Get an LLM provider instance."""
    provider_config = config.get_provider_config(provider_name)
    provider_type = provider_config.get("type", "openai")
    
    if provider_type == "openai":
        return OpenAILLM(
            model=provider_config.get("model", "gpt-3.5-turbo"),
            base_url=provider_config.get("base_url", "https://api.openai.com/v1"),
            api_key=provider_config["api_key"]
        )
    else:
        from llm_research.llm.custom import CustomLLM
        return CustomLLM(
            model=provider_config.get("model", "default"),
            base_url=provider_config.get("base_url", ""),
            api_key=provider_config["api_key"],
            **provider_config.get("options", {})
        )


def main():
    """Main entry point for the example script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract and analyze content from a URL')
    parser.add_argument('--url', '-u', required=True, help='URL to extract content from')
    parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'text', 'html'], 
                        help='Output format (markdown, text, html)')
    parser.add_argument('--output', '-o', help='Output file path (optional)')
    parser.add_argument('--analyze', '-a', action='store_true', help='Analyze the content using LLM')
    parser.add_argument('--provider', '-p', help='The LLM provider to use for analysis')
    args = parser.parse_args()
    
    console = Console()
    
    try:
        # Get the URL extractor
        url_extractor = get_url_extractor()
        
        # Extract the content
        console.print(f"[bold blue]Extracting content from URL:[/] {args.url}")
        content = url_extractor.extract_content(args.url, output_format=args.format)
        
        # Save to file if requested
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content)
            console.print(f"[bold green]Content saved to:[/] {args.output}")
        
        # Display the content
        if not args.analyze:
            console.print("\n[bold]Extracted content:[/]")
            if args.format == 'markdown':
                console.print(Markdown(content))
            else:
                console.print(content)
        
        # Analyze the content if requested
        if args.analyze:
            console.print("\n[bold yellow]Analyzing content...[/]")
            
            # Get the LLM provider
            config = Config()
            llm = get_llm_provider(config, args.provider)
            
            # Generate a prompt for analysis
            prompt = f"""
            Please analyze the following content extracted from {args.url}:
            
            {content[:4000]}  # Limit content to avoid token limits
            
            Provide a summary of the key points, main topics, and any important insights.
            """
            
            # Generate the analysis
            response = llm.generate(prompt=prompt, temperature=0.7)
            
            # Display the analysis
            console.print("\n[bold green]Analysis:[/]")
            console.print(response["text"])
            
    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()