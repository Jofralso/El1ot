"""
ELIOT Voice System

Fully offline voice pipeline:
- Wake word detection (OpenWakeWord)
- Speech-to-text (Whisper.cpp or faster-whisper)
- Text-to-speech (Piper)
- Audio capture/playback management
- Conversation manager
- WebSocket audio streaming
"""

import asyncio
import logging
import time
import struct
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class VoiceMessage:
    role: str = "system"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    audio_data: Optional[bytes] = None


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 3000
    format: str = "pcm_s16le"


class WakeWordDetector:
    """Wake word detection using OpenWakeWord."""

    def __init__(self, wake_word: str = "eliot", threshold: float = 0.5):
        self.wake_word = wake_word
        self.threshold = threshold
        self._model = None
        self._active = False
        self._detection_count = 0
        self._last_detection = 0.0

    async def start(self):
        try:
            import openwakeword
            self._model = openwakeword.Model(wakeword_models=[self.wake_word])
            self._active = True
            logger.info(f"Wake word detector started: '{self.wake_word}'")
        except ImportError:
            logger.warning("openwakeword not installed, wake word detection disabled")
            self._active = False
        except Exception as e:
            logger.error(f"Failed to start wake word detector: {e}")
            self._active = False

    async def stop(self):
        self._active = False
        self._model = None

    async def detect(self, audio_chunk: bytes) -> bool:
        if not self._model or not self._active:
            return False
        try:
            prediction = self._model.predict(audio_chunk)
            for name, score in prediction.items():
                if name == self.wake_word and score > self.threshold:
                    self._detection_count += 1
                    self._last_detection = time.time()
                    logger.info(f"Wake word detected (score={score:.3f})")
                    return True
        except Exception as e:
            logger.debug(f"Wake word detection error: {e}")
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "wake_word": self.wake_word,
            "active": self._active,
            "threshold": self.threshold,
            "detection_count": self._detection_count,
            "last_detection": self._last_detection,
        }


