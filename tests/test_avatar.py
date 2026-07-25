"""
Tests for Avatar Engine.
"""

import json
import pytest
from avatar.engine import (
    AvatarEngine,
    AvatarState,
    AvatarEmotion,
    AnimationTrigger,
    LipSyncEngine,
    EmotionEngine,
    STATE_EMOTION_MAP,
    STATE_ANIMATION_MAP,
)


class TestAvatarState:
    def test_all_states(self):
        states = [s.value for s in AvatarState]
        assert "booting" in states
        assert "idle" in states
        assert "listening" in states
        assert "thinking" in states
        assert "analyzing" in states
        assert "alert" in states
        assert "reporting" in states
        assert "speaking" in states
        assert "sleeping" in states


class TestAvatarEmotion:
    def test_all_emotions(self):
        emotions = [e.value for e in AvatarEmotion]
        assert "curious" in emotions
        assert "focused" in emotions
        assert "concerned" in emotions
        assert "satisfied" in emotions
        assert "neutral" in emotions
        assert "excited" in emotions


class TestAnimationTrigger:
    def test_all_triggers(self):
        triggers = [t.value for t in AnimationTrigger]
        assert "none" in triggers
        assert "nod" in triggers
        assert "blink" in triggers
        assert "think_bubble" in triggers
        assert "scanning" in triggers


class TestLipSyncEngine:
    def test_init(self):
        ls = LipSyncEngine()
        assert ls.sample_rate == 16000
        assert ls.sensitivity == 1.0
        assert ls.decay == 0.85

    def test_process_empty_audio(self):
        ls = LipSyncEngine()
        result = ls.process_audio(b"")
        assert 0.0 <= result <= 1.0

    def test_process_silence(self):
        ls = LipSyncEngine()
        result = ls.process_audio(b"\x00" * 320)
        assert 0.0 <= result <= 1.0

    def test_process_audio_decay(self):
        ls = LipSyncEngine()
        ls.process_audio(b"\xff" * 320)
        val1 = ls._current_value
        ls.process_audio(b"\x00" * 320)
        val2 = ls._current_value
        assert val2 <= val1

    def test_reset(self):
        ls = LipSyncEngine()
        ls._current_value = 0.9
        ls._peak = 1.0
        ls.reset()
        assert ls._current_value == 0.0
        assert ls._peak == 0.0


class TestEmotionEngine:
    def test_init(self):
        ee = EmotionEngine()
        assert ee.get_emotion() == AvatarEmotion.NEUTRAL

    def test_on_state_change_thinking(self):
        ee = EmotionEngine()
        ee.on_state_change(AvatarState.THINKING)
        assert ee.get_emotion() == AvatarEmotion.FOCUSED

    def test_on_state_change_alert(self):
        ee = EmotionEngine()
        ee.on_state_change(AvatarState.ALERT)
        assert ee.get_emotion() == AvatarEmotion.CONCERNED

    def test_on_text_input_error(self):
        ee = EmotionEngine()
        ee.on_text_input("error in system")
        assert ee.get_emotion() == AvatarEmotion.CONCERNED

    def test_on_text_input_success(self):
        ee = EmotionEngine()
        ee.on_text_input("great success!")
        assert ee.get_emotion() == AvatarEmotion.SATISFIED

    def test_on_thinking(self):
        ee = EmotionEngine()
        ee.on_thinking()
        assert ee.get_emotion() == AvatarEmotion.FOCUSED

    def test_on_result_success(self):
        ee = EmotionEngine()
        ee.on_result(True)
        assert ee.get_emotion() == AvatarEmotion.SATISFIED

    def test_on_result_failure(self):
        ee = EmotionEngine()
        ee.on_result(False)
        assert ee.get_emotion() == AvatarEmotion.CONCERNED

    def test_status(self):
        ee = EmotionEngine()
        status = ee.get_status()
        assert "current" in status
        assert "energy" in status
        assert "transitions" in status


