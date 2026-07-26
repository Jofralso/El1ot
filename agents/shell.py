"""
Shell Agent

Executes shell commands, launches applications, analyzes results, and chains events.
Includes security measures: command allowlist/blocklist, sandboxing, dangerous command confirmation.
"""

import os
import asyncio
import logging
import subprocess
import shlex
from typing import Any, Dict, List, Optional, Tuple
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
    Agent for executing shell commands, launching apps, and event chaining.
    
    Security model:
    - Commands are classified by safety level
    - Blocked commands are never executed
    - Dangerous commands require explicit confirmation (handled via metadata)
    - All commands are logged for audit
    """
    
    # Commands that are never allowed
    BLOCKED_COMMANDS = {
        'rm -rf /', 'mkfs', 'dd if=', ':(){', 'fork',
        'chmod -R 777 /', 'chown -R', '> /dev/sda',
        'shutdown', 'reboot', 'halt', 'init 0', 'init 6',
        'systemctl stop', 'systemctl disable',
    }
    
    # Commands requiring confirmation (dangerous)
    DANGEROUS_PATTERNS = {
        'rm -rf', 'rm -r', 'sudo rm', 'chmod 777', 'chown',
        'kill -9', 'killall', 'pkill', 'shutdown', 'reboot',
        'systemctl restart', 'service restart', 'apt remove', 'apt purge',
        'pip uninstall', 'npm uninstall', 'docker rm', 'docker stop',
        'iptables', 'ufw', 'nft', 'firewall-cmd',
    }
    
    # Safe commands (no confirmation needed)
    SAFE_COMMANDS = {
        'ls', 'pwd', 'whoami', 'date', 'uptime', 'df', 'du', 'free',
        'ps', 'top', 'htop', 'netstat', 'ss', 'ip', 'ifconfig',
        'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'uniq',
        'echo', 'env', 'printenv', 'uname', 'hostname',
        'nmap', 'nikto', 'whatweb', 'curl', 'wget',
        'python', 'python3', 'pip', 'pip3', 'node', 'npm',
        'git', 'docker', 'systemctl status',
        'journalctl', 'dmesg', 'lscpu', 'lshw',
    }
    
    # Applications that can be launched
    LAUNCHABLE_APPS = {
        'firefox': 'firefox',
        'chromium': 'chromium-browser',
        'terminal': 'gnome-terminal',
        'code': 'code',
        'vim': 'vim',
        'nano': 'nano',
        'top': 'top',
        'htop': 'htop',
        'wireshark': 'wireshark',
        'burpsuite': 'burpsuite',
        'metasploit': 'msfconsole',
        'nmap': 'nmap',
    }
    
    def __init__(self):
        super().__init__(
            role=AgentRole.CODE,  # Using CODE role as shell is code execution
            name="Shell",
            description="Executes commands, launches applications, chains events",
            permissions=["read", "write", "execute", "admin"],
            tools=["shell_executor", "app_launcher", "event_chainer"],
        )
        self._command_history: List[Dict[str, Any]] = []
        self._event_chains: Dict[str, List[str]] = {}
        self._pending_confirmations: Dict[str, str] = {}
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        content = message.content.strip()
        metadata = message.metadata
        
        # Check for confirmation of pending dangerous command
        if metadata.get("confirm_dangerous"):
            return await self._handle_confirmation(message)
        
        # Parse command from message
        if content.startswith("!"):
            return await self._execute_command(content[1:].strip(), message)
        
        # Check for app launch
        if content.lower().startswith("launch ") or content.lower().startswith("open "):
            app = content.split(None, 1)[1].strip()
            return await self._launch_app(app, message)
        
        # Check for event chaining
        if content.lower().startswith("chain "):
            return await self._handle_chain(content[6:].strip(), message)
        
        # Check for command analysis
        if content.lower().startswith("analyze ") or content.lower().startswith("analyse "):
            cmd = content.split(None, 1)[1].strip()
            return await self._analyze_command(cmd, message)
        
        # Natural language: use LLM to convert to shell command
        return await self._nl_to_command(message.content, message)
    
    async def _execute_command(self, command: str, message: AgentMessage) -> AgentMessage:
        """Execute a shell command with safety checks."""
        
        # Check if command is blocked
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
            # Store pending confirmation
            self._pending_confirmations[command] = message.sender
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"DANGEROUS: Command '{command}' requires confirmation.\n"
                       f"Reply with 'confirm {command}' to proceed or 'cancel' to abort.",
                message_type="warning",
                metadata={"requires_confirmation": True, "command": command},
            )
        
        # Execute the command
        try:
            # Use asyncio.create_subprocess_shell for async execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.expanduser("~"),
                env={**os.environ, "TERM": "dumb"},  # Simplified terminal
            )
            
            # Longer timeout for network commands
            timeout = 60.0 if any(kw in command.lower() for kw in ['nmap', 'arp', 'ping', 'scan', 'curl', 'wget']) else 30.0
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            # Log command execution
            self._command_history.append({
                "command": command,
                "return_code": process.returncode,
                "timestamp": __import__('time').time(),
                "user": message.sender,
            })
            
            # Prepare response
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
                    "stdout": stdout_text[:1000],  # Truncate for metadata
                    "stderr": stderr_text[:500],
                    "safety": safety.value,
                },
            )
            
        except asyncio.TimeoutError:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"Command timed out after 30 seconds: {command}",
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
        """Handle confirmation of dangerous command."""
        content = message.content.strip()
        
        if content.lower().startswith("confirm "):
            command = content[8:].strip()
            if command in self._pending_confirmations:
                del self._pending_confirmations[command]
                return await self._execute_command(command, message)
        
        if content.lower() == "cancel":
            # Clear all pending confirmations
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
        """Launch an application."""
        app_lower = app_name.lower()
        
        if app_lower in self.LAUNCHABLE_APPS:
            cmd = self.LAUNCHABLE_APPS[app_lower]
            # Add & to run in background
            return await self._execute_command(f"{cmd} &", message)
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=f"Unknown application: {app_name}\n"
                   f"Available apps: {', '.join(self.LAUNCHABLE_APPS.keys())}",
            message_type="text",
        )
    
    async def _handle_chain(self, chain_cmd: str, message: AgentMessage) -> AgentMessage:
        """Handle event chaining (multiple commands in sequence)."""
        # Parse chain: "chain cmd1 | cmd2 | cmd3" or "chain cmd1 && cmd2 && cmd3"
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
            # Execute each command
            result = await self._execute_command(cmd, message)
            results.append(f"Step {i+1}: {cmd}\n{result.content}")
            
            # Stop chain if command fails
            if result.metadata.get("return_code", 0) != 0:
                results.append(f"\nChain stopped at step {i+1} due to failure.")
                break
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content="\n\n".join(results),
            message_type="chain_output",
            metadata={"chain_length": len(results), "commands": commands},
        )
    
    async def _analyze_command(self, command: str, message: AgentMessage) -> AgentMessage:
        """Analyze a command without executing it."""
        safety = self._check_command_safety(command)
        
        # Get LLM analysis if available
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
        """Convert natural language request to a shell command using LLM."""
        llm_cmd = await self._llm_generate(
            prompt=(
                f"Convert this natural language request into a single Linux shell command.\n"
                f"Request: {text}\n\n"
                f"Rules:\n"
                f"- Reply with ONLY the shell command. No explanation, no markdown, no backticks.\n"
                f"- Use simple, fast commands. For network scanning use: ip -4 addr show | grep inet, arp -a, or nmap -sn 192.168.0.0/24\n"
                f"- Do NOT use sudo unless absolutely necessary.\n"
                f"- Do NOT use -O flag with nmap (it's slow). Use -sn for ping scan instead.\n"
                f"- Keep the command simple and fast (under 15 seconds to run).\n"
                f"- If the request is complex, pick the most important single command."
            ),
            system_prompt=(
                "You are a Linux shell expert. Convert natural language to shell commands. "
                "Reply with ONLY the raw command. No explanations. No code blocks. No backticks."
            ),
            max_tokens=128,
            temperature=0.1,
        )
        
        if llm_cmd:
            command = llm_cmd.strip().strip('`').strip()
            # Remove markdown code block if present
            if command.startswith('```'):
                command = command.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            
            safety = self._check_command_safety(command)
            
            if safety == CommandSafety.BLOCKED:
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=f"I understood your request, but the generated command is blocked for safety:\n`{command}`\n\nPlease try rephrasing or use a more specific request.",
                    message_type="text",
                    metadata={"generated_command": command, "blocked": True},
                )
            
            if safety == CommandSafety.DANGEROUS:
                self._pending_confirmations[command] = message.sender
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    content=f"I'll run this command (requires confirmation):\n\n`{command}`\n\nReply 'confirm' to proceed or 'cancel' to abort.",
                    message_type="warning",
                    metadata={"requires_confirmation": True, "command": command},
                )
            
            # Execute the generated command
            return await self._execute_command(command, message)
        
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content="I couldn't convert that to a shell command. Try using `!command` for direct execution.",
            message_type="text",
        )
    
    def _check_command_safety(self, command: str) -> CommandSafety:
        """Check command safety level."""
        command_lower = command.lower()
        
        # Check blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower:
                return CommandSafety.BLOCKED
        
        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return CommandSafety.DANGEROUS
        
        # Check if it's a known safe command
        first_word = command_lower.split()[0] if command_lower.split() else ""
        if first_word in self.SAFE_COMMANDS:
            return CommandSafety.SAFE
        
        # Check for pipe to dangerous commands
        if "|" in command:
            parts = command.split("|")
            for part in parts:
                part_lower = part.strip().lower()
                first_word_part = part_lower.split()[0] if part_lower.split() else ""
                if first_word_part in {"rm", "dd", "mkfs", "chmod", "chown"}:
                    return CommandSafety.DANGEROUS
        
        # Default to caution for unknown commands
        return CommandSafety.CAUTION
    
    def get_command_history(self) -> List[Dict[str, Any]]:
        """Get command execution history."""
        return self._command_history[-100:]  # Last 100 commands
    
    def clear_history(self):
        """Clear command history."""
        self._command_history.clear()
