"""
Shield AI - Metrics and Monitoring Module

Provides Prometheus metrics collection and monitoring endpoints
for the Shield AI application.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.registry import REGISTRY
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
import time
import psutil
import os
from typing import Dict, Any

# Create router for metrics endpoints
router = APIRouter(prefix="/metrics", tags=["Metrics"])

# === PROMETHEUS METRICS ===

# HTTP Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# PII Detection metrics
pii_detection_total = Counter(
    'pii_detection_total',
    'Total PII detections',
    ['pii_type']
)

pii_detection_errors_total = Counter(
    'pii_detection_errors_total',
    'Total PII detection errors',
    ['error_type']
)

pii_detection_duration_seconds = Histogram(
    'pii_detection_duration_seconds',
    'PII detection processing time in seconds'
)

# Deanonymization metrics
deanonymization_requests_total = Counter(
    'deanonymization_requests_total',
    'Total deanonymization requests'
)

deanonymization_failures_total = Counter(
    'deanonymization_failures_total',
    'Total deanonymization failures',
    ['failure_type']
)

deanonymization_duration_seconds = Histogram(
    'deanonymization_duration_seconds',
    'Deanonymization processing time in seconds'
)

# System metrics
system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

# Active sessions metric
active_sessions_total = Gauge(
    'active_sessions_total',
    'Total number of active sessions'
)

# Document processing metrics
document_processing_total = Counter(
    'document_processing_total',
    'Total documents processed',
    ['document_type']
)

document_processing_errors_total = Counter(
    'document_processing_errors_total',
    'Total document processing errors',
    ['error_type']
)

# === METRICS COLLECTION FUNCTIONS ===

def update_system_metrics():
    """Update system resource metrics"""
    try:
        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage_bytes.set(memory.used)
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage_percent.set(cpu_percent)
    except Exception as e:
        print(f"Error updating system metrics: {e}")

def record_http_request(method: str, endpoint: str, status: int, duration: float):
    """Record HTTP request metrics"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

def record_pii_detection(pii_type: str, duration: float):
    """Record PII detection metrics"""
    pii_detection_total.labels(pii_type=pii_type).inc()
    pii_detection_duration_seconds.observe(duration)

def record_pii_detection_error(error_type: str):
    """Record PII detection error metrics"""
    pii_detection_errors_total.labels(error_type=error_type).inc()

def record_deanonymization_request(duration: float):
    """Record deanonymization request metrics"""
    deanonymization_requests_total.inc()
    deanonymization_duration_seconds.observe(duration)

def record_deanonymization_failure(failure_type: str):
    """Record deanonymization failure metrics"""
    deanonymization_failures_total.labels(failure_type=failure_type).inc()

def record_document_processing(document_type: str):
    """Record document processing metrics"""
    document_processing_total.labels(document_type=document_type).inc()

def record_document_processing_error(error_type: str):
    """Record document processing error metrics"""
    document_processing_errors_total.labels(error_type=error_type).inc()

def update_active_sessions(count: int):
    """Update active sessions count"""
    active_sessions_total.set(count)

# === METRICS ENDPOINTS ===

@router.get("/")
async def get_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus format
    """
    # Update system metrics before returning
    update_system_metrics()
    
    # Generate metrics in Prometheus format
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )

@router.get("/health")
async def get_metrics_health():
    """
    Health check endpoint for metrics service
    """
    try:
        # Basic health checks
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "memory_usage_percent": memory.percent,
                "cpu_usage_percent": cpu_percent,
                "available_memory_mb": memory.available // (1024 * 1024)
            },
            "metrics": {
                "prometheus_registry_collectors": len(REGISTRY._collector_to_names),
                "http_requests_collected": http_requests_total._value.sum(),
                "pii_detections_collected": pii_detection_total._value.sum(),
                "deanonymization_requests_collected": deanonymization_requests_total._value.sum()
            }
        }
        
        return JSONResponse(content=health_data)
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            },
            status_code=500
        )

@router.get("/summary")
async def get_metrics_summary():
    """
    Get a summary of key metrics
    """
    try:
        # Update system metrics
        update_system_metrics()
        
        summary = {
            "timestamp": time.time(),
            "http_requests": {
                "total": http_requests_total._value.sum(),
                "avg_duration": http_request_duration_seconds._sum.sum() / max(http_request_duration_seconds._count.sum(), 1)
            },
            "pii_detection": {
                "total_detections": pii_detection_total._value.sum(),
                "total_errors": pii_detection_errors_total._value.sum(),
                "avg_duration": pii_detection_duration_seconds._sum.sum() / max(pii_detection_duration_seconds._count.sum(), 1)
            },
            "deanonymization": {
                "total_requests": deanonymization_requests_total._value.sum(),
                "total_failures": deanonymization_failures_total._value.sum(),
                "avg_duration": deanonymization_duration_seconds._sum.sum() / max(deanonymization_duration_seconds._count.sum(), 1)
            },
            "system": {
                "memory_usage_bytes": system_memory_usage_bytes._value.get(),
                "cpu_usage_percent": system_cpu_usage_percent._value.get(),
                "active_sessions": active_sessions_total._value.get()
            }
        }
        
        return JSONResponse(content=summary)
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )