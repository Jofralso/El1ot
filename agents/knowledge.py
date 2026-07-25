"""
Knowledge Agent

Queries local knowledge base, provides context, retrieves documentation.
"""

import logging
from typing import Any, Dict, Optional

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    def __init__(self, knowledge_engine: Optional[Any] = None):
        super().__init__(
            role=AgentRole.KNOWLEDGE,
            name="Knowledge",
            description="Queries the local knowledge base and retrieves documentation",
            permissions=["read", "knowledge_search"],
            tools=["vector_search", "document_retrieval"],
        )
        self._engine = knowledge_engine

    def set_engine(self, engine):
        self._engine = engine

    async def process(self, message: AgentMessage) -> AgentMessage:
        query = message.content
        context = message.metadata.get("context", {})

        if self._engine:
            results = await self._engine.search(query, top_k=5)
            content = self._format_results(results)
            metadata = {"results": results, "query": query}
        else:
            content = (
                "Knowledge engine not yet initialized. "
                "Please start the knowledge service to enable search."
            )
            metadata = {"query": query, "engine_status": "not_initialized"}

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=content,
            message_type="knowledge_response",
            metadata=metadata,
        )

    def _format_results(self, results: list) -> str:
        if not results:
            return "No relevant results found in the knowledge base."
        lines = ["Knowledge base results:"]
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            source = r.get("source", "unknown")
            text = r.get("text", "")[:200]
            lines.append(f"\n{i}. [{source}] (score: {score:.3f})")
            lines.append(f"   {text}...")
        return "\n".join(lines)
