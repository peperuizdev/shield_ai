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

# Redis mapping metrics
redis_mapping_sessions_total = Gauge(
    'redis_mapping_sessions_total',
    'Total number of sessions with mappings in Redis'
)

redis_mapping_entries_total = Gauge(
    'redis_mapping_entries_total',
    'Total number of mapping entries across all sessions in Redis'
)

redis_mapping_entries_per_session = Gauge(
    'redis_mapping_entries_per_session',
    'Average number of mapping entries per session',
    ['session_id']
)

redis_memory_usage_bytes = Gauge(
    'redis_memory_usage_bytes',
    'Redis memory usage in bytes'
)

redis_connection_status = Gauge(
    'redis_connection_status',
    'Redis connection status (1 = connected, 0 = disconnected)'
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

def update_redis_mapping_metrics():
    """Update Redis mapping-related metrics"""
    try:
        from core.redis_client import get_redis_client, get_redis_health
        import redis
        import json
        
        # Get Redis health and connection status
        redis_health = get_redis_health()
        redis_connection_status.set(1 if redis_health["status"] == "healthy" else 0)
        
        # If Redis is not healthy, set metrics to 0 and return
        if redis_health["status"] != "healthy":
            redis_mapping_sessions_total.set(0)
            redis_mapping_entries_total.set(0)
            redis_memory_usage_bytes.set(0)
            return
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Get Redis memory usage
        redis_info = redis_client.info('memory')
        redis_memory_usage_bytes.set(redis_info.get('used_memory', 0))
        
        # Find all session mapping keys
        session_keys = redis_client.keys("anon_map:session_*")
        session_keys = [k for k in session_keys if not k.endswith(('_request', '_meta', '_llm'))]
        
        redis_mapping_sessions_total.set(len(session_keys))
        
        # Count total mapping entries across all sessions
        total_mappings = 0
        session_mapping_counts = {}
        
        for session_key in session_keys:
            try:
                mapping_json = redis_client.get(session_key)
                if mapping_json:
                    mapping = json.loads(mapping_json)
                    mapping_count = len(mapping)
                    total_mappings += mapping_count
                    
                    # Extract session ID from key
                    session_id = session_key.replace("anon_map:session_", "")
                    session_mapping_counts[session_id] = mapping_count
                    
                    # Set per-session metric
                    redis_mapping_entries_per_session.labels(session_id=session_id).set(mapping_count)
            except (json.JSONDecodeError, redis.RedisError) as e:
                print(f"Error processing session {session_key}: {e}")
                continue
        
        redis_mapping_entries_total.set(total_mappings)
        
    except Exception as e:
        print(f"Error updating Redis mapping metrics: {e}")
        # Set error state
        redis_connection_status.set(0)
        redis_mapping_sessions_total.set(0)
        redis_mapping_entries_total.set(0)
        redis_memory_usage_bytes.set(0)

def record_mapping_session_created(session_id: str, mapping_count: int):
    """Record when a new mapping session is created"""
    redis_mapping_entries_per_session.labels(session_id=session_id).set(mapping_count)

def record_mapping_session_deleted(session_id: str):
    """Record when a mapping session is deleted"""
    # Remove the metric for this session
    try:
        redis_mapping_entries_per_session.remove(session_id)
    except Exception:
        pass  # Metric might not exist

# === METRICS ENDPOINTS ===

@router.get("/")
async def get_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus format
    """
    # Update system metrics before returning
    update_system_metrics()
    
    # Update Redis mapping metrics
    update_redis_mapping_metrics()
    
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
        
        # Update Redis metrics
        update_redis_mapping_metrics()
        
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
            },
            "redis": {
                "connection_status": redis_connection_status._value.get(),
                "memory_usage_bytes": redis_memory_usage_bytes._value.get(),
                "mapping_sessions_total": redis_mapping_sessions_total._value.get(),
                "mapping_entries_total": redis_mapping_entries_total._value.get(),
                "avg_mappings_per_session": redis_mapping_entries_total._value.get() / max(redis_mapping_sessions_total._value.get(), 1)
            }
        }
        
        return JSONResponse(content=summary)
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.get("/redis")
async def get_redis_metrics():
    """
    Get detailed Redis mapping metrics
    """
    try:
        # Update Redis metrics
        update_redis_mapping_metrics()
        
        from core.redis_client import get_redis_client, get_redis_health
        import json
        
        redis_health = get_redis_health()
        
        if redis_health["status"] != "healthy":
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "error": redis_health.get("error", "Redis connection failed"),
                    "timestamp": time.time()
                },
                status_code=503
            )
        
        redis_client = get_redis_client()
        
        # Get detailed session information
        session_keys = redis_client.keys("anon_map:session_*")
        session_keys = [k for k in session_keys if not k.endswith(('_request', '_meta', '_llm'))]
        
        sessions_detail = []
        total_mappings = 0
        
        for session_key in session_keys[:10]:  # Limit to first 10 for performance
            try:
                mapping_json = redis_client.get(session_key)
                if mapping_json:
                    mapping = json.loads(mapping_json)
                    mapping_count = len(mapping)
                    total_mappings += mapping_count
                    
                    session_id = session_key.replace("anon_map:session_", "")
                    
                    # Get TTL if available
                    ttl = redis_client.ttl(session_key)
                    
                    sessions_detail.append({
                        "session_id": session_id,
                        "mapping_count": mapping_count,
                        "ttl_seconds": ttl if ttl > 0 else None,
                        "sample_mappings": dict(list(mapping.items())[:3])  # First 3 mappings as sample
                    })
            except Exception as e:
                sessions_detail.append({
                    "session_id": session_key.replace("anon_map:session_", ""),
                    "error": str(e)
                })
        
        # Redis info
        redis_info = redis_client.info()
        
        redis_metrics = {
            "timestamp": time.time(),
            "connection_status": "healthy",
            "redis_info": {
                "version": redis_info.get("redis_version"),
                "memory_usage_bytes": redis_info.get("used_memory", 0),
                "memory_usage_human": redis_info.get("used_memory_human"),
                "connected_clients": redis_info.get("connected_clients", 0),
                "total_keys": redis_info.get("db0", {}).get("keys", 0) if "db0" in redis_info else 0
            },
            "mapping_sessions": {
                "total_sessions": len(session_keys),
                "total_mapping_entries": total_mappings,
                "avg_mappings_per_session": total_mappings / max(len(session_keys), 1),
                "sessions_detail": sessions_detail
            },
            "prometheus_metrics": {
                "redis_connection_status": redis_connection_status._value.get(),
                "redis_mapping_sessions_total": redis_mapping_sessions_total._value.get(),
                "redis_mapping_entries_total": redis_mapping_entries_total._value.get(),
                "redis_memory_usage_bytes": redis_memory_usage_bytes._value.get()
            }
        }
        
        return JSONResponse(content=redis_metrics)
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            },
            status_code=500
        )