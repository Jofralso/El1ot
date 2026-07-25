"""
Research Agent

Searches local vulnerability knowledge, CVE data, and security resources.
"""

import logging
from typing import Any, Dict, Optional

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    def __init__(self, knowledge_engine: Optional[Any] = None):
        super().__init__(
            role=AgentRole.RESEARCH,
            name="Research",
            description="Researches vulnerabilities, CVEs, and security topics from local knowledge",
            permissions=["read", "knowledge_search", "research"],
            tools=["vector_search", "cve_lookup", "security_db"],
        )
        self._engine = knowledge_engine

    def set_engine(self, engine):
        self._engine = engine

    async def process(self, message: AgentMessage) -> AgentMessage:
        query = message.content
        research = await self._research(query)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=research,
            message_type="research",
            metadata={"query": query, "source": "local_knowledge"},
        )

    async def _research(self, query: str) -> str:
        results = []
        if self._engine:
            results = await self._engine.search(query, top_k=10)

        lines = [
            f"=== Research: {query} ===",
            "",
        ]

        if results:
            lines.append(f"Found {len(results)} relevant resources in local knowledge base:")
            for i, r in enumerate(results, 1):
                score = r.get("score", 0)
                source = r.get("source", "unknown")
                text = r.get("text", "")[:300]
                category = r.get("metadata", {}).get("category", "general")
                lines.append(f"\n{i}. [{category}] {source} (relevance: {score:.3f})")
                lines.append(f"   {text}")
        else:
            lines.append("No local results found. The knowledge base may need to be populated.")
            lines.append("Try adding MITRE ATT&CK, CWE, or CVE data to the knowledge engine.")

        lines.extend([
            "",
            "=== Recommendation ===",
            "Consult the local knowledge base for authoritative information. "
            "All research should be validated before use in authorized assessments.",
        ])

        return "\n".join(lines)
