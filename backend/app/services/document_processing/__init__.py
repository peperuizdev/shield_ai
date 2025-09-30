"""
Document Processing Package for Shield AI

This package provides modular document processing capabilities for PDF, Word and Excel files.
Each document ytpe has its own processor class following the same interface, making it easy to extend and maintain.

Main components:
- DocumentProcessor: Base abstract class defining the interface
- PDFProcessor, WordProcessor, ExcelProcessor: Specific implementations
- DocumentProcessorFactory: Factory to create appropiate processors
- process_document: Main function to process any supported document type

Usage:
    from services.document_processing import process_document

    result = process_document(
        file_content=file_bytes,
        filename="document.pdf",
        content_type="application/pdf"
    )
"""

from .base import DocumentProcessor
from .pdf_processor import PDFProcessor
from .word_processor import WordProcessor
from .excel_processor import ExcelProcessor
from .factory import DocumentProcessorFactory, process_document

__all__ = [
    "DocumentProcessor",
    "PDFProcessor",
    "WordProcessor",
    "ExcelProcessor",
    "DocumentProcessorFactory",
    "process_document"
]