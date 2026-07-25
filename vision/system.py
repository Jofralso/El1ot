"""
ELIOT Vision System

Camera support, face recognition, OCR.
All processing local - no cloud dependencies.
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class VisionState(str, Enum):
    IDLE = "idle"
    CAPTURING = "capturing"
    RECOGNIZING = "recognizing"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class FaceIdentity:
    name: str
    confidence: float
    bounding_box: List[int] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class CameraManager:
    """Manages camera capture."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._cap = None

    async def initialize(self):
        try:
            import cv2
            self._cap = cv2.VideoCapture(self.device_index)
            if self._cap.isOpened():
                logger.info(f"Camera initialized: device {self.device_index}")
            else:
                logger.warning(f"Camera {self.device_index} not available")
                self._cap = None
        except ImportError:
            logger.warning("opencv-python not installed")
        except Exception as e:
            logger.error(f"Camera init error: {e}")

    async def capture(self) -> Optional[Any]:
        if not self._cap:
            return None
        try:
            ret, frame = self._cap.read()
            return frame if ret else None
        except Exception as e:
            logger.error(f"Capture error: {e}")
            return None

    def release(self):
        if self._cap:
            self._cap.release()
            self._cap = None


class FaceRecognitionEngine:
    """Face recognition using local embeddings."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self._model = None

    async def initialize(self):
        try:
            import face_recognition
            self._model = face_recognition
            logger.info("Face recognition engine initialized")
        except ImportError:
            logger.warning("face_recognition not installed")
        except Exception as e:
            logger.error(f"Face recognition init error: {e}")

    async def recognize(
        self,
        frame,
        known_faces: Dict[str, str],
    ) -> List[FaceIdentity]:
        if not self._model or frame is None:
            return []

        try:
            import numpy as np
            face_locations = self._model.face_locations(np.array(frame))
            face_encodings = self._model.face_encodings(np.array(frame), face_locations)

            identities = []
            for encoding, location in zip(face_encodings, face_locations):
                best_name = "unknown"
                best_confidence = 0.0
                for name, known_encoding in known_faces.items():
                    import numpy as np
                    distance = self._model.face_distance([known_encoding], encoding)[0]
                    confidence = 1.0 - distance
                    if confidence > best_confidence and confidence > self.threshold:
                        best_name = name
                        best_confidence = confidence
                identities.append(FaceIdentity(
                    name=best_name,
                    confidence=best_confidence,
                    bounding_box=list(location),
                ))
            return identities
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return []


class OCREngine:
    """OCR using local Tesseract or EasyOCR."""

    def __init__(self):
        self._reader = None

    async def initialize(self):
        try:
            import easyocr
            self._reader = easyocr.Reader(["en"])
            logger.info("OCR engine initialized (EasyOCR)")
        except ImportError:
            logger.warning("easyocr not installed, OCR unavailable")
        except Exception as e:
            logger.error(f"OCR init error: {e}")

    async def recognize_text(self, frame) -> str:
        if not self._reader or frame is None:
            return "[OCR not available]"
        try:
            import numpy as np
            results = self._reader.readtext(np.array(frame))
            return " ".join(text for _, text, _ in results)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "[OCR failed]"


class VisionManager:
    """Manages the complete vision pipeline."""

    def __init__(self):
        self.state = VisionState.IDLE
        self.camera = CameraManager()
        self.face_engine = FaceRecognitionEngine()
        self.ocr_engine = OCREngine()
        self._known_faces: Dict[str, str] = {}
        self._initialized = False

    async def initialize(self):
        await self.camera.initialize()
        await self.face_engine.initialize()
        await self.ocr_engine.initialize()
        self._initialized = True
        logger.info("Vision system initialized")

    def register_face(self, name: str, encoding: str):
        self._known_faces[name] = encoding

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "initialized": self._initialized,
            "camera_active": self.camera._cap is not None,
            "face_engine_ready": self.face_engine._model is not None,
            "ocr_ready": self.ocr_engine._reader is not None,
            "known_faces": len(self._known_faces),
        }


_vision_manager: Optional[VisionManager] = None


def get_vision_manager() -> VisionManager:
    global _vision_manager
    if _vision_manager is None:
        _vision_manager = VisionManager()
    return _vision_manager
