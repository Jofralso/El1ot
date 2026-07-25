import hashlib
import os
import json
import shutil
import tempfile
import logging
import time
import uuid
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class UpdateMode(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DELTA = "delta"


class UpdateStatus(Enum):
    PENDING = "pending"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UpdateManifest:
    version: str
    created_at: float
    sources: List[Dict[str, Any]]
    checksum: str
    description: str = ""
    min_eliot_version: str = "0.3.0"


@dataclass
class KnowledgeUpdateSource:
    name: str
    update_type: str
    url: Optional[str] = None
    local_path: Optional[str] = None
    checksum: str = ""
    size_bytes: int = 0
    last_updated: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrityVerifier:
    def compute_checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def compute_file_checksum(self, path: str) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_checksum(self, data: bytes, expected: str) -> bool:
        return self.compute_checksum(data) == expected

    def verify_file(self, path: str, expected: str) -> bool:
        return self.compute_file_checksum(path) == expected


class KnowledgeUpdateManager:
    def __init__(self, knowledge_engine, models_dir: str = "./models"):
        self.knowledge_engine = knowledge_engine
        self.models_dir = Path(models_dir)
        self._sources: List[KnowledgeUpdateSource] = []
        self._update_history: List[Dict] = []
        self._status: UpdateStatus = UpdateStatus.PENDING
        self.verifier = IntegrityVerifier()

    def add_source(self, source: KnowledgeUpdateSource) -> None:
        for i, existing in enumerate(self._sources):
            if existing.name == source.name:
                self._sources[i] = source
                return
        self._sources.append(source)

    def remove_source(self, name: str) -> bool:
        for i, source in enumerate(self._sources):
            if source.name == name:
                self._sources.pop(i)
                return True
        return False

    def list_sources(self) -> List[Dict]:
        return [asdict(s) for s in self._sources]

    def check_updates(self) -> List[Dict]:
        self._status = UpdateStatus.CHECKING
        available = []
        for source in self._sources:
            try:
                if source.local_path and os.path.exists(source.local_path):
                    current_size = os.path.getsize(source.local_path)
                    current_mtime = os.path.getmtime(source.local_path)
                    needs_update = (
                        source.last_updated == 0.0
                        or current_mtime > source.last_updated
                        or current_size != source.size_bytes
                    )
                    if needs_update:
                        available.append({
                            "name": source.name,
                            "type": source.update_type,
                            "available": True,
                            "local_path": source.local_path,
                            "size_bytes": current_size,
                            "last_modified": current_mtime,
                        })
                elif source.url:
                    available.append({
                        "name": source.name,
                        "type": source.update_type,
                        "available": True,
                        "url": source.url,
                        "needs_download": True,
                    })
                else:
                    available.append({
                        "name": source.name,
                        "type": source.update_type,
                        "available": False,
                        "reason": "no valid source location",
                    })
            except Exception as e:
                logger.error(f"Error checking source {source.name}: {e}")
                available.append({
                    "name": source.name,
                    "type": source.update_type,
                    "available": False,
                    "error": str(e),
                })
        self._status = UpdateStatus.PENDING
        return available

    def download_update(self, source_name: str, mode: UpdateMode = UpdateMode.ONLINE) -> str:
        self._status = UpdateStatus.DOWNLOADING
        source = None
        for s in self._sources:
            if s.name == source_name:
                source = s
                break
        if source is None:
            self._status = UpdateStatus.FAILED
            raise ValueError(f"Source '{source_name}' not found")

        temp_dir = tempfile.mkdtemp(prefix="eliot_update_")
        dest_path = os.path.join(temp_dir, f"{source.name}.json")

        try:
            if mode == UpdateMode.OFFLINE or source.local_path:
                src_path = source.local_path
                if src_path is None:
                    raise ValueError("No local path specified for offline mode")
                if not os.path.exists(src_path):
                    raise FileNotFoundError(f"Local path not found: {src_path}")
                shutil.copy2(src_path, dest_path)
            elif mode == UpdateMode.ONLINE and source.url:
                import urllib.request
                urllib.request.urlretrieve(source.url, dest_path)
            else:
                raise ValueError(f"Cannot download source '{source_name}' in {mode.value} mode")

            if source.checksum:
                if not self.verifier.verify_file(dest_path, source.checksum):
                    os.remove(dest_path)
                    os.rmdir(temp_dir)
                    self._status = UpdateStatus.FAILED
                    raise ValueError(f"Checksum verification failed for {source_name}")

            self._status = UpdateStatus.PENDING
            return dest_path
        except Exception as e:
            self._status = UpdateStatus.FAILED
            if os.path.exists(dest_path):
                os.remove(dest_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
            raise

    def apply_update(self, update_path: str, verify: bool = True) -> Dict:
        self._status = UpdateStatus.VERIFYING
        result = {
            "success": False,
            "source": os.path.basename(update_path),
            "documents_added": 0,
            "documents_updated": 0,
            "errors": [],
            "timestamp": time.time(),
        }

        try:
            if not os.path.exists(update_path):
                raise FileNotFoundError(f"Update file not found: {update_path}")

            with open(update_path, "rb") as f:
                raw_data = f.read()

            try:
                update_data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in update file: {e}")

            if verify and "checksum" in update_data:
                if not self.verifier.verify_checksum(raw_data, update_data["checksum"]):
                    raise ValueError("Manifest checksum verification failed")

            self._status = UpdateStatus.APPLYING

            documents = update_data.get("documents", [])
            if not documents and isinstance(update_data, list):
                documents = update_data
            elif not documents:
                documents = [update_data]

            for doc in documents:
                try:
                    if hasattr(self.knowledge_engine, "ingest_document"):
                        self.knowledge_engine.ingest_document(doc)
                    elif hasattr(self.knowledge_engine, "add_document"):
                        self.knowledge_engine.add_document(doc)
                    result["documents_added"] += 1
                except Exception as e:
                    result["errors"].append(str(e))
                    logger.error(f"Error ingesting document: {e}")

            result["success"] = len(result["errors"]) == 0 or result["documents_added"] > 0
            result["total_documents"] = len(documents)

            self._update_history.append({
                "update_id": str(uuid.uuid4()),
                "path": update_path,
                "timestamp": result["timestamp"],
                "success": result["success"],
                "documents_added": result["documents_added"],
                "errors": result["errors"],
            })

            self._status = UpdateStatus.COMPLETED
        except Exception as e:
            result["errors"].append(str(e))
            result["success"] = False
            self._status = UpdateStatus.FAILED
            logger.error(f"Update application failed: {e}")

        return result

    def full_update(self, mode: UpdateMode = UpdateMode.ONLINE) -> Dict:
        self._status = UpdateStatus.CHECKING
        results = {
            "success": True,
            "sources_updated": 0,
            "sources_failed": 0,
            "details": [],
            "timestamp": time.time(),
        }

        available = self.check_updates()
        for update_info in available:
            if not update_info.get("available"):
                continue

            source_name = update_info["name"]
            try:
                update_path = self.download_update(source_name, mode)
                apply_result = self.apply_update(update_path)
                results["details"].append({
                    "source": source_name,
                    "result": apply_result,
                })
                if apply_result["success"]:
                    results["sources_updated"] += 1
                else:
                    results["sources_failed"] += 1
            except Exception as e:
                results["details"].append({
                    "source": source_name,
                    "error": str(e),
                })
                results["sources_failed"] += 1
                logger.error(f"Failed to update source {source_name}: {e}")

        results["success"] = results["sources_failed"] == 0 or results["sources_updated"] > 0
        self._status = UpdateStatus.COMPLETED if results["success"] else UpdateStatus.FAILED
        return results

    def get_status(self) -> Dict:
        return {
            "status": self._status.value,
            "sources_count": len(self._sources),
            "history_count": len(self._update_history),
            "last_update": self._update_history[-1] if self._update_history else None,
        }

    def get_update_history(self) -> List[Dict]:
        return list(self._update_history)

    def export_knowledge(self, output_path: str) -> str:
        export_data = {
            "version": "1.0",
            "exported_at": time.time(),
            "sources": self.list_sources(),
            "history": self.get_update_history(),
            "status": self.get_status(),
        }

        if hasattr(self.knowledge_engine, "export_documents"):
            export_data["documents"] = self.knowledge_engine.export_documents()
        elif hasattr(self.knowledge_engine, "get_all_documents"):
            export_data["documents"] = self.knowledge_engine.get_all_documents()

        export_data["checksum"] = self.verifier.compute_checksum(
            json.dumps(export_data, default=str).encode()
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return output_path

    def import_knowledge(self, archive_path: str) -> Dict:
        result = {
            "success": False,
            "documents_imported": 0,
            "errors": [],
            "timestamp": time.time(),
        }

        try:
            if not os.path.exists(archive_path):
                raise FileNotFoundError(f"Archive not found: {archive_path}")

            with open(archive_path, "r") as f:
                import_data = json.load(f)

            if "checksum" in import_data:
                check_copy = dict(import_data)
                expected = check_copy.pop("checksum")
                if not self.verifier.verify_checksum(
                    json.dumps(check_copy, default=str).encode(), expected
                ):
                    raise ValueError("Archive checksum verification failed")

            if "sources" in import_data:
                for source_dict in import_data["sources"]:
                    source = KnowledgeUpdateSource(**{
                        k: v for k, v in source_dict.items()
                        if k in KnowledgeUpdateSource.__dataclass_fields__
                    })
                    self.add_source(source)

            documents = import_data.get("documents", [])
            for doc in documents:
                try:
                    if hasattr(self.knowledge_engine, "ingest_document"):
                        self.knowledge_engine.ingest_document(doc)
                    elif hasattr(self.knowledge_engine, "add_document"):
                        self.knowledge_engine.add_document(doc)
                    result["documents_imported"] += 1
                except Exception as e:
                    result["errors"].append(str(e))

            result["success"] = result["documents_imported"] > 0 or len(documents) == 0
            result["total_documents"] = len(documents)
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Knowledge import failed: {e}")

        return result


_update_manager_instance: Optional[KnowledgeUpdateManager] = None


def get_update_manager(knowledge_engine=None) -> KnowledgeUpdateManager:
    global _update_manager_instance
    if _update_manager_instance is None:
        if knowledge_engine is None:
            raise ValueError("knowledge_engine must be provided on first call")
        _update_manager_instance = KnowledgeUpdateManager(knowledge_engine)
    return _update_manager_instance
