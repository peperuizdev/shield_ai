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

PLATE_DETECTOR = None
try:
    from ultralytics import YOLO
    PLATE_DETECTOR = None 
    logger.info("✅ YOLO available for license plate detection")
except ImportError:
    logger.warning("⚠️  YOLO not available. License plate detection will be limited")


class ImageAnonymizer:
    
    def __init__(self, face_method: str = "blur", plate_method: str = "pixelate"):

        self.face_method = face_method
        self.plate_method = plate_method
        self.max_image_size = (1920, 1080) 
        
        self._yolo_model = None
        
        logger.info(f"ImageAnonymizer initialized: faces={face_method}, plates={plate_method}")
    
    def _load_yolo_model(self):
        """Lazy load YOLO model"""
        if self._yolo_model is None and PLATE_DETECTOR is not None:
            try:
                from ultralytics import YOLO

                self._yolo_model = YOLO('yolov8n.pt')
                logger.info("✅ YOLO model loaded")
            except Exception as e:
                logger.error(f"❌ Error loading YOLO: {e}")
        return self._yolo_model
    
    def _resize_if_needed(self, img: np.ndarray) -> Tuple[np.ndarray, float]:

        h, w = img.shape[:2]
        max_w, max_h = self.max_image_size
        
        if w <= max_w and h <= max_h:
            return img, 1.0
        
        scale = min(max_w / w, max_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
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
    
    def detect_license_plates(self, img: np.ndarray) -> List[Dict[str, Any]]:
        plates = []
        
        model = self._load_yolo_model()
        if model is not None:
            try:
                results = model(img, verbose=False)
                
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        width = x2 - x1
                        height = y2 - y1
                        aspect_ratio = width / height if height > 0 else 0
                        
                        if 1.5 < aspect_ratio < 6.0 and confidence > 0.3:
                            plates.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': float(confidence),
                                'detector': 'yolo',
                                'aspect_ratio': float(aspect_ratio)
                            })
                
                logger.info(f"YOLO detected {len(plates)} potential license plates")
            except Exception as e:
                logger.error(f"YOLO detection failed: {e}")
        
        if len(plates) == 0:
            try:
                plates = self._detect_plates_by_contours(img)
                logger.info(f"Contour detection found {len(plates)} potential license plates")
            except Exception as e:
                logger.error(f"Contour detection failed: {e}")
        
        return plates
    
    def _detect_plates_by_contours(self, img: np.ndarray) -> List[Dict[str, Any]]:

        plates = []
        
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 50, 150)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                area = w * h
                
                if (1.5 < aspect_ratio < 6.0 and  
                    area > 1000 and                
                    area < img.shape[0] * img.shape[1] * 0.1):  
                    
                    plates.append({
                        'bbox': [int(x), int(y), int(x + w), int(y + h)],
                        'confidence': 0.5, 
                        'detector': 'contour',
                        'aspect_ratio': float(aspect_ratio)
                    })
        except Exception as e:
            logger.error(f"Contour detection error: {e}")
        
        return plates
    
    def apply_blur(self, img: np.ndarray, bbox: List[int], strength: int = 99) -> np.ndarray:
        """Apply Gaussian blur to a region."""
        x1, y1, x2, y2 = bbox
        region = img[y1:y2, x1:x2].copy()
        
        if strength % 2 == 0:
            strength += 1
        
        blurred = cv2.GaussianBlur(region, (strength, strength), 30)
        img[y1:y2, x1:x2] = blurred
        
        return img
    
    def apply_pixelate(self, img: np.ndarray, bbox: List[int], pixel_size: int = 20) -> np.ndarray:
        """Apply pixelation to a region."""
        x1, y1, x2, y2 = bbox
        region = img[y1:y2, x1:x2].copy()
        
        h, w = region.shape[:2]
        
        small = cv2.resize(region, (w // pixel_size, h // pixel_size), 
                          interpolation=cv2.INTER_LINEAR)
        
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        img[y1:y2, x1:x2] = pixelated
        
        return img
    
    def apply_black_box(self, img: np.ndarray, bbox: List[int]) -> np.ndarray:
        """Apply black rectangle to a region."""
        x1, y1, x2, y2 = bbox
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
        region = img[y1:y2, x1:x2].copy()
        
        # Encode as PNG to preserve quality
        _, buffer = cv2.imencode('.png', region)
        region_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return region_base64
    
    def anonymize_image(
        self, 
        img: np.ndarray, 
        detect_faces: bool = True, 
        detect_plates: bool = True,
        store_originals: bool = True
    ) -> Tuple[np.ndarray, Dict[str, Any]]:

        img_processed, scale_factor = self._resize_if_needed(img)
        
        anonymization_map = {
            'faces': [],
            'plates': [],
            'image_shape': list(img_processed.shape),
            'scale_factor': float(scale_factor),
            'methods': {
                'faces': self.face_method,
                'plates': self.plate_method
            }
        }
        
        img_anonymized = img_processed.copy()
        
        if detect_faces:
            faces = self.detect_faces(img_processed)
            logger.info(f"Detected {len(faces)} faces")
            
            for i, face in enumerate(faces):
                bbox = face['bbox']
                
                original_base64 = None
                if store_originals:
                    try:
                        original_base64 = self.extract_region_base64(img_processed, bbox)
                    except Exception as e:
                        logger.warning(f"Could not extract face region: {e}")
                
                img_anonymized = self.anonymize_region(img_anonymized, bbox, self.face_method)
                
                anonymization_map['faces'].append({
                    'id': f'face_{i + 1}',
                    'bbox': bbox,
                    'confidence': face.get('confidence', 1.0),
                    'detector': face.get('detector', 'unknown'),
                    'method': self.face_method,
                    'original_base64': original_base64
                })
        
        if detect_plates:
            plates = self.detect_license_plates(img_processed)
            logger.info(f"Detected {len(plates)} license plates")
            
            for i, plate in enumerate(plates):
                bbox = plate['bbox']
                
                original_base64 = None
                if store_originals:
                    try:
                        original_base64 = self.extract_region_base64(img_processed, bbox)
                    except Exception as e:
                        logger.warning(f"Could not extract plate region: {e}")
                
                img_anonymized = self.anonymize_region(img_anonymized, bbox, self.plate_method)
                
                anonymization_map['plates'].append({
                    'id': f'plate_{i + 1}',
                    'bbox': bbox,
                    'confidence': plate.get('confidence', 1.0),
                    'detector': plate.get('detector', 'unknown'),
                    'method': self.plate_method,
                    'original_base64': original_base64
                })
        
        total_detections = len(anonymization_map['faces']) + len(anonymization_map['plates'])
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
        
        for plate in anonymization_map.get('plates', []):
            if 'original_base64' in plate and plate['original_base64']:
                try:
                    region_bytes = base64.b64decode(plate['original_base64'])
                    region_array = np.frombuffer(region_bytes, dtype=np.uint8)
                    region = cv2.imdecode(region_array, cv2.IMREAD_COLOR)
                    
                    bbox = plate['bbox']
                    x1, y1, x2, y2 = bbox
                    
                    expected_h = y2 - y1
                    expected_w = x2 - x1
                    if region.shape[0] != expected_h or region.shape[1] != expected_w:
                        region = cv2.resize(region, (expected_w, expected_h))
                    
                    img_restored[y1:y2, x1:x2] = region
                    
                except Exception as e:
                    logger.error(f"Error restoring plate region: {e}")
        
        total_restored = len([f for f in anonymization_map.get('faces', []) if f.get('original_base64')]) + \
                        len([p for p in anonymization_map.get('plates', []) if p.get('original_base64')])
        
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