#!/usr/bin/env python3
"""
ELIOT Knowledge Ingestion Script
Ingests security knowledge data into the knowledge engine.
Run: python3 scripts/ingest_knowledge.py
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.engine import KnowledgeEngine
from knowledge.ingestion import IngestionPipeline


KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge")


async def main():
    print(f"ELIOT Knowledge Ingestion")
    print(f"=" * 50)
    print(f"Knowledge directory: {KNOWLEDGE_DIR}")

    if not os.path.exists(KNOWLEDGE_DIR):
        print(f"ERROR: Knowledge directory not found: {KNOWLEDGE_DIR}")
        sys.exit(1)

    files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(('.md', '.txt', '.json', '.yaml', '.yml', '.csv'))]
    print(f"Found {len(files)} knowledge files:")
    for f in sorted(files):
        size = os.path.getsize(os.path.join(KNOWLEDGE_DIR, f))
        print(f"  - {f} ({size:,} bytes)")

    print(f"\nInitializing knowledge engine...")
    engine = KnowledgeEngine(
        persist_dir="./data/vectordb",
        chunk_size=512,
        chunk_overlap=64,
    )
    pipeline = IngestionPipeline(engine)

    total_chunks = 0
    start_time = time.time()

    for fname in sorted(files):
        fpath = os.path.join(KNOWLEDGE_DIR, fname)
        print(f"\nIngesting {fname}...")
        t0 = time.time()
        chunks = await pipeline.ingest_file(
            fpath,
            metadata={"category": fname.replace(".md", "").replace(".txt", "").replace(".json", "")}
        )
        elapsed = time.time() - t0
        print(f"  -> {chunks} chunks ingested in {elapsed:.1f}s")
        total_chunks += chunks

    elapsed_total = time.time() - start_time
    stats = engine.get_stats()

    print(f"\n{'=' * 50}")
    print(f"Ingestion complete!")
    print(f"  Files processed: {len(files)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Documents in store: {stats['total_documents']}")
    print(f"  Embedding dimensions: {stats['embedding_dimensions']}")
    print(f"  Time elapsed: {elapsed_total:.1f}s")

    print(f"\nTesting semantic search...")
    test_queries = [
        "SQL injection prevention",
        "how to detect XSS vulnerabilities",
        "Linux SSH hardening",
        "phishing attack detection",
        "container security best practices",
    ]
    for query in test_queries:
        results = await engine.search(query, top_k=2)
        if results:
            top = results[0]
            print(f"  Q: {query}")
            print(f"  A: [{top['source']}] {top['text'][:120]}... (score: {top['score']:.3f})")
        else:
            print(f"  Q: {query}")
            print(f"  A: No results")
        print()

    print(f"Knowledge base ready for agent use!")


if __name__ == "__main__":
    asyncio.run(main())
