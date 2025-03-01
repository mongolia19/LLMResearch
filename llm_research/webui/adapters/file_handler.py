"""
Adapter for file handling functionality.
"""

import os
from typing import List, Optional

from llm_research.file_handler import FileHandler as LLMFileHandler

class FileHandlerAdapter:
    """
    Adapter for the LLMResearch file handling functionality.
    
    This class provides a simplified interface to the LLMResearch file handling
    functionality for use in the WebUI.
    """
    
    def __init__(self):
        """
        Initialize the file handler adapter.
        """
        self.file_handler = LLMFileHandler()
    
    def read_file(self, file_path: str) -> str:
        """
        Read a file and return its contents.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The file contents as a string
        """
        return self.file_handler.read_file(file_path)
    
    def write_file(self, file_path: str, content: str) -> None:
        """
        Write content to a file.
        
        Args:
            file_path: Path to the file
            content: Content to write
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """
        List files in a directory.
        
        Args:
            directory: Directory to list files from
            pattern: Optional glob pattern to filter files
            
        Returns:
            A list of file paths
        """
        import glob
        
        # Ensure the directory exists
        if not os.path.exists(directory):
            return []
        
        # List files
        if pattern:
            return glob.glob(os.path.join(directory, pattern))
        else:
            return [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
            ]