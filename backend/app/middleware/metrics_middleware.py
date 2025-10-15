"""
Shield AI - Metrics Middleware

Middleware for automatic metrics collection on HTTP requests
and integration with monitoring systems.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable
from api.routes.metrics import record_http_request

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect HTTP request metrics
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics
        """
        # Record start time
        start_time = time.time()
        
        # Get request method and path
        method = request.method
        path = request.url.path
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics (exclude metrics endpoints to avoid recursion)
        if not path.startswith("/metrics"):
            try:
                record_http_request(
                    method=method,
                    endpoint=path,
                    status=response.status_code,
                    duration=duration
                )
            except Exception as e:
                # Don't let metrics collection break the main application
                print(f"Error recording HTTP metrics: {e}")
        
        return response