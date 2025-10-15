"""
Utility helper functions for Shield AI.

Common utility functions used across the application
for data processing, validation, and formatting.
"""

import re
import hashlib
import secrets
import string
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


def generate_session_id(prefix: str = "session") -> str:
    """
    Generate a secure random session ID.
    
    Args:
        prefix (str): Optional prefix for the session ID
        
    Returns:
        str: Generated session ID
    """
    # Generate random string
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(16))
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    return f"{prefix}_{timestamp}_{random_part}"


def sanitize_session_id(session_id: str) -> str:
    """
    Sanitize session ID by removing invalid characters.
    
    Args:
        session_id (str): Raw session ID
        
    Returns:
        str: Sanitized session ID
    """
    # Remove invalid characters, keep only alphanumeric, underscore, hyphen
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', session_id)
    
    # Truncate if too long
    if len(sanitized) > 128:
        sanitized = sanitized[:128]
    
    return sanitized


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds (int): Duration in seconds
        
    Returns:
        str: Human-readable duration
    """
    if seconds < 0:
        return "expired"
    
    if seconds < 60:
        return f"{seconds} seconds"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes} minutes {remaining_seconds} seconds"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        return f"{hours} hours {remaining_minutes} minutes"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    return f"{days} days {remaining_hours} hours"


def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
    """
    Hash sensitive data for logging or storage.
    
    Args:
        data (str): Sensitive data to hash
        salt (Optional[str]): Optional salt for hashing
        
    Returns:
        str: Hashed data
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Create hash
    hash_object = hashlib.sha256()
    hash_object.update(f"{data}{salt}".encode('utf-8'))
    
    return hash_object.hexdigest()


def mask_sensitive_value(value: str, mask_char: str = "*", visible_chars: int = 3) -> str:
    """
    Mask sensitive values for logging.
    
    Args:
        value (str): Value to mask
        mask_char (str): Character to use for masking
        visible_chars (int): Number of characters to keep visible
        
    Returns:
        str: Masked value
    """
    if len(value) <= visible_chars * 2:
        return mask_char * len(value)
    
    start = value[:visible_chars]
    end = value[-visible_chars:]
    middle = mask_char * (len(value) - visible_chars * 2)
    
    return f"{start}{middle}{end}"


def validate_ttl(ttl: Optional[int], min_ttl: int = 60, max_ttl: int = 86400) -> int:
    """
    Validate and normalize TTL value.
    
    Args:
        ttl (Optional[int]): TTL value to validate
        min_ttl (int): Minimum allowed TTL
        max_ttl (int): Maximum allowed TTL
        
    Returns:
        int: Validated TTL value
        
    Raises:
        ValueError: If TTL is invalid
    """
    if ttl is None:
        return 3600  # Default 1 hour
    
    if not isinstance(ttl, int):
        raise ValueError("TTL must be an integer")
    
    if ttl < min_ttl:
        raise ValueError(f"TTL must be at least {min_ttl} seconds")
    
    if ttl > max_ttl:
        raise ValueError(f"TTL cannot exceed {max_ttl} seconds")
    
    return ttl


def safe_json_serialize(obj: Any) -> Dict[str, Any]:
    """
    Safely serialize object to JSON-compatible format.
    
    Args:
        obj (Any): Object to serialize
        
    Returns:
        Dict[str, Any]: JSON-compatible dictionary
    """
    if isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    
    elif isinstance(obj, datetime):
        return obj.isoformat()
    
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    
    else:
        return str(obj)


def clean_text_for_logging(text: str, max_length: int = 100) -> str:
    """
    Clean and truncate text for safe logging.
    
    Args:
        text (str): Text to clean
        max_length (int): Maximum length for truncation
        
    Returns:
        str: Cleaned text safe for logging
    """
    if not text:
        return ""
    
    # Remove sensitive patterns (basic implementation)
    # This could be enhanced with PII detection
    cleaned = re.sub(r'\b\d{8}[A-Z]\b', '[DNI]', text)  # DNI pattern
    cleaned = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', cleaned)  # Email
    cleaned = re.sub(r'\b\d{9}\b', '[PHONE]', cleaned)  # Phone pattern
    
    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    
    return cleaned


def extract_entities_summary(entities: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Create summary of detected entities by type.
    
    Args:
        entities (List[Dict[str, Any]]): List of detected entities
        
    Returns:
        Dict[str, int]: Count of entities by type
    """
    summary = {}
    for entity in entities:
        entity_type = entity.get('entity_type', 'UNKNOWN')
        summary[entity_type] = summary.get(entity_type, 0) + 1
    
    return summary

def validate_session_id_format(session_id: str) -> bool:

    if not session_id or not session_id.strip():
        return False
    
    pattern = r'^[a-zA-Z0-9_\-]+$'
    return bool(re.match(pattern, session_id))


def format_file_size(size_bytes: int) -> str:

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def sanitize_filename(filename: str) -> str:

    safe_name = re.sub(r'[^\w\s\-\.]', '', filename)
    
    if len(safe_name) > 255:
        name, ext = safe_name.rsplit('.', 1) if '.' in safe_name else (safe_name, '')
        safe_name = name[:250] + ('.' + ext if ext else '')
    
    return safe_name


def extract_file_extension(filename: str) -> str:

    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def is_image_file(filename: str) -> bool:

    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg'}
    ext = extract_file_extension(filename)
    return ext in image_extensions


def is_document_file(filename: str) -> bool:

    document_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'rtf', 'odt'}
    ext = extract_file_extension(filename)
    return ext in document_extensions


# Export utility functions
__all__ = [
    "generate_session_id",
    "sanitize_session_id",
    "format_duration",
    "hash_sensitive_data",
    "mask_sensitive_value", 
    "validate_ttl",
    "safe_json_serialize",
    "clean_text_for_logging",
    "extract_entities_summary"
    "validate_session_id_format",
    "format_file_size",
    "sanitize_filename",
    "extract_file_extension",
    "is_image_file",
    "is_document_file"
]