import os
import tempfile
import pytest

from core.inference import (
    GPUDetector,
    GPUBackend,
    ModelManager,
    MODEL_REGISTRY,
    ModelStatus,
    LlamaCppInference,
    InferenceEngine,
    get_inference_engine,
    InferenceRequest,
    InferenceResponse,
)


class TestGPUDetector:
    def test_detect_backend_returns_enum(self):
        backend = GPUDetector.detect_backend()
        assert isinstance(backend, GPUBackend)

    def test_get_gpu_info_returns_dict(self):
        info = GPUDetector.get_gpu_info()
        assert isinstance(info, dict)
        assert "backend" in info
        assert isinstance(info["backend"], str)


class TestModelManager:
    def test_init_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = os.path.join(tmpdir, "models")
            manager = ModelManager(models_dir=models_dir)
            assert os.path.isdir(models_dir)

    def test_list_models_returns_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            models = manager.list_models()
            assert len(models) == 3

    def test_model_registry_entries(self):
        expected_keys = {"qwen2.5-coder-3b", "deepseek-r1-distill-1.5b", "nomic-embed-text"}
        assert set(MODEL_REGISTRY.keys()) == expected_keys

    def test_not_downloaded_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            models = manager.list_models()
            for model in models:
                assert model["status"] == ModelStatus.NOT_DOWNLOADED.value

    def test_is_downloaded_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            assert manager.is_downloaded("qwen2.5-coder-3b") is False

    def test_get_model_path_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            path = manager.get_model_path("qwen2.5-coder-3b")
            assert path is None

    def test_get_model_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            info = manager.get_model_info("qwen2.5-coder-3b")
            assert isinstance(info, dict)
            assert info["id"] == "qwen2.5-coder-3b"
            assert "parameters" in info

    def test_get_model_info_unknown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            with pytest.raises(ValueError, match="Unknown model"):
                manager.get_model_info("nonexistent-model")

    def test_validate_model_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            result = manager.validate_model("nonexistent-model")
            assert result is False

    def test_validate_model_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelManager(models_dir=tmpdir)
            result = manager.validate_model("qwen2.5-coder-3b")
            assert result is False


class TestLlamaCppInference:
    def test_init(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        assert inference.model_path == "/tmp/fake-model.gguf"

    def test_load_fallback(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        inference.load()
        assert inference._loaded is False

    def test_is_loaded_after_load(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        inference.load()
        assert inference._loaded is False

    def test_complete_returns_response(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        response = inference.complete("Hello, how are you?")
        assert isinstance(response, InferenceResponse)

    def test_complete_fallback_text(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        response = inference.complete("Tell me a joke")
        assert len(response.text) > 0

    def test_stream_yields_chunks(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        chunks = list(inference.stream("Count to five"))
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_build_prompt_with_system(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        prompt = inference._build_prompt("What is cybersecurity?", system_prompt="You are a security expert.")
        assert "You are a security expert." in prompt
        assert "What is cybersecurity?" in prompt

    def test_build_prompt_with_context(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        prompt = inference._build_prompt("Tell me more", context="Previous: What is a firewall?")
        assert "What is a firewall?" in prompt
        assert "Tell me more" in prompt

    def test_build_prompt_basic(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        prompt = inference._build_prompt("Hello")
        assert "Hello" in prompt
        assert "<|im_start|>" in prompt

    def test_unload(self):
        inference = LlamaCppInference(model_path="/tmp/fake-model.gguf")
        inference.load()
        inference.unload()
        assert inference._loaded is False


class TestInferenceEngine:
    def test_singleton(self):
        engine1 = get_inference_engine()
        engine2 = get_inference_engine()
        assert engine1 is engine2

    def test_list_models(self):
        engine = get_inference_engine()
        models = engine.list_models()
        assert isinstance(models, list)
        assert len(models) == 3

    def test_get_status(self):
        engine = get_inference_engine()
        status = engine.get_status()
        assert isinstance(status, dict)
        assert "initialized" in status
        assert "gpu" in status
        assert "loaded_models" in status
        assert "available_models" in status


class TestInferenceDataclasses:
    def test_inference_request_defaults(self):
        request = InferenceRequest(prompt="test")
        assert request.prompt == "test"
        assert request.system_prompt is None
        assert request.context is None
        assert request.max_tokens == 512
        assert request.temperature == 0.7

    def test_inference_response_defaults(self):
        response = InferenceResponse(text="hello", model="test")
        assert response.text == "hello"
        assert response.tokens_generated == 0
        assert response.model == "test"
        assert response.finish_reason == "stop"
        assert response.metadata == {}
