"""
ELIOT Avatar Engine

3D cyberpunk avatar with emotional states.
Designed for Godot Engine integration via WebSocket.
Avatar states: BOOTING, IDLE, LISTENING, THINKING, ANALYZING, ALERT, REPORTING
Emotions: curious, focused, concerned, satisfied, sleeping
"""

import time
import logging
from enum import Enum
from typing import Any, Dict, Optional
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


class AvatarEmotion(str, Enum):
    CURIOUS = "curious"
    FOCUSED = "focused"
    CONCERNED = "concerned"
    SATISFIED = "satisfied"
    SLEEPING = "sleeping"


@dataclass
class AvatarSnapshot:
    state: AvatarState = AvatarState.BOOTING
    emotion: AvatarEmotion = AvatarEmotion.CURIOUS
    lip_sync_value: float = 0.0
    eye_direction: str = "center"
    timestamp: float = field(default_factory=time.time)


class AvatarEngine:
    """
    Manages avatar state and provides WebSocket API for Godot client.
    """

    def __init__(self):
        self._state = AvatarState.BOOTING
        self._emotion = AvatarEmotion.CURIOUS
        self._lip_sync = 0.0
        self._eye_direction = "center"
        self._state_changed_at = time.time()
        self._boot_progress = 0.0

    def set_state(self, state: AvatarState):
        if state != self._state:
            logger.info(f"Avatar state: {self._state.value} -> {state.value}")
            self._state = state
            self._state_changed_at = time.time()

    def set_emotion(self, emotion: AvatarEmotion):
        if emotion != self._emotion:
            logger.info(f"Avatar emotion: {self._emotion.value} -> {emotion.value}")
            self._emotion = emotion

    def set_lip_sync(self, value: float):
        self._lip_sync = max(0.0, min(1.0, value))

    def set_eye_direction(self, direction: str):
        self._eye_direction = direction

    def update_boot(self, progress: float):
        self._boot_progress = min(1.0, progress)
        if progress >= 1.0:
            self.set_state(AvatarState.IDLE)

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "emotion": self._emotion.value,
            "lip_sync": self._lip_sync,
            "eye_direction": self._eye_direction,
            "state_duration": time.time() - self._state_changed_at,
            "boot_progress": self._boot_progress,
        }

    def get_ws_payload(self) -> str:
        """Generate JSON payload for WebSocket to Godot."""
        import json
        return json.dumps(self.get_snapshot())


_avatar_engine: Optional[AvatarEngine] = None


def get_avatar_engine() -> AvatarEngine:
    global _avatar_engine
    if _avatar_engine is None:
        _avatar_engine = AvatarEngine()
    return _avatar_engine
