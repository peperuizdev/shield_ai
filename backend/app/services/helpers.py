import uuid
import re
from datetime import datetime


def generate_session_id(prefix: str = "session") -> str:

    timestamp = int(datetime.now().timestamp())
    random_part = uuid.uuid4().hex[:8]
    
    return f"{prefix}_{timestamp}_{random_part}"


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


__all__ = [
    'generate_session_id',
    'validate_session_id_format',
    'format_file_size',
    'sanitize_filename',
    'extract_file_extension',
    'is_image_file',
    'is_document_file'
]