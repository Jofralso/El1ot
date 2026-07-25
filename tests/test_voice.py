"""
Tests for Voice System.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from voice.system import (
    VoiceManager,
    VoiceState,
    WakeWordDetector,
    SpeechToText,
    TextToSpeech,
    AudioCapture,
    AudioPlayback,
    ConversationManager,
    AudioConfig,
)


class TestVoiceState:
    def test_voice_states(self):
        assert VoiceState.IDLE.value == "idle"
        assert VoiceState.LISTENING.value == "listening"
        assert VoiceState.PROCESSING.value == "processing"
        assert VoiceState.SPEAKING.value == "speaking"
        assert VoiceState.ERROR.value == "error"


class TestWakeWordDetector:
    def test_init(self):
        det = WakeWordDetector(wake_word="test", threshold=0.7)
        assert det.wake_word == "test"
        assert det.threshold == 0.7
        assert det._active is False

    @pytest.mark.asyncio
    async def test_detect_when_inactive(self):
        det = WakeWordDetector()
        result = await det.detect(b"\x00" * 100)
        assert result is False

    @pytest.mark.asyncio
    async def test_stop(self):
        det = WakeWordDetector()
        await det.stop()
        assert det._active is False

    def test_status(self):
        det = WakeWordDetector(wake_word="hello")
        status = det.get_status()
        assert status["wake_word"] == "hello"
        assert "detection_count" in status


class TestSpeechToText:
    def test_init(self):
        stt = SpeechToText(model_name="tiny")
        assert stt.model_name == "tiny"
        assert stt._model is None

    @pytest.mark.asyncio
    async def test_transcribe_no_model(self):
        stt = SpeechToText()
        result = await stt.transcribe(b"\x00" * 100)
        assert result == "[STT not available]"

    def test_status(self):
        stt = SpeechToText(model_name="base")
        status = stt.get_status()
        assert status["model"] == "base"
        assert status["available"] is False
        assert status["total_transcriptions"] == 0


class TestTextToSpeech:
    def test_init(self):
        tts = TextToSpeech(voice="test-voice")
        assert tts.voice == "test-voice"

    @pytest.mark.asyncio
    async def test_synthesize_no_model(self):
        tts = TextToSpeech()
        result = await tts.synthesize("hello world")
        assert result == b""

    def test_status(self):
        tts = TextToSpeech(voice="en_voice")
        status = tts.get_status()
        assert status["voice"] == "en_voice"
        assert status["available"] is False


class TestAudioConfig:
    def test_defaults(self):
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.chunk_duration_ms == 3000

    def test_custom(self):
        config = AudioConfig(sample_rate=44100, channels=2)
        assert config.sample_rate == 44100
        assert config.channels == 2


class TestAudioCapture:
    def test_init(self):
        cap = AudioCapture(device_index=1)
        assert cap.device_index == 1
        assert cap._capturing is False

    @pytest.mark.asyncio
    async def test_read_chunk_when_inactive(self):
        cap = AudioCapture()
        result = await cap.read_chunk()
        assert result is None

    @pytest.mark.asyncio
    async def test_stop(self):
        cap = AudioCapture()
        await cap.stop()
        assert cap._capturing is False

    def test_status(self):
        cap = AudioCapture(device_index=2)
        status = cap.get_status()
        assert status["device_index"] == 2
        assert status["capturing"] is False


class TestAudioPlayback:
    def test_init(self):
        pb = AudioPlayback(device_index=1)
        assert pb.device_index == 1
        assert pb._playing is False

    @pytest.mark.asyncio
    async def test_play_empty(self):
        pb = AudioPlayback()
        result = await pb.play(b"")
        assert result is False

    def test_status(self):
        pb = AudioPlayback()
        status = pb.get_status()
        assert "playing" in status


class TestConversationManager:
    def test_add_messages(self):
        conv = ConversationManager()
        conv.add_user_message("hello")
        conv.add_assistant_message("hi there")
        assert len(conv.get_full_history()) == 2

    def test_context(self):
        conv = ConversationManager()
        conv.add_user_message("what is CVE?")
        conv.add_assistant_message("Common Vulnerabilities and Exposures")
        ctx = conv.get_context(n=2)
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "assistant"

    def test_clear(self):
        conv = ConversationManager()
        conv.add_user_message("test")
        conv.clear()
        assert len(conv.get_full_history()) == 0

    def test_max_history(self):
        conv = ConversationManager(max_history=3)
        for i in range(5):
            conv.add_user_message(f"msg {i}")
        assert len(conv.get_full_history()) == 3
        history = conv.get_full_history()
        assert history[0]["content"] == "msg 2"

    def test_status(self):
        conv = ConversationManager()
        conv.add_user_message("test")
        status = conv.get_status()
        assert status["messages"] == 1
        assert "duration_s" in status


class TestVoiceManager:
    def test_init(self):
        vm = VoiceManager(wake_word="test", stt_model="tiny", tts_voice="voice")
        assert vm.wake_detector.wake_word == "test"
        assert vm.stt.model_name == "tiny"
        assert vm.tts.voice == "voice"
        assert vm.state == VoiceState.IDLE

    @pytest.mark.asyncio
    async def test_initialize(self):
        vm = VoiceManager()
        await vm.initialize()
        assert vm._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        vm = VoiceManager()
        await vm.initialize()
        await vm.shutdown()
        assert vm._initialized is False

    @pytest.mark.asyncio
    async def test_speak_no_tts(self):
        vm = VoiceManager()
        await vm.initialize()
        result = await vm.speak("hello")
        assert result is False

    def test_status(self):
        vm = VoiceManager()
        status = vm.get_status()
        assert "state" in status
        assert "wake_word" in status
        assert "stt" in status
        assert "tts" in status
        assert "conversation" in status

    @pytest.mark.asyncio
    async def test_converse(self):
        vm = VoiceManager()
        result = await vm.converse("test input")
        assert result == "test input"
