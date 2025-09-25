"""
Base Document Processor for Shield AI

Defines the abstract interface that all document processors must implement.
This ensures consistency across different document types (PDF, Word, Excel) and 
makes it easy to add new document formats in the future.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor(ABC):
    """
    Abstract base class for document processors.
    
    All document processors (PDF, Word, Excel) must inherit from this class
    and implement the required abstract methods. This ensures a consistent
    interface regardless of document type.
    """
    
    def __init__(self):
        """Initialize the document processor."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def extract_text(self, file_content: bytes) -> str:
        """
        Extract plain text from document content.
        
        Args:
            file_content (bytes): Raw file bytes
            
        Returns:
            str: Extracted plain text
            
        Raises:
            DocumentProcessingError: If text extraction fails
        """
        pass
    
    @abstractmethod
    def validate_file(self, file_content: bytes, filename: str) -> bool:
        """
        Validate that the file is a supported format and not corrupted.
        
        Args:
            file_content (bytes): Raw file bytes
            filename (str): Original filename
            
        Returns:
            bool: True if file is valid and supported
            
        Raises:
            DocumentValidationError: If validation fails with specific error details
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of file extensions supported by this processor.
        
        Returns:
            List[str]: List of supported extensions (e.g., ['.pdf', '.PDF'])
        """
        pass
    
    @abstractmethod
    def get_supported_mime_types(self) -> List[str]:
        """
        Get list of MIME types supported by this processor.
        
        Returns:
            List[str]: List of supported MIME types
        """
        pass
    
    def get_max_file_size(self) -> int:
        """
        Get maximum file size supported by this processor.
        
        Returns:
            int: Maximum file size in bytes (default: 10MB)
        """
        return 10 * 1024 * 1024  # 10MB default
    
    def preprocess_content(self, file_content: bytes) -> bytes:
        """
        Preprocess file content before text extraction.
        
        Base implementation does nothing, but subclasses can override
        to perform format-specific preprocessing.
        
        Args:
            file_content (bytes): Raw file bytes
            
        Returns:
            bytes: Preprocessed file content
        """
        return file_content
    
    def postprocess_text(self, text: str) -> str:
        """
        Postprocess extracted text before returning.
        
        Common text cleaning operations that apply to all document types.
        Subclasses can override to add format-specific postprocessing.
        
        Args:
            text (str): Raw extracted text
            
        Returns:
            str: Cleaned and normalized text
        """
        if not text:
            return ""
        
        # Basic text cleaning
        import re
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """
        Extract metadata from document.
        
        Base implementation returns empty dict, but subclasses can override
        to extract format-specific metadata (author, creation date, etc.).
        
        Args:
            file_content (bytes): Raw file bytes
            
        Returns:
            Dict[str, Any]: Document metadata
        """
        return {}
    
    def process_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Complete document processing pipeline.
        
        This is the main method that orchestrates the entire process:
        1. Validate the file
        2. Preprocess content
        3. Extract text
        4. Postprocess text
        5. Extract metadata
        
        Args:
            file_content (bytes): Raw file bytes
            filename (str): Original filename
            
        Returns:
            Dict[str, Any]: Processing result with text, metadata, and stats
        """
        try:
            self.logger.info(f"Starting processing of {filename}")
            
            # Step 1: Validate file
            if not self.validate_file(file_content, filename):
                raise DocumentValidationError(f"File validation failed: {filename}")
            
            # Step 2: Preprocess
            processed_content = self.preprocess_content(file_content)
            
            # Step 3: Extract text
            raw_text = self.extract_text(processed_content)
            
            # Step 4: Postprocess text
            cleaned_text = self.postprocess_text(raw_text)
            
            # Step 5: Extract metadata
            metadata = self.get_metadata(file_content)
            
            # Compile result
            result = {
                "text": cleaned_text,
                "metadata": metadata,
                "stats": {
                    "original_size": len(file_content),
                    "text_length": len(cleaned_text),
                    "processor": self.__class__.__name__
                }
            }
            
            self.logger.info(f"Successfully processed {filename}: {len(cleaned_text)} characters extracted")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {filename}: {str(e)}")
            raise DocumentProcessingError(f"Failed to process {filename}: {str(e)}")


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass


class DocumentValidationError(DocumentProcessingError):
    """Custom exception for document validation errors."""
    pass