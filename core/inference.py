from __future__ import annotations

import enum
import logging
import os
import platform
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

GGUF_MAGIC = b"GGUF"


class GPUBackend(enum.Enum):
    CUDA = "cuda"
    METAL = "metal"
    CPU = "cpu"
    VULKAN = "vulkan"


class ModelStatus(enum.Enum):
    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    READY = "ready"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    name: str
    path: Optional[Path]
    size_bytes: int
    quantization: str
    parameters: str
    backend: GPUBackend
    status: ModelStatus
    loaded_at: Optional[float] = None
    last_used: Optional[float] = None
    usage_count: int = 0
    total_tokens_generated: int = 0
    avg_tokens_per_sec: float = 0.0


@dataclass
class InferenceRequest:
    prompt: str
    model: str = "qwen2.5-coder-3b"
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: Optional[List[str]] = None
    stream: bool = False
    system_prompt: Optional[str] = None
    context: Optional[str] = None


@dataclass
class InferenceResponse:
    text: str
    model: str
    tokens_generated: int = 0
    tokens_per_sec: float = 0.0
    total_duration_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


class GPUDetector:

    @staticmethod
    def detect_backend() -> GPUBackend:
        if GPUDetector._has_cuda():
            return GPUBackend.CUDA
        if GPUDetector._has_metal():
            return GPUBackend.METAL
        if GPUDetector._has_vulkan():
            return GPUBackend.VULKAN
        return GPUBackend.CPU

    @staticmethod
    def _has_cuda() -> bool:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _has_metal() -> bool:
        return platform.system() == "Darwin"

    @staticmethod
    def _has_vulkan() -> bool:
        try:
            result = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and "GPU" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def get_gpu_info() -> Dict[str, Any]:
        backend = GPUDetector.detect_backend()
        info: Dict[str, Any] = {
            "backend": backend.value,
            "gpu_name": "Unknown",
            "memory_total_mb": 0,
            "memory_free_mb": 0,
        }
        if backend == GPUBackend.CUDA:
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=name,memory.total,memory.free",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(", ")
                    if len(parts) >= 1:
                        info["gpu_name"] = parts[0]
                    if len(parts) >= 3:
                        try:
                            info["memory_total_mb"] = int(parts[1])
                        except ValueError:
                            info["memory_total_mb"] = 0
                        try:
                            info["memory_free_mb"] = int(parts[2])
                        except ValueError:
                            info["memory_free_mb"] = 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        elif backend == GPUBackend.METAL:
            info["gpu_name"] = "Apple Silicon GPU"
        elif backend == GPUBackend.VULKAN:
            try:
                result = subprocess.run(
                    ["vulkaninfo", "--summary"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "GPU" in line and ":" in line:
                            info["gpu_name"] = line.split(":", 1)[1].strip()
                            break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return info


MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "qwen2.5-coder-3b": {
        "repo": "bartowski/Qwen2.5-Coder-3B-Instruct-GGUF",
        "filename": "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf",
        "description": "Qwen2.5-Coder 3B - compact code generation model",
        "parameters": "3B",
        "quantization": "Q4_K_M",
        "context_length": 32768,
        "use_cases": ["code_generation", "code_completion", "refactoring"],
    },
    "deepseek-r1-distill-1.5b": {
        "repo": "bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
        "filename": "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "description": "DeepSeek-R1 Distill 1.5B - reasoning model",
        "parameters": "1.5B",
        "quantization": "Q4_K_M",
        "context_length": 32768,
        "use_cases": ["reasoning", "chain_of_thought", "problem_solving"],
    },
    "nomic-embed-text": {
        "repo": "nomic-ai/nomic-embed-text-v1.5-GGUF",
        "filename": "nomic-embed-text-v1.5.Q4_K_M.gguf",
        "description": "Nomic Embed Text v1.5 - text embeddings",
        "parameters": "137M",
        "quantization": "Q4_K_M",
        "context_length": 8192,
        "use_cases": ["embeddings", "semantic_search", "similarity"],
    },
}


class ModelManager:

    def __init__(self, models_dir: str = "./models") -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._scanned_models: Dict[str, Path] = {}
        self._scan_models()

    def _scan_models(self) -> None:
        for model_id, meta in MODEL_REGISTRY.items():
            expected = self.models_dir / meta["filename"]
            if expected.exists() and expected.stat().st_size > 0:
                self._scanned_models[model_id] = expected

    def list_models(self) -> List[Dict[str, Any]]:
        result = []
        for model_id, meta in MODEL_REGISTRY.items():
            path = self._scanned_models.get(model_id)
            downloaded = path is not None
            result.append(
                {
                    "id": model_id,
                    "description": meta["description"],
                    "parameters": meta["parameters"],
                    "quantization": meta["quantization"],
                    "status": ModelStatus.READY.value
                    if downloaded
                    else ModelStatus.NOT_DOWNLOADED.value,
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 1)
                    if path
                    else 0,
                    "path": str(path) if path else None,
                    "use_cases": meta["use_cases"],
                    "context_length": meta["context_length"],
                }
            )
        return result

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        if model_id not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_id}")
        meta = MODEL_REGISTRY[model_id]
        path = self._scanned_models.get(model_id)
        downloaded = path is not None
        return {
            "id": model_id,
            "description": meta["description"],
            "parameters": meta["parameters"],
            "quantization": meta["quantization"],
            "status": ModelStatus.READY.value
            if downloaded
            else ModelStatus.NOT_DOWNLOADED.value,
            "size_mb": round(path.stat().st_size / (1024 * 1024), 1) if path else 0,
            "path": str(path) if path else None,
            "use_cases": meta["use_cases"],
            "context_length": meta["context_length"],
        }

    def is_downloaded(self, model_id: str) -> bool:
        return model_id in self._scanned_models

    def get_model_path(self, model_id: str) -> Optional[Path]:
        return self._scanned_models.get(model_id)

    async def download_model(
        self, model_id: str, quantization: str = "Q4_K_M"
    ) -> Path:
        if model_id not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_id}")
        meta = MODEL_REGISTRY[model_id]
        repo = meta["repo"]
        filename = meta["filename"]

        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            raise RuntimeError(
                "huggingface_hub is required for model downloads. "
                "Install it with: pip install huggingface_hub"
            )

        logger.info("Downloading model %s from %s", model_id, repo)
        downloaded_path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=str(self.models_dir),
            local_dir_use_symlinks=False,
        )
        final_path = self.models_dir / filename
        if downloaded_path != str(final_path):
            import shutil

            shutil.move(downloaded_path, str(final_path))
        self._scanned_models[model_id] = final_path
        logger.info("Model %s downloaded to %s", model_id, final_path)
        return final_path

    def validate_model(self, model_id: str) -> bool:
        path = self._scanned_models.get(model_id)
        if path is None or not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                magic = f.read(4)
            if magic != GGUF_MAGIC:
                logger.warning(
                    "Model %s has invalid GGUF header: %s", model_id, magic.hex()
                )
                return False
            size = path.stat().st_size
            if size < 1024 * 1024:
                logger.warning("Model %s appears too small: %d bytes", model_id, size)
                return False
            return True
        except OSError as e:
            logger.error("Failed to validate model %s: %s", model_id, e)
            return False


