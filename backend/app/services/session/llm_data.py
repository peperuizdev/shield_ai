"""
LLM data management for Shield AI sessions.

Handles storage and retrieval of LLM-related data including
responses and anonymized requests sent to language models.
"""

import logging
from typing import Optional

from .storage import get_storage


logger = logging.getLogger(__name__)


def store_llm_response(session_id: str, llm_response: str, ttl_seconds: Optional[int] = None) -> bool:
    """
    Store LLM response for a session.
    
    Args:
        session_id: Session identifier
        llm_response: LLM response text
        ttl_seconds: TTL in seconds
        
    Returns:
        bool: True if successful
    """
    try:
        storage = get_storage()
        success = storage.store_text("llm", session_id, llm_response, ttl_seconds)
        
        if success:
            logger.info(f"LLM response stored for session {session_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error storing LLM response for session {session_id}: {e}")
        return False


def get_llm_response(session_id: str) -> Optional[str]:
    """
    Retrieve LLM response for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Optional[str]: LLM response text or None if not found
    """
    try:
        storage = get_storage()
        return storage.get_text("llm", session_id)
        
    except Exception as e:
        logger.error(f"Error retrieving LLM response for session {session_id}: {e}")
        return None


def store_anonymized_request(session_id: str, anonymized_text: str, ttl_seconds: Optional[int] = None) -> bool:
    """
    Store anonymized request text that was sent to the LLM.
    
    Args:
        session_id: Session identifier
        anonymized_text: Anonymized text sent to LLM
        ttl_seconds: TTL in seconds
        
    Returns:
        bool: True if successful
    """
    try:
        storage = get_storage()
        
        logger.info(f"Storing anonymized request for session {session_id}")
        logger.debug(f"Text length: {len(anonymized_text)}")
        
        success = storage.store_text("request", session_id, anonymized_text, ttl_seconds)
        
        if success:
            logger.info(f"Anonymized request stored successfully for session {session_id}")
        else:
            logger.error(f"Failed to store anonymized request for session {session_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error storing anonymized request for session {session_id}: {e}")
        return False


def get_anonymized_request(session_id: str) -> Optional[str]:
    """
    Retrieve anonymized request text for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Optional[str]: Anonymized request text or None if not found
    """
    try:
        storage = get_storage()
        
        logger.info(f"Retrieving anonymized request for session {session_id}")
        
        text = storage.get_text("request", session_id)
        
        if text:
            logger.info(f"Anonymized request retrieved for session {session_id}, length: {len(text)}")
        else:
            logger.warning(f"No anonymized request found for session {session_id}")
        
        return text
        
    except Exception as e:
        logger.error(f"Error retrieving anonymized request for session {session_id}: {e}")
        return None