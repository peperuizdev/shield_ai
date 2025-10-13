from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
import logging
import io
import json

from services.image_anonymizer import (
    ImageAnonymizer,
    image_to_base64,
    base64_to_image,
    load_image_from_bytes
)

from services.session_manager import (
    store_anonymization_map,
    get_anonymization_map,
    get_session_manager
)

from utils.helpers import generate_session_id

router_image = APIRouter(prefix="/anonymize", tags=["Image Anonymization"])
logger = logging.getLogger(__name__)


@router_image.post("/image")
async def anonymize_image(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    detect_faces: Optional[bool] = Form(True),
    detect_plates: Optional[bool] = Form(True),
    face_method: Optional[str] = Form("blur"),
    plate_method: Optional[str] = Form("pixelate"),
    store_originals: Optional[bool] = Form(True),
    return_format: Optional[str] = Form("base64")  # "base64" or "binary"
):
    try:
        logger.info(f"📸 Processing image: {file.filename}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        allowed_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if file.content_type not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed: {', '.join(allowed_formats)}"
            )
        
        if not session_id or session_id.strip() == "" or session_id == "string":
            session_id = generate_session_id(prefix="img")
            logger.info(f"🆔 Auto-generated session ID: {session_id}")
        
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        max_size = 10 * 1024 * 1024  
        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size / (1024*1024):.1f}MB"
            )
        
        logger.info(f"📦 File size: {len(file_bytes) / 1024:.2f} KB")
        
        try:
            img = load_image_from_bytes(file_bytes)
            logger.info(f"✅ Image loaded: shape={img.shape}")
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not load image: {str(e)}"
            )
        
        anonymizer = ImageAnonymizer(
            face_method=face_method,
            plate_method=plate_method
        )
        
        try:
            img_anonymized, anonymization_map = anonymizer.anonymize_image(
                img=img,
                detect_faces=detect_faces,
                detect_plates=detect_plates,
                store_originals=store_originals
            )
            logger.info(f"✅ Image anonymized successfully")
        except Exception as e:
            logger.error(f"❌ Anonymization failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Image anonymization failed: {str(e)}"
            )
        
        faces_detected = len(anonymization_map.get('faces', []))
        plates_detected = len(anonymization_map.get('plates', []))
        total_detections = faces_detected + plates_detected
        
        logger.info(f"📊 Detections: {faces_detected} faces, {plates_detected} plates")
        
        try:
            store_anonymization_map(session_id, anonymization_map)
            logger.info(f"💾 Map stored in Redis for session: {session_id}")
        except Exception as e:
            logger.warning(f"⚠️  Could not store map in Redis: {e}")
        
        img_base64 = image_to_base64(img_anonymized, format='jpg', quality=85)
        
        if return_format == "binary":
            import cv2
            _, buffer = cv2.imencode('.jpg', img_anonymized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            
            return StreamingResponse(
                io.BytesIO(buffer.tobytes()),
                media_type="image/jpeg",
                headers={
                    "X-Session-ID": session_id,
                    "X-Faces-Detected": str(faces_detected),
                    "X-Plates-Detected": str(plates_detected)
                }
            )
        else:
            return {
                "success": True,
                "session_id": session_id,
                "anonymized_image": f"data:image/jpeg;base64,{img_base64}",
                "pii_detected": total_detections > 0,
                "detections": {
                    "faces": faces_detected,
                    "plates": plates_detected,
                    "total": total_detections
                },
                "image_info": {
                    "filename": file.filename,
                    "original_format": file.content_type,
                    "size_kb": len(file_bytes) / 1024,
                    "shape": list(img.shape)
                },
                "methods": anonymization_map.get('methods', {})
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error processing image: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router_image.get("/session/{session_id}/image-map")
async def get_image_anonymization_map(session_id: str):
    
    try:
        logger.info(f"🔍 Retrieving image map for session: {session_id}")
        
        anonymization_map = get_anonymization_map(session_id)
        
        map_metadata = {
            'session_id': session_id,
            'image_shape': anonymization_map.get('image_shape'),
            'scale_factor': anonymization_map.get('scale_factor'),
            'methods': anonymization_map.get('methods'),
            'faces': [
                {
                    'id': face.get('id'),
                    'bbox': face.get('bbox'),
                    'confidence': face.get('confidence'),
                    'detector': face.get('detector'),
                    'method': face.get('method'),
                    'has_original': bool(face.get('original_base64'))
                }
                for face in anonymization_map.get('faces', [])
            ],
            'plates': [
                {
                    'id': plate.get('id'),
                    'bbox': plate.get('bbox'),
                    'confidence': plate.get('confidence'),
                    'detector': plate.get('detector'),
                    'method': plate.get('method'),
                    'has_original': bool(plate.get('original_base64'))
                }
                for plate in anonymization_map.get('plates', [])
            ]
        }
        
        total_detections = len(map_metadata['faces']) + len(map_metadata['plates'])
        
        return {
            "success": True,
            "session_id": session_id,
            "map": map_metadata,
            "total_detections": total_detections
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving image map: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve image map: {str(e)}"
        )


@router_image.post("/image/deanonymize")
async def deanonymize_image(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    return_format: Optional[str] = Form("base64")
):
    try:
        logger.info(f"🔓 Deanonymizing image for session: {session_id}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_bytes = await file.read()
        img_anonymized = load_image_from_bytes(file_bytes)
        
        anonymization_map = get_anonymization_map(session_id)
        
        anonymizer = ImageAnonymizer()
        
        try:
            img_restored = anonymizer.deanonymize_image(img_anonymized, anonymization_map)
            logger.info(f"✅ Image deanonymized successfully")
        except Exception as e:
            logger.error(f"❌ Deanonymization failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Image deanonymization failed: {str(e)}"
            )
        
        if return_format == "binary":
            import cv2
            _, buffer = cv2.imencode('.jpg', img_restored, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            
            return StreamingResponse(
                io.BytesIO(buffer.tobytes()),
                media_type="image/jpeg",
                headers={"X-Session-ID": session_id}
            )
        else:
            img_base64 = image_to_base64(img_restored, format='jpg', quality=95)
            
            return {
                "success": True,
                "session_id": session_id,
                "restored_image": f"data:image/jpeg;base64,{img_base64}",
                "regions_restored": len(anonymization_map.get('faces', [])) + 
                                  len(anonymization_map.get('plates', []))
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deanonymizing image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deanonymize image: {str(e)}"
        )


@router_image.get("/test-image-detector")
async def test_image_detector():

    from services.image_anonymizer import FACE_DETECTOR_TYPE, PLATE_DETECTOR
    
    capabilities = {
        "face_detection": {
            "available": FACE_DETECTOR_TYPE is not None,
            "detector_type": FACE_DETECTOR_TYPE,
            "methods": ["retinaface", "mtcnn", "haar"]
        },
        "plate_detection": {
            "available": PLATE_DETECTOR is not None or True,  
            "detector_type": "yolo" if PLATE_DETECTOR else "contour",
            "methods": ["yolo", "contour"]
        },
        "anonymization_methods": {
            "faces": ["blur", "pixelate", "black"],
            "plates": ["blur", "pixelate", "black"]
        },
        "supported_formats": ["image/jpeg", "image/png", "image/webp"],
        "max_file_size_mb": 10
    }
    
    return {
        "success": True,
        "capabilities": capabilities,
        "status": "ready" if capabilities["face_detection"]["available"] else "limited"
    }


__all__ = ["router_image"]