"""
Shield AI - Alerts and Webhook Management

Endpoints for receiving and processing alerts from monitoring systems
like AlertManager, and managing alert notifications.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import time
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

# Setup router and security
router = APIRouter(prefix="/api/alerts", tags=["Alerts"])
security = HTTPBasic()

# Setup logging
logger = logging.getLogger(__name__)

# === ALERT MODELS ===

class AlertLabel(BaseModel):
    """Alert label model"""
    alertname: Optional[str] = None
    instance: Optional[str] = None
    job: Optional[str] = None
    severity: Optional[str] = None

class AlertAnnotation(BaseModel):
    """Alert annotation model"""
    summary: Optional[str] = None
    description: Optional[str] = None

class Alert(BaseModel):
    """Individual alert model"""
    status: str  # "firing" or "resolved"
    labels: AlertLabel
    annotations: AlertAnnotation
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

class AlertManagerWebhook(BaseModel):
    """AlertManager webhook payload model"""
    receiver: str
    status: str  # "firing" or "resolved"
    alerts: List[Alert]
    groupLabels: Dict[str, Any]
    commonLabels: Dict[str, Any]
    commonAnnotations: Dict[str, Any]
    externalURL: str
    version: str
    groupKey: str

# === ALERT STORAGE (In-memory for now) ===

# Store recent alerts (in production, use Redis or database)
recent_alerts: List[Dict[str, Any]] = []
MAX_STORED_ALERTS = 100

def store_alert(alert_data: Dict[str, Any]):
    """Store alert in memory (temporary solution)"""
    alert_data["received_at"] = time.time()
    recent_alerts.insert(0, alert_data)
    
    # Keep only recent alerts
    if len(recent_alerts) > MAX_STORED_ALERTS:
        recent_alerts[:] = recent_alerts[:MAX_STORED_ALERTS]

# === AUTHENTICATION ===

def verify_alert_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verify basic auth credentials for alert webhooks
    """
    correct_username = secrets.compare_digest(credentials.username, "alert_user")
    correct_password = secrets.compare_digest(credentials.password, "alert_password")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

# === ALERT ENDPOINTS ===

@router.post("/webhook")
async def receive_alertmanager_webhook(
    webhook_data: AlertManagerWebhook,
    credentials: HTTPBasicCredentials = Depends(verify_alert_credentials)
):
    """
    Receive webhooks from AlertManager
    
    This endpoint processes incoming alerts from Prometheus AlertManager
    and can trigger actions like notifications, logging, or automated responses.
    """
    try:
        logger.info(f"Received AlertManager webhook: {webhook_data.status} - {len(webhook_data.alerts)} alerts")
        
        # Process each alert
        processed_alerts = []
        for alert in webhook_data.alerts:
            alert_info = {
                "status": alert.status,
                "alertname": alert.labels.alertname,
                "instance": alert.labels.instance,
                "severity": alert.labels.severity,
                "summary": alert.annotations.summary,
                "description": alert.annotations.description,
                "starts_at": alert.startsAt,
                "ends_at": alert.endsAt,
                "fingerprint": alert.fingerprint
            }
            
            processed_alerts.append(alert_info)
            
            # Log alert based on severity
            if alert.labels.severity == "critical":
                logger.critical(f"CRITICAL ALERT: {alert.annotations.summary} - {alert.annotations.description}")
            elif alert.labels.severity == "warning":
                logger.warning(f"WARNING ALERT: {alert.annotations.summary} - {alert.annotations.description}")
            else:
                logger.info(f"INFO ALERT: {alert.annotations.summary} - {alert.annotations.description}")
        
        # Store webhook data
        webhook_info = {
            "receiver": webhook_data.receiver,
            "status": webhook_data.status,
            "group_key": webhook_data.groupKey,
            "alerts_count": len(webhook_data.alerts),
            "alerts": processed_alerts,
            "common_labels": dict(webhook_data.commonLabels),
            "common_annotations": dict(webhook_data.commonAnnotations)
        }
        
        store_alert(webhook_info)
        
        # Here you could add additional alert processing:
        # - Send notifications (email, Slack, etc.)
        # - Trigger automated responses
        # - Update external systems
        # - Store in database
        
        logger.info(f"Successfully processed {len(webhook_data.alerts)} alerts from AlertManager")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Processed {len(webhook_data.alerts)} alerts",
            "alerts_processed": len(processed_alerts),
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error processing AlertManager webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
        )

@router.get("/recent")
async def get_recent_alerts(limit: int = 20):
    """
    Get recent alerts received by the system
    """
    try:
        # Return recent alerts with limit
        alerts_to_return = recent_alerts[:min(limit, len(recent_alerts))]
        
        return JSONResponse(content={
            "status": "success",
            "alerts_count": len(alerts_to_return),
            "total_stored": len(recent_alerts),
            "alerts": alerts_to_return,
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving recent alerts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving alerts: {str(e)}"
        )

@router.get("/summary")
async def get_alerts_summary():
    """
    Get summary of alert statistics
    """
    try:
        # Calculate statistics
        total_alerts = len(recent_alerts)
        
        # Count by status
        firing_count = 0
        resolved_count = 0
        
        # Count by severity
        critical_count = 0
        warning_count = 0
        info_count = 0
        
        # Recent alerts (last hour)
        current_time = time.time()
        recent_count = 0
        
        for alert_data in recent_alerts:
            # Count by status
            if alert_data.get("status") == "firing":
                firing_count += 1
            elif alert_data.get("status") == "resolved":
                resolved_count += 1
            
            # Count recent alerts
            if current_time - alert_data.get("received_at", 0) <= 3600:  # 1 hour
                recent_count += 1
            
            # Count by severity (from alerts array)
            for alert in alert_data.get("alerts", []):
                severity = alert.get("severity")
                if severity == "critical":
                    critical_count += 1
                elif severity == "warning":
                    warning_count += 1
                else:
                    info_count += 1
        
        summary = {
            "total_alerts": total_alerts,
            "status_breakdown": {
                "firing": firing_count,
                "resolved": resolved_count
            },
            "severity_breakdown": {
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count
            },
            "recent_alerts_last_hour": recent_count,
            "timestamp": current_time
        }
        
        return JSONResponse(content=summary)
        
    except Exception as e:
        logger.error(f"Error generating alerts summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )

@router.delete("/clear")
async def clear_stored_alerts():
    """
    Clear all stored alerts (admin function)
    """
    try:
        alerts_cleared = len(recent_alerts)
        recent_alerts.clear()
        
        logger.info(f"Cleared {alerts_cleared} stored alerts")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Cleared {alerts_cleared} alerts",
            "alerts_cleared": alerts_cleared,
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error clearing alerts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing alerts: {str(e)}"
        )

@router.get("/health")
async def alerts_health_check():
    """
    Health check for alerts system
    """
    try:
        health_data = {
            "status": "healthy",
            "alerts_system": "operational",
            "stored_alerts": len(recent_alerts),
            "max_capacity": MAX_STORED_ALERTS,
            "usage_percent": (len(recent_alerts) / MAX_STORED_ALERTS) * 100,
            "timestamp": time.time()
        }
        
        return JSONResponse(content=health_data)
        
    except Exception as e:
        logger.error(f"Error in alerts health check: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            },
            status_code=500
        )