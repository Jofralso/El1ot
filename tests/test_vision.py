"""
Tests for Vision System.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from vision.system import (
    VisionManager,
    VisionState,
    CameraManager,
    FaceRecognitionEngine,
    FaceRegistration,
    OCREngine,
    FaceIdentity,
    RegisteredFace,
    FrameResult,
)


class TestVisionState:
    def test_states(self):
        assert VisionState.IDLE.value == "idle"
        assert VisionState.CAPTURING.value == "capturing"
        assert VisionState.RECOGNIZING.value == "recognizing"
        assert VisionState.REGISTERING.value == "registering"


class TestFaceIdentity:
    def test_defaults(self):
        fi = FaceIdentity(name="test", confidence=0.9)
        assert fi.name == "test"
        assert fi.confidence == 0.9
        assert fi.bounding_box == []
        assert fi.timestamp > 0


class TestRegisteredFace:
    def test_defaults(self):
        rf = RegisteredFace(name="Alice", user_id="alice")
        assert rf.name == "Alice"
        assert rf.embeddings == []
        assert rf.access_count == 0


class TestCameraManager:
    def test_init(self):
        cam = CameraManager(device_index=1, width=800, height=600, fps=15)
        assert cam.device_index == 1
        assert cam.width == 800
        assert cam.height == 600
        assert cam.fps == 15

    @pytest.mark.asyncio
    async def test_capture_no_device(self):
        cam = CameraManager()
        result = await cam.capture()
        assert result is None

    def test_release(self):
        cam = CameraManager()
        cam.release()
        assert cam._cap is None

    def test_status(self):
        cam = CameraManager(device_index=2)
        status = cam.get_status()
        assert status["device_index"] == 2
        assert status["active"] is False
        assert "frame_count" in status

    def test_frame_info(self):
        cam = CameraManager(width=1024, height=768)
        info = cam.get_frame_info()
        assert info["width"] == 1024
        assert info["height"] == 768


class TestFaceRecognitionEngine:
    def test_init(self):
        engine = FaceRecognitionEngine(threshold=0.7)
        assert engine.threshold == 0.7

    @pytest.mark.asyncio
    async def test_detect_faces_no_model(self):
        engine = FaceRecognitionEngine()
        result = await engine.detect_faces(None)
        assert result == []

    @pytest.mark.asyncio
    async def test_recognize_no_model(self):
        engine = FaceRecognitionEngine()
        result = await engine.recognize(None, {})
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_encoding_no_model(self):
        engine = FaceRecognitionEngine()
        result = await engine.extract_encoding(None)
        assert result is None

    def test_status(self):
        engine = FaceRecognitionEngine()
        status = engine.get_status()
        assert status["available"] is False
        assert status["threshold"] == 0.6
        assert status["total_recognitions"] == 0


class TestFaceRegistration:
    def test_init(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        assert reg.is_registering is False
        assert reg.sample_count == 0

    @pytest.mark.asyncio
    async def test_start_registration(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        await reg.start_registration("Alice", "alice_01")
        assert reg.is_registering is True

    @pytest.mark.asyncio
    async def test_complete_registration_insufficient_samples(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        await reg.start_registration("Alice")
        result = await reg.complete_registration()
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_registration_success(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        await reg.start_registration("Alice")
        reg._pending_embeddings = [[0.1] * 128, [0.2] * 128, [0.3] * 128]
        result = await reg.complete_registration("alice_01")
        assert result is True
        assert reg.is_registering is False

    def test_cancel(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        reg._pending_name = "test"
        reg._pending_embeddings = [[0.1]]
        reg.cancel_registration()
        assert reg.is_registering is False

    def test_get_registered_faces(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        reg._registered["alice"] = RegisteredFace(name="Alice", user_id="alice")
        faces = reg.get_registered_faces()
        assert "alice" in faces
        assert faces["alice"]["name"] == "Alice"

    def test_get_known_embeddings(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        reg._registered["alice"] = RegisteredFace(
            name="Alice", user_id="alice", embeddings=[[0.5] * 128]
        )
        embeddings = reg.get_known_embeddings()
        assert "Alice" in embeddings

    def test_remove_face(self):
        engine = FaceRecognitionEngine()
        reg = FaceRegistration(engine)
        reg._registered["alice"] = RegisteredFace(name="Alice", user_id="alice")
        reg.remove_face("alice")
        assert "alice" not in reg._registered


class TestOCREngine:
    def test_init(self):
        ocr = OCREngine(languages=["en", "es"])
        assert ocr.languages == ["en", "es"]

    @pytest.mark.asyncio
    async def test_recognize_no_model(self):
        ocr = OCREngine()
        result = await ocr.recognize_text(None)
        assert result == "[OCR not available]"

    @pytest.mark.asyncio
    async def test_recognize_regions_no_model(self):
        ocr = OCREngine()
        result = await ocr.recognize_regions(None)
        assert result == []

    def test_status(self):
        ocr = OCREngine()
        status = ocr.get_status()
        assert status["available"] is False
        assert status["languages"] == ["en"]


class TestFrameResult:
    def test_defaults(self):
        fr = FrameResult()
        assert fr.faces == []
        assert fr.ocr_text == ""
        assert fr.processed is False
        assert fr.timestamp > 0


class TestVisionManager:
    def test_init(self):
        vm = VisionManager(camera_device=1, face_threshold=0.8)
        assert vm.camera.device_index == 1
        assert vm.face_engine.threshold == 0.8
        assert vm.state == VisionState.IDLE

    @pytest.mark.asyncio
    async def test_initialize(self):
        vm = VisionManager()
        result = await vm.initialize()
        assert vm._initialized is True

    def test_register_face(self):
        vm = VisionManager()
        vm.register_face("Alice", "embedding_data")
        assert "Alice" in vm._known_faces

    @pytest.mark.asyncio
    async def test_process_frame_no_faces(self):
        vm = VisionManager()
        await vm.initialize()
        try:
            import numpy as np
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            result = await vm.process_frame(frame)
            assert isinstance(result, FrameResult)
            assert result.processed is True
        except ImportError:
            pytest.skip("numpy not installed")

    @pytest.mark.asyncio
    async def test_capture_and_recognize_no_camera(self):
        vm = VisionManager()
        await vm.initialize()
        result = await vm.capture_and_recognize()
        assert isinstance(result, FrameResult)

    def test_status(self):
        vm = VisionManager()
        status = vm.get_status()
        assert "state" in status
        assert "camera" in status
        assert "face_engine" in status
        assert "ocr" in status
        assert "registered_faces" in status

    def test_on_frame_callback(self):
        vm = VisionManager()
        called = []
        def cb(result):
            called.append(result)
        vm.on_frame(cb)
        assert len(called) == 0
