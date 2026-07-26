"""
Supervisor Agent

Central orchestrator that routes messages to specialist agents.
Maintains global task state and coordinates multi-agent workflows.
Improved: Context-aware routing, follows recent agent interactions.
"""

import logging
import time
from typing import Any, Dict, List, Optional

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
        self._recent_agent: Optional[str] = None  # Track which agent was recently used
        self._recent_agent_time: float = 0
        self._context_timeout = 300  # 5 minutes context window

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

    async def execute_pentest_workflow(self, target: str, initial_message: AgentMessage) -> AgentMessage:
        """
        Execute a full pentest workflow on a target:
        1. Recon: Shell discovers network/devices
        2. Scan: Shell runs nmap service scan on target
        3. Web scan: Shell scans HTTP ports with nikto
        4. Analyze: Analysis agent processes findings
        5. Exploit: Shell runs targeted exploits based on findings
        6. Report: Documentation agent generates report
        """
        results = []
        shell = self._agents.get("Shell")
        analysis = self._agents.get("Analysis")
        docs = self._agents.get("Documentation")
        
        if not shell:
            return AgentMessage(
                sender=self.name, receiver=initial_message.sender,
                content="Shell agent not available for pentest workflow.",
                message_type="error",
            )
        
        # Track context so follow-ups route to Shell
        self._recent_agent = "Shell"
        self._recent_agent_time = time.time()
        
        # Step 1: Recon
        recon_msg = AgentMessage(
            sender="supervisor", receiver="Shell",
            content=f"!nmap -sn {target}/24 2>/dev/null | grep -E 'Nmap scan report|Host is up'",
            metadata={"workflow_step": "recon", "target": target},
        )
        recon_result = await shell.handle(recon_msg)
        results.append(("RECON", recon_result))
        
        # Step 2: Service scan
        scan_msg = AgentMessage(
            sender="supervisor", receiver="Shell",
            content=f"!nmap -sV -sC --version-intensity 5 {target}",
            metadata={"workflow_step": "service_scan", "target": target},
        )
        scan_result = await shell.handle(scan_msg)
        results.append(("SERVICE_SCAN", scan_result))
        
        # Step 3: Web scan if HTTP ports found
        scan_output = scan_result.metadata.get("stdout", "")
        web_ports = []
        for line in scan_output.split("\n"):
            if "/tcp" in line and ("http" in line.lower() or "www" in line.lower()):
                port = line.split("/")[0].strip()
                web_ports.append(port)
        
        for port in web_ports[:3]:  # Limit to 3 web ports
            web_msg = AgentMessage(
                sender="supervisor", receiver="Shell",
                content=f"!nikto -h http://{target}:{port}/ -maxtime 60s 2>/dev/null | head -50",
                metadata={"workflow_step": "web_scan", "target": target, "port": port},
            )
            web_result = await shell.handle(web_msg)
            results.append((f"WEB_SCAN_{port}", web_result))
        
        # Step 4: Analyze all findings
        all_findings = "\n\n".join([
            f"=== {step} ===\n{r.content[:1500]}" for step, r in results
        ])
        
        analysis_text = ""
        if analysis:
            analyze_msg = AgentMessage(
                sender="supervisor", receiver="Analysis",
                content=(
                    f"Perform a complete vulnerability analysis of target {target} based on these scan results:\n\n"
                    f"{all_findings[:5000]}\n\n"
                    f"Provide:\n"
                    f"1. Prioritized list of vulnerabilities (CRITICAL/HIGH/MEDIUM/LOW)\n"
                    f"2. For each: CWE ID, OWASP category, risk description\n"
                    f"3. Specific exploitation commands (full shell commands with flags, ready to execute)\n"
                    f"4. Remediation recommendations"
                ),
                metadata={"workflow_step": "analysis", "target": target},
            )
            analysis_result = await analysis.handle(analyze_msg)
            analysis_text = analysis_result.content
            results.append(("ANALYSIS", analysis_result))
        
        # Step 5: Generate and execute exploit commands based on analysis
        exploit_cmds = await self._generate_exploit_commands(target, analysis_text)
        
        exploit_results = []
        for cmd in exploit_cmds:
            exploit_msg = AgentMessage(
                sender="supervisor", receiver="Shell",
                content=f"!{cmd}",
                metadata={"workflow_step": "exploit", "target": target},
            )
            exploit_result = await shell.handle(exploit_msg)
            exploit_results.append(exploit_result)
            results.append((f"EXPLOIT_{cmd.split()[0]}", exploit_result))
        
        # Step 6: Compile final report
        final_report = f"# ELIOT Pentest Report — Target: {target}\n\n"
        for step, r in results:
            final_report += f"## {step}\n{r.content[:2000]}\n\n"
        
        return AgentMessage(
            sender=self.name,
            receiver=initial_message.sender,
            content=final_report[:10000],
            message_type="pentest_report",
            metadata={
                "workflow": "pentest",
                "target": target,
                "steps_completed": [s for s, _ in results],
                "total_steps": len(results),
                "exploits_run": len(exploit_results),
            },
        )
    
    async def _generate_exploit_commands(self, target: str, analysis_text: str) -> List[str]:
        """Use LLM to generate specific exploit commands from analysis findings."""
        # Check authorization requirements via Tamagotchi
        try:
            from agents.tamagotchi import get_tamagotchi_engine
            tama = get_tamagotchi_engine()
        except ImportError:
            tama = None

        llm_result = await self._llm_generate(
            prompt=(
                f"Based on this vulnerability analysis of target {target}:\n\n"
                f"{analysis_text[:4000]}\n\n"
                f"Generate up to 5 specific shell commands to test or exploit the top findings.\n"
                f"Rules:\n"
                f"- Each command must be a complete, ready-to-run shell command\n"
                f"- Use nmap scripts (e.g. nmap --script=vuln), nikto, sqlmap, hydra, curl, searchsploit\n"
                f"- Target is {target} - use the discovered ports and services\n"
                f"- Focus on highest severity findings first\n"
                f"- Include one command per line, nothing else\n"
                f"- Do NOT include commands that require interactive input\n"
                f"- Do NOT include destructive commands (no DoS, no crashers)\n"
                f"- For metasploit, use: msfconsole -q -x 'use exploit/...; set RHOSTS {target}; exploit; exit'\n"
            ),
            system_prompt=(
                "You are a penetration testing expert. Generate safe, non-destructive exploit and validation commands. "
                "Return ONLY the commands, one per line. No explanations, no markdown, no numbering."
            ),
            max_tokens=512,
            temperature=0.2,
        )
        
        if not llm_result:
            return []
        
        commands = []
        for line in llm_result.strip().split("\n"):
            line = line.strip()
            line = line.lstrip("0123456789.-) ")
            line = line.strip('`').strip()
            if not line or line.startswith("#") or len(line) < 10:
                continue
            if any(d in line.lower() for d in ["rm ", "dd ", "mkfs", "shutdown", "reboot", "fork", ":(){"]):
                continue

            # Check if this command needs authorization
            if tama and tama.needs_authorization(line):
                tama.create_notification(
                    ntype="exploit_ready",
                    title=f"Workflow exploit: {line.split()[0]}",
                    message=f"Target: {target}",
                    target=target,
                    severity="high",
                    needs_auth=True,
                    exploit_cmd=line,
                )
                logger.info(f"Exploit queued for auth: {line[:80]}")
                continue  # Skip unauthorized exploits in automated workflow

            commands.append(line)
        
        return commands[:5]

    def _store_knowledge(self, category: str, key: str, value: Any, source: str = "supervisor"):
        """Store knowledge for future reference."""
        try:
            from agents.tamagotchi import get_tamagotchi_engine
            tama = get_tamagotchi_engine()
            tama.log_knowledge(category, key, value, source=source)
        except ImportError:
            pass

    async def process(self, message: AgentMessage) -> AgentMessage:
        """Route incoming request to appropriate agent(s)."""
        content = message.content.lower()

        # Check for explicit agent routing
        target_agent = self._resolve_target(content)
        if target_agent:
            agent = self._agents.get(target_agent)
            if agent:
                logger.info(f"Supervisor routing to: {target_agent}")
                self._recent_agent = target_agent
                self._recent_agent_time = time.time()
                return await agent.handle(message)

        # Route shell commands to ShellAgent
        if message.content.startswith("!") or content.startswith("launch ") or content.startswith("open "):
            self._recent_agent = "Shell"
            self._recent_agent_time = time.time()
            return await self._route_to("Shell", message)
        
        # Route event chaining to ShellAgent
        if content.startswith("chain "):
            self._recent_agent = "Shell"
            self._recent_agent_time = time.time()
            return await self._route_to("Shell", message)
        
        # Route command analysis to ShellAgent (only for actual commands, not general analysis requests)
        # Check if it's a command analysis request (analyze + command-like content)
        if content.startswith("analyze ") or content.startswith("analyse "):
            # If it contains analysis-related keywords, route to Analysis agent
            if any(kw in content for kw in ["findings", "results", "data", "report", "summary", "report findings"]):
                return await self._route_to("Analysis", message)
            # Otherwise, treat as command analysis for Shell agent
            self._recent_agent = "Shell"
            self._recent_agent_time = time.time()
            return await self._route_to("Shell", message)

        # Check for context-aware routing: follow-up to recent agent
        if self._recent_agent and self._is_context_followup(content):
            time_since = time.time() - self._recent_agent_time
            if time_since < self._context_timeout:
                logger.info(f"Supervisor context routing to: {self._recent_agent} (follow-up)")
                return await self._route_to(self._recent_agent, message)

        llm_result = await self._llm_generate(
            prompt=(
                f"User message: {message.content}\n\n"
                f"Available agents: {', '.join(f'{n} ({a.description})' for n, a in self._agents.items())}\n\n"
                f"Which single agent should handle this message? Reply with ONLY the agent name."
            ),
            system_prompt=(
                "You are ELIOT CORE, the supervisor agent. You route user messages to specialist agents. "
                "Reply with ONLY the agent name, nothing else."
            ),
            max_tokens=20,
            temperature=0.1,
        )
        if llm_result:
            resolved = llm_result.strip().strip('"').strip("'")
            for name in self._agents:
                if name.lower() in resolved.lower():
                    logger.info(f"Supervisor LLM routing to: {name}")
                    self._recent_agent = name
                    self._recent_agent_time = time.time()
                    return await self._agents[name].handle(message)

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

    def _is_context_followup(self, content: str) -> bool:
        """Check if this message is a follow-up that should stay with recent agent."""
        followup_patterns = [
            "create a list", "summarize", "summary", "explain", "what does",
            "which ones", "how many", "show me", "filter", "sort", "analyze",
            "analyse", "details", "more info", "tell me about", "what are",
            "list them", "convert", "format", "parse", "extract", "them",
            "those", "these", "above", "previous", "last", "again",
        ]
        return any(p in content for p in followup_patterns)

    def _resolve_target(self, content: str) -> Optional[str]:
        for name, agent in self._agents.items():
            if name.lower() in content:
                return name
        return None

    async def _route_to(self, agent_name: str, message: AgentMessage) -> AgentMessage:
        agent = self._agents.get(agent_name)
        if agent:
            self._recent_agent = agent_name
            self._recent_agent_time = time.time()
            return await agent.handle(message)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=f"Agent '{agent_name}' is not available.",
            message_type="error",
        )
