"""
Built-in tools for ELIOT.

Each tool is a simple async function wrapped in a ToolDefinition.
"""

import asyncio
import os
import platform
import psutil
import time
from typing import Any, Dict

from tools.registry import ToolDefinition, ToolCategory, ToolPermission, tool_registry


# ── System Tools ─────────────────────────────────────────────

async def system_info() -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "platform": platform.system(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),
        "memory_used_gb": round(mem.used / (1024 ** 3), 2),
        "memory_percent": mem.percent,
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_percent": disk.percent,
        "uptime_seconds": time.time() - psutil.boot_time(),
    }


async def process_list(top_n: int = 10) -> list:
    procs = []
    for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                    key=lambda x: x.info.get("cpu_percent", 0) or 0, reverse=True):
        info = p.info
        procs.append({
            "pid": info["pid"],
            "name": info["name"],
            "cpu_percent": info.get("cpu_percent", 0),
            "memory_percent": round(info.get("memory_percent", 0) or 0, 1),
        })
        if len(procs) >= top_n:
            break
    return procs


async def read_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            return f.read(1024 * 1024)
    except Exception as e:
        return f"Error reading {path}: {e}"


async def list_directory(path: str = ".") -> list:
    entries = []
    try:
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            entries.append({
                "name": name,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else 0,
            })
    except Exception as e:
        entries.append({"error": str(e)})
    return entries


# ── Network Tools ────────────────────────────────────────────

async def network_connections() -> list:
    conns = []
    for c in psutil.net_connections(kind="inet"):
        conns.append({
            "fd": c.fd,
            "family": str(c.family),
            "type": str(c.type),
            "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
            "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
            "status": c.status,
            "pid": c.pid,
        })
    return conns


async def network_interfaces() -> dict:
    addrs = psutil.net_if_addrs()
    result = {}
    for name, addr_list in addrs.items():
        result[name] = [
            {"family": str(a.family), "address": a.address, "netmask": a.netmask}
            for a in addr_list
        ]
    return result


# ── Registration ─────────────────────────────────────────────

def register_builtin_tools():
    tools = [
        (
            ToolDefinition(
                name="system_info",
                description="Get system information (CPU, memory, disk, uptime)",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.READ],
            ),
            system_info,
        ),
        (
            ToolDefinition(
                name="process_list",
                description="List running processes sorted by CPU usage",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.READ],
            ),
            process_list,
        ),
        (
            ToolDefinition(
                name="read_file",
                description="Read contents of a file",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.READ],
            ),
            read_file,
        ),
        (
            ToolDefinition(
                name="list_directory",
                description="List contents of a directory",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.READ],
            ),
            list_directory,
        ),
        (
            ToolDefinition(
                name="network_connections",
                description="List active network connections",
                category=ToolCategory.NETWORK,
                permissions_required=[ToolPermission.READ, ToolPermission.NETWORK],
            ),
            network_connections,
        ),
        (
            ToolDefinition(
                name="network_interfaces",
                description="List network interfaces and addresses",
                category=ToolCategory.NETWORK,
                permissions_required=[ToolPermission.READ, ToolPermission.NETWORK],
            ),
            network_interfaces,
        ),
    ]

    for definition, handler in tools:
        tool_registry.register(definition, handler)
