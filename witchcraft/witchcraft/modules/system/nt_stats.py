#!/usr/bin/env python3
"""
WitchcraftFEX System Statistics & Hardware Monitor Module (nt_stats).
Collects CPU, RAM, GPU, Containers (Docker), VMs (libvirt), Processes (htop-like),
Network Interfaces, and Uptime with colored CLI and JSON support.
"""

import os
import sys
import json
import subprocess
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from witchcraft.metalcore.core import (
    net_logger,
    eyeliner,
    search_arg,
    PROGRESS_BAR,
    COLORS
)


def get_system_metrics() -> Dict[str, Any]:
    """Collect real-time system metrics using pure standard library & coreutils."""
    metrics: Dict[str, Any] = {}

    # 1. OS & Uptime
    uname = os.uname()
    metrics["os"] = {
        "system": uname.sysname,
        "hostname": uname.nodename,
        "kernel": uname.release,
        "arch": uname.machine
    }

    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            metrics["uptime"] = {
                "seconds": uptime_seconds,
                "formatted": f"{days}d {hours}h {minutes}m"
            }
    except Exception:
        metrics["uptime"] = {"seconds": 0, "formatted": "N/A"}

    # 2. Load Average & CPU
    try:
        l1, l5, l15 = os.getloadavg()
        loadavg = {"1m": round(l1, 2), "5m": round(l5, 2), "15m": round(l15, 2)}
    except Exception:
        loadavg = {"1m": 0.0, "5m": 0.0, "15m": 0.0}

    cpu_model = "Generic CPU"
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    cores = os.cpu_count() or 1
    cpu_percent = round(min(100.0, (loadavg["1m"] / cores) * 100), 1)

    metrics["cpu"] = {
        "model": cpu_model,
        "cores": cores,
        "loadavg": loadavg,
        "usage_percent": cpu_percent
    }

    # 3. RAM & Swap
    meminfo = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = parts[1].strip().split()[0]
                    meminfo[k] = int(v) * 1024
        total = meminfo.get("MemTotal", 1)
        avail = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used = total - avail
        swap_total = meminfo.get("SwapTotal", 0)
        swap_free = meminfo.get("SwapFree", 0)
        swap_used = swap_total - swap_free

        metrics["memory"] = {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": meminfo.get("MemFree", 0),
            "available_bytes": avail,
            "percent_used": round((used / total) * 100, 1),
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "available_gb": round(avail / (1024**3), 2),
            "swap_total_gb": round(swap_total / (1024**3), 2),
            "swap_used_gb": round(swap_used / (1024**3), 2),
            "swap_percent_used": round((swap_used / swap_total) * 100, 1) if swap_total > 0 else 0
        }
    except Exception as e:
        metrics["memory"] = {"error": str(e), "percent_used": 0}

    # 4. GPU Detection
    gpu_list: List[Dict[str, Any]] = []
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=1
        )
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpu_list.append({
                        "name": parts[0],
                        "vram_total_mb": parts[1],
                        "vram_used_mb": parts[2],
                        "utilization_percent": parts[3],
                        "temp_c": parts[4]
                    })
    except Exception:
        pass

    if not gpu_list:
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=1)
            for line in res.stdout.splitlines():
                if any(x in line for x in ("VGA compatible controller", "3D controller", "Display controller")):
                    gpu_name = line.split(":", 2)[-1].strip()
                    gpu_list.append({"name": gpu_name, "utilization_percent": "N/A"})
        except Exception:
            pass

    metrics["gpu"] = gpu_list

    # 5. Containers (Docker & Podman)
    containers: List[Dict[str, Any]] = []
    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().splitlines():
                parts = line.split("\t")
                status = parts[3] if len(parts) > 3 else ""
                containers.append({
                    "id": parts[0],
                    "image": parts[1] if len(parts) > 1 else "",
                    "name": parts[2] if len(parts) > 2 else "",
                    "status": status,
                    "running": "Up" in status,
                    "ports": parts[4] if len(parts) > 4 else ""
                })
    except Exception:
        pass

    metrics["containers"] = {
        "items": containers,
        "total": len(containers),
        "running": sum(1 for c in containers if c.get("running"))
    }

    # 6. Virtual Machines (libvirt / virsh)
    vms: List[Dict[str, Any]] = []
    try:
        res = subprocess.run(["virsh", "list", "--all"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            if len(lines) > 2:
                for line in lines[2:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        state = " ".join(parts[2:])
                        vms.append({
                            "id": parts[0],
                            "name": parts[1],
                            "state": state,
                            "running": "running" in state.lower()
                        })
    except Exception:
        pass

    metrics["vms"] = {
        "items": vms,
        "total": len(vms),
        "running": sum(1 for v in vms if v.get("running"))
    }

    # 7. Active Processes (Top CPU/Memory)
    processes: List[Dict[str, Any]] = []
    try:
        res = subprocess.run(
            ["ps", "-eo", "pid,user,pcpu,pmem,comm", "--sort=-pcpu"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            for line in lines[1:12]:
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    processes.append({
                        "pid": parts[0],
                        "user": parts[1],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "command": parts[4]
                    })
    except Exception:
        pass

    metrics["processes"] = processes

    # 8. Network Interfaces & Traffic
    net_ifaces: List[Dict[str, Any]] = []
    try:
        with open("/proc/net/dev", "r") as f:
            for line in f.readlines()[2:]:
                if ":" in line:
                    iface, data = line.split(":", 1)
                    iface = iface.strip()
                    parts = data.split()
                    if len(parts) >= 16:
                        rx_bytes = int(parts[0])
                        tx_bytes = int(parts[8])
                        net_ifaces.append({
                            "interface": iface,
                            "rx_mb": round(rx_bytes / (1024 * 1024), 2),
                            "tx_mb": round(tx_bytes / (1024 * 1024), 2)
                        })
    except Exception:
        pass

    metrics["network"] = net_ifaces
    return metrics


def format_progress_bar(percent: float, length: int = 20) -> str:
    """Generate an ASCII progress bar."""
    filled = int(round(length * percent / 100))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {percent}%"


def print_cli_stats(metrics: Dict[str, Any]):
    """Format and display system statistics in terminal with colors."""
    eyeliner("WitchcraftFEX :: System Hardware & Monitor Dashboard", "magenta")

    # Host & Uptime
    os_info = metrics.get("os", {})
    uptime = metrics.get("uptime", {})
    net_logger(f"  ● Hostname : {os_info.get('hostname')} ({os_info.get('system')} {os_info.get('kernel')} {os_info.get('arch')})", "cyan", "bold")
    net_logger(f"  ● Uptime   : {uptime.get('formatted')} | Load Avg: 1m={metrics.get('cpu', {}).get('loadavg', {}).get('1m')}, 5m={metrics.get('cpu', {}).get('loadavg', {}).get('5m')}, 15m={metrics.get('cpu', {}).get('loadavg', {}).get('15m')}", "white")

    # CPU & RAM
    cpu = metrics.get("cpu", {})
    mem = metrics.get("memory", {})
    print()
    net_logger("── CPU & MEMORY ─────────────────────────────────────────────────────────────", "yellow", "bold")
    net_logger(f"  CPU Model: {cpu.get('model')} ({cpu.get('cores')} cores)", "white")
    net_logger(f"  CPU Load : {format_progress_bar(cpu.get('usage_percent', 0))}", "green", "bold")
    net_logger(f"  RAM Usage: {format_progress_bar(mem.get('percent_used', 0))} ({mem.get('used_gb')} GB / {mem.get('total_gb')} GB)", "cyan", "bold")
    if mem.get("swap_total_gb", 0) > 0:
        net_logger(f"  Swap     : {format_progress_bar(mem.get('swap_percent_used', 0))} ({mem.get('swap_used_gb')} GB / {mem.get('swap_total_gb')} GB)", "magenta")

    # GPU
    gpu_list = metrics.get("gpu", [])
    if gpu_list:
        print()
        net_logger("── GPU HARDWARE ─────────────────────────────────────────────────────────────", "yellow", "bold")
        for g in gpu_list:
            vram_info = f" | VRAM: {g.get('vram_used_mb')}MB / {g.get('vram_total_mb')}MB" if "vram_total_mb" in g else ""
            net_logger(f"  🎮 {g.get('name')}{vram_info}", "white")

    # Containers & VMs
    containers = metrics.get("containers", {})
    vms = metrics.get("vms", {})
    print()
    net_logger("── VIRTUALIZATION & CONTAINERS ──────────────────────────────────────────────", "yellow", "bold")
    net_logger(f"  🐳 Docker Containers: {containers.get('running', 0)} running / {containers.get('total', 0)} total", "cyan", "bold")
    for c in containers.get("items", [])[:5]:
        status_color = "green" if c.get("running") else "bright_black"
        net_logger(f"     [{c.get('id')[:10]}] {c.get('name'):<20} ({c.get('image')[:25]}) - {c.get('status')}", status_color)

    net_logger(f"  🖥️  Libvirt VMs      : {vms.get('running', 0)} running / {vms.get('total', 0)} total", "magenta", "bold")
    for v in vms.get("items", [])[:5]:
        v_color = "green" if v.get("running") else "bright_black"
        net_logger(f"     [{v.get('name')}] - State: {v.get('state')}", v_color)

    # Processes
    procs = metrics.get("processes", [])
    if procs:
        print()
        net_logger("── TOP PROCESSES (HTOP) ─────────────────────────────────────────────────────", "yellow", "bold")
        net_logger(f"  {'PID':<10} {'USER':<12} {'CPU%':<8} {'MEM%':<8} {'COMMAND'}", "cyan", "bold")
        for p in procs[:8]:
            net_logger(f"  {p.get('pid'):<10} {p.get('user'):<12} {p.get('cpu'):<8} {p.get('mem'):<8} {p.get('command')}", "white")

    # Network
    net_list = metrics.get("network", [])
    if net_list:
        print()
        net_logger("── NETWORK INTERFACES ───────────────────────────────────────────────────────", "yellow", "bold")
        for iface in net_list:
            net_logger(f"  📡 {iface.get('interface'):<15} RX: {iface.get('rx_mb')} MB | TX: {iface.get('tx_mb')} MB", "white")

    print()


def nt_stats_wrapper(args_v: list) -> int:
    """Entry point for CLI command nt_stats / system.stats."""
    is_json = False
    for arg in args_v:
        if arg in ("--json", "--json=true", "--output_mode_json") or search_arg(args_v, "json", False) in ("true", "1", "yes"):
            is_json = True
            break

    metrics = get_system_metrics()

    if is_json:
        print(json.dumps(metrics, indent=2))
    else:
        print_cli_stats(metrics)

    return 0


if __name__ == "__main__":
    nt_stats_wrapper(sys.argv)
