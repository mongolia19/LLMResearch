"""
URL content extraction utilities using the docling library.

This module provides tools for extracting content from URLs and converting it to
various formats for LLM processing.
"""

import os
from typing import Optional, Dict, Any, Union

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    raise ImportError("docling is required for URL content extraction. Install it with 'pip install docling'.")


class URLExtractor:
    """
    URL content extractor using the docling library.
    
    This class provides utilities for extracting content from URLs and converting
    it to various formats for LLM processing.
    """
    
    def __init__(self):
        """
        Initialize the URL extractor.
        """
        self.converter = DocumentConverter()
    
    def extract_content(self, url: str, output_format: str = "markdown") -> str:
        """
        Extract content from a URL.
        
        Args:
            url: The URL to extract content from
            output_format: The output format (markdown, text, html)
            
        Returns:
            The extracted content as a string
            
        Raises:
            ValueError: If the URL is invalid or the content cannot be extracted
        """
        try:
            # Convert the URL to a document
            result = self.converter.convert(url)
            
            # Return the content in the requested format
            if output_format.lower() == "markdown":
                return result.document.export_to_markdown()
            elif output_format.lower() == "text":
                return result.document.export_to_text()
            elif output_format.lower() == "html":
                return result.document.export_to_html()
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
        except Exception as e:
            raise ValueError(f"Failed to extract content from URL: {url}. Error: {str(e)}")


def get_url_extractor() -> URLExtractor:
    """
    Get a URL extractor instance.
    
    Returns:
        A URL extractor instance
    """
    return URLExtractor()