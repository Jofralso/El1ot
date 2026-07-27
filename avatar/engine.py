"""
ELIOT Avatar Engine

3D cyberpunk avatar with emotional states.
WebSocket server for Godot Engine integration.
Avatar states: BOOTING, IDLE, LISTENING, THINKING, ANALYZING, ALERT, REPORTING
Emotions: curious, focused, concerned, satisfied, sleeping

Features:
- Real-time state synchronization via WebSocket
- Lip sync calculation from audio amplitude
- Emotion auto-detection from agent activity
- Animation trigger system
- Multi-client support (Godot + web UI)
"""

import asyncio
import json
import logging
import math
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AvatarState(str, Enum):
    BOOTING = "booting"
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ANALYZING = "analyzing"
    ALERT = "alert"
    REPORTING = "reporting"
    SPEAKING = "speaking"
    SLEEPING = "sleeping"


class AvatarEmotion(str, Enum):
    CURIOUS = "curious"
    FOCUSED = "focused"
    CONCERNED = "concerned"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    EXCITED = "excited"


class AnimationTrigger(str, Enum):
    NONE = "none"
    NOD = "nod"
    SHAKE_HEAD = "shake_head"
    BLINK = "blink"
    LOOK_LEFT = "look_left"
    LOOK_RIGHT = "look_right"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"
    WAVE = "wave"
    THINK_BUBBLE = "think_bubble"
    EXCLAMATION = "exclamation"
    SCANNING = "scanning"


# State -> Emotion mapping for auto-detection
STATE_EMOTION_MAP = {
    AvatarState.BOOTING: AvatarEmotion.CURIOUS,
    AvatarState.IDLE: AvatarEmotion.NEUTRAL,
    AvatarState.LISTENING: AvatarEmotion.CURIOUS,
    AvatarState.THINKING: AvatarEmotion.FOCUSED,
    AvatarState.ANALYZING: AvatarEmotion.FOCUSED,
    AvatarState.ALERT: AvatarEmotion.CONCERNED,
    AvatarState.REPORTING: AvatarEmotion.FOCUSED,
    AvatarState.SPEAKING: AvatarEmotion.NEUTRAL,
    AvatarState.SLEEPING: AvatarEmotion.NEUTRAL,
}

# State -> recommended animation mapping
STATE_ANIMATION_MAP = {
    AvatarState.BOOTING: AnimationTrigger.NONE,
    AvatarState.IDLE: AnimationTrigger.BLINK,
    AvatarState.LISTENING: AnimationTrigger.LOOK_LEFT,
    AvatarState.THINKING: AnimationTrigger.THINK_BUBBLE,
    AvatarState.ANALYZING: AnimationTrigger.SCANNING,
    AvatarState.ALERT: AnimationTrigger.EXCLAMATION,
    AvatarState.REPORTING: AnimationTrigger.NOD,
    AvatarState.SPEAKING: AnimationTrigger.NOD,
    AvatarState.SLEEPING: AnimationTrigger.BLINK,
}


@dataclass
class AvatarSnapshot:
    state: AvatarState = AvatarState.BOOTING
    emotion: AvatarEmotion = AvatarEmotion.CURIOUS
    lip_sync_value: float = 0.0
    eye_direction: str = "center"
    animation: str = AnimationTrigger.NONE.value
    text_display: str = ""
    boot_progress: float = 0.0
    timestamp: float = field(default_factory=time.time)


class LipSyncEngine:
    """Calculates lip sync values from audio amplitude."""

    def __init__(self, sample_rate: int = 16000, sensitivity: float = 1.0, decay: float = 0.85):
        self.sample_rate = sample_rate
        self.sensitivity = sensitivity
        self.decay = decay
        self._current_value = 0.0
        self._peak = 0.0
        self._smoothing_buffer: List[float] = []

    def process_audio(self, audio_chunk: bytes) -> float:
        """Process raw audio bytes and return lip sync value (0.0 - 1.0)."""
        if not audio_chunk:
            self._current_value *= self.decay
            return self._current_value

        try:
            samples = []
            for i in range(0, min(len(audio_chunk), 640), 2):
                if i + 1 < len(audio_chunk):
                    sample = int.from_bytes(audio_chunk[i:i+2], byteorder='little', signed=True)
                    samples.append(abs(sample) / 32768.0)

            if samples:
                amplitude = sum(samples) / len(samples)
                target = min(1.0, amplitude * self.sensitivity * 3.0)
                self._current_value = self._current_value * self.decay + target * (1 - self.decay)
                self._peak = max(self._peak * 0.99, self._current_value)
        except Exception:
            self._current_value *= self.decay

        return max(0.0, min(1.0, self._current_value))

    def reset(self):
        self._current_value = 0.0
        self._peak = 0.0


class EmotionEngine:
    """Automatically detects and transitions emotions based on context."""

    def __init__(self):
        self._current = AvatarEmotion.NEUTRAL
        self._transition_time = time.time()
        self._emotion_history: List[tuple] = []
        self._energy = 0.5
        self._confidence = 0.5

    def on_state_change(self, state: AvatarState):
        new_emotion = STATE_EMOTION_MAP.get(state, AvatarEmotion.NEUTRAL)
        if new_emotion != self._current:
            self._transition(new_emotion)

    def on_text_input(self, text: str):
        text_lower = text.lower()
        if any(w in text_lower for w in ["error", "fail", "alert", "warning", "danger"]):
            self._transition(AvatarEmotion.CONCERNED)
        elif any(w in text_lower for w in ["great", "success", "complete", "found"]):
            self._transition(AvatarEmotion.SATISFIED)
        elif any(w in text_lower for w in ["search", "find", "what", "how"]):
            self._transition(AvatarEmotion.CURIOUS)
        elif any(w in text_lower for w in ["analyzing", "processing", "computing"]):
            self._transition(AvatarEmotion.FOCUSED)

    def on_thinking(self):
        self._transition(AvatarEmotion.FOCUSED)
        self._energy = min(1.0, self._energy + 0.1)

    def on_result(self, success: bool):
        if success:
            self._transition(AvatarEmotion.SATISFIED)
        else:
            self._transition(AvatarEmotion.CONCERNED)
        self._energy = max(0.0, self._energy - 0.1)

    def _transition(self, new_emotion: AvatarEmotion):
        if new_emotion != self._current:
            self._emotion_history.append((self._current.value, time.time()))
            self._current = new_emotion
            self._transition_time = time.time()
            logger.debug(f"Emotion: {self._current.value}")

    def get_emotion(self) -> AvatarEmotion:
        return self._current

    def get_status(self) -> Dict[str, Any]:
        return {
            "current": self._current.value,
            "energy": round(self._energy, 2),
            "confidence": round(self._confidence, 2),
            "transitions": len(self._emotion_history),
        }


