"""
Session management package for Shield AI.

Modular session management with separate concerns for storage,
anonymization, LLM data handling, and image data.
"""

from .manager import (
    SessionManager,
    get_session_manager,
    get_session_status,
    delete_session,
    extend_session_ttl,
    list_active_sessions,
    cleanup_expired_sessions
)

from .anonymization import (
    store_anonymization_map,
    get_anonymization_map
)

from .llm_data import (
    store_llm_response,
    get_llm_response,
    store_anonymized_request,
    get_anonymized_request
)

from .image_data import (
    store_anonymization_map as store_image_map,
    get_anonymization_map as get_image_map,
    delete_anonymization_map as delete_image_map,
    session_exists as image_session_exists,
    get_session_ttl as get_image_session_ttl,
    extend_session_ttl as extend_image_session_ttl
)

__all__ = [
    "SessionManager",
    "get_session_manager",
    "get_session_status",
    "delete_session",
    "extend_session_ttl",
    "list_active_sessions",
    "cleanup_expired_sessions",
    "store_anonymization_map",
    "get_anonymization_map",
    "store_llm_response",
    "get_llm_response",
    "store_anonymized_request",
    "get_anonymized_request",
    "store_image_map",
    "get_image_map",
    "delete_image_map",
    "image_session_exists",
    "get_image_session_ttl",
    "extend_image_session_ttl"
]