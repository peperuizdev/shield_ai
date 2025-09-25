"""
PDF Document Processor for Shield AI

Specialized processor for PDF files using pdfplumber for robust text extraction.
Handles complex PDF structures including tables and multi-column layouts.
"""

import io
import logging
from typing import Dict, List, Any

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from .base import DocumentProcessor, DocumentProcessingError, DocumentValidationError

logger = logging.getLogger(__name__)


class PDFProcessor(DocumentProcessor):
    """
    PDF document processor using pdfplumber for text extraction.
    
    Implements the DocumentProcessor interface for PDF files,
    providing robust text extraction from complex PDF layouts.
    """
    
    def __init__(self):
        """Initialize PDF processor."""
        super().__init__()
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber is required for PDF processing. Install with: pip install pdfplumber==0.10.0")
    
    def extract_text(self, file_content: bytes) -> str:
        """
        Extract text from PDF using pdfplumber.
        
        Args:
            file_content (bytes): Raw PDF file bytes
            
        Returns:
            str: Extracted plain text from all pages
            
        Raises:
            DocumentProcessingError: If text extraction fails
        """
        try:
            self.logger.info("Extracting text from PDF")
            
            pdf_file = io.BytesIO(file_content)
            extracted_text = ""
            
            with pdfplumber.open(pdf_file) as pdf:
                self.logger.debug(f"PDF has {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            extracted_text += page_text + "\n\n"
                        else:
                            # Try extracting tables if no text found
                            tables = page.extract_tables()
                            if tables:
                                for table in tables:
                                    for row in table:
                                        if row:
                                            row_text = " | ".join([str(cell) for cell in row if cell])
                                            if row_text.strip():
                                                extracted_text += row_text + "\n"
                                extracted_text += "\n"
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing page {page_num}: {str(e)}")
                        continue
            
            if not extracted_text.strip():
                raise DocumentProcessingError("No text could be extracted from PDF")
            
            self.logger.info("PDF text extraction completed successfully")
            return extracted_text.strip()
            
        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {str(e)}")
            raise DocumentProcessingError(f"Failed to extract text from PDF: {str(e)}")
    
    def validate_file(self, file_content: bytes, filename: str) -> bool:
        """
        Validate PDF file structure and readability.
        
        Args:
            file_content (bytes): Raw file bytes
            filename (str): Original filename
            
        Returns:
            bool: True if file is valid PDF
            
        Raises:
            DocumentValidationError: If validation fails
        """
        try:
            if len(file_content) == 0:
                raise DocumentValidationError("PDF file is empty")
            
            if not file_content.startswith(b'%PDF-'):
                raise DocumentValidationError("File is not a valid PDF")
            
            pdf_file = io.BytesIO(file_content)
            
            with pdfplumber.open(pdf_file) as pdf:
                if len(pdf.pages) == 0:
                    raise DocumentValidationError("PDF contains no pages")
                
                # Test if we can read first page
                first_page = pdf.pages[0]
                test_text = first_page.extract_text()
                
                # Check if PDF is encrypted and try to decrypt
                if hasattr(pdf.pdf, 'is_encrypted') and pdf.pdf.is_encrypted:
                    try:
                        pdf.pdf.decrypt("")
                    except:
                        raise DocumentValidationError("PDF is password-protected")
            
            self.logger.info(f"PDF validation successful: {filename}")
            return True
            
        except DocumentValidationError:
            raise
        except Exception as e:
            self.logger.error(f"PDF validation failed for {filename}: {str(e)}")
            raise DocumentValidationError(f"PDF validation failed: {str(e)}")
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of PDF file extensions supported.
        
        Returns:
            List[str]: Supported extensions
        """
        return ['.pdf', '.PDF']
    
    def get_supported_mime_types(self) -> List[str]:
        """
        Get list of PDF MIME types supported.
        
        Returns:
            List[str]: Supported MIME types
        """
        return ['application/pdf']
    
    def get_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """
        Extract metadata from PDF document.
        
        Args:
            file_content (bytes): Raw file bytes
            
        Returns:
            Dict[str, Any]: PDF metadata
        """
        try:
            pdf_file = io.BytesIO(file_content)
            metadata = {}
            
            with pdfplumber.open(pdf_file) as pdf:
                metadata.update({
                    "page_count": len(pdf.pages),
                    "file_size": len(file_content)
                })
                
                # Extract PDF document info if available
                if hasattr(pdf.pdf, 'info') and pdf.pdf.info:
                    info = pdf.pdf.info[0]
                    
                    for field in ['/Title', '/Author', '/Subject', '/Creator']:
                        if field in info:
                            key = field.strip('/').lower()
                            metadata[key] = str(info[field])
            
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Could not extract PDF metadata: {str(e)}")
            return {"file_size": len(file_content)}