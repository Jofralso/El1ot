"""
Tests for the Knowledge Engine.
"""

import pytest
from knowledge.engine import KnowledgeEngine, TextChunker, EmbeddingEngine


@pytest.fixture
def engine():
    return KnowledgeEngine(
        embedding_model="all-MiniLM-L6-v2",
        chunk_size=100,
        chunk_overlap=10,
    )


class TestTextChunker:
    def test_chunk_basic(self):
        chunker = TextChunker(chunk_size=10, overlap=2)
        text = "word " * 50
        chunks = chunker.chunk(text.strip())
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.content.split()) <= 10

    def test_chunk_empty(self):
        chunker = TextChunker(chunk_size=10, overlap=2)
        chunks = chunker.chunk("")
        assert len(chunks) <= 1


class TestEmbeddingEngine:
    def test_embed_returns_vector(self):
        engine = EmbeddingEngine()
        vec = engine.embed("hello world")
        assert isinstance(vec, list)
        assert len(vec) == engine.dimensions

    def test_embed_batch(self):
        engine = EmbeddingEngine()
        vecs = engine.embed_batch(["hello", "world"])
        assert len(vecs) == 2
        assert len(vecs[0]) == engine.dimensions


class TestKnowledgeEngine:
    @pytest.mark.asyncio
    async def test_ingest_and_search(self, engine):
        chunks = await engine.ingest(
            "Buffer overflow is a memory safety vulnerability",
            source="test",
        )
        assert chunks > 0

        results = await engine.search("buffer overflow vulnerability", top_k=3)
        assert len(results) > 0
        assert results[0]["score"] > 0

    @pytest.mark.asyncio
    async def test_stats(self, engine):
        await engine.ingest("test document", source="test")
        stats = engine.get_stats()
        assert stats["total_documents"] > 0
        assert stats["embedding_dimensions"] > 0
