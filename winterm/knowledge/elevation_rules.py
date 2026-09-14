"""Elevation Rules: Detection, UAC handling, and elevation command wrappers."""

import os
import sys
import ctypes
from typing import List, Set
from winterm.models.context import ElevationLevel, ShellType


class ElevationRules:
    """Manages Windows User Account Control (UAC), Administrator token verification, and elevation wrapping."""

    # Keywords and subsystem paths that strictly require Administrator privileges
    ELEVATION_REQUIRED_PATTERNS: List[str] = [
        "hklm:",
        "hkey_local_machine",
        "system32/drivers/etc/hosts",
        "netsh advfirewall",
        "restart-service",
        "start-service",
        "stop-service",
        "set-service",
        "sc.exe",
        "diskpart",
        "sfc /scannow",
        "dism /online",
        "bcdedit",
    ]

    @classmethod
    def is_current_process_admin(cls) -> bool:
        """Determines if current Python execution context has Administrator privileges."""
        if os.name != "nt":
            return False
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @classmethod
    def detect_elevation_level(cls) -> ElevationLevel:
        """Returns current ElevationLevel enum."""
        if cls.is_current_process_admin():
            return ElevationLevel.ADMIN
        return ElevationLevel.STANDARD

    @classmethod
    def requires_elevation(cls, command: str) -> bool:
        """Determines if a command text triggers elevated permission requirements."""
        cmd_lower = command.lower()
        return any(pattern in cmd_lower for pattern in cls.ELEVATION_REQUIRED_PATTERNS)

    @classmethod
    def wrap_with_runas(cls, command: str, shell: ShellType = ShellType.POWERSHELL_51) -> str:
        """Wraps a command into an elevated UAC RunAs invocation."""
        escaped_cmd = command.replace('"', '`"')
        if shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7):
            return (
                f"Start-Process powershell.exe -Verb RunAs -ArgumentList "
                f"'-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', \"{escaped_cmd}\""
            )
        else:
            return (
                f"powershell.exe -Command \"Start-Process cmd.exe -Verb RunAs -ArgumentList "
                f"'/c', \\\"{escaped_cmd}\\\"\""
            )
