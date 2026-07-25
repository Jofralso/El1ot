import os
import shutil
import tempfile

import pytest

from knowledge.update import (
    IntegrityVerifier,
    KnowledgeUpdateManager,
    KnowledgeUpdateSource,
    UpdateManifest,
    UpdateMode,
    UpdateStatus,
)


class TestUpdateEnums:
    def test_update_modes(self):
        assert UpdateMode.ONLINE.value == "online"
        assert UpdateMode.OFFLINE.value == "offline"
        assert UpdateMode.DELTA.value == "delta"
        assert len(UpdateMode) == 3

    def test_update_statuses(self):
        expected = {"pending", "checking", "downloading", "verifying", "applying", "completed", "failed"}
        actual = {s.value for s in UpdateStatus}
        assert expected == actual


class TestIntegrityVerifier:
    def test_compute_checksum(self):
        verifier = IntegrityVerifier()
        result = verifier.compute_checksum(b"hello world")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_verify_checksum_valid(self):
        verifier = IntegrityVerifier()
        data = b"test data for verification"
        checksum = verifier.compute_checksum(data)
        assert verifier.verify_checksum(data, checksum) is True

    def test_verify_checksum_invalid(self):
        verifier = IntegrityVerifier()
        data = b"test data for verification"
        wrong = "0" * 64
        assert verifier.verify_checksum(data, wrong) is False

    def test_compute_file_checksum(self):
        verifier = IntegrityVerifier()
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "test.txt")
            with open(path, "wb") as f:
                f.write(b"file content")
            result = verifier.compute_file_checksum(path)
            assert isinstance(result, str)
            assert len(result) == 64
        finally:
            shutil.rmtree(tmpdir)

    def test_verify_file(self):
        verifier = IntegrityVerifier()
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "test.txt")
            content = b"verify me"
            with open(path, "wb") as f:
                f.write(content)
            checksum = verifier.compute_checksum(content)
            assert verifier.verify_file(path, checksum) is True
            assert verifier.verify_file(path, "0" * 64) is False
        finally:
            shutil.rmtree(tmpdir)


class TestUpdateManifest:
    def test_manifest_creation(self):
        manifest = UpdateManifest(
            version="1.0.0",
            created_at=1000.0,
            sources=[{"name": "test"}],
            checksum="abc123",
            description="Test manifest",
        )
        assert manifest.version == "1.0.0"
        assert manifest.created_at == 1000.0
        assert manifest.checksum == "abc123"
        assert manifest.description == "Test manifest"

    def test_manifest_defaults(self):
        manifest = UpdateManifest(
            version="1.0",
            created_at=1000.0,
            sources=[],
            checksum="",
        )
        assert manifest.description == ""
        assert manifest.min_eliot_version == "0.3.0"


class TestKnowledgeUpdateManager:
    def test_init(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        assert manager.knowledge_engine is engine
        assert manager._sources == []
        assert manager._update_history == []

    def test_add_source(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        source = KnowledgeUpdateSource(name="src1", update_type="full", url="http://example.com")
        manager.add_source(source)
        assert len(manager._sources) == 1
        assert manager._sources[0].name == "src1"

    def test_remove_source(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        source = KnowledgeUpdateSource(name="src1", update_type="full")
        manager.add_source(source)
        assert manager.remove_source("src1") is True
        assert len(manager._sources) == 0

    def test_list_sources(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        source = KnowledgeUpdateSource(name="src1", update_type="full", url="http://example.com")
        manager.add_source(source)
        sources = manager.list_sources()
        assert isinstance(sources, list)
        assert len(sources) == 1
        assert sources[0]["name"] == "src1"
        assert sources[0]["url"] == "http://example.com"

    def test_check_updates_empty(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        assert manager.check_updates() == []

    def test_full_update_no_sources(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        result = manager.full_update()
        assert result["sources_updated"] == 0
        assert result["sources_failed"] == 0

    def test_get_status(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        status = manager.get_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert "sources_count" in status
        assert "last_update" in status

    def test_get_update_history_initial(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        history = manager.get_update_history()
        assert isinstance(history, list)
        assert len(history) == 0

    def test_export_knowledge(self):
        engine = object()
        manager = KnowledgeUpdateManager(knowledge_engine=engine)
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "export.json")
            result = manager.export_knowledge(path)
            assert result == path
            assert os.path.exists(path)
            import json
            with open(path) as f:
                data = json.load(f)
            assert "sources" in data
            assert "status" in data
            assert "history" in data
        finally:
            shutil.rmtree(tmpdir)


class TestKnowledgeUpdateSource:
    def test_source_creation(self):
        source = KnowledgeUpdateSource(
            name="test_source",
            update_type="full",
            url="http://example.com/updates",
        )
        assert source.name == "test_source"
        assert source.url == "http://example.com/updates"
        assert source.update_type == "full"

    def test_source_defaults(self):
        source = KnowledgeUpdateSource(name="x", update_type="full")
        assert source.url is None
        assert source.local_path is None
        assert source.checksum == ""
        assert source.size_bytes == 0
        assert source.last_updated == 0.0
        assert source.metadata == {}
