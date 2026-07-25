"""
Configuration management for ELIOT Core Service

Loads settings from environment variables with sensible defaults.
Supports multiple environments (dev, test, prod).
"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """ELIOT Configuration"""

    # Environment
    env: Literal["development", "testing", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # API
    core_host: str = "0.0.0.0"
    core_port: int = 8000

    # Hardware
    hardware_target: Literal[
        "jetson-orin-nano",
        "jetson-orin",
        "raspberry-pi",
        "dev-machine",
    ] = "dev-machine"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # Prometheus
    prometheus_port: int = 9090
    prometheus_enabled: bool = True

    # Security
    enable_auth: bool = False
    enable_audit_log: bool = True
    security_dir: str = "security"

    # AI Models (Phase 2)
    models_dir: str = "./models"
    primary_model: str = "qwen2.5-coder-3b-pentest"
    reasoning_model: str = "deepseek-r1-distill-qwen-7b"
    embedding_model: str = "nomic-embed-text"
    cuda_enabled: bool = False
    llama_cpp_host: str = "llama-cpp"
    llama_cpp_port: int = 8080

    # Knowledge Engine (Phase 3)
    vectordb_path: str = "./data/vectordb"
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000

    # Voice (Phase 4)
    wake_word: str = "eliot"
    mic_device_index: int = 0
    speaker_device_index: int = 0
    whisper_model: str = "base"
    tts_voice: str = "en_US-lessac-medium"

    # Vision (Phase 5)
    camera_device_index: int = 0
    face_recognition_threshold: float = 0.6

    # Avatar (Phase 6)
    avatar_enabled: bool = True
    avatar_ws_port: int = 8765

    # MQTT (Raspberry Pi comms)
    mqtt_host: str = "mqtt"
    mqtt_port: int = 1883

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
