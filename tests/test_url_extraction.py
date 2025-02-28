"""
Test script for URL content extraction using docling.
"""

import os
import sys
import argparse

# Add the parent directory to the path so we can import the llm_research package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_research.url_extractor import get_url_extractor


def main():
    """
    Main entry point for the test script.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract content from a URL using docling')
    parser.add_argument('--url', '-u', required=True, help='URL to extract content from')
    parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'text', 'html'], 
                        help='Output format (markdown, text, html)')
    parser.add_argument('--output', '-o', help='Output file path (optional)')
    args = parser.parse_args()
    
    try:
        # Get the URL extractor
        url_extractor = get_url_extractor()
        
        # Extract the content
        print(f"Extracting content from URL: {args.url}")
        content = url_extractor.extract_content(args.url, output_format=args.format)
        
        # Save to file or print to console
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Content saved to {args.output}")
        else:
            print("\nExtracted content:")
            print(content)
    except Exception as e:
        print(f"Error extracting content: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()