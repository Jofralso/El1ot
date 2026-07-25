"""
Vision Agent

Handles camera input, face recognition, OCR, and visual analysis.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role=AgentRole.VISION,
            name="Vision",
            description="Handles camera processing, face recognition, and OCR",
            permissions=["read", "vision", "face_recognition"],
            tools=["camera", "face_detector", "ocr"],
        )
        self._camera = None
        self._face_engine = None
        self._ocr_engine = None
        self._known_faces: Dict[str, str] = {}

    def set_camera(self, camera):
        self._camera = camera

    def set_face_engine(self, engine):
        self._face_engine = engine

    def set_ocr_engine(self, engine):
        self._ocr_engine = engine

    def register_face(self, name: str, embedding: List[float]):
        self._known_faces[name] = embedding

    async def process(self, message: AgentMessage) -> AgentMessage:
        msg_type = message.metadata.get("vision_type", "analyze")

        if msg_type == "capture":
            frame = await self._capture_frame()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content="Frame captured",
                message_type="vision_frame",
                metadata={"frame": frame},
            )
        elif msg_type == "recognize":
            result = await self._recognize_face(message.metadata.get("frame"))
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"Recognition result: {result}",
                message_type="vision_result",
                metadata={"recognition": result},
            )
        elif msg_type == "ocr":
            text = await self._read_text(message.metadata.get("frame"))
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=text,
                message_type="vision_ocr",
                metadata={"ocr_text": text},
            )

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content="Vision processing available: capture, recognize, ocr",
            message_type="text",
        )

    async def _capture_frame(self):
        if self._camera:
            return await self._camera.capture()
        return None

    async def _recognize_face(self, frame=None) -> Dict[str, Any]:
        if self._face_engine and frame:
            return await self._face_engine.recognize(frame, self._known_faces)
        return {"status": "engine_not_ready", "identity": "unknown"}

    async def _read_text(self, frame=None) -> str:
        if self._ocr_engine and frame:
            return await self._ocr_engine.recognize_text(frame)
        return "[OCR engine not initialized]"
