"""
Example script demonstrating the improved URL extraction process.

This script shows how the refactored code makes it easier to work with search results
and extract content from relevant URLs.
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
from llm_research.web_search import get_web_search_tool
from llm_research.url_extractor import get_url_extractor
from llm_research.llm.openai import OpenAILLM


def main():
    """Main entry point for the example script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Demonstrate improved URL extraction')
    parser.add_argument('--query', '-q', required=True, help='The search query')
    parser.add_argument('--provider', '-p', help='The LLM provider to use')
    parser.add_argument('--bocha-api-key', help='Bocha API key for web search')
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
    
    # Initialize web search tool
    if not api_key:
        console.print("[bold red]Error: Bocha API key is required.[/]")
        sys.exit(1)
    
    web_search = get_web_search_tool(api_key=api_key)
    console.print("[bold green]Web search initialized[/]")
    
    # Initialize URL extractor
    url_extractor = get_url_extractor()
    console.print("[bold green]URL extractor initialized[/]")
    
    # Get the LLM provider
    provider_config = config.get_provider_config(args.provider)
    llm = OpenAILLM(
        model=provider_config.get("model", "gpt-3.5-turbo"),
        base_url=provider_config.get("base_url", "https://api.openai.com/v1"),
        api_key=provider_config["api_key"]
    )
    console.print("[bold green]LLM initialized[/]")
    
    # Display query information
    console.print(Panel(
        f"[bold]Query:[/] {args.query}",
        title="Search Configuration",
        border_style="blue"
    ))
    
    # Perform the search
    console.print(f"\n🔍 Searching for: [bold]{args.query}[/]")
    search_results = web_search.search(query=args.query)
    
    # Check if search was successful
    if not search_results["success"]:
        console.print(f"[bold red]Search failed:[/] {search_results.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Display search results
    console.print(f"\n✅ Found [bold]{len(search_results.get('results', []))}[/] results")
    
    # Extract URLs and summaries
    if not search_results.get("results"):
        console.print("[bold yellow]No results found[/]")
        sys.exit(0)
    
    urls = []
    url_summaries = []
    
    # Collect URLs and their summaries
    for result in search_results["results"]:
        urls.append(result["url"])
        url_summaries.append({
            "url": result["url"],
            "title": result["name"],
            "summary": result["summary"]
        })
    
    # Display the URLs
    console.print("\n[bold]Search Results:[/]")
    for i, summary in enumerate(url_summaries, start=1):
        console.print(f"{i}. [bold]{summary['title']}[/]")
        console.print(f"   URL: {summary['url']}")
        console.print(f"   Summary: {summary['summary'][:100]}...")
    
    # Create a prompt to ask the LLM which URLs to extract content from
    console.print("\n🤔 Asking LLM to select the most relevant URLs...")
    url_selection_prompt = f"Based on the following search results for the query '{args.query}', which URLs would be most relevant to extract full content from? Select up to 3 URLs that seem most promising based on their summaries.\n\n"
    
    # Add formatted summaries for the LLM to evaluate
    for i, summary in enumerate(url_summaries, start=1):
        url_selection_prompt += f"{i}. {summary['title']}\n   URL: {summary['url']}\n   Summary: {summary['summary']}\n\n"
    
    url_selection_prompt += "List the numbers of the most relevant URLs (e.g., '1, 3, 5'):"
    
    # Get the LLM's recommendation on which URLs to extract
    url_selection_response = llm.generate(
        prompt=url_selection_prompt,
        max_tokens=50,
        temperature=0.3
    )
    
    # Parse the response to get the selected URL indices
    selected_indices = []
    selection_text = url_selection_response["text"].strip()
    console.print(f"LLM response: [italic]{selection_text}[/]")
    
    # Try to parse numbers from the response
    import re
    for num in re.findall(r'\d+', selection_text):
        try:
            idx = int(num) - 1  # Convert to 0-based index
            if 0 <= idx < len(urls):
                selected_indices.append(idx)
        except ValueError:
            continue
    
    # Limit to at most 3 URLs
    selected_indices = selected_indices[:3]
    
    if not selected_indices:
        console.print("[bold yellow]No URLs selected for extraction[/]")
        sys.exit(0)
    
    # Extract content from the selected URLs
    console.print(f"\n📄 Extracting content from [bold]{len(selected_indices)}[/] selected URLs...")
    
    extracted_contents = []
    for url_idx in selected_indices:
        url = urls[url_idx]
        title = url_summaries[url_idx]["title"]
        
        console.print(f"\n[bold]Extracting from:[/] {title}")
        console.print(f"URL: {url}")
        
        try:
            content = url_extractor.extract_content(url, output_format="markdown")
            
            # Truncate content if it's too long (to avoid token limits)
            max_content_length = 4000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "...\n[Content truncated due to length]"
            
            extracted_contents.append({
                "url": url,
                "title": title,
                "content": content
            })
            
            console.print(f"✅ Successfully extracted [bold]{len(content)}[/] characters")
        except Exception as e:
            console.print(f"❌ Extraction failed: {str(e)}")
    
    # Display the extracted content
    if extracted_contents:
        console.print("\n[bold green]Extracted Content:[/]")
        
        for i, content in enumerate(extracted_contents, start=1):
            console.print(Panel(
                f"[bold]Title:[/] {content['title']}\n"
                f"[bold]URL:[/] {content['url']}\n\n"
                f"{content['content'][:500]}...",
                title=f"Content {i}/{len(extracted_contents)}",
                border_style="green"
            ))
    else:
        console.print("[bold yellow]No content was successfully extracted[/]")


if __name__ == "__main__":
    main()