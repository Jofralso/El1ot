"""
Knowledge ingestion pipeline.

Parses documents from various formats and feeds them into the knowledge engine.
"""

import os
import re
import time
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse various document formats into plain text."""

    @staticmethod
    def parse(path: str) -> Optional[str]:
        ext = Path(path).suffix.lower()
        try:
            if ext == ".md":
                return DocumentParser._parse_markdown(path)
            elif ext == ".txt":
                return DocumentParser._parse_text(path)
            elif ext == ".json":
                return DocumentParser._parse_json(path)
            elif ext == ".yaml" or ext == ".yml":
                return DocumentParser._parse_yaml(path)
            elif ext == ".csv":
                return DocumentParser._parse_csv(path)
            elif ext == ".xml":
                return DocumentParser._parse_xml(path)
            else:
                return DocumentParser._parse_text(path)
        except Exception as e:
            logger.error(f"Failed to parse {path}: {e}")
            return None

    @staticmethod
    def _parse_markdown(path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _parse_text(path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _parse_json(path: str) -> str:
        import json
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)

    @staticmethod
    def _parse_yaml(path: str) -> str:
        try:
            import yaml
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                data = yaml.safe_load(f)
            import json
            return json.dumps(data, indent=2, default=str)
        except ImportError:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    @staticmethod
    def _parse_csv(path: str) -> str:
        import csv
        lines = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                lines.append(" | ".join(row))
        return "\n".join(lines)

    @staticmethod
    def _parse_xml(path: str) -> str:
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        return ET.tostring(root, encoding="unicode", method="text")


class IngestionPipeline:
    """
    Full ingestion pipeline: scan -> parse -> chunk -> embed -> store.
    """

    def __init__(self, knowledge_engine):
        self.engine = knowledge_engine
        self.parser = DocumentParser()

    async def ingest_file(self, path: str, metadata: Dict[str, Any] = None) -> int:
        text = self.parser.parse(path)
        if not text:
            return 0
        meta = metadata or {}
        meta["file_path"] = path
        meta["file_name"] = os.path.basename(path)
        return await self.engine.ingest(text, meta, source=os.path.basename(path))

    async def ingest_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> int:
        extensions = extensions or [".md", ".txt", ".json", ".yaml", ".yml", ".csv"]
        total_chunks = 0

        if recursive:
            for root, dirs, files in os.walk(directory):
                for fname in files:
                    if any(fname.endswith(ext) for ext in extensions):
                        path = os.path.join(root, fname)
                        chunks = await self.ingest_file(path)
                        total_chunks += chunks
        else:
            for fname in os.listdir(directory):
                path = os.path.join(directory, fname)
                if os.path.isfile(path) and any(fname.endswith(ext) for ext in extensions):
                    chunks = await self.ingest_file(path)
                    total_chunks += chunks

        logger.info(f"Directory ingestion complete: {total_chunks} chunks from {directory}")
        return total_chunks

    async def ingest_text(
        self,
        text: str,
        source: str = "manual",
        metadata: Dict[str, Any] = None,
    ) -> int:
        return await self.engine.ingest(text, metadata, source)
