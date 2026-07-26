"""
Tamagotchi Engine — ELIOT Autonomous Agent

Mr. Robot-themed autonomous intelligence agent.
Runs in the background, discovers devices/vulns, prioritizes exploits,
manages cracking sessions (pausing Ollama for GPU), and creates
notifications requiring authorization for machine-access exploits.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TamaState(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    MAPPING = "mapping"
    CRACKING = "cracking"
    ANALYZING = "analyzing"
    EXPLOITING = "exploiting"
    ALERT = "alert"
    SLEEPING = "sleeping"


class NotificationType(str, Enum):
    NEW_DEVICE = "new_device"
    VULN_FOUND = "vuln_found"
    EXPLOIT_READY = "exploit_ready"
    CRACK_COMPLETE = "crack_complete"
    ACCESS_GAINED = "access_gained"
    ALERT = "alert"
    INFO = "info"


class AuthStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    AUTO_APPROVED = "auto_approved"
    EXPIRED = "expired"


@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: NotificationType = NotificationType.INFO
    title: str = ""
    message: str = ""
    target: str = ""
    severity: str = "info"
    needs_auth: bool = False
    auth_status: AuthStatus = AuthStatus.AUTO_APPROVED
    created_at: float = field(default_factory=time.time)
    auth_at: Optional[float] = None
    result: Optional[str] = None
    exploit_cmd: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        d["auth_status"] = self.auth_status.value
        return d


@dataclass
class CrackSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool: str = "john"
    target: str = ""
    hash_file: str = ""
    wordlist: str = "/usr/share/wordlists/rockyou.txt"
    status: str = "pending"
    progress: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[str] = None
    pid: Optional[int] = None
    gpu_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExploitTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target: str = ""
    service: str = ""
    exploit_name: str = ""
    command: str = ""
    priority: int = 0  # Higher = more important
    cve: str = ""
    cvss: float = 0.0
    needs_auth: bool = True
    auth_status: AuthStatus = AuthStatus.PENDING
    created_at: float = field(default_factory=time.time)
    executed: bool = False
    result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["auth_status"] = self.auth_status.value
        return d


class TamagotchiEngine:
    """
    Autonomous intelligence agent.
    Discovers, maps, prioritizes, and (with authorization) exploits.
    Gamified with XP, levels, weighted rewards, and learning from mistakes.
    """

    # Commands that need authorization (machine access / data extraction)
    AUTH_REQUIRED_PATTERNS = [
        "msfconsole", "msfvenom", "meterpreter",
        "hydra", "ncrack",
        "sqlmap --dump", "sqlmap --os-shell", "sqlmap --os-pwn",
        "exploit", "payload", "reverse_tcp",
        "john --show", "hashcat",
        "sshpass", "smbclient -L",
        "mount", "chroot",
        "curl -d", "wget --post",
    ]

    # Commands that are always safe (no auth needed)
    SAFE_PATTERNS = [
        "nmap", "nikto", "whatweb", "gobuster", "dirb", "dirbuster",
        "enum4linux", "smbclient -N", "snmpwalk",
        "curl", "wget", "httpie",
        "arp", "ip ", "ifconfig", "ss", "netstat",
        "hcitool", "bluetoothctl",
        "nmcli", "iwlist",
        "searchsploit",
        "cat ", "ls ", "grep ", "find ", "head ", "tail ",
    ]

    # ── Gamification Constants ───────────────────────────────
    XP_WEIGHTS = {
        "scan_complete": 10,
        "device_discovered": 15,
        "service_detected": 20,
        "vuln_found": 30,
        "exploit_success": 50,
        "crack_complete": 40,
        "auth_granted": 5,
        "knowledge_logged": 8,
        "new_network_mapped": 25,
        "wifi_ap_found": 12,
        "bluetooth_found": 10,
        "false_positive": -15,
        "scan_timeout": -5,
        "exploit_failed": -20,
        "wrong_classification": -10,
    }

    LEVEL_XP = [
        0, 100, 250, 500, 800, 1200, 1800, 2500, 3500, 5000,
        7000, 10000, 14000, 19000, 25000, 32000, 40000, 50000,
        62000, 75000, 90000, 110000, 135000, 165000, 200000,
    ]

    LEVEL_NAMES = [
        "Script Kiddie", "Script Kiddie", "Script Kiddie",
        "Novice Hacker", "Novice Hacker",
        "Junior Pentester", "Junior Pentester",
        "Pentester", "Pentester", "Pentester",
        "Senior Pentester", "Senior Pentester",
        "Security Analyst", "Security Analyst",
        "Red Team Operator", "Red Team Operator",
        "Exploit Developer", "Exploit Developer",
        "Security Researcher", "Security Researcher",
        "Bug Hunter", "Bug Hunter",
        "Elite Hacker", "Elite Hacker", "Elite Hacker",
    ]

    ACHIEVEMENTS = {
        "first_scan": {"name": "First Steps", "desc": "Complete your first scan", "xp": 50, "icon": "🔍"},
        "first_device": {"name": "Network Explorer", "desc": "Discover your first device", "xp": 75, "icon": "📡"},
        "first_vuln": {"name": "Bug Finder", "desc": "Find your first vulnerability", "xp": 100, "icon": "🐛"},
        "first_exploit": {"name": "Exploit Artist", "desc": "Execute your first exploit", "xp": 200, "icon": "💥"},
        "first_crack": {"name": "Password Hunter", "desc": "Complete your first crack session", "xp": 150, "icon": "🔐"},
        "ten_devices": {"name": "Network Mapper", "desc": "Discover 10 devices", "xp": 300, "icon": "🗺️"},
        "ten_vulns": {"name": "Vuln Collector", "desc": "Find 10 vulnerabilities", "xp": 400, "icon": "📋"},
        "hundred_xp": {"name": "Rising Star", "desc": "Earn 100 XP total", "xp": 50, "icon": "⭐"},
        "thousand_xp": {"name": "Dedicated Hacker", "desc": "Earn 1000 XP total", "xp": 100, "icon": "🌟"},
        "level_5": {"name": "Getting Serious", "desc": "Reach level 5", "xp": 200, "icon": "📈"},
        "level_10": {"name": "Pro Pentester", "desc": "Reach level 10", "xp": 500, "icon": "🏆"},
        "night_owl": {"name": "Night Owl", "desc": "Run a scan between 2-5 AM", "xp": 75, "icon": "🦉"},
        "full_network": {"name": "Network Dominator", "desc": "Map an entire /24 subnet", "xp": 600, "icon": "🌐"},
        "stealth_master": {"name": "Ghost", "desc": "Complete 10 scans without detection", "xp": 300, "icon": "👻"},
    }

    def __init__(self):
        self._state = TamaState.IDLE
        self._notifications: List[Notification] = []
        self._exploit_queue: List[ExploitTask] = []
        self._crack_sessions: List[CrackSession] = []
        self._knowledge_log: List[Dict[str, Any]] = []
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._ollama_pid: Optional[int] = None
        self._ollama_was_running = False
        self._stats = {
            "scans_run": 0,
            "devices_found": 0,
            "vulns_found": 0,
            "exploits_executed": 0,
            "cracks_run": 0,
            "notifications_created": 0,
            "authorizations_granted": 0,
        }
        # ── Gamification State ──
        self._xp: int = 0
        self._level: int = 1
        self._total_xp: int = 0
        self._achievements: List[str] = []
        self._event_log: List[Dict[str, Any]] = []
        self._streaks: Dict[str, int] = {
            "scans": 0, "devices": 0, "vulns": 0, "exploits": 0,
        }
        self._mistakes: List[Dict[str, Any]] = []

    @property
    def state(self) -> TamaState:
        return self._state

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "running": self._running,
            "pending_notifications": sum(
                1 for n in self._notifications
                if n.needs_auth and n.auth_status == AuthStatus.PENDING
            ),
            "total_notifications": len(self._notifications),
            "pending_exploits": sum(
                1 for e in self._exploit_queue
                if e.auth_status == AuthStatus.PENDING
            ),
            "active_cracks": sum(
                1 for c in self._crack_sessions if c.status == "running"
            ),
            "stats": self._stats,
            "ollama_paused": self._ollama_was_running,
            # Gamification
            "xp": self._xp,
            "level": self._level,
            "level_name": self._get_level_name(),
            "total_xp": self._total_xp,
            "xp_to_next": self._xp_to_next_level(),
            "xp_progress": self._xp_progress(),
            "achievements": self._achievements,
            "achievements_total": len(self.ACHIEVEMENTS),
            "streaks": self._streaks,
            "mistakes_count": len(self._mistakes),
        }

    # ── Gamification Methods ─────────────────────────────────

    def award_xp(self, action: str, amount: int = 0, detail: str = "") -> int:
        """Award XP for an action. Returns actual XP gained (may differ with multipliers)."""
        base = amount or self.XP_WEIGHTS.get(action, 5)

        # Streak bonus: +10% per streak level (max +50%)
        streak_key = action.split("_")[0] if "_" in action else action
        streak = self._streaks.get(streak_key, 0)
        multiplier = 1.0 + min(streak * 0.1, 0.5)
        final_xp = int(base * multiplier)

        self._xp += final_xp
        self._total_xp += final_xp

        # Level up check
        old_level = self._level
        self._level = self._calculate_level()
        leveled_up = self._level > old_level

        # Log the event
        self._event_log.append({
            "type": "xp",
            "action": action,
            "xp": final_xp,
            "base": base,
            "multiplier": round(multiplier, 1),
            "total": self._total_xp,
            "level": self._level,
            "detail": detail,
            "timestamp": time.time(),
        })

        # Keep log manageable
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]

        # Check achievements
        self._check_achievements()

        if leveled_up:
            self._event_log.append({
                "type": "level_up",
                "level": self._level,
                "name": self._get_level_name(),
                "timestamp": time.time(),
            })

        logger.info(f"XP awarded: {final_xp} for {action} (total: {self._total_xp}, level: {self._level})")
        return final_xp

    def penalize(self, action: str, amount: int = 0, reason: str = ""):
        """Penalize for mistakes (false positives, failures, etc)."""
        base = amount or abs(self.XP_WEIGHTS.get(action, -5))
        penalty = min(base, self._xp)  # Never go below 0
        self._xp -= penalty

        self._mistakes.append({
            "action": action,
            "penalty": penalty,
            "reason": reason,
            "timestamp": time.time(),
        })

        # Keep mistakes log manageable
        if len(self._mistakes) > 200:
            self._mistakes = self._mistakes[-200:]

        self._event_log.append({
            "type": "penalty",
            "action": action,
            "xp": -penalty,
            "reason": reason,
            "timestamp": time.time(),
        })

        logger.info(f"XP penalty: -{penalty} for {action} (reason: {reason})")
        return penalty

    def record_mistake(self, action: str, expected: str, actual: str):
        """Record a classification/prediction mistake for learning."""
        self._mistakes.append({
            "action": action,
            "expected": expected,
            "actual": actual,
            "timestamp": time.time(),
            "learned": False,
        })
        self.penalize("wrong_classification", reason=f"Expected {expected}, got {actual}")

    def get_learning_data(self) -> Dict[str, Any]:
        """Get data about mistakes and learning progress."""
        unlearned = [m for m in self._mistakes if not m.get("learned")]
        return {
            "total_mistakes": len(self._mistakes),
            "unlearned": len(unlearned),
            "recent_mistakes": self._mistakes[-10:],
            "learning_rate": 1.0 - (len(unlearned) / max(len(self._mistakes), 1)),
            "categories": self._mistake_categories(),
        }

    def _mistake_categories(self) -> Dict[str, int]:
        """Count mistakes by category."""
        cats = {}
        for m in self._mistakes:
            cat = m.get("action", "unknown")
            cats[cat] = cats.get(cat, 0) + 1
        return cats

    def _calculate_level(self) -> int:
        """Calculate level from total XP."""
        level = 1
        for i, threshold in enumerate(self.LEVEL_XP):
            if self._total_xp >= threshold:
                level = i + 1
            else:
                break
        return min(level, len(self.LEVEL_XP))

    def _get_level_name(self) -> str:
        idx = min(self._level - 1, len(self.LEVEL_NAMES) - 1)
        return self.LEVEL_NAMES[idx]

    def _xp_to_next_level(self) -> int:
        if self._level >= len(self.LEVEL_XP):
            return 0
        return self.LEVEL_XP[self._level] - self._total_xp

    def _xp_progress(self) -> float:
        if self._level >= len(self.LEVEL_XP):
            return 1.0
        current = self.LEVEL_XP[self._level - 1] if self._level > 1 else 0
        nxt = self.LEVEL_XP[self._level]
        return (self._total_xp - current) / max(nxt - current, 1)

    def _check_achievements(self):
        """Check and award achievements."""
        new_achievements = []

        def try_achieve(key):
            if key not in self._achievements:
                ach = self.ACHIEVEMENTS[key]
                self._achievements.append(key)
                new_achievements.append(ach)
                self._event_log.append({
                    "type": "achievement",
                    "key": key,
                    "name": ach["name"],
                    "desc": ach["desc"],
                    "icon": ach["icon"],
                    "xp": ach["xp"],
                    "timestamp": time.time(),
                })

        if self._stats["scans_run"] >= 1:
            try_achieve("first_scan")
        if self._stats["devices_found"] >= 1:
            try_achieve("first_device")
        if self._stats["vulns_found"] >= 1:
            try_achieve("first_vuln")
        if self._stats["exploits_executed"] >= 1:
            try_achieve("first_exploit")
        if self._stats["cracks_run"] >= 1:
            try_achieve("first_crack")
        if self._stats["devices_found"] >= 10:
            try_achieve("ten_devices")
        if self._stats["vulns_found"] >= 10:
            try_achieve("ten_vulns")
        if self._total_xp >= 100:
            try_achieve("hundred_xp")
        if self._total_xp >= 1000:
            try_achieve("thousand_xp")
        if self._level >= 5:
            try_achieve("level_5")
        if self._level >= 10:
            try_achieve("level_10")

        hour = time.localtime().tm_hour
        if 2 <= hour <= 5 and self._stats["scans_run"] > 0:
            try_achieve("night_owl")

        for ach in new_achievements:
            self.award_xp("achievement_unlocked", ach["xp"], ach["name"])

    # ── Authorization Logic ───────────────────────────────────

    def needs_authorization(self, command: str) -> bool:
        """Check if a command requires user authorization."""
        cmd_lower = command.lower()

        # Always safe commands don't need auth
        for pattern in self.SAFE_PATTERNS:
            if pattern in cmd_lower:
                return False

        # Check if command matches auth-required patterns
        for pattern in self.AUTH_REQUIRED_PATTERNS:
            if pattern in cmd_lower:
                return True

        return False

    def create_notification(
        self,
        ntype: NotificationType,
        title: str,
        message: str,
        target: str = "",
        severity: str = "info",
        needs_auth: bool = False,
        exploit_cmd: Optional[str] = None,
    ) -> Notification:
        """Create a notification (and optionally an exploit task)."""
        notif = Notification(
            type=ntype,
            title=title,
            message=message,
            target=target,
            severity=severity,
            needs_auth=needs_auth,
            exploit_cmd=exploit_cmd,
        )
        if needs_auth:
            notif.auth_status = AuthStatus.PENDING

        self._notifications.append(notif)
        self._stats["notifications_created"] += 1

        if exploit_cmd:
            task = ExploitTask(
                target=target,
                command=exploit_cmd,
                needs_auth=needs_auth,
                auth_status=notif.auth_status,
            )
            self._exploit_queue.append(task)

        logger.info(f"Notification: [{ntype.value}] {title} (auth={needs_auth})")
        return notif

    def authorize_notification(self, notification_id: str) -> bool:
        """Authorize a pending notification/exploit."""
        for notif in self._notifications:
            if notif.id == notification_id and notif.needs_auth:
                notif.auth_status = AuthStatus.APPROVED
                notif.auth_at = time.time()
                self._stats["authorizations_granted"] += 1

                # Also approve linked exploit task
                for task in self._exploit_queue:
                    if task.command == notif.exploit_cmd:
                        task.auth_status = AuthStatus.APPROVED

                logger.info(f"Authorized: {notif.title}")
                return True
        return False

    def deny_notification(self, notification_id: str) -> bool:
        """Deny a pending notification."""
        for notif in self._notifications:
            if notif.id == notification_id and notif.needs_auth:
                notif.auth_status = AuthStatus.DENIED
                notif.auth_at = time.time()

                for task in self._exploit_queue:
                    if task.command == notif.exploit_cmd:
                        task.auth_status = AuthStatus.DENIED

                logger.info(f"Denied: {notif.title}")
                return True
        return False

    # ── Knowledge Growth ──────────────────────────────────────

    def log_knowledge(self, category: str, key: str, value: Any, source: str = ""):
        """Log a piece of knowledge for future reference."""
        entry = {
            "category": category,
            "key": key,
            "value": value,
            "source": source,
            "timestamp": time.time(),
        }
        self._knowledge_log.append(entry)

        # Keep knowledge log manageable
        if len(self._knowledge_log) > 5000:
            self._knowledge_log = self._knowledge_log[-5000:]

    def get_knowledge(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get knowledge entries, optionally filtered by category."""
        entries = self._knowledge_log
        if category:
            entries = [e for e in entries if e["category"] == category]
        return entries[-limit:]

    def get_knowledge_stats(self) -> Dict[str, int]:
        """Get knowledge stats by category."""
        stats = {}
        for entry in self._knowledge_log:
            cat = entry["category"]
            stats[cat] = stats.get(cat, 0) + 1
        return stats

    # ── Crack Management ──────────────────────────────────────

    async def _pause_ollama(self):
        """Pause Ollama to free GPU for hashcat."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "ollama"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid_str in pids:
                    if pid_str.strip():
                        pid = int(pid_str.strip())
                        os.kill(pid, signal.SIGSTOP)
                        self._ollama_pid = pid
                        self._ollama_was_running = True
                        logger.info(f"Paused Ollama (PID {pid}) for GPU cracking")
                        return True
        except Exception as e:
            logger.warning(f"Could not pause Ollama: {e}")
        return False

    async def _resume_ollama(self):
        """Resume Ollama after cracking."""
        if self._ollama_pid and self._ollama_was_running:
            try:
                os.kill(self._ollama_pid, signal.SIGCONT)
                logger.info(f"Resumed Ollama (PID {self._ollama_pid})")
            except Exception as e:
                logger.warning(f"Could not resume Ollama: {e}")
            self._ollama_pid = None
            self._ollama_was_running = False

    async def start_crack(self, hash_file: str, tool: str = "john", gpu: bool = False) -> CrackSession:
        """Start a cracking session."""
        session = CrackSession(
            tool=tool,
            hash_file=hash_file,
            gpu_mode=gpu,
            status="starting",
        )

        if gpu and tool == "hashcat":
            await self._pause_ollama()

        self._crack_sessions.append(session)
        self._stats["cracks_run"] += 1

        # Build command
        if tool == "john":
            cmd = f"john {hash_file}"
        elif tool == "hashcat":
            mode = "0"  # default hash mode
            cmd = f"hashcat -m {mode} {hash_file} /usr/share/wordlists/rockyou.txt"
        else:
            cmd = f"{tool} {hash_file}"

        session.status = "running"
        session.started_at = time.time()

        # Run in background
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            session.pid = proc.pid
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
            session.result = stdout.decode("utf-8", errors="replace")
            session.status = "completed"
            session.completed_at = time.time()
        except asyncio.TimeoutError:
            session.status = "timeout"
            session.result = "Cracking session timed out after 1 hour"
            try:
                if proc and proc.returncode is None:
                    proc.kill()
                    await proc.wait()
                    logger.info(f"Killed orphaned cracking process PID={session.pid}")
            except Exception:
                pass
        except Exception as e:
            session.status = "error"
            session.result = str(e)
        finally:
            if gpu:
                await self._resume_ollama()

        self.create_notification(
            NotificationType.CRACK_COMPLETE,
            "Cracking Complete",
            f"Tool: {tool}, Status: {session.status}",
            target=hash_file,
        )

        return session

    # ── Exploit Prioritization ────────────────────────────────

    def prioritize_exploits(self) -> List[ExploitTask]:
        """Sort exploit queue by priority and CVSS score."""
        pending = [
            t for t in self._exploit_queue
            if t.auth_status in (AuthStatus.PENDING, AuthStatus.APPROVED)
            and not t.executed
        ]
        pending.sort(key=lambda t: (-t.priority, -t.cvss))
        return pending

    async def execute_authorized_exploits(self, shell_agent):
        """Execute all authorized exploits."""
        for task in self.prioritize_exploits():
            if task.auth_status == AuthStatus.APPROVED:
                self._state = TamaState.EXPLOITING
                logger.info(f"Executing authorized exploit: {task.command}")

                from agents.base import AgentMessage
                msg = AgentMessage(
                    sender="tamagotchi",
                    receiver="Shell",
                    content=f"!{task.command}",
                    metadata={"tamagotchi_exploit": True, "task_id": task.id},
                )
                result = await shell_agent.handle(msg)
                task.executed = True
                task.result = result.content
                self._stats["exploits_executed"] += 1

                self.log_knowledge(
                    "exploit",
                    task.exploit_name or task.command[:100],
                    {"target": task.target, "result": result.content[:500]},
                    source="tamagotchi",
                )

    # ── Learning from Discoveries ──────────────────────────────

    def learn_from_device(self, device: Dict[str, Any]):
        """Extract and store knowledge from a discovered device."""
        ip = device.get("ip", "")
        services = device.get("services", [])

        for svc in services:
            name = svc.get("name", "")
            version = svc.get("version", "")

            if version:
                self.log_knowledge(
                    "service_version",
                    f"{ip}:{svc.get('port')}",
                    {"service": name, "version": version},
                    source="sentient",
                )

            # Check for known vulnerable versions
            if name in ("http", "https") and version:
                self.log_knowledge(
                    "web_service",
                    ip,
                    {"port": svc.get("port"), "version": version},
                    source="sentient",
                )

        # Log the device itself
        self.log_knowledge(
            "device",
            ip,
            {
                "hostname": device.get("hostname", ""),
                "type": device.get("device_type", "unknown"),
                "services": len(services),
            },
            source="sentient",
        )

    # ── Prompt Suggestions ────────────────────────────────────

    def get_prompt_suggestions(self) -> List[Dict[str, str]]:
        """Get contextual prompt suggestions based on current state."""
        suggestions = []

        # Always-available suggestions
        suggestions.extend([
            {"text": "Scan my network", "category": "recon", "icon": "radar"},
            {"text": "Show discovered devices", "category": "recon", "icon": "list"},
            {"text": "Generate network map", "category": "recon", "icon": "map"},
            {"text": "Check system health", "category": "system", "icon": "heart"},
            {"text": "List all agents", "category": "system", "icon": "users"},
        ])

        # Context-aware suggestions based on state
        if self._stats["devices_found"] > 0:
            suggestions.extend([
                {"text": "Pentest all discovered devices", "category": "pentest", "icon": "crosshair"},
                {"text": "Enumerate services on all targets", "category": "recon", "icon": "scan"},
                {"text": "Search for known CVEs", "category": "vuln", "icon": "bug"},
            ])

        if self._stats["vulns_found"] > 0:
            suggestions.extend([
                {"text": "Prioritize exploits by severity", "category": "exploit", "icon": "fire"},
                {"text": "Generate vulnerability report", "category": "report", "icon": "file"},
                {"text": "Show pending authorizations", "category": "tamagotchi", "icon": "shield"},
            ])

        pending = sum(1 for n in self._notifications if n.needs_auth and n.auth_status == AuthStatus.PENDING)
        if pending > 0:
            suggestions.append(
                {"text": f"Review {pending} pending authorization(s)", "category": "tamagotchi", "icon": "alert"}
            )

        # Knowledge-based suggestions
        knowledge_stats = self.get_knowledge_stats()
        if knowledge_stats:
            suggestions.append(
                {"text": "What do we know about [target]?", "category": "knowledge", "icon": "brain"}
            )

        return suggestions

    # ── Main Autonomous Loop ──────────────────────────────────

    async def start(self, scan_interval: int = 600):
        """Start the autonomous loop."""
        if self._running:
            return
        self._running = True
        self._state = TamaState.IDLE
        logger.info(f"Tamagotchi engine started (interval: {scan_interval}s)")
        self._loop_task = asyncio.create_task(self._autonomous_loop(scan_interval))

    async def stop(self):
        """Stop the autonomous loop."""
        self._running = False
        self._state = TamaState.SLEEPING
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        await self._resume_ollama()
        logger.info("Tamagotchi engine stopped")

    async def _autonomous_loop(self, interval: int):
        """Main autonomous loop."""
        while self._running:
            try:
                # Phase 1: Scan (delegates to Sentient)
                self._state = TamaState.SCANNING
                from agents.sentient import get_sentient_engine
                sentient = get_sentient_engine()

                if sentient.running:
                    scan_result = await sentient.run_full_scan()
                    self._stats["scans_run"] += 1
                    self._streaks["scans"] = self._streaks.get("scans", 0) + 1
                    self.award_xp("scan_complete", detail=f"Scan #{self._stats['scans_run']}")

                    old_devices = self._stats["devices_found"]
                    self._stats["devices_found"] = len(sentient.get_devices())
                    new_devices = self._stats["devices_found"] - old_devices
                    if new_devices > 0:
                        self._streaks["devices"] = self._streaks.get("devices", 0) + new_devices
                        self.award_xp("device_discovered", 15 * new_devices, f"+{new_devices} devices")
                        # Check full network achievement
                        if self._stats["devices_found"] >= 25:
                            if "full_network" not in self._achievements:
                                self.award_xp("new_network_mapped", 600, "Full /24 mapped")

                    # Learn from discoveries
                    for device_data in sentient.get_devices():
                        self.learn_from_device(device_data)

                    # Create notifications for new devices
                    for event in sentient.get_live_events(time.time() - interval):
                        if event["type"] == "device_discovered":
                            data = event["data"]
                            self.create_notification(
                                NotificationType.NEW_DEVICE,
                                f"New device: {data.get('ip')}",
                                f"Hostname: {data.get('hostname', 'unknown')}, "
                                f"Type: {data.get('type', 'unknown')}, "
                                f"Services: {data.get('services', 0)}",
                                target=data.get("ip", ""),
                                severity="info",
                            )

                # Phase 2: Analyze
                self._state = TamaState.ANALYZING
                await asyncio.sleep(2)

                # Phase 3: Execute authorized exploits
                authorized = [
                    t for t in self._exploit_queue
                    if t.auth_status == AuthStatus.APPROVED and not t.executed
                ]
                if authorized:
                    self._state = TamaState.EXPLOITING

                # Phase 4: Idle
                self._state = TamaState.IDLE

            except Exception as e:
                logger.error(f"Tamagotchi loop error: {e}", exc_info=True)
                self._state = TamaState.ALERT

            await asyncio.sleep(interval)

    # ── Data Access ───────────────────────────────────────────

    def get_notifications(
        self,
        status: Optional[AuthStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get notifications, optionally filtered by auth status."""
        notifs = self._notifications
        if status:
            notifs = [n for n in notifs if n.auth_status == status]
        return [n.to_dict() for n in notifs[-limit:]]

    def get_exploit_queue(self) -> List[Dict[str, Any]]:
        """Get prioritized exploit queue."""
        return [t.to_dict() for t in self.prioritize_exploits()]

    def get_crack_sessions(self) -> List[Dict[str, Any]]:
        """Get all cracking sessions."""
        return [c.to_dict() for c in self._crack_sessions]

    def clear_old_notifications(self, max_age_hours: int = 24):
        """Clear notifications older than max_age hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        self._notifications = [
            n for n in self._notifications
            if n.created_at > cutoff
        ]

    # ── Event Log & Gamification Data ────────────────────────

    def get_event_log(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict]:
        """Get recent events (XP gains, achievements, penalties, level ups)."""
        log = self._event_log
        if event_type:
            log = [e for e in log if e.get("type") == event_type]
        return log[-limit:]

    def get_mistakes(self, limit: int = 50) -> List[Dict]:
        """Get recent mistakes for learning review."""
        return self._mistakes[-limit:]

    def get_gamification(self) -> Dict[str, Any]:
        """Get full gamification status."""
        return {
            "xp": self._xp,
            "level": self._level,
            "level_name": self._get_level_name(),
            "total_xp": self._total_xp,
            "xp_to_next": self._xp_to_next_level(),
            "xp_progress": round(self._xp_progress(), 3),
            "next_level_name": self.LEVEL_NAMES[min(self._level, len(self.LEVEL_NAMES)-1)],
            "achievements": [
                {**self.ACHIEVEMENTS[k], "key": k}
                for k in self._achievements
            ],
            "achievements_available": len(self.ACHIEVEMENTS),
            "streaks": self._streaks,
            "mistakes": self.get_learning_data(),
            "recent_events": self.get_event_log(20),
            "stats": self._stats,
        }


# ── Singleton ────────────────────────────────────────────────

_tamagotchi_engine: Optional[TamagotchiEngine] = None


def get_tamagotchi_engine() -> TamagotchiEngine:
    global _tamagotchi_engine
    if _tamagotchi_engine is None:
        _tamagotchi_engine = TamagotchiEngine()
    return _tamagotchi_engine
