"""
Supervisor Agent

Central orchestrator that routes messages to specialist agents.
Maintains global task state and coordinates multi-agent workflows.
"""

import logging
from typing import Dict, List, Optional

from agents.base import BaseAgent, AgentRole, AgentState, AgentMessage

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    The ELIOT CORE supervisor.
    Receives user requests, decides which agents to invoke, coordinates responses.
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.SUPERVISOR,
            name="ELIOT CORE",
            description="Central orchestrator for all ELIOT agent operations",
            permissions=["admin"],
        )
        self._agents: Dict[str, BaseAgent] = {}
        self._workflows: Dict[str, List[str]] = {}

    def register_agent(self, agent: BaseAgent):
        """Register a specialist agent."""
        self._agents[agent.name] = agent
        logger.info(f"Supervisor registered agent: {agent.name}")

    def unregister_agent(self, name: str):
        self._agents.pop(name, None)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def list_agents(self) -> List[Dict]:
        return [a.get_status() for a in self._agents.values()]

    def define_workflow(self, name: str, agent_sequence: List[str]):
        """Define a multi-agent workflow (ordered list of agent names)."""
        self._workflows[name] = agent_sequence
        logger.info(f"Workflow defined: {name} -> {agent_sequence}")

    async def execute_workflow(self, workflow_name: str, initial_message: AgentMessage) -> AgentMessage:
        """Execute a predefined workflow by passing messages through agents in order."""
        sequence = self._workflows.get(workflow_name)
        if not sequence:
            return AgentMessage(
                sender=self.name,
                receiver=initial_message.sender,
                content=f"Unknown workflow: {workflow_name}",
                message_type="error",
            )

        current_message = initial_message
        for agent_name in sequence:
            agent = self._agents.get(agent_name)
            if not agent:
                logger.warning(f"Workflow {workflow_name}: agent {agent_name} not found, skipping")
                continue
            current_message = await agent.handle(current_message)

        return current_message

    async def process(self, message: AgentMessage) -> AgentMessage:
        """Route incoming request to appropriate agent(s)."""
        content = message.content.lower()

        target_agent = self._resolve_target(content)

        if target_agent:
            agent = self._agents.get(target_agent)
            if agent:
                logger.info(f"Supervisor routing to: {target_agent}")
                return await agent.handle(message)

        if any(kw in content for kw in ["analyze", "summary", "report findings"]):
            return await self._route_to("Analysis", message)
        if any(kw in content for kw in ["search for", "find info", "lookup", "knowledge", "query"]):
            return await self._route_to("Knowledge", message)
        if any(kw in content for kw in ["plan", "workflow", "steps", "organize"]):
            return await self._route_to("Planner", message)
        if any(kw in content for kw in ["research", "vulnerability", "cve", "exploit"]):
            return await self._route_to("Research", message)
        if any(kw in content for kw in ["code", "script", "generate", "write a"]):
            return await self._route_to("Code", message)
        if any(kw in content for kw in ["document", "wiki", "readme", "create a report"]):
            return await self._route_to("Documentation", message)

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=(
                f"I received your request. Available agents: "
                f"{', '.join(self._agents.keys())}. "
                f"Please specify which agent should handle this, or rephrase."
            ),
            message_type="text",
            metadata={"available_agents": list(self._agents.keys())},
        )

    def _resolve_target(self, content: str) -> Optional[str]:
        for name, agent in self._agents.items():
            if name.lower() in content:
                return name
        return None

    async def _route_to(self, agent_name: str, message: AgentMessage) -> AgentMessage:
        agent = self._agents.get(agent_name)
        if agent:
            return await agent.handle(message)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=f"Agent '{agent_name}' is not available.",
            message_type="error",
        )
