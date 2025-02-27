"""
Test script for the web search feature.

This script tests the web search functionality directly without using the reasoning process.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.web_search import get_web_search_tool


def main():
    """
    Test the web search functionality.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test web search functionality")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--bocha-api-key", "-k", help="Bocha API key for web search")
    parser.add_argument("--count", "-c", type=int, default=5, help="Number of search results to return")
    args = parser.parse_args()
    
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("No .env file found. Using environment variables.")
    
    # Get the API key
    api_key = args.bocha_api_key or os.environ.get("BOCHA_API_KEY")
    
    # If no API key is provided, prompt the user
    if not api_key:
        import getpass
        api_key = getpass.getpass("Enter Bocha API key: ")
    
    if not api_key:
        print("Error: Bocha API key is required")
        return
    
    # Initialize the web search tool
    try:
        web_search = get_web_search_tool(api_key=api_key)
        print(f"Web search tool initialized with API key: {api_key[:4]}...{api_key[-4:]}")
    except Exception as e:
        print(f"Error initializing web search: {e}")
        return
    
    # Perform the search
    print(f"\nSearching for: {args.query}")
    print(f"Retrieving {args.count} results...\n")
    
    try:
        results = web_search.search(query=args.query, count=args.count)
        print("Search Results:")
        print("==============")
        print(results)
    except Exception as e:
        print(f"Error performing search: {e}")


if __name__ == "__main__":
    main()