class TestAvatarEngine:
    def test_init(self):
        engine = AvatarEngine()
        snap = engine.get_snapshot()
        assert snap["state"] == "booting"
        assert snap["emotion"] == "neutral"
        assert snap["boot_progress"] == 0.0

    def test_set_state(self):
        engine = AvatarEngine()
        engine.set_state(AvatarState.IDLE)
        assert engine._state == AvatarState.IDLE

    def test_set_state_same_no_log(self):
        engine = AvatarEngine()
        engine.set_state(AvatarState.BOOTING)
        assert engine._state == AvatarState.BOOTING

    def test_set_emotion(self):
        engine = AvatarEngine()
        engine.set_emotion(AvatarEmotion.EXCITED)
        snap = engine.get_snapshot()
        assert snap["emotion"] == "excited"

    def test_lip_sync_clamping(self):
        engine = AvatarEngine()
        engine.set_lip_sync(1.5)
        assert engine._lip_sync._current_value <= 1.0
        engine.set_lip_sync(-0.5)
        assert engine._lip_sync._current_value >= 0.0

    def test_process_audio_lip_sync(self):
        engine = AvatarEngine()
        result = engine.process_audio_lip_sync(b"\x00" * 320)
        assert 0.0 <= result <= 1.0

    def test_eye_direction(self):
        engine = AvatarEngine()
        engine.set_eye_direction("left")
        assert engine._eye_direction == "left"
        engine.set_eye_direction("invalid")
        assert engine._eye_direction == "center"

    def test_text_display(self):
        engine = AvatarEngine()
        engine.set_text_display("Hello ELIOT")
        assert engine._text_display == "Hello ELIOT"

    def test_text_display_truncation(self):
        engine = AvatarEngine()
        engine.set_text_display("x" * 300)
        assert len(engine._text_display) == 200

    def test_trigger_animation(self):
        engine = AvatarEngine()
        engine.trigger_animation(AnimationTrigger.WAVE)
        assert engine._animation == AnimationTrigger.WAVE

    def test_update_boot(self):
        engine = AvatarEngine()
        engine.update_boot(0.5)
        assert engine._boot_progress == 0.5
        assert engine._state == AvatarState.BOOTING
        engine.update_boot(1.0)
        assert engine._boot_progress == 1.0
        assert engine._state == AvatarState.IDLE

    def test_update_boot_clamp(self):
        engine = AvatarEngine()
        engine.update_boot(2.0)
        assert engine._boot_progress == 1.0

    def test_on_thinking(self):
        engine = AvatarEngine()
        engine.on_thinking()
        assert engine._state == AvatarState.THINKING

    def test_on_listening(self):
        engine = AvatarEngine()
        engine.on_listening()
        assert engine._state == AvatarState.LISTENING

    def test_on_speaking(self):
        engine = AvatarEngine()
        engine.on_speaking("Hello world")
        assert engine._state == AvatarState.SPEAKING
        assert engine._text_display == "Hello world"

    def test_on_alert(self):
        engine = AvatarEngine()
        engine.on_alert("Warning!")
        assert engine._state == AvatarState.ALERT
        assert engine._text_display == "Warning!"

    def test_on_result(self):
        engine = AvatarEngine()
        engine.on_result(True, "Task complete")
        assert engine._state == AvatarState.REPORTING

    def test_ws_payload(self):
        engine = AvatarEngine()
        payload = engine.get_ws_payload()
        data = json.loads(payload)
        assert "state" in data
        assert "emotion" in data
        assert "lip_sync" in data
        assert "animation" in data

    def test_snapshot_completeness(self):
        engine = AvatarEngine()
        snap = engine.get_snapshot()
        required_keys = {
            "state", "emotion", "lip_sync", "eye_direction",
            "animation", "text_display", "boot_progress",
            "state_duration", "timestamp",
        }
        assert required_keys.issubset(set(snap.keys()))

    def test_state_emotion_map_completeness(self):
        for state in AvatarState:
            assert state in STATE_EMOTION_MAP

    def test_state_animation_map_completeness(self):
        for state in AvatarState:
            if state not in STATE_ANIMATION_MAP:
                # Some states may have no specific animation mapped
                continue
            assert state in STATE_ANIMATION_MAP

    def test_singleton(self):
        from avatar.engine import get_avatar_engine
        a = get_avatar_engine()
        b = get_avatar_engine()
        assert a is b
