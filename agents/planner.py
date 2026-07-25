"""
Planner Agent

Understands user goals, creates workflows, coordinates multi-step tasks.
"""

import logging
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role=AgentRole.PLANNER,
            name="Planner",
            description="Creates workflows and coordinates multi-step tasks",
            permissions=["read", "plan"],
            tools=["task_manager"],
        )

    async def process(self, message: AgentMessage) -> AgentMessage:
        llm_plan = await self._llm_generate(
            prompt=(
                f"Create an execution plan for the following goal. "
                f"Return a JSON object with keys: goal (string), steps (list of objects with step number, action, description), "
                f"required_agents (list of agent name strings).\n\n"
                f"Available agents: Planner, Analysis, Research, Code, Documentation, Knowledge, Voice, Vision\n\n"
                f"Goal: {message.content}"
            ),
            system_prompt=(
                "You are the Planner agent for the ELIOT cybersecurity system. "
                "Create detailed, actionable execution plans for security-related tasks. "
                "Always return valid JSON only, no markdown formatting."
            ),
            max_tokens=1024,
            temperature=0.3,
        )

        if llm_plan:
            import json
            try:
                plan = json.loads(llm_plan.strip().removeprefix("```json").removesuffix("```").strip())
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=self._format_plan(plan),
                    message_type="plan",
                    metadata={"plan": plan, "source": "llm"},
                )
            except (json.JSONDecodeError, KeyError):
                pass

        plan = self._create_plan(message.content)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=self._format_plan(plan),
            message_type="plan",
            metadata={"plan": plan, "source": "template"},
        )

    def _create_plan(self, goal: str) -> Dict[str, Any]:
        steps = []
        goal_lower = goal.lower()

        if any(kw in goal_lower for kw in ["scan", "network", "nmap"]):
            steps = [
                {"step": 1, "action": "target_approval", "description": "Verify target is whitelisted"},
                {"step": 2, "action": "network_discovery", "description": "Discover hosts and ports"},
                {"step": 3, "action": "service_enumeration", "description": "Identify running services"},
                {"step": 4, "action": "analysis", "description": "Analyze findings"},
                {"step": 5, "action": "report", "description": "Generate report"},
            ]
        elif any(kw in goal_lower for kw in ["research", "vulnerability", "cve"]):
            steps = [
                {"step": 1, "action": "knowledge_search", "description": "Search local knowledge base"},
                {"step": 2, "action": "gather_context", "description": "Collect relevant context"},
                {"step": 3, "action": "analysis", "description": "Analyze vulnerability data"},
                {"step": 4, "action": "report", "description": "Summarize findings"},
            ]
        elif any(kw in goal_lower for kw in ["document", "report", "wiki"]):
            steps = [
                {"step": 1, "action": "gather_data", "description": "Collect information to document"},
                {"step": 2, "action": "structure", "description": "Structure the document"},
                {"step": 3, "action": "write", "description": "Generate documentation"},
                {"step": 4, "action": "review", "description": "Review and finalize"},
            ]
        else:
            steps = [
                {"step": 1, "action": "understand", "description": "Clarify the goal"},
                {"step": 2, "action": "plan", "description": "Create execution plan"},
                {"step": 3, "action": "execute", "description": "Execute the plan"},
                {"step": 4, "action": "verify", "description": "Verify results"},
            ]

        return {
            "goal": goal,
            "estimated_steps": len(steps),
            "steps": steps,
            "required_agents": self._infer_agents(goal_lower),
        }

    def _infer_agents(self, goal_lower: str) -> List[str]:
        agents = []
        if "scan" in goal_lower or "network" in goal_lower:
            agents.append("Research")
        if "knowledge" in goal_lower or "search" in goal_lower:
            agents.append("Knowledge")
        if "code" in goal_lower or "script" in goal_lower:
            agents.append("Code")
        if "document" in goal_lower or "report" in goal_lower:
            agents.append("Documentation")
        agents.append("Analysis")
        return agents

    def _format_plan(self, plan: Dict[str, Any]) -> str:
        lines = [f"Plan for: {plan['goal']}", ""]
        for step in plan["steps"]:
            lines.append(f"  {step['step']}. [{step['action']}] {step['description']}")
        lines.append(f"\nRequired agents: {', '.join(plan['required_agents'])}")
        return "\n".join(lines)
