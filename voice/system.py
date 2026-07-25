"""
ELIOT Voice System

Fully offline voice pipeline:
- Wake word detection (OpenWakeWord)
- Speech-to-text (Whisper.cpp or faster-whisper)
- Text-to-speech (Piper or edge-tts fallback)
- Voice conversation management
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class WakeWordDetector:
    """Wake word detection using OpenWakeWord."""

    def __init__(self, wake_word: str = "eliot"):
        self.wake_word = wake_word
        self._model = None
        self._active = False

    async def start(self):
        try:
            import openwakeword
            self._model = openwakeword.Model(wakeword_models=[self.wake_word])
            self._active = True
            logger.info(f"Wake word detector started: '{self.wake_word}'")
        except ImportError:
            logger.warning("openwakeword not installed, wake word detection disabled")
        except Exception as e:
            logger.error(f"Failed to start wake word detector: {e}")

    async def stop(self):
        self._active = False
        self._model = None

    async def detect(self, audio_chunk: bytes) -> bool:
        if not self._model or not self._active:
            return False
        try:
            prediction = self._model.predict(audio_chunk)
            for name, score in prediction.items():
                if name == self.wake_word and score > 0.5:
                    return True
        except Exception:
            pass
        return False


class SpeechToText:
    """Offline speech-to-text using Whisper."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None

    async def initialize(self):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            logger.info(f"Whisper STT initialized: {self.model_name}")
        except ImportError:
            logger.warning("faster-whisper not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")

    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        if not self._model:
            return "[STT not available]"
        try:
            segments, info = self._model.transcribe(audio_data, language=language)
            text = " ".join(seg.text for seg in segments)
            return text.strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return "[Transcription failed]"


class TextToSpeech:
    """Offline text-to-speech using Piper."""

    def __init__(self, voice: str = "en_US-lessac-medium"):
        self.voice = voice
        self._model = None

    async def initialize(self):
        try:
            import piper
            self._model = piper.PiperVoice.load(self.voice)
            logger.info(f"Piper TTS initialized: {self.voice}")
        except ImportError:
            logger.warning("piper not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Piper: {e}")

    async def synthesize(self, text: str) -> bytes:
        if not self._model:
            return b""
        try:
            import io
            audio_buffer = io.BytesIO()
            self._model.synthesize(text, audio_buffer)
            return audio_buffer.getvalue()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""


class VoiceManager:
    """Manages the complete voice pipeline."""

    def __init__(self):
        self.state = VoiceState.IDLE
        self.wake_detector = WakeWordDetector()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self._initialized = False

    async def initialize(self):
        await self.wake_detector.start()
        await self.stt.initialize()
        await self.tts.initialize()
        self._initialized = True
        logger.info("Voice system initialized")

    async def shutdown(self):
        await self.wake_detector.stop()
        self._initialized = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "initialized": self._initialized,
            "wake_word": self.wake_detector.wake_word,
            "stt_model": self.stt.model_name,
            "tts_voice": self.tts.voice,
        }


_voice_manager: Optional[VoiceManager] = None


def get_voice_manager() -> VoiceManager:
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager
