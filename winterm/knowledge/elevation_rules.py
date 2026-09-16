"""Elevation Rules: Detection, UAC handling, and elevation command wrappers."""

import os
import re
import base64
import ctypes
from typing import List
from winterm.models.context import ElevationLevel, ShellType


class ElevationRules:
    """Manages Windows User Account Control (UAC), Administrator token verification, and elevation wrapping."""

    # Human-readable keywords that strictly require Administrator privileges.
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

    # Compiled, word-boundary aware matchers (path separators normalized) so that
    # e.g. `Get-Content sc.exe.log` is not mistaken for an elevation request.
    _ELEVATION_REGEXES: List[re.Pattern] = [
        re.compile(r"\bhklm\b", re.IGNORECASE),
        re.compile(r"hkey_local_machine", re.IGNORECASE),
        re.compile(r"system32[\\/]drivers[\\/]etc[\\/]hosts", re.IGNORECASE),
        re.compile(r"\bnetsh\s+advfirewall\b", re.IGNORECASE),
        re.compile(r"\b(restart|start|stop|set)-service\b", re.IGNORECASE),
        re.compile(r"(?:^|[\s\"'\\/])sc\.exe\b", re.IGNORECASE),
        re.compile(r"\bdiskpart\b", re.IGNORECASE),
        re.compile(r"\bsfc\s+/scannow\b", re.IGNORECASE),
        re.compile(r"\bdism\s+/online\b", re.IGNORECASE),
        re.compile(r"\bbcdedit\b", re.IGNORECASE),
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
        normalized = str(command).replace("\\", "/")
        return any(pat.search(normalized) for pat in cls._ELEVATION_REGEXES)

    @classmethod
    def wrap_with_runas(cls, command: str, shell: ShellType = ShellType.POWERSHELL_51) -> str:
        """Wraps a command into an elevated invocation.

        Windows uses a ``Start-Process -Verb RunAs -Wait`` with an
        ``-EncodedCommand`` payload (Base64 UTF-16LE). Encoding avoids all
        quoting/injection problems from interpolating the command into a
        ``-Command`` string. The elevated child's stdout/stderr cannot be
        captured across the UAC boundary; only completion is awaited.

        POSIX shells use ``sudo -n`` so a password prompt fails fast instead of
        hanging a non-interactive agent.
        """
        if shell in (ShellType.WSL_BASH, ShellType.BASH):
            escaped = str(command).replace("'", "'\\''")
            return f"sudo -n bash -c '{escaped}'"

        encoded = base64.b64encode(str(command).encode("utf-16-le")).decode("ascii")
        return (
            "Start-Process -FilePath powershell.exe -Verb RunAs -Wait -ArgumentList "
            f"'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand','{encoded}'"
        )