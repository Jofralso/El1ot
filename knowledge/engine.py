"""
ELIOT Knowledge Engine

Offline-capable cybersecurity knowledge system:
- Document ingestion (MITRE ATT&CK, CWE, CVE, OWASP, custom notes)
- Text chunking
- Embedding generation (nomic-embed-text via llama.cpp or sentence-transformers)
- Vector storage (ChromaDB)
- Semantic search
- Agent context retrieval

Pipeline: Documents -> Parser -> Chunking -> Embeddings -> VectorDB -> Search -> Agent Context
"""

import os
import time
import uuid
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Document:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    chunk_index: int = 0
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    document: Document
    score: float = 0.0


class TextChunker:
    """Split documents into overlapping chunks for embedding."""

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        metadata = metadata or {}
        words = text.split()
        chunks = []

        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(Document(
                content=chunk_text,
                metadata=metadata,
                source=metadata.get("source", "unknown"),
                chunk_index=len(chunks),
            ))
            start += self.chunk_size - self.overlap

        return chunks


class EmbeddingEngine:
    """Generate embeddings for text. Uses sentence-transformers as fallback when llama.cpp is unavailable."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model = None
        self._model_name = model_name
        self._dimensions = 384

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._dimensions = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self._model_name} (dim={self._dimensions})")
        except ImportError:
            logger.warning("sentence-transformers not installed, using hash-based embeddings")
            self._model = "hash"

    def embed(self, text: str) -> List[float]:
        self._load_model()
        if self._model == "hash":
            return self._hash_embed(text)
        return self._model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if self._model == "hash":
            return [self._hash_embed(t) for t in texts]
        return self._model.encode(texts).tolist()

    def _hash_embed(self, text: str) -> List[float]:
        import hashlib
        h = hashlib.sha256(text.lower().encode()).digest()
        vec = [((b - 128) / 128.0) for b in h]
        while len(vec) < self._dimensions:
            vec.extend(vec[:min(32, self._dimensions - len(vec))])
        return vec[:self._dimensions]

    @property
    def dimensions(self) -> int:
        return self._dimensions


class VectorStore:
    """Simple in-memory vector store with cosine similarity.
    Switches to ChromaDB if available."""

    def __init__(self, persist_dir: str = "./data/vectordb"):
        self._persist_dir = persist_dir
        self._documents: List[Document] = []
        self._chroma = None
        self._collection = None
        self._use_chroma = False

    def _init_chroma(self):
        if self._chroma is not None:
            return
        try:
            import chromadb
            os.makedirs(self._persist_dir, exist_ok=True)
            self._chroma = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._chroma.get_or_create_collection(
                name="eliot_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chroma = True
            logger.info(f"ChromaDB initialized at {self._persist_dir}")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}), using in-memory store")

    def add(self, documents: List[Document]):
        self._init_chroma()
        if self._use_chroma and self._collection:
            batch_ids = [d.id for d in documents]
            batch_docs = [d.content for d in documents]
            batch_meta = [d.metadata for d in documents]
            batch_embs = [d.embedding for d in documents if d.embedding]
            if batch_embs and len(batch_embs) == len(batch_ids):
                self._collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_meta,
                    embeddings=batch_embs,
                )
        else:
            self._documents.extend(documents)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[SearchResult]:
        self._init_chroma()
        if self._use_chroma and self._collection:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, max(self._collection.count(), 1)),
            )
            out = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    dist = results["distances"][0][i] if results["distances"] else 0
                    score = 1.0 - dist
                    out.append(SearchResult(
                        document=Document(
                            content=doc,
                            metadata=meta,
                            source=meta.get("source", "unknown"),
                        ),
                        score=score,
                    ))
            return out
        else:
            return self._cosine_search(query_embedding, top_k)

    def _cosine_search(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        import math

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0

        scored = []
        for doc in self._documents:
            if doc.embedding:
                score = cosine(query_embedding, doc.embedding)
                scored.append(SearchResult(document=doc, score=score))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        if self._use_chroma and self._collection:
            return self._collection.count()
        return len(self._documents)

    def clear(self):
        if self._use_chroma and self._collection:
            self._chroma.delete_collection("eliot_knowledge")
            self._collection = self._chroma.get_or_create_collection(
                name="eliot_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
        self._documents.clear()


class KnowledgeEngine:
    """
    Main knowledge engine. Orchestrates ingestion, embedding, storage, and search.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        persist_dir: str = "./data/vectordb",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ):
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=chunk_overlap)
        self.embedder = EmbeddingEngine(model_name=embedding_model)
        self.store = VectorStore(persist_dir=persist_dir)
        self._ingestion_count = 0

    async def ingest(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        source: str = "unknown",
    ) -> int:
        metadata = metadata or {}
        metadata["source"] = source
        metadata["ingested_at"] = time.time()

        chunks = self.chunker.chunk(text, metadata)
        for chunk in chunks:
            chunk.embedding = self.embedder.embed(chunk.content)

        self.store.add(chunks)
        self._ingestion_count += len(chunks)
        logger.info(f"Ingested {len(chunks)} chunks from '{source}' (total: {self._ingestion_count})")
        return len(chunks)

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedder.embed(query)
        results = self.store.search(query_embedding, top_k)
        return [
            {
                "text": r.document.content,
                "score": r.score,
                "source": r.document.source,
                "metadata": r.document.metadata,
            }
            for r in results
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": self.store.count(),
            "total_ingested": self._ingestion_count,
            "embedding_dimensions": self.embedder.dimensions,
        }


# Global knowledge engine instance (lazy init)
_knowledge_engine: Optional[KnowledgeEngine] = None


def get_knowledge_engine() -> KnowledgeEngine:
    global _knowledge_engine
    if _knowledge_engine is None:
        from core.config import settings
        _knowledge_engine = KnowledgeEngine(
            persist_dir=settings.vectordb_path,
        )
    return _knowledge_engine
