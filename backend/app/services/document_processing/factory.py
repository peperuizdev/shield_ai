"""
Document Processor Factory for Shield AI

Factory pattern implementation for automatic document type detection
and processor creation. Provides unified interface for processing
PDF, Word, and Excel documents.
"""

import logging
import os
from typing import Dict, Any, Optional

from .base import DocumentProcessor, DocumentProcessingError, DocumentValidationError
from .pdf_processor import PDFProcessor
from .word_processor import WordProcessor
from .excel_processor import ExcelProcessor

logger = logging.getLogger(__name__)


class DocumentProcessorFactory:
    """
    Factory class for creating document processors based on file type.
    
    Automatically detects document type and returns appropriate processor
    instance for PDF, Word, or Excel files.
    """
    
    # Mapping of file types to processor classes
    _PROCESSORS = {
        'pdf': PDFProcessor,
        'word': WordProcessor,
        'excel': ExcelProcessor
    }
    
    # File extension mappings
    _EXTENSION_MAP = {
        '.pdf': 'pdf',
        '.PDF': 'pdf',
        '.docx': 'word',
        '.DOCX': 'word',
        '.xlsx': 'excel',
        '.XLSX': 'excel'
    }
    
    # MIME type mappings
    _MIME_TYPE_MAP = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel'
    }
    
    @classmethod
    def detect_file_type(cls, filename: str, content_type: Optional[str] = None) -> str:
        """
        Detect document type from filename and content type.
        
        Args:
            filename (str): Original filename
            content_type (Optional[str]): MIME content type
            
        Returns:
            str: Detected file type ('pdf', 'word', or 'excel')
            
        Raises:
            DocumentValidationError: If file type is not supported
        """
        detected_type = None
        
        # First try MIME type detection (more reliable)
        if content_type and content_type in cls._MIME_TYPE_MAP:
            detected_type = cls._MIME_TYPE_MAP[content_type]
            logger.debug(f"File type detected from MIME type {content_type}: {detected_type}")
        
        # Fallback to file extension
        if not detected_type:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in cls._EXTENSION_MAP:
                detected_type = cls._EXTENSION_MAP[file_ext]
                logger.debug(f"File type detected from extension {file_ext}: {detected_type}")
        
        # Handle case-insensitive extension check
        if not detected_type:
            file_ext = os.path.splitext(filename)[1]  # Keep original case
            if file_ext in cls._EXTENSION_MAP:
                detected_type = cls._EXTENSION_MAP[file_ext]
                logger.debug(f"File type detected from extension {file_ext}: {detected_type}")
        
        if not detected_type:
            supported_extensions = list(cls._EXTENSION_MAP.keys())
            supported_mime_types = list(cls._MIME_TYPE_MAP.keys())
            
            error_msg = (
                f"Unsupported file type: {filename} (content-type: {content_type}). "
                f"Supported extensions: {supported_extensions}. "
                f"Supported MIME types: {supported_mime_types}"
            )
            
            logger.error(error_msg)
            raise DocumentValidationError(error_msg)
        
        return detected_type
    
    @classmethod
    def get_processor(cls, file_type: str) -> DocumentProcessor:
        """
        Create appropriate document processor instance.
        
        Args:
            file_type (str): Type of document ('pdf', 'word', or 'excel')
            
        Returns:
            DocumentProcessor: Processor instance for the file type
            
        Raises:
            DocumentValidationError: If file type is not supported
        """
        if file_type not in cls._PROCESSORS:
            supported_types = list(cls._PROCESSORS.keys())
            error_msg = f"No processor available for file type: {file_type}. Supported types: {supported_types}"
            logger.error(error_msg)
            raise DocumentValidationError(error_msg)
        
        processor_class = cls._PROCESSORS[file_type]
        
        try:
            processor = processor_class()
            logger.info(f"Created {processor_class.__name__} instance")
            return processor
        
        except Exception as e:
            error_msg = f"Failed to create processor for {file_type}: {str(e)}"
            logger.error(error_msg)
            raise DocumentProcessingError(error_msg)
    
    @classmethod
    def get_supported_types(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all supported document types.
        
        Returns:
            Dict containing supported file types with their extensions and MIME types
        """
        supported_types = {}
        
        for file_type, processor_class in cls._PROCESSORS.items():
            try:
                # Create temporary instance to get supported formats
                processor = processor_class()
                
                supported_types[file_type] = {
                    'processor_class': processor_class.__name__,
                    'extensions': processor.get_supported_extensions(),
                    'mime_types': processor.get_supported_mime_types(),
                    'max_file_size': processor.get_max_file_size()
                }
            
            except Exception as e:
                logger.warning(f"Could not get info for {file_type}: {str(e)}")
                supported_types[file_type] = {
                    'processor_class': processor_class.__name__,
                    'error': str(e)
                }
        
        return supported_types


def process_document(
    file_content: bytes,
    filename: str,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a document automatically detecting its type.
    
    This is the main public function for document processing. It automatically
    detects the file type, creates the appropriate processor, and extracts
    the text content.
    
    Args:
        file_content (bytes): Raw file content
        filename (str): Original filename
        content_type (Optional[str]): MIME content type
        
    Returns:
        Dict[str, Any]: Processing result with text, metadata, and stats
        
    Raises:
        DocumentValidationError: If file type is not supported or invalid
        DocumentProcessingError: If processing fails
    """
    try:
        logger.info(f"Starting document processing for file: {filename}")
        
        # Detect file type
        file_type = DocumentProcessorFactory.detect_file_type(filename, content_type)
        logger.info(f"Detected file type: {file_type}")
        
        # Create appropriate processor
        processor = DocumentProcessorFactory.get_processor(file_type)
        
        # Process the document using the base class pipeline
        result = processor.process_document(file_content, filename)
        
        # Add factory metadata
        result['processing_info'] = {
            'detected_type': file_type,
            'processor_used': processor.__class__.__name__,
            'filename': filename,
            'content_type': content_type
        }
        
        logger.info(f"Document processing completed successfully for {filename}")
        return result
        
    except (DocumentValidationError, DocumentProcessingError):
        # Re-raise document-specific errors
        raise
    
    except Exception as e:
        error_msg = f"Unexpected error processing document {filename}: {str(e)}"
        logger.error(error_msg)
        raise DocumentProcessingError(error_msg)


def get_supported_file_types() -> Dict[str, Any]:
    """
    Get information about all supported file types.
    
    Returns:
        Dict containing comprehensive information about supported formats
    """
    return DocumentProcessorFactory.get_supported_types()


def validate_file_type(filename: str, content_type: Optional[str] = None) -> bool:
    """
    Validate if a file type is supported without processing.
    
    Args:
        filename (str): Filename to check
        content_type (Optional[str]): MIME content type
        
    Returns:
        bool: True if file type is supported, False otherwise
    """
    try:
        DocumentProcessorFactory.detect_file_type(filename, content_type)
        return True
    except DocumentValidationError:
        return False