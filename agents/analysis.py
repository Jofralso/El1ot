"""
Analysis Agent

Analyzes collected information and produces summaries.
Uses pentest model for specialized security analysis when available.
"""

import logging
from typing import Any, Dict, Optional

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role=AgentRole.ANALYSIS,
            name="Analysis",
            description="Analyzes collected information and produces structured summaries",
            permissions=["read", "analyze"],
            tools=["text_analysis"],
        )
        self._pentest_model = None

    def _get_pentest_model(self):
        """Get pentest model name from config if available."""
        if self._pentest_model is None:
            try:
                from core.config import settings
                self._pentest_model = settings.pentest_model
            except Exception:
                self._pentest_model = False  # Mark as not available
        return self._pentest_model if self._pentest_model else None

    async def process(self, message: AgentMessage) -> AgentMessage:
        content = message.content
        
        # Use pentest model for security analysis if available
        pentest_model = self._get_pentest_model()

        llm_analysis = await self._llm_generate(
            prompt=(
                f"Analyze the following content and provide a structured security analysis. "
                f"Include: key findings, risks identified, severity assessment, and actionable recommendations.\n\n"
                f"Content:\n{content}"
            ),
            system_prompt=(
                "You are the Analysis agent for the ELIOT cybersecurity system. "
                "Provide thorough, structured analysis of security-related information. "
                "Be precise, identify risks, and give actionable recommendations."
            ),
            max_tokens=1024,
            temperature=0.3,
            model=pentest_model,
        )

        if llm_analysis:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=llm_analysis,
                message_type="analysis",
                metadata={"analysis_type": "llm", "input_length": len(content), "source": "llm", "model": pentest_model or "default"},
            )

        analysis = self._analyze(content)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=analysis,
            message_type="analysis",
            metadata={"analysis_type": "summary", "input_length": len(content), "source": "template"},
        )

    def _analyze(self, content: str) -> str:
        words = content.split()
        word_count = len(words)
        unique_words = len(set(w.lower() for w in words))

        lines = [
            "=== Analysis Report ===",
            "",
            f"Input size: {word_count} words, {len(content)} characters",
            f"Vocabulary diversity: {unique_words}/{word_count} unique words",
            "",
            "=== Key Findings ===",
        ]

        keywords = self._extract_keywords(content)
        if keywords:
            lines.append(f"Key terms: {', '.join(keywords[:10])}")

        sentences = [s.strip() for s in content.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        if sentences:
            lines.append(f"Sentences: {len(sentences)}")
            lines.append(f"Average sentence length: {sum(len(s.split()) for s in sentences) / max(len(sentences), 1):.1f} words")

        lines.extend([
            "",
            "=== Summary ===",
            f"The provided content contains {word_count} words covering topics related to: {', '.join(keywords[:5]) if keywords else 'general information'}.",
        ])

        return "\n".join(lines)

    def _extract_keywords(self, text: str) -> list:
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "and", "but", "or",
            "not", "no", "nor", "so", "yet", "both", "each", "few", "more",
            "most", "other", "some", "such", "than", "too", "very", "just",
            "that", "this", "these", "those", "it", "its", "he", "she", "they",
            "we", "you", "i", "me", "my", "your", "his", "her", "their", "our",
            "what", "which", "who", "whom", "when", "where", "how", "all",
        }
        words = [
            w.lower().strip(".,;:!?\"'()-")
            for w in text.split()
            if len(w) > 3
        ]
        freq: Dict[str, int] = {}
        for w in words:
            if w and w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])]
