"""Live Windows environment inspection and context resolution."""

import os
import sys
import shutil
import platform
import subprocess
from typing import List, Dict, Optional
from winterm.models.context import SystemContext, ElevationLevel
from winterm.knowledge.elevation_rules import ElevationRules


class WindowsEnvironment:
    """Probes the live Windows operating system to build an accurate SystemContext snapshot."""

    _cached_context: Optional[SystemContext] = None

    @classmethod
    def probe(cls, force_refresh: bool = False) -> SystemContext:
        """Inspects the local Windows system and returns a populated SystemContext."""
        if cls._cached_context and not force_refresh:
            return cls._cached_context

        # OS Details
        os_name = platform.system()
        os_release = platform.release()
        os_version = platform.version()
        arch = platform.machine()

        # Linux / WSL detection
        is_linux_host = (os_name == "Linux")
        is_wsl = False
        linux_distro = ""

        if is_linux_host:
            # Check WSL via /proc/version or env
            if "WSL_DISTRO_NAME" in os.environ:
                is_wsl = True
                linux_distro = os.environ.get("WSL_DISTRO_NAME", "")
            elif os.path.exists("/proc/version"):
                try:
                    with open("/proc/version", "r", encoding="utf-8") as f:
                        vcontent = f.read().lower()
                        if "microsoft" in vcontent or "wsl" in vcontent:
                            is_wsl = True
                except Exception:
                    pass
            # Read distro name from /etc/os-release
            if not linux_distro and os.path.exists("/etc/os-release"):
                try:
                    with open("/etc/os-release", "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("NAME="):
                                linux_distro = line.split("=")[1].strip().strip('"')
                                break
                except Exception:
                    pass

        # Elevation
        elevation = ElevationRules.detect_elevation_level()

        # PowerShell / Bash version check
        ps_version = "5.1" if os_name == "Windows" else "N/A"
        pwsh_available = shutil.which("pwsh") is not None
        wsl_available = shutil.which("wsl") is not None

        # Detect package managers
        package_managers = []
        for pm in ["winget", "choco", "scoop", "apt", "apt-get", "dnf", "yum", "pacman", "apk"]:
            if shutil.which(pm) is not None:
                package_managers.append(pm)

        # Detect LongPathsEnabled via registry or default
        long_paths = False
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\FileSystem",
                0,
                winreg.KEY_READ,
            ) as key:
                val, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
                long_paths = (val == 1)
        except Exception:
            pass

        # Code page
        code_page = 65001
        try:
            import ctypes
            code_page = ctypes.windll.kernel32.GetConsoleOutputCP()
        except Exception:
            pass

        context = SystemContext(
            os_name=os_name,
            os_release=os_release,
            os_build=os_version,
            architecture=arch,
            powershell_version=ps_version,
            pwsh_available=pwsh_available,
            wsl_available=wsl_available,
            is_wsl=is_wsl,
            is_linux_host=is_linux_host,
            linux_distro=linux_distro,
            current_elevation=elevation,
            current_directory=os.getcwd(),
            active_code_page=code_page,
            long_paths_enabled=long_paths,
            installed_package_managers=package_managers,
            environment_variables={
                "PATH": os.environ.get("PATH", ""),
                "TEMP": os.environ.get("TEMP", ""),
                "USERPROFILE": os.environ.get("USERPROFILE", ""),
                "PROCESSOR_ARCHITECTURE": os.environ.get("PROCESSOR_ARCHITECTURE", arch),
            },
        )

        cls._cached_context = context
        return context
