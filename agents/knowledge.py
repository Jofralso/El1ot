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

        if not self._engine:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content="Knowledge engine not yet initialized. Please start the knowledge service to enable search.",
                message_type="knowledge_response",
                metadata={"query": query, "engine_status": "not_initialized"},
            )

        results = await self._engine.search(query, top_k=5)

        if results:
            context_chunks = "\n".join(
                f"[{r.get('source', 'unknown')}] {r.get('text', '')[:400]}"
                for r in results
            )
            llm_answer = await self._llm_generate(
                prompt=(
                    f"Answer the user's question using ONLY the provided knowledge base context. "
                    f"Cite specific sources. If the context doesn't contain enough info, say so.\n\n"
                    f"Question: {query}\n\n"
                    f"Knowledge base context:\n{context_chunks}"
                ),
                system_prompt=(
                    "You are the Knowledge agent for the ELIOT cybersecurity system. "
                    "Answer questions accurately using the provided knowledge base context. "
                    "Always cite sources. Be concise and actionable."
                ),
                max_tokens=1024,
                temperature=0.3,
            )
            if llm_answer:
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=llm_answer,
                    message_type="knowledge_response",
                    metadata={"query": query, "source": "llm", "results_count": len(results)},
                )

        content = self._format_results(results)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=content,
            message_type="knowledge_response",
            metadata={"query": query, "results": results, "source": "template"},
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
