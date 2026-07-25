"""
Knowledge API Routes

Endpoints for querying and ingesting knowledge.
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from knowledge.engine import get_knowledge_engine
from knowledge.ingestion import IngestionPipeline

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResultItem(BaseModel):
    text: str
    score: float
    source: str
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int


class IngestTextRequest(BaseModel):
    text: str
    source: str = "manual"
    metadata: Dict[str, Any] = {}


class IngestResponse(BaseModel):
    chunks_ingested: int
    source: str


class StatsResponse(BaseModel):
    total_documents: int
    total_ingested: int
    embedding_dimensions: int


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search the knowledge base using semantic similarity."""
    engine = get_knowledge_engine()
    results = await engine.search(request.query, top_k=request.top_k)
    return SearchResponse(
        query=request.query,
        results=[
            SearchResultItem(
                text=r["text"],
                score=r["score"],
                source=r["source"],
                metadata=r.get("metadata", {}),
            )
            for r in results
        ],
        total=len(results),
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_text(request: IngestTextRequest):
    """Ingest text into the knowledge base."""
    engine = get_knowledge_engine()
    chunks = await engine.ingest(request.text, request.metadata, request.source)
    return IngestResponse(chunks_ingested=chunks, source=request.source)


@router.post("/ingest/directory", response_model=IngestResponse)
async def ingest_directory(path: str = "./docs"):
    """Ingest all supported files from a directory."""
    engine = get_knowledge_engine()
    pipeline = IngestionPipeline(engine)
    chunks = await pipeline.ingest_directory(path)
    return IngestResponse(chunks_ingested=chunks, source=path)


@router.get("/stats", response_model=StatsResponse)
async def knowledge_stats():
    """Get knowledge engine statistics."""
    engine = get_knowledge_engine()
    stats = engine.get_stats()
    return StatsResponse(**stats)
