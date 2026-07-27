"""
Stealth Engine

Always-on network stealth for ELIOT. Handles MAC rotation, scan profiles,
decoy generation, timing obfuscation, and fingerprint avoidance.
The device should never be marked or identifiable on the network.
"""

import asyncio
import logging
import os
import random
import subprocess
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ScanProfile(str, Enum):
    SILENT = "silent"
    LOW = "low"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    MAX = "max"


SCAN_PROFILE_CONFIG = {
    ScanProfile.SILENT: {
        "nmap_timing": "-T0",
        "max_rate": "5",
        "scan_delay": "5",
        "decoys": 10,
        "source_port": True,
        "description": "Barely detectable. Very slow. Uses decoys.",
    },
    ScanProfile.LOW: {
        "nmap_timing": "-T1",
        "max_rate": "50",
        "scan_delay": "2",
        "decoys": 5,
        "source_port": True,
        "description": "Low visibility. Slow but thorough.",
    },
    ScanProfile.NORMAL: {
        "nmap_timing": "-T2",
        "max_rate": "500",
        "scan_delay": "0.5",
        "decoys": 3,
        "source_port": False,
        "description": "Default profile. Balanced speed and stealth.",
    },
    ScanProfile.AGGRESSIVE: {
        "nmap_timing": "-T3",
        "max_rate": "2000",
        "scan_delay": "0",
        "decoys": 0,
        "source_port": False,
        "description": "Fast. Only for internal/authorized targets.",
    },
    ScanProfile.MAX: {
        "nmap_timing": "-T4",
        "max_rate": "0",
        "scan_delay": "0",
        "decoys": 0,
        "source_port": False,
        "description": "Maximum speed. Never use without explicit override.",
    },
}


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0",
    "curl/7.88.1",
    "Wget/1.21.3",
]


