"""
ELIOT Vision System

Camera support, face recognition, OCR, face registration.
All processing local - no cloud dependencies.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class VisionState(str, Enum):
    IDLE = "idle"
    CAPTURING = "capturing"
    RECOGNIZING = "recognizing"
    PROCESSING = "processing"
    REGISTERING = "registering"
    ERROR = "error"


@dataclass
class FaceIdentity:
    name: str
    confidence: float
    bounding_box: List[int] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class RegisteredFace:
    name: str
    user_id: str
    embeddings: List[List[float]] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    last_seen: float = 0.0
    access_count: int = 0


@dataclass
class FrameResult:
    timestamp: float = field(default_factory=time.time)
    faces: List[FaceIdentity] = field(default_factory=list)
    ocr_text: str = ""
    processed: bool = False


class CameraManager:
    """Manages camera capture with frame buffering."""

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None
        self._frame_count = 0
        self._last_frame = None

    async def initialize(self) -> bool:
        try:
            import cv2
            self._cap = cv2.VideoCapture(self.device_index)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self._cap.set(cv2.CAP_PROP_FPS, self.fps)
                logger.info(f"Camera initialized: device={self.device_index}, {self.width}x{self.height}@{self.fps}fps")
                return True
            else:
                logger.warning(f"Camera {self.device_index} not available")
                self._cap = None
                return False
        except ImportError:
            logger.warning("opencv-python not installed")
            return False
        except Exception as e:
            logger.error(f"Camera init error: {e}")
            return False

    async def capture(self) -> Optional[Any]:
        if not self._cap:
            return None
        try:
            ret, frame = self._cap.read()
            if ret:
                self._frame_count += 1
                self._last_frame = frame
                return frame
            return None
        except Exception as e:
            logger.error(f"Capture error: {e}")
            return None

    async def frame_stream(self) -> AsyncIterator[Any]:
        """Async generator yielding camera frames."""
        while self._cap and self._cap.isOpened():
            frame = await self.capture()
            if frame is not None:
                yield frame
            await asyncio.sleep(1.0 / self.fps)

    def get_frame_info(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self._frame_count,
            "has_frame": self._last_frame is not None,
        }

    def release(self):
        if self._cap:
            self._cap.release()
            self._cap = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "device_index": self.device_index,
            "active": self._cap is not None and self._cap.isOpened(),
            "frame_count": self._frame_count,
            **self.get_frame_info(),
        }


class FaceRecognitionEngine:
    """Face recognition using local embeddings."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self._model = None
        self._total_recognitions = 0
        self._total_faces_detected = 0

    async def initialize(self) -> bool:
        try:
            import face_recognition
            self._model = face_recognition
            logger.info("Face recognition engine initialized")
            return True
        except ImportError:
            logger.warning("face_recognition not installed")
            return False
        except Exception as e:
            logger.error(f"Face recognition init error: {e}")
            return False

    async def extract_encoding(self, frame, face_location=None) -> Optional[List[float]]:
        """Extract face encoding from a frame."""
        if not self._model or frame is None:
            return None
        try:
            import numpy as np
            np_frame = np.array(frame)
            if face_location:
                encodings = self._model.face_encodings(np_frame, [face_location])
            else:
                encodings = self._model.face_encodings(np_frame)
            if encodings:
                return encodings[0].tolist()
            return None
        except Exception as e:
            logger.error(f"Encoding extraction error: {e}")
            return None

    async def detect_faces(self, frame) -> List[List[int]]:
        """Detect face locations in a frame."""
        if not self._model or frame is None:
            return []
        try:
            import numpy as np
            locations = self._model.face_locations(np.array(frame))
            self._total_faces_detected += len(locations)
            return [list(loc) for loc in locations]
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    async def recognize(
        self,
        frame,
        known_faces: Dict[str, List[float]],
    ) -> List[FaceIdentity]:
        if not self._model or frame is None:
            return []

        try:
            import numpy as np
            np_frame = np.array(frame)
            face_locations = self._model.face_locations(np_frame)
            face_encodings = self._model.face_encodings(np_frame, face_locations)

            identities = []
            for encoding, location in zip(face_encodings, face_locations):
                best_name = "unknown"
                best_confidence = 0.0
                for name, known_encoding in known_faces.items():
                    known_enc = known_encoding[0] if isinstance(known_encoding[0], list) else known_encoding
                    distance = self._model.face_distance([known_enc], encoding)[0]
                    confidence = 1.0 - distance
                    if confidence > best_confidence and confidence > self.threshold:
                        best_name = name
                        best_confidence = confidence
                identities.append(FaceIdentity(
                    name=best_name,
                    confidence=best_confidence,
                    bounding_box=list(location),
                ))
            self._total_recognitions += 1
            return identities
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        return {
            "available": self._model is not None,
            "threshold": self.threshold,
            "total_recognitions": self._total_recognitions,
            "total_faces_detected": self._total_faces_detected,
        }


