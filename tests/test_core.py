"""
Unit tests for ELIOT Core Service

Phase 2: Foundation + Agents + Knowledge + Tools + Security
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from core.main import app
from core.config import settings


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


# ── Health Endpoints ─────────────────────────────────────────

class TestHealthEndpoints:
    def test_health_check(self, client):
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "services" in data

    def test_health_detailed(self, client):
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "hardware" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


# ── System Endpoints ─────────────────────────────────────────

class TestSystemEndpoints:
    def test_metrics_endpoint(self, client):
        response = client.get("/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "disk_percent" in data

    def test_info_endpoint(self, client):
        response = client.get("/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "hardware" in data
        assert "metrics" in data

    def test_readiness_probe(self, client):
        response = client.get("/system/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


# ── Configuration ────────────────────────────────────────────

class TestConfiguration:
    def test_settings_loaded(self):
        assert settings.core_host == "0.0.0.0"
        assert settings.core_port == 8000

    def test_redis_url(self):
        from core.deps import get_redis_url
        url = get_redis_url()
        assert "redis://" in url
        assert "6379" in url


# ── Hardware Detection ───────────────────────────────────────

class TestHardwareDetection:
    def test_hardware_detection(self):
        from core.hardware import detect_hardware
        hardware = detect_hardware()
        assert "target" in hardware
        assert "cpu_count" in hardware
        assert hardware["cpu_count"] > 0
        assert "memory_gb" in hardware
        assert hardware["memory_gb"] > 0

    def test_cuda_detection(self):
        from core.hardware import _detect_cuda
        result = _detect_cuda()
        assert isinstance(result, bool)


# ── Prometheus Metrics ───────────────────────────────────────

class TestMetrics:
    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "eliot_requests_total" in response.text or "eliot_app_info" in response.text


# ── Agent System ─────────────────────────────────────────────

class TestAgentSystem:
    def test_list_agents(self, client):
        response = client.get("/agents/")
        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, list)
        assert len(agents) >= 7
        names = [a["name"] for a in agents]
        assert "Planner" in names
        assert "Knowledge" in names
        assert "Analysis" in names
        assert "Research" in names
        assert "Code" in names
        assert "Documentation" in names

    def test_chat_with_supervisor(self, client):
        response = client.post("/agents/chat", json={"message": "hello"})
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "sender" in data

    def test_chat_to_specific_agent(self, client):
        response = client.post("/agents/chat", json={
            "message": "create a plan for network scanning",
            "agent": "Planner",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["message_type"] == "plan"

    def test_chat_to_code_agent(self, client):
        response = client.post("/agents/chat", json={
            "message": "generate a port scanning script",
            "agent": "Code",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["message_type"] == "code"

    def test_chat_to_analysis_agent(self, client):
        response = client.post("/agents/chat", json={
            "message": "analyze this text for keywords",
            "agent": "Analysis",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["message_type"] == "analysis"

    def test_get_agent_status(self, client):
        response = client.get("/agents/Planner")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Planner"
        assert "state" in data

    def test_unknown_agent(self, client):
        response = client.get("/agents/NonExistent")
        assert response.status_code == 404


# ── Knowledge System ─────────────────────────────────────────

class TestKnowledgeSystem:
    def test_knowledge_stats(self, client):
        response = client.get("/knowledge/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "embedding_dimensions" in data

    def test_ingest_text(self, client):
        response = client.post("/knowledge/ingest", json={
            "text": "MITRE ATT&CK T1059 Command and Scripting Interpreter",
            "source": "test",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["chunks_ingested"] > 0

    def test_search_after_ingest(self, client):
        client.post("/knowledge/ingest", json={
            "text": "Buffer overflow vulnerability in web application allows remote code execution",
            "source": "cve-test",
        })
        response = client.post("/knowledge/search", json={
            "query": "buffer overflow vulnerability",
            "top_k": 3,
        })
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# ── Tool System ──────────────────────────────────────────────

class TestToolSystem:
    def test_list_tools(self, client):
        response = client.get("/tools/")
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) >= 5
        names = [t["name"] for t in tools]
        assert "system_info" in names
        assert "process_list" in names

    def test_execute_system_info(self, client):
        response = client.post("/tools/system_info/execute", json={
            "params": {},
            "user_permissions": ["admin"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cpu_percent" in data["output"]

    def test_execute_process_list(self, client):
        response = client.post("/tools/process_list/execute", json={
            "params": {"top_n": 5},
            "user_permissions": ["admin"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_execute_unknown_tool(self, client):
        response = client.post("/tools/nonexistent/execute", json={
            "params": {},
            "user_permissions": ["admin"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_tool_audit_log(self, client):
        client.post("/tools/system_info/execute", json={
            "params": {},
            "user_permissions": ["admin"],
        })
        response = client.get("/tools/audit")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data


# ── UI ───────────────────────────────────────────────────────

class TestUI:
    def test_ui_home(self, client):
        response = client.get("/ui/")
        assert response.status_code == 200
        assert "ELIOT" in response.text
        assert "Chat" in response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
