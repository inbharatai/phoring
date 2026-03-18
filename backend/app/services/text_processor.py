"""
Text processing service.
"""

from typing import List
from..utils.file_parser import split_text_into_chunks


class TextProcessor:
    """Text handler for file extraction and text splitting."""
    
    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Source text to split.
            chunk_size: Maximum characters per chunk.
            overlap: Overlap characters between chunks.

        Returns:
            List of text chunks.
        """
        return split_text_into_chunks(text, chunk_size, overlap)
    
    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocess text by cleaning whitespace and normalizing line breaks.

        Args:
            text: Input text.

        Returns:
            Preprocessed text.
        """
        import re
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines (keep at most one blank line)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    

