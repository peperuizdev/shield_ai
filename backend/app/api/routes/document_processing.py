"""
Document Processing Router for Shield AI

FastAPI router for document processing endpoint.
Integrates document text extraction with PII detection and anonymization.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from services.document_processing.factory import process_document
from services.document_processing.base import DocumentProcessingError, DocumentValidationError
from services.session.anonymization import get_anonymization_map
from utils.helpers import generate_session_id

router = APIRouter(prefix="/document", tags=["Document Processing"])
logger = logging.getLogger(__name__)


@router.post("/process")
async def process_document_endpoint(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    model: Optional[str] = Form("es"),
    use_regex: Optional[bool] = Form(True),
    pseudonymize: Optional[bool] = Form(True),
    save_mapping: Optional[bool] = Form(True),
    use_realistic_fake: Optional[bool] = Form(True)
):
    """
    Process uploaded document and return anonymized text.
    
    This endpoint:
    1. Extracts text from PDF, Word, or Excel files
    2. Applies PII detection and anonymization
    3. Returns anonymized text with mapping
    
    Args:
        file (UploadFile): Document file to process (PDF, Word, Excel)
        session_id (Optional[str]): Session ID for storing anonymization map
        model (Optional[str]): Language model for PII detection (default: "es")
        use_regex (Optional[bool]): Enable regex-based PII detection (default: True)
        pseudonymize (Optional[bool]): Use pseudonymization (default: True)
        save_mapping (Optional[bool]): Save anonymization mapping (default: True)
        use_realistic_fake (Optional[bool]): Use realistic fake data (default: True)
        
    Returns:
        JSON response with anonymized text and processing metadata
        
    Raises:
        HTTPException: If file processing or anonymization fails
    """
    try:
        logger.info(f"Processing document: {file.filename}")
        
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )
        
        if not session_id or session_id.strip() == "" or session_id == "string":
            session_id = generate_session_id(prefix="chat")
            logger.info(f"Auto-generated session_id: {session_id}")
        
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )
        
        try:
            extraction_result = process_document(
                file_content=file_content,
                filename=file.filename,
                content_type=file.content_type
            )
            
            extracted_text = extraction_result['text']
            document_metadata = extraction_result.get('metadata', {})
            processing_info = extraction_result.get('processing_info', {})
            
            logger.info(f"Text extraction successful: {len(extracted_text)} characters")
            
        except (DocumentValidationError, DocumentProcessingError) as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Document processing failed: {str(e)}"
            )
        
        try:
            from services.pii_detector import run_pipeline
            
            anonymization_result = run_pipeline(
                model=model,
                text=extracted_text,
                use_regex=use_regex,
                pseudonymize=pseudonymize,
                save_mapping=False,
                use_realistic_fake=use_realistic_fake
            )
            
            anonymized_text = anonymization_result.get('anonymized', extracted_text)
            pii_mapping = anonymization_result.get('mapping', {})
            pii_backend = anonymization_result.get('backend', 'unknown')
            
            logger.info(f"PII anonymization completed: {len(pii_mapping)} entities processed")
            
        except Exception as e:
            logger.error(f"PII anonymization failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"PII anonymization failed: {str(e)}"
            )
        
        if save_mapping and session_id and pii_mapping:
            try:
                from services.session.anonymization import store_anonymization_map
                store_anonymization_map(session_id, pii_mapping)
                logger.info(f"Anonymization mapping saved for session: {session_id}")
            except Exception as e:
                logger.warning(f"Failed to save anonymization mapping: {str(e)}")
        
        response_data = {
            "success": True,
            "anonymized_text": anonymized_text,
            "session_id": session_id,
            "pii_detected": bool(pii_mapping),
            "entities_anonymized": len(pii_mapping),
            "mapping": pii_mapping,
            "document_info": {
                "filename": file.filename,
                "processor_used": processing_info.get('processor_used', 'unknown'),
                "detected_type": processing_info.get('detected_type', 'unknown')
            }
        }
        
        logger.info(f"Document processing completed successfully for {file.filename}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing document {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/mapping/{session_id}")
async def get_document_mapping(session_id: str):
    """
    Retrieve the complete anonymization mapping for a processed document.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        JSON with the complete mapping of original to anonymized data
        
    Raises:
        HTTPException: If session not found
    """
    try:
        logger.info(f"Retrieving mapping for session: {session_id}")
        
        mapping = get_anonymization_map(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "mapping": mapping,
            "entities_count": len(mapping)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving mapping for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve mapping: {str(e)}"
        )


@router.post("/deanonymize")
async def deanonymize_document(
    session_id: str = Form(...),
    anonymized_text: str = Form(...)
):
    """
    Deanonymize text from a processed document using stored mapping.
    
    Args:
        session_id (str): Session identifier
        anonymized_text (str): Text with fake data to restore
        
    Returns:
        JSON with original text restored
        
    Raises:
        HTTPException: If session not found or deanonymization fails
    """
    try:
        logger.info(f"Deanonymizing document for session: {session_id}")
        
        mapping = get_anonymization_map(session_id)
        
        from services.deanonymization_service import create_reverse_map, deanonymize_text
        
        reverse_map = create_reverse_map(mapping)
        original_text = deanonymize_text(anonymized_text, reverse_map)
        
        logger.info(f"Document deanonymization completed for session: {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "original_text": original_text,
            "anonymized_text": anonymized_text,
            "entities_restored": len(reverse_map)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deanonymizing document for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deanonymize document: {str(e)}"
        )