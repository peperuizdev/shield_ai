import cv2
import numpy as np
import base64
import logging
import io
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image

logger = logging.getLogger(__name__)

FACE_DETECTOR = None
FACE_DETECTOR_TYPE = None

try:
    from retinaface import RetinaFace
    FACE_DETECTOR = RetinaFace
    FACE_DETECTOR_TYPE = "retinaface"
    logger.info("✅ RetinaFace loaded for face detection")
except ImportError:
    try:
        from mtcnn import MTCNN
        FACE_DETECTOR = MTCNN()
        FACE_DETECTOR_TYPE = "mtcnn"
        logger.info("✅ MTCNN loaded for face detection")
    except ImportError:
        logger.warning("⚠️  No face detection library found. Face detection will use Haar Cascades (less accurate)")
        FACE_DETECTOR_TYPE = "haar"


class ImageAnonymizer:
    
    def __init__(self, face_method: str = "blur"):
        self.face_method = face_method
        self.max_image_size = (1920, 1080) 
        
        logger.info(f"ImageAnonymizer initialized: faces={face_method}")
    
    def _resize_if_needed(self, img: np.ndarray) -> Tuple[np.ndarray, float]:
        if img is None or img.size == 0:
            raise ValueError("Invalid image: empty or None")
        
        h, w = img.shape[:2]
        
        if h <= 0 or w <= 0:
            raise ValueError(f"Invalid image dimensions: {w}x{h}")
        
        max_w, max_h = self.max_image_size
        
        if w <= max_w and h <= max_h:
            return img, 1.0
        
        scale = min(max_w / w, max_h / h)
        
        if scale <= 0:
            raise ValueError(f"Invalid scale factor: {scale}")
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        if new_w <= 0 or new_h <= 0:
            raise ValueError(f"Invalid target dimensions: {new_w}x{new_h}")
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.info(f"Image resized from {w}x{h} to {new_w}x{new_h} (scale={scale:.2f})")
        
        return resized, scale
    
    def detect_faces(self, img: np.ndarray) -> List[Dict[str, Any]]:
        faces = []
        
        if FACE_DETECTOR_TYPE == "retinaface":
            try:
                detections = RetinaFace.detect_faces(img)
                if isinstance(detections, dict):
                    for key, face_data in detections.items():
                        facial_area = face_data.get('facial_area', [])
                        if len(facial_area) == 4:
                            x1, y1, x2, y2 = facial_area
                            faces.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': face_data.get('score', 1.0),
                                'detector': 'retinaface'
                            })
                logger.info(f"RetinaFace detected {len(faces)} faces")
            except Exception as e:
                logger.error(f"RetinaFace detection failed: {e}")
        
        elif FACE_DETECTOR_TYPE == "mtcnn":
            try:
                detections = FACE_DETECTOR.detect_faces(img)
                for detection in detections:
                    bbox = detection.get('box', [])
                    if len(bbox) == 4:
                        x, y, w, h = bbox
                        faces.append({
                            'bbox': [int(x), int(y), int(x + w), int(y + h)],
                            'confidence': detection.get('confidence', 1.0),
                            'detector': 'mtcnn'
                        })
                logger.info(f"MTCNN detected {len(faces)} faces")
            except Exception as e:
                logger.error(f"MTCNN detection failed: {e}")
        
        else: 
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                detections = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                for (x, y, w, h) in detections:
                    faces.append({
                        'bbox': [int(x), int(y), int(x + w), int(y + h)],
                        'confidence': 0.8,  
                        'detector': 'haar'
                    })
                logger.info(f"Haar Cascades detected {len(faces)} faces")
            except Exception as e:
                logger.error(f"Haar Cascades detection failed: {e}")
        
        return faces
    
    def apply_blur(self, img: np.ndarray, bbox: List[int], strength: int = 99) -> np.ndarray:
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            logger.warning(f"Invalid bbox dimensions: {bbox}, skipping blur")
            return img
        
        region = img[y1:y2, x1:x2].copy()
        
        if region.size == 0:
            logger.warning(f"Empty region for bbox: {bbox}, skipping blur")
            return img
        
        if strength % 2 == 0:
            strength += 1
        
        blurred = cv2.GaussianBlur(region, (strength, strength), 30)
        img[y1:y2, x1:x2] = blurred
        
        return img
    
    def apply_pixelate(self, img: np.ndarray, bbox: List[int], pixel_size: int = 20) -> np.ndarray:
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            logger.warning(f"Invalid bbox dimensions: {bbox}, skipping pixelate")
            return img
        
        region = img[y1:y2, x1:x2].copy()
        
        if region.size == 0:
            logger.warning(f"Empty region for bbox: {bbox}, skipping pixelate")
            return img
        
        h, w = region.shape[:2]
        
        if w < pixel_size or h < pixel_size:
            logger.warning(f"Region too small for pixelation: {w}x{h}, using minimum size")
            pixel_size = min(max(w // 2, 1), max(h // 2, 1))
        
        small = cv2.resize(region, (max(w // pixel_size, 1), max(h // pixel_size, 1)), 
                          interpolation=cv2.INTER_LINEAR)
        
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        img[y1:y2, x1:x2] = pixelated
        
        return img
    
    def apply_black_box(self, img: np.ndarray, bbox: List[int]) -> np.ndarray:
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            logger.warning(f"Invalid bbox dimensions: {bbox}, skipping black box")
            return img
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
        return img
    
    def anonymize_region(self, img: np.ndarray, bbox: List[int], method: str) -> np.ndarray:
        if method == "blur":
            return self.apply_blur(img, bbox)
        elif method == "pixelate":
            return self.apply_pixelate(img, bbox)
        elif method == "black":
            return self.apply_black_box(img, bbox)
        else:
            logger.warning(f"Unknown method {method}, using blur")
            return self.apply_blur(img, bbox)
    
    def extract_region_base64(self, img: np.ndarray, bbox: List[int]) -> str:
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            logger.warning(f"Invalid bbox dimensions: {bbox}, cannot extract region")
            return ""
        
        region = img[y1:y2, x1:x2].copy()
        
        if region.size == 0:
            logger.warning(f"Empty region for bbox: {bbox}, cannot extract")
            return ""
        
        _, buffer = cv2.imencode('.png', region)
        region_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return region_base64
    
    def anonymize_image(
        self, 
        img: np.ndarray, 
        detect_faces: bool = True,
        store_originals: bool = True
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        img_processed, scale_factor = self._resize_if_needed(img)
        
        anonymization_map = {
            'faces': [],
            'image_shape': list(img.shape),
            'scale_factor': float(scale_factor),
            'methods': {
                'faces': self.face_method
            }
        }
        
        img_anonymized = img.copy()
        
        if detect_faces:
            faces = self.detect_faces(img_processed)
            logger.info(f"Detected {len(faces)} faces")
            
            for i, face in enumerate(faces):
                bbox_small = face['bbox']
                
                bbox_original = [
                    int(bbox_small[0] / scale_factor),
                    int(bbox_small[1] / scale_factor),
                    int(bbox_small[2] / scale_factor),
                    int(bbox_small[3] / scale_factor)
                ]
                
                h, w = img.shape[:2]
                bbox_original[0] = max(0, min(bbox_original[0], w - 1))
                bbox_original[1] = max(0, min(bbox_original[1], h - 1))
                bbox_original[2] = max(bbox_original[0] + 1, min(bbox_original[2], w))
                bbox_original[3] = max(bbox_original[1] + 1, min(bbox_original[3], h))
                
                original_base64 = None
                if store_originals:
                    try:
                        original_base64 = self.extract_region_base64(img, bbox_original)
                    except Exception as e:
                        logger.warning(f"Could not extract face region: {e}")
                
                img_anonymized = self.anonymize_region(img_anonymized, bbox_original, self.face_method)
                
                anonymization_map['faces'].append({
                    'id': f'face_{i + 1}',
                    'bbox': bbox_original,
                    'confidence': face.get('confidence', 1.0),
                    'detector': face.get('detector', 'unknown'),
                    'method': self.face_method,
                    'original_base64': original_base64
                })
        
        total_detections = len(anonymization_map['faces'])
        logger.info(f"Anonymization complete: {total_detections} regions anonymized")
        
        return img_anonymized, anonymization_map
    
    def deanonymize_image(
        self, 
        img_anonymized: np.ndarray, 
        anonymization_map: Dict[str, Any]
    ) -> np.ndarray:
        img_restored = img_anonymized.copy()
        
        for face in anonymization_map.get('faces', []):
            if 'original_base64' in face and face['original_base64']:
                try:
                    region_bytes = base64.b64decode(face['original_base64'])
                    region_array = np.frombuffer(region_bytes, dtype=np.uint8)
                    region = cv2.imdecode(region_array, cv2.IMREAD_COLOR)
                    
                    bbox = face['bbox']
                    x1, y1, x2, y2 = bbox
                    
                    expected_h = y2 - y1
                    expected_w = x2 - x1
                    if region.shape[0] != expected_h or region.shape[1] != expected_w:
                        region = cv2.resize(region, (expected_w, expected_h))
                    
                    img_restored[y1:y2, x1:x2] = region
                    
                except Exception as e:
                    logger.error(f"Error restoring face region: {e}")
        
        total_restored = len([f for f in anonymization_map.get('faces', []) if f.get('original_base64')])
        
        logger.info(f"Deanonymization complete: {total_restored} regions restored")
        
        return img_restored


def image_to_base64(img: np.ndarray, format: str = 'png', quality: int = 85) -> str:
    if format.lower() == 'jpg' or format.lower() == 'jpeg':
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode('.jpg', img, encode_param)
    else:
        _, buffer = cv2.imencode('.png', img)
    
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64


def base64_to_image(img_base64: str) -> np.ndarray:
    if ',' in img_base64:
        img_base64 = img_base64.split(',', 1)[1]
    
    img_bytes = base64.b64decode(img_base64)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    return img


def load_image_from_bytes(file_bytes: bytes) -> np.ndarray:
    img_array = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode image from bytes")
    
    return img


__all__ = [
    'ImageAnonymizer',
    'image_to_base64',
    'base64_to_image',
    'load_image_from_bytes'
]