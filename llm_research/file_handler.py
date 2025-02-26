"""
File handling utilities for reading and processing local files.
"""

import os
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path


class FileHandler:
    """
    File handler for reading and processing local files.
    
    This class provides utilities for reading text files and preparing their
    content for LLM processing.
    """
    
    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200):
        """
        Initialize the file handler.
        
        Args:
            chunk_size: Maximum size of text chunks (in characters)
            chunk_overlap: Overlap between chunks (in characters)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def read_file(self, file_path: str) -> str:
        """
        Read the content of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The file content as a string
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported
        """
        # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get the file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Read the file based on its extension
        if ext in [".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".yaml", ".yml", ".xml", ".csv"]:
            # Text files
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            # PDF files
            try:
                import pypdf
                with open(file_path, "rb") as f:
                    pdf = pypdf.PdfReader(f)
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n\n"
                    return text
            except ImportError:
                raise ImportError("pypdf is required for reading PDF files. Install it with 'pip install pypdf'.")
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def read_files(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Read the content of multiple files.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            A dictionary mapping file paths to their content
        """
        result = {}
        for file_path in file_paths:
            try:
                result[file_path] = self.read_file(file_path)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        
        return result
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of approximately equal size.
        
        Args:
            text: The text to split
            
        Returns:
            A list of text chunks
        """
        # If the text is shorter than the chunk size, return it as is
        if len(text) <= self.chunk_size:
            return [text]
        
        # Split the text into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the chunk size,
            # add the current chunk to the list and start a new one
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                # If the current chunk is not empty, add it to the list
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If the paragraph itself is longer than the chunk size,
                # split it into smaller chunks
                if len(paragraph) > self.chunk_size:
                    # Split the paragraph into sentences
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > self.chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk)
                            
                            # If the sentence itself is longer than the chunk size,
                            # split it into smaller chunks
                            if len(sentence) > self.chunk_size:
                                # Split the sentence into words
                                words = sentence.split()
                                
                                current_chunk = ""
                                for word in words:
                                    if len(current_chunk) + len(word) + 1 > self.chunk_size:
                                        chunks.append(current_chunk)
                                        current_chunk = word
                                    else:
                                        if current_chunk:
                                            current_chunk += " " + word
                                        else:
                                            current_chunk = word
                            else:
                                current_chunk = sentence
                        else:
                            if current_chunk:
                                current_chunk += " " + sentence
                            else:
                                current_chunk = sentence
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # Add overlap between chunks
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # Add overlap from the previous chunk
                    prev_chunk = chunks[i - 1]
                    overlap = prev_chunk[-self.chunk_overlap:]
                    chunk = overlap + "\n\n" + chunk
                
                overlapped_chunks.append(chunk)
            
            return overlapped_chunks
        
        return chunks
    
    def process_file(self, file_path: str) -> List[str]:
        """
        Read and process a file into chunks.
        
        Args:
            file_path: Path to the file
            
        Returns:
            A list of text chunks
        """
        # Read the file
        text = self.read_file(file_path)
        
        # Chunk the text
        return self.chunk_text(text)
    
    def process_files(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Read and process multiple files into chunks.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            A dictionary mapping file paths to lists of text chunks
        """
        result = {}
        for file_path in file_paths:
            try:
                result[file_path] = self.process_file(file_path)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        return result