class SpeechToText:
    """Offline speech-to-text using faster-whisper."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None
        self._total_transcriptions = 0

    async def initialize(self):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            logger.info(f"Whisper STT initialized: {self.model_name}")
        except ImportError:
            logger.warning("faster-whisper not installed, STT disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")

    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        if not self._model:
            return "[STT not available]"
        try:
            segments, info = self._model.transcribe(audio_data, language=language)
            text = " ".join(seg.text for seg in segments)
            self._total_transcriptions += 1
            logger.debug(f"Transcribed ({info.language}, {info.duration:.1f}s): {text[:80]}...")
            return text.strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return "[Transcription failed]"

    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes], language: str = "en") -> str:
        """Transcribe from an async audio stream by collecting chunks."""
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)
        if not chunks:
            return ""
        audio_data = b"".join(chunks)
        return await self.transcribe(audio_data, language)

    def get_status(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "available": self._model is not None,
            "total_transcriptions": self._total_transcriptions,
        }


class TextToSpeech:
    """Offline text-to-speech using Piper."""

    def __init__(self, voice: str = "en_US-lessac-medium"):
        self.voice = voice
        self._model = None
        self._total_synthesized = 0
        self._total_duration = 0.0

    async def initialize(self):
        try:
            import piper
            self._model = piper.PiperVoice.load(self.voice)
            logger.info(f"Piper TTS initialized: {self.voice}")
        except ImportError:
            logger.warning("piper not installed, TTS disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Piper: {e}")

    async def synthesize(self, text: str) -> bytes:
        if not self._model:
            return b""
        try:
            import io
            audio_buffer = io.BytesIO()
            self._model.synthesize(text, audio_buffer)
            audio_bytes = audio_buffer.getvalue()
            self._total_synthesized += 1
            self._total_duration += len(audio_bytes) / (16000 * 2)
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""

    async def synthesize_chunks(self, text: str, chunk_size: int = 200) -> AsyncIterator[bytes]:
        """Synthesize text in chunks for streaming playback."""
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            audio = await self.synthesize(chunk_text)
            if audio:
                yield audio

    def get_status(self) -> Dict[str, Any]:
        return {
            "voice": self.voice,
            "available": self._model is not None,
            "total_synthesized": self._total_synthesized,
            "total_audio_duration_s": round(self._total_duration, 1),
        }


class AudioCapture:
    """Manages microphone input capture."""

    def __init__(self, device_index: int = 0, config: Optional[AudioConfig] = None):
        self.device_index = device_index
        self.config = config or AudioConfig()
        self._stream = None
        self._capturing = False
        self._total_captured = 0

    async def start(self) -> bool:
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=int(self.config.sample_rate * self.config.chunk_duration_ms / 1000),
            )
            self._capturing = True
            logger.info(f"Audio capture started: device={self.device_index}, rate={self.config.sample_rate}")
            return True
        except ImportError:
            logger.warning("pyaudio not installed")
            return False
        except Exception as e:
            logger.error(f"Audio capture start error: {e}")
            return False

    async def stop(self):
        self._capturing = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    async def read_chunk(self) -> Optional[bytes]:
        if not self._stream or not self._capturing:
            return None
        try:
            chunk_size = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000)
            data = self._stream.read(chunk_size, exception_on_overflow=False)
            self._total_captured += len(data)
            return data
        except Exception as e:
            logger.error(f"Audio read error: {e}")
            return None

    async def audio_stream(self) -> AsyncIterator[bytes]:
        """Async generator yielding audio chunks."""
        while self._capturing:
            chunk = await self.read_chunk()
            if chunk:
                yield chunk
            await asyncio.sleep(0.01)

    def get_status(self) -> Dict[str, Any]:
        return {
            "device_index": self.device_index,
            "capturing": self._capturing,
            "sample_rate": self.config.sample_rate,
            "total_bytes_captured": self._total_captured,
        }


class AudioPlayback:
    """Manages speaker output playback."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._stream = None
        self._playing = False

    async def play(self, audio_data: bytes) -> bool:
        if not audio_data:
            return False
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                output=True,
                output_device_index=self.device_index,
            )
            self._playing = True
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            self._playing = False
            return True
        except ImportError:
            logger.warning("pyaudio not installed")
            return False
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self._playing = False
            return False

    async def play_stream(self, audio_chunks: AsyncIterator[bytes]) -> bool:
        """Play from an async audio stream."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                output=True,
                output_device_index=self.device_index,
            )
            self._playing = True
            async for chunk in audio_chunks:
                stream.write(chunk)
            stream.stop_stream()
            stream.close()
            self._playing = False
            return True
        except ImportError:
            logger.warning("pyaudio not installed")
            return False
        except Exception as e:
            logger.error(f"Stream playback error: {e}")
            self._playing = False
            return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "device_index": self.device_index,
            "playing": self._playing,
        }


class ConversationManager:
    """Manages voice conversation history and context."""

    def __init__(self, max_history: int = 50):
        self._history: List[VoiceMessage] = []
        self._max_history = max_history
        self._conversation_start = time.time()

    def add_user_message(self, content: str, audio_data: Optional[bytes] = None):
        msg = VoiceMessage(role="user", content=content, audio_data=audio_data)
        self._history.append(msg)
        self._trim()

    def add_assistant_message(self, content: str, audio_data: Optional[bytes] = None):
        msg = VoiceMessage(role="assistant", content=content, audio_data=audio_data)
        self._history.append(msg)
        self._trim()

    def get_context(self, n: int = 10) -> List[Dict[str, str]]:
        recent = self._history[-n:]
        return [{"role": m.role, "content": m.content} for m in recent]

    def get_full_history(self) -> List[Dict[str, Any]]:
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in self._history
        ]

    def clear(self):
        self._history.clear()
        self._conversation_start = time.time()

    def _trim(self):
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_status(self) -> Dict[str, Any]:
        return {
            "messages": len(self._history),
            "duration_s": round(time.time() - self._conversation_start, 1),
        }


class VoiceManager:
    """Manages the complete voice pipeline."""

    def __init__(
        self,
        wake_word: str = "eliot",
        stt_model: str = "base",
        tts_voice: str = "en_US-lessac-medium",
        mic_device: int = 0,
        speaker_device: int = 0,
    ):
        self.state = VoiceState.IDLE
        self.wake_detector = WakeWordDetector(wake_word=wake_word)
        self.stt = SpeechToText(model_name=stt_model)
        self.tts = TextToSpeech(voice=tts_voice)
        self.capture = AudioCapture(device_index=mic_device)
        self.playback = AudioPlayback(device_index=speaker_device)
        self.conversation = ConversationManager()
        self._initialized = False
        self._callbacks: List[Callable] = []

    async def initialize(self):
        await self.wake_detector.start()
        await self.stt.initialize()
        await self.tts.initialize()
        self._initialized = True
        logger.info("Voice system initialized")

    async def shutdown(self):
        await self.wake_detector.stop()
        await self.capture.stop()
        self._initialized = False
        logger.info("Voice system shut down")

    def on_wake_word(self, callback: Callable):
        self._callbacks.append(callback)

    async def listen_for_wake_word(self) -> bool:
        """Listen continuously until wake word is detected."""
        if not self.capture._capturing:
            await self.capture.start()

        self.state = VoiceState.LISTENING
        async for chunk in self.capture.audio_stream():
            if await self.wake_detector.detect(chunk):
                for cb in self._callbacks:
                    try:
                        await cb() if asyncio.iscoroutinefunction(cb) else cb()
                    except Exception as e:
                        logger.error(f"Wake word callback error: {e}")
                return True
        return False

    async def listen_and_transcribe(self, duration_seconds: float = 5.0) -> str:
        """Listen for a fixed duration and transcribe."""
        self.state = VoiceState.LISTENING
        chunks = []
        start = time.time()

        if not self.capture._capturing:
            await self.capture.start()

        while time.time() - start < duration_seconds:
            chunk = await self.capture.read_chunk()
            if chunk:
                chunks.append(chunk)
            await asyncio.sleep(0.01)

        self.state = VoiceState.PROCESSING
        audio_data = b"".join(chunks)
        text = await self.stt.transcribe(audio_data)

        if text and text != "[STT not available]":
            self.conversation.add_user_message(text, audio_data)

        self.state = VoiceState.IDLE
        return text

    async def speak(self, text: str) -> bool:
        """Synthesize and play text."""
        self.state = VoiceState.SPEAKING
        audio = await self.tts.synthesize(text)
        if audio:
            self.conversation.add_assistant_message(text, audio)
            result = await self.playback.play(audio)
            self.state = VoiceState.IDLE
            return result
        self.state = VoiceState.IDLE
        return False

    async def converse(self, user_input: str) -> str:
        """Process user input and return response (for integration with agent system)."""
        self.conversation.add_user_message(user_input)
        return user_input

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "initialized": self._initialized,
            "wake_word": self.wake_detector.get_status(),
            "stt": self.stt.get_status(),
            "tts": self.tts.get_status(),
            "capture": self.capture.get_status(),
            "playback": self.playback.get_status(),
            "conversation": self.conversation.get_status(),
        }


_voice_manager: Optional[VoiceManager] = None


def get_voice_manager() -> VoiceManager:
    global _voice_manager
    if _voice_manager is None:
        from core.config import settings
        _voice_manager = VoiceManager(
            wake_word=settings.wake_word,
            stt_model=settings.whisper_model,
            tts_voice=settings.tts_voice,
            mic_device=settings.mic_device_index,
            speaker_device=settings.speaker_device_index,
        )
    return _voice_manager
