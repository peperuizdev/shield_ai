"""
Session management package for Shield AI.

Modular session management with separate concerns for storage,
anonymization, and LLM data handling.
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
    "get_anonymized_request"
]