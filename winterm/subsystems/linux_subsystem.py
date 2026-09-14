"""Layer 10: Linux & WSL Subsystem.

Provides deterministic system operations, service inspection (systemd),
process control, storage/networking diagnostics, package management,
and bidirectional path translation between Windows and Linux/WSL.
"""

import os
import re
import shutil
import subprocess
from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class LinuxSubsystem:
    """Manages Linux & WSL2 system operations, processes, services, networking, and path translation."""

    @classmethod
    def convert_path(cls, path: str, to_linux: bool = True) -> str:
        """Converts paths between Windows format (e.g. C:\\path\\to\\file) and Linux format (/mnt/c/path/to/file)."""
        clean_path = path.strip()
        if not clean_path:
            return ""

        # Try native wslpath if available
        if shutil.which("wsl") is not None:
            flag = "-u" if to_linux else "-w"
            try:
                res = subprocess.run(
                    ["wsl.exe", "wslpath", flag, clean_path],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass

        # Deterministic Python fallback
        if to_linux:
            # Match Windows drive letter: e.g. C:\ or C:/ or D:\
            match = re.match(r"^([a-zA-Z]):[\\/](.*)$", clean_path)
            if match:
                drive_letter = match.group(1).lower()
                rest = match.group(2).replace("\\", "/")
                return f"/mnt/{drive_letter}/{rest}"
            return clean_path.replace("\\", "/")
        else:
            # Match WSL mount: e.g. /mnt/c/path or /mnt/d/path
            match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", clean_path)
            if match:
                drive_letter = match.group(1).upper()
                rest = match.group(2).replace("/", "\\")
                return f"{drive_letter}:\\{rest}"
            return clean_path.replace("/", "\\")

    @classmethod
    def list_wsl_distros(cls) -> PlanStep:
        """Enumerates installed WSL distributions, running states, and WSL version."""
        return PlanStep(
            step_id="linux-wsl-distros",
            title="Enumerate WSL Linux Distributions and Running States",
            category=ActionCategory.VIRTUALIZATION,
            raw_intent="list wsl distros",
            target_shell=ShellType.CMD,
            command="wsl.exe --list --verbose",
            metadata={"subsystem": "linux", "action": "wsl_list"},
        )

    @classmethod
    def inspect_service(cls, service_name: str) -> PlanStep:
        """Inspects status of a systemd service daemon inside Linux / WSL."""
        return PlanStep(
            step_id=f"linux-service-status-{service_name}",
            title=f"Inspect Status of Linux Service: {service_name}",
            category=ActionCategory.SERVICE,
            raw_intent=f"inspect service {service_name}",
            target_shell=ShellType.WSL_BASH,
            command=f"systemctl status {service_name} --no-pager",
            metadata={"subsystem": "linux", "service": service_name, "action": "service_status"},
        )

    @classmethod
    def restart_service(cls, service_name: str) -> PlanStep:
        """Restarts a systemd service daemon inside Linux / WSL with elevated privileges."""
        return PlanStep(
            step_id=f"linux-service-restart-{service_name}",
            title=f"Restart Linux Service: {service_name}",
            category=ActionCategory.SERVICE,
            raw_intent=f"restart service {service_name}",
            target_shell=ShellType.WSL_BASH,
            required_elevation=ElevationLevel.ADMIN,
            command=f"sudo systemctl restart {service_name}",
            metadata={"subsystem": "linux", "service": service_name, "action": "service_restart"},
        )

    @classmethod
    def list_processes(cls, filter_name: Optional[str] = None) -> PlanStep:
        """Lists active Linux processes, optionally filtering by executable name."""
        if filter_name:
            cmd = f"ps aux | grep -i '{filter_name}' | grep -v grep"
        else:
            cmd = "ps aux --sort=-%mem | head -n 30"

        return PlanStep(
            step_id="linux-processes-list",
            title="Enumerate Active Linux Processes",
            category=ActionCategory.PROCESS,
            raw_intent="list linux processes",
            target_shell=ShellType.WSL_BASH,
            command=cmd,
            metadata={"subsystem": "linux", "action": "process_list"},
        )

    @classmethod
    def kill_process(cls, pid: int, signal: int = 15) -> PlanStep:
        """Terminates a Linux process by PID using standard POSIX signal (15=SIGTERM, 9=SIGKILL)."""
        return PlanStep(
            step_id=f"linux-kill-pid-{pid}",
            title=f"Send Signal {signal} to Linux Process {pid}",
            category=ActionCategory.PROCESS,
            raw_intent=f"kill linux pid {pid}",
            target_shell=ShellType.WSL_BASH,
            command=f"kill -{signal} {pid}",
            metadata={"subsystem": "linux", "pid": pid, "signal": signal, "action": "process_kill"},
        )

    @classmethod
    def disk_free(cls) -> PlanStep:
        """Queries human-readable disk capacity and mounted filesystem metrics."""
        return PlanStep(
            step_id="linux-disk-free",
            title="Inspect Linux Filesystem Free Space",
            category=ActionCategory.STORAGE,
            raw_intent="check linux disk free space",
            target_shell=ShellType.WSL_BASH,
            command="df -h -x tmpfs -x devtmpfs",
            metadata={"subsystem": "linux", "action": "disk_free"},
        )

    @classmethod
    def list_block_devices(cls) -> PlanStep:
        """Lists block devices, partition layout, sizes, and mountpoints."""
        return PlanStep(
            step_id="linux-block-devices",
            title="Enumerate Linux Storage Block Devices",
            category=ActionCategory.STORAGE,
            raw_intent="list linux block devices",
            target_shell=ShellType.WSL_BASH,
            command="lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE",
            metadata={"subsystem": "linux", "action": "block_devices"},
        )

    @classmethod
    def network_interfaces(cls) -> PlanStep:
        """Displays Linux network interface addresses and link states."""
        return PlanStep(
            step_id="linux-net-interfaces",
            title="Inspect Linux Network Interfaces and IP Addresses",
            category=ActionCategory.NETWORK,
            raw_intent="check linux network interfaces",
            target_shell=ShellType.WSL_BASH,
            command="ip -brief address show",
            metadata={"subsystem": "linux", "action": "network_interfaces"},
        )

    @classmethod
    def listening_ports(cls) -> PlanStep:
        """Enumerates active TCP and UDP listening ports and associated processes."""
        return PlanStep(
            step_id="linux-listening-ports",
            title="Inspect Linux Active Listening Ports",
            category=ActionCategory.NETWORK,
            raw_intent="check linux listening ports",
            target_shell=ShellType.WSL_BASH,
            command="ss -tulpn",
            metadata={"subsystem": "linux", "action": "listening_ports"},
        )

    @classmethod
    def install_package(cls, package_name: str, manager: str = "auto") -> PlanStep:
        """Installs a Linux package with guaranteed non-interactive switches."""
        if manager == "apt" or manager == "auto":
            cmd = f"sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {package_name}"
        elif manager == "dnf":
            cmd = f"sudo dnf install -y {package_name}"
        elif manager == "pacman":
            cmd = f"sudo pacman -S --noconfirm {package_name}"
        elif manager == "apk":
            cmd = f"apk add --no-cache {package_name}"
        else:
            cmd = f"sudo apt-get install -y {package_name}"

        return PlanStep(
            step_id=f"linux-pkg-install-{package_name}",
            title=f"Install Linux Package: {package_name}",
            category=ActionCategory.VIRTUALIZATION,
            raw_intent=f"install package {package_name}",
            target_shell=ShellType.WSL_BASH,
            required_elevation=ElevationLevel.ADMIN,
            command=cmd,
            metadata={"subsystem": "linux", "package": package_name, "action": "package_install"},
        )
