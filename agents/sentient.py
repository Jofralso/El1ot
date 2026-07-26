"""
Sentient Engine

Autonomous network discovery, device mapping, and topology generation.
Continuously scans all reachable networks, maps devices, services, and connections.
Generates interactive topology diagrams and maintains a live device inventory.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    ROUTER = "router"
    SERVER = "server"
    WORKSTATION = "workstation"
    IoT = "iot"
    MOBILE = "mobile"
    PRINTER = "printer"
    NAS = "nas"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Service:
    port: int
    protocol: str = "tcp"
    name: str = ""
    version: str = ""
    banner: str = ""
    scripts: Dict[str, str] = field(default_factory=dict)


@dataclass
class Device:
    ip: str
    mac: str = ""
    hostname: str = ""
    os_guess: str = ""
    device_type: DeviceType = DeviceType.UNKNOWN
    services: List[Service] = field(default_factory=list)
    vulnerabilities: List[Dict[str, str]] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    signal_strength: Optional[int] = None  # dBm for WiFi
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["device_type"] = self.device_type.value
        d["services"] = [asdict(s) for s in self.services]
        return d


@dataclass
class WiFiAP:
    bssid: str
    ssid: str
    channel: int
    frequency: str
    encryption: str
    signal: int  # dBm
    quality: int  # 0-100
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Network:
    cidr: str
    gateway: str = ""
    interface: str = ""
    discovered_at: float = field(default_factory=time.time)
    device_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SentientEngine:
    """
    Autonomous network intelligence engine.
    Discovers all networks, maps devices, builds topology.
    """

    # WiFi interface priority: external adapter first, built-in as fallback
    WIFI_INTERFACES = ["wlxc4e984dfb30f", "wlP1p1s0"]

    def __init__(self):
        self._devices: Dict[str, Device] = {}  # IP -> Device
        self._networks: Dict[str, Network] = {}  # CIDR -> Network
        self._wifi_aps: Dict[str, WiFiAP] = {}  # BSSID -> WiFiAP
        self._topology: Dict[str, Any] = {"nodes": [], "edges": []}
        self._scan_history: List[Dict[str, Any]] = []
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._last_full_scan = 0.0
        self._our_ip: str = ""
        self._our_mac: str = ""
        self._live_events: List[Dict[str, Any]] = []
        self._max_live_events = 200
        self._my_interfaces: Dict[str, str] = {}  # name -> IP
        self._wifi_interface: str = ""  # detected at runtime

    @property
    def running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "devices": len(self._devices),
            "networks": len(self._networks),
            "wifi_aps": len(self._wifi_aps),
            "last_scan": self._last_full_scan,
            "our_ip": self._our_ip,
            "topology_nodes": len(self._topology.get("nodes", [])),
            "topology_edges": len(self._topology.get("edges", [])),
        }

    # ── Shell Execution ──────────────────────────────────────

    async def _run(self, cmd: str, timeout: float = 60.0) -> Tuple[str, int]:
        """Run a command, return (stdout, returncode)."""
        proc = None
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode("utf-8", errors="replace"), proc.returncode or 0
        except asyncio.TimeoutError:
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            return "", -1
        except Exception as e:
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            return str(e), -1

    # ── Network Discovery ────────────────────────────────────

    async def _detect_our_interfaces(self):
        """Detect our own IP addresses and interfaces."""
        stdout, _ = await self._run("ip -4 addr show")
        current_iface = ""
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("inet "):
                ip = line.split()[1].split("/")[0]
                if ip.startswith("127."):
                    continue
                self._my_interfaces[current_iface] = ip
                if not self._our_ip:
                    self._our_ip = ip
            elif line.startswith(("2:", "3:", "4:", "5:", "6:", "7:", "8:", "9:")):
                parts = line.split(":")
                if len(parts) >= 2:
                    current_iface = parts[1].strip().split("@")[0]

        # Get our MAC
        stdout, _ = await self._run("ip link show")
        for line in stdout.split("\n"):
            if "link/ether" in line and self._our_ip:
                self._our_mac = line.split("link/ether")[1].split()[0]
                break

        logger.info(f"Our interfaces: {self._my_interfaces}")

    async def _detect_local_networks(self) -> List[str]:
        """Detect all local network subnets (excluding link-local, loopback, docker)."""
        networks = []
        skip_prefixes = ("127.", "169.254.", "224.", "239.", "240.", "172.")

        # Get from interface addresses (most reliable)
        stdout, _ = await self._run("ip -4 addr show")
        for line in stdout.split("\n"):
            if "inet " in line:
                parts = line.split()
                for p in parts:
                    if "/" in p and not any(p.startswith(s) for s in skip_prefixes):
                        ip, mask = p.rsplit("/", 1)
                        if int(mask) >= 24:
                            octets = ip.split(".")
                            networks.append(f"{octets[0]}.{octets[1]}.{octets[2]}.0/24")
                        else:
                            networks.append(p)

        # Also check routing table for non-docker, non-link-local networks
        stdout2, _ = await self._run("ip route show")
        for line in stdout2.split("\n"):
            parts = line.split()
            if len(parts) >= 1 and "/" in parts[0]:
                cidr = parts[0]
                if not any(cidr.startswith(s) for s in skip_prefixes):
                    if cidr not in networks:
                        networks.append(cidr)

        # Deduplicate
        seen = set()
        unique = []
        for n in networks:
            if n not in seen:
                seen.add(n)
                unique.append(n)

        return unique

    async def _scan_network_discovery(self, cidr: str) -> List[Dict[str, str]]:
        """Ping scan a subnet to discover live hosts."""
        from agents.stealth import get_stealth_engine, ScanProfile
        stealth = get_stealth_engine()

        # Use AGGRESSIVE for local discovery (internal/authorized target)
        saved = stealth._profile
        stealth._profile = ScanProfile.AGGRESSIVE
        cmd = stealth.build_nmap_discovery(cidr)
        stealth._profile = saved
        logger.info(f"Discovery scan: {cmd}")
        stdout, rc = await self._run(cmd, timeout=120)
        stealth.record_scan()

        hosts = []
        current_ip = None
        for line in stdout.split("\n"):
            line = line.strip()
            if "Nmap scan report for" in line:
                # Parse: "Nmap scan report for hostname (192.168.1.1)" or "Nmap scan report for 192.168.1.1"
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

        return hosts

    async def _scan_service_detection(self, ip: str) -> List[Service]:
        """Run service version detection on a host."""
        from agents.stealth import get_stealth_engine
        stealth = get_stealth_engine()

        cmd = stealth.build_nmap_service_scan(ip)
        stdout, rc = await self._run(cmd, timeout=180)
        stealth.record_scan()

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

        return services

    async def _scan_os_detection(self, ip: str) -> str:
        """Detect OS of a host."""
        cmd = f"echo jetson | sudo -S nmap -O --osscan-guess {ip} 2>/dev/null | grep 'OS details\\|Running'"
        stdout, _ = await self._run(cmd, timeout=60)
        for line in stdout.split("\n"):
            if "OS details" in line or "Running" in line:
                return line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        return ""

    # ── WiFi Interface Detection ──────────────────────────────

    async def _detect_wifi_interface(self) -> str:
        """Detect best available WiFi interface. External adapter preferred."""
        if self._wifi_interface:
            return self._wifi_interface

        for iface in self.WIFI_INTERFACES:
            stdout, rc = await self._run(f"cat /sys/class/net/{iface}/type 2>/dev/null")
            if rc == 0 and stdout.strip() == "1":  # Type 1 = wireless
                self._wifi_interface = iface
                logger.info(f"Using WiFi interface: {iface}")
                return iface

        # Fallback: find any wireless interface
        stdout, _ = await self._run("iw dev 2>/dev/null | grep Interface | head -1 | awk '{print $2}'")
        if stdout.strip():
            self._wifi_interface = stdout.strip()
            logger.info(f"Using detected WiFi interface: {self._wifi_interface}")
            return self._wifi_interface

        logger.warning("No WiFi interface found, using wlP1p1s0 as fallback")
        self._wifi_interface = "wlP1p1s0"
        return self._wifi_interface

    # ── WiFi Scanning ────────────────────────────────────────

    async def _scan_wifi(self) -> List[WiFiAP]:
        """Scan for WiFi access points using nmcli."""
        iface = await self._detect_wifi_interface()

        stdout, rc = await self._run(
            f"nmcli -t -f BSSID,SSID,CHAN,FREQ,MODE,SIGNAL,RATE,SIGNAL-BAR device wifi list"
        )
        if rc != 0:
            # Fallback to non-verbose
            stdout, rc = await self._run("nmcli device wifi list")

        aps = []
        if rc == 0:
            for line in stdout.split("\n"):
                line = line.strip()
                if not line or line.startswith("BSSID"):
                    continue
                # Try to parse nmcli output
                parts = line.split(":")
                if len(parts) >= 3:
                    bssid = parts[0].strip()
                    ssid = parts[1].strip() if len(parts) > 1 else ""
                    if bssid and len(bssid) == 17:  # MAC format
                        ap = WiFiAP(
                            bssid=bssid,
                            ssid=ssid,
                            channel=0,
                            frequency="",
                            encryption="unknown",
                            signal=0,
                            quality=0,
                        )
                        aps.append(ap)
                        self._wifi_aps[bssid] = ap

        # Also try iwlist for more detail on selected interface
        stdout2, _ = await self._run(f"echo jetson | sudo -S iwlist {iface} scan 2>/dev/null")
        current_ap = None
        for line in stdout2.split("\n"):
            line = line.strip()
            if "Cell" in line and "Address:" in line:
                bssid = line.split("Address:")[1].strip()
                if bssid in self._wifi_aps:
                    current_ap = self._wifi_aps[bssid]
                else:
                    current_ap = WiFiAP(
                        bssid=bssid, ssid="", channel=0,
                        frequency="", encryption="unknown",
                        signal=0, quality=0,
                    )
                    self._wifi_aps[bssid] = current_ap
            elif current_ap:
                if "ESSID:" in line:
                    current_ap.ssid = line.split('"')[1] if '"' in line else ""
                elif "Channel:" in line:
                    try:
                        current_ap.channel = int(line.split(":")[1].strip())
                    except ValueError:
                        pass
                elif "Frequency:" in line:
                    current_ap.frequency = line.split(":")[1].strip() if ":" in line else ""
                elif "Encryption key:" in line:
                    current_ap.encryption = "on" if "on" in line.lower() else "off"
                elif "Signal level=" in line:
                    try:
                        current_ap.signal = int(line.split("level=")[1].split()[0])
                        current_ap.quality = max(0, min(100, current_ap.signal + 100))
                    except (ValueError, IndexError):
                        pass

        return list(self._wifi_aps.values())

    # ── Bluetooth Scanning ───────────────────────────────────

    async def _scan_bluetooth(self) -> List[Dict[str, str]]:
        """Scan for Bluetooth devices."""
        devices = []

        # hcitool scan
        stdout, rc = await self._run(
            "echo jetson | sudo -S timeout 10 hcitool scan 2>/dev/null"
        )
        if rc == 0:
            for line in stdout.split("\n"):
                line = line.strip()
                if "\t" in line and len(line) > 20:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        mac = parts[0].strip()
                        name = parts[1].strip()
                        devices.append({"mac": mac, "name": name, "type": "classic"})

        # hcitool inq (inquiry for devices that don't respond to scan)
        stdout2, rc2 = await self._run(
            "echo jetson | sudo -S timeout 10 hcitool inq 2>/dev/null"
        )
        if rc2 == 0:
            for line in stdout2.split("\n"):
                line = line.strip()
                if "BD_ADDR:" in line:
                    mac = line.split("BD_ADDR:")[1].split()[0].strip()
                    if not any(d["mac"] == mac for d in devices):
                        devices.append({"mac": mac, "name": "", "type": "classic"})

        return devices

    # ── Topology Building ────────────────────────────────────

    def _build_topology(self):
        """Build interactive topology graph from discovered devices."""
        nodes = []
        edges = []
        node_ids = set()

        # Add our own machine
        our_id = f"self_{self._our_ip}"
        nodes.append({
            "id": our_id,
            "ip": self._our_ip,
            "mac": self._our_mac,
            "label": "ELIOT",
            "type": "self",
            "severity": "none",
            "icon": "shield",
        })
        node_ids.add(our_id)

        # Add gateway
        gateway = ""
        stdout = ""
        import subprocess
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=5
            )
            stdout = result.stdout
        except Exception:
            stdout = ""

        for line in stdout.split("\n"):
            if "via" in line:
                gateway = line.split("via")[1].split()[0].strip()
                break

        if gateway and gateway not in node_ids:
            gw_id = f"router_{gateway}"
            nodes.append({
                "id": gw_id,
                "ip": gateway,
                "label": "Gateway",
                "type": "router",
                "severity": "none",
                "icon": "router",
            })
            node_ids.add(gw_id)
            edges.append({
                "source": our_id,
                "target": gw_id,
                "type": "route",
                "label": "gateway",
            })

        # Add all discovered devices
        for ip, device in self._devices.items():
            node_id = f"device_{ip}"
            if node_id in node_ids:
                continue

            # Determine max severity
            max_sev = Severity.NONE
            for vuln in device.vulnerabilities:
                sev = Severity(vuln.get("severity", "none"))
                if list(Severity).index(sev) > list(Severity).index(max_sev):
                    max_sev = sev

            nodes.append({
                "id": node_id,
                "ip": ip,
                "mac": device.mac,
                "label": device.hostname or ip,
                "type": device.device_type.value,
                "severity": max_sev.value,
                "os": device.os_guess,
                "services": len(device.services),
                "icon": self._device_icon(device.device_type),
            })
            node_ids.add(node_id)

            # Connect to gateway if on same network
            if gateway:
                gw_id = f"router_{gateway}"
                # Simple heuristic: same /24 subnet
                if ip.rsplit(".", 1)[0] == gateway.rsplit(".", 1)[0]:
                    edges.append({
                        "source": node_id,
                        "target": gw_id,
                        "type": "lan",
                        "label": f"{len(device.services)} services",
                    })

            # Connect devices that have client-server relationships
            for svc in device.services:
                if svc.name in ("http", "https", "ssh", "ftp", "smb", "rdp", "vnc"):
                    # This device provides a service
                    pass

        # Add WiFi APs
        for bssid, ap in self._wifi_aps.items():
            ap_id = f"ap_{bssid}"
            if ap_id not in node_ids:
                nodes.append({
                    "id": ap_id,
                    "ip": "",
                    "mac": bssid,
                    "label": ap.ssid or bssid,
                    "type": "wifi_ap",
                    "severity": "none",
                    "signal": ap.signal,
                    "channel": ap.channel,
                    "encryption": ap.encryption,
                    "icon": "wifi",
                })
                node_ids.add(ap_id)

        self._topology = {"nodes": nodes, "edges": edges}

    def _device_icon(self, dtype: DeviceType) -> str:
        return {
            DeviceType.ROUTER: "router",
            DeviceType.SERVER: "server",
            DeviceType.WORKSTATION: "desktop",
            DeviceType.IoT: "iot",
            DeviceType.MOBILE: "mobile",
            DeviceType.PRINTER: "printer",
            DeviceType.NAS: "nas",
            DeviceType.UNKNOWN: "unknown",
        }.get(dtype, "unknown")

    # ── Device Classification ─────────────────────────────────

    def _classify_device(self, device: Device) -> DeviceType:
        """Classify device type based on services and OS."""
        svc_names = {s.name.lower() for s in device.services}
        os_lower = device.os_guess.lower()

        if any(s in svc_names for s in ["router", "telnet"]) or "router" in os_lower:
            return DeviceType.ROUTER
        if any(s in svc_names for s in ["mysql", "postgresql", "mongodb", "redis", "http", "https"]):
            if "linux" in os_lower:
                return DeviceType.SERVER
        if any(s in svc_names for s in ["airplay", "chromecast", "upnp", "mdns"]):
            return DeviceType.IoT
        if "printer" in os_lower or any(s in svc_names for s in ["ipp", "lpd"]):
            return DeviceType.PRINTER
        if "nas" in os_lower or any(s in svc_names for s in ["nfs", "smb"]):
            return DeviceType.NAS
        if any(s in svc_names for s in ["ssh", "rdp", "vnc"]):
            return DeviceType.WORKSTATION

        return DeviceType.UNKNOWN

    # ── Event System ──────────────────────────────────────────

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit a live event for WebSocket streaming."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        self._live_events.append(event)
        if len(self._live_events) > self._max_live_events:
            self._live_events = self._live_events[-self._max_live_events:]
        logger.debug(f"Event: {event_type} - {data}")

    def get_live_events(self, since: float = 0) -> List[Dict[str, Any]]:
        """Get events since timestamp."""
        if since == 0:
            return self._live_events[-50:]
        return [e for e in self._live_events if e["timestamp"] > since]

    # ── Main Scan Loop ────────────────────────────────────────

    async def run_full_scan(self) -> Dict[str, Any]:
        """Execute a complete network scan cycle."""
        logger.info("Starting full sentient scan...")
        scan_start = time.time()
        self._emit_event("scan_start", {"phase": "interface_detection"})

        # Detect our interfaces
        await self._detect_our_interfaces()

        # Detect local networks
        self._emit_event("scan_progress", {"phase": "network_detection"})
        networks = await self._detect_local_networks()
        for cidr in networks:
            if cidr not in self._networks:
                self._networks[cidr] = Network(cidr=cidr)
                self._emit_event("network_discovered", {"cidr": cidr})

        # WiFi scan
        self._emit_event("scan_progress", {"phase": "wifi_scan"})
        wifi_aps = await self._scan_wifi()
        for ap in wifi_aps:
            self._emit_event("wifi_ap_found", {"bssid": ap.bssid, "ssid": ap.ssid, "signal": ap.signal})

        # Bluetooth scan
        self._emit_event("scan_progress", {"phase": "bluetooth_scan"})
        bt_devices = await self._scan_bluetooth()
        for bt in bt_devices:
            self._emit_event("bluetooth_found", bt)

        # Network discovery scans
        all_hosts = []
        for cidr in networks:
            self._emit_event("scan_progress", {"phase": "host_discovery", "network": cidr})
            hosts = await self._scan_network_discovery(cidr)
            all_hosts.extend(hosts)

            if cidr in self._networks:
                self._networks[cidr].device_count = len(hosts)

        # Service detection on discovered hosts
        new_devices = 0
        for host in all_hosts:
            ip = host["ip"]
            if ip in self._devices:
                self._devices[ip].last_seen = time.time()
                continue

            self._emit_event("scan_progress", {"phase": "service_detection", "ip": ip})
            services = await self._scan_service_detection(ip)

            device = Device(
                ip=ip,
                hostname=host.get("hostname", ""),
                services=services,
            )
            device.device_type = self._classify_device(device)
            self._devices[ip] = device
            new_devices += 1

            self._emit_event("device_discovered", {
                "ip": ip,
                "hostname": device.hostname,
                "type": device.device_type.value,
                "services": len(services),
            })

        # OS detection on first few new devices
        for host in all_hosts[:5]:
            ip = host["ip"]
            if ip in self._devices and not self._devices[ip].os_guess:
                self._emit_event("scan_progress", {"phase": "os_detection", "ip": ip})
                os_guess = await self._scan_os_detection(ip)
                if os_guess:
                    self._devices[ip].os_guess = os_guess
                    self._devices[ip].device_type = self._classify_device(self._devices[ip])

        # Build topology
        self._emit_event("scan_progress", {"phase": "building_topology"})
        self._build_topology()

        self._last_full_scan = time.time()
        scan_duration = time.time() - scan_start

        result = {
            "duration_seconds": round(scan_duration, 1),
            "networks_scanned": len(networks),
            "hosts_found": len(all_hosts),
            "new_devices": new_devices,
            "total_devices": len(self._devices),
            "wifi_aps": len(wifi_aps),
            "bluetooth_devices": len(bt_devices),
            "topology_nodes": len(self._topology.get("nodes", [])),
        }

        self._scan_history.append(result)
        self._emit_event("scan_complete", result)

        logger.info(f"Full scan complete: {result}")
        return result

    # ── Background Loop ───────────────────────────────────────

    async def start(self, scan_interval: int = 300):
        """Start the background scan loop."""
        if self._running:
            return
        self._running = True
        logger.info(f"Sentient engine started (interval: {scan_interval}s)")
        self._scan_task = asyncio.create_task(self._scan_loop(scan_interval))

    async def stop(self):
        """Stop the background scan loop."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        logger.info("Sentient engine stopped")

    async def _scan_loop(self, interval: int):
        """Background scan loop."""
        while self._running:
            try:
                await self.run_full_scan()
            except Exception as e:
                logger.error(f"Sentient scan error: {e}", exc_info=True)
            await asyncio.sleep(interval)

    # ── Data Access ───────────────────────────────────────────

    def get_devices(self) -> List[Dict[str, Any]]:
        """Get all discovered devices."""
        return [d.to_dict() for d in self._devices.values()]

    def get_device(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get a specific device."""
        device = self._devices.get(ip)
        return device.to_dict() if device else None

    def get_networks(self) -> List[Dict[str, Any]]:
        """Get all discovered networks."""
        return [n.to_dict() for n in self._networks.values()]

    def get_topology(self) -> Dict[str, Any]:
        """Get the interactive topology graph."""
        return self._topology

    def get_wifi_aps(self) -> List[Dict[str, Any]]:
        """Get all discovered WiFi APs."""
        return [ap.to_dict() for ap in self._wifi_aps.values()]

    def get_scan_history(self) -> List[Dict[str, Any]]:
        """Get scan history."""
        return self._scan_history

    def search_devices(self, query: str) -> List[Dict[str, Any]]:
        """Search devices by IP, hostname, service name, or OS."""
        query_lower = query.lower()
        results = []
        for device in self._devices.values():
            if query_lower in device.ip.lower():
                results.append(device.to_dict())
                continue
            if query_lower in device.hostname.lower():
                results.append(device.to_dict())
                continue
            if query_lower in device.os_guess.lower():
                results.append(device.to_dict())
                continue
            for svc in device.services:
                if query_lower in svc.name.lower() or query_lower in svc.version.lower():
                    results.append(device.to_dict())
                    break
        return results


# ── Singleton ────────────────────────────────────────────────

_sentient_engine: Optional[SentientEngine] = None


def get_sentient_engine() -> SentientEngine:
    global _sentient_engine
    if _sentient_engine is None:
        _sentient_engine = SentientEngine()
    return _sentient_engine
