"""
Code Agent

Generates scripts, automation helpers, and code snippets.
"""

import logging
from typing import Any, Dict

from agents.base import BaseAgent, AgentRole, AgentMessage

logger = logging.getLogger(__name__)


class CodeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role=AgentRole.CODE,
            name="Code",
            description="Generates scripts, automation helpers, and code snippets",
            permissions=["read", "write", "code_generate"],
            tools=["code_generator", "script_runner"],
        )

    async def process(self, message: AgentMessage) -> AgentMessage:
        code_response = self._generate_code(message.content)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            content=code_response,
            message_type="code",
            metadata={"language": "python", "type": "generated"},
        )

    def _generate_code(self, request: str) -> str:
        request_lower = request.lower()

        if any(kw in request_lower for kw in ["nmap", "scan", "network"]):
            return self._network_scan_script(request)
        if any(kw in request_lower for kw in ["hash", "md5", "sha"]):
            return self._hash_script()
        if any(kw in request_lower for kw in ["port", "connect", "socket"]):
            return self._port_check_script()
        if any(kw in request_lower for kw in ["directory", "brute", "fuzz"]):
            return self._dir_brute_script()

        return self._generic_response(request)

    def _network_scan_script(self, request: str) -> str:
        return (
            '#!/usr/bin/env python3\n'
            '"""Network Discovery Script - For authorized testing only"""\n\n'
            'import subprocess\n'
            'import sys\n\n'
            'def scan_network(target, ports="1-1000"):\n'
            '    """Simple port scan using system tools"""\n'
            '    if not target:\n'
            '        print("Usage: python scan.py <target>")\n'
            '        sys.exit(1)\n'
            '    \n'
            '    print(f"[*] Scanning {target}...")\n'
            '    result = subprocess.run(\n'
            '        ["nmap", "-sV", "-p", ports, target],\n'
            '        capture_output=True, text=True\n'
            '    )\n'
            '    print(result.stdout)\n'
            '    return result.stdout\n\n'
            'if __name__ == "__main__":\n'
            '    scan_network(sys.argv[1] if len(sys.argv) > 1 else None)\n'
        )

    def _hash_script(self) -> str:
        return (
            '#!/usr/bin/env python3\n'
            '"""Hashing utility"""\n\n'
            'import hashlib\n'
            'import sys\n\n'
            'def hash_text(text, algorithm="sha256"):\n'
            '    h = hashlib.new(algorithm)\n'
            '    h.update(text.encode())\n'
            '    return h.hexdigest()\n\n'
            'if __name__ == "__main__":\n'
            '    text = sys.argv[1] if len(sys.argv) > 1 else input("Enter text: ")\n'
            '    for algo in ["md5", "sha1", "sha256"]:\n'
            '        print(f"{algo}: {hash_text(text, algo)}")\n'
        )

    def _port_check_script(self) -> str:
        return (
            '#!/usr/bin/env python3\n'
            '"""Quick port checker"""\n\n'
            'import socket\n\n'
            'def check_port(host, port, timeout=2):\n'
            '    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n'
            '        s.settimeout(timeout)\n'
            '        result = s.connect_ex((host, port))\n'
            '        return result == 0\n\n'
            'def scan_common(host):\n'
            '    common_ports = [21, 22, 25, 53, 80, 443, 445, 8080, 8443]\n'
            '    print(f"Scanning {host}...")\n'
            '    for port in common_ports:\n'
            '        status = "OPEN" if check_port(host, port) else "closed"\n'
            '        print(f"  Port {port}: {status}")\n\n'
            'if __name__ == "__main__":\n'
            '    import sys\n'
            '    scan_common(sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1")\n'
        )

    def _dir_brute_script(self) -> str:
        return (
            '#!/usr/bin/env python3\n'
            '"""Simple directory discovery - For authorized testing"""\n\n'
            'import urllib.request\n'
            'import sys\n\n'
            'COMMON_DIRS = [\n'
            '    "admin", "login", "api", "backup", "config",\n'
            '    "debug", "dev", "docs", "env", "git",\n'
            '    "health", "images", "js", "logs", "metrics",\n'
            '    "private", "robots.txt", "secret", "server-status",\n'
            '    "swagger", "test", "uploads", "v1", "v2",\n'
            ']\n\n'
            'def discover(base_url):\n'
            '    for path in COMMON_DIRS:\n'
            '        url = f"{base_url.rstrip("/")}/{path}"\n'
            '        try:\n'
            '            req = urllib.request.Request(url, method="HEAD")\n'
            '            resp = urllib.request.urlopen(req, timeout=3)\n'
            '            print(f"  [+] {resp.status} {url}")\n'
            '        except Exception:\n'
            '            pass\n\n'
            'if __name__ == "__main__":\n'
            '    if len(sys.argv) < 2:\n'
            '        print("Usage: python dirbrute.py <url>")\n'
            '    else:\n'
            '        discover(sys.argv[1])\n'
        )

    def _generic_response(self, request: str) -> str:
        return (
            f"Code request received: {request}\n\n"
            "Available script templates:\n"
            "  - Network scanning (nmap-based)\n"
            "  - Port checking (socket-based)\n"
            "  - Hashing utilities\n"
            "  - Directory discovery\n\n"
            "Specify the type of script you need, or provide more details."
        )
