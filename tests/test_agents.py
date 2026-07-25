"""
Tests for the Agent Framework.
"""

import pytest
from agents.base import BaseAgent, AgentRole, AgentState, AgentMessage
from agents.supervisor import SupervisorAgent
from agents.planner import PlannerAgent
from agents.analysis import AnalysisAgent
from agents.code import CodeAgent
from agents.documentation import DocumentationAgent


@pytest.fixture
def supervisor():
    sup = SupervisorAgent()
    sup.register_agent(PlannerAgent())
    sup.register_agent(AnalysisAgent())
    sup.register_agent(CodeAgent())
    sup.register_agent(DocumentationAgent())
    return sup


class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_planner_processes_message(self):
        agent = PlannerAgent()
        msg = AgentMessage(sender="test", content="scan the network 192.168.1.0/24")
        response = await agent.handle(msg)
        assert response.message_type == "plan"
        assert "scan" in response.content.lower() or "192.168" in response.content

    @pytest.mark.asyncio
    async def test_analysis_processes_message(self):
        agent = AnalysisAgent()
        msg = AgentMessage(sender="test", content="This is a test analysis of security vulnerabilities")
        response = await agent.handle(msg)
        assert response.message_type == "analysis"
        assert "Analysis Report" in response.content

    @pytest.mark.asyncio
    async def test_code_generates_script(self):
        agent = CodeAgent()
        msg = AgentMessage(sender="test", content="generate a port scanning script")
        response = await agent.handle(msg)
        assert response.message_type == "code"
        assert "python" in response.content.lower() or "socket" in response.content.lower()

    def test_agent_status(self):
        agent = PlannerAgent()
        status = agent.get_status()
        assert status["name"] == "Planner"
        assert status["role"] == "planner"
        assert status["state"] == "idle"


class TestSupervisor:
    @pytest.mark.asyncio
    async def test_route_to_planner(self, supervisor):
        msg = AgentMessage(sender="user", content="create a plan for this task")
        response = await supervisor.handle(msg)
        assert response.sender == "Planner"

    @pytest.mark.asyncio
    async def test_route_to_code(self, supervisor):
        msg = AgentMessage(sender="user", content="write a script to scan ports")
        response = await supervisor.handle(msg)
        assert response.sender == "Code"

    @pytest.mark.asyncio
    async def test_route_to_analysis(self, supervisor):
        msg = AgentMessage(sender="user", content="analyze these findings")
        response = await supervisor.handle(msg)
        assert "Analysis" in response.sender or response.message_type == "analysis"

    @pytest.mark.asyncio
    async def test_explicit_agent_routing(self, supervisor):
        msg = AgentMessage(sender="user", receiver="Code", content="generate a hash script")
        response = await supervisor.handle(msg)
        assert response.sender == "Code"

    def test_list_agents(self, supervisor):
        agents = supervisor.list_agents()
        names = [a["name"] for a in agents]
        assert "Planner" in names
        assert "Code" in names

    @pytest.mark.asyncio
    async def test_unknown_agent(self, supervisor):
        msg = AgentMessage(sender="user", content="hello")
        response = await supervisor.handle(msg)
        assert "available" in response.content.lower() or "error" in response.message_type