class AvatarEngine:
    """
    Manages avatar state, provides WebSocket API for Godot client.
    """

    def __init__(self):
        self._state = AvatarState.BOOTING
        self._emotion_engine = EmotionEngine()
        self._lip_sync = LipSyncEngine()
        self._eye_direction = "center"
        self._state_changed_at = time.time()
        self._boot_progress = 0.0
        self._text_display = ""
        self._animation = AnimationTrigger.NONE
        self._connected_clients: Set = set()
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()
        self._boot_complete = False

    # ── State Management ─────────────────────────────────────

    def set_state(self, state: AvatarState, animate: bool = True):
        if state != self._state:
            logger.info(f"Avatar state: {self._state.value} -> {state.value}")
            self._state = state
            self._state_changed_at = time.time()
            self._emotion_engine.on_state_change(state)
            if animate:
                self._animation = STATE_ANIMATION_MAP.get(state, AnimationTrigger.NONE)

    def set_emotion(self, emotion: AvatarEmotion):
        self._emotion_engine._transition(emotion)

    def set_lip_sync(self, value: float):
        self._lip_sync._current_value = max(0.0, min(1.0, value))

    def process_audio_lip_sync(self, audio_chunk: bytes) -> float:
        return self._lip_sync.process_audio(audio_chunk)

    def set_eye_direction(self, direction: str):
        valid = {"center", "left", "right", "up", "down", "crossed"}
        self._eye_direction = direction if direction in valid else "center"

    def set_text_display(self, text: str):
        self._text_display = text[:200]

    def trigger_animation(self, animation: AnimationTrigger):
        self._animation = animation

    def update_boot(self, progress: float):
        self._boot_progress = min(1.0, progress)
        if progress >= 1.0:
            self.set_state(AvatarState.IDLE)

    def complete_boot(self):
        """Transition from BOOTING to IDLE state."""
        if self._state == AvatarState.BOOTING or not self._boot_complete:
            self._boot_complete = True
            self._boot_progress = 1.0
            self.set_state(AvatarState.IDLE)
            logger.info("Avatar boot completed, transitioning to IDLE")

    def on_thinking(self):
        self.set_state(AvatarState.THINKING)
        self._emotion_engine.on_thinking()

    def on_listening(self):
        self.set_state(AvatarState.LISTENING)

    def on_speaking(self, text: str = ""):
        self.set_state(AvatarState.SPEAKING)
        if text:
            self.set_text_display(text)

    def on_alert(self, message: str = ""):
        self.set_state(AvatarState.ALERT)
        if message:
            self.set_text_display(message)

    def on_result(self, success: bool, text: str = ""):
        self._emotion_engine.on_result(success)
        self.set_state(AvatarState.REPORTING)
        if text:
            self.set_text_display(text)

    # ── Snapshot ─────────────────────────────────────────────

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "emotion": self._emotion_engine.get_emotion().value,
            "lip_sync": round(self._lip_sync._current_value, 3),
            "eye_direction": self._eye_direction,
            "animation": self._animation.value,
            "text_display": self._text_display,
            "boot_progress": self._boot_progress,
            "state_duration": round(time.time() - self._state_changed_at, 1),
            "timestamp": time.time(),
        }

    def get_ws_payload(self) -> str:
        return json.dumps(self.get_snapshot())

    # ── WebSocket Server ─────────────────────────────────────

    async def ws_handler(self, websocket):
        """Handle a WebSocket client connection."""
        self._connected_clients.add(websocket)
        logger.info(f"Avatar client connected (total: {len(self._connected_clients)})")

        try:
            await websocket.send(self.get_ws_payload())

            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "invalid JSON"}))
        except Exception as e:
            logger.debug(f"Avatar client disconnected: {e}")
        finally:
            self._connected_clients.discard(websocket)
            logger.info(f"Avatar client removed (total: {len(self._connected_clients)})")

    async def _handle_client_message(self, websocket, data: Dict[str, Any]):
        msg_type = data.get("type", "")

        if msg_type == "get_state":
            await websocket.send(self.get_ws_payload())

        elif msg_type == "set_state":
            state = data.get("state", "idle")
            try:
                self.set_state(AvatarState(state))
                await websocket.send(json.dumps({"ok": True}))
            except ValueError:
                await websocket.send(json.dumps({"error": f"invalid state: {state}"}))

        elif msg_type == "set_emotion":
            emotion = data.get("emotion", "neutral")
            try:
                self.set_emotion(AvatarEmotion(emotion))
                await websocket.send(json.dumps({"ok": True}))
            except ValueError:
                await websocket.send(json.dumps({"error": f"invalid emotion: {emotion}"}))

        elif msg_type == "animate":
            animation = data.get("animation", "none")
            try:
                self.trigger_animation(AnimationTrigger(animation))
                await websocket.send(json.dumps({"ok": True}))
            except ValueError:
                await websocket.send(json.dumps({"error": f"invalid animation: {animation}"}))

        elif msg_type == "set_text":
            self.set_text_display(data.get("text", ""))
            await websocket.send(json.dumps({"ok": True}))

    async def broadcast(self, data: Optional[Dict[str, Any]] = None):
        """Broadcast state to all connected clients."""
        payload = json.dumps(data or self.get_snapshot())
        disconnected = set()
        for ws in list(self._connected_clients):
            try:
                await ws.send(payload)
            except Exception:
                disconnected.add(ws)
        self._connected_clients -= disconnected

    async def start_broadcast_loop(self, interval: float = 0.1):
        """Continuously broadcast state at given interval."""
        while True:
            if self._connected_clients:
                try:
                    await self.broadcast()
                except Exception:
                    pass
            await asyncio.sleep(interval)


# ── Singleton ────────────────────────────────────────────────

_avatar_engine: Optional[AvatarEngine] = None


def get_avatar_engine() -> AvatarEngine:
    global _avatar_engine
    if _avatar_engine is None:
        _avatar_engine = AvatarEngine()
    return _avatar_engine