class FaceRegistration:
    """Manages face registration for known users."""

    def __init__(self, face_engine: FaceRecognitionEngine):
        self._engine = face_engine
        self._registered: Dict[str, RegisteredFace] = {}
        self._pending_name: str = ""
        self._pending_embeddings: List[List[float]] = []

    async def start_registration(self, name: str, user_id: str = ""):
        self._pending_name = name
        self._pending_embeddings = []
        logger.info(f"Face registration started for: {name}")

    async def add_sample(self, frame) -> bool:
        """Add a face sample during registration."""
        encoding = await self._engine.extract_encoding(frame)
        if encoding:
            self._pending_embeddings.append(encoding)
            logger.debug(f"Registration sample added ({len(self._pending_embeddings)} total)")
            return True
        return False

    async def complete_registration(self, user_id: str = "") -> bool:
        """Complete registration with collected samples."""
        if not self._pending_name or len(self._pending_embeddings) < 3:
            logger.warning("Need at least 3 samples to complete registration")
            return False

        face = RegisteredFace(
            name=self._pending_name,
            user_id=user_id or self._pending_name.lower().replace(" ", "_"),
            embeddings=self._pending_embeddings.copy(),
        )
        self._registered[face.user_id] = face
        logger.info(f"Face registered: {face.name} ({len(face.embeddings)} samples)")
        self._pending_name = ""
        self._pending_embeddings = []
        return True

    def cancel_registration(self):
        self._pending_name = ""
        self._pending_embeddings = []

    def get_registered_faces(self) -> Dict[str, Dict[str, Any]]:
        return {
            uid: {
                "name": f.name,
                "user_id": f.user_id,
                "samples": len(f.embeddings),
                "registered_at": f.registered_at,
                "last_seen": f.last_seen,
                "access_count": f.access_count,
            }
            for uid, f in self._registered.items()
        }

    def get_known_embeddings(self) -> Dict[str, List[float]]:
        """Get embeddings dict for recognition."""
        return {
            f.name: f.embeddings[0]
            for f in self._registered.values()
            if f.embeddings
        }

    def remove_face(self, user_id: str):
        self._registered.pop(user_id, None)

    @property
    def is_registering(self) -> bool:
        return bool(self._pending_name)

    @property
    def sample_count(self) -> int:
        return len(self._pending_embeddings)


class OCREngine:
    """OCR using EasyOCR."""

    def __init__(self, languages: Optional[List[str]] = None):
        self.languages = languages or ["en"]
        self._reader = None
        self._total_ocr_calls = 0

    async def initialize(self) -> bool:
        try:
            import easyocr
            self._reader = easyocr.Reader(self.languages)
            logger.info(f"OCR engine initialized: {self.languages}")
            return True
        except ImportError:
            logger.warning("easyocr not installed, OCR unavailable")
            return False
        except Exception as e:
            logger.error(f"OCR init error: {e}")
            return False

    async def recognize_text(self, frame) -> str:
        if not self._reader or frame is None:
            return "[OCR not available]"
        try:
            import numpy as np
            results = self._reader.readtext(np.array(frame))
            self._total_ocr_calls += 1
            return " ".join(text for _, text, _ in results)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "[OCR failed]"

    async def recognize_regions(self, frame) -> List[Dict[str, Any]]:
        """Get OCR results with bounding boxes and confidence."""
        if not self._reader or frame is None:
            return []
        try:
            import numpy as np
            results = self._reader.readtext(np.array(frame))
            self._total_ocr_calls += 1
            return [
                {
                    "bbox": [int(x) for x in box],
                    "text": text,
                    "confidence": float(conf),
                }
                for box, text, conf in results
            ]
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        return {
            "available": self._reader is not None,
            "languages": self.languages,
            "total_ocr_calls": self._total_ocr_calls,
        }


