"""
Voice Agent

Handles speech interaction, wake word events, STT/TTS coordination.
"""

import logging
from typing import Any, Dict, Optional

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class VoiceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role=AgentRole.VOICE,
            name="Voice",
            description="Handles voice interaction, speech-to-text, and text-to-speech",
            permissions=["read", "voice"],
            tools=["stt", "tts", "wake_word"],
        )
        self._stt_engine = None
        self._tts_engine = None
        self._wake_word = None

    def set_stt(self, engine):
        self._stt_engine = engine

    def set_tts(self, engine):
        self._tts_engine = engine

    def set_wake_word(self, engine):
        self._wake_word = engine

    async def process(self, message: AgentMessage) -> AgentMessage:
        msg_type = message.metadata.get("voice_type", "text")

        if msg_type == "transcribe":
            text = await self._transcribe(message.metadata.get("audio_data", b""))
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=text,
                message_type="voice_response",
                metadata={"original_type": "transcription"},
            )
        elif msg_type == "speak":
            audio = await self._synthesize(message.content)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content="Speech synthesized",
                message_type="voice_audio",
                metadata={"audio_data": audio},
            )
        else:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"Voice processing: {message.content}",
                message_type="text",
                metadata={"voice_status": "processed"},
            )

    async def _transcribe(self, audio_data: bytes) -> str:
        if self._stt_engine:
            return await self._stt_engine.transcribe(audio_data)
        return "[Voice transcription not available - STT engine not initialized]"

    async def _synthesize(self, text: str) -> bytes:
        if self._tts_engine:
            return await self._tts_engine.synthesize(text)
        return b""
