# API Reference

Base URL: `http://localhost:8000`

## Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Basic health check |
| GET | `/health/detailed` | Hardware + uptime info |

## System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/system/metrics` | CPU, memory, disk usage |
| GET | `/system/info` | Hardware + metrics |
| GET | `/system/ready` | Readiness probe |
| GET | `/metrics` | Prometheus metrics |

## Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/` | List all agents |
| GET | `/agents/{name}` | Agent status |
| POST | `/agents/chat` | Chat with agent system |
| POST | `/agents/workflow/{name}` | Execute workflow |

### POST /agents/chat

```json
{
  "message": "create a plan for network scanning",
  "agent": "Planner",
  "user_id": "owner",
  "metadata": {}
}
```

Response:
```json
{
  "sender": "Planner",
  "content": "Plan for: ...",
  "message_type": "plan",
  "metadata": {"plan": {...}}
}
```

Available agents: `ELIOT CORE`, `Planner`, `Knowledge`, `Analysis`, `Research`, `Code`, `Documentation`, `Voice`, `Vision`

## Knowledge

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/knowledge/search` | Semantic search |
| POST | `/knowledge/ingest` | Ingest text |
| POST | `/knowledge/ingest/directory` | Ingest directory |
| GET | `/knowledge/stats` | Engine statistics |

### POST /knowledge/search

```json
{
  "query": "buffer overflow vulnerability",
  "top_k": 5
}
```

## Tools

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tools/` | List all tools |
| POST | `/tools/{name}/execute` | Execute tool |
| GET | `/tools/audit` | Audit log |

Built-in tools: `system_info`, `process_list`, `read_file`, `list_directory`, `network_connections`, `network_interfaces`

## UI

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ui/` | Touch interface |
