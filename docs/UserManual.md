# User Manual

## Getting Started

### First Boot

1. Power on the ELIOT device
2. Wait for boot sequence (avatar will show BOOTING state)
3. Touch the screen to begin setup
4. Register as Owner (face + voice)
5. Start using ELIOT

### Voice Commands

Say "Hey ELIOT" to activate, then:

- "Scan the network" - Start network discovery
- "Search for CVEs" - Query knowledge base
- "Generate a report" - Create documentation
- "What's the system status?" - Check hardware
- "Analyze these findings" - Run analysis

### Touch Interface

Pages:

- **Home** - Avatar, status, current task
- **Dashboard** - CPU, GPU, RAM, temperature
- **Knowledge** - Search indexed documents
- **Timeline** - Events and discoveries
- **Chat** - Text conversation
- **Reports** - Generated documentation

## Agent Commands

| Command | Agent | Description |
|---------|-------|-------------|
| "Create a plan..." | Planner | Workflow creation |
| "Search for..." | Knowledge | Knowledge base query |
| "Analyze..." | Analysis | Data analysis |
| "Research..." | Research | Vulnerability research |
| "Write a script..." | Code | Code generation |
| "Document..." | Documentation | Report creation |

## Target Management

Before scanning any target:

1. Go to Security settings
2. Add target IP/hostname
3. Approve the target
4. ELIOT will now allow operations against it

## Reports

ELIOT generates reports in Markdown format:

- Security assessment reports
- Vulnerability summaries
- Network topology documents
- Analysis summaries

Reports are stored in `data/reports/` and accessible via the UI.