class VisionManager:
    """Manages the complete vision pipeline."""

    def __init__(
        self,
        camera_device: int = 0,
        face_threshold: float = 0.6,
        camera_width: int = 640,
        camera_height: int = 480,
    ):
        self.state = VisionState.IDLE
        self.camera = CameraManager(
            device_index=camera_device,
            width=camera_width,
            height=camera_height,
        )
        self.face_engine = FaceRecognitionEngine(threshold=face_threshold)
        self.face_registration = FaceRegistration(self.face_engine)
        self.ocr_engine = OCREngine()
        self._known_faces: Dict[str, str] = {}
        self._initialized = False
        self._frame_callbacks: List[Callable] = []

    async def initialize(self) -> bool:
        cam_ok = await self.camera.initialize()
        face_ok = await self.face_engine.initialize()
        ocr_ok = await self.ocr_engine.initialize()
        self._initialized = True
        logger.info(f"Vision initialized: camera={'OK' if cam_ok else 'FAIL'}, "
                    f"face={'OK' if face_ok else 'FAIL'}, ocr={'OK' if ocr_ok else 'FAIL'}")
        return self._initialized

    def register_face(self, name: str, encoding: str):
        self._known_faces[name] = encoding

    def on_frame(self, callback: Callable):
        self._frame_callbacks.append(callback)

    async def process_frame(self, frame) -> FrameResult:
        """Process a single frame through the full pipeline."""
        result = FrameResult()

        known = self.face_registration.get_known_embeddings()
        known.update(self._known_faces)
        if known:
            result.faces = await self.face_engine.recognize(frame, known)

        result.ocr_text = await self.ocr_engine.recognize_text(frame)
        result.processed = True

        for cb in self._frame_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(result)
                else:
                    cb(result)
            except Exception as e:
                logger.error(f"Frame callback error: {e}")

        return result

    async def capture_and_recognize(self) -> FrameResult:
        """Capture a frame and run full recognition."""
        self.state = VisionState.RECOGNIZING
        frame = await self.camera.capture()
        if frame is None:
            self.state = VisionState.IDLE
            return FrameResult()

        result = await self.process_frame(frame)
        self.state = VisionState.IDLE
        return result

    async def register_user_face(self, name: str, user_id: str = "") -> bool:
        """Capture multiple frames to register a face."""
        self.state = VisionState.REGISTERING
        await self.face_registration.start_registration(name, user_id)

        samples_needed = 5
        for i in range(samples_needed + 2):
            frame = await self.camera.capture()
            if frame is not None:
                await self.face_registration.add_sample(frame)
            await asyncio.sleep(0.3)

        success = await self.face_registration.complete_registration(user_id)
        self.state = VisionState.IDLE
        return success

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "initialized": self._initialized,
            "camera": self.camera.get_status(),
            "face_engine": self.face_engine.get_status(),
            "ocr": self.ocr_engine.get_status(),
            "registered_faces": self.face_registration.get_registered_faces(),
            "known_faces": len(self._known_faces),
        }


_vision_manager: Optional[VisionManager] = None


def get_vision_manager() -> VisionManager:
    global _vision_manager
    if _vision_manager is None:
        from core.config import settings
        _vision_manager = VisionManager(
            camera_device=settings.camera_device_index,
            face_threshold=settings.face_recognition_threshold,
        )
    return _vision_manager