class StealthEngine:
    """
    Manages all stealth operations for ELIOT.
    Always active by default — every scan goes through this engine.
    """

    # WiFi interface priority: external adapter first, built-in as fallback
    WIFI_INTERFACES = ["wlxc4e984dfb30f", "wlP1p1s0"]

    def __init__(self):
        self._profile = ScanProfile.NORMAL
        self._original_mac: Optional[str] = None
        self._current_mac: Optional[str] = None
        self._mac_randomized = False
        self._scan_count = 0
        self._last_scan_time = 0.0
        self._jitter_base = 0.5
        self._active = True
        self._wifi_interface: str = ""  # detected at runtime
        self._original_macs: Dict[str, str] = {}  # interface -> original MAC
        self._decoy_macs: Dict[str, str] = {}  # interface -> current decoy MAC
        self._jetson_interfaces: List[str] = ["wlP1p1s0", "eth0"]  # built-in interfaces to protect

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        logger.info(f"Stealth engine {'activated' if value else 'deactivated'}")

    @property
    def profile(self) -> ScanProfile:
        return self._profile

    def set_profile(self, profile: ScanProfile):
        old = self._profile
        self._profile = profile
        logger.info(f"Stealth profile: {old.value} -> {profile.value}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "profile": self._profile.value,
            "profile_config": SCAN_PROFILE_CONFIG[self._profile],
            "mac_randomized": self._mac_randomized,
            "current_mac": self._current_mac,
            "original_mac": self._original_mac,
            "scan_count": self._scan_count,
            "last_scan_time": self._last_scan_time,
            "jetson_original_macs": dict(self._original_macs),
            "jetson_decoy_macs": dict(self._decoy_macs),
            "jetson_protected_interfaces": self._jetson_interfaces,
        }

    # ── MAC Address Management ──────────────────────────────

    async def _run_cmd(self, cmd: str, timeout: float = 10.0) -> Tuple[str, str, int]:
        """Run a shell command and return (stdout, stderr, returncode)."""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
                proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            return "", "timeout", -1
        except Exception as e:
            return "", str(e), -1

    async def _detect_wifi_interface(self) -> str:
        """Detect best available WiFi interface. External adapter preferred."""
        if self._wifi_interface:
            return self._wifi_interface

        for iface in self.WIFI_INTERFACES:
            stdout, _, rc = await self._run_cmd(f"cat /sys/class/net/{iface}/type 2>/dev/null")
            if rc == 0 and stdout.strip() == "1":  # Type 1 = wireless
                self._wifi_interface = iface
                logger.info(f"Stealth using WiFi interface: {iface}")
                return iface

        # Fallback: find any wireless interface
        stdout, _, _ = await self._run_cmd("iw dev 2>/dev/null | grep Interface | head -1 | awk '{print $2}'")
        if stdout.strip():
            self._wifi_interface = stdout.strip()
            logger.info(f"Stealth using detected WiFi interface: {self._wifi_interface}")
            return self._wifi_interface

        logger.warning("No WiFi interface found, using wlP1p1s0 as fallback")
        self._wifi_interface = "wlP1p1s0"
        return self._wifi_interface

    async def _get_mac(self, interface: str = "") -> Optional[str]:
        """Get current MAC address of an interface."""
        if not interface:
            interface = await self._detect_wifi_interface()
        stdout, _, rc = await self._run_cmd(
            f"cat /sys/class/net/{interface}/address"
        )
        if rc == 0 and stdout.strip():
            return stdout.strip().lower()
        return None

    async def randomize_mac(self, interface: str = "") -> bool:
        """Randomize MAC address. Returns True if successful."""
        if self._mac_randomized:
            logger.debug("MAC already randomized, skipping")
            return True

        self._original_mac = await self._get_mac(interface)
        if not self._original_mac:
            logger.warning(f"Could not read MAC for {interface}")
            return False

        # Generate random MAC (locally administered, unicast)
        octets = [random.randint(0x00, 0xFF) for _ in range(6)]
        octets[0] = (octets[0] & 0xFE) | 0x02  # Locally administered, unicast
        random_mac = ":".join(f"{b:02x}" for b in octets)

        # Bring interface down, change MAC, bring up
        cmds = [
            f"echo jetson | sudo -S ip link set {interface} down",
            f"echo jetson | sudo -S ip link set {interface} address {random_mac}",
            f"echo jetson | sudo -S ip link set {interface} up",
        ]
        for cmd in cmds:
            _, stderr, rc = await self._run_cmd(cmd)
            if rc != 0:
                logger.warning(f"MAC randomize cmd failed: {stderr}")
                # Try to restore
                await self._restore_mac(interface)
                return False

        self._current_mac = random_mac
        self._mac_randomized = True
        logger.info(f"MAC randomized: {self._original_mac} -> {random_mac}")
        return True

    async def restore_mac(self, interface: str = "") -> bool:
        """Restore original MAC address."""
        if not interface:
            interface = await self._detect_wifi_interface()
        return await self._restore_mac(interface)

    async def _restore_mac(self, interface: str) -> bool:
        if not self._original_mac:
            return False

        cmds = [
            f"echo jetson | sudo -S ip link set {interface} down",
            f"echo jetson | sudo -S ip link set {interface} address {self._original_mac}",
            f"echo jetson | sudo -S ip link set {interface} up",
        ]
        for cmd in cmds:
            await self._run_cmd(cmd)

        self._current_mac = self._original_mac
        self._mac_randomized = False
        logger.info(f"MAC restored: {self._original_mac}")
        return True

    # ── Jetson Anonymity: Auto MAC Rotation ────────────────

    async def auto_rotate_jetson(self) -> Dict[str, bool]:
        """Rotate MAC addresses on all Jetson built-in interfaces for anonymity.
        Called at startup. External WiFi adapter is NOT rotated (it's the attack interface).
        Returns dict of interface -> success.
        """
        results = {}
        for iface in self._jetson_interfaces:
            exists, _, rc = await self._run_cmd(f"test -d /sys/class/net/{iface} && echo 1 || echo 0")
            if rc != 0 or "0" in exists.strip():
                continue
            original = await self._get_mac(iface)
            if original:
                self._original_macs[iface] = original

            octets = [random.randint(0x00, 0xFF) for _ in range(6)]
            octets[0] = (octets[0] & 0xFE) | 0x02
            random_mac = ":".join(f"{b:02x}" for b in octets)

            cmds = [
                f"echo jetson | sudo -S ip link set {iface} down",
                f"echo jetson | sudo -S ip link set {iface} address {random_mac}",
                f"echo jetson | sudo -S ip link set {iface} up",
            ]
            ok = True
            for cmd in cmds:
                _, stderr, rc = await self._run_cmd(cmd)
                if rc != 0:
                    ok = False
                    break

            if ok:
                self._decoy_macs[iface] = random_mac
                logger.info(f"[ANONYMITY] MAC rotated {iface}: {original} -> {random_mac}")
                results[iface] = True
            else:
                logger.warning(f"[ANONYMITY] Failed to rotate MAC on {iface}")
                results[iface] = False

        return results

    async def restore_all_macs(self) -> Dict[str, bool]:
        """Restore original MAC addresses on all Jetson interfaces. Called at shutdown."""
        results = {}
        for iface, original in self._original_macs.items():
            cmds = [
                f"echo jetson | sudo -S ip link set {iface} down",
                f"echo jetson | sudo -S ip link set {iface} address {original}",
                f"echo jetson | sudo -S ip link set {iface} up",
            ]
            for cmd in cmds:
                await self._run_cmd(cmd)
            self._decoy_macs.pop(iface, None)
            logger.info(f"[ANONYMITY] MAC restored {iface}: {original}")
            results[iface] = True
        return results

    async def rotate_jetson_mac(self, iface: str) -> bool:
        """Re-randomize a single Jetson interface (for periodic rotation)."""
        original = self._original_macs.get(iface)
        if not original:
            original = await self._get_mac(iface)
            if original:
                self._original_macs[iface] = original

        octets = [random.randint(0x00, 0xFF) for _ in range(6)]
        octets[0] = (octets[0] & 0xFE) | 0x02
        random_mac = ":".join(f"{b:02x}" for b in octets)

        cmds = [
            f"echo jetson | sudo -S ip link set {iface} down",
            f"echo jetson | sudo -S ip link set {iface} address {random_mac}",
            f"echo jetson | sudo -S ip link set {iface} up",
        ]
        for cmd in cmds:
            _, stderr, rc = await self._run_cmd(cmd)
            if rc != 0:
                return False

        self._decoy_macs[iface] = random_mac
        logger.info(f"[ANONYMITY] MAC rotated {iface}: {self._decoy_macs.get(iface, '?')} -> {random_mac}")
        return True

    # ── Scan Command Building ────────────────────────────────

    def build_nmap_cmd(
        self,
        target: str,
        ports: Optional[str] = None,
        scripts: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> str:
        """Build a stealth nmap command with current profile settings."""
        cfg = SCAN_PROFILE_CONFIG[self._profile]
        parts = ["nmap"]

        # Timing
        parts.append(cfg["nmap_timing"])

        # Rate limit
        if cfg["max_rate"] != "0":
            parts.append(f"--max-rate {cfg['max_rate']}")

        # Scan delay
        if cfg["scan_delay"] != "0":
            parts.append(f"--scan-delay {cfg['scan_delay']}s")

        # Decoys
        if cfg["decoys"] > 0:
            count = min(cfg["decoys"], 10)
            parts.append(f"-D RND:{count}")

        # Random source port
        if cfg["source_port"]:
            parts.append(f"--source-port {random.randint(1024, 65535)}")

        # Randomize HTTP User-Agent for script scans
        if scripts:
            ua = random.choice(USER_AGENTS)
            parts.append(f"--script-args http.useragent='{ua}'")

        # Port specification
        if ports:
            parts.append(f"-p {ports}")

        # Scripts
        if scripts:
            parts.append(f"--script={','.join(scripts)}")

        # Extra args
        if extra_args:
            parts.extend(extra_args)

        # Target
        parts.append(target)

        return " ".join(parts)

    def build_nmap_discovery(self, subnet: str) -> str:
        """Build a stealth host discovery command."""
        cfg = SCAN_PROFILE_CONFIG[self._profile]
        parts = ["nmap"]

        if self._profile in (ScanProfile.SILENT, ScanProfile.LOW):
            parts.append("-sn")
            parts.append("-PS22,80,443,445,3389")
        else:
            parts.append("-sn")

        parts.append(cfg["nmap_timing"])

        if cfg["max_rate"] != "0":
            parts.append(f"--max-rate {cfg['max_rate']}")

        if cfg["decoys"] > 0:
            parts.append(f"-D RND:{cfg['decoys']}")

        parts.append(subnet)
        return " ".join(parts)

    def build_nmap_service_scan(self, target: str) -> str:
        """Build a stealth service version detection command."""
        return self.build_nmap_cmd(
            target=target,
            scripts=["banner", "default"],
            extra_args=["-sV", "--version-intensity", "3"],
        )

    def build_nmap_vuln_scan(self, target: str, ports: Optional[str] = None) -> str:
        """Build a vulnerability scan command."""
        return self.build_nmap_cmd(
            target=target,
            ports=ports,
            scripts=["vuln"],
            extra_args=["--script-timeout", "30"],
        )

    # ── Timing & Jitter ──────────────────────────────────────

    async def apply_jitter(self, base: Optional[float] = None):
        """Apply random delay before next operation."""
        if not self._active:
            return
        base = base or self._jitter_base
        delay = random.uniform(base * 0.5, base * 2.0)
        await asyncio.sleep(delay)

    def should_throttle(self) -> bool:
        """Check if we should slow down based on recent scan frequency."""
        now = time.time()
        if now - self._last_scan_time < 10:
            return True
        return False

    def record_scan(self):
        """Record that a scan was performed."""
        self._scan_count += 1
        self._last_scan_time = time.time()

    # ── Utility ──────────────────────────────────────────────

    def get_random_ua(self) -> str:
        """Get a random User-Agent string."""
        return random.choice(USER_AGENTS)

    def get_random_source_port(self) -> int:
        """Get a random high port for source port spoofing."""
        return random.randint(40000, 65535)


# ── Singleton ────────────────────────────────────────────────

_stealth_engine: Optional[StealthEngine] = None


def get_stealth_engine() -> StealthEngine:
    global _stealth_engine
    if _stealth_engine is None:
        _stealth_engine = StealthEngine()
    return _stealth_engine