try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None


class LlamaCppInference:

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_threads: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self.verbose = verbose
        self._model: Any = None
        self._loaded: bool = False
        self._backend = GPUDetector.detect_backend()

    def load(self) -> None:
        if not LLAMA_CPP_AVAILABLE:
            logger.warning(
                "llama-cpp-python not installed. Inference will use fallback."
            )
            self._loaded = False
            return

        logger.info(
            "Loading model from %s with backend %s",
            self.model_path,
            self._backend.value,
        )
        gpu_layers = self.n_gpu_layers
        if self._backend == GPUBackend.CPU:
            gpu_layers = 0

        kwargs: Dict[str, Any] = {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": gpu_layers,
            "verbose": self.verbose,
        }
        if self.n_threads is not None:
            kwargs["n_threads"] = self.n_threads

        try:
            self._model = Llama(**kwargs)
            self._loaded = True
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            self._model = None
            self._loaded = False

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        self._loaded = False
        logger.info("Model unloaded")

    def complete(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> InferenceResponse:
        full_prompt = self._build_prompt(prompt, system_prompt, context)
        start_time = time.perf_counter()

        if not self._loaded or self._model is None:
            return self._fallback_complete(prompt, max_tokens)

        try:
            result = self._model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                stop=stop or [],
                echo=False,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            text = result["choices"][0]["text"]
            tokens_generated = result.get("usage", {}).get("completion_tokens", 0)
            if tokens_generated == 0:
                tokens_generated = int(len(text.split()) * 1.3)
            tokens_per_sec = (
                tokens_generated / (elapsed_ms / 1000) if elapsed_ms > 0 else 0
            )

            return InferenceResponse(
                text=text,
                model=self.model_path,
                tokens_generated=tokens_generated,
                tokens_per_sec=round(tokens_per_sec, 2),
                total_duration_ms=round(elapsed_ms, 2),
                finish_reason=result["choices"][0].get("finish_reason", "stop"),
                metadata={"backend": self._backend.value},
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Inference failed: %s", e)
            return InferenceResponse(
                text="",
                model=self.model_path,
                tokens_generated=0,
                tokens_per_sec=0.0,
                total_duration_ms=round(elapsed_ms, 2),
                finish_reason="error",
                metadata={"error": str(e)},
            )

    def stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Generator[str, None, None]:
        full_prompt = self._build_prompt(prompt, system_prompt, context)

        if not self._loaded or self._model is None:
            yield f"[Model not loaded: {self.model_path}]"
            return

        try:
            stream_result = self._model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                stop=stop or [],
                echo=False,
                stream=True,
            )
            for chunk in stream_result:
                if chunk["choices"][0]["text"]:
                    yield chunk["choices"][0]["text"]
        except Exception as e:
            logger.error("Streaming inference failed: %s", e)
            yield f"[Error: {e}]"

    def _build_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        parts: List[str] = []
        parts.append("<|im_start|>system")
        sys_text = "You are a helpful assistant."
        if system_prompt:
            sys_text = system_prompt
        if context:
            sys_text += f"\n\nContext:\n{context}"
        parts.append(sys_text)
        parts.append("<|im_end|>")
        parts.append("<|im_start|>user")
        parts.append(prompt)
        parts.append("<|im_end|>")
        parts.append("<|im_start|>assistant")
        return "\n".join(parts)

    def _fallback_complete(
        self, prompt: str, max_tokens: int = 512
    ) -> InferenceResponse:
        response_text = (
            "[ELIOT Inference] No model loaded. "
            "This is a placeholder response. "
            "Please install llama-cpp-python and download a model "
            "to enable local inference."
        )
        return InferenceResponse(
            text=response_text,
            model="fallback",
            tokens_generated=len(response_text.split()),
            tokens_per_sec=0.0,
            total_duration_ms=0.0,
            finish_reason="stop",
            metadata={"fallback": True, "prompt": prompt[:200]},
        )


_inference_engine_instance: Optional["InferenceEngine"] = None


class InferenceEngine:

    def __init__(self, models_dir: str = "./models") -> None:
        self.model_manager = ModelManager(models_dir)
        self._loaded_backends: Dict[str, LlamaCppInference] = {}
        self._default_model = "qwen2.5-coder-3b"
        self._initialized = False
        self._gpu_info = GPUDetector.get_gpu_info()
        logger.info("InferenceEngine created with GPU backend: %s", self._gpu_info["backend"])

    async def initialize(self, model_id: Optional[str] = None) -> None:
        target = model_id or self._default_model
        if not self.model_manager.is_downloaded(target):
            logger.warning(
                "Default model %s not downloaded. Attempting download.", target
            )
            try:
                await self.model_manager.download_model(target)
            except Exception as e:
                logger.error("Failed to download model %s: %s", target, e)
                return
        self._load_model(target)
        self._initialized = True

    def _load_model(self, model_id: str) -> None:
        path = self.model_manager.get_model_path(model_id)
        if path is None:
            logger.error("Model %s not found", model_id)
            return
        if model_id in self._loaded_backends:
            return
        backend = LlamaCppInference(str(path))
        backend.load()
        self._loaded_backends[model_id] = backend

    def shutdown(self) -> None:
        for model_id, backend in self._loaded_backends.items():
            logger.info("Unloading model %s", model_id)
            backend.unload()
        self._loaded_backends.clear()
        self._initialized = False
        logger.info("InferenceEngine shut down")

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        model_id = request.model
        if model_id not in self._loaded_backends:
            self._load_model(model_id)
        backend = self._loaded_backends.get(model_id)
        if backend is None:
            return InferenceResponse(
                text="",
                model=model_id,
                finish_reason="error",
                metadata={"error": f"Model {model_id} not available"},
            )
        return backend.complete(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            repeat_penalty=request.repeat_penalty,
            stop=request.stop,
            system_prompt=request.system_prompt,
            context=request.context,
        )

    def stream(self, request: InferenceRequest) -> Generator[str, None, None]:
        model_id = request.model
        if model_id not in self._loaded_backends:
            self._load_model(model_id)
        backend = self._loaded_backends.get(model_id)
        if backend is None:
            yield f"[Error: Model {model_id} not available]"
            return
        yield from backend.stream(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            repeat_penalty=request.repeat_penalty,
            stop=request.stop,
            system_prompt=request.system_prompt,
            context=request.context,
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "gpu": self._gpu_info,
            "loaded_models": {
                mid: {
                    "loaded": True,
                    "backend": backend._backend.value,
                }
                for mid, backend in self._loaded_backends.items()
            },
            "available_models": [
                m["id"] for m in self.model_manager.list_models()
            ],
        }

    def list_models(self) -> List[Dict[str, Any]]:
        return self.model_manager.list_models()

    async def download_model(
        self, model_id: str, quantization: str = "Q4_K_M"
    ) -> Path:
        return await self.model_manager.download_model(model_id, quantization)

    def validate_model(self, model_id: str) -> bool:
        return self.model_manager.validate_model(model_id)


def get_inference_engine() -> InferenceEngine:
    global _inference_engine_instance
    if _inference_engine_instance is None:
        _inference_engine_instance = InferenceEngine()
    return _inference_engine_instance
